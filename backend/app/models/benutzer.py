"""DM-10 `benutzer`/`sitzungen` — einfaches Rollen-Login (§0: Prototyp,
daher Passwort-Login mit serverseitiger Session statt eines externen
Auth-Providers). Zwei Rollen: `admin` darf Fälle (soft-)löschen, `user`
darf alles andere (Fälle bearbeiten, Freigaben entscheiden) außer löschen.
"""

import enum
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class BenutzerRolle(str, enum.Enum):
    admin = "admin"
    user = "user"


class Benutzer(SQLModel, table=True):
    __tablename__ = "benutzer"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(unique=True, index=True)
    passwort_hash: str
    rolle: BenutzerRolle = BenutzerRolle.user
    erstellt_am: datetime = Field(default_factory=datetime.utcnow)
    # Brute-Force-Schutz (OWASP Authentication Cheat Sheet): Zähler +
    # temporäre, exponentiell wachsende Sperre statt permanenter Sperre
    # (die selbst zum DoS-Vektor würde) — siehe app/auth.py.
    fehlversuche: int = 0
    gesperrt_bis: Optional[datetime] = None


class Sitzung(SQLModel, table=True):
    """Serverseitige Session — der Cookie trägt nur das Token, nicht die
    Nutzerdaten. Löschen der Zeile (Logout) entzieht sofort den Zugriff,
    ohne auf Cookie-Ablauf beim Client angewiesen zu sein."""

    __tablename__ = "sitzungen"

    token: str = Field(primary_key=True)
    benutzer_id: int = Field(foreign_key="benutzer.id")
    erstellt_am: datetime = Field(default_factory=datetime.utcnow)
    laeuft_ab_am: datetime
