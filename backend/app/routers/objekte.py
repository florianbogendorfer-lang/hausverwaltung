from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.models import Objekt

router = APIRouter(prefix="/objekte", tags=["objekte"])


class ObjektEingabe(BaseModel):
    bezeichnung: str
    adresse: str
    einheit: Optional[str] = None
    notizen: Optional[str] = None


@router.get("", response_model=list[Objekt])
def liste_objekte(session: Session = Depends(get_session)) -> list[Objekt]:
    return list(session.exec(select(Objekt)).all())


@router.get("/{objekt_id}", response_model=Objekt)
def objekt_details(objekt_id: int, session: Session = Depends(get_session)) -> Objekt:
    objekt = session.get(Objekt, objekt_id)
    if objekt is None:
        raise HTTPException(status_code=404, detail="Objekt nicht gefunden")
    return objekt


@router.post("", response_model=Objekt, status_code=201)
def objekt_anlegen(eingabe: ObjektEingabe, session: Session = Depends(get_session)) -> Objekt:
    """UI-4 — Stammdatenpflege (§10)."""
    objekt = Objekt(**eingabe.model_dump())
    session.add(objekt)
    session.commit()
    session.refresh(objekt)
    return objekt


@router.put("/{objekt_id}", response_model=Objekt)
def objekt_aktualisieren(
    objekt_id: int, eingabe: ObjektEingabe, session: Session = Depends(get_session)
) -> Objekt:
    objekt = session.get(Objekt, objekt_id)
    if objekt is None:
        raise HTTPException(status_code=404, detail="Objekt nicht gefunden")
    for feld, wert in eingabe.model_dump().items():
        setattr(objekt, feld, wert)
    session.add(objekt)
    session.commit()
    session.refresh(objekt)
    return objekt


@router.delete("/{objekt_id}", status_code=204)
def objekt_loeschen(objekt_id: int, session: Session = Depends(get_session)) -> None:
    objekt = session.get(Objekt, objekt_id)
    if objekt is None:
        raise HTTPException(status_code=404, detail="Objekt nicht gefunden")
    session.delete(objekt)
    session.commit()
