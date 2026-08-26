from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import Objekt

router = APIRouter(prefix="/objekte", tags=["objekte"])


@router.get("", response_model=list[Objekt])
def liste_objekte(session: Session = Depends(get_session)) -> list[Objekt]:
    return list(session.exec(select(Objekt)).all())


@router.get("/{objekt_id}", response_model=Objekt)
def objekt_details(objekt_id: int, session: Session = Depends(get_session)) -> Objekt:
    objekt = session.get(Objekt, objekt_id)
    if objekt is None:
        raise HTTPException(status_code=404, detail="Objekt nicht gefunden")
    return objekt
