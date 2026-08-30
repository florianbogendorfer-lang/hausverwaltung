"""Lesende Endpunkte für Fälle inkl. Trace/Audit (§10 UI-1/UI-3 — die
grafische Oberfläche folgt erst in Phase 4; diese Endpunkte machen den
Agent-Lauf bereits jetzt über die API nachvollziehbar, §11)."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlmodel import Session, select

from app.agent.tools import log_aktion
from app.auth import admin_erforderlich
from app.db import get_session
from app.models import (
    Aktion,
    Akteur,
    Benutzer,
    Dienstleister,
    Fall,
    FallStatus,
    Gewerk,
    Kontakt,
    Nachricht,
    Objekt,
    Rechnungsbeleg,
    Trace,
)

router = APIRouter(prefix="/faelle", tags=["faelle"])


class FallManuelleZuordnung(BaseModel):
    objekt_id: Optional[int] = None
    melder_kontakt_id: Optional[int] = None
    dienstleister_id: Optional[int] = None
    gewerk: Optional[Gewerk] = None
    status: Optional[FallStatus] = None


@router.get("", response_model=list[Fall])
def liste_faelle(session: Session = Depends(get_session)) -> list[Fall]:
    # Explizite Reihenfolge: ohne ORDER BY garantiert SQL keine bestimmte
    # Zeilenreihenfolge (Postgres/Prod kann sie sogar zwischen Abfragen
    # ändern) — das Kanban-Board (frontend/src/pages/Board.tsx) sortiert
    # selbst nicht, verlässt sich also direkt auf diese Reihenfolge.
    return list(
        session.exec(
            select(Fall).where(Fall.geloescht.is_(False)).order_by(Fall.erstellt_am)
        ).all()
    )


@router.get("/{fall_id}", response_model=Fall)
def fall_details(fall_id: int, session: Session = Depends(get_session)) -> Fall:
    fall = session.get(Fall, fall_id)
    if fall is None or fall.geloescht:
        raise HTTPException(status_code=404, detail="Fall nicht gefunden")
    return fall


@router.delete("/{fall_id}", status_code=204)
def fall_loeschen(
    fall_id: int,
    admin: Benutzer = Depends(admin_erforderlich),
    session: Session = Depends(get_session),
) -> None:
    """Soft-Delete (FR/§0: der Audit-Trail — Aktionen/Traces — bleibt
    append-only erhalten, nur die Sichtbarkeit in Board/Listen entfällt)."""
    fall = session.get(Fall, fall_id)
    if fall is None or fall.geloescht:
        raise HTTPException(status_code=404, detail="Fall nicht gefunden")

    fall.geloescht = True
    fall.geloescht_am = datetime.utcnow()
    fall.geaendert_am = fall.geloescht_am
    session.add(fall)
    session.commit()
    log_aktion(session, fall.id, Akteur.operator, "fall:geloescht", {"von": admin.email})


@router.get("/{fall_id}/trace", response_model=list[Trace])
def fall_trace(fall_id: int, session: Session = Depends(get_session)) -> list[Trace]:
    if session.get(Fall, fall_id) is None:
        raise HTTPException(status_code=404, detail="Fall nicht gefunden")
    return list(
        session.exec(select(Trace).where(Trace.fall_id == fall_id).order_by(Trace.schritt_nr)).all()
    )


@router.get("/{fall_id}/aktionen", response_model=list[Aktion])
def fall_aktionen(fall_id: int, session: Session = Depends(get_session)) -> list[Aktion]:
    if session.get(Fall, fall_id) is None:
        raise HTTPException(status_code=404, detail="Fall nicht gefunden")
    return list(
        session.exec(
            select(Aktion).where(Aktion.fall_id == fall_id).order_by(Aktion.zeitstempel)
        ).all()
    )


@router.patch("/{fall_id}", response_model=Fall)
def fall_manuell_zuordnen(
    fall_id: int, eingabe: FallManuelleZuordnung, session: Session = Depends(get_session)
) -> Fall:
    """Manuelle Zuordnung von Objekt/Melder/Dienstleister/Gewerk durch den
    Bearbeiter (u. a. für eskalierte Fälle, bei denen der Agent die
    Stammdaten nicht selbst ermitteln konnte)."""
    fall = session.get(Fall, fall_id)
    if fall is None or fall.geloescht:
        raise HTTPException(status_code=404, detail="Fall nicht gefunden")

    aenderungen: dict = {}
    daten = eingabe.model_dump(exclude_unset=True)

    if "objekt_id" in daten:
        if daten["objekt_id"] is not None and session.get(Objekt, daten["objekt_id"]) is None:
            raise HTTPException(status_code=404, detail="Objekt nicht gefunden")
        fall.objekt_id = daten["objekt_id"]
        aenderungen["objekt_id"] = daten["objekt_id"]

    if "melder_kontakt_id" in daten:
        if (
            daten["melder_kontakt_id"] is not None
            and session.get(Kontakt, daten["melder_kontakt_id"]) is None
        ):
            raise HTTPException(status_code=404, detail="Kontakt nicht gefunden")
        fall.melder_kontakt_id = daten["melder_kontakt_id"]
        aenderungen["melder_kontakt_id"] = daten["melder_kontakt_id"]

    if "dienstleister_id" in daten:
        if (
            daten["dienstleister_id"] is not None
            and session.get(Dienstleister, daten["dienstleister_id"]) is None
        ):
            raise HTTPException(status_code=404, detail="Dienstleister nicht gefunden")
        fall.dienstleister_id = daten["dienstleister_id"]
        aenderungen["dienstleister_id"] = daten["dienstleister_id"]

    if "gewerk" in daten:
        fall.gewerk = daten["gewerk"]
        aenderungen["gewerk"] = daten["gewerk"]

    if "status" in daten and daten["status"] is not None:
        ziel = daten["status"]
        # Manuell erlaubte Übergänge: (a) der bestehende Resume-Weg
        # ESKALIERT -> EINGEORDNET, (b) eine manuelle Eskalation aus JEDEM
        # Status — als Notausstieg, falls ein Fall z. B. durch einen
        # unerwarteten Fehler mitten im (synchronen, nicht automatisch
        # wiederholten) Agent-Loop hängen bleibt und kein automatischer
        # Trigger mehr greift — und (c) der Abschluss durch den Bearbeiter,
        # nachdem die Arbeit vor Ort erledigt (und optional die Rechnung
        # über das Dienstleister-Portal eingereicht) wurde. Es gibt dafür
        # bewusst KEINEN automatischen Übergang: der Abschluss eines Falls
        # ist eine bewusste Entscheidung des Bearbeiters (HITL), keine
        # Automatik.
        erlaubt = (
            (fall.status == FallStatus.eskaliert and ziel == FallStatus.eingeordnet)
            or (ziel == FallStatus.eskaliert)
            or (
                fall.status in (FallStatus.arbeit_erledigt, FallStatus.rechnung_erfasst)
                and ziel == FallStatus.abgeschlossen
            )
        )
        if not erlaubt:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Nur der Übergang von ESKALIERT zu EINGEORDNET, eine manuelle "
                    "Eskalation oder der Abschluss ab ARBEIT_ERLEDIGT/RECHNUNG_ERFASST "
                    "sind erlaubt"
                ),
            )
        fall.status = ziel
        aenderungen["status"] = ziel.value

    if not aenderungen:
        return fall

    fall.geaendert_am = datetime.utcnow()
    session.add(fall)
    session.commit()
    session.refresh(fall)
    log_aktion(session, fall.id, Akteur.operator, "fall:manuell_aktualisiert", aenderungen)
    return fall


@router.get("/{fall_id}/nachrichten", response_model=list[Nachricht])
def fall_nachrichten(fall_id: int, session: Session = Depends(get_session)) -> list[Nachricht]:
    if session.get(Fall, fall_id) is None:
        raise HTTPException(status_code=404, detail="Fall nicht gefunden")
    return list(
        session.exec(
            select(Nachricht).where(Nachricht.fall_id == fall_id).order_by(Nachricht.erstellt_am)
        ).all()
    )


@router.get("/{fall_id}/rechnungsbeleg")
def rechnungsbeleg_herunterladen(fall_id: int, session: Session = Depends(get_session)) -> Response:
    """Download des vom Dienstleister eingereichten Rechnungsbelegs (siehe
    POST /dienstleister-portal/{token}/rechnung) — nur für eingeloggte
    Bearbeiter (Router-weite `_angemeldet`-Dependency, app/main.py), die
    Bytes selbst sind nie Teil der normalen JSON-Fall-Ansicht."""
    if session.get(Fall, fall_id) is None:
        raise HTTPException(status_code=404, detail="Fall nicht gefunden")
    beleg = session.exec(
        select(Rechnungsbeleg)
        .where(Rechnungsbeleg.fall_id == fall_id)
        .order_by(Rechnungsbeleg.hochgeladen_am.desc())
    ).first()
    if beleg is None:
        raise HTTPException(status_code=404, detail="Kein Rechnungsbeleg vorhanden")
    # Anführungszeichen aus dem Dateinamen entfernen, bevor er roh in den
    # Content-Disposition-Header eingebettet wird (Header-Injection-Schutz;
    # Zeilenumbrüche wurden bereits beim Upload entfernt, siehe
    # app/routers/dienstleister_portal.py).
    dateiname = beleg.dateiname.replace('"', "'")
    return Response(
        content=beleg.inhalt,
        media_type=beleg.content_type,
        headers={"Content-Disposition": f'attachment; filename="{dateiname}"'},
    )
