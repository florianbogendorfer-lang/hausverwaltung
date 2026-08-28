"""IP-Rate-Bremse für /postfach/eingang (app/rate_limit.py, siehe
Begründung in app/routers/postfach.py): jeder Aufruf löst einen echten
LLM-API-Aufruf aus, eine Retry-Schleife oder kompromittierte Session
sollte keine unbegrenzten Kosten verursachen können. Analog zu
tests/test_rate_limit.py entfernt dieser Test das globale Test-Override
gezielt, um die Bremse selbst zu prüfen."""

import pytest
from fastapi.testclient import TestClient

from app.agent.model_router import ModelRouter
from app.main import app
from app.rate_limit import _VERSUCHE
from app.routers.postfach import get_model_router, postfach_rate_limiter
from tests.fakes import FakeLLMClient

fake_client = FakeLLMClient()
app.dependency_overrides[get_model_router] = lambda: ModelRouter(client=fake_client)


@pytest.fixture
def echter_rate_limit_client():
    override = app.dependency_overrides.pop(postfach_rate_limiter)
    _VERSUCHE.clear()
    try:
        yield TestClient(app)
    finally:
        _VERSUCHE.clear()
        app.dependency_overrides[postfach_rate_limiter] = override


def test_postfach_eingang_wird_nach_zu_vielen_versuchen_gebremst(
    echter_rate_limit_client: TestClient,
):
    mail = {
        "von": "erika.musterfrau@example.test",
        "betreff": "Türschloss defekt",
        "inhalt": "Das Türschloss meiner Wohnung in der Musterstraße 5 ist kaputt.",
    }
    for _ in range(30):
        response = echter_rate_limit_client.post("/api/postfach/eingang", json=mail)
        assert response.status_code == 200

    gebremst = echter_rate_limit_client.post("/api/postfach/eingang", json=mail)
    assert gebremst.status_code == 429
    assert "Retry-After" in gebremst.headers
