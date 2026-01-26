"""add_appt_setting_extra_columns

Revision ID: b4c3d2e1f0a9
Revises: a3b2c1d4e5f6
Create Date: 2026-01-24 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b4c3d2e1f0a9'
down_revision = 'a3b2c1d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('appointment_setting_messages', schema=None) as batch_op:
        batch_op.add_column(sa.Column('contatti_unici_chiusi', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('conversazioni_assegnate', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('conversazioni_chiuse', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    with op.batch_alter_table('appointment_setting_messages', schema=None) as batch_op:
        batch_op.drop_column('conversazioni_chiuse')
        batch_op.drop_column('conversazioni_assegnate')
        batch_op.drop_column('contatti_unici_chiusi')
