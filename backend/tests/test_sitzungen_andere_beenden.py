"""POST /api/auth/sitzungen/andere-beenden — Sessions eines Kontos
beenden, ohne dafür das Passwort ändern zu müssen (OWASP Session
Management Cheat Sheet). Nutzt echter_login_client wie
tests/test_auth.py, denselben eigenen Test-Benutzer-Ansatz wie
tests/test_passwort_aendern.py (kein gemeinsam genutztes Seed-Konto)."""

import pytest
from fastapi.testclient import TestClient

from app.auth import aktueller_benutzer
from app.main import app


@pytest.fixture
def echter_login_client():
    override = app.dependency_overrides.pop(aktueller_benutzer)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides[aktueller_benutzer] = override


def _test_benutzer_anlegen(client: TestClient, email: str, passwort: str = "start-passwort-123") -> None:
    client.post("/api/auth/login", json={"email": "admin@example.test", "passwort": "admin123"})
    erstellt = client.post(
        "/api/benutzer",
        json={"name": "Sitzungs-Test", "email": email, "passwort": passwort, "rolle": "user"},
    )
    assert erstellt.status_code == 201
    client.post("/api/auth/logout")


def test_ohne_login_gibt_401(echter_login_client: TestClient):
    antwort = echter_login_client.post("/api/auth/sitzungen/andere-beenden")
    assert antwort.status_code == 401


def test_beendet_andere_sessions_aber_nicht_die_eigene(echter_login_client: TestClient):
    _test_benutzer_anlegen(echter_login_client, "sitzung-test-1@example.test")

    client_a = echter_login_client
    client_b = TestClient(app)
    client_c = TestClient(app)

    for client in (client_a, client_b, client_c):
        login = client.post(
            "/api/auth/login",
            json={"email": "sitzung-test-1@example.test", "passwort": "start-passwort-123"},
        )
        assert login.status_code == 200

    antwort = client_a.post("/api/auth/sitzungen/andere-beenden")
    assert antwort.status_code == 200
    assert antwort.json() == {"beendet": 2}

    assert client_a.get("/api/auth/me").status_code == 200
    assert client_b.get("/api/auth/me").status_code == 401
    assert client_c.get("/api/auth/me").status_code == 401


def test_ohne_weitere_sessions_gibt_null_zurueck(echter_login_client: TestClient):
    _test_benutzer_anlegen(echter_login_client, "sitzung-test-2@example.test")
    echter_login_client.post(
        "/api/auth/login",
        json={"email": "sitzung-test-2@example.test", "passwort": "start-passwort-123"},
    )

    antwort = echter_login_client.post("/api/auth/sitzungen/andere-beenden")
    assert antwort.status_code == 200
    assert antwort.json() == {"beendet": 0}
    assert echter_login_client.get("/api/auth/me").status_code == 200
