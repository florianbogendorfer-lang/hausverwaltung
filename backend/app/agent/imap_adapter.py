"""Echter eingehender Mailkanal über IMAP (§6) — Gegenstück zu
`app.agent.mail_adapter` (dort der ausgehende Kanal). Bewusst manuell
auslösbar (`POST /api/postfach/abrufen`, siehe app/routers/postfach.py)
statt über einen Hintergrund-Scheduler zu laufen: der Prototyp läuft
synchron in einzelnen HTTP-Requests (siehe app/db.py, NullPool-
Begründung), ein zusätzlicher Scheduler-Prozess wäre eigene Infrastruktur,
die für einen ersten Testlauf ("wie fühlt sich das in der Realität an")
nicht nötig ist — ein Klick auf "Postfach abrufen" reicht.

Nur aktiv, wenn `HV_IMAP_HOST` gesetzt ist (gleiches Muster wie
`SmtpMailAdapter`/`HV_SMTP_HOST`) — ohne Konfiguration bleibt
`/postfach/abrufen` schlicht nicht verfügbar (404), die simulierte
Einspielung über `/postfach/eingang` funktioniert unverändert weiter.

Bewusst nur `imaplib`/`email` aus der Standardbibliothek — kein Grund,
eine zusätzliche Abhängigkeit für ein simples "ungelesene Mails abholen"
einzuführen."""

import email
import imaplib
import re
from dataclasses import dataclass
from email.header import decode_header
from email.message import Message
from email.utils import parseaddr

from app.config import settings

# Passend zum bestehenden Betreff-Format ausgehender Mails
# (f"[{fall.ticket_nummer}] ...", siehe app/agent/loop.py) und zur
# Ticketnummer selbst (app.models.fall._ticket_nummer_erzeugen: "HV-" +
# 8 Hex-Zeichen).
_TICKET_MUSTER = re.compile(r"HV-[0-9A-F]{8}", re.IGNORECASE)

# Obergrenze pro Abruf (OWASP API4:2023 — Resource Consumption): ein
# einzelner Klick auf "Postfach abrufen" soll nicht Hunderte Mails in
# einem synchronen Request verarbeiten (LLM-Kosten pro neuem Fall,
# Requestdauer). Wer mehr ungelesene Mails hat, klickt einfach erneut.
_MAX_MAILS_PRO_ABRUF = 20


@dataclass
class AbgerufeneMail:
    von: str
    betreff: str
    inhalt: str
    ticket_nummer: str | None


def _dekodieren(wert: str | None) -> str:
    if not wert:
        return ""
    teile = decode_header(wert)
    ergebnis = []
    for text, kodierung in teile:
        if isinstance(text, bytes):
            ergebnis.append(text.decode(kodierung or "utf-8", errors="replace"))
        else:
            ergebnis.append(text)
    return "".join(ergebnis)


def _text_extrahieren(nachricht: Message) -> str:
    if not nachricht.is_multipart():
        payload = nachricht.get_payload(decode=True)
        if payload is None:
            return str(nachricht.get_payload() or "")
        charset = nachricht.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")

    # Nur der erste text/plain-Teil ohne Dateiname (kein Anhang) — HTML-
    # Only-Mails und Anhänge sind für den ersten Testlauf bewusst nicht
    # unterstützt (kein HTML-Parsing, keine Anhang-Ablage).
    for teil in nachricht.walk():
        if teil.get_content_type() == "text/plain" and not teil.get_filename():
            payload = teil.get_payload(decode=True)
            if payload is not None:
                charset = teil.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
    return ""


def unbearbeitete_mails_abrufen() -> list[AbgerufeneMail]:
    """Holt ungelesene Mails aus dem konfigurierten Postfach (HV_IMAP_*).
    Das IMAP-FETCH markiert die Mails dabei als gelesen (\\Seen) — ein
    erneuter Abruf holt sie nicht doppelt. Verbindungs-/Auth-Fehler werden
    NICHT abgefangen, sondern laufen zum Aufrufer durch (siehe
    app/routers/postfach.py — klare 502-Fehlermeldung statt eines
    unbehandelten 500ers)."""
    ergebnisse: list[AbgerufeneMail] = []
    with imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port) as verbindung:
        verbindung.login(settings.imap_benutzer, settings.imap_passwort)
        verbindung.select(settings.imap_ordner)
        status, daten = verbindung.search(None, "UNSEEN")
        if status != "OK" or not daten or not daten[0]:
            return ergebnisse

        for msg_id in daten[0].split()[:_MAX_MAILS_PRO_ABRUF]:
            status, msg_daten = verbindung.fetch(msg_id, "(RFC822)")
            if status != "OK" or not msg_daten or msg_daten[0] is None:
                continue
            roh = msg_daten[0][1]
            if not isinstance(roh, (bytes, bytearray)):
                continue
            nachricht = email.message_from_bytes(roh)

            _, von_adresse = parseaddr(_dekodieren(nachricht.get("From")))
            betreff = _dekodieren(nachricht.get("Subject"))
            inhalt = _text_extrahieren(nachricht).strip()
            treffer = _TICKET_MUSTER.search(betreff)

            ergebnisse.append(
                AbgerufeneMail(
                    von=von_adresse,
                    betreff=betreff[:500],
                    inhalt=inhalt[:20_000],
                    ticket_nummer=treffer.group(0).upper() if treffer else None,
                )
            )
    return ergebnisse
