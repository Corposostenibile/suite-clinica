"""Add durata_*_giorni columns for per-service duration

Revision ID: cb02_durata_servizio_giorni
Revises: cb01_call_bonus_interest
Create Date: 2026-02-27
"""
from alembic import op
import sqlalchemy as sa

revision = 'cb02_durata_servizio_giorni'
down_revision = 'cb01_call_bonus_interest'
branch_labels = None
depends_on = None


def _add_column_if_not_exists(table, column_name, column):
    """Add a column only if it doesn't already exist (idempotent)."""
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :table AND column_name = :col"
    ), {"table": table, "col": column_name})
    if not result.fetchone():
        op.add_column(table, column)


def upgrade():
    _add_column_if_not_exists('clienti', 'durata_nutrizione_giorni',
        sa.Column('durata_nutrizione_giorni', sa.Integer(), nullable=True,
                  comment='Durata piano nutrizione in giorni'))
    _add_column_if_not_exists('clienti', 'durata_coach_giorni',
        sa.Column('durata_coach_giorni', sa.Integer(), nullable=True,
                  comment='Durata piano coach in giorni'))
    _add_column_if_not_exists('clienti', 'durata_psicologia_giorni',
        sa.Column('durata_psicologia_giorni', sa.Integer(), nullable=True,
                  comment='Durata piano psicologia in giorni'))

    # Popola le durate dai dati esistenti (data_scadenza - data_inizio)
    op.execute("""
        UPDATE clienti
        SET durata_nutrizione_giorni = (data_scadenza_nutrizione - data_inizio_nutrizione)
        WHERE data_inizio_nutrizione IS NOT NULL AND data_scadenza_nutrizione IS NOT NULL
    """)
    op.execute("""
        UPDATE clienti
        SET durata_coach_giorni = (data_scadenza_coach - data_inizio_coach)
        WHERE data_inizio_coach IS NOT NULL AND data_scadenza_coach IS NOT NULL
    """)
    op.execute("""
        UPDATE clienti
        SET durata_psicologia_giorni = (data_scadenza_psicologia - data_inizio_psicologia)
        WHERE data_inizio_psicologia IS NOT NULL AND data_scadenza_psicologia IS NOT NULL
    """)


def downgrade():
    op.drop_column('clienti', 'durata_psicologia_giorni')
    op.drop_column('clienti', 'durata_coach_giorni')
    op.drop_column('clienti', 'durata_nutrizione_giorni')
