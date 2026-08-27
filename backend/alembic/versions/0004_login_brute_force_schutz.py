"""Brute-Force-Schutz für den Login (Fehlversuchszähler + temporäre Sperre)

Revision ID: 0004_login_brute_force_schutz
Revises: 0003_benutzer_und_softdelete
Create Date: 2026-08-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004_login_brute_force_schutz"
down_revision: Union[str, None] = "0003_benutzer_und_softdelete"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "benutzer", sa.Column("fehlversuche", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column("benutzer", sa.Column("gesperrt_bis", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("benutzer", "gesperrt_bis")
    op.drop_column("benutzer", "fehlversuche")
