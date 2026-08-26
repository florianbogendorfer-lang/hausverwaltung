"""Mail-Adapter-Schnittstelle (§6, §16 Phase 6).

Der eingehende Kanal (simuliertes Postfach) hat seine Austauschstelle
bereits in `app.routers.postfach` (siehe dessen Docstring: „Die
Schnittstelle ist so geschnitten, dass sie später durch einen echten
Mail-Adapter ersetzt werden kann"). Dieses Modul formalisiert den
ausgehenden Kanal auf dieselbe Weise: `MailAdapter` ist der Rand zwischen
Agent-Kern und der Außenwelt E-Mail, per Dependency Injection austauschbar
— wie `ModelRouter` (Anthropic-API vs. Demo-Client) und `DokumentenIndex`
(Chroma). `freigabe_service.freigeben` kennt nur das Protokoll, nicht die
konkrete Implementierung.

§2.2/§0: Im Prototyp bleibt der Versand simuliert. `SmtpMailAdapter` ist
eine echte, funktionierende Implementierung — sie wird aber nur aktiv,
wenn der Betreiber explizit `HV_SMTP_HOST` (und die zugehörigen
Zugangsdaten) konfiguriert (`get_mail_adapter()`). Ohne diese Konfiguration
bleibt `SimulierterMailAdapter` der Default: nichts geht real raus.
"""

import smtplib
from email.message import EmailMessage
from typing import Protocol

from app.config import settings
from app.models import Nachricht, NachrichtStatus


class MailAdapter(Protocol):
    def senden(self, nachricht: Nachricht) -> None:
        """Versendet eine freigegebene Nachricht und setzt
        `nachricht.status` auf den passenden Endzustand. Persistiert die
        Nachricht selbst NICHT — das bleibt Aufgabe des Aufrufers
        (freigabe_service), analog zu den anderen Tools (§9)."""
        ...


class SimulierterMailAdapter:
    """§2.2/§13: kein echter Mailversand. Die Nachricht bleibt vollständig
    in der Outbox nachvollziehbar (§10 UI-5) — Nachweis, dass nichts real
    rausging."""

    def senden(self, nachricht: Nachricht) -> None:
        nachricht.status = NachrichtStatus.gesendet_simuliert


class SmtpMailAdapter:
    """Echter Versand über SMTP (STARTTLS). Wird nur verwendet, wenn der
    Betreiber `HV_SMTP_HOST` explizit setzt (§0: bei Unklarheit die
    sichere Variante — Default bleibt simuliert)."""

    def senden(self, nachricht: Nachricht) -> None:
        nachricht_absender = settings.smtp_absender or nachricht.von
        mail = EmailMessage()
        mail["Von"] = nachricht_absender
        mail["An"] = nachricht.an
        mail["Betreff"] = nachricht.betreff
        mail.set_content(nachricht.inhalt)

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            smtp.starttls()
            if settings.smtp_benutzer and settings.smtp_passwort:
                smtp.login(settings.smtp_benutzer, settings.smtp_passwort)
            smtp.send_message(mail, from_addr=nachricht_absender, to_addrs=[nachricht.an])

        nachricht.status = NachrichtStatus.gesendet


def get_mail_adapter() -> MailAdapter:
    """Wählt den Adapter anhand der Konfiguration — reiner
    Konfigurationswechsel (NFR-5), kein Code-Umbau."""
    if settings.smtp_host:
        return SmtpMailAdapter()
    return SimulierterMailAdapter()
