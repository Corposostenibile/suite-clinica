"""compat merge stub for historical revision e9f0a1b2c3d4

Revision ID: e9f0a1b2c3d4
Revises: capacity_type_weights_01
Create Date: 2026-03-17 16:35:00.000000
"""

# revision identifiers, used by Alembic.
revision = "e9f0a1b2c3d4"
down_revision = "capacity_type_weights_01"
branch_labels = None
depends_on = None


def upgrade():
    # Historical DBs can be stamped at this revision id.
    # Keep it as a no-op bridge so Alembic can continue to newer revisions.
    pass


def downgrade():
    pass
