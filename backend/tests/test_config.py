"""app.config.Settings — Seed-Passwort-Absicherung beim Start.

War ursprünglich eine Fail-Fast-Prüfung (siehe Git-Historie), die aber den
echten Clever-Cloud-Deploy brach: kein interaktiver Schritt existiert, um
HV_SEED_ADMIN_PASSWORT/HV_SEED_USER_PASSWORT vor dem allerersten Start zu
setzen, ein Startfehler ließ den Deploy endlos fehlschlagen. Jetzt wird
stattdessen automatisch ein zufälliges Passwort erzeugt, sobald
HV_COOKIE_SECURE aktiv ist (Produktions-Deploy) und kein eigenes Passwort
gesetzt wurde — sicherer als das bekannte Demo-Passwort, ohne die
Deploy-Pipeline zu blockieren."""

from app.config import Settings


def test_cookie_secure_ohne_admin_passwort_erzeugt_zufallspasswort():
    settings = Settings(cookie_secure=True, seed_user_passwort="x" * 20)
    assert settings.seed_admin_passwort != "admin123"
    assert len(settings.seed_admin_passwort) >= 20


def test_cookie_secure_ohne_user_passwort_erzeugt_zufallspasswort():
    settings = Settings(cookie_secure=True, seed_admin_passwort="x" * 20)
    assert settings.seed_user_passwort != "user1234"
    assert len(settings.seed_user_passwort) >= 20


def test_zwei_instanzen_erzeugen_unterschiedliche_zufallspasswoerter():
    erste = Settings(cookie_secure=True)
    zweite = Settings(cookie_secure=True)
    assert erste.seed_admin_passwort != zweite.seed_admin_passwort


def test_cookie_secure_mit_gesetzten_passwoertern_behaelt_sie():
    settings = Settings(
        cookie_secure=True, seed_admin_passwort="x" * 20, seed_user_passwort="y" * 20
    )
    assert settings.seed_admin_passwort == "x" * 20
    assert settings.seed_user_passwort == "y" * 20


def test_cookie_secure_false_erlaubt_demo_passwoerter():
    settings = Settings(cookie_secure=False)
    assert settings.seed_admin_passwort == "admin123"
    assert settings.seed_user_passwort == "user1234"
