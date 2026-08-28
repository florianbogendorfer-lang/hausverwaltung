"""Middleware body_groesse_begrenzen (app/main.py, OWASP API4:2023): ein
Request mit einem zu großen Content-Length wird früh mit 413 abgelehnt,
bevor Pydantic ihn überhaupt zu sehen bekommt."""

from fastapi.testclient import TestClient

from app.main import _MAX_BODY_BYTES, app

client = TestClient(app)


def test_zu_grosser_request_body_wird_abgelehnt():
    zu_gross = b"x" * (_MAX_BODY_BYTES + 1)
    response = client.post(
        "/api/auth/login",
        content=zu_gross,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413


def test_normal_grosser_request_body_wird_nicht_abgelehnt():
    response = client.post(
        "/api/auth/login", json={"email": "nope@example.test", "passwort": "x"}
    )
    assert response.status_code == 401
