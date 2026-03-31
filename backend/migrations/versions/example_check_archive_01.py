"""add example check archive tables

Revision ID: example_check_archive_01
Revises: version_tables_parity_01
Create Date: 2026-03-30 20:35:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "example_check_archive_01"
down_revision = "version_tables_parity_01"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = inspect(bind)
    existing = set(insp.get_table_names())

    if "example_check_import_batches" not in existing:
        op.create_table(
            "example_check_import_batches",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("source_file", sa.String(length=512), nullable=False),
            sa.Column("batch_label", sa.String(length=255), nullable=True),
            sa.Column("file_hash", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("stats_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_example_check_import_batches_file_hash", "example_check_import_batches", ["file_hash"])
        op.create_index("ix_example_check_import_batches_status", "example_check_import_batches", ["status"])

    if "example_check_entries" not in existing:
        op.create_table(
            "example_check_entries",
            sa.Column("id", sa.BigInteger(), nullable=False),
            sa.Column("batch_id", sa.Integer(), nullable=False),
            sa.Column("section_name", sa.String(length=255), nullable=False),
            sa.Column("external_response_id", sa.String(length=255), nullable=False),
            sa.Column("first_name", sa.String(length=255), nullable=True),
            sa.Column("last_name", sa.String(length=255), nullable=True),
            sa.Column("birth_date_raw", sa.String(length=128), nullable=True),
            sa.Column("matched_cliente_id", sa.BigInteger(), nullable=True),
            sa.Column("response_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("submitted_at", sa.DateTime(), nullable=True),
            sa.Column("network_id", sa.String(length=255), nullable=True),
            sa.Column("response_type", sa.String(length=64), nullable=True),
            sa.Column("raw_row_hash", sa.String(length=64), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["batch_id"], ["example_check_import_batches.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["matched_cliente_id"], ["clienti.cliente_id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "section_name",
                "external_response_id",
                name="uq_example_check_entries_section_external_response",
            ),
        )
        op.create_index("ix_example_check_entries_batch_id", "example_check_entries", ["batch_id"])
        op.create_index("ix_example_check_entries_section_name", "example_check_entries", ["section_name"])
        op.create_index("ix_example_check_entries_first_name", "example_check_entries", ["first_name"])
        op.create_index("ix_example_check_entries_last_name", "example_check_entries", ["last_name"])
        op.create_index("ix_example_check_entries_matched_cliente_id", "example_check_entries", ["matched_cliente_id"])
        op.create_index("ix_example_check_entries_submitted_at", "example_check_entries", ["submitted_at"])
        op.create_index("ix_example_check_entries_network_id", "example_check_entries", ["network_id"])
        op.create_index("ix_example_check_entries_response_type", "example_check_entries", ["response_type"])
        op.create_index("ix_example_check_entries_raw_row_hash", "example_check_entries", ["raw_row_hash"])
        op.create_index(
            "ix_example_check_entries_cliente_submitted",
            "example_check_entries",
            ["matched_cliente_id", "submitted_at"],
        )


def downgrade():
    op.execute("DROP TABLE IF EXISTS example_check_entries CASCADE")
    op.execute("DROP TABLE IF EXISTS example_check_import_batches CASCADE")
