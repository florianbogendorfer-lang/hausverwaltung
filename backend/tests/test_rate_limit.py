"""IP-Rate-Bremse für /auth/login (app/rate_limit.py) — ergänzt den
Konto-Lockout in app/auth.py um einen Schutz gegen "Lockout als DoS"
(siehe dortiger Kommentar). Die übrige Testsuite überschreibt diese
Bremse global (conftest.py), damit sie unabhängig von der Aufrufreihen-
folge deterministisch bleibt; hier wird das Override gezielt entfernt,
um die Bremse selbst zu prüfen."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.rate_limit import _VERSUCHE
from app.routers.auth import login_rate_limiter


@pytest.fixture
def echter_rate_limit_client():
    override = app.dependency_overrides.pop(login_rate_limiter)
    _VERSUCHE.clear()
    try:
        yield TestClient(app)
    finally:
        _VERSUCHE.clear()
        app.dependency_overrides[login_rate_limiter] = override


def test_login_wird_nach_zu_vielen_versuchen_pro_ip_gebremst(
    echter_rate_limit_client: TestClient,
):
    for _ in range(20):
        response = echter_rate_limit_client.post(
            "/api/auth/login", json={"email": "nope@example.test", "passwort": "x"}
        )
        assert response.status_code == 401

    gebremst = echter_rate_limit_client.post(
        "/api/auth/login", json={"email": "nope@example.test", "passwort": "x"}
    )
    assert gebremst.status_code == 429
    assert "Retry-After" in gebremst.headers
