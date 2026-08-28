"""DM-7 `aktionen` — Audit-Log, append-only (NFR-LOG-2).

Es gibt bewusst keine Update-/Delete-Operationen für diese Tabelle in der
Anwendungsschicht — Einträge werden nur angehängt.
"""

import enum
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel
from sqlalchemy import JSON, Column


class Akteur(str, enum.Enum):
    agent = "agent"
    operator = "operator"
    system = "system"
    # Externer Dienstleister über das login-freie Terminportal
    # (`/dienstleister-portal/{token}`) — kein Systemnutzer, daher ein
    # eigener Akteur statt operator/agent.
    dienstleister = "dienstleister"


class Aktion(SQLModel, table=True):
    __tablename__ = "aktionen"

    id: Optional[int] = Field(default=None, primary_key=True)
    fall_id: int = Field(foreign_key="faelle.id", index=True)
    zeitstempel: datetime = Field(default_factory=datetime.utcnow)
    akteur: Akteur
    aktionsart: str
    details: dict = Field(default_factory=dict, sa_column=Column(JSON))
    freigabe_id: Optional[int] = Field(default=None, foreign_key="freigaben.id")
