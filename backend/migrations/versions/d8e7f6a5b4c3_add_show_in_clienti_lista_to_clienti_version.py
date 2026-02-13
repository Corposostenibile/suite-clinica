"""add_show_in_clienti_lista_to_clienti_version

Revision ID: d8e7f6a5b4c3
Revises: b7c6d5e4f3a2
Create Date: 2026-02-13 16:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd8e7f6a5b4c3'
down_revision = 'b7c6d5e4f3a2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('clienti_version', sa.Column('show_in_clienti_lista', sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column('clienti_version', 'show_in_clienti_lista')
