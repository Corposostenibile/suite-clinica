"""add planner sync fields

Revision ID: b2c3d4e5f6a7
Revises: f9a0b1c2d3e4
Create Date: 2026-02-23 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'f9a0b1c2d3e4'
branch_labels = None
depends_on = None


def upgrade():
    # Add planner_task_id to team_tickets
    op.add_column('team_tickets', sa.Column('planner_task_id', sa.String(255), nullable=True))
    op.create_unique_constraint('uq_team_tickets_planner_task_id', 'team_tickets', ['planner_task_id'])
    op.create_index('ix_team_tickets_planner_task_id', 'team_tickets', ['planner_task_id'])

    # Add 'planner' value to teamticketsourceenum
    op.execute("ALTER TYPE teamticketsourceenum ADD VALUE IF NOT EXISTS 'planner'")

    # Create planner_sync_state table
    op.create_table(
        'planner_sync_state',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('subscription_id', sa.String(255), nullable=True),
        sa.Column('last_renewed_at', sa.DateTime(), nullable=True),
        sa.Column('plan_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('planner_sync_state')
    op.drop_index('ix_team_tickets_planner_task_id', table_name='team_tickets')
    op.drop_constraint('uq_team_tickets_planner_task_id', 'team_tickets', type_='unique')
    op.drop_column('team_tickets', 'planner_task_id')
    # Note: cannot remove enum values in PostgreSQL
