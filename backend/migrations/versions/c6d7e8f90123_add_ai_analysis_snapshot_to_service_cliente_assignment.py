"""add ai_analysis_snapshot to service_cliente_assignments

Revision ID: c6d7e8f90123
Revises: fa6222fc1fb3
Create Date: 2026-04-20 15:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'c6d7e8f90123'
down_revision = 'fa6222fc1fb3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'service_cliente_assignments',
        sa.Column('ai_analysis_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade():
    op.drop_column('service_cliente_assignments', 'ai_analysis_snapshot')
