"""Öffentliche, unauthentifizierte Kundenansicht eines Falls (§0-Wunsch:
Kunden sollen ihr Ticket ansehen können, verknüpft mit dem Mailverkehr).

Kein Login im Prototyp — Zugriff läuft über `zugriffstoken`
(192 Bit Entropie, `secrets.token_urlsafe`), NICHT über die kurze
`ticket_nummer` (nur 32 Bit — als Referenznummer für Menschen gedacht,
nicht als Zugriffsschutz; siehe app.models.fall für die Begründung nach
OWASP/W3C-Empfehlungen für Capability-URLs). Die Antwort gibt bewusst
nur einen kundengerechten Ausschnitt zurück: Klartext-Status statt
interner Statuswerte, und nur die Korrespondenz, die den Kunden selbst
betrifft — die interne Beauftragungsmail an den Dienstleister z. B.
bleibt außen vor."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.models import Fall, FallStatus, Nachricht, NachrichtRichtung
from app.rate_limit import ip_rate_limit

# Wie /auth/login und /postfach/eingang (OWASP API Security Top 10,
# API4:2023 — Unrestricted Resource Consumption): der Zugriffstoken hat
# zwar 192 Bit Entropie und ist damit nicht sinnvoll erratbar, aber ohne
# Bremse könnte dieser öffentliche, unauthentifizierte Endpunkt trotzdem
# für eine Flut an DB-Abfragen (und beim Fund eines gültigen Tokens für
# automatisiertes Auslesen) missbraucht werden. 60/5min ist großzügig für
# einen Kunden, der sein eigenes Ticket wiederholt neu lädt.
ticket_rate_limiter = ip_rate_limit(max_versuche=60, fenster_sekunden=300)

router = APIRouter(prefix="/ticket", tags=["ticket"])

_STATUS_TEXT: dict[FallStatus, str] = {
    FallStatus.neu: "Ihr Anliegen ist eingegangen und wird bearbeitet.",
    FallStatus.eingeordnet: "Ihr Anliegen wird bearbeitet.",
    FallStatus.wartet_auf_freigabe: "Ihr Anliegen wird bearbeitet.",
    FallStatus.dienstleister_beauftragt: (
        "Ein Dienstleister wurde beauftragt und meldet sich zur Terminvereinbarung."
    ),
    FallStatus.termin_bestaetigt: "Der Termin mit dem Dienstleister ist bestätigt.",
    FallStatus.arbeit_erledigt: "Die Arbeiten wurden durchgeführt.",
    FallStatus.rechnung_erfasst: "Die Arbeiten sind abgeschlossen, die Abrechnung wird geprüft.",
    FallStatus.abgeschlossen: "Ihr Anliegen ist abgeschlossen.",
    FallStatus.eskaliert: "Ihr Anliegen wird von einem Mitarbeiter persönlich bearbeitet.",
    FallStatus.abgebrochen: "Ihr Anliegen wurde storniert.",
}


class TicketNachricht(BaseModel):
    richtung: NachrichtRichtung
    betreff: str
    inhalt: str
    erstellt_am: datetime


class TicketAnsicht(BaseModel):
    ticket_nummer: str
    betreff: str
    status_text: str
    erstellt_am: datetime
    geaendert_am: datetime
    nachrichten: list[TicketNachricht]


def _kundenkorrespondenz(nachrichten: list[Nachricht]) -> list[Nachricht]:
    eingehende = [n for n in nachrichten if n.richtung == NachrichtRichtung.eingehend]
    if not eingehende:
        return []
    kunde_adresse = eingehende[0].von
    return [
        n
        for n in nachrichten
        if n.richtung == NachrichtRichtung.eingehend or n.an == kunde_adresse
    ]


@router.get("/{zugriffstoken}", response_model=TicketAnsicht, dependencies=[Depends(ticket_rate_limiter)])
def ticket_ansehen(zugriffstoken: str, session: Session = Depends(get_session)) -> TicketAnsicht:
    fall = session.exec(select(Fall).where(Fall.zugriffstoken == zugriffstoken)).first()
    if fall is None or fall.geloescht:
        raise HTTPException(status_code=404, detail="Ticket nicht gefunden")

    nachrichten = list(
        session.exec(
            select(Nachricht).where(Nachricht.fall_id == fall.id).order_by(Nachricht.erstellt_am)
        ).all()
    )

    return TicketAnsicht(
        ticket_nummer=fall.ticket_nummer,
        betreff=fall.betreff,
        status_text=_STATUS_TEXT[fall.status],
        erstellt_am=fall.erstellt_am,
        geaendert_am=fall.geaendert_am,
        nachrichten=[
            TicketNachricht(
                richtung=n.richtung, betreff=n.betreff, inhalt=n.inhalt, erstellt_am=n.erstellt_am
            )
            for n in _kundenkorrespondenz(nachrichten)
        ],
    )
