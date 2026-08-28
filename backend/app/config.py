"""Zentrale Konfiguration.

NFR-5 / §12: Modell-/Provider-Konfiguration gehört hierher, nicht in Prompts.
Modell-IDs sind austauschbar (Provider-Wechsel Anthropic-API → Bedrock EU
per Konfiguration, siehe §12/§13) — daher hier und nicht im Code verdrahtet.
"""

import secrets

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Manueller Umschalter: NVIDIA NIM (Nemotron) statt Mistral verwenden,
# wenn HV_LLM_PROVIDER=mistral gesetzt ist (app/agent/model_router.py
# liest diese Konstante). Bewusst eine einfache Python-Konstante hier im
# Code, KEIN Settings-Feld/keine Env-Var — der Betreiber hat aktuell
# Zugriff auf ein einzelnes, persönliches NVIDIA-Kontingent, kein
# zugesagtes Produktions-Kontingent; ein Versehen in der
# Deploy-Konfiguration (falsch gesetzte Env-Var) soll den Provider daher
# nicht unbemerkt umschalten können. Die bestehende Mistral-Anbindung
# (MistralLLMClient) bleibt vollständig erhalten, diese Konstante
# entscheidet nur, welcher Client hinter der Wahl "mistral" tatsächlich
# steckt. Hier statt in model_router.py definiert, damit der Fail-Fast-
# Check unten (_provider_und_key_zusammen_pruefen) den richtigen Key
# verlangt, je nachdem wie die Konstante steht.
NVIDIA_STATT_MISTRAL = False


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HV_")

    database_url: str = "sqlite:///./hausverwaltung.db"

    anthropic_api_key: str | None = None
    mistral_api_key: str | None = None
    # NVIDIA NIM (OpenAI-kompatible API, integrate.api.nvidia.com) — probeweise
    # Alternative zu Mistral. Bewusst NICHT über llm_provider wählbar: der
    # Umschalter dazu ist die Code-Konstante NVIDIA_STATT_MISTRAL oben in
    # dieser Datei, keine Konfigurationsoption — siehe dort für die
    # Begründung. Der Key bleibt trotzdem regulär über die Umgebung gesetzt
    # (gleiches Muster wie die anderen *_api_key-Felder).
    nvidia_api_key: str | None = None

    # Explizite Provider-Wahl: "anthropic" | "mistral" | "demo". Ohne
    # Angabe gilt das bisherige Verhalten (Altkompatibilität): Anthropic-
    # Key gesetzt -> Anthropic, sonst Demo. Damit lassen sich beide echten
    # Provider parallel konfiguriert lassen und trotzdem gezielt zwischen
    # ihnen wechseln, ohne einen Key entfernen zu müssen.
    llm_provider: str | None = None

    # FR-AGENT-2 — Modell-Routing: günstig für Klassifikation/Extraktion,
    # stark für Kundentexte/Planung. Austauschbar, siehe §12.
    modell_guenstig: str = "claude-haiku-4-5"
    modell_stark: str = "claude-sonnet-5"
    mistral_modell_guenstig: str = "mistral-small-latest"
    mistral_modell_stark: str = "mistral-large-latest"
    # NVIDIA bietet für dieses Modell (Stand jetzt) keine separate
    # günstige/starke Variante — beide Stufen laufen probeweise auf
    # demselben Modell, bis es eine kleinere Nemotron-Variante gibt.
    nvidia_modell_guenstig: str = "nvidia/nemotron-3-super-120b-a12b"
    nvidia_modell_stark: str = "nvidia/nemotron-3-super-120b-a12b"

    # FR-HITL-6 / FR-AGENT-4 — unterhalb dieser Konfidenz wird eskaliert
    # statt geraten.
    konfidenz_schwelle: float = 0.6

    # FR-HITL-7 — offene Freigaben werden ab dieser Frist als überfällig
    # markiert (keine Auto-Ausführung, nur Anzeige).
    freigabe_timeout_stunden: int = 24

    # §16 Phase 5 — Vektorspeicher für dokumente_durchsuchen, getrennt von
    # der relationalen DB (§6), damit er unabhängig von SQLite/Postgres ist.
    chroma_persist_dir: str = "./chroma_data"

    # §16 Phase 6 — echter SMTP-Versand, bewusst per Default deaktiviert
    # (§2.2/§0: kein echter Mailversand im Prototyp). Erst wenn smtp_host
    # gesetzt ist, verwendet get_mail_adapter() den echten SmtpMailAdapter
    # statt des simulierten (gleiches Muster wie anthropic_api_key).
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_benutzer: str | None = None
    smtp_passwort: str | None = None
    smtp_absender: str | None = None

    # Öffentliche Basis-URL des Deployments (z. B. "https://hv.example.com",
    # ohne abschließenden Slash) — wird gebraucht, um in Mails an
    # Dienstleister einen anklickbaren Link zum Terminportal
    # (/dienstleister-portal/{token}) einzubetten. E-Mail-Clients kennen
    # anders als der Browser keinen "aktuellen Origin", eine relative URL
    # funktioniert dort nicht. Ohne gesetzten Wert lässt der Agent den Link
    # einfach weg (siehe app/agent/loop.py) — kein Fail-Fast, da sonst
    # (siehe Incident zu HV_SEED_ADMIN_PASSWORT) der Deploy-Start unnötig
    # riskiert würde, nur weil dieser eine, nicht sicherheitskritische Wert
    # fehlt.
    oeffentliche_basis_url: str | None = None

    # Session-Cookie nur über HTTPS versenden (OWASP Session Management).
    # Default False, damit lokales `uvicorn --reload` über http://
    # weiterhin funktioniert (Browser verwerfen Secure-Cookies ohne TLS
    # stillschweigend); docker-entrypoint.sh setzt dies im Deploy-Pfad
    # automatisch auf True, ohne dass eine manuelle Konfiguration nötig ist.
    cookie_secure: bool = False

    # Passwörter der von `app.seed` angelegten Demo-Benutzer. Default sind
    # die bisherigen, im Repo öffentlich sichtbaren Demo-Werte (nur für
    # lokale Entwicklung/Demo unbedenklich) — im Deploy-Pfad (Clever Cloud)
    # sollten HV_SEED_ADMIN_PASSWORT/HV_SEED_USER_PASSWORT gesetzt werden,
    # damit der öffentlich erreichbare Admin-Login nicht ein aus dem
    # Quellcode bekanntes, triviales Passwort trägt.
    _SEED_ADMIN_PASSWORT_DEFAULT = "admin123"
    _SEED_USER_PASSWORT_DEFAULT = "user1234"

    seed_admin_passwort: str = _SEED_ADMIN_PASSWORT_DEFAULT
    seed_user_passwort: str = _SEED_USER_PASSWORT_DEFAULT

    @model_validator(mode="after")
    def _provider_und_key_zusammen_pruefen(self) -> "Settings":
        # Fail fast beim Start statt eines kryptischen Fehlers erst beim
        # ersten LLM-Aufruf mitten im (asynchron nicht wiederholten)
        # Agent-Loop — HV_LLM_PROVIDER ist eine explizite Betreiber-
        # Entscheidung, der zugehörige Key muss dann auch da sein.
        if self.llm_provider == "mistral":
            if NVIDIA_STATT_MISTRAL and not self.nvidia_api_key:
                raise ValueError(
                    "HV_LLM_PROVIDER=mistral gesetzt und NVIDIA_STATT_MISTRAL "
                    "in app/config.py aktiviert, aber HV_NVIDIA_API_KEY fehlt."
                )
            if not NVIDIA_STATT_MISTRAL and not self.mistral_api_key:
                raise ValueError(
                    "HV_LLM_PROVIDER=mistral gesetzt, aber HV_MISTRAL_API_KEY fehlt."
                )
        if self.llm_provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError(
                "HV_LLM_PROVIDER=anthropic gesetzt, aber HV_ANTHROPIC_API_KEY fehlt."
            )
        return self

    @model_validator(mode="after")
    def _keine_demo_passwoerter_in_produktion(self) -> "Settings":
        # cookie_secure=True heißt: wir laufen hinter TLS (docker-
        # entrypoint.sh setzt das automatisch im Deploy-Pfad, siehe oben) —
        # also ein öffentlich erreichbares Deployment, kein lokaler Dev-
        # Server. Diese Prüfung verhinderte ursprünglich per Fail-Fast, dass
        # ein Betreiber, der HV_SEED_ADMIN_PASSWORT/HV_SEED_USER_PASSWORT
        # vergisst, unbemerkt einen Admin-Account mit einem aus dem
        # öffentlichen Quellcode bekannten, trivialen Passwort live schaltet
        # — das brach aber den echten Clever-Cloud-Deploy (kein
        # interaktiver Schritt, um die Variable vor dem allerersten Start
        # zu setzen; Startfehler == Deploy schlägt endlos fehl, die App ist
        # nicht erreichbar). Statt hart abzubrechen wird jetzt ein
        # kryptographisch zufälliges Passwort erzeugt und einmalig klar ins
        # Deploy-Log geschrieben (Betreiber kann es dort abholen und/oder
        # HV_SEED_ADMIN_PASSWORT danach setzen) — sicherer als das
        # bekannte Demo-Passwort, aber ohne die Deploy-Pipeline zu blockieren.
        if self.cookie_secure and self.seed_admin_passwort == self._SEED_ADMIN_PASSWORT_DEFAULT:
            self.seed_admin_passwort = secrets.token_urlsafe(18)
            print(
                "WARNUNG: HV_SEED_ADMIN_PASSWORT war nicht gesetzt — zufälliges "
                f"Admin-Passwort erzeugt: {self.seed_admin_passwort}\n"
                "Bitte notieren und HV_SEED_ADMIN_PASSWORT auf einen eigenen "
                "Wert setzen (dieses zufällige Passwort wird bei jedem Neustart "
                "neu erzeugt, aber nur beim allerersten Seed-Lauf tatsächlich "
                "verwendet)."
            )
        if self.cookie_secure and self.seed_user_passwort == self._SEED_USER_PASSWORT_DEFAULT:
            self.seed_user_passwort = secrets.token_urlsafe(18)
            print(
                "WARNUNG: HV_SEED_USER_PASSWORT war nicht gesetzt — zufälliges "
                f"User-Passwort erzeugt: {self.seed_user_passwort}\n"
                "Bitte notieren und HV_SEED_USER_PASSWORT auf einen eigenen "
                "Wert setzen (dieses zufällige Passwort wird bei jedem Neustart "
                "neu erzeugt, aber nur beim allerersten Seed-Lauf tatsächlich "
                "verwendet)."
            )
        return self


settings = Settings()
