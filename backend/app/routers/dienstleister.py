from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import Dienstleister, Gewerk

router = APIRouter(prefix="/dienstleister", tags=["dienstleister"])


@router.get("", response_model=list[Dienstleister])
def liste_dienstleister(
    gewerk: Optional[Gewerk] = None,
    session: Session = Depends(get_session),
) -> list[Dienstleister]:
    query = select(Dienstleister)
    if gewerk is not None:
        query = query.where(Dienstleister.gewerk == gewerk)
    return list(session.exec(query).all())


@router.get("/{dienstleister_id}", response_model=Dienstleister)
def dienstleister_details(
    dienstleister_id: int, session: Session = Depends(get_session)
) -> Dienstleister:
    dienstleister = session.get(Dienstleister, dienstleister_id)
    if dienstleister is None:
        raise HTTPException(status_code=404, detail="Dienstleister nicht gefunden")
    return dienstleister
