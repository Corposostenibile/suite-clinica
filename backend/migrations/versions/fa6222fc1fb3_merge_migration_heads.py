"""merge_migration_heads

Revision ID: fa6222fc1fb3
Revises: c7f8e9d0a1b2, d8e7f6a5b4c3
Create Date: 2026-02-15 17:09:58.838144

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fa6222fc1fb3'
down_revision = ('c7f8e9d0a1b2', 'd8e7f6a5b4c3')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
