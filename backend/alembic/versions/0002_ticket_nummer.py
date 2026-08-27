"""ticket_nummer für faelle — Kundenansicht (§0 Kundenwunsch)

Revision ID: 0002_ticket_nummer
Revises: 0001_initial
Create Date: 2026-08-27

"""
import secrets
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002_ticket_nummer"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

faelle = sa.table("faelle", sa.column("id", sa.Integer), sa.column("ticket_nummer", sa.String))


def _neue_ticket_nummer(vergeben: set[str]) -> str:
    nummer = f"HV-{secrets.token_hex(4).upper()}"
    while nummer in vergeben:
        nummer = f"HV-{secrets.token_hex(4).upper()}"
    vergeben.add(nummer)
    return nummer


def upgrade() -> None:
    op.add_column("faelle", sa.Column("ticket_nummer", sa.String(), nullable=True))

    connection = op.get_bind()
    ids = [row[0] for row in connection.execute(sa.select(faelle.c.id))]
    vergeben: set[str] = set()
    for fall_id in ids:
        nummer = _neue_ticket_nummer(vergeben)
        connection.execute(
            faelle.update().where(faelle.c.id == fall_id).values(ticket_nummer=nummer)
        )

    with op.batch_alter_table("faelle") as batch_op:
        batch_op.alter_column("ticket_nummer", nullable=False)
    op.create_index("ix_faelle_ticket_nummer", "faelle", ["ticket_nummer"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_faelle_ticket_nummer", table_name="faelle")
    op.drop_column("faelle", "ticket_nummer")
