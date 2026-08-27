"""Eigenständiges hochentropisches Zugriffs-Token für die Kundenansicht,
getrennt von der kurzen, für Menschen lesbaren Ticketnummer (32 Bit
Entropie reichten laut OWASP/W3C nicht für eine Capability-URL).

Revision ID: 0005_zugriffstoken
Revises: 0004_login_brute_force_schutz
Create Date: 2026-08-27

"""
import secrets
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0005_zugriffstoken"
down_revision: Union[str, None] = "0004_login_brute_force_schutz"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

faelle = sa.table("faelle", sa.column("id", sa.Integer), sa.column("zugriffstoken", sa.String))


def upgrade() -> None:
    op.add_column("faelle", sa.Column("zugriffstoken", sa.String(), nullable=True))

    connection = op.get_bind()
    ids = [row[0] for row in connection.execute(sa.select(faelle.c.id))]
    vergeben: set[str] = set()
    for fall_id in ids:
        token = secrets.token_urlsafe(24)
        while token in vergeben:
            token = secrets.token_urlsafe(24)
        vergeben.add(token)
        connection.execute(
            faelle.update().where(faelle.c.id == fall_id).values(zugriffstoken=token)
        )

    with op.batch_alter_table("faelle") as batch_op:
        batch_op.alter_column("zugriffstoken", nullable=False)
    op.create_index("ix_faelle_zugriffstoken", "faelle", ["zugriffstoken"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_faelle_zugriffstoken", table_name="faelle")
    op.drop_column("faelle", "zugriffstoken")
