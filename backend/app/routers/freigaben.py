"""Freigabe-Queue-API (§10 UI-2 — die grafische Oberfläche folgt in Phase 4;
diese Endpunkte machen den propose/commit-Mechanismus bereits jetzt
bedienbar, FR-HITL-4/5)."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.agent.freigabe_service import FreigabeBereitsEntschieden, ablehnen, freigeben, ist_ueberfaellig
from app.agent.mail_adapter import MailAdapter, get_mail_adapter
from app.auth import aktueller_benutzer
from app.db import get_session
from app.models import Benutzer, Fall, Freigabe, FreigabeStatus

router = APIRouter(prefix="/freigaben", tags=["freigaben"])


class FreigabeAnsicht(BaseModel):
    """Freigabe-Karte für den Operator (FR-HITL-4): Auslöser/Payload/
    Begründung/Fakten liegen bereits im `Freigabe`-Datensatz; `ueberfaellig`
    ist abgeleitet (FR-HITL-7)."""

    id: int
    fall_id: int
    aktionstyp: str
    payload: dict
    begruendung: str
    kontext_referenzen: dict
    status: str
    idempotency_key: str
    entscheider: Optional[str]
    entscheidung_am: Optional[str]
    ablehnungsgrund: Optional[str]
    erstellt_am: str
    ueberfaellig: bool

    @staticmethod
    def aus(freigabe: Freigabe) -> "FreigabeAnsicht":
        return FreigabeAnsicht(
            id=freigabe.id,
            fall_id=freigabe.fall_id,
            aktionstyp=freigabe.aktionstyp.value,
            payload=freigabe.payload,
            begruendung=freigabe.begruendung,
            kontext_referenzen=freigabe.kontext_referenzen,
            status=freigabe.status.value,
            idempotency_key=freigabe.idempotency_key,
            entscheider=freigabe.entscheider,
            entscheidung_am=freigabe.entscheidung_am.isoformat() if freigabe.entscheidung_am else None,
            ablehnungsgrund=freigabe.ablehnungsgrund,
            erstellt_am=freigabe.erstellt_am.isoformat(),
            ueberfaellig=ist_ueberfaellig(freigabe),
        )


class FreigebenRequest(BaseModel):
    # Obergrenze wie bei EingehendeMail (OWASP Input Validation Cheat
    # Sheet) — auch für authentifizierte Endpunkte gilt: jede Eingabe
    # sollte begrenzt sein, nicht erst die öffentlich erreichbaren.
    bearbeiteter_text: Optional[str] = Field(default=None, max_length=20_000)


class AblehnenRequest(BaseModel):
    grund: str = Field(max_length=2_000)


def _get_freigabe_oder_404(session: Session, freigabe_id: int) -> Freigabe:
    freigabe = session.get(Freigabe, freigabe_id)
    if freigabe is None:
        raise HTTPException(status_code=404, detail="Freigabe nicht gefunden")
    return freigabe


def _sicherstellen_fall_nicht_geloescht(session: Session, freigabe: Freigabe) -> None:
    # Ein Soft-Delete des Falls (fall_loeschen) ließ bisher offene
    # Freigaben unangetastet — sie blieben in der Freigabe-Queue sichtbar
    # (Badge-Zahl!) und über die API weiter freigeb-/ablehnbar, obwohl der
    # zugehörige Fall dem Bearbeiter als gelöscht/verschwunden erscheint.
    fall = session.get(Fall, freigabe.fall_id)
    if fall is not None and fall.geloescht:
        raise HTTPException(
            status_code=409, detail="Der zugehörige Fall wurde gelöscht"
        )


@router.get("", response_model=list[FreigabeAnsicht])
def liste_freigaben(
    nur_offene: bool = True,
    fall_id: Optional[int] = None,
    session: Session = Depends(get_session),
) -> list[FreigabeAnsicht]:
    # Freigaben gelöschter Fälle ausblenden — dieselbe Sichtbarkeitsregel
    # wie beim Fall selbst ("verschwindet aus Board/Listen", siehe
    # fall_loeschen in app/routers/faelle.py); der Audit-Trail (Aktionen)
    # bleibt davon unberührt.
    query = select(Freigabe).join(Fall, Freigabe.fall_id == Fall.id).where(Fall.geloescht.is_(False))
    if nur_offene:
        query = query.where(Freigabe.status == FreigabeStatus.offen)
    if fall_id is not None:
        query = query.where(Freigabe.fall_id == fall_id)
    freigaben = session.exec(query.order_by(Freigabe.erstellt_am)).all()
    return [FreigabeAnsicht.aus(f) for f in freigaben]


@router.get("/{freigabe_id}", response_model=FreigabeAnsicht)
def freigabe_details(freigabe_id: int, session: Session = Depends(get_session)) -> FreigabeAnsicht:
    return FreigabeAnsicht.aus(_get_freigabe_oder_404(session, freigabe_id))


@router.post("/{freigabe_id}/freigeben", response_model=FreigabeAnsicht)
def freigabe_erteilen(
    freigabe_id: int,
    body: FreigebenRequest,
    session: Session = Depends(get_session),
    mail_adapter: MailAdapter = Depends(get_mail_adapter),
    benutzer: Benutzer = Depends(aktueller_benutzer),
) -> FreigabeAnsicht:
    """FR-HITL-5: Freigeben — optional mit bearbeitetem Text (dann
    "bearbeitet_freigegeben"). `entscheider` kommt aus der authentifizierten
    Session, nicht mehr als Klartext-Feld vom Client — sonst könnte sich
    jeder eingeloggte Nutzer im Audit-Trail als jemand anderes ausgeben."""
    freigabe = _get_freigabe_oder_404(session, freigabe_id)
    _sicherstellen_fall_nicht_geloescht(session, freigabe)
    try:
        freigabe = freigeben(session, freigabe, benutzer.email, body.bearbeiteter_text, mail_adapter)
    except FreigabeBereitsEntschieden as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return FreigabeAnsicht.aus(freigabe)


@router.post("/{freigabe_id}/ablehnen", response_model=FreigabeAnsicht)
def freigabe_ablehnen(
    freigabe_id: int,
    body: AblehnenRequest,
    session: Session = Depends(get_session),
    benutzer: Benutzer = Depends(aktueller_benutzer),
) -> FreigabeAnsicht:
    """FR-HITL-5: Ablehnen — Grund fließt in den Fall zurück. `entscheider`
    kommt wie bei freigeben() aus der Session (siehe dort)."""
    freigabe = _get_freigabe_oder_404(session, freigabe_id)
    _sicherstellen_fall_nicht_geloescht(session, freigabe)
    try:
        freigabe = ablehnen(session, freigabe, benutzer.email, body.grund)
    except FreigabeBereitsEntschieden as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return FreigabeAnsicht.aus(freigabe)
