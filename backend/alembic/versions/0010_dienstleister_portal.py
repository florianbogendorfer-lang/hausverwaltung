"""Dienstleister-Selbstbedienungsportal: eigenes hochentropisches
Zugriffs-Token je Fall (getrennt vom Kunden-`zugriffstoken`, siehe
0005_zugriffstoken) sowie ein Feld für den vom Dienstleister bestätigten
Termin — Grundlage für ein strukturiertes, login-freies Terminportal
statt Termine per Freitext-Mail-Antwort parsen zu müssen.

Revision ID: 0010_dienstleister_portal
Revises: 0009_sitzungen_indizes
Create Date: 2026-08-28

"""
import secrets
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0010_dienstleister_portal"
down_revision: Union[str, None] = "0009_sitzungen_indizes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

faelle = sa.table(
    "faelle", sa.column("id", sa.Integer), sa.column("dienstleister_zugriffstoken", sa.String)
)


def upgrade() -> None:
    op.add_column("faelle", sa.Column("dienstleister_zugriffstoken", sa.String(), nullable=True))
    op.add_column("faelle", sa.Column("termin_am", sa.DateTime(), nullable=True))

    connection = op.get_bind()
    ids = [row[0] for row in connection.execute(sa.select(faelle.c.id))]
    vergeben: set[str] = set()
    for fall_id in ids:
        token = secrets.token_urlsafe(24)
        while token in vergeben:
            token = secrets.token_urlsafe(24)
        vergeben.add(token)
        connection.execute(
            faelle.update().where(faelle.c.id == fall_id).values(dienstleister_zugriffstoken=token)
        )

    with op.batch_alter_table("faelle") as batch_op:
        batch_op.alter_column("dienstleister_zugriffstoken", nullable=False)
    op.create_index(
        "ix_faelle_dienstleister_zugriffstoken", "faelle", ["dienstleister_zugriffstoken"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_faelle_dienstleister_zugriffstoken", table_name="faelle")
    op.drop_column("faelle", "termin_am")
    op.drop_column("faelle", "dienstleister_zugriffstoken")
