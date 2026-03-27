"""add old suite columns to sales_leads_version table

Revision ID: version_tbl_old_suite_cols
Revises: old_suite_sales_leads_cols
Create Date: 2026-03-11 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'version_tbl_old_suite_cols'
down_revision = 'old_suite_sales_leads_cols'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE sales_leads_version ADD COLUMN IF NOT EXISTS source_system VARCHAR(50);")
    op.execute("ALTER TABLE sales_leads_version ADD COLUMN IF NOT EXISTS old_suite_id INTEGER;")
    op.execute("ALTER TABLE sales_leads_version ADD COLUMN IF NOT EXISTS ai_analysis JSONB;")
    op.execute("ALTER TABLE sales_leads_version ADD COLUMN IF NOT EXISTS ai_analyzed_at TIMESTAMP WITHOUT TIME ZONE;")


def downgrade():
    op.drop_column('sales_leads_version', 'ai_analyzed_at')
    op.drop_column('sales_leads_version', 'ai_analysis')
    op.drop_column('sales_leads_version', 'old_suite_id')
    op.drop_column('sales_leads_version', 'source_system')
