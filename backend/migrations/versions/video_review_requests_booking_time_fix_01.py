"""repair booking_time column on video_review_requests

Revision ID: video_review_requests_01c
Revises: video_review_requests_01b
Create Date: 2026-03-19 16:36:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "video_review_requests_01c"
down_revision = "video_review_requests_01b"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("video_review_requests")}

    if "booking_time" not in columns:
        op.add_column(
            "video_review_requests",
            sa.Column("booking_time", sa.Time(), nullable=True, comment="Orario selezionato per la prenotazione della video recensione"),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("video_review_requests")}

    if "booking_time" in columns:
        op.drop_column("video_review_requests", "booking_time")
