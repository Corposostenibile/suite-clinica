"""Add referral bonus fields to Cliente

Revision ID: 864501f73770
Revises: version_tables_parity_01
Create Date: 2026-03-23 12:20:46.668647

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '864501f73770'
down_revision = 'version_tables_parity_01'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('clienti', sa.Column('referral_bonus_scelto', sa.String(length=255), nullable=True))
    op.add_column('clienti', sa.Column('referral_bonus_utilizzato', sa.String(length=255), nullable=True))
    op.add_column('clienti', sa.Column('referral_bonus_da_utilizzare', sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column('clienti', 'referral_bonus_da_utilizzare')
    op.drop_column('clienti', 'referral_bonus_utilizzato')
    op.drop_column('clienti', 'referral_bonus_scelto')
