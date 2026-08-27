"""Öffentliche Kundenansicht (`GET /api/ticket/{zugriffstoken}`): ein
hochentropisches Zugriffs-Token wird pro Fall vergeben, dient als
Zugriffsschutz (kein Login im Prototyp) und die Antwort zeigt nur
kundengerechte Klartext-Infos plus die den Kunden betreffende
Korrespondenz — nicht die interne Beauftragungsmail an den
Dienstleister. Die kurze `ticket_nummer` ist nur noch eine für Menschen
lesbare Referenznummer, kein Zugriffsschutz mehr."""

from fastapi.testclient import TestClient

from app.agent.model_router import ModelRouter
from app.main import app
from app.routers.postfach import get_model_router
from tests.fakes import FakeLLMClient

fake_client = FakeLLMClient()
app.dependency_overrides[get_model_router] = lambda: ModelRouter(client=fake_client)

client = TestClient(app)


def _tuerschloss_fall() -> dict:
    response = client.post(
        "/api/postfach/eingang",
        json={
            "von": "erika.musterfrau@example.test",
            "betreff": "Türschloss defekt",
            "inhalt": (
                "Guten Tag, das Türschloss meiner Wohnung in der Musterstraße 5 "
                "ist seit heute Morgen defekt und lässt sich nicht mehr "
                "versperren. Bitte um rasche Hilfe. Erika Musterfrau"
            ),
        },
    )
    assert response.status_code == 200
    return response.json()


def test_fall_hat_eindeutige_ticket_nummer():
    fall_a = _tuerschloss_fall()
    fall_b = _tuerschloss_fall()
    assert fall_a["ticket_nummer"]
    assert fall_a["ticket_nummer"].startswith("HV-")
    assert fall_a["ticket_nummer"] != fall_b["ticket_nummer"]


def test_ticket_ansehen_zeigt_klartext_status_und_eigene_korrespondenz():
    fall = _tuerschloss_fall()
    response = client.get(f"/api/ticket/{fall['zugriffstoken']}")
    assert response.status_code == 200
    daten = response.json()

    assert daten["ticket_nummer"] == fall["ticket_nummer"]
    assert daten["status_text"]
    assert "WARTET_AUF_FREIGABE" not in daten["status_text"]

    # Die eigene eingehende Mail ist Teil der Korrespondenz …
    eingehend = [n for n in daten["nachrichten"] if n["richtung"] == "eingehend"]
    assert len(eingehend) == 1
    assert "Türschloss" in eingehend[0]["betreff"]

    # … die interne Beauftragungsmail an den Dienstleister dagegen nicht.
    for nachricht in daten["nachrichten"]:
        assert "Beauftragung" not in nachricht["betreff"]


def test_beauftragungsmail_traegt_ticket_nummer_im_betreff():
    fall = _tuerschloss_fall()
    nachrichten = client.get(f"/api/faelle/{fall['id']}/nachrichten").json()
    ausgehende = [n for n in nachrichten if n["richtung"] == "ausgehend"]
    assert len(ausgehende) == 1
    assert ausgehende[0]["betreff"].startswith(f"[{fall['ticket_nummer']}]")


def test_unbekanntes_zugriffstoken_gibt_404():
    response = client.get("/api/ticket/dieses-token-existiert-nicht")
    assert response.status_code == 404
