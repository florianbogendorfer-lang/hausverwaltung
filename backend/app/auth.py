"""Passwort-Hashing + serverseitige Session (§0: Prototyp-Login, kein
externer Auth-Provider). Sitzungen leben in der DB — das Cookie trägt nur
ein zufälliges Token, sodass ein Logout durch bloßes Löschen der Zeile
sofort durchsetzbar ist, unabhängig vom Client."""

import secrets
from datetime import datetime, timedelta

import bcrypt
from fastapi import Cookie, Depends, HTTPException, Response
from sqlmodel import Session

from app.db import get_session
from app.models import Benutzer, BenutzerRolle, Sitzung

SESSION_COOKIE = "hv_session"
SITZUNGSDAUER = timedelta(days=7)


def passwort_hashen(klartext: str) -> str:
    return bcrypt.hashpw(klartext.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def passwort_pruefen(klartext: str, hash_: str) -> bool:
    return bcrypt.checkpw(klartext.encode("utf-8"), hash_.encode("utf-8"))


def sitzung_anlegen(session: Session, benutzer: Benutzer, response: Response) -> Sitzung:
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
