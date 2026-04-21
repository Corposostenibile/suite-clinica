"""compat legacy revision hm_team_second_leader_01

Revision ID: hm_team_second_leader_01
Revises: cb02_durata_servizio_giorni
Create Date: 2026-04-20 11:15:00.000000
"""

from alembic import op


revision = "hm_team_second_leader_01"
down_revision = "cb02_durata_servizio_giorni"
branch_labels = None
depends_on = None


def upgrade():
    # Compatibilita' con ambienti che hanno usato un revision id legacy
    # per l'introduzione del team type "health_manager".
    op.execute("ALTER TYPE teamtypeenum ADD VALUE IF NOT EXISTS 'health_manager'")


def downgrade():
    # PostgreSQL non supporta il drop diretto di valori enum.
    pass
