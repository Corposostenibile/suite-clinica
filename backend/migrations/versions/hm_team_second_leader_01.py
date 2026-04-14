"""Add head_2_id to teams table for HM team second leader

Revision ID: hm_team_second_leader_01
Revises: 
Create Date: 2025-04-13
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'hm_team_second_leader_01'
down_revision = '90f0ea3788d9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Aggiungi colonna head_2_id alla tabella teams
    op.add_column(
        'teams',
        sa.Column(
            'head_2_id',
            sa.Integer(),
            sa.ForeignKey(
                'users.id',
                name='fk_teams_head_2_id',
                ondelete='SET NULL'
            ),
            nullable=True,
            index=True
        )
    )


def downgrade() -> None:
    op.drop_column('teams', 'head_2_id')
