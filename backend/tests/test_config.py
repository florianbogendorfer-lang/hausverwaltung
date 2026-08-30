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


# NVIDIA_STATT_MISTRAL steht aktuell auf True (siehe app/config.py) — die
# folgenden Tests decken den Fail-Fast-Check daher für BEIDE Zustände des
# Umschalters ab, statt sich auf den jeweils aktuellen Default zu verlassen.


def test_llm_provider_mistral_ohne_nvidia_key_schlaegt_fehl_bei_aktiviertem_umschalter(monkeypatch):
    monkeypatch.setattr(config_modul, "NVIDIA_STATT_MISTRAL", True)
    with pytest.raises(ValueError, match="HV_NVIDIA_API_KEY fehlt"):
        Settings(llm_provider="mistral", mistral_api_key=None, nvidia_api_key=None)


def test_llm_provider_mistral_mit_nvidia_key_ist_gueltig_bei_aktiviertem_umschalter(monkeypatch):
    monkeypatch.setattr(config_modul, "NVIDIA_STATT_MISTRAL", True)
    Settings(llm_provider="mistral", mistral_api_key=None, nvidia_api_key="irgendein-key")


def test_llm_provider_mistral_ohne_mistral_key_schlaegt_fehl_bei_deaktiviertem_umschalter(monkeypatch):
    monkeypatch.setattr(config_modul, "NVIDIA_STATT_MISTRAL", False)
    with pytest.raises(ValueError, match="HV_MISTRAL_API_KEY fehlt"):
        Settings(llm_provider="mistral", mistral_api_key=None)


def test_llm_provider_mistral_mit_mistral_key_ist_gueltig_bei_deaktiviertem_umschalter(monkeypatch):
    monkeypatch.setattr(config_modul, "NVIDIA_STATT_MISTRAL", False)
    Settings(llm_provider="mistral", mistral_api_key="irgendein-key")


# _demo_fallbacks_in_produktion_warnen: kein Fail-Fast (siehe Modul-
# Docstring, gleiche Begründung wie bei den Seed-Passwörtern), aber ein
# unübersehbares Log-Warning, falls ein Produktions-Deploy (cookie_secure)
# unbemerkt mit Fake-LLM bzw. simuliertem Mailversand läuft.


def test_demo_llm_ohne_key_warnt_in_produktion(capsys):
    Settings(cookie_secure=True, anthropic_api_key=None, llm_provider=None)
    ausgabe = capsys.readouterr().out
    assert "DemoLLMClient" in ausgabe


def test_demo_llm_ohne_key_warnt_nicht_ausserhalb_produktion(capsys):
    Settings(cookie_secure=False, anthropic_api_key=None, llm_provider=None)
    ausgabe = capsys.readouterr().out
    assert "DemoLLMClient" not in ausgabe


def test_kein_demo_llm_warning_mit_anthropic_key(capsys):
    Settings(cookie_secure=True, anthropic_api_key="irgendein-key", llm_provider=None)
    ausgabe = capsys.readouterr().out
    assert "DemoLLMClient" not in ausgabe


def test_kein_demo_llm_warning_bei_explizitem_provider_demo_ist_trotzdem_gewarnt(capsys):
    Settings(cookie_secure=True, llm_provider="demo")
    ausgabe = capsys.readouterr().out
    assert "DemoLLMClient" in ausgabe


def test_smtp_nicht_konfiguriert_warnt_in_produktion(capsys):
    Settings(cookie_secure=True, smtp_host=None)
    ausgabe = capsys.readouterr().out
    assert "SimulierterMailAdapter" in ausgabe


def test_smtp_konfiguriert_warnt_nicht(capsys):
    Settings(cookie_secure=True, smtp_host="smtp.example.test", anthropic_api_key="k")
    ausgabe = capsys.readouterr().out
    assert "SimulierterMailAdapter" not in ausgabe
