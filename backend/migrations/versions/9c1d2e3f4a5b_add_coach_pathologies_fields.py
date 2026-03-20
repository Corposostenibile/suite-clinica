"""add coach pathologies fields to clienti and clienti_version

Revision ID: coach_pathologies_01
Revises: 7f3c1a9b2d10
Create Date: 2026-03-20 13:10:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "coach_pathologies_01"
down_revision = "7f3c1a9b2d10"
branch_labels = None
depends_on = None


def _table_exists(inspector, table_name):
    return table_name in inspector.get_table_names()


def _column_exists(inspector, table_name, column_name):
    return column_name in {col["name"] for col in inspector.get_columns(table_name)}


def _add_column_if_missing(inspector, table_name, column):
    if _table_exists(inspector, table_name) and not _column_exists(inspector, table_name, column.name):
        op.add_column(table_name, column)


def _drop_column_if_exists(inspector, table_name, column_name):
    if _table_exists(inspector, table_name) and _column_exists(inspector, table_name, column_name):
        op.drop_column(table_name, column_name)


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    bool_fields = [
        "nessuna_patologia_coach",
        "patologia_coach_infortuni",
        "patologia_coach_dolori_cronici",
        "patologia_coach_limitazioni_articolari",
        "patologia_coach_posturali",
        "patologia_coach_cardiovascolari",
    ]

    for table_name in ("clienti", "clienti_version"):
        for field in bool_fields:
            _add_column_if_missing(
                inspector,
                table_name,
                sa.Column(field, sa.Boolean(), nullable=True),
            )
        _add_column_if_missing(
            inspector,
            table_name,
            sa.Column("patologia_coach_altro", sa.Text(), nullable=True),
        )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    all_fields = [
        "patologia_coach_altro",
        "patologia_coach_cardiovascolari",
        "patologia_coach_posturali",
        "patologia_coach_limitazioni_articolari",
        "patologia_coach_dolori_cronici",
        "patologia_coach_infortuni",
        "nessuna_patologia_coach",
    ]

    for table_name in ("clienti_version", "clienti"):
        for field in all_fields:
            _drop_column_if_exists(inspector, table_name, field)
