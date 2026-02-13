"""add_ghl_opportunity_data_table

Revision ID: f8a1b2c3d4e5
Revises: 161cfcdebb2e
Create Date: 2026-02-09 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f8a1b2c3d4e5'
down_revision = '161cfcdebb2e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'ghl_opportunity_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=255), nullable=False),
        sa.Column('storia', sa.Text(), nullable=True),
        sa.Column('pacchetto', sa.String(length=255), nullable=True),
        sa.Column('durata', sa.String(length=50), nullable=True),
        sa.Column('received_at', sa.DateTime(), nullable=True),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('raw_payload', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('processed', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('ghl_opportunity_data')
