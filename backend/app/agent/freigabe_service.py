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

from sqlmodel import Session, update

from app.agent.mail_adapter import MailAdapter, get_mail_adapter
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


def _atomar_reservieren(session: Session, freigabe: Freigabe, neuer_status: FreigabeStatus) -> None:
    """FR-HITL-8 unter Nebenläufigkeit: ein reiner Python-Check auf
    `freigabe.status == offen` vor dem Ausführen der Seiteneffekte hat ein
    Time-of-Check-to-Time-of-Use-Fenster — zwei gleichzeitige Requests
    (Doppelklick, zwei Bearbeiter) könnten beide den alten Status lesen und
    beide die Aktion ausführen. Ein bedingtes UPDATE (WHERE status='offen')
    ist dagegen atomar auf DB-Ebene: nur der Request, dessen UPDATE
    tatsächlich eine Zeile trifft, darf fortfahren."""
    ergebnis = session.exec(
        update(Freigabe)
        .where(Freigabe.id == freigabe.id, Freigabe.status == FreigabeStatus.offen)
        .values(status=neuer_status)
    )
    session.commit()
    if ergebnis.rowcount != 1:
        raise FreigabeBereitsEntschieden(
            f"Freigabe {freigabe.id} wurde bereits entschieden."
        )
    session.refresh(freigabe)


def freigeben(
    session: Session,
    freigabe: Freigabe,
    entscheider: str,
    bearbeiteter_text: str | None = None,
    mail_adapter: MailAdapter | None = None,
) -> Freigabe:
    """Freigeben, optional nach Bearbeitung des Entwurfs (FR-HITL-5). Der
    tatsächliche Versand läuft über den (austauschbaren) MailAdapter —
    §16 Phase 6, Default bleibt simuliert."""
    neuer_status = (
        FreigabeStatus.bearbeitet_freigegeben
        if bearbeiteter_text is not None
        else FreigabeStatus.freigegeben
    )
    _atomar_reservieren(session, freigabe, neuer_status)
    fall = session.get(Fall, freigabe.fall_id)

    if freigabe.aktionstyp == Aktionstyp.nachricht_senden:
        nachricht = session.get(Nachricht, freigabe.payload["nachricht_id"])
        if bearbeiteter_text is not None:
            nachricht.inhalt = bearbeiteter_text
        (mail_adapter or get_mail_adapter()).senden(nachricht)
        session.add(nachricht)
        fall.status = FallStatus.dienstleister_beauftragt
    elif freigabe.aktionstyp == Aktionstyp.dienstleister_beauftragen:
        fall.status = FallStatus.dienstleister_beauftragt
    elif freigabe.aktionstyp == Aktionstyp.rechnung_erfassen:
        fall.status = FallStatus.rechnung_erfasst

    fall.geaendert_am = datetime.utcnow()
    session.add(fall)

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
    _atomar_reservieren(session, freigabe, FreigabeStatus.abgelehnt)
    fall = session.get(Fall, freigabe.fall_id)

    if freigabe.aktionstyp == Aktionstyp.nachricht_senden:
        nachricht = session.get(Nachricht, freigabe.payload["nachricht_id"])
        nachricht.status = NachrichtStatus.abgelehnt
        session.add(nachricht)

    fall.status = FallStatus.eingeordnet
    fall.geaendert_am = datetime.utcnow()
    session.add(fall)

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
