"""DM-3 `dienstleister` — Schlosser, Maurer, Installateur etc."""

import enum
from typing import Optional

from sqlmodel import Field, SQLModel


class Gewerk(str, enum.Enum):
    schlosser = "schlosser"
    maurer = "maurer"
    installateur = "installateur"
    elektriker = "elektriker"
    sonstiges = "sonstiges"


class Dienstleister(SQLModel, table=True):
    __tablename__ = "dienstleister"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    gewerk: Gewerk
    email: str
    telefon: Optional[str] = None
    konditionen: Optional[str] = None
    aktiv: bool = True
