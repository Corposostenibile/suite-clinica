"""merge_heads

Revision ID: 76412b8d05f3
Revises: perf_indexes_01, perf_indexes_02, rinnovo_interventions_01
Create Date: 2026-04-08 08:33:48.967076

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '76412b8d05f3'
down_revision = ('perf_indexes_01', 'perf_indexes_02', 'rinnovo_interventions_01')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
