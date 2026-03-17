"""Add missing old-suite columns to sales_leads tables

Revision ID: b1c2d3e4f5a6
Revises: a89453d78ec2
Create Date: 2026-03-17 16:50:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = "b1c2d3e4f5a6"
down_revision = "a89453d78ec2"
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

    for table_name in ("sales_leads", "sales_leads_version"):
        _add_column_if_missing(inspector, table_name, sa.Column("source_system", sa.String(length=50), nullable=True))
        _add_column_if_missing(inspector, table_name, sa.Column("old_suite_id", sa.Integer(), nullable=True))
        _add_column_if_missing(inspector, table_name, sa.Column("ai_analysis", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
        _add_column_if_missing(inspector, table_name, sa.Column("ai_analyzed_at", sa.DateTime(), nullable=True))

    if _table_exists(inspector, "sales_leads"):
        indexes = {idx["name"] for idx in inspector.get_indexes("sales_leads")}
        if "idx_sales_leads_source_system" not in indexes:
            op.create_index("idx_sales_leads_source_system", "sales_leads", ["source_system"])
        if "idx_sales_leads_old_suite_id" not in indexes:
            op.create_index("idx_sales_leads_old_suite_id", "sales_leads", ["old_suite_id"])


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if _table_exists(inspector, "sales_leads"):
        indexes = {idx["name"] for idx in inspector.get_indexes("sales_leads")}
        if "idx_sales_leads_old_suite_id" in indexes:
            op.drop_index("idx_sales_leads_old_suite_id", table_name="sales_leads")
        if "idx_sales_leads_source_system" in indexes:
            op.drop_index("idx_sales_leads_source_system", table_name="sales_leads")

    for table_name in ("sales_leads_version", "sales_leads"):
        _drop_column_if_exists(inspector, table_name, "ai_analyzed_at")
        _drop_column_if_exists(inspector, table_name, "ai_analysis")
        _drop_column_if_exists(inspector, table_name, "old_suite_id")
        _drop_column_if_exists(inspector, table_name, "source_system")
