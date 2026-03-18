"""add missing version-table columns for parity checks

Revision ID: version_tables_parity_01
Revises: video_review_requests_01
Create Date: 2026-03-18 15:25:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "version_tables_parity_01"
down_revision = "capacity_type_weights_01"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        ALTER TABLE public.clienti_version
          ADD COLUMN IF NOT EXISTS loom_link VARCHAR(500),
          ADD COLUMN IF NOT EXISTS tipologia_supporto_nutrizione VARCHAR(20),
          ADD COLUMN IF NOT EXISTS tipologia_supporto_coach VARCHAR(20);
        """
    )
    op.execute(
        """
        ALTER TABLE public.sales_leads_version
          ADD COLUMN IF NOT EXISTS onboarding_notes TEXT,
          ADD COLUMN IF NOT EXISTS loom_link VARCHAR(500);
        """
    )


def downgrade():
    op.execute(
        """
        ALTER TABLE public.sales_leads_version
          DROP COLUMN IF EXISTS loom_link,
          DROP COLUMN IF EXISTS onboarding_notes;
        """
    )
    op.execute(
        """
        ALTER TABLE public.clienti_version
          DROP COLUMN IF EXISTS tipologia_supporto_coach,
          DROP COLUMN IF EXISTS tipologia_supporto_nutrizione,
          DROP COLUMN IF EXISTS loom_link;
        """
    )
