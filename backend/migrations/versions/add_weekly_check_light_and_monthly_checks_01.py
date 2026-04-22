"""Add weekly_check_light and monthly_checks tables

Revision ID: add_wcl_monthly_01
Revises: cb04_add_durata_clienti_ver
Create Date: 2026-04-22

Aggiunge:
- weekly_check_light: link permanente auto-generato per il check settimanale light
- weekly_check_light_responses: risposte al check settimanale light (JSON)
- monthly_checks: link permanente per i check mensili (regolare/dca/minori)
- monthly_check_responses: risposte ai check mensili (JSON)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PgEnum

revision = "add_wcl_monthly_01"
down_revision = ("cb04_add_durata_clienti_ver", "tip_chk_cli_ver_01")
branch_labels = None
depends_on = None


def upgrade():
    # ── Enum per tipologia mensile ───────────────────────────────────────────
    # Usiamo un DO block PostgreSQL perché:
    # 1. Non esiste "CREATE TYPE IF NOT EXISTS" in PostgreSQL
    # 2. sa.Enum().create(checkfirst=True) ignora lo stato interno di SQLAlchemy
    #    e può ricrearlo durante create_table se non si usa create_type=False
    # Il DO block è la soluzione più robusta: cattura l'eccezione duplicate_object
    # e prosegue silenziosamente se il tipo esiste già.
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE tipologia_monthly_enum AS ENUM ('regolare', 'dca', 'minori');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$
    """)

    # ── weekly_check_light ───────────────────────────────────────────────────
    op.create_table(
        'weekly_check_light',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('cliente_id', sa.BigInteger(), nullable=False),
        sa.Column('token', sa.String(64), nullable=False,
                  comment='Token univoco PERMANENTE per link'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.ForeignKeyConstraint(['cliente_id'], ['clienti.cliente_id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_weekly_check_light_token', 'weekly_check_light', ['token'], unique=True)
    op.create_index('ix_weekly_check_light_cliente_id', 'weekly_check_light', ['cliente_id'])

    # ── weekly_check_light_responses ─────────────────────────────────────────
    op.create_table(
        'weekly_check_light_responses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('weekly_check_light_id', sa.Integer(), nullable=False),
        sa.Column('submit_date', sa.DateTime(), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('responses_data', sa.JSON(), nullable=False,
                  comment='Risposte check light in JSON'),
        sa.ForeignKeyConstraint(['weekly_check_light_id'], ['weekly_check_light.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_wclr_check_id', 'weekly_check_light_responses',
                    ['weekly_check_light_id'])
    op.create_index('ix_wclr_submit_date', 'weekly_check_light_responses', ['submit_date'])

    # ── monthly_checks ───────────────────────────────────────────────────────
    op.create_table(
        'monthly_checks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('cliente_id', sa.BigInteger(), nullable=False),
        sa.Column('token', sa.String(64), nullable=False,
                  comment='Token univoco PERMANENTE per link'),
        sa.Column('tipologia', PgEnum(name='tipologia_monthly_enum', create_type=False),
                  nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('assigned_by_id', sa.Integer(), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), nullable=False),
        sa.Column('deactivated_at', sa.DateTime(), nullable=True),
        sa.Column('deactivated_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['cliente_id'], ['clienti.cliente_id'], ),
        sa.ForeignKeyConstraint(['assigned_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['deactivated_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_monthly_checks_token', 'monthly_checks', ['token'], unique=True)
    op.create_index('ix_monthly_checks_cliente_id', 'monthly_checks', ['cliente_id'])

    # ── monthly_check_responses ──────────────────────────────────────────────
    op.create_table(
        'monthly_check_responses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('monthly_check_id', sa.Integer(), nullable=False),
        sa.Column('submit_date', sa.DateTime(), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('responses_data', sa.JSON(), nullable=False,
                  comment='Risposte check mensile in JSON'),
        sa.ForeignKeyConstraint(['monthly_check_id'], ['monthly_checks.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_mcr_check_id', 'monthly_check_responses', ['monthly_check_id'])
    op.create_index('ix_mcr_submit_date', 'monthly_check_responses', ['submit_date'])


def downgrade():
    op.drop_table('monthly_check_responses')
    op.drop_table('monthly_checks')
    op.drop_table('weekly_check_light_responses')
    op.drop_table('weekly_check_light')

    sa.Enum(name='tipologia_monthly_enum').drop(op.get_bind(), checkfirst=True)
