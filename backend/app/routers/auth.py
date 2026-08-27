"""Login/Logout/aktueller Benutzer (§0: einfaches Passwort-Login)."""

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlmodel import Session

from app.auth import aktueller_benutzer, login_pruefen, sitzung_anlegen, sitzung_beenden
from app.db import get_session
from app.models import Benutzer, BenutzerRolle

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginEingabe(BaseModel):
    email: str
    passwort: str


class BenutzerAntwort(BaseModel):
    id: int
    name: str
    email: str
    rolle: BenutzerRolle


def _antwort(benutzer: Benutzer) -> BenutzerAntwort:
    return BenutzerAntwort(id=benutzer.id, name=benutzer.name, email=benutzer.email, rolle=benutzer.rolle)


@router.post("/login", response_model=BenutzerAntwort)
def login(
    eingabe: LoginEingabe, response: Response, session: Session = Depends(get_session)
) -> BenutzerAntwort:
    benutzer = login_pruefen(session, eingabe.email, eingabe.passwort)
    if benutzer is None:
        # Bewusst dieselbe Meldung für "falsches Passwort", "Konto
        # existiert nicht" und "Konto vorübergehend gesperrt" — kein
        # Informationsleck über den Grund (OWASP Authentication Cheat
        # Sheet, User-Enumeration-Vermeidung).
        raise HTTPException(status_code=401, detail="E-Mail oder Passwort falsch")
    sitzung_anlegen(session, benutzer, response)
    return _antwort(benutzer)


@router.post("/logout")
def logout(
    response: Response,
    session: Session = Depends(get_session),
    hv_session: str | None = Cookie(default=None),
) -> dict[str, str]:
    sitzung_beenden(session, hv_session, response)
    return {"status": "ok"}


@router.get("/me", response_model=BenutzerAntwort)
def me(benutzer: Benutzer = Depends(aktueller_benutzer)) -> BenutzerAntwort:
    return _antwort(benutzer)
