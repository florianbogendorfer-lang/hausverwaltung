"""app.observability — Request-IDs zur Log-Korrelation (siehe Modul-
Docstring) + Sentry-Init bleibt ohne HV_SENTRY_DSN ein reines No-Op."""

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from app.observability import init_sentry, neue_request_id, request_id, request_id_var

client = TestClient(app)


def test_neue_request_id_uebernimmt_vorgeschlagene_id():
    assert neue_request_id("mein-request-id") == "mein-request-id"


def test_neue_request_id_erzeugt_eigene_id_ohne_vorschlag():
    erste = neue_request_id(None)
    zweite = neue_request_id(None)
    assert erste and zweite and erste != zweite


def test_request_id_ausserhalb_eines_requests_ist_platzhalter():
    assert request_id() == "-"


def test_response_traegt_x_request_id_header():
    response = client.get("/health")
    assert "X-Request-Id" in response.headers
    assert response.headers["X-Request-Id"]


def test_client_vorgegebene_request_id_wird_uebernommen():
    response = client.get("/health", headers={"X-Request-Id": "abc-123"})
    assert response.headers["X-Request-Id"] == "abc-123"


def test_zwei_requests_bekommen_unterschiedliche_ids_ohne_vorgabe():
    erste = client.get("/health").headers["X-Request-Id"]
    zweite = client.get("/health").headers["X-Request-Id"]
    assert erste != zweite


def test_init_sentry_ohne_dsn_ist_no_op(monkeypatch):
    monkeypatch.setattr("app.observability.settings", Settings(sentry_dsn=None))
    # Darf nicht werfen und braucht kein Sentry-Paket-Setup, um zu laufen.
    init_sentry()


def test_init_sentry_mit_dsn_ruft_sentry_sdk_init_auf(monkeypatch):
    import sentry_sdk

    aufrufe: list[dict] = []
    monkeypatch.setattr(sentry_sdk, "init", lambda **kwargs: aufrufe.append(kwargs))
    monkeypatch.setattr(
        "app.observability.settings",
        Settings(sentry_dsn="https://key@example.test/1", cookie_secure=True),
    )

    init_sentry()

    assert len(aufrufe) == 1
    assert aufrufe[0]["dsn"] == "https://key@example.test/1"
    assert aufrufe[0]["environment"] == "produktion"
    assert aufrufe[0]["send_default_pii"] is False


def test_request_id_var_kontext_wird_nach_request_zurueckgesetzt():
    assert request_id_var.get() == "-"
    client.get("/health")
    assert request_id_var.get() == "-"
