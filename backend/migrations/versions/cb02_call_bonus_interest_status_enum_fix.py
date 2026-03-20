"""Fix callbonusstatusenum missing interested values

Revision ID: cb02_cb_status_enum_fix
Revises: video_review_requests_01c
Create Date: 2026-03-18 15:20:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "cb02_cb_status_enum_fix"
down_revision = "video_review_requests_01c"
branch_labels = None
depends_on = None


def upgrade():
    # Postgres ALTER TYPE ... ADD VALUE cannot run inside a transaction block.
    op.execute("COMMIT")
    op.execute("ALTER TYPE public.callbonusstatusenum ADD VALUE IF NOT EXISTS 'interessato'")
    op.execute("ALTER TYPE public.callbonusstatusenum ADD VALUE IF NOT EXISTS 'non_interessato'")


def downgrade():
    # NOTE: Postgres does not support dropping enum values safely.
    pass
