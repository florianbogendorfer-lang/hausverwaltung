"""initial schema — Datenmodell §7 (DM-1 bis DM-9)

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "objekte",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bezeichnung", sa.String(), nullable=False),
        sa.Column("adresse", sa.String(), nullable=False),
        sa.Column("einheit", sa.String(), nullable=True),
        sa.Column("notizen", sa.String(), nullable=True),
    )

    op.create_table(
        "kontakte",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("rolle", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("telefon", sa.String(), nullable=True),
        sa.Column("objekt_id", sa.Integer(), sa.ForeignKey("objekte.id"), nullable=True),
    )

    op.create_table(
        "dienstleister",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("gewerk", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("telefon", sa.String(), nullable=True),
        sa.Column("konditionen", sa.String(), nullable=True),
        sa.Column("aktiv", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "faelle",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("typ", sa.String(), nullable=False),
        sa.Column("gewerk", sa.String(), nullable=True),
        sa.Column("objekt_id", sa.Integer(), sa.ForeignKey("objekte.id"), nullable=True),
        sa.Column("melder_kontakt_id", sa.Integer(), sa.ForeignKey("kontakte.id"), nullable=True),
        sa.Column(
            "dienstleister_id", sa.Integer(), sa.ForeignKey("dienstleister.id"), nullable=True
        ),
        sa.Column("status", sa.String(), nullable=False, server_default="NEU"),
        sa.Column("betreff", sa.String(), nullable=False),
        sa.Column("zusammenfassung", sa.String(), nullable=True),
        sa.Column("konfidenz", sa.Float(), nullable=True),
        sa.Column("erstellt_am", sa.DateTime(), nullable=False),
        sa.Column("geaendert_am", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "nachrichten",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fall_id", sa.Integer(), sa.ForeignKey("faelle.id"), nullable=False),
        sa.Column("richtung", sa.String(), nullable=False),
        sa.Column("kanal", sa.String(), nullable=False, server_default="email"),
        sa.Column("von", sa.String(), nullable=False),
        sa.Column("an", sa.String(), nullable=False),
        sa.Column("betreff", sa.String(), nullable=False),
        sa.Column("inhalt", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("erstellt_am", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "freigaben",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fall_id", sa.Integer(), sa.ForeignKey("faelle.id"), nullable=False),
        sa.Column("aktionstyp", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("begruendung", sa.String(), nullable=False),
        sa.Column("kontext_referenzen", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="offen"),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("entscheider", sa.String(), nullable=True),
        sa.Column("entscheidung_am", sa.DateTime(), nullable=True),
        sa.Column("ablehnungsgrund", sa.String(), nullable=True),
        sa.Column("erstellt_am", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_freigaben_idempotency_key", "freigaben", ["idempotency_key"], unique=True
    )

    op.create_table(
        "aktionen",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fall_id", sa.Integer(), sa.ForeignKey("faelle.id"), nullable=False),
        sa.Column("zeitstempel", sa.DateTime(), nullable=False),
        sa.Column("akteur", sa.String(), nullable=False),
        sa.Column("aktionsart", sa.String(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("freigabe_id", sa.Integer(), sa.ForeignKey("freigaben.id"), nullable=True),
    )

    op.create_table(
        "traces",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fall_id", sa.Integer(), sa.ForeignKey("faelle.id"), nullable=False),
        sa.Column("schritt_nr", sa.Integer(), nullable=False),
        sa.Column("phase", sa.String(), nullable=False),
        sa.Column("modell", sa.String(), nullable=True),
        sa.Column("inhalt", sa.String(), nullable=False),
        sa.Column("token_kosten", sa.Integer(), nullable=True),
        sa.Column("dauer_ms", sa.Integer(), nullable=True),
        sa.Column("zeitstempel", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "dokumente",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("titel", sa.String(), nullable=False),
        sa.Column("quelle", sa.String(), nullable=False),
        sa.Column("inhalt", sa.String(), nullable=False),
        sa.Column("metadaten", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("dokumente")
    op.drop_table("traces")
    op.drop_table("aktionen")
    op.drop_index("ix_freigaben_idempotency_key", table_name="freigaben")
    op.drop_table("freigaben")
    op.drop_table("nachrichten")
    op.drop_table("faelle")
    op.drop_table("dienstleister")
    op.drop_table("kontakte")
    op.drop_table("objekte")
