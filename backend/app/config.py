"""Zentrale Konfiguration.

NFR-5 / §12: Modell-/Provider-Konfiguration gehört hierher, nicht in Prompts.
Modell-IDs sind austauschbar (Provider-Wechsel Anthropic-API → Bedrock EU
per Konfiguration, siehe §12/§13) — daher hier und nicht im Code verdrahtet.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HV_")

    database_url: str = "sqlite:///./hausverwaltung.db"

    anthropic_api_key: str | None = None
    mistral_api_key: str | None = None

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

    # Session-Cookie nur über HTTPS versenden (OWASP Session Management).
    # Default False, damit lokales `uvicorn --reload` über http://
    # weiterhin funktioniert (Browser verwerfen Secure-Cookies ohne TLS
    # stillschweigend); docker-entrypoint.sh setzt dies im Deploy-Pfad
    # automatisch auf True, ohne dass eine manuelle Konfiguration nötig ist.
    cookie_secure: bool = False


settings = Settings()
