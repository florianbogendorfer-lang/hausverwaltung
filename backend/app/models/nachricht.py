"""DM-5 `nachrichten` — ein-/ausgehende Kommunikation zu einem Fall."""

import enum
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class NachrichtRichtung(str, enum.Enum):
    eingehend = "eingehend"
    ausgehend = "ausgehend"


class Kanal(str, enum.Enum):
    email = "email"


class NachrichtStatus(str, enum.Enum):
    empfangen = "empfangen"
    entwurf = "entwurf"
    freigegeben = "freigegeben"
    gesendet_simuliert = "gesendet_simuliert"
    abgelehnt = "abgelehnt"


class Nachricht(SQLModel, table=True):
    __tablename__ = "nachrichten"

    id: Optional[int] = Field(default=None, primary_key=True)
    fall_id: int = Field(foreign_key="faelle.id")
    richtung: NachrichtRichtung
    kanal: Kanal = Kanal.email
    von: str
    an: str
    betreff: str
    inhalt: str
    status: NachrichtStatus
    erstellt_am: datetime = Field(default_factory=datetime.utcnow)
