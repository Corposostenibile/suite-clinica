"""add video_review_requests table

Revision ID: video_review_requests_01
Revises: trustpilot_reviews_01
Create Date: 2026-03-18 12:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "video_review_requests_01"
down_revision = "trustpilot_reviews_01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "video_review_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cliente_id", sa.BigInteger(), nullable=False),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=False),
        sa.Column("hm_user_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("booking_confirmed_at", sa.DateTime(), nullable=False),
        sa.Column("hm_confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("loom_link", sa.String(length=500), nullable=True),
        sa.Column("hm_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["cliente_id"], ["clienti.cliente_id"]),
        sa.ForeignKeyConstraint(["hm_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_video_review_requests_cliente_id", "video_review_requests", ["cliente_id"])
    op.create_index("ix_video_review_requests_hm_user_id", "video_review_requests", ["hm_user_id"])
    op.create_index("ix_video_review_requests_requested_by_user_id", "video_review_requests", ["requested_by_user_id"])
    op.create_index("ix_video_review_requests_status", "video_review_requests", ["status"])


def downgrade():
    op.drop_index("ix_video_review_requests_status", table_name="video_review_requests")
    op.drop_index("ix_video_review_requests_requested_by_user_id", table_name="video_review_requests")
    op.drop_index("ix_video_review_requests_hm_user_id", table_name="video_review_requests")
    op.drop_index("ix_video_review_requests_cliente_id", table_name="video_review_requests")
    op.drop_table("video_review_requests")

