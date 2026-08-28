"""app.config.Settings — Seed-Passwort-Absicherung beim Start.

War ursprünglich eine Fail-Fast-Prüfung (siehe Git-Historie), die aber den
echten Clever-Cloud-Deploy brach: kein interaktiver Schritt existiert, um
HV_SEED_ADMIN_PASSWORT/HV_SEED_USER_PASSWORT vor dem allerersten Start zu
setzen, ein Startfehler ließ den Deploy endlos fehlschlagen. Jetzt wird
stattdessen automatisch ein zufälliges Passwort erzeugt, sobald
HV_COOKIE_SECURE aktiv ist (Produktions-Deploy) und kein eigenes Passwort
gesetzt wurde — sicherer als das bekannte Demo-Passwort, ohne die
Deploy-Pipeline zu blockieren."""

import pytest

from app import config as config_modul
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


def test_llm_provider_mistral_ohne_key_schlaegt_fehl():
    with pytest.raises(ValueError, match="HV_MISTRAL_API_KEY fehlt"):
        Settings(llm_provider="mistral", mistral_api_key=None)


def test_llm_provider_mistral_mit_key_ist_gueltig():
    Settings(llm_provider="mistral", mistral_api_key="irgendein-key")


def test_llm_provider_mistral_mit_aktiviertem_nvidia_umschalter_verlangt_nvidia_key(monkeypatch):
    # NVIDIA_STATT_MISTRAL ist eine reine Code-Konstante (siehe
    # app/config.py) — hier per monkeypatch aktiviert, um zu prüfen, dass
    # der Fail-Fast-Check dann den richtigen Key verlangt (nicht mehr
    # HV_MISTRAL_API_KEY, das bei aktiviertem Umschalter unbenutzt bliebe).
    monkeypatch.setattr(config_modul, "NVIDIA_STATT_MISTRAL", True)
    with pytest.raises(ValueError, match="HV_NVIDIA_API_KEY fehlt"):
        Settings(llm_provider="mistral", mistral_api_key=None, nvidia_api_key=None)
    Settings(llm_provider="mistral", mistral_api_key=None, nvidia_api_key="irgendein-key")
