"""POST /api/postfach/abrufen — echter IMAP-Abruf (Gegenstück zur
simulierten Einspielung, tests/test_agent_loop.py). Mockt
unbearbeitete_mails_abrufen komplett (das IMAP-Parsing selbst ist in
tests/test_imap_adapter.py abgedeckt) — hier geht es nur um die Routing-
Logik: neuer Fall vs. bestehenden Fall per Ticketnummer erweitern."""

import imaplib

import pytest
from fastapi.testclient import TestClient

from app.agent.imap_adapter import AbgerufeneMail
from app.agent.model_router import ModelRouter
from app.config import settings
from app.main import app
from app.models import FallStatus
from app.routers import postfach as postfach_module
from app.routers.postfach import get_model_router
from tests.fakes import FakeLLMClient

fake_client = FakeLLMClient()
app.dependency_overrides[get_model_router] = lambda: ModelRouter(client=fake_client)

client = TestClient(app)

TUERSCHLOSS_MAIL = {
    "von": "erika.musterfrau@example.test",
    "betreff": "Türschloss defekt",
    "inhalt": (
        "Guten Tag, das Türschloss meiner Wohnung in der Musterstraße 5 ist "
        "seit heute Morgen defekt. Erika Musterfrau"
    ),
}


@pytest.fixture(autouse=True)
def _imap_host_gesetzt(monkeypatch):
    """/postfach/abrufen ist ohne HV_IMAP_HOST nicht verfügbar (404) —
    für die meisten Tests hier soll es aber verfügbar sein."""
    monkeypatch.setattr(settings, "imap_host", "imap.example.test")
    monkeypatch.setattr(settings, "imap_benutzer", "betrieb@example.test")
    monkeypatch.setattr(settings, "imap_passwort", "geheim")


def test_ohne_imap_host_gibt_404(monkeypatch):
    monkeypatch.setattr(settings, "imap_host", None)
    antwort = client.post("/api/postfach/abrufen")
    assert antwort.status_code == 404


def test_mail_ohne_ticketnummer_erzeugt_neuen_fall(monkeypatch):
    monkeypatch.setattr(
        postfach_module,
        "unbearbeitete_mails_abrufen",
        lambda: [
            AbgerufeneMail(
                von="erika.musterfrau@example.test",
                betreff="Türschloss defekt",
                inhalt="Guten Tag, das Türschloss meiner Wohnung in der Musterstraße 5 ist defekt.",
                ticket_nummer=None,
            )
        ],
    )

    antwort = client.post("/api/postfach/abrufen")
    assert antwort.status_code == 200
    ergebnis = antwort.json()
    assert ergebnis == {"neue_faelle": 1, "zugeordnete_antworten": 0, "uebersprungene_mails": 0}

    faelle = client.get("/api/faelle").json()
    neuester = max(faelle, key=lambda f: f["id"])
    assert neuester["gewerk"] == "schlosser"


def test_mail_mit_bekannter_ticketnummer_wird_bestehendem_fall_angehaengt(monkeypatch):
    fall = client.post("/api/postfach/eingang", json=TUERSCHLOSS_MAIL).json()
    ticket_nummer = fall["ticket_nummer"]

    monkeypatch.setattr(
        postfach_module,
        "unbearbeitete_mails_abrufen",
        lambda: [
            AbgerufeneMail(
                von="auftraege@schlosserei-sicherheit.example.test",
                betreff=f"Re: [{ticket_nummer}] Beauftragung: Türschloss defekt",
                inhalt="Termin passt am Montag um 9 Uhr.",
                ticket_nummer=ticket_nummer,
            )
        ],
    )

    antwort = client.post("/api/postfach/abrufen")
    assert antwort.status_code == 200
    ergebnis = antwort.json()
    assert ergebnis == {"neue_faelle": 0, "zugeordnete_antworten": 1, "uebersprungene_mails": 0}

    nachrichten = client.get(f"/api/faelle/{fall['id']}/nachrichten").json()
    neue_eingehende = [n for n in nachrichten if n["inhalt"] == "Termin passt am Montag um 9 Uhr."]
    assert len(neue_eingehende) == 1
    assert neue_eingehende[0]["richtung"] == "eingehend"

    aktionsarten = {a["aktionsart"] for a in client.get(f"/api/faelle/{fall['id']}/aktionen").json()}
    assert "postfach:antwort_empfangen" in aktionsarten

    # Der Fall-Status ändert sich durch eine reine Antwort nicht automatisch
    # — der Bearbeiter entscheidet selbst über das weitere Vorgehen (FR-HITL-3).
    fall_danach = client.get(f"/api/faelle/{fall['id']}").json()
    assert fall_danach["status"] == fall["status"]
    assert fall_danach["status"] != FallStatus.abgeschlossen.value


def test_mail_mit_unbekannter_ticketnummer_erzeugt_stattdessen_neuen_fall(monkeypatch):
    monkeypatch.setattr(
        postfach_module,
        "unbearbeitete_mails_abrufen",
        lambda: [
            AbgerufeneMail(
                von="erika.musterfrau@example.test",
                betreff="Re: [HV-DEADBEEF] Türschloss defekt",
                inhalt="Das Türschloss in der Musterstraße 5 ist immer noch defekt.",
                ticket_nummer="HV-DEADBEEF",
            )
        ],
    )

    antwort = client.post("/api/postfach/abrufen")
    assert antwort.status_code == 200
    assert antwort.json() == {"neue_faelle": 1, "zugeordnete_antworten": 0, "uebersprungene_mails": 0}


def test_mail_mit_ungueltiger_absenderadresse_wird_uebersprungen(monkeypatch):
    monkeypatch.setattr(
        postfach_module,
        "unbearbeitete_mails_abrufen",
        lambda: [
            AbgerufeneMail(von="", betreff="Automatische Benachrichtigung", inhalt="...", ticket_nummer=None)
        ],
    )

    antwort = client.post("/api/postfach/abrufen")
    assert antwort.status_code == 200
    assert antwort.json() == {"neue_faelle": 0, "zugeordnete_antworten": 0, "uebersprungene_mails": 1}


def test_verbindungsfehler_gibt_502(monkeypatch):
    def _fehlschlagen():
        raise imaplib.IMAP4.error("LOGIN failed")

    monkeypatch.setattr(postfach_module, "unbearbeitete_mails_abrufen", _fehlschlagen)

    antwort = client.post("/api/postfach/abrufen")
    assert antwort.status_code == 502
