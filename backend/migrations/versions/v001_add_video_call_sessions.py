"""add_video_call_sessions

Revision ID: v001_videocalls
Revises: e2dd6adb402d
Create Date: 2026-03-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'v001_videocalls'
down_revision = 'e2dd6adb402d'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'video_call_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('room_name', sa.String(length=120), nullable=False),
        sa.Column('session_token', sa.String(length=64), nullable=False),
        sa.Column('professionista_id', sa.Integer(), nullable=False),
        sa.Column('cliente_id', sa.BigInteger(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='waiting'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['professionista_id'], ['users.id']),
        sa.ForeignKeyConstraint(['cliente_id'], ['clienti.cliente_id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_video_call_sessions_room_name', 'video_call_sessions', ['room_name'], unique=True)
    op.create_index('ix_video_call_sessions_session_token', 'video_call_sessions', ['session_token'], unique=True)
    op.create_index('ix_video_call_sessions_professionista_id', 'video_call_sessions', ['professionista_id'])
    op.create_index('ix_video_call_sessions_cliente_id', 'video_call_sessions', ['cliente_id'])


def downgrade():
    op.drop_table('video_call_sessions')
