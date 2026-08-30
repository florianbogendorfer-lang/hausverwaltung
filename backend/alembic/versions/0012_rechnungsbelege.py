"""Neue Tabelle rechnungsbelege: optionaler Datei-Anhang (PDF/Foto) zur
Rechnung, die ein Dienstleister über das Terminportal einreicht — siehe
app/models/rechnungsbeleg.py für die Begründung, warum die Datei direkt
als Bytes in der DB liegt statt auf dem Dateisystem.

Revision ID: 0012_rechnungsbelege
Revises: 0011_rechnung_abschluss
Create Date: 2026-08-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0012_rechnungsbelege"
down_revision: Union[str, None] = "0011_rechnung_abschluss"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rechnungsbelege",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fall_id", sa.Integer(), sa.ForeignKey("faelle.id"), nullable=False),
        sa.Column("dateiname", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("groesse_bytes", sa.Integer(), nullable=False),
        sa.Column("inhalt", sa.LargeBinary(), nullable=False),
        sa.Column("hochgeladen_am", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_rechnungsbelege_fall_id", "rechnungsbelege", ["fall_id"])


def downgrade() -> None:
    op.drop_index("ix_rechnungsbelege_fall_id", table_name="rechnungsbelege")
    op.drop_table("rechnungsbelege")
