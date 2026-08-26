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


def test_tuerschloss_mail_erzeugt_fall_mit_korrekter_einordnung():
    response = client.post(
        "/postfach/eingang",
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
    fall = response.json()

    assert fall["typ"] == "reparaturmeldung"
    assert fall["gewerk"] == "schlosser"
    assert fall["status"] == FallStatus.eingeordnet.value
    assert fall["objekt_id"] is not None
    assert fall["melder_kontakt_id"] is not None
    assert fall["dienstleister_id"] is not None
    assert fall["konfidenz"] == 0.92

    fall_id = fall["id"]

    trace_response = client.get(f"/faelle/{fall_id}/trace")
    assert trace_response.status_code == 200
    trace = trace_response.json()
    phasen = [t["phase"] for t in trace]
    assert "wahrnehmung" in phasen
    assert "tool_call" in phasen
    assert "tool_result" in phasen
    assert any(t["schritt_nr"] == i + 1 for i, t in enumerate(trace))
    modelle_im_trace = {t["modell"] for t in trace if t["modell"]}
    assert modelle_im_trace, "mindestens ein Trace-Eintrag sollte das verwendete Modell nennen"

    nachrichten_response = client.get(f"/faelle/{fall_id}/nachrichten")
    assert nachrichten_response.status_code == 200
    nachrichten = nachrichten_response.json()
    ausgehende = [n for n in nachrichten if n["richtung"] == "ausgehend"]
    assert len(ausgehende) == 1
    assert ausgehende[0]["status"] == NachrichtStatus.entwurf.value
    assert "Termin" in ausgehende[0]["inhalt"] or "Schloss" in ausgehende[0]["inhalt"]

    aktionen_response = client.get(f"/faelle/{fall_id}/aktionen")
    assert aktionen_response.status_code == 200
    aktionsarten = {a["aktionsart"] for a in aktionen_response.json()}
    assert "fall:angelegt" in aktionsarten
    assert "nachricht:entwurf_erstellt" in aktionsarten


def test_unklares_anliegen_wird_eskaliert():
    response = client.post(
        "/postfach/eingang",
        json={
            "von": "unbekannt@example.test",
            "betreff": "Frage",
            "inhalt": "Ich hätte da eine allgemeine Frage zu meinem Vertrag.",
        },
    )
    assert response.status_code == 200
    fall = response.json()
    assert fall["status"] == FallStatus.eskaliert.value

    aktionen_response = client.get(f"/faelle/{fall['id']}/aktionen")
    aktionsarten = {a["aktionsart"] for a in aktionen_response.json()}
    assert "fall:eskaliert" in aktionsarten
