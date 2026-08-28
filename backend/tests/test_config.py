"""app.config.Settings — Fail-fast-Validierung beim Start. Ergänzt die
bestehende LLM-Provider-Prüfung um eine analoge Prüfung für die Seed-
Passwörter: ein Produktions-Deploy (HV_COOKIE_SECURE=true) darf niemals
mit den im Quellcode öffentlich sichtbaren Demo-Passwörtern starten."""

import pytest

from app.config import Settings


def test_cookie_secure_ohne_admin_passwort_schlaegt_fehl():
    with pytest.raises(ValueError, match="HV_SEED_ADMIN_PASSWORT"):
        Settings(cookie_secure=True, seed_user_passwort="x" * 20)


def test_cookie_secure_ohne_user_passwort_schlaegt_fehl():
    with pytest.raises(ValueError, match="HV_SEED_USER_PASSWORT"):
        Settings(cookie_secure=True, seed_admin_passwort="x" * 20)


def test_cookie_secure_mit_gesetzten_passwoertern_startet():
    settings = Settings(
        cookie_secure=True, seed_admin_passwort="x" * 20, seed_user_passwort="y" * 20
    )
    assert settings.cookie_secure is True


def test_cookie_secure_false_erlaubt_demo_passwoerter():
    settings = Settings(cookie_secure=False)
    assert settings.seed_admin_passwort == "admin123"
