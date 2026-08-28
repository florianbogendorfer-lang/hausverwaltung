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
    # §16 Phase 6: echter Versand über einen konfigurierten SMTP-Adapter
    # (app.agent.mail_adapter.SmtpMailAdapter) — per Default inaktiv, siehe
    # dort. Unterscheidet sich bewusst von gesendet_simuliert, damit das
    # Audit-Log (§11) erkennen lässt, ob wirklich etwas rausging.
    gesendet = "gesendet"
    # Ein SMTP-Fehler (Netzwerk, ungültiger Empfänger, o. Ä.) darf die
    # bereits atomar reservierte Freigabe-Entscheidung nicht spurlos
    # verschlucken (siehe app.agent.freigabe_service.freigeben) — dieser
    # Status macht sichtbar, dass die Freigabe zwar entschieden ist, der
    # eigentliche Versand aber fehlgeschlagen ist und manuell nachverfolgt
    # werden muss.
    versand_fehlgeschlagen = "versand_fehlgeschlagen"


class Nachricht(SQLModel, table=True):
    __tablename__ = "nachrichten"

    id: Optional[int] = Field(default=None, primary_key=True)
    fall_id: int = Field(foreign_key="faelle.id", index=True)
    richtung: NachrichtRichtung
    kanal: Kanal = Kanal.email
    von: str
    an: str
    betreff: str
    inhalt: str
    status: NachrichtStatus
    erstellt_am: datetime = Field(default_factory=datetime.utcnow)
