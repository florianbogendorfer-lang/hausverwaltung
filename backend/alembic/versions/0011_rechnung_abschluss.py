"""Rechnungsdaten am Fall + Abschluss-Workflow: der Dienstleister reicht
über das Portal (`/dienstleister-portal/{token}/rechnung`, Status
ARBEIT_ERLEDIGT -> RECHNUNG_ERFASST) Betrag und optional eine
Rechnungsnummer ein. Vorher gab es dafür keinen Codepfad — ein Fall blieb
nach "Arbeit erledigt" dauerhaft in diesem Status stecken, weil weder ein
automatischer noch ein manueller Übergang zu RECHNUNG_ERFASST/
ABGESCHLOSSEN existierte.

Revision ID: 0011_rechnung_abschluss
Revises: 0010_dienstleister_portal
Create Date: 2026-08-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0011_rechnung_abschluss"
down_revision: Union[str, None] = "0010_dienstleister_portal"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("faelle", sa.Column("rechnung_betrag", sa.Float(), nullable=True))
    op.add_column("faelle", sa.Column("rechnung_nummer", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("faelle", "rechnung_nummer")
    op.drop_column("faelle", "rechnung_betrag")
