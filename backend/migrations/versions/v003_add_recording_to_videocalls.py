"""add_recording_to_videocalls

Revision ID: v003_videocalls_rec
Revises: v002_videocalls_sched
Create Date: 2026-03-03 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'v003_videocalls_rec'
down_revision = 'v002_videocalls_sched'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'video_call_sessions',
        sa.Column('recording_path', sa.String(500), nullable=True),
    )
    op.add_column(
        'video_call_sessions',
        sa.Column('transcription', sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_column('video_call_sessions', 'transcription')
    op.drop_column('video_call_sessions', 'recording_path')
