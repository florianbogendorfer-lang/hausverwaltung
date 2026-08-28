"""Middleware KoerpergroesseBegrenzenMiddleware (app/main.py, OWASP
API4:2023): ein zu großer Request wird früh mit 413 abgelehnt, bevor
Pydantic ihn überhaupt zu sehen bekommt — auch ohne Content-Length-Header
(Transfer-Encoding: chunked), da die Middleware die tatsächlich am
ASGI-`receive`-Kanal eintreffenden Bytes zählt statt nur dem Header zu
vertrauen."""

import anyio
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


def test_zu_grosser_body_ohne_content_length_header_wird_ebenfalls_abgelehnt():
    """Simuliert Transfer-Encoding: chunked auf ASGI-Ebene direkt (kein
    Content-Length-Header in scope["headers"]) — die frühere Middleware-
    Version prüfte NUR den Header und hätte das hier durchgelassen."""
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/auth/login",
        "headers": [(b"content-type", b"application/json")],
        "query_string": b"",
        "client": ("testclient", 1234),
    }

    chunk = b"x" * (_MAX_BODY_BYTES // 4)
    anzahl_chunks = 6  # insgesamt deutlich über _MAX_BODY_BYTES, in Stücken geliefert
    verbleibend = [anzahl_chunks]

    async def receive():
        if verbleibend[0] > 0:
            verbleibend[0] -= 1
            return {
                "type": "http.request",
                "body": chunk,
                "more_body": verbleibend[0] > 0,
            }
        return {"type": "http.disconnect"}

    antworten = []

    async def send(nachricht):
        antworten.append(nachricht)

    async def lauf():
        await app(scope, receive, send)

    anyio.run(lauf)

    status_nachrichten = [n for n in antworten if n["type"] == "http.response.start"]
    assert status_nachrichten, "keine Antwort erhalten"
    assert status_nachrichten[0]["status"] == 413
