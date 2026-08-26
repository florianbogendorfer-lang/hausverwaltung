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

    # FR-AGENT-2 — Modell-Routing: günstig für Klassifikation/Extraktion,
    # stark für Kundentexte/Planung. Austauschbar, siehe §12.
    modell_guenstig: str = "claude-haiku-4-5"
    modell_stark: str = "claude-sonnet-5"

    # FR-HITL-6 / FR-AGENT-4 — unterhalb dieser Konfidenz wird eskaliert
    # statt geraten.
    konfidenz_schwelle: float = 0.6

    # FR-HITL-7 — offene Freigaben werden ab dieser Frist als überfällig
    # markiert (keine Auto-Ausführung, nur Anzeige).
    freigabe_timeout_stunden: int = 24

    # §16 Phase 5 — Vektorspeicher für dokumente_durchsuchen, getrennt von
    # der relationalen DB (§6), damit er unabhängig von SQLite/Postgres ist.
    chroma_persist_dir: str = "./chroma_data"


settings = Settings()
