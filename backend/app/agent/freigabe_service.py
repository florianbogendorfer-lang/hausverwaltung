"""Freigabe-Ausführung (commit) — Kern des HITL-Mechanismus (§5).

FR-HITL-1: Erst hier, beim Commit einer Freigabe, wird die vorgeschlagene
Aktion tatsächlich ausgeführt (propose/commit-Trennung).
FR-HITL-5: drei Entscheidungen — Freigeben, Bearbeiten (dann Freigeben,
über `bearbeiteter_text`), Ablehnen (mit Grund, der in den Fall
zurückfließt).
FR-HITL-8: Eine bereits entschiedene Freigabe kann nicht erneut committet
oder abgelehnt werden — Doppelausführung ist ausgeschlossen.
"""

from datetime import datetime

from sqlmodel import Session

from app.agent.tools import log_aktion
from app.config import settings
from app.models import (
    Akteur,
    Aktionstyp,
    Fall,
    FallStatus,
    Freigabe,
    FreigabeStatus,
    Nachricht,
    NachrichtStatus,
)


class FreigabeBereitsEntschieden(Exception):
    """FR-HITL-8: Idempotenz-Schutz — verhindert doppeltes Committen/
    Ablehnen derselben Freigabe."""


def ist_ueberfaellig(freigabe: Freigabe) -> bool:
    """FR-HITL-7: markiert offene Freigaben, die die konfigurierte Frist
    überschritten haben (im Prototyp keine Auto-Ausführung — nur Anzeige)."""
    if freigabe.status != FreigabeStatus.offen:
        return False
    alter = datetime.utcnow() - freigabe.erstellt_am
    return alter.total_seconds() > settings.freigabe_timeout_stunden * 3600


def _sicherstellen_offen(freigabe: Freigabe) -> None:
    if freigabe.status != FreigabeStatus.offen:
        raise FreigabeBereitsEntschieden(
            f"Freigabe {freigabe.id} wurde bereits entschieden (Status: {freigabe.status.value})."
        )


def freigeben(
    session: Session, freigabe: Freigabe, entscheider: str, bearbeiteter_text: str | None = None
) -> Freigabe:
    """Freigeben, optional nach Bearbeitung des Entwurfs (FR-HITL-5)."""
    _sicherstellen_offen(freigabe)
    fall = session.get(Fall, freigabe.fall_id)

    if freigabe.aktionstyp == Aktionstyp.nachricht_senden:
        nachricht = session.get(Nachricht, freigabe.payload["nachricht_id"])
        if bearbeiteter_text is not None:
            nachricht.inhalt = bearbeiteter_text
        nachricht.status = NachrichtStatus.gesendet_simuliert
        session.add(nachricht)
        fall.status = FallStatus.dienstleister_beauftragt
    elif freigabe.aktionstyp == Aktionstyp.dienstleister_beauftragen:
        fall.status = FallStatus.dienstleister_beauftragt
    elif freigabe.aktionstyp == Aktionstyp.rechnung_erfassen:
        fall.status = FallStatus.rechnung_erfasst

    fall.geaendert_am = datetime.utcnow()
    session.add(fall)

    freigabe.status = (
        FreigabeStatus.bearbeitet_freigegeben
        if bearbeiteter_text is not None
        else FreigabeStatus.freigegeben
    )
    freigabe.entscheider = entscheider
    freigabe.entscheidung_am = datetime.utcnow()
    session.add(freigabe)
    session.commit()
    session.refresh(freigabe)

    log_aktion(
        session,
        freigabe.fall_id,
        Akteur.operator,
        "freigabe:erteilt",
        {
            "freigabe_id": freigabe.id,
            "aktionstyp": freigabe.aktionstyp.value,
            "bearbeitet": bearbeiteter_text is not None,
            "entscheider": entscheider,
        },
        freigabe_id=freigabe.id,
    )
    return freigabe


def ablehnen(session: Session, freigabe: Freigabe, entscheider: str, grund: str) -> Freigabe:
    """Ablehnen — der Grund fließt als Notiz zurück in den Fall (FR-HITL-5)."""
    _sicherstellen_offen(freigabe)
    fall = session.get(Fall, freigabe.fall_id)

    if freigabe.aktionstyp == Aktionstyp.nachricht_senden:
        nachricht = session.get(Nachricht, freigabe.payload["nachricht_id"])
        nachricht.status = NachrichtStatus.abgelehnt
        session.add(nachricht)

    fall.status = FallStatus.eingeordnet
    fall.geaendert_am = datetime.utcnow()
    session.add(fall)

    freigabe.status = FreigabeStatus.abgelehnt
    freigabe.entscheider = entscheider
    freigabe.entscheidung_am = datetime.utcnow()
    freigabe.ablehnungsgrund = grund
    session.add(freigabe)
    session.commit()
    session.refresh(freigabe)

    log_aktion(
        session,
        freigabe.fall_id,
        Akteur.operator,
        "freigabe:abgelehnt",
        {"freigabe_id": freigabe.id, "aktionstyp": freigabe.aktionstyp.value, "grund": grund},
        freigabe_id=freigabe.id,
    )
    return freigabe
