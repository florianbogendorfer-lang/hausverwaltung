from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlmodel import Session, select

from app.db import get_session
from app.models import Dienstleister, Fall, Gewerk
from app.validators import email_gueltig_pruefen

router = APIRouter(prefix="/dienstleister", tags=["dienstleister"])


class DienstleisterEingabe(BaseModel):
    # Obergrenzen nach OWASP Input Validation Cheat Sheet.
    name: str = Field(max_length=200)
    gewerk: Gewerk
    email: str = Field(max_length=320)
    telefon: Optional[str] = Field(default=None, max_length=50)
    konditionen: Optional[str] = Field(default=None, max_length=2_000)
    aktiv: bool = True

    _email_gueltig = field_validator("email")(email_gueltig_pruefen)


@router.get("", response_model=list[Dienstleister])
def liste_dienstleister(
    gewerk: Optional[Gewerk] = None,
    session: Session = Depends(get_session),
) -> list[Dienstleister]:
    query = select(Dienstleister)
    if gewerk is not None:
        query = query.where(Dienstleister.gewerk == gewerk)
    # Deterministische Reihenfolge — siehe Begründung bei liste_faelle
    # (app/routers/faelle.py).
    return list(session.exec(query.order_by(Dienstleister.name)).all())


@router.get("/{dienstleister_id}", response_model=Dienstleister)
def dienstleister_details(
    dienstleister_id: int, session: Session = Depends(get_session)
) -> Dienstleister:
    dienstleister = session.get(Dienstleister, dienstleister_id)
    if dienstleister is None:
        raise HTTPException(status_code=404, detail="Dienstleister nicht gefunden")
    return dienstleister


@router.post("", response_model=Dienstleister, status_code=201)
def dienstleister_anlegen(
    eingabe: DienstleisterEingabe, session: Session = Depends(get_session)
) -> Dienstleister:
    """UI-4 — Stammdatenpflege (§10)."""
    dienstleister = Dienstleister(**eingabe.model_dump())
    session.add(dienstleister)
    session.commit()
    session.refresh(dienstleister)
    return dienstleister


@router.put("/{dienstleister_id}", response_model=Dienstleister)
def dienstleister_aktualisieren(
    dienstleister_id: int, eingabe: DienstleisterEingabe, session: Session = Depends(get_session)
) -> Dienstleister:
    dienstleister = session.get(Dienstleister, dienstleister_id)
    if dienstleister is None:
        raise HTTPException(status_code=404, detail="Dienstleister nicht gefunden")
    for feld, wert in eingabe.model_dump().items():
        setattr(dienstleister, feld, wert)
    session.add(dienstleister)
    session.commit()
    session.refresh(dienstleister)
    return dienstleister


@router.delete("/{dienstleister_id}", status_code=204)
def dienstleister_loeschen(dienstleister_id: int, session: Session = Depends(get_session)) -> None:
    dienstleister = session.get(Dienstleister, dienstleister_id)
    if dienstleister is None:
        raise HTTPException(status_code=404, detail="Dienstleister nicht gefunden")

    # Referentielle Integrität explizit prüfen — siehe Begründung in
    # app/routers/objekte.py::objekt_loeschen.
    if session.exec(select(Fall).where(Fall.dienstleister_id == dienstleister_id)).first() is not None:
        raise HTTPException(
            status_code=409,
            detail="Dienstleister kann nicht gelöscht werden — wird von Fällen referenziert",
        )

    session.delete(dienstleister)
    session.commit()
