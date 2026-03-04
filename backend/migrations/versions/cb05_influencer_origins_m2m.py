"""Influencer origins many-to-many

Revision ID: cb05_influencer_origins_m2m
Revises: e2dd6adb402d
Create Date: 2026-03-04

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "cb05_influencer_origins_m2m"
down_revision = "e2dd6adb402d"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create the M2M join table
    op.create_table(
        "influencer_origins",
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("origin_id", sa.Integer, sa.ForeignKey("origins.id"), primary_key=True),
    )

    # 2. Migrate existing 1:1 data into the new M2M table
    op.execute(
        """
        INSERT INTO influencer_origins (user_id, origin_id)
        SELECT influencer_id, id
        FROM origins
        WHERE influencer_id IS NOT NULL
        """
    )

    # 3. Drop the old FK column (index + FK + column)
    op.drop_constraint(
        op.f("origins_influencer_id_key"), "origins", type_="unique"
    )
    op.drop_constraint(
        "origins_influencer_id_fkey", "origins", type_="foreignkey"
    )
    op.drop_column("origins", "influencer_id")


def downgrade():
    # Re-add the influencer_id column
    op.add_column(
        "origins",
        sa.Column("influencer_id", sa.Integer, sa.ForeignKey("users.id"), unique=True),
    )

    # Migrate data back (pick first user per origin if multiple exist)
    op.execute(
        """
        UPDATE origins
        SET influencer_id = io.user_id
        FROM (
            SELECT DISTINCT ON (origin_id) origin_id, user_id
            FROM influencer_origins
            ORDER BY origin_id, user_id
        ) io
        WHERE origins.id = io.origin_id
        """
    )

    # Drop the M2M table
    op.drop_table("influencer_origins")
