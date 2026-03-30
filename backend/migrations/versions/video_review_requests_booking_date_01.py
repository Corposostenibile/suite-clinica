"""add booking_date and booking_time to video_review_requests

Revision ID: video_review_requests_01b
Revises: video_review_requests_01
Create Date: 2026-03-19 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "video_review_requests_01b"
down_revision = "version_tables_parity_01"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "video_review_requests",
        sa.Column("booking_date", sa.Date(), nullable=True, comment="Data selezionata per la prenotazione della video recensione"),
    )
    op.add_column(
        "video_review_requests",
        sa.Column("booking_time", sa.Time(), nullable=True, comment="Orario selezionato per la prenotazione della video recensione"),
    )


def downgrade():
    op.drop_column("video_review_requests", "booking_time")
    op.drop_column("video_review_requests", "booking_date")
