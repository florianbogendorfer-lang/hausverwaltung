from fastapi.testclient import TestClient

from app.agent.model_router import ModelRouter
from app.main import app
from app.models import FallStatus, NachrichtStatus
from app.routers.postfach import get_model_router
from tests.fakes import FakeLLMClient

fake_client = FakeLLMClient()


def _get_model_router_override() -> ModelRouter:
    return ModelRouter(client=fake_client)


app.dependency_overrides[get_model_router] = _get_model_router_override

client = TestClient(app)

TUERSCHLOSS_MAIL = {
    "von": "erika.musterfrau@example.test",
    "betreff": "Türschloss defekt",
    "inhalt": (
        "Guten Tag, das Türschloss meiner Wohnung in der Musterstraße 5 ist "
        "seit heute Morgen defekt. Erika Musterfrau"
    ),
}


def _fall_mit_offener_freigabe_erzeugen():
    fall = client.post("/api/postfach/eingang", json=TUERSCHLOSS_MAIL).json()
    freigabe = next(
        f for f in client.get("/api/freigaben").json() if f["fall_id"] == fall["id"]
    )
    return fall, freigabe


def test_freigeben_sendet_simuliert_und_beauftragt_dienstleister():
    fall, freigabe = _fall_mit_offener_freigabe_erzeugen()

    response = client.post(
        f"/api/freigaben/{freigabe['id']}/freigeben",
        json={"entscheider": "operator@example.test"},
    )
    assert response.status_code == 200
    entschieden = response.json()
    assert entschieden["status"] == "freigegeben"
    assert entschieden["entscheider"] == "operator@example.test"

    fall_response = client.get(f"/api/faelle/{fall['id']}").json()
    assert fall_response["status"] == FallStatus.dienstleister_beauftragt.value

    nachrichten = client.get(f"/api/faelle/{fall['id']}/nachrichten").json()
    ausgehende = next(n for n in nachrichten if n["richtung"] == "ausgehend")
    assert ausgehende["status"] == NachrichtStatus.gesendet_simuliert.value

    aktionsarten = {
        a["aktionsart"] for a in client.get(f"/api/faelle/{fall['id']}/aktionen").json()
    }
    assert "freigabe:erteilt" in aktionsarten


def test_freigabe_kann_nicht_doppelt_committet_werden():
    _, freigabe = _fall_mit_offener_freigabe_erzeugen()

    erster = client.post(
        f"/api/freigaben/{freigabe['id']}/freigeben", json={"entscheider": "operator@example.test"}
    )
    assert erster.status_code == 200

    zweiter = client.post(
        f"/api/freigaben/{freigabe['id']}/freigeben", json={"entscheider": "operator@example.test"}
    )
    assert zweiter.status_code == 409


def test_bearbeiten_und_freigeben_uebernimmt_geaenderten_text():
    fall, freigabe = _fall_mit_offener_freigabe_erzeugen()

    neuer_text = "Bitte kontaktieren Sie den Mieter direkt zur Terminvereinbarung."
    response = client.post(
        f"/api/freigaben/{freigabe['id']}/freigeben",
        json={"entscheider": "operator@example.test", "bearbeiteter_text": neuer_text},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "bearbeitet_freigegeben"

    nachrichten = client.get(f"/api/faelle/{fall['id']}/nachrichten").json()
    ausgehende = next(n for n in nachrichten if n["richtung"] == "ausgehend")
    assert ausgehende["inhalt"] == neuer_text
    assert ausgehende["status"] == NachrichtStatus.gesendet_simuliert.value


def test_ablehnen_setzt_nachricht_und_fall_zurueck():
    fall, freigabe = _fall_mit_offener_freigabe_erzeugen()

    response = client.post(
        f"/api/freigaben/{freigabe['id']}/ablehnen",
        json={"entscheider": "operator@example.test", "grund": "Falscher Dienstleister ausgewählt."},
    )
    assert response.status_code == 200
    abgelehnt = response.json()
    assert abgelehnt["status"] == "abgelehnt"
    assert abgelehnt["ablehnungsgrund"] == "Falscher Dienstleister ausgewählt."

    fall_response = client.get(f"/api/faelle/{fall['id']}").json()
    assert fall_response["status"] == FallStatus.eingeordnet.value

    nachrichten = client.get(f"/api/faelle/{fall['id']}/nachrichten").json()
    ausgehende = next(n for n in nachrichten if n["richtung"] == "ausgehend")
    assert ausgehende["status"] == NachrichtStatus.abgelehnt.value


def test_freigaben_liste_zeigt_standardmaessig_nur_offene():
    fall, freigabe = _fall_mit_offener_freigabe_erzeugen()
    client.post(f"/api/freigaben/{freigabe['id']}/ablehnen", json={"entscheider": "op", "grund": "x"})

    offene = client.get("/api/freigaben").json()
    assert freigabe["id"] not in [f["id"] for f in offene]

    alle = client.get("/api/freigaben", params={"nur_offene": False}).json()
    assert freigabe["id"] in [f["id"] for f in alle]
