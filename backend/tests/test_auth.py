"""Echter Login/Logout/Rollen-Flow — im Unterschied zu allen anderen Tests
wird hier die globale `aktueller_benutzer`-Test-Override (siehe conftest.py)
bewusst kurz entfernt, damit die tatsächliche Session-/Cookie-Logik läuft."""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.auth import aktueller_benutzer
from app.main import app
from app.models import Benutzer, Sitzung
from tests.conftest import engine


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


def test_login_ignoriert_gross_kleinschreibung_der_email(echter_login_client: TestClient):
    login = echter_login_client.post(
        "/api/auth/login", json={"email": "Admin@Example.Test", "passwort": "admin123"}
    )
    assert login.status_code == 200
    assert login.json()["email"] == "admin@example.test"


def test_benutzer_anlegen_normalisiert_email_und_erkennt_duplikat_ueber_case(
    echter_login_client: TestClient,
):
    echter_login_client.post(
        "/api/auth/login", json={"email": "admin@example.test", "passwort": "admin123"}
    )
    erstellt = echter_login_client.post(
        "/api/benutzer",
        json={
            "name": "Case-Test",
            "email": "Case.Test@Example.Test",
            "passwort": "ein-ausreichend-langes-testpasswort",
            "rolle": "user",
        },
    )
    assert erstellt.status_code == 201
    assert erstellt.json()["email"] == "case.test@example.test"

    duplikat = echter_login_client.post(
        "/api/benutzer",
        json={
            "name": "Case-Test 2",
            "email": "case.test@example.test",
            "passwort": "ein-anderes-ausreichend-langes-passwort",
            "rolle": "user",
        },
    )
    assert duplikat.status_code == 409


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


def test_login_fehlermeldung_gleich_fuer_unbekannte_mail_und_falsches_passwort(
    echter_login_client: TestClient,
):
    """OWASP-Vorgabe gegen User-Enumeration: identische Antwort, egal ob
    das Konto nicht existiert oder nur das Passwort falsch ist."""
    unbekannt = echter_login_client.post(
        "/api/auth/login", json={"email": "gibts-nicht@example.test", "passwort": "irgendwas"}
    )
    falsch = echter_login_client.post(
        "/api/auth/login", json={"email": "admin@example.test", "passwort": "falsch"}
    )
    assert unbekannt.status_code == falsch.status_code == 401
    assert unbekannt.json()["detail"] == falsch.json()["detail"]


def test_benutzer_anlegen_lehnt_kurzes_passwort_ab(echter_login_client: TestClient):
    echter_login_client.post(
        "/api/auth/login", json={"email": "admin@example.test", "passwort": "admin123"}
    )
    response = echter_login_client.post(
        "/api/benutzer",
        json={
            "name": "Zu kurzes Passwort",
            "email": "zu-kurz@example.test",
            "passwort": "kurz1234",
            "rolle": "user",
        },
    )
    assert response.status_code == 422


def test_benutzer_anlegen_lehnt_ungueltige_email_ab(echter_login_client: TestClient):
    echter_login_client.post(
        "/api/auth/login", json={"email": "admin@example.test", "passwort": "admin123"}
    )
    response = echter_login_client.post(
        "/api/benutzer",
        json={
            "name": "Ungültige E-Mail",
            "email": "nicht-valide",
            "passwort": "x" * 20,
            "rolle": "user",
        },
    )
    assert response.status_code == 422


def test_benutzer_anlegen_lehnt_passwort_ueber_72_bytes_ab(echter_login_client: TestClient):
    """bcrypt>=5.0 wirft für Passwörter >72 Bytes ein ValueError statt (wie
    <5.0) stillschweigend abzuschneiden — ohne die Byte-Prüfung in
    app.auth.passwort_byte_laenge_pruefen würde das hier zu einem
    unbehandelten 500er statt eines sauberen 422ers führen. 100 ASCII-
    Zeichen sind unter max_length=128 (Zeichen) gültig, aber 100 Bytes."""
    echter_login_client.post(
        "/api/auth/login", json={"email": "admin@example.test", "passwort": "admin123"}
    )
    response = echter_login_client.post(
        "/api/benutzer",
        json={
            "name": "Zu langes Passwort",
            "email": "zu-lang@example.test",
            "passwort": "a" * 100,
            "rolle": "user",
        },
    )
    assert response.status_code == 422


def test_login_lehnt_passwort_ueber_72_bytes_ab_statt_500(echter_login_client: TestClient):
    response = echter_login_client.post(
        "/api/auth/login",
        json={"email": "admin@example.test", "passwort": "a" * 100},
    )
    assert response.status_code == 422


def test_login_sperrt_konto_nach_mehreren_fehlversuchen(echter_login_client: TestClient):
    """Brute-Force-Schutz: eigenes Wegwerf-Konto, damit admin@/user@
    für die übrigen Tests unangetastet bleiben."""
    echter_login_client.post(
        "/api/auth/login", json={"email": "admin@example.test", "passwort": "admin123"}
    )
    passwort = "ein-ausreichend-langes-testpasswort"
    erstellt = echter_login_client.post(
        "/api/benutzer",
        json={
            "name": "Lockout-Test",
            "email": "lockout-test@example.test",
            "passwort": passwort,
            "rolle": "user",
        },
    )
    assert erstellt.status_code == 201
    echter_login_client.post("/api/auth/logout")

    for _ in range(5):
        r = echter_login_client.post(
            "/api/auth/login",
            json={"email": "lockout-test@example.test", "passwort": "falsches-passwort"},
        )
        assert r.status_code == 401

    # Selbst mit dem korrekten Passwort jetzt gesperrt.
    gesperrt = echter_login_client.post(
        "/api/auth/login",
        json={"email": "lockout-test@example.test", "passwort": passwort},
    )
    assert gesperrt.status_code == 401


def test_login_raeumt_abgelaufene_sitzungen_auf(echter_login_client: TestClient):
    """Ohne Cron/Hintergrundjob würde die sitzungen-Tabelle in einem lang
    laufenden Deployment unbegrenzt wachsen — ein Login räumt abgelaufene
    Zeilen opportunistisch mit weg (siehe app/auth.py::sitzung_anlegen)."""
    with Session(engine) as session:
        admin_id = session.exec(
            select(Benutzer.id).where(Benutzer.email == "admin@example.test")
        ).one()
        abgelaufen = Sitzung(
            token="abgelaufenes-test-token",
            benutzer_id=admin_id,
            laeuft_ab_am=datetime.utcnow() - timedelta(days=1),
        )
        session.add(abgelaufen)
        session.commit()

    echter_login_client.post(
        "/api/auth/login", json={"email": "admin@example.test", "passwort": "admin123"}
    )

    with Session(engine) as session:
        noch_da = session.exec(
            select(Sitzung).where(Sitzung.token == "abgelaufenes-test-token")
        ).first()
        assert noch_da is None
