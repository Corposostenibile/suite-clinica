"""add hm_capacity_target to users

Revision ID: hm_capacity_target_01
Revises: mk02_cliente_marketing_flags
Create Date: 2026-04-27
"""

from alembic import op
import sqlalchemy as sa


revision = "hm_capacity_target_01"
down_revision = "mk02_cliente_marketing_flags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS hm_capacity_target INTEGER"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "ALTER TABLE users DROP COLUMN IF EXISTS hm_capacity_target"
        )
    )
