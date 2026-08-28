"""IP-Rate-Bremse für /ticket/{zugriffstoken} (app/rate_limit.py, siehe
Begründung in app/routers/ticket.py): der öffentliche, unauthentifizierte
Endpunkt soll trotz des hochentropischen Tokens nicht unbegrenzt oft
abgefragt werden können (OWASP API4:2023). Analog zu
tests/test_rate_limit.py entfernt dieser Test das globale Test-Override
gezielt, um die Bremse selbst zu prüfen."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.rate_limit import _VERSUCHE
from app.routers.ticket import ticket_rate_limiter


@pytest.fixture
def echter_rate_limit_client():
    override = app.dependency_overrides.pop(ticket_rate_limiter)
    _VERSUCHE.clear()
    try:
        yield TestClient(app)
    finally:
        _VERSUCHE.clear()
        app.dependency_overrides[ticket_rate_limiter] = override


def test_ticket_ansehen_wird_nach_zu_vielen_versuchen_gebremst(
    echter_rate_limit_client: TestClient,
):
    for _ in range(60):
        response = echter_rate_limit_client.get("/api/ticket/gibts-nicht")
        assert response.status_code == 404

    gebremst = echter_rate_limit_client.get("/api/ticket/gibts-nicht")
    assert gebremst.status_code == 429
    assert "Retry-After" in gebremst.headers
