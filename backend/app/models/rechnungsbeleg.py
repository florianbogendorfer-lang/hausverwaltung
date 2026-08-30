"""Optionaler Datei-Anhang zur Rechnung, die ein Dienstleister über das
Terminportal einreicht (`POST /dienstleister-portal/{token}/rechnung`,
siehe app/routers/dienstleister_portal.py). Bewusst als eigene, schlanke
Tabelle statt einer Erweiterung von `Dokument` (DM-9) — `Dokument` ist eine
RAG-Textquelle für `dokumente_durchsuchen`, keine Datei-Ablage; ein
Rechnungsbeleg ist eine reine Binärdatei ohne inhaltliche Volltextsuche.

Die Datei wird direkt als Bytes in der Datenbank gespeichert statt auf dem
Dateisystem: der Docker-Container läuft ohne persistentes Volume (siehe
README, Production-Readiness), ein lokal abgelegter Beleg wäre nach jedem
Neustart/Redeploy verloren. Für die erwartete Größenordnung (einzelne
Rechnungs-PDFs/-Fotos, siehe MAX_BELEG_GROESSE_BYTES) ist das unproblematisch;
bei deutlich höherem Volumen wäre ein externer Objektspeicher (z. B. Clever
Cloud Cellar) der nächste Schritt."""

from datetime import datetime
from typing import Optional

from sqlalchemy import LargeBinary
from sqlmodel import Column, Field, SQLModel

# OWASP API4:2023 (Unrestricted Resource Consumption): Obergrenze für
# Rechnungsbelege — großzügig für ein gescanntes/fotografiertes
# Rechnungs-PDF, aber begrenzt genug, um die DB nicht mit beliebig großen
# Uploads zu fluten. Der globale Body-Size-Limit in app/main.py ist auf
# denselben Wert abgestimmt (siehe dort).
MAX_BELEG_GROESSE_BYTES = 8 * 1024 * 1024

# Bewusst kein PDF-only: Dienstleister fotografieren Rechnungen häufig
# einfach mit dem Handy statt sie einzuscannen.
ERLAUBTE_BELEG_CONTENT_TYPES = {"application/pdf", "image/jpeg", "image/png"}


class Rechnungsbeleg(SQLModel, table=True):
    __tablename__ = "rechnungsbelege"

    id: Optional[int] = Field(default=None, primary_key=True)
    fall_id: int = Field(foreign_key="faelle.id", index=True)
    dateiname: str
    content_type: str
    groesse_bytes: int
    inhalt: bytes = Field(sa_column=Column(LargeBinary))
    hochgeladen_am: datetime = Field(default_factory=datetime.utcnow)
