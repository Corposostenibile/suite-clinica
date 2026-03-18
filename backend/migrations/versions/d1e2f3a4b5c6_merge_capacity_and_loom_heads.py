"""merge capacity_type_weights and loom_recordings heads

Revision ID: merge_cap_loom_01
Revises: a1e307c76cdd, capacity_type_weights_01
Create Date: 2026-03-18 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_cap_loom_01'
down_revision = ('a1e307c76cdd', 'capacity_type_weights_01')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
