from unittest.mock import MagicMock, patch

from app.agent.mail_adapter import SimulierterMailAdapter, SmtpMailAdapter, get_mail_adapter
from app.config import settings
from app.models import Nachricht, NachrichtRichtung, NachrichtStatus


def _nachricht() -> Nachricht:
    return Nachricht(
        fall_id=1,
        richtung=NachrichtRichtung.ausgehend,
        von="hausverwaltung@example.test",
        an="dienstleister@example.test",
        betreff="Beauftragung",
        inhalt="Bitte um Terminvereinbarung.",
        status=NachrichtStatus.entwurf,
    )


def test_get_mail_adapter_ist_ohne_smtp_konfiguration_simuliert():
    assert settings.smtp_host is None
    assert isinstance(get_mail_adapter(), SimulierterMailAdapter)


def test_simulierter_adapter_setzt_status_ohne_netzwerk():
    nachricht = _nachricht()
    SimulierterMailAdapter().senden(nachricht)
    assert nachricht.status == NachrichtStatus.gesendet_simuliert


def test_smtp_adapter_sendet_ueber_smtplib_und_setzt_status():
    nachricht = _nachricht()
    smtp_instanz = MagicMock()
    smtp_instanz.__enter__.return_value = smtp_instanz

    with (
        patch("app.agent.mail_adapter.smtplib.SMTP", return_value=smtp_instanz) as smtp_klasse,
        patch.object(settings, "smtp_host", "smtp.example.test"),
        patch.object(settings, "smtp_benutzer", "user"),
        patch.object(settings, "smtp_passwort", "pass"),
    ):
        SmtpMailAdapter().senden(nachricht)

        smtp_klasse.assert_called_once_with("smtp.example.test", settings.smtp_port, timeout=10)
        smtp_instanz.starttls.assert_called_once()
        smtp_instanz.login.assert_called_once_with("user", "pass")
        smtp_instanz.send_message.assert_called_once()

    assert nachricht.status == NachrichtStatus.gesendet


def test_get_mail_adapter_waehlt_smtp_wenn_konfiguriert():
    with patch.object(settings, "smtp_host", "smtp.example.test"):
        assert isinstance(get_mail_adapter(), SmtpMailAdapter)
