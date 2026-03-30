"""add rinnovo_interventions table and referral bonus fields

Revision ID: rinnovo_referral_01
Revises: video_review_requests_01b
Create Date: 2026-03-31 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "rinnovo_referral_01"
down_revision = "video_review_requests_01b"
branch_labels = None
depends_on = None


def upgrade():
    # Create rinnovo_interventions table
    op.create_table(
        "rinnovo_interventions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cliente_id", sa.BigInteger(), nullable=False),
        sa.Column("intervention_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("loom_link", sa.String(length=500), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["cliente_id"], ["clienti.cliente_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rinnovo_interventions_cliente_id", "rinnovo_interventions", ["cliente_id"])
    op.create_index("ix_rinnovo_interventions_intervention_date", "rinnovo_interventions", ["intervention_date"])

    # Add referral bonus fields to clienti
    op.add_column("clienti", sa.Column("referral_bonus_scelto", sa.String(length=255), nullable=True))
    op.add_column("clienti", sa.Column("referral_bonus_utilizzato", sa.String(length=255), nullable=True))
    op.add_column("clienti", sa.Column("referral_bonus_da_utilizzare", sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column("clienti", "referral_bonus_da_utilizzare")
    op.drop_column("clienti", "referral_bonus_utilizzato")
    op.drop_column("clienti", "referral_bonus_scelto")
    op.drop_index("ix_rinnovo_interventions_intervention_date", table_name="rinnovo_interventions")
    op.drop_index("ix_rinnovo_interventions_cliente_id", table_name="rinnovo_interventions")
    op.drop_table("rinnovo_interventions")
