"""POST /api/auth/passwort — Self-Service-Passwortänderung.

Nutzt echter_login_client (siehe tests/test_auth.py) statt der globalen
Test-Override, weil hier die tatsächliche Session-/Passwort-Logik geprüft
wird, nicht nur Fachlogik hinter einer fest angenommenen Rolle.

Testet gezielt gegen einen frisch angelegten Test-Benutzer (nicht den
gemeinsam genutzten Seed-Nutzer user@example.test) — sonst würde eine
Passwortänderung das Passwort für alle anderen, unabhängig laufenden
Testdateien verändern, die sich auf den Seed-Wert verlassen."""

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
    """Legt über einen frisch eingeloggten Admin einen eigenen Test-Benutzer
    an, damit die Passwort-Tests kein gemeinsam genutztes Seed-Konto
    verändern."""
    client.post("/api/auth/login", json={"email": "admin@example.test", "passwort": "admin123"})
    erstellt = client.post(
        "/api/benutzer",
        json={"name": "PW-Test", "email": email, "passwort": passwort, "rolle": "user"},
    )
    assert erstellt.status_code == 201
    client.post("/api/auth/logout")


def test_passwort_aendern_mit_falschem_aktuellem_passwort_gibt_401(
    echter_login_client: TestClient,
):
    _test_benutzer_anlegen(echter_login_client, "pw-test-1@example.test")
    echter_login_client.post(
        "/api/auth/login",
        json={"email": "pw-test-1@example.test", "passwort": "start-passwort-123"},
    )
    antwort = echter_login_client.post(
        "/api/auth/passwort",
        json={"aktuelles_passwort": "falsch-falsch-falsch", "neues_passwort": "x" * 20},
    )
    assert antwort.status_code == 401


def test_passwort_aendern_ohne_login_gibt_401(echter_login_client: TestClient):
    antwort = echter_login_client.post(
        "/api/auth/passwort",
        json={"aktuelles_passwort": "start-passwort-123", "neues_passwort": "x" * 20},
    )
    assert antwort.status_code == 401


def test_passwort_aendern_zu_kurzes_neues_passwort_gibt_422(echter_login_client: TestClient):
    _test_benutzer_anlegen(echter_login_client, "pw-test-2@example.test")
    echter_login_client.post(
        "/api/auth/login",
        json={"email": "pw-test-2@example.test", "passwort": "start-passwort-123"},
    )
    antwort = echter_login_client.post(
        "/api/auth/passwort",
        json={"aktuelles_passwort": "start-passwort-123", "neues_passwort": "zukurz"},
    )
    assert antwort.status_code == 422


def test_passwort_aendern_erfolgreich_und_neues_passwort_funktioniert(
    echter_login_client: TestClient,
):
    _test_benutzer_anlegen(echter_login_client, "pw-test-3@example.test")
    echter_login_client.post(
        "/api/auth/login",
        json={"email": "pw-test-3@example.test", "passwort": "start-passwort-123"},
    )
    aendern = echter_login_client.post(
        "/api/auth/passwort",
        json={
            "aktuelles_passwort": "start-passwort-123",
            "neues_passwort": "ein-neues-langes-passwort",
        },
    )
    assert aendern.status_code == 204

    # Aktuelle Session bleibt gültig (kein Selbst-Aussperren).
    me = echter_login_client.get("/api/auth/me")
    assert me.status_code == 200

    echter_login_client.post("/api/auth/logout")

    # Altes Passwort funktioniert nicht mehr, neues schon.
    alt = echter_login_client.post(
        "/api/auth/login",
        json={"email": "pw-test-3@example.test", "passwort": "start-passwort-123"},
    )
    assert alt.status_code == 401

    neu = echter_login_client.post(
        "/api/auth/login",
        json={"email": "pw-test-3@example.test", "passwort": "ein-neues-langes-passwort"},
    )
    assert neu.status_code == 200


def test_passwort_aendern_beendet_andere_sessions_nicht_aber_die_eigene(
    echter_login_client: TestClient,
):
    """Zwei Logins (zwei Sessions) desselben Kontos — nach der
    Passwortänderung über Client A muss Client B ausgeloggt sein, Client A
    (der die Änderung ausgeführt hat) bleibt eingeloggt."""
    _test_benutzer_anlegen(echter_login_client, "pw-test-4@example.test")

    client_a = echter_login_client
    client_b = TestClient(app)

    client_a.post(
        "/api/auth/login", json={"email": "pw-test-4@example.test", "passwort": "start-passwort-123"}
    )
    client_b.post(
        "/api/auth/login", json={"email": "pw-test-4@example.test", "passwort": "start-passwort-123"}
    )

    assert client_b.get("/api/auth/me").status_code == 200

    aendern = client_a.post(
        "/api/auth/passwort",
        json={
            "aktuelles_passwort": "start-passwort-123",
            "neues_passwort": "noch-ein-langes-passwort",
        },
    )
    assert aendern.status_code == 204

    assert client_a.get("/api/auth/me").status_code == 200
    assert client_b.get("/api/auth/me").status_code == 401
