"""Add TeamTicket IT board fields and enum values

Revision ID: 2b4c7f9a1d23
Revises: 03cedd75f299
Create Date: 2026-03-17 12:45:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2b4c7f9a1d23"
down_revision = "03cedd75f299"
branch_labels = None
depends_on = None


def upgrade():
    # New columns for board routing + IT system
    op.add_column(
        "team_tickets",
        sa.Column("board", sa.String(length=50), nullable=False, server_default="general"),
    )
    op.add_column(
        "team_tickets",
        sa.Column("system", sa.String(length=50), nullable=True),
    )
    op.create_index("ix_team_tickets_board", "team_tickets", ["board"])
    op.create_index("ix_team_tickets_system", "team_tickets", ["system"])

    # Expand ENUMs (Postgres)
    # Note: Postgres allows adding values to existing enums.
    op.execute("ALTER TYPE public.teamticketstatusenum ADD VALUE IF NOT EXISTS 'standby'")
    op.execute("ALTER TYPE public.teamticketpriorityenum ADD VALUE IF NOT EXISTS 'bloccante'")
    op.execute("ALTER TYPE public.teamticketpriorityenum ADD VALUE IF NOT EXISTS 'non_bloccante'")

    # Backfill existing rows to general board
    op.execute("UPDATE team_tickets SET board = 'general' WHERE board IS NULL")

    # Drop server default to keep ORM default authoritative
    op.alter_column("team_tickets", "board", server_default=None)


def downgrade():
    # NOTE: Downgrade cannot safely remove enum values in Postgres without type recreation.
    op.drop_index("ix_team_tickets_system", table_name="team_tickets")
    op.drop_index("ix_team_tickets_board", table_name="team_tickets")
    op.drop_column("team_tickets", "system")
    op.drop_column("team_tickets", "board")

