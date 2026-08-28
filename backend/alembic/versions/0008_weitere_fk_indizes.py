"""Indizes auf Fall.objekt_id/melder_kontakt_id/dienstleister_id und
Kontakt.objekt_id.

Fortsetzung von 0007_fall_id_indizes — dieselbe Begründung gilt auch für
diese Fremdschlüsselspalten: sie werden in den referentiellen-Integritäts-
Prüfungen beim Löschen (objekt_loeschen/kontakt_loeschen/
dienstleister_loeschen) sowie bei der Kontakt-Objekt-Validierung
gefiltert.

Revision ID: 0008_weitere_fk_indizes
Revises: 0007_fall_id_indizes
Create Date: 2026-08-28

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008_weitere_fk_indizes"
down_revision: Union[str, None] = "0007_fall_id_indizes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_faelle_objekt_id", "faelle", ["objekt_id"])
    op.create_index("ix_faelle_melder_kontakt_id", "faelle", ["melder_kontakt_id"])
    op.create_index("ix_faelle_dienstleister_id", "faelle", ["dienstleister_id"])
    op.create_index("ix_kontakte_objekt_id", "kontakte", ["objekt_id"])


def downgrade() -> None:
    op.drop_index("ix_kontakte_objekt_id", table_name="kontakte")
    op.drop_index("ix_faelle_dienstleister_id", table_name="faelle")
    op.drop_index("ix_faelle_melder_kontakt_id", table_name="faelle")
    op.drop_index("ix_faelle_objekt_id", table_name="faelle")
