"""Strukturierte Ein-/Ausgaben des Agenten (FR-AGENT-3)."""

from typing import Optional

from pydantic import BaseModel, Field

from app.models.dienstleister import Gewerk
from app.models.fall import FallTyp


class EingehendeMail(BaseModel):
    von: str
    betreff: str
    inhalt: str


class Einordnung(BaseModel):
    """Ausgabe von Tool `fall_einordnen`."""

    typ: FallTyp
    gewerk: Optional[Gewerk] = None
    objekt_suchbegriff: Optional[str] = None
    melder_suchbegriff: Optional[str] = None
    konfidenz: float = Field(ge=0.0, le=1.0)
    begruendung: str
