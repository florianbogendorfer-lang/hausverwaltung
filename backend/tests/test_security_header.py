"""Sicherheits-Header-Middleware (app/main.py::sicherheits_header_setzen)
— bisher nur manuell per curl verifiziert. Diese Tests fixieren das
Verhalten dauerhaft: OWASP Secure Headers Project für alle Responses,
Strict-Transport-Security nur wenn cookie_secure (TLS-Deploy) aktiv ist."""

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


def test_sicherheits_header_auf_jeder_antwort():
    response = client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in response.headers["permissions-policy"]
    csp = response.headers["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "object-src 'none'" in csp
    assert "form-action 'self'" in csp
    assert "frame-ancestors 'none'" in csp


def test_hsts_nur_wenn_cookie_secure_aktiv():
    response = client.get("/health")
    if settings.cookie_secure:
        assert "strict-transport-security" in response.headers
    else:
        # Lokaler Test läuft ohne HV_COOKIE_SECURE — HSTS über http:// zu
        # senden würde Browsern fälschlich "immer HTTPS erzwingen"
        # beibringen (siehe app/main.py).
        assert "strict-transport-security" not in response.headers
