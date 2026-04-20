"""add_tipologia_check_assegnato_to_clienti

Revision ID: tipologia_check_assegnato_01
Revises: it_support_commit_sha_01
Create Date: 2026-04-20 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "tipologia_check_assegnato_01"
down_revision = "it_support_commit_sha_01"
branch_labels = None
depends_on = None


tipologia_check_enum = postgresql.ENUM(
    "regolare",
    "minori",
    "dca",
    name="tipologiacheckenum",
)


def upgrade():
    bind = op.get_bind()
    tipologia_check_enum.create(bind, checkfirst=True)
    op.add_column(
        "clienti",
        sa.Column("tipologia_check_assegnato", tipologia_check_enum, nullable=True),
    )


def downgrade():
    op.drop_column("clienti", "tipologia_check_assegnato")
    bind = op.get_bind()
    tipologia_check_enum.drop(bind, checkfirst=True)
