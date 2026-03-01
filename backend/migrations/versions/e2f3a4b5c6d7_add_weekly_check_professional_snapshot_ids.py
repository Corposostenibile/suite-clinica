"""add_weekly_check_professional_snapshot_ids

Revision ID: e2f3a4b5c6d7
Revises: e1f2a3b4c5d6
Create Date: 2026-02-20 11:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e2f3a4b5c6d7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("weekly_check_responses", sa.Column("nutritionist_user_id", sa.Integer(), nullable=True))
    op.add_column("weekly_check_responses", sa.Column("psychologist_user_id", sa.Integer(), nullable=True))
    op.add_column("weekly_check_responses", sa.Column("coach_user_id", sa.Integer(), nullable=True))

    op.create_foreign_key(
        "fk_weekly_check_responses_nutritionist_user_id_users",
        "weekly_check_responses",
        "users",
        ["nutritionist_user_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_weekly_check_responses_psychologist_user_id_users",
        "weekly_check_responses",
        "users",
        ["psychologist_user_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_weekly_check_responses_coach_user_id_users",
        "weekly_check_responses",
        "users",
        ["coach_user_id"],
        ["id"],
    )


def downgrade():
    op.drop_constraint("fk_weekly_check_responses_coach_user_id_users", "weekly_check_responses", type_="foreignkey")
    op.drop_constraint("fk_weekly_check_responses_psychologist_user_id_users", "weekly_check_responses", type_="foreignkey")
    op.drop_constraint("fk_weekly_check_responses_nutritionist_user_id_users", "weekly_check_responses", type_="foreignkey")

    op.drop_column("weekly_check_responses", "coach_user_id")
    op.drop_column("weekly_check_responses", "psychologist_user_id")
    op.drop_column("weekly_check_responses", "nutritionist_user_id")
