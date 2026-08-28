import json

from fastapi.testclient import TestClient

from app.agent.model_router import LLMAntwort, ModelRouter
from app.config import settings
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
    fall = response.json()

    assert fall["typ"] == "reparaturmeldung"
    assert fall["gewerk"] == "schlosser"
    assert fall["status"] == FallStatus.wartet_auf_freigabe.value
    assert fall["objekt_id"] is not None
    assert fall["melder_kontakt_id"] is not None
    assert fall["dienstleister_id"] is not None
    assert fall["konfidenz"] == 0.92

    fall_id = fall["id"]

    trace_response = client.get(f"/api/faelle/{fall_id}/trace")
    assert trace_response.status_code == 200
    trace = trace_response.json()
    phasen = [t["phase"] for t in trace]
    assert "wahrnehmung" in phasen
    assert "tool_call" in phasen
    assert "tool_result" in phasen
    assert any(t["schritt_nr"] == i + 1 for i, t in enumerate(trace))
    modelle_im_trace = {t["modell"] for t in trace if t["modell"]}
    assert modelle_im_trace, "mindestens ein Trace-Eintrag sollte das verwendete Modell nennen"

    nachrichten_response = client.get(f"/api/faelle/{fall_id}/nachrichten")
    assert nachrichten_response.status_code == 200
    nachrichten = nachrichten_response.json()
    ausgehende = [n for n in nachrichten if n["richtung"] == "ausgehend"]
    assert len(ausgehende) == 1
    assert ausgehende[0]["status"] == NachrichtStatus.entwurf.value
    assert "Termin" in ausgehende[0]["inhalt"] or "Schloss" in ausgehende[0]["inhalt"]

    aktionen_response = client.get(f"/api/faelle/{fall_id}/aktionen")
    assert aktionen_response.status_code == 200
    aktionsarten = {a["aktionsart"] for a in aktionen_response.json()}
    assert "fall:angelegt" in aktionsarten
    assert "nachricht:entwurf_erstellt" in aktionsarten
    assert "freigabe:angefordert" in aktionsarten

    freigaben_response = client.get("/api/freigaben")
    assert freigaben_response.status_code == 200
    offene_freigaben = [f for f in freigaben_response.json() if f["fall_id"] == fall_id]
    assert len(offene_freigaben) == 1
    freigabe = offene_freigaben[0]
    assert freigabe["status"] == "offen"
    assert freigabe["aktionstyp"] == "nachricht_senden"
    assert freigabe["ueberfaellig"] is False
    assert freigabe["begruendung"]


def test_beauftragungsmail_enthaelt_terminportal_link_ohne_konfiguration():
    """Die Basis-URL für den Terminportal-Link (siehe app/agent/loop.py)
    braucht keine manuell gesetzte HV_OEFFENTLICHE_BASIS_URL mehr — sie
    wird aus dem eingehenden Request abgeleitet (app/routers/postfach.py).
    Der TestClient sendet Requests standardmäßig an "http://testserver",
    der Link muss also genau darauf zeigen."""
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
    fall = response.json()

    nachrichten = client.get(f"/api/faelle/{fall['id']}/nachrichten").json()
    ausgehende = next(n for n in nachrichten if n["richtung"] == "ausgehend")
    erwarteter_link = f"http://testserver/dienstleister-portal/{fall['dienstleister_zugriffstoken']}"
    assert erwarteter_link in ausgehende["inhalt"]


def test_explizite_basis_url_hat_vorrang_vor_request_abgeleiteter(monkeypatch):
    """HV_OEFFENTLICHE_BASIS_URL bleibt als Override nutzbar (z. B. eine
    eigene Domain statt der Clever-Cloud-Vorschau-URL) und muss die aus
    dem Request abgeleitete Basis-URL überstimmen."""
    monkeypatch.setattr(settings, "oeffentliche_basis_url", "https://hv.example.com")
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
    fall = response.json()

    nachrichten = client.get(f"/api/faelle/{fall['id']}/nachrichten").json()
    ausgehende = next(n for n in nachrichten if n["richtung"] == "ausgehend")
    erwarteter_link = f"https://hv.example.com/dienstleister-portal/{fall['dienstleister_zugriffstoken']}"
    assert erwarteter_link in ausgehende["inhalt"]
    assert "testserver" not in ausgehende["inhalt"]


def test_trace_zeigt_tatsaechlich_verwendetes_modell_beim_mailentwurf():
    """Regression: der Trace-Schritt "Entwurf erstellt" zeigte früher immer
    die KONFIGURIERTE Modell-ID (router.modell_fuer(...)) statt des von
    LLMClient.complete tatsächlich zurückgegebenen `LLMAntwort.modell` —
    lief kein API-Key konfiguriert und damit der DemoLLMClient, verschwand
    dessen "(demo, kein API-Key konfiguriert)"-Hinweis aus genau diesem
    einen Trace-Schritt (obwohl er beim Einordnungs-Schritt korrekt
    erscheint), was den Eindruck erweckte, es sei ein echter LLM-Aufruf
    gewesen. Ein Fake-Client, der ein vom angefragten Modell abweichendes
    `modell` zurückgibt, deckt das zuverlässig auf."""

    class _AbweichendesModellClient:
        modell_guenstig = "fake-guenstig"
        modell_stark = "fake-stark"

        def complete(self, modell: str, system: str, prompt: str, temperature: float) -> LLMAntwort:
            if "Zweck der Mail" in prompt:
                text = "Sehr geehrte Damen und Herren,\n\nBitte Termin vereinbaren.\n\nGrüße"
                return LLMAntwort(text=text, modell=f"{modell} (abweichend)", dauer_ms=5)
            daten = {
                "typ": "reparaturmeldung",
                "gewerk": "schlosser",
                "objekt_suchbegriff": "Musterstraße 5",
                "melder_suchbegriff": "Erika Musterfrau",
                "konfidenz": 0.92,
                "begruendung": "Türschloss defekt.",
            }
            return LLMAntwort(text=json.dumps(daten), modell=modell, dauer_ms=5)

    app.dependency_overrides[get_model_router] = lambda: ModelRouter(client=_AbweichendesModellClient())
    try:
        response = client.post(
            "/api/postfach/eingang",
            json={
                "von": "erika.musterfrau@example.test",
                "betreff": "Türschloss defekt",
                "inhalt": "Das Türschloss in der Musterstraße 5 ist defekt.",
            },
        )
        assert response.status_code == 200
        fall_id = response.json()["id"]

        trace = client.get(f"/api/faelle/{fall_id}/trace").json()
        entwurf_schritt = next(t for t in trace if "Entwurf erstellt" in t["inhalt"])
        assert entwurf_schritt["modell"] == "fake-stark (abweichend)"
    finally:
        app.dependency_overrides[get_model_router] = _get_model_router_override


def test_unklares_anliegen_wird_eskaliert():
    response = client.post(
        "/api/postfach/eingang",
        json={
            "von": "unbekannt@example.test",
            "betreff": "Frage",
            "inhalt": "Ich hätte da eine allgemeine Frage zu meinem Vertrag.",
        },
    )
    assert response.status_code == 200
    fall = response.json()
    assert fall["status"] == FallStatus.eskaliert.value

    aktionen_response = client.get(f"/api/faelle/{fall['id']}/aktionen")
    aktionsarten = {a["aktionsart"] for a in aktionen_response.json()}
    assert "fall:eskaliert" in aktionsarten


def test_uebergrosser_mailinhalt_wird_abgelehnt():
    """OWASP Input Validation Cheat Sheet: jede Eingabe muss längenbegrenzt
    sein — sonst könnte ein einzelner Eingang unbegrenzt LLM-Tokenkosten
    verursachen."""
    response = client.post(
        "/api/postfach/eingang",
        json={
            "von": "unbekannt@example.test",
            "betreff": "Frage",
            "inhalt": "x" * 20_001,
        },
    )
    assert response.status_code == 422
