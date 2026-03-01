"""add_plan_date_columns_to_clienti_version

Revision ID: c1a8e7d9f244
Revises: 9e4c2f5b8a11
Create Date: 2026-02-13

Fix post-migrazione: aggiunge i campi date piano anche alla tabella
versionata `clienti_version` (SQLAlchemy-Continuum).
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c1a8e7d9f244"
down_revision = "9e4c2f5b8a11"
branch_labels = None
depends_on = None


PLAN_DATE_COLUMNS = (
    ("data_inizio_nutrizione", sa.Date()),
    ("data_scadenza_nutrizione", sa.Date()),
    ("data_inizio_coach", sa.Date()),
    ("data_scadenza_coach", sa.Date()),
    ("data_inizio_psicologia", sa.Date()),
    ("data_scadenza_psicologia", sa.Date()),
)


def _existing_columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if table_name not in tables:
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade():
    existing = _existing_columns("clienti_version")
    if not existing:
        return

    for name, coltype in PLAN_DATE_COLUMNS:
        if name not in existing:
            op.add_column("clienti_version", sa.Column(name, coltype, nullable=True))


def downgrade():
    existing = _existing_columns("clienti_version")
    if not existing:
        return

    for name, _ in reversed(PLAN_DATE_COLUMNS):
        if name in existing:
            op.drop_column("clienti_version", name)

