"""Indizes auf fall_id (traces, aktionen, nachrichten, freigaben).

Alle vier Tabellen werden regelmäßig mit `WHERE fall_id = X` abgefragt
(Fall-Detail-Ansicht: Trace-Timeline, Audit-Log, Nachrichtenverlauf,
offene Freigabe) — ohne Index läuft das ab einer gewissen Datenmenge auf
einen vollen Tabellenscan hinaus. Für den aktuellen Prototyp-Datenumfang
unkritisch, aber ein Standard-Best-Practice für Fremdschlüsselspalten in
Filterbedingungen.

Revision ID: 0007_fall_id_indizes
Revises: 0006_email_lowercase
Create Date: 2026-08-28

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007_fall_id_indizes"
down_revision: Union[str, None] = "0006_email_lowercase"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_traces_fall_id", "traces", ["fall_id"])
    op.create_index("ix_aktionen_fall_id", "aktionen", ["fall_id"])
    op.create_index("ix_nachrichten_fall_id", "nachrichten", ["fall_id"])
    op.create_index("ix_freigaben_fall_id", "freigaben", ["fall_id"])


def downgrade() -> None:
    op.drop_index("ix_freigaben_fall_id", table_name="freigaben")
    op.drop_index("ix_nachrichten_fall_id", table_name="nachrichten")
    op.drop_index("ix_aktionen_fall_id", table_name="aktionen")
    op.drop_index("ix_traces_fall_id", table_name="traces")
