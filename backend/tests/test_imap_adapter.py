"""app.agent.imap_adapter — Parsing echter, per IMAP abgerufener Mails
(Gegenstück zu app.agent.mail_adapter für den ausgehenden Kanal). Mockt
imaplib.IMAP4_SSL komplett — kein echtes Postfach nötig, netzwerkfrei wie
der Rest der Suite."""

from email.message import EmailMessage
from unittest.mock import MagicMock, patch

from app.agent.imap_adapter import unbearbeitete_mails_abrufen


def _roh_mail(von: str, betreff: str, inhalt: str) -> bytes:
    mail = EmailMessage()
    mail["From"] = von
    mail["Subject"] = betreff
    mail["To"] = "hausverwaltung@example.test"
    mail.set_content(inhalt)
    return mail.as_bytes()


def _imap_mock(such_ids: bytes, mails: dict[bytes, bytes]) -> MagicMock:
    verbindung = MagicMock()
    verbindung.__enter__.return_value = verbindung
    verbindung.__exit__.return_value = False
    verbindung.search.return_value = ("OK", [such_ids])

    def _fetch(msg_id: bytes, _teile: str):
        if msg_id not in mails:
            return ("NO", [None])
        return ("OK", [(b"1 (RFC822 {123}", mails[msg_id])])

    verbindung.fetch.side_effect = _fetch
    return verbindung


@patch("app.agent.imap_adapter.settings")
@patch("app.agent.imap_adapter.imaplib.IMAP4_SSL")
def test_erkennt_ticketnummer_im_betreff(imap_ssl_cls, settings_mock):
    settings_mock.imap_host = "imap.example.test"
    settings_mock.imap_port = 993
    settings_mock.imap_benutzer = "betrieb@example.test"
    settings_mock.imap_passwort = "geheim"
    settings_mock.imap_ordner = "INBOX"

    roh = _roh_mail(
        "dienstleister@example.test",
        "Re: [HV-A1B2C3D4] Beauftragung: Türschloss defekt",
        "Termin passt am Montag.",
    )
    imap_ssl_cls.return_value = _imap_mock(b"1", {b"1": roh})

    ergebnisse = unbearbeitete_mails_abrufen()

    assert len(ergebnisse) == 1
    mail = ergebnisse[0]
    assert mail.von == "dienstleister@example.test"
    assert mail.ticket_nummer == "HV-A1B2C3D4"
    assert "Termin passt am Montag." in mail.inhalt


@patch("app.agent.imap_adapter.settings")
@patch("app.agent.imap_adapter.imaplib.IMAP4_SSL")
def test_ohne_ticketnummer_im_betreff_ist_ticket_nummer_none(imap_ssl_cls, settings_mock):
    settings_mock.imap_host = "imap.example.test"
    settings_mock.imap_port = 993
    settings_mock.imap_benutzer = "betrieb@example.test"
    settings_mock.imap_passwort = "geheim"
    settings_mock.imap_ordner = "INBOX"

    roh = _roh_mail("erika@example.test", "Türschloss defekt", "Bitte um Hilfe.")
    imap_ssl_cls.return_value = _imap_mock(b"1", {b"1": roh})

    ergebnisse = unbearbeitete_mails_abrufen()

    assert len(ergebnisse) == 1
    assert ergebnisse[0].ticket_nummer is None


@patch("app.agent.imap_adapter.settings")
@patch("app.agent.imap_adapter.imaplib.IMAP4_SSL")
def test_ohne_ungelesene_mails_gibt_leere_liste(imap_ssl_cls, settings_mock):
    settings_mock.imap_host = "imap.example.test"
    settings_mock.imap_port = 993
    settings_mock.imap_benutzer = "betrieb@example.test"
    settings_mock.imap_passwort = "geheim"
    settings_mock.imap_ordner = "INBOX"

    imap_ssl_cls.return_value = _imap_mock(b"", {})

    assert unbearbeitete_mails_abrufen() == []


@patch("app.agent.imap_adapter.settings")
@patch("app.agent.imap_adapter.imaplib.IMAP4_SSL")
def test_begrenzt_auf_maximal_20_mails_pro_abruf(imap_ssl_cls, settings_mock):
    settings_mock.imap_host = "imap.example.test"
    settings_mock.imap_port = 993
    settings_mock.imap_benutzer = "betrieb@example.test"
    settings_mock.imap_passwort = "geheim"
    settings_mock.imap_ordner = "INBOX"

    such_ids = b" ".join(str(i).encode() for i in range(1, 31))
    mails = {
        str(i).encode(): _roh_mail(f"absender{i}@example.test", f"Betreff {i}", f"Text {i}")
        for i in range(1, 31)
    }
    imap_ssl_cls.return_value = _imap_mock(such_ids, mails)

    ergebnisse = unbearbeitete_mails_abrufen()

    assert len(ergebnisse) == 20
