"""merge heads: capacity_type_weights_01 + 2b4c7f9a1d23

Revision ID: 7f3c1a9b2d10
Revises: capacity_type_weights_01, 2b4c7f9a1d23
Create Date: 2026-03-17 13:15:00.000000
"""

# This is a merge migration, no schema changes.

from alembic import op  # noqa: F401


# revision identifiers, used by Alembic.
revision = "7f3c1a9b2d10"
down_revision = ("capacity_type_weights_01", "2b4c7f9a1d23")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass

