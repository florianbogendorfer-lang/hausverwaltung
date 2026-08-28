"""Login/Logout/aktueller Benutzer (§0: einfaches Passwort-Login)."""

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, Field, field_validator
from sqlmodel import Session, delete

from app.audit_log import audit
from app.auth import (
    PASSWORT_MIN_LAENGE,
    aktueller_benutzer,
    login_pruefen,
    passwort_byte_laenge_pruefen,
    passwort_hashen,
    passwort_pruefen,
    sitzung_anlegen,
    sitzung_beenden,
)
from app.db import get_session
from app.models import Benutzer, BenutzerRolle, Sitzung
from app.rate_limit import ip_rate_limit
from app.validators import email_gueltig_pruefen

router = APIRouter(prefix="/auth", tags=["auth"])

# IP-Bremse zusätzlich zum Konto-Lockout in app.auth — verhindert, dass ein
# Angreifer den Lockout-Mechanismus selbst als DoS gegen fremde Konten
# missbraucht (siehe app/rate_limit.py). 20 Versuche/5 Minuten ist großzügig
# genug für legitime Nutzer (auch hinter geteilten IPs/NAT), bremst aber
# automatisiertes Durchprobieren spürbar.
#
# Als benannte Funktion (nicht anonym in Depends(...)) definiert, damit
# Tests sie gezielt per app.dependency_overrides ansprechen können — die
# gemeinsame Test-Suite teilt sich eine IP ("testclient"), ein globales
# Override hält die übrigen, funktionalen Tests unabhängig von der
# Aufrufreihenfolge deterministisch (siehe conftest.py), während
# tests/test_rate_limit.py das Override gezielt wieder entfernt.
login_rate_limiter = ip_rate_limit(max_versuche=20, fenster_sekunden=300)

# Dieselbe Begründung wie login_rate_limiter: Passwortänderung verlangt zwar
# eine gültige Session, aber das aktuelle Passwort wird per Klartext-
# Vergleich geprüft — ohne Bremse könnte ein Angreifer mit gestohlenem
# Session-Cookie das aktuelle Passwort per Brute-Force erraten.
passwort_aendern_rate_limiter = ip_rate_limit(max_versuche=10, fenster_sekunden=300)


class LoginEingabe(BaseModel):
    # Obergrenzen (OWASP Input Validation Cheat Sheet) gegen unnötig teure
    # Verarbeitung. bcrypt>=5.0 wirft für Passwörter >72 Bytes ein
    # ValueError statt (wie <5.0) stillschweigend abzuschneiden — die
    # explizite Byte-Prüfung unten wandelt das in einen sauberen
    # Validierungsfehler statt eines unbehandelten 500ers (siehe
    # app/auth.py::passwort_byte_laenge_pruefen).
    email: str = Field(max_length=320)
    passwort: str = Field(max_length=128)

    _passwort_byte_laenge = field_validator("passwort")(passwort_byte_laenge_pruefen)
    _email_gueltig = field_validator("email")(email_gueltig_pruefen)


class BenutzerAntwort(BaseModel):
    id: int
    name: str
    email: str
    rolle: BenutzerRolle


def _antwort(benutzer: Benutzer) -> BenutzerAntwort:
    return BenutzerAntwort(id=benutzer.id, name=benutzer.name, email=benutzer.email, rolle=benutzer.rolle)


@router.post("/login", response_model=BenutzerAntwort, dependencies=[Depends(login_rate_limiter)])
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


class PasswortAendernEingabe(BaseModel):
    aktuelles_passwort: str = Field(max_length=128)
    neues_passwort: str = Field(min_length=PASSWORT_MIN_LAENGE, max_length=128)

    _aktuelles_byte_laenge = field_validator("aktuelles_passwort")(passwort_byte_laenge_pruefen)
    _neues_byte_laenge = field_validator("neues_passwort")(passwort_byte_laenge_pruefen)


@router.post(
    "/passwort",
    status_code=204,
    dependencies=[Depends(passwort_aendern_rate_limiter)],
)
def passwort_aendern(
    eingabe: PasswortAendernEingabe,
    benutzer: Benutzer = Depends(aktueller_benutzer),
    session: Session = Depends(get_session),
    hv_session: str | None = Cookie(default=None),
) -> None:
    # Aktuelles Passwort erneut prüfen (OWASP: eine bestehende Session
    # allein darf keine Passwortänderung erlauben, z. B. bei einem kurz
    # unbeaufsichtigten, eingeloggten Gerät).
    if not passwort_pruefen(eingabe.aktuelles_passwort, benutzer.passwort_hash):
        audit("passwort_aendern_fehlgeschlagen", email=benutzer.email)
        raise HTTPException(status_code=401, detail="Aktuelles Passwort falsch")

    benutzer.passwort_hash = passwort_hashen(eingabe.neues_passwort)
    session.add(benutzer)

    # Alle anderen Sessions dieses Kontos beenden (OWASP Session Management:
    # eine Passwortänderung soll jeden anderen, potenziell kompromittierten
    # Zugriff sofort beenden) — nur die aktuelle Session bleibt bestehen,
    # damit der Nutzer nicht sich selbst aussperrt.
    bedingung = Sitzung.benutzer_id == benutzer.id
    if hv_session is not None:
        bedingung = bedingung & (Sitzung.token != hv_session)
    session.exec(delete(Sitzung).where(bedingung))

    session.commit()
    audit("passwort_geaendert", email=benutzer.email)
