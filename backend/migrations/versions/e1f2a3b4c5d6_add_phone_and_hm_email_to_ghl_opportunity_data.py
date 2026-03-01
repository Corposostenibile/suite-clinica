"""add_phone_and_hm_email_to_ghl_opportunity_data

Revision ID: e1f2a3b4c5d6
Revises: d4b8a7f0c3e1
Create Date: 2026-02-19 15:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e1f2a3b4c5d6"
down_revision = "d4b8a7f0c3e1"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ghl_opportunity_data", sa.Column("lead_phone", sa.String(length=64), nullable=True))
    op.add_column("ghl_opportunity_data", sa.Column("health_manager_email", sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column("ghl_opportunity_data", "health_manager_email")
    op.drop_column("ghl_opportunity_data", "lead_phone")
