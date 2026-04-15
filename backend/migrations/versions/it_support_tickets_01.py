"""create it_support_tickets, comments, attachments tables

Revision ID: it_support_tickets_01
Revises: live_trainings_coach_01
Create Date: 2026-04-13 23:00:00.000000

Tabelle per il sistema di ticket IT con sync bidirezionale ClickUp.
- it_support_tickets
- it_support_ticket_comments
- it_support_ticket_attachments
+ enum types: itsupportticketstatusenum, itsupporttickettipoenum,
              itsupportticketmoduloenum, itsupportticketcriticitaenum
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "it_support_tickets_01"
down_revision = "live_trainings_coach_01"
branch_labels = None
depends_on = None


# ── Enum definitions (Postgres) ───────────────────────────────────────────
_STATUS_VALUES = (
    "nuovo",
    "in_triage",
    "in_lavorazione",
    "in_attesa_utente",
    "da_testare",
    "risolto",
    "non_valido",
)
_TIPO_VALUES = ("bug", "dato_errato", "accesso", "lentezza")
_MODULO_VALUES = (
    "assegnazioni",
    "calendario",
    "check",
    "clienti",
    "dashboard",
    "formazione",
    "generico",
    "profilo",
    "quality",
    "supporto",
    "task",
    "team",
)
_CRITICITA_VALUES = ("bloccante", "non_bloccante")


def upgrade():
    conn = op.get_bind()

    # Enum types (idempotenti)
    conn.execute(
        sa.text(
            """
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'itsupportticketstatusenum') THEN
                    CREATE TYPE itsupportticketstatusenum AS ENUM (
                        'nuovo','in_triage','in_lavorazione','in_attesa_utente',
                        'da_testare','risolto','non_valido'
                    );
                END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'itsupporttickettipoenum') THEN
                    CREATE TYPE itsupporttickettipoenum AS ENUM (
                        'bug','dato_errato','accesso','lentezza'
                    );
                END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'itsupportticketmoduloenum') THEN
                    CREATE TYPE itsupportticketmoduloenum AS ENUM (
                        'assegnazioni','calendario','check','clienti','dashboard',
                        'formazione','generico','profilo','quality','supporto','task','team'
                    );
                END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'itsupportticketcriticitaenum') THEN
                    CREATE TYPE itsupportticketcriticitaenum AS ENUM (
                        'bloccante','non_bloccante'
                    );
                END IF;
            END $$;
            """
        )
    )

    # Dichiaro i tipi ENUM come "esterni" (create_type=False): i tipi vengono
    # creati al boot dell'app da register_enums(), quindi qui Alembic NON deve
    # emettere CREATE TYPE. postgresql.ENUM rispetta create_type=False mentre
    # sa.Enum no in tutte le versioni.
    tipo_enum = postgresql.ENUM(
        *_TIPO_VALUES, name="itsupporttickettipoenum", create_type=False
    )
    modulo_enum = postgresql.ENUM(
        *_MODULO_VALUES, name="itsupportticketmoduloenum", create_type=False
    )
    criticita_enum = postgresql.ENUM(
        *_CRITICITA_VALUES, name="itsupportticketcriticitaenum", create_type=False
    )
    status_enum = postgresql.ENUM(
        *_STATUS_VALUES, name="itsupportticketstatusenum", create_type=False
    )

    # ── it_support_tickets ───────────────────────────────────────────────
    op.create_table(
        "it_support_tickets",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("ticket_number", sa.String(length=20), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("tipo", tipo_enum, nullable=False),
        sa.Column("modulo", modulo_enum, nullable=False),
        sa.Column("criticita", criticita_enum, nullable=False),
        sa.Column("cliente_coinvolto", sa.String(length=255), nullable=True),
        sa.Column("link_registrazione", sa.String(length=500), nullable=True),
        sa.Column("pagina_origine", sa.String(length=500), nullable=True),
        sa.Column("browser", sa.String(length=120), nullable=True),
        sa.Column("os", sa.String(length=120), nullable=True),
        sa.Column("versione_app", sa.String(length=80), nullable=True),
        sa.Column("user_agent_raw", sa.Text(), nullable=True),
        sa.Column(
            "status",
            status_enum,
            nullable=False,
            server_default=sa.text("'nuovo'::itsupportticketstatusenum"),
        ),
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_it_support_tickets_user_id",
        ),
        sa.UniqueConstraint("ticket_number", name="uq_it_support_tickets_number"),
        sa.UniqueConstraint("clickup_task_id", name="uq_it_support_tickets_clickup_task"),
    )
    op.create_index(
        "ix_it_support_tickets_ticket_number",
        "it_support_tickets",
        ["ticket_number"],
    )
    op.create_index(
        "ix_it_support_tickets_user_id",
        "it_support_tickets",
        ["user_id"],
    )
    op.create_index(
        "ix_it_support_tickets_status",
        "it_support_tickets",
        ["status"],
    )
    op.create_index(
        "ix_it_support_tickets_tipo",
        "it_support_tickets",
        ["tipo"],
    )
    op.create_index(
        "ix_it_support_tickets_modulo",
        "it_support_tickets",
        ["modulo"],
    )
    op.create_index(
        "ix_it_support_tickets_criticita",
        "it_support_tickets",
        ["criticita"],
    )
    op.create_index(
        "ix_it_support_tickets_clickup_task_id",
        "it_support_tickets",
        ["clickup_task_id"],
    )

    # ── it_support_ticket_comments ───────────────────────────────────────
    op.create_table(
        "it_support_ticket_comments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("author_user_id", sa.Integer(), nullable=True),
        sa.Column("author_name_external", sa.String(length=255), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("clickup_comment_id", sa.String(length=50), nullable=True),
        sa.Column(
            "direction",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'from_suite'"),
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
            ["it_support_tickets.id"],
            ondelete="CASCADE",
            name="fk_it_support_ticket_comments_ticket_id",
        ),
        sa.ForeignKeyConstraint(
            ["author_user_id"],
            ["users.id"],
            name="fk_it_support_ticket_comments_author_user_id",
        ),
        sa.UniqueConstraint(
            "clickup_comment_id", name="uq_it_support_ticket_comments_clickup_id"
        ),
    )
    op.create_index(
        "ix_it_support_ticket_comments_ticket_id",
        "it_support_ticket_comments",
        ["ticket_id"],
    )
    op.create_index(
        "ix_it_support_ticket_comments_clickup_comment_id",
        "it_support_ticket_comments",
        ["clickup_comment_id"],
    )

    # ── it_support_ticket_attachments ────────────────────────────────────
    op.create_table(
        "it_support_ticket_attachments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=True),
        sa.Column("uploaded_by_id", sa.Integer(), nullable=True),
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
            ["it_support_tickets.id"],
            ondelete="CASCADE",
            name="fk_it_support_ticket_attachments_ticket_id",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_id"],
            ["users.id"],
            name="fk_it_support_ticket_attachments_uploaded_by_id",
        ),
    )
    op.create_index(
        "ix_it_support_ticket_attachments_ticket_id",
        "it_support_ticket_attachments",
        ["ticket_id"],
    )


def downgrade():
    op.drop_index("ix_it_support_ticket_attachments_ticket_id", table_name="it_support_ticket_attachments")
    op.drop_table("it_support_ticket_attachments")

    op.drop_index("ix_it_support_ticket_comments_clickup_comment_id", table_name="it_support_ticket_comments")
    op.drop_index("ix_it_support_ticket_comments_ticket_id", table_name="it_support_ticket_comments")
    op.drop_table("it_support_ticket_comments")

    op.drop_index("ix_it_support_tickets_clickup_task_id", table_name="it_support_tickets")
    op.drop_index("ix_it_support_tickets_criticita", table_name="it_support_tickets")
    op.drop_index("ix_it_support_tickets_modulo", table_name="it_support_tickets")
    op.drop_index("ix_it_support_tickets_tipo", table_name="it_support_tickets")
    op.drop_index("ix_it_support_tickets_status", table_name="it_support_tickets")
    op.drop_index("ix_it_support_tickets_user_id", table_name="it_support_tickets")
    op.drop_index("ix_it_support_tickets_ticket_number", table_name="it_support_tickets")
    op.drop_table("it_support_tickets")

    op.execute("DROP TYPE IF EXISTS itsupportticketstatusenum")
    op.execute("DROP TYPE IF EXISTS itsupporttickettipoenum")
    op.execute("DROP TYPE IF EXISTS itsupportticketmoduloenum")
    op.execute("DROP TYPE IF EXISTS itsupportticketcriticitaenum")
