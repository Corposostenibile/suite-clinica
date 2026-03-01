"""Add interessato/non_interessato to CallBonusStatusEnum + new columns

Revision ID: cb01_call_bonus_interest
Revises:
Create Date: 2026-02-27
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'cb01_call_bonus_interest'
down_revision = '90f0ea3788d9'
branch_labels = None
depends_on = None


def upgrade():
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction block in Postgres.
    # We must commit first so the new values are visible to subsequent DDL.
    op.execute("COMMIT")
    op.execute("ALTER TYPE callbonusstatusenum ADD VALUE IF NOT EXISTS 'interessato'")
    op.execute("ALTER TYPE callbonusstatusenum ADD VALUE IF NOT EXISTS 'non_interessato'")

    op.add_column('call_bonus', sa.Column('data_interesse', sa.DateTime(), nullable=True))
    op.add_column('call_bonus', sa.Column('hm_booking_confirmed', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('call_bonus', sa.Column('data_hm_booking_confirmed', sa.DateTime(), nullable=True))
    op.add_column('call_bonus', sa.Column('webhook_sent', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('call_bonus', sa.Column('webhook_sent_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('call_bonus', 'webhook_sent_at')
    op.drop_column('call_bonus', 'webhook_sent')
    op.drop_column('call_bonus', 'data_hm_booking_confirmed')
    op.drop_column('call_bonus', 'hm_booking_confirmed')
    op.drop_column('call_bonus', 'data_interesse')
    # NOTE: ALTER TYPE ... DROP VALUE is not supported in PostgreSQL.
    # The enum values 'interessato' and 'non_interessato' will remain.
