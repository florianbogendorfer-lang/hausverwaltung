from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import Dokument

router = APIRouter(prefix="/dokumente", tags=["dokumente"])


@router.get("", response_model=list[Dokument])
def liste_dokumente(session: Session = Depends(get_session)) -> list[Dokument]:
    return list(session.exec(select(Dokument)).all())


@router.get("/{dokument_id}", response_model=Dokument)
def dokument_details(dokument_id: int, session: Session = Depends(get_session)) -> Dokument:
    dokument = session.get(Dokument, dokument_id)
    if dokument is None:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden")
    return dokument
