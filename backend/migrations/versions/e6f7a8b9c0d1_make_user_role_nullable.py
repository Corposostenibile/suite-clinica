"""make_user_role_nullable

Revision ID: e6f7a8b9c0d1
Revises: m9a1b2c3d4e5
Create Date: 2026-02-23

"""
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "e6f7a8b9c0d1"
down_revision = "m9a1b2c3d4e5"
branch_labels = None
depends_on = None


_USER_ROLE_ENUM = postgresql.ENUM(
    "admin",
    "team_leader",
    "professionista",
    "team_esterno",
    "influencer",
    "health_manager",
    name="userroleenum",
    create_type=False,
)


def upgrade():
    op.alter_column(
        "users",
        "role",
        existing_type=_USER_ROLE_ENUM,
        nullable=True,
        existing_nullable=False,
    )


def downgrade():
    op.execute(
        "UPDATE public.users "
        "SET role = 'professionista'::userroleenum "
        "WHERE role IS NULL"
    )
    op.alter_column(
        "users",
        "role",
        existing_type=_USER_ROLE_ENUM,
        nullable=False,
        existing_nullable=True,
    )
