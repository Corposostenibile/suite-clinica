"""add sales fields to ghl_opportunity_data

Revision ID: 7c8d9e0f1a2b
Revises: e2dd6adb402d
Create Date: 2026-04-20 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7c8d9e0f1a2b"
down_revision = "e2dd6adb402d"
branch_labels = None
depends_on = None


def _column_exists(inspector, table_name, column_name):
    return column_name in {col["name"] for col in inspector.get_columns(table_name)}


def _foreign_key_exists(inspector, table_name, column_name, referred_table=None):
    for fk in inspector.get_foreign_keys(table_name):
        if column_name not in fk.get("constrained_columns", []):
            continue
        if referred_table and fk.get("referred_table") != referred_table:
            continue
        return True
    return False


def _index_exists(inspector, table_name, index_name):
    return any(idx.get("name") == index_name for idx in inspector.get_indexes(table_name))


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _column_exists(inspector, "ghl_opportunity_data", "sales_consultant"):
        op.add_column(
            "ghl_opportunity_data",
            sa.Column("sales_consultant", sa.String(length=255), nullable=True),
        )

    if not _column_exists(inspector, "ghl_opportunity_data", "sales_person_id"):
        op.add_column(
            "ghl_opportunity_data",
            sa.Column("sales_person_id", sa.Integer(), nullable=True),
        )

    if not _index_exists(inspector, "ghl_opportunity_data", "ix_ghl_opportunity_data_sales_person_id"):
        op.create_index(
            "ix_ghl_opportunity_data_sales_person_id",
            "ghl_opportunity_data",
            ["sales_person_id"],
        )

    if not _foreign_key_exists(inspector, "ghl_opportunity_data", "sales_person_id", "sales_person"):
        op.create_foreign_key(
            "fk_ghl_opportunity_data_sales_person_id",
            "ghl_opportunity_data",
            "sales_person",
            ["sales_person_id"],
            ["sales_person_id"],
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _foreign_key_exists(inspector, "ghl_opportunity_data", "sales_person_id", "sales_person"):
        op.drop_constraint(
            "fk_ghl_opportunity_data_sales_person_id",
            "ghl_opportunity_data",
            type_="foreignkey",
        )

    if _index_exists(inspector, "ghl_opportunity_data", "ix_ghl_opportunity_data_sales_person_id"):
        op.drop_index("ix_ghl_opportunity_data_sales_person_id", table_name="ghl_opportunity_data")

    if _column_exists(inspector, "ghl_opportunity_data", "sales_person_id"):
        op.drop_column("ghl_opportunity_data", "sales_person_id")

    if _column_exists(inspector, "ghl_opportunity_data", "sales_consultant"):
        op.drop_column("ghl_opportunity_data", "sales_consultant")
