"""Benutzer/Sitzungen (Rollen-Login) + Soft-Delete für faelle

Revision ID: 0003_benutzer_und_softdelete
Revises: 0002_ticket_nummer
Create Date: 2026-08-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003_benutzer_und_softdelete"
down_revision: Union[str, None] = "0002_ticket_nummer"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "benutzer",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("passwort_hash", sa.String(), nullable=False),
        sa.Column("rolle", sa.String(), nullable=False, server_default="user"),
        sa.Column("erstellt_am", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_benutzer_email", "benutzer", ["email"], unique=True)

    op.create_table(
        "sitzungen",
        sa.Column("token", sa.String(), primary_key=True),
        sa.Column("benutzer_id", sa.Integer(), sa.ForeignKey("benutzer.id"), nullable=False),
        sa.Column("erstellt_am", sa.DateTime(), nullable=False),
        sa.Column("laeuft_ab_am", sa.DateTime(), nullable=False),
    )

    op.add_column(
        "faelle", sa.Column("geloescht", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.add_column("faelle", sa.Column("geloescht_am", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("faelle", "geloescht_am")
    op.drop_column("faelle", "geloescht")
    op.drop_table("sitzungen")
    op.drop_index("ix_benutzer_email", table_name="benutzer")
    op.drop_table("benutzer")
