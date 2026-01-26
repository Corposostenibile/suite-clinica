"""add_appointment_setting_funnel_table

Revision ID: d6e5f4a3b2c1
Revises: c5d4e3f2a1b0
Create Date: 2026-01-24 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd6e5f4a3b2c1'
down_revision = 'c5d4e3f2a1b0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('appointment_setting_funnel',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('mese', sa.String(length=20), nullable=False),
        sa.Column('anno', sa.Integer(), nullable=False),
        sa.Column('fase', sa.String(length=100), nullable=False),
        sa.Column('tasso_conversione', sa.Float(), nullable=False, server_default='0'),
        sa.Column('tempo_medio_fase', sa.Float(), nullable=False, server_default='0'),
        sa.Column('tasso_abbandono', sa.Float(), nullable=False, server_default='0'),
        sa.Column('cold', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('non_in_target', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('prenotato_non_in_target', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('under', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('fase', 'mese', 'anno', name='uq_appt_funnel_fase_mese_anno')
    )


def downgrade():
    op.drop_table('appointment_setting_funnel')
