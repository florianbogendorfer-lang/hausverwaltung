"""Öffentliches, login-freies Terminportal für Dienstleister
(`/api/dienstleister-portal/{dienstleister_zugriffstoken}`) — Gegenstück
zu tests/test_ticket.py, aber mit Schreibzugriff (Termin bestätigen,
Erledigung melden). Nutzt denselben Flow wie tests/test_freigabe_queue.py,
um einen Fall bis DIENSTLEISTER_BEAUFTRAGT zu bringen."""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.agent.model_router import ModelRouter
from app.main import app
from app.models import FallStatus
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


def _fall_bei_dienstleister_beauftragt() -> dict:
    fall = client.post("/api/postfach/eingang", json=TUERSCHLOSS_MAIL).json()
    freigabe = next(f for f in client.get("/api/freigaben").json() if f["fall_id"] == fall["id"])
    freigeben = client.post(f"/api/freigaben/{freigabe['id']}/freigeben", json={})
    assert freigeben.status_code == 200
    return client.get(f"/api/faelle/{fall['id']}").json()


def test_unbekanntes_token_gibt_404():
    response = client.get("/api/dienstleister-portal/nicht-vergeben")
    assert response.status_code == 404


def test_ansehen_zeigt_falldaten():
    fall = _fall_bei_dienstleister_beauftragt()
    response = client.get(f"/api/dienstleister-portal/{fall['dienstleister_zugriffstoken']}")
    assert response.status_code == 200
    daten = response.json()
    assert daten["ticket_nummer"] == fall["ticket_nummer"]
    assert daten["status"] == FallStatus.dienstleister_beauftragt.value
    assert daten["termin_am"] is None


def test_termin_bestaetigen_setzt_status_und_termin():
    fall = _fall_bei_dienstleister_beauftragt()
    token = fall["dienstleister_zugriffstoken"]
    termin = (datetime.utcnow() + timedelta(days=3)).isoformat()

    antwort = client.post(f"/api/dienstleister-portal/{token}/termin", json={"termin_am": termin})
    assert antwort.status_code == 200
    daten = antwort.json()
    assert daten["status"] == FallStatus.termin_bestaetigt.value
    assert daten["termin_am"] is not None

    fall_response = client.get(f"/api/faelle/{fall['id']}").json()
    assert fall_response["status"] == FallStatus.termin_bestaetigt.value

    aktionsarten = {a["aktionsart"] for a in client.get(f"/api/faelle/{fall['id']}/aktionen").json()}
    assert "fall:termin_bestaetigt" in aktionsarten


def test_termin_bestaetigen_akzeptiert_tz_aware_iso_datum():
    # Das Frontend schickt Date.toISOString() (endet auf "Z", tz-aware) —
    # ein reines .isoformat() auf einem naiven datetime (wie in den übrigen
    # Tests dieser Datei) deckt das nicht ab. Regression für einen Bug, bei
    # dem der Vergleich mit dem naiven datetime.utcnow() im Endpunkt mit
    # TypeError: can't compare offset-naive and offset-aware datetimes
    # abstürzte (siehe app/routers/dienstleister_portal.py::TerminEingabe).
    fall = _fall_bei_dienstleister_beauftragt()
    token = fall["dienstleister_zugriffstoken"]
    termin = (datetime.utcnow() + timedelta(days=3)).isoformat() + "Z"

    antwort = client.post(f"/api/dienstleister-portal/{token}/termin", json={"termin_am": termin})
    assert antwort.status_code == 200
    assert antwort.json()["status"] == FallStatus.termin_bestaetigt.value


def test_termin_in_der_vergangenheit_wird_abgelehnt():
    fall = _fall_bei_dienstleister_beauftragt()
    token = fall["dienstleister_zugriffstoken"]
    termin = (datetime.utcnow() - timedelta(days=1)).isoformat()

    antwort = client.post(f"/api/dienstleister-portal/{token}/termin", json={"termin_am": termin})
    assert antwort.status_code == 422


def test_termin_bestaetigen_ohne_beauftragung_gibt_409():
    fall = client.post("/api/postfach/eingang", json=TUERSCHLOSS_MAIL).json()
    token = fall["dienstleister_zugriffstoken"]
    termin = (datetime.utcnow() + timedelta(days=1)).isoformat()

    antwort = client.post(f"/api/dienstleister-portal/{token}/termin", json={"termin_am": termin})
    assert antwort.status_code == 409


def test_erledigt_melden_nach_terminbestaetigung():
    fall = _fall_bei_dienstleister_beauftragt()
    token = fall["dienstleister_zugriffstoken"]
    termin = (datetime.utcnow() + timedelta(days=1)).isoformat()
    client.post(f"/api/dienstleister-portal/{token}/termin", json={"termin_am": termin})

    antwort = client.post(f"/api/dienstleister-portal/{token}/erledigt")
    assert antwort.status_code == 200
    assert antwort.json()["status"] == FallStatus.arbeit_erledigt.value

    aktionsarten = {a["aktionsart"] for a in client.get(f"/api/faelle/{fall['id']}/aktionen").json()}
    assert "fall:arbeit_erledigt" in aktionsarten


def test_erledigt_melden_ohne_termin_gibt_409():
    fall = _fall_bei_dienstleister_beauftragt()
    token = fall["dienstleister_zugriffstoken"]

    antwort = client.post(f"/api/dienstleister-portal/{token}/erledigt")
    assert antwort.status_code == 409


def test_kunden_zugriffstoken_und_dienstleister_zugriffstoken_sind_unterschiedlich():
    fall = _fall_bei_dienstleister_beauftragt()
    assert fall["zugriffstoken"] != fall["dienstleister_zugriffstoken"]

    # Der Kunden-Token darf keinen Zugriff auf das Dienstleister-Portal geben.
    antwort = client.get(f"/api/dienstleister-portal/{fall['zugriffstoken']}")
    assert antwort.status_code == 404


def test_ansehen_vor_freigabe_zeigt_spezifischen_hinweis_statt_generischen_text():
    # Regression: der Link steht schon im (noch nicht freigegebenen)
    # Mailentwurf, den der Operator im Freigabe-Review sieht — klickt
    # jemand ihn zu früh, bekam er/sie bislang denselben unspezifischen
    # "wird bereits anderweitig bearbeitet"-Text wie ein längst
    # abgeschlossener oder eskalierter Fall. status_text unterscheidet
    # jetzt explizit zwischen "noch nicht freigegeben" und anderen
    # Zuständen (siehe app/routers/dienstleister_portal.py::_STATUS_TEXT).
    fall = client.post("/api/postfach/eingang", json=TUERSCHLOSS_MAIL).json()
    assert fall["status"] == FallStatus.wartet_auf_freigabe.value

    antwort = client.get(f"/api/dienstleister-portal/{fall['dienstleister_zugriffstoken']}")
    assert antwort.status_code == 200
    daten = antwort.json()
    assert daten["status"] == FallStatus.wartet_auf_freigabe.value
    assert "noch nicht freigegeben" in daten["status_text"]


def test_status_text_deckt_jeden_fallstatus_ab():
    # _STATUS_TEXT indiziert jetzt direkt (kein .get(..., default) mehr) —
    # ein künftig neu hinzugefügter FallStatus ohne Eintrag würde die
    # Portal-Ansicht mit einem KeyError abstürzen lassen. Dieser Test holt
    # sich die aktuelle Zuordnung direkt aus dem Router-Modul, damit ein
    # vergessener Eintrag hier auffällt statt erst live im Portal.
    from app.routers.dienstleister_portal import _STATUS_TEXT

    assert set(_STATUS_TEXT.keys()) == set(FallStatus)
