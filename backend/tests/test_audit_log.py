"""app.audit_log — sicherheitsrelevante Ereignisse werden protokolliert
(OWASP Logging Cheat Sheet). Nutzt caplog auf den Logger-Namen "hv.audit",
über den echte Requests (siehe tests/test_auth.py::echter_login_client)
laufen — kein eigener Mechanismus, dieselbe Login-/Passwort-/Benutzer-
verwaltungs-Logik wie die übrigen Auth-Tests."""

import logging

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


def test_login_erfolg_wird_protokolliert(echter_login_client: TestClient, caplog: pytest.LogCaptureFixture):
    with caplog.at_level(logging.INFO, logger="hv.audit"):
        echter_login_client.post(
            "/api/auth/login", json={"email": "admin@example.test", "passwort": "admin123"}
        )
    assert any("login_erfolgreich" in satz and "admin@example.test" in satz for satz in caplog.messages)


def test_login_fehlschlag_wird_protokolliert(
    echter_login_client: TestClient, caplog: pytest.LogCaptureFixture
):
    with caplog.at_level(logging.INFO, logger="hv.audit"):
        echter_login_client.post(
            "/api/auth/login", json={"email": "admin@example.test", "passwort": "falsch"}
        )
    assert any("login_fehlgeschlagen" in satz for satz in caplog.messages)


def test_login_unbekanntes_konto_wird_protokolliert(
    echter_login_client: TestClient, caplog: pytest.LogCaptureFixture
):
    with caplog.at_level(logging.INFO, logger="hv.audit"):
        echter_login_client.post(
            "/api/auth/login", json={"email": "nie-gesehen@example.test", "passwort": "irgendwas12345"}
        )
    assert any(
        "login_fehlgeschlagen" in satz and "konto_unbekannt" in satz for satz in caplog.messages
    )


def test_passwort_aendern_wird_protokolliert(
    echter_login_client: TestClient, caplog: pytest.LogCaptureFixture
):
    echter_login_client.post("/api/auth/login", json={"email": "admin@example.test", "passwort": "admin123"})
    erstellt = echter_login_client.post(
        "/api/benutzer",
        json={"name": "Audit-Test", "email": "audit-pw@example.test", "passwort": "start-passwort-123", "rolle": "user"},
    )
    assert erstellt.status_code == 201
    echter_login_client.post("/api/auth/logout")
    echter_login_client.post(
        "/api/auth/login", json={"email": "audit-pw@example.test", "passwort": "start-passwort-123"}
    )

    with caplog.at_level(logging.INFO, logger="hv.audit"):
        antwort = echter_login_client.post(
            "/api/auth/passwort",
            json={"aktuelles_passwort": "start-passwort-123", "neues_passwort": "ein-neues-langes-passwort"},
        )
    assert antwort.status_code == 204
    assert any(
        "passwort_geaendert" in satz and "audit-pw@example.test" in satz for satz in caplog.messages
    )


def test_benutzer_anlegen_und_loeschen_wird_protokolliert(
    echter_login_client: TestClient, caplog: pytest.LogCaptureFixture
):
    echter_login_client.post("/api/auth/login", json={"email": "admin@example.test", "passwort": "admin123"})

    with caplog.at_level(logging.INFO, logger="hv.audit"):
        erstellt = echter_login_client.post(
            "/api/benutzer",
            json={
                "name": "Audit-CRUD-Test",
                "email": "audit-crud@example.test",
                "passwort": "start-passwort-123",
                "rolle": "user",
            },
        )
    assert erstellt.status_code == 201
    assert any(
        "benutzer_angelegt" in satz
        and "audit-crud@example.test" in satz
        and "admin@example.test" in satz
        for satz in caplog.messages
    )

    benutzer_id = erstellt.json()["id"]
    with caplog.at_level(logging.INFO, logger="hv.audit"):
        geloescht = echter_login_client.delete(f"/api/benutzer/{benutzer_id}")
    assert geloescht.status_code == 204
    assert any("benutzer_geloescht" in satz and "audit-crud@example.test" in satz for satz in caplog.messages)
