from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import Kontakt

router = APIRouter(prefix="/kontakte", tags=["kontakte"])


@router.get("", response_model=list[Kontakt])
def liste_kontakte(session: Session = Depends(get_session)) -> list[Kontakt]:
    return list(session.exec(select(Kontakt)).all())


@router.get("/{kontakt_id}", response_model=Kontakt)
def kontakt_details(kontakt_id: int, session: Session = Depends(get_session)) -> Kontakt:
    kontakt = session.get(Kontakt, kontakt_id)
    if kontakt is None:
        raise HTTPException(status_code=404, detail="Kontakt nicht gefunden")
    return kontakt
