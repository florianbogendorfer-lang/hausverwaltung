from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.db import get_session
from app.models import Fall, Kontakt, Objekt

router = APIRouter(prefix="/objekte", tags=["objekte"])


class ObjektEingabe(BaseModel):
    # Obergrenzen nach OWASP Input Validation Cheat Sheet.
    bezeichnung: str = Field(max_length=200)
    adresse: str = Field(max_length=300)
    einheit: Optional[str] = Field(default=None, max_length=100)
    notizen: Optional[str] = Field(default=None, max_length=2_000)


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

    # Referentielle Integrität explizit prüfen statt den DB-Fehler
    # durchschlagen zu lassen: SQLite (Dev/Tests) erzwingt Foreign Keys
    # standardmäßig gar nicht (stiller Datenverlust), Postgres (Prod) würde
    # bei einer verweisenden Zeile mit einem harten IntegrityError/500
    # abbrechen — beides schlechter als eine klare 409-Fehlermeldung.
    if session.exec(select(Fall).where(Fall.objekt_id == objekt_id)).first() is not None:
        raise HTTPException(
            status_code=409, detail="Objekt kann nicht gelöscht werden — wird von Fällen referenziert"
        )
    if session.exec(select(Kontakt).where(Kontakt.objekt_id == objekt_id)).first() is not None:
        raise HTTPException(
            status_code=409,
            detail="Objekt kann nicht gelöscht werden — wird von Kontakten referenziert",
        )

    session.delete(objekt)
    session.commit()
