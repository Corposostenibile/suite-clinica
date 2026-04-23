"""add photo columns to monthly_check_responses

Revision ID: monthly_check_photos_01
Revises: video_review_requests_01b
Create Date: 2026-04-23 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "monthly_check_photos_01"
down_revision = "add_wcl_monthly_01"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "monthly_check_responses",
        sa.Column("photo_front", sa.String(500), nullable=True,
                  comment="Foto frontale (solo tipologia regolare)"),
    )
    op.add_column(
        "monthly_check_responses",
        sa.Column("photo_side", sa.String(500), nullable=True,
                  comment="Foto laterale (solo tipologia regolare)"),
    )
    op.add_column(
        "monthly_check_responses",
        sa.Column("photo_back", sa.String(500), nullable=True,
                  comment="Foto posteriore (solo tipologia regolare)"),
    )


def downgrade():
    op.drop_column("monthly_check_responses", "photo_back")
    op.drop_column("monthly_check_responses", "photo_side")
    op.drop_column("monthly_check_responses", "photo_front")
