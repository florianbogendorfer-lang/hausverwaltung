"""DM-2 `kontakte` — Mieter/Eigentümer."""

import enum
from typing import Optional

from sqlmodel import Field, SQLModel


class KontaktRolle(str, enum.Enum):
    mieter = "mieter"
    eigentuemer = "eigentümer"


class Kontakt(SQLModel, table=True):
    __tablename__ = "kontakte"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    rolle: KontaktRolle
    email: str
    telefon: Optional[str] = None
    objekt_id: Optional[int] = Field(default=None, foreign_key="objekte.id")
