"""add rinnovo interventions table

Revision ID: rinnovo_interventions_01
Revises: 864501f73770
Create Date: 2026-03-23 18:42:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "rinnovo_interventions_01"
down_revision = "864501f73770"
branch_labels = None
depends_on = None


def upgrade():
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
    op.create_index(op.f("ix_rinnovo_interventions_cliente_id"), "rinnovo_interventions", ["cliente_id"], unique=False)
    op.create_index(op.f("ix_rinnovo_interventions_intervention_date"), "rinnovo_interventions", ["intervention_date"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_rinnovo_interventions_intervention_date"), table_name="rinnovo_interventions")
    op.drop_index(op.f("ix_rinnovo_interventions_cliente_id"), table_name="rinnovo_interventions")
    op.drop_table("rinnovo_interventions")
