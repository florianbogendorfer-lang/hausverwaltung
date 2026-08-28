"""Strukturierte Ein-/Ausgaben des Agenten (FR-AGENT-3)."""

from typing import Optional

from pydantic import BaseModel, Field

from app.models.dienstleister import Gewerk
from app.models.fall import FallTyp


class EingehendeMail(BaseModel):
    # Obergrenzen nach OWASP Input Validation Cheat Sheet (jede Eingabe
    # längenbegrenzen) — verhindert, dass ein einzelner Eingang unbegrenzt
    # LLM-Tokenkosten verursacht oder die DB mit übergroßen Texten flutet.
    von: str = Field(max_length=320)  # RFC 5321 max. Mailadressenlänge
    betreff: str = Field(max_length=500)
    inhalt: str = Field(max_length=20_000)


class Einordnung(BaseModel):
    """Ausgabe von Tool `fall_einordnen`."""

    typ: FallTyp
    gewerk: Optional[Gewerk] = None
    objekt_suchbegriff: Optional[str] = None
    melder_suchbegriff: Optional[str] = None
    konfidenz: float = Field(ge=0.0, le=1.0)
    begruendung: str
