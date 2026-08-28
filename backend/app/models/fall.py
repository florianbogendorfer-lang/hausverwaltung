"""DM-4 `faelle` — zentraler Geschäftsfall.

Zustände gemäß §4.1. Die Zustandsmaschine selbst (Übergänge, Aktions-
Auslösung) wird erst in Phase 2/3 implementiert — hier nur das Schema.
"""

import enum
import secrets
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.models.dienstleister import Gewerk


def _ticket_nummer_erzeugen() -> str:
    """Kurze, für Menschen les-/nennbare Referenznummer (E-Mail-Betreff,
    Kundenansicht) — NICHT der Zugriffsschutz, siehe `zugriffstoken`."""
    return f"HV-{secrets.token_hex(4).upper()}"


def _zugriffstoken_erzeugen() -> str:
    """Eigenständiges Zugriffs-Token für die unauthentifizierte
    Kundenansicht (`GET /api/ticket/{token}`, kein Login im Prototyp,
    §0) — getrennt von der kurzen `ticket_nummer`, weil die als
    Referenznummer für Menschen lesbar/kurz bleiben soll, während ein
    Zugriffs-Token laut OWASP/W3C-Empfehlung für Capability-URLs
    mindestens ~120 Bit Entropie braucht (32 Bit reichen nicht, um
    Erraten/Durchprobieren praktisch auszuschließen). token_urlsafe(24)
    liefert 192 Bit."""
    return secrets.token_urlsafe(24)


def _dienstleister_zugriffstoken_erzeugen() -> str:
    """Eigenes Zugriffs-Token für die unauthentifizierte Dienstleister-
    Ansicht (`GET/POST /api/dienstleister-portal/{token}`) — getrennt vom
    Kunden-`zugriffstoken`: Dienstleister und Kunde sehen unterschiedliche
    Ausschnitte desselben Falls und dürfen unterschiedliche Aktionen
    auslösen (Termin bestätigen, Arbeit als erledigt melden), ein
    gemeinsames Token würde diese Grenze verwischen. Gleiche Entropie wie
    der Kunden-Token (siehe `_zugriffstoken_erzeugen`)."""
    return secrets.token_urlsafe(24)


class FallTyp(str, enum.Enum):
    reparaturmeldung = "reparaturmeldung"


class FallStatus(str, enum.Enum):
    neu = "NEU"
    eingeordnet = "EINGEORDNET"
    wartet_auf_freigabe = "WARTET_AUF_FREIGABE"
    dienstleister_beauftragt = "DIENSTLEISTER_BEAUFTRAGT"
    termin_bestaetigt = "TERMIN_BESTAETIGT"
    arbeit_erledigt = "ARBEIT_ERLEDIGT"
    rechnung_erfasst = "RECHNUNG_ERFASST"
    abgeschlossen = "ABGESCHLOSSEN"
    eskaliert = "ESKALIERT"
    abgebrochen = "ABGEBROCHEN"


class Fall(SQLModel, table=True):
    __tablename__ = "faelle"

    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_nummer: str = Field(default_factory=_ticket_nummer_erzeugen, unique=True, index=True)
    zugriffstoken: str = Field(default_factory=_zugriffstoken_erzeugen, unique=True, index=True)
    dienstleister_zugriffstoken: str = Field(
        default_factory=_dienstleister_zugriffstoken_erzeugen, unique=True, index=True
    )
    typ: FallTyp
    gewerk: Optional[Gewerk] = None
    objekt_id: Optional[int] = Field(default=None, foreign_key="objekte.id", index=True)
    melder_kontakt_id: Optional[int] = Field(default=None, foreign_key="kontakte.id", index=True)
    dienstleister_id: Optional[int] = Field(default=None, foreign_key="dienstleister.id", index=True)
    status: FallStatus = FallStatus.neu
    betreff: str
    # Vom Dienstleister über das Portal (`/dienstleister-portal/{token}`)
    # bestätigter Vor-Ort-Termin — bewusst kein separates Termin-Modell,
    # ein Fall hat im Prototyp höchstens einen aktiven Termin gleichzeitig.
    termin_am: Optional[datetime] = None
    zusammenfassung: Optional[str] = None
    konfidenz: Optional[float] = None
    erstellt_am: datetime = Field(default_factory=datetime.utcnow)
    geaendert_am: datetime = Field(default_factory=datetime.utcnow)
    geloescht: bool = False
    geloescht_am: Optional[datetime] = None
