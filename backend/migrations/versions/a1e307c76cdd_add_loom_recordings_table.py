"""add loom_recordings table

Revision ID: a1e307c76cdd
Revises: cb05_influencer_origins_m2m
Create Date: 2026-03-04 14:47:16.745222

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a1e307c76cdd"
down_revision = "cb05_influencer_origins_m2m"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "loom_recordings_version",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("loom_link", sa.String(length=500), autoincrement=False, nullable=True),
        sa.Column("title", sa.String(length=255), autoincrement=False, nullable=True),
        sa.Column("note", sa.Text(), autoincrement=False, nullable=True),
        sa.Column("source", sa.String(length=50), autoincrement=False, nullable=True),
        sa.Column("submitter_user_id", sa.Integer(), autoincrement=False, nullable=True),
        sa.Column("cliente_id", sa.BigInteger(), autoincrement=False, nullable=True),
        sa.Column("created_at", sa.DateTime(), autoincrement=False, nullable=True),
        sa.Column("updated_at", sa.DateTime(), autoincrement=False, nullable=True),
        sa.Column("transaction_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("end_transaction_id", sa.BigInteger(), nullable=True),
        sa.Column("operation_type", sa.SmallInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id", "transaction_id"),
    )
    op.create_index("ix_loom_recordings_version_cliente_id", "loom_recordings_version", ["cliente_id"])
    op.create_index("ix_loom_recordings_version_end_transaction_id", "loom_recordings_version", ["end_transaction_id"])
    op.create_index("ix_loom_recordings_version_loom_link", "loom_recordings_version", ["loom_link"])
    op.create_index("ix_loom_recordings_version_operation_type", "loom_recordings_version", ["operation_type"])
    op.create_index("ix_loom_recordings_version_submitter_user_id", "loom_recordings_version", ["submitter_user_id"])
    op.create_index("ix_loom_recordings_version_transaction_id", "loom_recordings_version", ["transaction_id"])

    op.create_table(
        "loom_recordings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("loom_link", sa.String(length=500), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("submitter_user_id", sa.Integer(), nullable=False),
        sa.Column("cliente_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["cliente_id"], ["clienti.cliente_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["submitter_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_loom_recordings_cliente_id", "loom_recordings", ["cliente_id"])
    op.create_index("ix_loom_recordings_loom_link", "loom_recordings", ["loom_link"])
    op.create_index("ix_loom_recordings_submitter_user_id", "loom_recordings", ["submitter_user_id"])


def downgrade():
    op.drop_index("ix_loom_recordings_submitter_user_id", table_name="loom_recordings")
    op.drop_index("ix_loom_recordings_loom_link", table_name="loom_recordings")
    op.drop_index("ix_loom_recordings_cliente_id", table_name="loom_recordings")
    op.drop_table("loom_recordings")

    op.drop_index("ix_loom_recordings_version_transaction_id", table_name="loom_recordings_version")
    op.drop_index("ix_loom_recordings_version_submitter_user_id", table_name="loom_recordings_version")
    op.drop_index("ix_loom_recordings_version_operation_type", table_name="loom_recordings_version")
    op.drop_index("ix_loom_recordings_version_loom_link", table_name="loom_recordings_version")
    op.drop_index("ix_loom_recordings_version_end_transaction_id", table_name="loom_recordings_version")
    op.drop_index("ix_loom_recordings_version_cliente_id", table_name="loom_recordings_version")
    op.drop_table("loom_recordings_version")
