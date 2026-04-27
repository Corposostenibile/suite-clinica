"""compat stub for missing historical revision hm_team_second_leader_01

This migration is a no-op and exists only to satisfy environments where
alembic_version contains 'hm_team_second_leader_01'.

Revision ID: hm_team_second_leader_01
Revises: cb03_hm_team_type
Create Date: 2026-04-27
"""

from alembic import op


revision = "hm_team_second_leader_01"
down_revision = "cb03_hm_team_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Historical compatibility no-op
    pass


def downgrade() -> None:
    # Historical compatibility no-op
    pass
