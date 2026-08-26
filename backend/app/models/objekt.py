"""DM-1 `objekte` — Liegenschaften/Einheiten."""

from typing import Optional

from sqlmodel import Field, SQLModel


class Objekt(SQLModel, table=True):
    __tablename__ = "objekte"

    id: Optional[int] = Field(default=None, primary_key=True)
    bezeichnung: str
    adresse: str
    einheit: Optional[str] = None
    notizen: Optional[str] = None
