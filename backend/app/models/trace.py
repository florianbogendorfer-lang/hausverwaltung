"""DM-8 `traces` — Denk-/Schritt-Protokoll pro Loop-Durchlauf (§8, §11)."""

import enum
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class TracePhase(str, enum.Enum):
    wahrnehmung = "wahrnehmung"
    plan = "plan"
    tool_call = "tool_call"
    tool_result = "tool_result"
    entscheidung = "entscheidung"
    reasoning = "reasoning"


class Trace(SQLModel, table=True):
    __tablename__ = "traces"

    id: Optional[int] = Field(default=None, primary_key=True)
    fall_id: int = Field(foreign_key="faelle.id", index=True)
    schritt_nr: int
    phase: TracePhase
    modell: Optional[str] = None
    inhalt: str
    token_kosten: Optional[int] = None
    dauer_ms: Optional[int] = None
    zeitstempel: datetime = Field(default_factory=datetime.utcnow)
