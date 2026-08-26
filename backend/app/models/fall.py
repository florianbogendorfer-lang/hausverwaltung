"""DM-4 `faelle` — zentraler Geschäftsfall.

Zustände gemäß §4.1. Die Zustandsmaschine selbst (Übergänge, Aktions-
Auslösung) wird erst in Phase 2/3 implementiert — hier nur das Schema.
"""

import enum
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.models.dienstleister import Gewerk


class FallTyp(str, enum.Enum):
    reparaturmeldung = "reparaturmeldung"


class FallStatus(str, enum.Enum):
    neu = "NEU"
    eingeordnet = "EINGEORDNET"
    wartet_auf_freigabe = "WARTET_AUF_FREIGABE"
    dienstleister_beauftragt = "DIENSTLEISTER_BEAUFTRAGT"
    termin_bestaetigt = "TERMIN_BESTAETIGT"
    arbeit_erledigt = "ARBEIT_ERLEDIGT"
    rechnung_erfasst = "RECHNUNG_ERFASST"
    abgeschlossen = "ABGESCHLOSSEN"
    eskaliert = "ESKALIERT"
    abgebrochen = "ABGEBROCHEN"


class Fall(SQLModel, table=True):
    __tablename__ = "faelle"

    id: Optional[int] = Field(default=None, primary_key=True)
    typ: FallTyp
    gewerk: Optional[Gewerk] = None
    objekt_id: Optional[int] = Field(default=None, foreign_key="objekte.id")
    melder_kontakt_id: Optional[int] = Field(default=None, foreign_key="kontakte.id")
    dienstleister_id: Optional[int] = Field(default=None, foreign_key="dienstleister.id")
    status: FallStatus = FallStatus.neu
    betreff: str
    zusammenfassung: Optional[str] = None
    konfidenz: Optional[float] = None
    erstellt_am: datetime = Field(default_factory=datetime.utcnow)
    geaendert_am: datetime = Field(default_factory=datetime.utcnow)
