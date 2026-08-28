from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.db import get_session
from app.models import Fall, Kontakt, KontaktRolle, Objekt

router = APIRouter(prefix="/kontakte", tags=["kontakte"])


class KontaktEingabe(BaseModel):
    # Obergrenzen nach OWASP Input Validation Cheat Sheet.
    name: str = Field(max_length=200)
    rolle: KontaktRolle
    email: str = Field(max_length=320)
    telefon: Optional[str] = Field(default=None, max_length=50)
    objekt_id: Optional[int] = None


@router.get("", response_model=list[Kontakt])
def liste_kontakte(session: Session = Depends(get_session)) -> list[Kontakt]:
    # Deterministische Reihenfolge — siehe Begründung bei liste_faelle
    # (app/routers/faelle.py).
    return list(session.exec(select(Kontakt).order_by(Kontakt.name)).all())


@router.get("/{kontakt_id}", response_model=Kontakt)
def kontakt_details(kontakt_id: int, session: Session = Depends(get_session)) -> Kontakt:
    kontakt = session.get(Kontakt, kontakt_id)
    if kontakt is None:
        raise HTTPException(status_code=404, detail="Kontakt nicht gefunden")
    return kontakt


def _objekt_referenz_pruefen(session: Session, objekt_id: Optional[int]) -> None:
    # Ohne diese Prüfung würde SQLite (Dev/Tests) einen frei erfundenen
    # objekt_id klaglos speichern (kein FK-Enforcement), Postgres (Prod)
    # dagegen mit einem harten IntegrityError/500 statt einer
    # verständlichen 404 abbrechen.
    if objekt_id is not None and session.get(Objekt, objekt_id) is None:
        raise HTTPException(status_code=404, detail="Objekt nicht gefunden")


@router.post("", response_model=Kontakt, status_code=201)
def kontakt_anlegen(eingabe: KontaktEingabe, session: Session = Depends(get_session)) -> Kontakt:
    """UI-4 — Stammdatenpflege (§10)."""
    _objekt_referenz_pruefen(session, eingabe.objekt_id)
    kontakt = Kontakt(**eingabe.model_dump())
    session.add(kontakt)
    session.commit()
    session.refresh(kontakt)
    return kontakt


@router.put("/{kontakt_id}", response_model=Kontakt)
def kontakt_aktualisieren(
    kontakt_id: int, eingabe: KontaktEingabe, session: Session = Depends(get_session)
) -> Kontakt:
    kontakt = session.get(Kontakt, kontakt_id)
    if kontakt is None:
        raise HTTPException(status_code=404, detail="Kontakt nicht gefunden")
    _objekt_referenz_pruefen(session, eingabe.objekt_id)
    for feld, wert in eingabe.model_dump().items():
        setattr(kontakt, feld, wert)
    session.add(kontakt)
    session.commit()
    session.refresh(kontakt)
    return kontakt


@router.delete("/{kontakt_id}", status_code=204)
def kontakt_loeschen(kontakt_id: int, session: Session = Depends(get_session)) -> None:
    kontakt = session.get(Kontakt, kontakt_id)
    if kontakt is None:
        raise HTTPException(status_code=404, detail="Kontakt nicht gefunden")

    # Referentielle Integrität explizit prüfen — siehe Begründung in
    # app/routers/objekte.py::objekt_loeschen.
    if session.exec(select(Fall).where(Fall.melder_kontakt_id == kontakt_id)).first() is not None:
        raise HTTPException(
            status_code=409,
            detail="Kontakt kann nicht gelöscht werden — wird von Fällen referenziert",
        )

    session.delete(kontakt)
    session.commit()
