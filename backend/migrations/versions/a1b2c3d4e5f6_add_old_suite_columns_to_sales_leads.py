"""add old suite columns to sales_leads

Revision ID: old_suite_sales_leads_cols
Revises: cb05_influencer_origins_m2m
Create Date: 2026-03-11 12:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'old_suite_sales_leads_cols'
down_revision = 'cb05_influencer_origins_m2m'
branch_labels = None
depends_on = None


def upgrade():
    # Idempotente: evita errori se le colonne esistono già (es. schema da create-db o import SQL).
    op.execute("ALTER TABLE sales_leads ADD COLUMN IF NOT EXISTS source_system VARCHAR(50)")
    op.execute("ALTER TABLE sales_leads ADD COLUMN IF NOT EXISTS old_suite_id INTEGER")
    op.execute(
        "ALTER TABLE sales_leads ADD COLUMN IF NOT EXISTS ai_analysis JSONB"
    )
    op.execute("ALTER TABLE sales_leads ADD COLUMN IF NOT EXISTS ai_analyzed_at TIMESTAMP")

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_sales_leads_source_system ON sales_leads (source_system)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_sales_leads_old_suite_id ON sales_leads (old_suite_id)"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_sales_leads_old_suite_id")
    op.execute("DROP INDEX IF EXISTS idx_sales_leads_source_system")

    op.execute("ALTER TABLE sales_leads DROP COLUMN IF EXISTS ai_analyzed_at")
    op.execute("ALTER TABLE sales_leads DROP COLUMN IF EXISTS ai_analysis")
    op.execute("ALTER TABLE sales_leads DROP COLUMN IF EXISTS old_suite_id")
    op.execute("ALTER TABLE sales_leads DROP COLUMN IF EXISTS source_system")
