"""Öffentliche, unauthentifizierte Kundenansicht eines Falls (§0-Wunsch:
Kunden sollen ihr Ticket ansehen können, verknüpft mit dem Mailverkehr).

Kein Login im Prototyp — Zugriff läuft ausschließlich über die unerratbare
`ticket_nummer` als Capability-Token (siehe `app.models.fall`). Die Antwort
gibt bewusst nur einen kundengerechten Ausschnitt zurück: Klartext-Status
statt interner Statuswerte, und nur die Korrespondenz, die den Kunden
selbst betrifft — die interne Beauftragungsmail an den Dienstleister z. B.
bleibt außen vor."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.models import Fall, FallStatus, Nachricht, NachrichtRichtung

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


@router.get("/{ticket_nummer}", response_model=TicketAnsicht)
def ticket_ansehen(ticket_nummer: str, session: Session = Depends(get_session)) -> TicketAnsicht:
    fall = session.exec(select(Fall).where(Fall.ticket_nummer == ticket_nummer)).first()
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
