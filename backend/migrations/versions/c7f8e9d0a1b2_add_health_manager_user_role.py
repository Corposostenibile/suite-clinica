"""add_health_manager_user_role

Revision ID: c7f8e9d0a1b2
Revises: c1a8e7d9f244
Create Date: 2026-02-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'c7f8e9d0a1b2'
down_revision = 'c1a8e7d9f244'
branch_labels = None
depends_on = None


def upgrade():
    # Add 'health_manager' to userroleenum (PostgreSQL: add value to existing enum)
    op.execute("ALTER TYPE userroleenum ADD VALUE IF NOT EXISTS 'health_manager'")


def downgrade():
    # PostgreSQL does not support removing enum values directly.
    # We would need to recreate the type and alter the column; for safety we leave no-op.
    pass
