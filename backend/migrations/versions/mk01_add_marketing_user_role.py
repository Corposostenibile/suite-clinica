"""add_marketing_user_role

Revision ID: mk01_add_marketing_user_role
Revises: it_support_commit_sha_01
Create Date: 2026-04-23

"""
from alembic import op


revision = 'mk01_add_marketing_user_role'
down_revision = 'it_support_commit_sha_01'
branch_labels = None
depends_on = None


def upgrade():
    # Add 'marketing' to userroleenum (PostgreSQL: add value to existing enum)
    op.execute("ALTER TYPE userroleenum ADD VALUE IF NOT EXISTS 'marketing'")


def downgrade():
    # PostgreSQL does not support removing enum values directly; no-op for safety.
    pass
