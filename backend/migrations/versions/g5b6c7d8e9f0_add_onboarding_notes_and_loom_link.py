"""add onboarding_notes and loom_link to sales_leads and loom_link to clienti

Revision ID: onboarding_loom_fields_01
Revises: support_capacity_fields_01
Create Date: 2026-03-18 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'onboarding_loom_fields_01'
down_revision = 'support_capacity_fields_01'
branch_labels = None
depends_on = None


def upgrade():
    # Cliente: loom_link
    op.add_column('clienti', sa.Column(
        'loom_link',
        sa.String(500),
        nullable=True,
    ))

    # SalesLead: onboarding_notes + loom_link
    op.add_column('sales_leads', sa.Column(
        'onboarding_notes',
        sa.Text,
        nullable=True,
    ))
    op.add_column('sales_leads', sa.Column(
        'loom_link',
        sa.String(500),
        nullable=True,
    ))


def downgrade():
    op.drop_column('sales_leads', 'loom_link')
    op.drop_column('sales_leads', 'onboarding_notes')
    op.drop_column('clienti', 'loom_link')
