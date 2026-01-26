"""add_appointment_setting_messages_table

Revision ID: a3b2c1d4e5f6
Revises: 161cfcdebb2e
Create Date: 2026-01-24 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a3b2c1d4e5f6'
down_revision = '161cfcdebb2e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('appointment_setting_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('utente', sa.String(length=255), nullable=False),
        sa.Column('mese', sa.String(length=20), nullable=False),
        sa.Column('anno', sa.Integer(), nullable=False),
        sa.Column('messaggi_inviati', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('utente', 'mese', 'anno', name='uq_appt_utente_mese_anno')
    )


def downgrade():
    op.drop_table('appointment_setting_messages')
