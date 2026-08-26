"""DM-9 `dokumente` — RAG-Quellen (Metadaten; Embeddings folgen in Phase 5).

In Phase 1 wird der Volltext direkt im Feld `inhalt` gehalten (kein
Vektorspeicher), damit Dokumente bereits über die Stammdaten-API lesbar
sind. Der Vektorspeicher/Embedding-Anbindung ist §16 Phase 5.
"""

from typing import Optional

from sqlmodel import Field, SQLModel
from sqlalchemy import JSON, Column


class Dokument(SQLModel, table=True):
    __tablename__ = "dokumente"

    id: Optional[int] = Field(default=None, primary_key=True)
    titel: str
    quelle: str
    inhalt: str
    metadaten: dict = Field(default_factory=dict, sa_column=Column(JSON))
