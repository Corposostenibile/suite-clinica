"""add medico to user specialty and professionista type enums

Revision ID: m9a1b2c3d4e5
Revises: field_label_to_text
Create Date: 2026-02-23 11:25:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "m9a1b2c3d4e5"
down_revision = "field_label_to_text"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE userspecialtyenum ADD VALUE IF NOT EXISTS 'medico'")
    op.execute("ALTER TYPE tipoprofessionistaenum ADD VALUE IF NOT EXISTS 'medico'")


def downgrade():
    # PostgreSQL ENUM value removal is not safely reversible without type rebuild.
    pass
