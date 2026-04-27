"""add onboarding_email_sent_at to clienti

Revision ID: onboarding_cliente_email_01
Revises: hm_capacity_target_01
Create Date: 2026-04-27
"""

from alembic import op
import sqlalchemy as sa


revision = "onboarding_cliente_email_01"
down_revision = "hm_capacity_target_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "ALTER TABLE clienti ADD COLUMN IF NOT EXISTS onboarding_email_sent_at TIMESTAMP"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "ALTER TABLE clienti DROP COLUMN IF EXISTS onboarding_email_sent_at"
        )
    )
