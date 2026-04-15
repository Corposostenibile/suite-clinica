"""add commit_sha column to it_support_tickets

Revision ID: it_support_commit_sha_01
Revises: ghl_support_tickets_01
Create Date: 2026-04-16 09:00:00.000000

Aggiunge colonna `commit_sha` (varchar 40, nullable) alla tabella
it_support_tickets. Permette di tracciare separatamente SemVer e Git short
hash per ogni ticket aperto, in modo che il custom field "Commit SHA" su
ClickUp venga popolato distintamente dalla "Versione app".
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "it_support_commit_sha_01"
down_revision = "ghl_support_tickets_01"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "it_support_tickets",
        sa.Column("commit_sha", sa.String(length=40), nullable=True),
    )


def downgrade():
    op.drop_column("it_support_tickets", "commit_sha")
