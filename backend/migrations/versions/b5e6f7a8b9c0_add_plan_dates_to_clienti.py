"""add_plan_dates_to_clienti

Revision ID: b5e6f7a8b9c0
Revises: a9b8c7d6e5f4
Create Date: 2026-02-11

Aggiunge date inizio/scadenza per piano (nutrizione, coach, psicologia) alla tabella clienti.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b5e6f7a8b9c0'
down_revision = 'a9b8c7d6e5f4'
branch_labels = None
depends_on = None


def upgrade():
    # Tabella principale
    op.add_column('clienti', sa.Column('data_inizio_nutrizione', sa.Date(), nullable=True))
    op.add_column('clienti', sa.Column('data_scadenza_nutrizione', sa.Date(), nullable=True))
    op.add_column('clienti', sa.Column('data_inizio_coach', sa.Date(), nullable=True))
    op.add_column('clienti', sa.Column('data_scadenza_coach', sa.Date(), nullable=True))
    op.add_column('clienti', sa.Column('data_inizio_psicologia', sa.Date(), nullable=True))
    op.add_column('clienti', sa.Column('data_scadenza_psicologia', sa.Date(), nullable=True))

    # Tabella di versioning (SQLAlchemy-Continuum)
    op.add_column('clienti_version', sa.Column('data_inizio_nutrizione', sa.Date(), nullable=True))
    op.add_column('clienti_version', sa.Column('data_scadenza_nutrizione', sa.Date(), nullable=True))
    op.add_column('clienti_version', sa.Column('data_inizio_coach', sa.Date(), nullable=True))
    op.add_column('clienti_version', sa.Column('data_scadenza_coach', sa.Date(), nullable=True))
    op.add_column('clienti_version', sa.Column('data_inizio_psicologia', sa.Date(), nullable=True))
    op.add_column('clienti_version', sa.Column('data_scadenza_psicologia', sa.Date(), nullable=True))


def downgrade():
    op.drop_column('clienti', 'data_scadenza_psicologia')
    op.drop_column('clienti', 'data_inizio_psicologia')
    op.drop_column('clienti', 'data_scadenza_coach')
    op.drop_column('clienti', 'data_inizio_coach')
    op.drop_column('clienti', 'data_scadenza_nutrizione')
    op.drop_column('clienti', 'data_inizio_nutrizione')

    op.drop_column('clienti_version', 'data_scadenza_psicologia')
    op.drop_column('clienti_version', 'data_inizio_psicologia')
    op.drop_column('clienti_version', 'data_scadenza_coach')
    op.drop_column('clienti_version', 'data_inizio_coach')
    op.drop_column('clienti_version', 'data_scadenza_nutrizione')
    op.drop_column('clienti_version', 'data_inizio_nutrizione')
