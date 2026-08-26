"""Zentrale Konfiguration.

NFR-5 / §12: Modell-/Provider-Konfiguration gehört hierher, nicht in Prompts.
In Phase 1 nur Datenbank-Settings; Modell-Routing-Konfiguration folgt in Phase 2.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HV_")

    database_url: str = "sqlite:///./hausverwaltung.db"


settings = Settings()
