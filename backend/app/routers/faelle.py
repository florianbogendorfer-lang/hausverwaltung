"""Lesende Endpunkte für Fälle inkl. Trace/Audit (§10 UI-1/UI-3 — die
grafische Oberfläche folgt erst in Phase 4; diese Endpunkte machen den
Agent-Lauf bereits jetzt über die API nachvollziehbar, §11)."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.agent.tools import log_aktion
from app.db import get_session
from app.models import Aktion, Akteur, Dienstleister, Fall, FallStatus, Gewerk, Kontakt, Nachricht, Objekt, Trace

router = APIRouter(prefix="/faelle", tags=["faelle"])


class FallManuelleZuordnung(BaseModel):
    objekt_id: Optional[int] = None
    melder_kontakt_id: Optional[int] = None
    dienstleister_id: Optional[int] = None
    gewerk: Optional[Gewerk] = None
    status: Optional[FallStatus] = None


@router.get("", response_model=list[Fall])
def liste_faelle(session: Session = Depends(get_session)) -> list[Fall]:
    return list(session.exec(select(Fall)).all())


@router.get("/{fall_id}", response_model=Fall)
def fall_details(fall_id: int, session: Session = Depends(get_session)) -> Fall:
    fall = session.get(Fall, fall_id)
    if fall is None:
        raise HTTPException(status_code=404, detail="Fall nicht gefunden")
    return fall


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
    if fall is None:
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
        if not (fall.status == FallStatus.eskaliert and daten["status"] == FallStatus.eingeordnet):
            raise HTTPException(
                status_code=400,
                detail="Nur der Übergang von ESKALIERT zu EINGEORDNET ist manuell erlaubt",
            )
        fall.status = daten["status"]
        aenderungen["status"] = daten["status"].value

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
