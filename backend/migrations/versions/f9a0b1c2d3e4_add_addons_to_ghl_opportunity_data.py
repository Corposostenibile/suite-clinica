"""add addons to ghl_opportunity_data

Revision ID: f9a0b1c2d3e4
Revises: e2f3a4b5c6d7
Create Date: 2026-02-22 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f9a0b1c2d3e4'
down_revision = 'e2f3a4b5c6d7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('ghl_opportunity_data', sa.Column('addons', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('ghl_opportunity_data', 'addons')
