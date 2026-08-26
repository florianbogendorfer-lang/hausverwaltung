"""Outbox (§6, §10 UI-5): alle „gesendeten" Nachrichten — Nachweis, dass
nichts real rausging (Status bleibt `gesendet_simuliert`)."""

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db import get_session
from app.models import Nachricht, NachrichtRichtung, NachrichtStatus

router = APIRouter(prefix="/outbox", tags=["outbox"])


@router.get("", response_model=list[Nachricht])
def outbox_liste(session: Session = Depends(get_session)) -> list[Nachricht]:
    return list(
        session.exec(
            select(Nachricht)
            .where(
                Nachricht.richtung == NachrichtRichtung.ausgehend,
                Nachricht.status == NachrichtStatus.gesendet_simuliert,
            )
            .order_by(Nachricht.erstellt_am.desc())
        ).all()
    )
