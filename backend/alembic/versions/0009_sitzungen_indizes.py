"""Indizes auf sitzungen.benutzer_id und sitzungen.laeuft_ab_am.

Fortsetzung von 0007/0008 — laeuft_ab_am wird bei jedem Login per
WHERE laeuft_ab_am < ... gefiltert (Aufräum-Mechanismus für abgelaufene
Sitzungen, siehe app/auth.py::sitzung_anlegen), benutzer_id beim
Benutzer-Löschen (app/routers/benutzer.py::loeschen).

Revision ID: 0009_sitzungen_indizes
Revises: 0008_weitere_fk_indizes
Create Date: 2026-08-28

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009_sitzungen_indizes"
down_revision: Union[str, None] = "0008_weitere_fk_indizes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_sitzungen_benutzer_id", "sitzungen", ["benutzer_id"])
    op.create_index("ix_sitzungen_laeuft_ab_am", "sitzungen", ["laeuft_ab_am"])


def downgrade() -> None:
    op.drop_index("ix_sitzungen_laeuft_ab_am", table_name="sitzungen")
    op.drop_index("ix_sitzungen_benutzer_id", table_name="sitzungen")
