"""Bestehende Benutzer.email-Werte auf Kleinschreibung normalisieren.

Login/Benutzer-Anlegen behandeln E-Mail-Adressen jetzt case-insensitiv
(neue Konten werden bereits normalisiert gespeichert, siehe
app/routers/benutzer.py) — ohne diese Migration könnte ein VOR diesem
Fix mit gemischter Groß-/Kleinschreibung angelegtes Konto sich plötzlich
nicht mehr einloggen können (Vergleich normalisiert die Eingabe, die
gespeicherte Zeile aber nicht).

Revision ID: 0006_email_lowercase
Revises: 0005_zugriffstoken
Create Date: 2026-08-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0006_email_lowercase"
down_revision: Union[str, None] = "0005_zugriffstoken"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text("UPDATE benutzer SET email = lower(email)"))


def downgrade() -> None:
    # Nicht umkehrbar (die ursprüngliche Groß-/Kleinschreibung ist nach
    # dem Upgrade nicht mehr bekannt) — bewusst ein No-op statt eines
    # irreführenden "downgrade", das nichts wirklich rückgängig macht.
    pass
