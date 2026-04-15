"""create ghl_support_tickets, comments, attachments tables

Revision ID: ghl_support_tickets_01
Revises: it_support_tickets_01
Create Date: 2026-04-15 12:00:00.000000

Tabelle per il sistema di ticket GHL con sync bidirezionale ClickUp
(space "Go High Level - Ticket", ID 90127111740).
- ghl_support_tickets
- ghl_support_ticket_comments
- ghl_support_ticket_attachments
+ enum type: ghlsupportticketstatusenum
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "ghl_support_tickets_01"
down_revision = "it_support_tickets_01"
branch_labels = None
depends_on = None


# ── Enum definitions (Postgres) ───────────────────────────────────────────
_STATUS_VALUES = (
    "nuovo",
    "in_analisi",
    "in_lavorazione",
    "in_attesa_highlevel",
    "in_attesa_utente",
    "risolto",
    "non_valido",
)


def upgrade():
    conn = op.get_bind()

    # Enum type (idempotente). Nota: il tipo viene comunque creato al boot
    # dell'app da register_enums() (models.py), quindi qui ci si limita a
    # garantire esistenza senza duplicare. create_type=False sul tipo usato
    # nelle colonne evita che Alembic provi a ricrearlo.
    conn.execute(
        sa.text(
            """
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'ghlsupportticketstatusenum') THEN
                    CREATE TYPE ghlsupportticketstatusenum AS ENUM (
                        'nuovo','in_analisi','in_lavorazione','in_attesa_highlevel',
                        'in_attesa_utente','risolto','non_valido'
                    );
                END IF;
            END $$;
            """
        )
    )

    # Dichiaro il tipo ENUM come "esterno" (create_type=False) in modo che
    # Alembic NON emetta un secondo CREATE TYPE quando lo usa nelle colonne.
    status_enum = postgresql.ENUM(
        *_STATUS_VALUES,
        name="ghlsupportticketstatusenum",
        create_type=False,
    )

    # ── ghl_support_tickets ──────────────────────────────────────────────
    op.create_table(
        "ghl_support_tickets",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("ticket_number", sa.String(length=20), nullable=False),
        # Identità GHL (stringhe, no FK)
        sa.Column("ghl_user_id", sa.String(length=50), nullable=False),
        sa.Column("ghl_user_email", sa.String(length=255), nullable=True),
        sa.Column("ghl_user_name", sa.String(length=255), nullable=True),
        sa.Column("ghl_user_role", sa.String(length=50), nullable=True),
        sa.Column("ghl_location_id", sa.String(length=50), nullable=True),
        sa.Column("ghl_location_name", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        # Contesto tecnico
        sa.Column("pagina_origine", sa.String(length=500), nullable=True),
        sa.Column("browser", sa.String(length=120), nullable=True),
        sa.Column("os", sa.String(length=120), nullable=True),
        sa.Column("user_agent_raw", sa.Text(), nullable=True),
        sa.Column(
            "status",
            status_enum,
            nullable=False,
            server_default=sa.text("'nuovo'::ghlsupportticketstatusenum"),
        ),
        # Sync ClickUp
        sa.Column("clickup_task_id", sa.String(length=50), nullable=True),
        sa.Column("clickup_task_url", sa.String(length=500), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("sync_error", sa.Text(), nullable=True),
        sa.Column(
            "sync_attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("ticket_number", name="uq_ghl_support_tickets_number"),
        sa.UniqueConstraint("clickup_task_id", name="uq_ghl_support_tickets_clickup_task"),
    )
    op.create_index(
        "ix_ghl_support_tickets_ticket_number",
        "ghl_support_tickets",
        ["ticket_number"],
    )
    op.create_index(
        "ix_ghl_support_tickets_ghl_user_id",
        "ghl_support_tickets",
        ["ghl_user_id"],
    )
    op.create_index(
        "ix_ghl_support_tickets_ghl_location_id",
        "ghl_support_tickets",
        ["ghl_location_id"],
    )
    op.create_index(
        "ix_ghl_support_tickets_status",
        "ghl_support_tickets",
        ["status"],
    )
    op.create_index(
        "ix_ghl_support_tickets_clickup_task_id",
        "ghl_support_tickets",
        ["clickup_task_id"],
    )

    # ── ghl_support_ticket_comments ──────────────────────────────────────
    op.create_table(
        "ghl_support_ticket_comments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("author_ghl_user_id", sa.String(length=50), nullable=True),
        sa.Column("author_ghl_user_name", sa.String(length=255), nullable=True),
        sa.Column("author_name_external", sa.String(length=255), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("clickup_comment_id", sa.String(length=50), nullable=True),
        sa.Column(
            "direction",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'from_ghl'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["ghl_support_tickets.id"],
            ondelete="CASCADE",
            name="fk_ghl_support_ticket_comments_ticket_id",
        ),
        sa.UniqueConstraint(
            "clickup_comment_id", name="uq_ghl_support_ticket_comments_clickup_id"
        ),
    )
    op.create_index(
        "ix_ghl_support_ticket_comments_ticket_id",
        "ghl_support_ticket_comments",
        ["ticket_id"],
    )
    op.create_index(
        "ix_ghl_support_ticket_comments_clickup_comment_id",
        "ghl_support_ticket_comments",
        ["clickup_comment_id"],
    )

    # ── ghl_support_ticket_attachments ───────────────────────────────────
    op.create_table(
        "ghl_support_ticket_attachments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("uploaded_by_ghl_user_id", sa.String(length=50), nullable=True),
        sa.Column("uploaded_by_ghl_user_name", sa.String(length=255), nullable=True),
        sa.Column("clickup_attachment_id", sa.String(length=100), nullable=True),
        sa.Column(
            "synced_to_clickup",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["ghl_support_tickets.id"],
            ondelete="CASCADE",
            name="fk_ghl_support_ticket_attachments_ticket_id",
        ),
    )
    op.create_index(
        "ix_ghl_support_ticket_attachments_ticket_id",
        "ghl_support_ticket_attachments",
        ["ticket_id"],
    )


def downgrade():
    op.drop_index(
        "ix_ghl_support_ticket_attachments_ticket_id",
        table_name="ghl_support_ticket_attachments",
    )
    op.drop_table("ghl_support_ticket_attachments")

    op.drop_index(
        "ix_ghl_support_ticket_comments_clickup_comment_id",
        table_name="ghl_support_ticket_comments",
    )
    op.drop_index(
        "ix_ghl_support_ticket_comments_ticket_id",
        table_name="ghl_support_ticket_comments",
    )
    op.drop_table("ghl_support_ticket_comments")

    op.drop_index("ix_ghl_support_tickets_clickup_task_id", table_name="ghl_support_tickets")
    op.drop_index("ix_ghl_support_tickets_status", table_name="ghl_support_tickets")
    op.drop_index("ix_ghl_support_tickets_ghl_location_id", table_name="ghl_support_tickets")
    op.drop_index("ix_ghl_support_tickets_ghl_user_id", table_name="ghl_support_tickets")
    op.drop_index("ix_ghl_support_tickets_ticket_number", table_name="ghl_support_tickets")
    op.drop_table("ghl_support_tickets")

    op.execute("DROP TYPE IF EXISTS ghlsupportticketstatusenum")
