"""DM-6 `freigaben` — propose store, Herzstück des HITL-Konzepts (§5).

FR-HITL-1: Aktionen werden hier als Payload persistiert, bevor irgendetwas
ausgeführt wird. Die eigentliche Ausführungslogik folgt in Phase 3.
"""

import enum
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel
from sqlalchemy import JSON, Column


class Aktionstyp(str, enum.Enum):
    nachricht_senden = "nachricht_senden"
    dienstleister_beauftragen = "dienstleister_beauftragen"
    rechnung_erfassen = "rechnung_erfassen"


class FreigabeStatus(str, enum.Enum):
    offen = "offen"
    freigegeben = "freigegeben"
    bearbeitet_freigegeben = "bearbeitet_freigegeben"
    abgelehnt = "abgelehnt"


class Freigabe(SQLModel, table=True):
    __tablename__ = "freigaben"

    id: Optional[int] = Field(default=None, primary_key=True)
    fall_id: int = Field(foreign_key="faelle.id", index=True)
    aktionstyp: Aktionstyp
    payload: dict = Field(sa_column=Column(JSON))
    begruendung: str
    kontext_referenzen: dict = Field(default_factory=dict, sa_column=Column(JSON))
    status: FreigabeStatus = FreigabeStatus.offen
    idempotency_key: str = Field(unique=True, index=True)
    entscheider: Optional[str] = None
    entscheidung_am: Optional[datetime] = None
    ablehnungsgrund: Optional[str] = None
    erstellt_am: datetime = Field(default_factory=datetime.utcnow)
