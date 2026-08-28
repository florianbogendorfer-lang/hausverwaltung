"""Passwort-Hashing + serverseitige Session (§0: Prototyp-Login, kein
externer Auth-Provider). Sitzungen leben in der DB — das Cookie trägt nur
ein zufälliges Token, sodass ein Logout durch bloßes Löschen der Zeile
sofort durchsetzbar ist, unabhängig vom Client.

Login-Härtung nach OWASP Authentication Cheat Sheet:
- Timing-Angriff/User-Enumeration: `login_pruefen` führt IMMER einen
  bcrypt-Vergleich aus (gegen einen fixen Dummy-Hash, falls die E-Mail
  nicht existiert), damit die Antwortzeit nicht verrät, ob ein Konto
  existiert.
- Brute-Force: Fehlversuche werden je Konto gezählt (nicht nach IP —
  das ließe sich trivial umgehen); ab einer Schwelle greift eine
  temporäre, exponentiell wachsende Sperre statt einer permanenten
  Sperre (die selbst zum Denial-of-Service-Vektor würde).
- Einheitliche Fehlermeldung für „falsches Passwort", „Konto existiert
  nicht" und „Konto gesperrt" (kein Informationsleck über den Grund).
"""

import secrets
from datetime import datetime, timedelta

import bcrypt
from fastapi import Cookie, Depends, HTTPException, Response
from sqlmodel import Session, delete, select

from app.config import settings
from app.db import get_session
from app.models import Benutzer, BenutzerRolle, Sitzung

SESSION_COOKIE = "hv_session"
SITZUNGSDAUER = timedelta(days=7)

FEHLVERSUCHE_SCHWELLE = 5
MAX_SPERRDAUER = timedelta(hours=1)

# Fixer, gültiger bcrypt-Hash für den Vergleich bei unbekannter E-Mail —
# ein Klartext, den niemand als echtes Passwort verwendet. Einmal beim
# Modul-Import berechnet (nicht pro Request), damit nur der eigentliche
# `checkpw`-Vergleich (die zeitkritische Operation) pro Login-Versuch
# läuft.
_DUMMY_HASH = bcrypt.hashpw(b"hv-dummy-passwort-fuer-timing-schutz", bcrypt.gensalt()).decode(
    "utf-8"
)


def passwort_hashen(klartext: str) -> str:
    return bcrypt.hashpw(klartext.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def passwort_pruefen(klartext: str, hash_: str) -> bool:
    return bcrypt.checkpw(klartext.encode("utf-8"), hash_.encode("utf-8"))


def login_pruefen(session: Session, email: str, passwort: str) -> Benutzer | None:
    """Prüft Login-Daten inkl. Sperre, konstante Laufzeit unabhängig davon,
    ob das Konto existiert. Gibt bei Erfolg den Benutzer zurück, sonst
    None — der Aufrufer meldet in jedem Fall dieselbe generische
    Fehlermeldung (kein User-Enumeration-Leck)."""
    # E-Mail-Adressen case-insensitiv behandeln (Domain-Teil ist es laut
    # RFC 5321 immer, der Local-Part wird in der Praxis von praktisch
    # jedem Provider ebenfalls case-insensitiv behandelt) — sonst könnte
    # sich ein Nutzer mit anderer Groß-/Kleinschreibung fälschlich
    # "ausgesperrt" fühlen. Benutzer.anlegen speichert email bereits
    # normalisiert (siehe app/routers/benutzer.py), daher reicht hier ein
    # Normalisieren der Eingabe für den Vergleich.
    benutzer = session.exec(select(Benutzer).where(Benutzer.email == email.strip().lower())).first()
    ziel_hash = benutzer.passwort_hash if benutzer is not None else _DUMMY_HASH
    # IMMER ausführen, auch wenn `benutzer` None ist oder gesperrt —
    # sonst wäre die Antwortzeit selbst das Leck.
    passwort_korrekt = passwort_pruefen(passwort, ziel_hash)

    if benutzer is None:
        return None

    gesperrt = benutzer.gesperrt_bis is not None and benutzer.gesperrt_bis > datetime.utcnow()
    if gesperrt or not passwort_korrekt:
        _fehlversuch_vermerken(session, benutzer)
        return None

    if benutzer.fehlversuche > 0 or benutzer.gesperrt_bis is not None:
        benutzer.fehlversuche = 0
        benutzer.gesperrt_bis = None
        session.add(benutzer)
        session.commit()
    return benutzer


def _fehlversuch_vermerken(session: Session, benutzer: Benutzer) -> None:
    benutzer.fehlversuche += 1
    if benutzer.fehlversuche >= FEHLVERSUCHE_SCHWELLE:
        exponent = benutzer.fehlversuche - FEHLVERSUCHE_SCHWELLE
        sperrdauer = min(timedelta(minutes=2**exponent), MAX_SPERRDAUER)
        benutzer.gesperrt_bis = datetime.utcnow() + sperrdauer
    session.add(benutzer)
    session.commit()


def sitzung_anlegen(session: Session, benutzer: Benutzer, response: Response) -> Sitzung:
    # Kein Cron/Hintergrundjob nötig — ohne irgendein Aufräumen würde die
    # sitzungen-Tabelle in einem lang laufenden Deployment unbegrenzt
    # wachsen (jede Session bleibt nach Ablauf als Karteileiche stehen).
    # Ein Login ist ein günstiger, natürlicher Zeitpunkt, um abgelaufene
    # Zeilen opportunistisch mit wegzuräumen.
    session.exec(delete(Sitzung).where(Sitzung.laeuft_ab_am < datetime.utcnow()))

    token = secrets.token_urlsafe(32)
    sitzung = Sitzung(
        token=token, benutzer_id=benutzer.id, laeuft_ab_am=datetime.utcnow() + SITZUNGSDAUER
    )
    session.add(sitzung)
    session.commit()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(SITZUNGSDAUER.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    return sitzung


def sitzung_beenden(session: Session, token: str | None, response: Response) -> None:
    if token:
        sitzung = session.get(Sitzung, token)
        if sitzung is not None:
            session.delete(sitzung)
            session.commit()
    response.delete_cookie(SESSION_COOKIE)


def aktueller_benutzer(
    hv_session: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
) -> Benutzer:
    if hv_session is None:
        raise HTTPException(status_code=401, detail="Nicht angemeldet")
    sitzung = session.get(Sitzung, hv_session)
    if sitzung is None or sitzung.laeuft_ab_am < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Sitzung abgelaufen oder ungültig")
    benutzer = session.get(Benutzer, sitzung.benutzer_id)
    if benutzer is None:
        raise HTTPException(status_code=401, detail="Nicht angemeldet")
    return benutzer


def admin_erforderlich(benutzer: Benutzer = Depends(aktueller_benutzer)) -> Benutzer:
    if benutzer.rolle != BenutzerRolle.admin:
        raise HTTPException(status_code=403, detail="Diese Aktion ist Admins vorbehalten")
    return benutzer
