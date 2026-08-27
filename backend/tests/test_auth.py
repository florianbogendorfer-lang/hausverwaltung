"""Echter Login/Logout/Rollen-Flow — im Unterschied zu allen anderen Tests
wird hier die globale `aktueller_benutzer`-Test-Override (siehe conftest.py)
bewusst kurz entfernt, damit die tatsächliche Session-/Cookie-Logik läuft."""

import pytest
from fastapi.testclient import TestClient

from app.auth import aktueller_benutzer
from app.main import app


@pytest.fixture
def echter_login_client():
    """Entfernt die Test-weite Auth-Override für die Dauer des Tests."""
    override = app.dependency_overrides.pop(aktueller_benutzer)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides[aktueller_benutzer] = override


def test_geschuetzter_endpunkt_ohne_login_gibt_401(echter_login_client: TestClient):
    response = echter_login_client.get("/api/faelle")
    assert response.status_code == 401


def test_login_falsches_passwort_gibt_401(echter_login_client: TestClient):
    response = echter_login_client.post(
        "/api/auth/login", json={"email": "admin@example.test", "passwort": "falsch"}
    )
    assert response.status_code == 401


def test_login_logout_und_geschuetzter_zugriff(echter_login_client: TestClient):
    login = echter_login_client.post(
        "/api/auth/login", json={"email": "admin@example.test", "passwort": "admin123"}
    )
    assert login.status_code == 200
    daten = login.json()
    assert daten["email"] == "admin@example.test"
    assert daten["rolle"] == "admin"

    me = echter_login_client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "admin@example.test"

    faelle = echter_login_client.get("/api/faelle")
    assert faelle.status_code == 200

    logout = echter_login_client.post("/api/auth/logout")
    assert logout.status_code == 200

    nach_logout = echter_login_client.get("/api/faelle")
    assert nach_logout.status_code == 401


def test_normaler_user_darf_fall_nicht_loeschen(echter_login_client: TestClient):
    login = echter_login_client.post(
        "/api/auth/login", json={"email": "user@example.test", "passwort": "user1234"}
    )
    assert login.status_code == 200
    assert login.json()["rolle"] == "user"

    response = echter_login_client.delete("/api/faelle/1")
    assert response.status_code == 403


def test_admin_darf_benutzer_verwalten_user_nicht(echter_login_client: TestClient):
    echter_login_client.post(
        "/api/auth/login", json={"email": "user@example.test", "passwort": "user1234"}
    )
    assert echter_login_client.get("/api/benutzer").status_code == 403

    echter_login_client.post("/api/auth/logout")
    echter_login_client.post(
        "/api/auth/login", json={"email": "admin@example.test", "passwort": "admin123"}
    )
    assert echter_login_client.get("/api/benutzer").status_code == 200
