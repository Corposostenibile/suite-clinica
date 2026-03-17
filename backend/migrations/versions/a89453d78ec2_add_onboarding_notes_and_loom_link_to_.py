"""Add onboarding_notes and loom_link to SalesLead and Cliente

Revision ID: a89453d78ec2
Revises: e9f0a1b2c3d4
Create Date: 2026-03-17 16:06:58.687352
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "a89453d78ec2"
down_revision = "e9f0a1b2c3d4"
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

    _add_column_if_missing(inspector, "sales_leads", sa.Column("onboarding_notes", sa.Text(), nullable=True))
    _add_column_if_missing(inspector, "sales_leads", sa.Column("loom_link", sa.String(length=500), nullable=True))

    _add_column_if_missing(inspector, "sales_leads_version", sa.Column("onboarding_notes", sa.Text(), nullable=True))
    _add_column_if_missing(inspector, "sales_leads_version", sa.Column("loom_link", sa.String(length=500), nullable=True))

    _add_column_if_missing(inspector, "clienti", sa.Column("loom_link", sa.String(length=500), nullable=True))
    _add_column_if_missing(inspector, "clienti_version", sa.Column("loom_link", sa.String(length=500), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    _drop_column_if_exists(inspector, "clienti_version", "loom_link")
    _drop_column_if_exists(inspector, "clienti", "loom_link")

    _drop_column_if_exists(inspector, "sales_leads_version", "loom_link")
    _drop_column_if_exists(inspector, "sales_leads_version", "onboarding_notes")

    _drop_column_if_exists(inspector, "sales_leads", "loom_link")
    _drop_column_if_exists(inspector, "sales_leads", "onboarding_notes")
