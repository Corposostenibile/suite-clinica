"""add_durata_giorni_to_clienti_version

Revision ID: cb04_add_durata_clienti_ver
Revises: cb03_hm_team_type
Create Date: 2026-02-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "cb04_add_durata_clienti_ver"
down_revision = "cb03_hm_team_type"
branch_labels = None
depends_on = None


def _existing_columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    insp = inspect(bind)
    return {c["name"] for c in insp.get_columns(table_name)}


def upgrade():
    existing = _existing_columns("clienti_version")
    if "durata_nutrizione_giorni" not in existing:
        op.add_column(
            "clienti_version",
            sa.Column("durata_nutrizione_giorni", sa.Integer(), nullable=True),
        )
    if "durata_coach_giorni" not in existing:
        op.add_column(
            "clienti_version",
            sa.Column("durata_coach_giorni", sa.Integer(), nullable=True),
        )
    if "durata_psicologia_giorni" not in existing:
        op.add_column(
            "clienti_version",
            sa.Column("durata_psicologia_giorni", sa.Integer(), nullable=True),
        )


def downgrade():
    existing = _existing_columns("clienti_version")
    if "durata_psicologia_giorni" in existing:
        op.drop_column("clienti_version", "durata_psicologia_giorni")
    if "durata_coach_giorni" in existing:
        op.drop_column("clienti_version", "durata_coach_giorni")
    if "durata_nutrizione_giorni" in existing:
        op.drop_column("clienti_version", "durata_nutrizione_giorni")

