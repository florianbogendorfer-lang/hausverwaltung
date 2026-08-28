"""Öffentliches, unauthentifiziertes Terminportal für Dienstleister —
Gegenstück zu app/routers/ticket.py (Kundenansicht), aber mit
Schreibzugriff: der Dienstleister bestätigt hier einen Vor-Ort-Termin und
meldet die Erledigung, statt dass der Agent das aus einer Freitext-
Mail-Antwort herauslesen müsste (fehleranfällig, nicht zuverlässig
strukturiert). Zugriff über `dienstleister_zugriffstoken` (eigenes Token,
192 Bit Entropie, getrennt vom Kunden-`zugriffstoken` — siehe
app.models.fall), NICHT über die kurze `ticket_nummer`."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlmodel import Session, select

from app.agent.tools import log_aktion
from app.db import get_session
from app.models import Akteur, Fall, FallStatus, Kontakt, Objekt
from app.rate_limit import ip_rate_limit

# Wie /ticket/{zugriffstoken}: unauthentifiziert und öffentlich erreichbar,
# daher dieselbe OWASP-API4:2023-Bremse gegen Resource-Consumption-
# Missbrauch bzw. automatisiertes Durchprobieren.
dienstleister_portal_rate_limiter = ip_rate_limit(max_versuche=60, fenster_sekunden=300)

router = APIRouter(prefix="/dienstleister-portal", tags=["dienstleister-portal"])

_STATUS_TEXT: dict[FallStatus, str] = {
    FallStatus.dienstleister_beauftragt: "Bitte bestätigen Sie einen Termin für den Vor-Ort-Besuch.",
    FallStatus.termin_bestaetigt: "Termin bestätigt. Bitte melden Sie sich, sobald die Arbeit erledigt ist.",
    FallStatus.arbeit_erledigt: "Als erledigt gemeldet — vielen Dank.",
}


class DienstleisterPortalAnsicht(BaseModel):
    ticket_nummer: str
    betreff: str
    status: FallStatus
    status_text: str
    objekt_adresse: str | None
    melder_name: str | None
    melder_telefon: str | None
    termin_am: datetime | None


class TerminEingabe(BaseModel):
    termin_am: datetime

    @field_validator("termin_am")
    @classmethod
    def _auf_naive_utc_normalisieren(cls, wert: datetime) -> datetime:
        # Der Rest der Anwendung speichert Zeitstempel konsequent als naive
        # UTC-Datetimes (datetime.utcnow(), siehe z. B. Fall.erstellt_am) —
        # ein Vergleich zwischen naiv und tz-aware wirft in Python ein
        # TypeError. Das Frontend schickt hier ein tz-aware ISO-Datum
        # (Date.toISOString(), endet auf "Z"), das vor dem Vergleich mit
        # datetime.utcnow() in dieselbe naive UTC-Form gebracht werden muss.
        if wert.tzinfo is not None:
            return wert.astimezone(timezone.utc).replace(tzinfo=None)
        return wert


def _fall_laden(session: Session, zugriffstoken: str) -> Fall:
    fall = session.exec(select(Fall).where(Fall.dienstleister_zugriffstoken == zugriffstoken)).first()
    if fall is None or fall.geloescht:
        raise HTTPException(status_code=404, detail="Portal-Link nicht gefunden")
    return fall


def _ansicht(session: Session, fall: Fall) -> DienstleisterPortalAnsicht:
    objekt = session.get(Objekt, fall.objekt_id) if fall.objekt_id else None
    kontakt = session.get(Kontakt, fall.melder_kontakt_id) if fall.melder_kontakt_id else None
    return DienstleisterPortalAnsicht(
        ticket_nummer=fall.ticket_nummer,
        betreff=fall.betreff,
        status=fall.status,
        status_text=_STATUS_TEXT.get(fall.status, "Dieser Fall wird bereits anderweitig bearbeitet."),
        objekt_adresse=f"{objekt.bezeichnung}, {objekt.adresse}" if objekt else None,
        melder_name=kontakt.name if kontakt else None,
        melder_telefon=kontakt.telefon if kontakt else None,
        termin_am=fall.termin_am,
    )


@router.get(
    "/{zugriffstoken}",
    response_model=DienstleisterPortalAnsicht,
    dependencies=[Depends(dienstleister_portal_rate_limiter)],
)
def ansehen(zugriffstoken: str, session: Session = Depends(get_session)) -> DienstleisterPortalAnsicht:
    fall = _fall_laden(session, zugriffstoken)
    return _ansicht(session, fall)


@router.post(
    "/{zugriffstoken}/termin",
    response_model=DienstleisterPortalAnsicht,
    dependencies=[Depends(dienstleister_portal_rate_limiter)],
)
def termin_bestaetigen(
    zugriffstoken: str, eingabe: TerminEingabe, session: Session = Depends(get_session)
) -> DienstleisterPortalAnsicht:
    fall = _fall_laden(session, zugriffstoken)
    if fall.status != FallStatus.dienstleister_beauftragt:
        raise HTTPException(
            status_code=409,
            detail="Für diesen Fall kann aktuell kein Termin bestätigt werden.",
        )
    # Grobe Plausibilitätsprüfung (kein sinnvoller Vor-Ort-Termin in der
    # Vergangenheit oder unrealistisch weit in der Zukunft) — verhindert
    # Fehleingaben, kein Ersatz für eine echte Kalenderprüfung.
    jetzt = datetime.utcnow()
    if eingabe.termin_am < jetzt - timedelta(minutes=5):
        raise HTTPException(status_code=422, detail="Der Termin darf nicht in der Vergangenheit liegen.")
    if eingabe.termin_am > jetzt + timedelta(days=365):
        raise HTTPException(status_code=422, detail="Der Termin liegt zu weit in der Zukunft.")

    fall.termin_am = eingabe.termin_am
    fall.status = FallStatus.termin_bestaetigt
    fall.geaendert_am = jetzt
    session.add(fall)
    session.commit()
    session.refresh(fall)
    log_aktion(
        session,
        fall.id,
        Akteur.dienstleister,
        "fall:termin_bestaetigt",
        {"termin_am": eingabe.termin_am.isoformat()},
    )
    return _ansicht(session, fall)


@router.post(
    "/{zugriffstoken}/erledigt",
    response_model=DienstleisterPortalAnsicht,
    dependencies=[Depends(dienstleister_portal_rate_limiter)],
)
def als_erledigt_melden(
    zugriffstoken: str, session: Session = Depends(get_session)
) -> DienstleisterPortalAnsicht:
    fall = _fall_laden(session, zugriffstoken)
    if fall.status != FallStatus.termin_bestaetigt:
        raise HTTPException(
            status_code=409,
            detail="Dieser Fall kann aktuell nicht als erledigt gemeldet werden.",
        )

    fall.status = FallStatus.arbeit_erledigt
    fall.geaendert_am = datetime.utcnow()
    session.add(fall)
    session.commit()
    session.refresh(fall)
    log_aktion(session, fall.id, Akteur.dienstleister, "fall:arbeit_erledigt", {})
    return _ansicht(session, fall)
