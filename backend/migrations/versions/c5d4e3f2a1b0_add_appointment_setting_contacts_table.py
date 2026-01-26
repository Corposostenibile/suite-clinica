"""add_appointment_setting_contacts_table

Revision ID: c5d4e3f2a1b0
Revises: b4c3d2e1f0a9
Create Date: 2026-01-24 10:40:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c5d4e3f2a1b0'
down_revision = 'b4c3d2e1f0a9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('appointment_setting_contacts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('utente', sa.String(length=255), nullable=False),
        sa.Column('giorno', sa.Integer(), nullable=False),
        sa.Column('mese', sa.String(length=20), nullable=False),
        sa.Column('anno', sa.Integer(), nullable=False),
        sa.Column('contatti', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('utente', 'giorno', 'mese', 'anno', name='uq_appt_contact_utente_giorno')
    )


def downgrade():
    op.drop_table('appointment_setting_contacts')
