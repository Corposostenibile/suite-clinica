"""add_professional_comment_to_check_responses

Revision ID: a7b8c9d0e1f2
Revises: f688901c582d
Create Date: 2026-02-27

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a7b8c9d0e1f2"
down_revision = "f688901c582d"
branch_labels = None
depends_on = None


def upgrade():
    # weekly_check_responses
    op.add_column(
        "weekly_check_responses",
        sa.Column("professional_comment", sa.Text(), nullable=True, comment="Commento del professionista sulla compilazione"),
    )
    op.add_column(
        "weekly_check_responses",
        sa.Column("professional_comment_by_id", sa.Integer(), nullable=True, comment="Utente che ha scritto il commento"),
    )
    op.add_column(
        "weekly_check_responses",
        sa.Column("professional_comment_at", sa.DateTime(), nullable=True, comment="Data/ora del commento"),
    )
    op.create_foreign_key(
        "fk_weekly_check_responses_professional_comment_by_id_users",
        "weekly_check_responses",
        "users",
        ["professional_comment_by_id"],
        ["id"],
    )

    # dca_check_responses
    op.add_column(
        "dca_check_responses",
        sa.Column("professional_comment", sa.Text(), nullable=True, comment="Commento del professionista sulla compilazione"),
    )
    op.add_column(
        "dca_check_responses",
        sa.Column("professional_comment_by_id", sa.Integer(), nullable=True, comment="Utente che ha scritto il commento"),
    )
    op.add_column(
        "dca_check_responses",
        sa.Column("professional_comment_at", sa.DateTime(), nullable=True, comment="Data/ora del commento"),
    )
    op.create_foreign_key(
        "fk_dca_check_responses_professional_comment_by_id_users",
        "dca_check_responses",
        "users",
        ["professional_comment_by_id"],
        ["id"],
    )

    # minor_check_responses
    op.add_column(
        "minor_check_responses",
        sa.Column("professional_comment", sa.Text(), nullable=True, comment="Commento del professionista sulla compilazione"),
    )
    op.add_column(
        "minor_check_responses",
        sa.Column("professional_comment_by_id", sa.Integer(), nullable=True, comment="Utente che ha scritto il commento"),
    )
    op.add_column(
        "minor_check_responses",
        sa.Column("professional_comment_at", sa.DateTime(), nullable=True, comment="Data/ora del commento"),
    )
    op.create_foreign_key(
        "fk_minor_check_responses_professional_comment_by_id_users",
        "minor_check_responses",
        "users",
        ["professional_comment_by_id"],
        ["id"],
    )


def downgrade():
    # minor_check_responses
    op.drop_constraint(
        "fk_minor_check_responses_professional_comment_by_id_users",
        "minor_check_responses",
        type_="foreignkey",
    )
    op.drop_column("minor_check_responses", "professional_comment_at")
    op.drop_column("minor_check_responses", "professional_comment_by_id")
    op.drop_column("minor_check_responses", "professional_comment")

    # dca_check_responses
    op.drop_constraint(
        "fk_dca_check_responses_professional_comment_by_id_users",
        "dca_check_responses",
        type_="foreignkey",
    )
    op.drop_column("dca_check_responses", "professional_comment_at")
    op.drop_column("dca_check_responses", "professional_comment_by_id")
    op.drop_column("dca_check_responses", "professional_comment")

    # weekly_check_responses
    op.drop_constraint(
        "fk_weekly_check_responses_professional_comment_by_id_users",
        "weekly_check_responses",
        type_="foreignkey",
    )
    op.drop_column("weekly_check_responses", "professional_comment_at")
    op.drop_column("weekly_check_responses", "professional_comment_by_id")
    op.drop_column("weekly_check_responses", "professional_comment")
