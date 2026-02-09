"""add_email_to_ghl_opportunity_data

Revision ID: a9b8c7d6e5f4
Revises: f8a1b2c3d4e5
Create Date: 2026-02-09 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a9b8c7d6e5f4'
down_revision = 'f8a1b2c3d4e5'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('ghl_opportunity_data', sa.Column('email', sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column('ghl_opportunity_data', 'email')
