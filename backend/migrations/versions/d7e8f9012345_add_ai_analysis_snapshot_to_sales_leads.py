"""add ai_analysis_snapshot to sales_leads and sales_leads_version

Revision ID: d7e8f9012345
Revises: c6d7e8f90123
Create Date: 2026-04-20 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'd7e8f9012345'
down_revision = 'c6d7e8f90123'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'sales_leads',
        sa.Column('ai_analysis_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        'sales_leads_version',
        sa.Column('ai_analysis_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # Backfill opzionale: copia il contenuto corrente di ai_analysis come snapshot iniziale
    op.execute("UPDATE sales_leads SET ai_analysis_snapshot = ai_analysis WHERE ai_analysis_snapshot IS NULL AND ai_analysis IS NOT NULL")
    op.execute("UPDATE sales_leads_version SET ai_analysis_snapshot = ai_analysis WHERE ai_analysis_snapshot IS NULL AND ai_analysis IS NOT NULL")


def downgrade():
    op.drop_column('sales_leads_version', 'ai_analysis_snapshot')
    op.drop_column('sales_leads', 'ai_analysis_snapshot')
