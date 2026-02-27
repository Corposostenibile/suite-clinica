"""add_health_manager_team_type

Revision ID: cb03_add_health_manager_team_type
Revises: cb02_durata_servizio_giorni
Create Date: 2026-02-27

"""
from alembic import op


revision = "cb03_add_health_manager_team_type"
down_revision = "cb02_durata_servizio_giorni"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE teamtypeenum ADD VALUE IF NOT EXISTS 'health_manager'")


def downgrade():
    # PostgreSQL non supporta la rimozione diretta di valori enum senza ricreare il tipo.
    pass

