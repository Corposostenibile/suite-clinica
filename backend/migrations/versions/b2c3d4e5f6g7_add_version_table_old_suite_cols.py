"""add old suite columns to sales_leads_version table

Revision ID: version_tbl_old_suite_cols
Revises: old_suite_sales_leads_cols
Create Date: 2026-03-11 14:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'version_tbl_old_suite_cols'
down_revision = 'old_suite_sales_leads_cols'
branch_labels = None
depends_on = None


def upgrade():
    # Idempotente: evita errore se lo schema è già allineato
    op.execute("ALTER TABLE sales_leads_version ADD COLUMN IF NOT EXISTS source_system VARCHAR(50)")
    op.execute("ALTER TABLE sales_leads_version ADD COLUMN IF NOT EXISTS old_suite_id INTEGER")
    op.execute("ALTER TABLE sales_leads_version ADD COLUMN IF NOT EXISTS ai_analysis JSONB")
    op.execute("ALTER TABLE sales_leads_version ADD COLUMN IF NOT EXISTS ai_analyzed_at TIMESTAMP")


def downgrade():
    op.execute("ALTER TABLE sales_leads_version DROP COLUMN IF EXISTS ai_analyzed_at")
    op.execute("ALTER TABLE sales_leads_version DROP COLUMN IF EXISTS ai_analysis")
    op.execute("ALTER TABLE sales_leads_version DROP COLUMN IF EXISTS old_suite_id")
    op.execute("ALTER TABLE sales_leads_version DROP COLUMN IF EXISTS source_system")
