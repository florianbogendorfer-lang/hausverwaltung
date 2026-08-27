"""Ein unerwarteter Fehler nach der Einordnung (z. B. ein fehlschlagender
echter LLM-API-Aufruf beim Mailentwurf) darf den Fall nicht auf
EINGEORDNET hängen lassen — der Loop läuft synchron in der Request und
wird nicht automatisch erneut angestoßen, also muss er eskalieren statt
stillschweigend stehen zu bleiben."""

import json

from fastapi.testclient import TestClient

from app.agent.model_router import LLMAntwort, ModelRouter
from app.main import app
from app.models import FallStatus
from app.routers.postfach import get_model_router


class _CrashtBeimEntwerfenClient:
    """Einordnung gelingt, der Mailentwurf-Schritt wirft (simuliert einen
    fehlschlagenden echten API-Aufruf)."""

    modell_guenstig = "fake-guenstig"
    modell_stark = "fake-stark"

    def complete(self, modell: str, system: str, prompt: str, temperature: float) -> LLMAntwort:
        if "Zweck der Mail" in prompt:
            raise RuntimeError("Simulierter API-Fehler beim Mailentwurf")
        daten = {
            "typ": "reparaturmeldung",
            "gewerk": "schlosser",
            "objekt_suchbegriff": "Musterstraße 5",
            "melder_suchbegriff": "Erika Musterfrau",
            "konfidenz": 0.92,
            "begruendung": "Mail beschreibt eindeutig ein defektes Türschloss.",
        }
        return LLMAntwort(text=json.dumps(daten), modell=modell, dauer_ms=5)


def _get_model_router_override() -> ModelRouter:
    return ModelRouter(client=_CrashtBeimEntwerfenClient())


def test_fehler_nach_einordnung_eskaliert_statt_haengen_zu_bleiben():
    app.dependency_overrides[get_model_router] = _get_model_router_override
    try:
        client = TestClient(app)
        response = client.post(
            "/api/postfach/eingang",
            json={
                "von": "erika.musterfrau@example.test",
                "betreff": "Türschloss defekt",
                "inhalt": (
                    "Guten Tag, das Türschloss meiner Wohnung in der Musterstraße 5 "
                    "ist seit heute Morgen defekt. Erika Musterfrau"
                ),
            },
        )
        assert response.status_code == 200
        fall = response.json()

        # Nicht auf EINGEORDNET stehen bleiben — der Fehler muss sichtbar
        # als Eskalation landen, nicht als stiller Sackgassen-Status.
        assert fall["status"] == FallStatus.eskaliert.value

        aktionen = client.get(f"/api/faelle/{fall['id']}/aktionen").json()
        aktionsarten = {a["aktionsart"] for a in aktionen}
        assert "fall:eskaliert" in aktionsarten
    finally:
        from tests.test_agent_loop import _get_model_router_override as normale_override

        app.dependency_overrides[get_model_router] = normale_override
