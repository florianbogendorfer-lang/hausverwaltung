"""Lesende Endpunkte für Fälle inkl. Trace/Audit (§10 UI-1/UI-3 — die
grafische Oberfläche folgt erst in Phase 4; diese Endpunkte machen den
Agent-Lauf bereits jetzt über die API nachvollziehbar, §11)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import Aktion, Fall, Nachricht, Trace

router = APIRouter(prefix="/faelle", tags=["faelle"])


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


@router.get("/{fall_id}/nachrichten", response_model=list[Nachricht])
def fall_nachrichten(fall_id: int, session: Session = Depends(get_session)) -> list[Nachricht]:
    if session.get(Fall, fall_id) is None:
        raise HTTPException(status_code=404, detail="Fall nicht gefunden")
    return list(
        session.exec(
            select(Nachricht).where(Nachricht.fall_id == fall_id).order_by(Nachricht.erstellt_am)
        ).all()
    )
