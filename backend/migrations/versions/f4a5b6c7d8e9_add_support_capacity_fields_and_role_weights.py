"""add support capacity fields and role weights

Revision ID: support_capacity_fields_01
Revises: merge_cap_loom_01
Create Date: 2026-03-18 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'support_capacity_fields_01'
down_revision = 'merge_cap_loom_01'
branch_labels = None
depends_on = None


def upgrade():
    # Nuovi campi tipologia supporto su clienti
    op.add_column('clienti', sa.Column(
        'tipologia_supporto_nutrizione',
        sa.String(20),
        nullable=True,
        comment='Tipologia supporto nutrizione: a, b, c, secondario',
    ))
    op.add_column('clienti', sa.Column(
        'tipologia_supporto_coach',
        sa.String(20),
        nullable=True,
        comment='Tipologia supporto coach: a, b, c, secondario',
    ))

    # Tabella pesi capienza per area professionale
    op.create_table(
        'capacity_role_type_weights',
        sa.Column('role_type', sa.String(20), primary_key=True, comment='Area professionale: nutrizione, coach'),
        sa.Column('tipo', sa.String(20), primary_key=True, comment='Tipologia supporto: a, b, c, secondario'),
        sa.Column('peso', sa.Float, nullable=False, server_default='1.0', comment='Peso per il calcolo capienza'),
        sa.Column('created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
    )

    # Seed default weights
    op.execute("""
        INSERT INTO capacity_role_type_weights (role_type, tipo, peso) VALUES
        ('nutrizione', 'a', 2.0),
        ('nutrizione', 'b', 1.5),
        ('nutrizione', 'c', 1.0),
        ('nutrizione', 'secondario', 0.5),
        ('coach', 'a', 2.0),
        ('coach', 'b', 1.5),
        ('coach', 'c', 1.0),
        ('coach', 'secondario', 0.5)
    """)


def downgrade():
    op.drop_table('capacity_role_type_weights')
    op.drop_column('clienti', 'tipologia_supporto_coach')
    op.drop_column('clienti', 'tipologia_supporto_nutrizione')
