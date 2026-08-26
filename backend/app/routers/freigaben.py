"""Freigabe-Queue-API (§10 UI-2 — die grafische Oberfläche folgt in Phase 4;
diese Endpunkte machen den propose/commit-Mechanismus bereits jetzt
bedienbar, FR-HITL-4/5)."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.agent.freigabe_service import FreigabeBereitsEntschieden, ablehnen, freigeben, ist_ueberfaellig
from app.agent.mail_adapter import MailAdapter, get_mail_adapter
from app.db import get_session
from app.models import Freigabe, FreigabeStatus

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
    entscheider: str
    bearbeiteter_text: Optional[str] = None


class AblehnenRequest(BaseModel):
    entscheider: str
    grund: str


def _get_freigabe_oder_404(session: Session, freigabe_id: int) -> Freigabe:
    freigabe = session.get(Freigabe, freigabe_id)
    if freigabe is None:
        raise HTTPException(status_code=404, detail="Freigabe nicht gefunden")
    return freigabe


@router.get("", response_model=list[FreigabeAnsicht])
def liste_freigaben(
    nur_offene: bool = True,
    fall_id: Optional[int] = None,
    session: Session = Depends(get_session),
) -> list[FreigabeAnsicht]:
    query = select(Freigabe)
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
) -> FreigabeAnsicht:
    """FR-HITL-5: Freigeben — optional mit bearbeitetem Text (dann
    "bearbeitet_freigegeben")."""
    freigabe = _get_freigabe_oder_404(session, freigabe_id)
    try:
        freigabe = freigeben(session, freigabe, body.entscheider, body.bearbeiteter_text, mail_adapter)
    except FreigabeBereitsEntschieden as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return FreigabeAnsicht.aus(freigabe)


@router.post("/{freigabe_id}/ablehnen", response_model=FreigabeAnsicht)
def freigabe_ablehnen(
    freigabe_id: int, body: AblehnenRequest, session: Session = Depends(get_session)
) -> FreigabeAnsicht:
    """FR-HITL-5: Ablehnen — Grund fließt in den Fall zurück."""
    freigabe = _get_freigabe_oder_404(session, freigabe_id)
    try:
        freigabe = ablehnen(session, freigabe, body.entscheider, body.grund)
    except FreigabeBereitsEntschieden as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return FreigabeAnsicht.aus(freigabe)
