"""add referral_bonus columns to clienti_version table

Revision ID: rinnovo_referral_version_fix_01
Revises: rinnovo_referral_01
Create Date: 2026-03-31 01:30:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "rinnovo_referral_version_fix_01"
down_revision = "rinnovo_referral_01"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {col["name"] for col in inspector.get_columns("clienti_version")}

    if "referral_bonus_scelto" not in existing:
        op.add_column("clienti_version", sa.Column("referral_bonus_scelto", sa.String(length=255), nullable=True))
    if "referral_bonus_utilizzato" not in existing:
        op.add_column("clienti_version", sa.Column("referral_bonus_utilizzato", sa.String(length=255), nullable=True))
    if "referral_bonus_da_utilizzare" not in existing:
        op.add_column("clienti_version", sa.Column("referral_bonus_da_utilizzare", sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column("clienti_version", "referral_bonus_da_utilizzare")
    op.drop_column("clienti_version", "referral_bonus_utilizzato")
    op.drop_column("clienti_version", "referral_bonus_scelto")
