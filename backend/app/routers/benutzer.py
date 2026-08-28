"""Benutzerverwaltung — ausschließlich für Admins (Anlegen/Auflisten/
Löschen weiterer Konten)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlmodel import Session, select

from app.auth import (
    PASSWORT_MIN_LAENGE,
    admin_erforderlich,
    passwort_byte_laenge_pruefen,
    passwort_hashen,
)
from app.db import get_session
from app.models import Benutzer, BenutzerRolle, Sitzung
from app.validators import email_gueltig_pruefen

router = APIRouter(prefix="/benutzer", tags=["benutzer"], dependencies=[Depends(admin_erforderlich)])


class BenutzerEingabe(BaseModel):
    name: str = Field(max_length=200)
    email: str = Field(max_length=320)
    passwort: str = Field(min_length=PASSWORT_MIN_LAENGE, max_length=128)
    rolle: BenutzerRolle = BenutzerRolle.user

    _passwort_byte_laenge = field_validator("passwort")(passwort_byte_laenge_pruefen)
    _email_gueltig = field_validator("email")(email_gueltig_pruefen)


class BenutzerAusgabe(BaseModel):
    id: int
    name: str
    email: str
    rolle: BenutzerRolle


def _ausgabe(benutzer: Benutzer) -> BenutzerAusgabe:
    return BenutzerAusgabe(id=benutzer.id, name=benutzer.name, email=benutzer.email, rolle=benutzer.rolle)


@router.get("", response_model=list[BenutzerAusgabe])
def liste(session: Session = Depends(get_session)) -> list[BenutzerAusgabe]:
    # Deterministische Reihenfolge — siehe Begründung bei liste_faelle
    # (app/routers/faelle.py).
    return [_ausgabe(b) for b in session.exec(select(Benutzer).order_by(Benutzer.name)).all()]


@router.post("", response_model=BenutzerAusgabe, status_code=201)
def anlegen(eingabe: BenutzerEingabe, session: Session = Depends(get_session)) -> BenutzerAusgabe:
    # E-Mail case-insensitiv normalisieren (siehe app/auth.py::login_pruefen)
    # — sonst könnten "Admin@Example.test" und "admin@example.test" als
    # zwei verschiedene Konten angelegt werden, obwohl sie de facto
    # dieselbe Adresse sind.
    email = eingabe.email.strip().lower()
    vorhanden = session.exec(select(Benutzer).where(Benutzer.email == email)).first()
    if vorhanden is not None:
        raise HTTPException(status_code=409, detail="E-Mail bereits vergeben")
    benutzer = Benutzer(
        name=eingabe.name,
        email=email,
        passwort_hash=passwort_hashen(eingabe.passwort),
        rolle=eingabe.rolle,
    )
    session.add(benutzer)
    session.commit()
    session.refresh(benutzer)
    return _ausgabe(benutzer)


@router.delete("/{benutzer_id}", status_code=204)
def loeschen(
    benutzer_id: int,
    aktiver_benutzer: Benutzer = Depends(admin_erforderlich),
    session: Session = Depends(get_session),
) -> None:
    benutzer = session.get(Benutzer, benutzer_id)
    if benutzer is None:
        raise HTTPException(status_code=404, detail="Benutzer nicht gefunden")
    if benutzer.id == aktiver_benutzer.id:
        raise HTTPException(status_code=400, detail="Das eigene Konto kann nicht gelöscht werden")

    for sitzung in session.exec(select(Sitzung).where(Sitzung.benutzer_id == benutzer.id)).all():
        session.delete(sitzung)
    session.delete(benutzer)
    session.commit()
