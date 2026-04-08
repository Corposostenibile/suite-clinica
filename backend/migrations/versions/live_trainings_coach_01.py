"""add live trainings counters for coaching

Revision ID: live_trainings_coach_01
Revises: marketing_consents_01
Create Date: 2026-04-08 17:00:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "live_trainings_coach_01"
down_revision = "marketing_consents_01"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        ALTER TABLE public.clienti
          ADD COLUMN IF NOT EXISTS live_trainings_acquistate INTEGER,
          ADD COLUMN IF NOT EXISTS live_trainings_svolte INTEGER;
        """
    )
    op.execute(
        """
        ALTER TABLE public.clienti_version
          ADD COLUMN IF NOT EXISTS live_trainings_acquistate INTEGER,
          ADD COLUMN IF NOT EXISTS live_trainings_svolte INTEGER;
        """
    )


def downgrade():
    op.execute(
        """
        ALTER TABLE public.clienti_version
          DROP COLUMN IF EXISTS live_trainings_svolte,
          DROP COLUMN IF EXISTS live_trainings_acquistate;
        """
    )
    op.execute(
        """
        ALTER TABLE public.clienti
          DROP COLUMN IF EXISTS live_trainings_svolte,
          DROP COLUMN IF EXISTS live_trainings_acquistate;
        """
    )
