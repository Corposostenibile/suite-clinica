"""add old suite columns to sales_leads

Revision ID: old_suite_sales_leads_cols
Revises: cb05_influencer_origins_m2m
Create Date: 2026-03-11 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'old_suite_sales_leads_cols'
down_revision = 'cb05_influencer_origins_m2m'
branch_labels = None
depends_on = None


def upgrade():
    # Main table
    op.add_column('sales_leads', sa.Column('source_system', sa.String(50), nullable=True))
    op.add_column('sales_leads', sa.Column('old_suite_id', sa.Integer(), nullable=True))
    op.add_column('sales_leads', sa.Column('ai_analysis', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('sales_leads', sa.Column('ai_analyzed_at', sa.DateTime(), nullable=True))

    op.create_index('idx_sales_leads_source_system', 'sales_leads', ['source_system'])
    op.create_index('idx_sales_leads_old_suite_id', 'sales_leads', ['old_suite_id'])



def downgrade():
    op.drop_index('idx_sales_leads_old_suite_id', table_name='sales_leads')
    op.drop_index('idx_sales_leads_source_system', table_name='sales_leads')

    op.drop_column('sales_leads', 'ai_analyzed_at')
    op.drop_column('sales_leads', 'ai_analysis')
    op.drop_column('sales_leads', 'old_suite_id')
    op.drop_column('sales_leads', 'source_system')
