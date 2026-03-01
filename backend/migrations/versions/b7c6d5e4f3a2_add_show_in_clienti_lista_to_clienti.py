"""add_show_in_clienti_lista_to_clienti

Revision ID: b7c6d5e4f3a2
Revises: a9b8c7d6e5f4
Create Date: 2026-02-13 17:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7c6d5e4f3a2'
down_revision = 'a9b8c7d6e5f4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'clienti',
        sa.Column('show_in_clienti_lista', sa.Boolean(), nullable=False, server_default=sa.true())
    )
    op.create_index(
        op.f('ix_clienti_show_in_clienti_lista'),
        'clienti',
        ['show_in_clienti_lista'],
        unique=False,
    )


def downgrade():
    op.drop_index(op.f('ix_clienti_show_in_clienti_lista'), table_name='clienti')
    op.drop_column('clienti', 'show_in_clienti_lista')
