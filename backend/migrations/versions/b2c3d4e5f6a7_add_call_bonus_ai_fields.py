"""Add AI-driven fields to call_bonus and make professionista_id nullable

Revision ID: b2c3d4e5f6a7
Revises: 03cedd75f299
Create Date: 2026-02-16 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = '03cedd75f299'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns for AI-driven call bonus flow
    op.add_column('call_bonus', sa.Column('note_richiesta', sa.Text(), nullable=True))
    op.add_column('call_bonus', sa.Column('ai_analysis', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('call_bonus', sa.Column('ai_matches', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('call_bonus', sa.Column('booking_confirmed', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('call_bonus', sa.Column('data_booking_confirmed', sa.DateTime(), nullable=True))

    # Make professionista_id nullable (set after AI step 2)
    op.alter_column('call_bonus', 'professionista_id',
                    existing_type=sa.Integer(),
                    nullable=True)


def downgrade():
    op.alter_column('call_bonus', 'professionista_id',
                    existing_type=sa.Integer(),
                    nullable=False)

    op.drop_column('call_bonus', 'data_booking_confirmed')
    op.drop_column('call_bonus', 'booking_confirmed')
    op.drop_column('call_bonus', 'ai_matches')
    op.drop_column('call_bonus', 'ai_analysis')
    op.drop_column('call_bonus', 'note_richiesta')
