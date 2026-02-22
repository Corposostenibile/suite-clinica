"""compat stub for missing historical revision field_label_to_text

Revision ID: field_label_to_text
Revises: e2f3a4b5c6d7
Create Date: 2026-02-22 10:50:00.000000

"""


# revision identifiers, used by Alembic.
revision = "field_label_to_text"
down_revision = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade():
    # Historical revision was present in production alembic_version but missing
    # from the repository. This no-op stub restores graph continuity.
    pass


def downgrade():
    pass
