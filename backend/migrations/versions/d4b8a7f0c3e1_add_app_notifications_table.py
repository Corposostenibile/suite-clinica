"""add app notifications table

Revision ID: d4b8a7f0c3e1
Revises: c9d0e1f2a3b4
Create Date: 2026-02-18 16:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d4b8a7f0c3e1"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "app_notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_app_notifications_user_id"), "app_notifications", ["user_id"], unique=False)
    op.create_index(op.f("ix_app_notifications_kind"), "app_notifications", ["kind"], unique=False)
    op.create_index(op.f("ix_app_notifications_is_read"), "app_notifications", ["is_read"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_app_notifications_is_read"), table_name="app_notifications")
    op.drop_index(op.f("ix_app_notifications_kind"), table_name="app_notifications")
    op.drop_index(op.f("ix_app_notifications_user_id"), table_name="app_notifications")
    op.drop_table("app_notifications")
