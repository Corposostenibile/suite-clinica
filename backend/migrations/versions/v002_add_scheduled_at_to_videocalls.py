"""add_scheduled_at_to_videocalls

Revision ID: v002_videocalls_sched
Revises: v001_videocalls
Create Date: 2026-03-03 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'v002_videocalls_sched'
down_revision = 'v001_videocalls'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'video_call_sessions',
        sa.Column('scheduled_at', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_column('video_call_sessions', 'scheduled_at')
