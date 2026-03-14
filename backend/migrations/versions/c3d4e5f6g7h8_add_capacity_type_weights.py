"""add capacity_type_weights table

Revision ID: capacity_type_weights_01
Revises: version_tbl_old_suite_cols
Create Date: 2026-03-14 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'capacity_type_weights_01'
down_revision = 'version_tbl_old_suite_cols'
branch_labels = None
depends_on = None


def upgrade():
    tbl = op.create_table(
        'capacity_type_weights',
        sa.Column('tipo', sa.String(10), primary_key=True, comment='Tipologia cliente: a, b, c'),
        sa.Column('peso', sa.Float, nullable=False, server_default='1.0', comment='Peso per il calcolo capienza'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    )

    op.bulk_insert(tbl, [
        {'tipo': 'a', 'peso': 1.0},
        {'tipo': 'b', 'peso': 1.0},
        {'tipo': 'c', 'peso': 1.0},
    ])


def downgrade():
    op.drop_table('capacity_type_weights')
