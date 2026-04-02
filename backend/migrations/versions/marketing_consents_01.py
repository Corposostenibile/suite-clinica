"""Add marketing consent tables and note_marketing column

Revision ID: marketing_consents_01
Revises: patologie_coach_01
Create Date: 2026-04-02 12:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "marketing_consents_01"
down_revision = "patologie_coach_01"
branch_labels = None
depends_on = None


def upgrade():
    # --- Enum types (idempotent via DO $$ block) ---
    conn = op.get_bind()
    conn.execute(sa.text(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'marketingflagtypeenum') THEN "
        "CREATE TYPE marketingflagtypeenum AS ENUM ('usabile_marketing','stories_editata','carosello_editato','videofeedback_editato'); "
        "END IF; END $$;"
    ))
    conn.execute(sa.text(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'marketingcontenttypeenum') THEN "
        "CREATE TYPE marketingcontenttypeenum AS ENUM ('stories','carosello','videofeedback'); "
        "END IF; END $$;"
    ))
    marketingflagtype = sa.Enum(
        "usabile_marketing", "stories_editata", "carosello_editato", "videofeedback_editato",
        name="marketingflagtypeenum", create_type=False,
    )
    marketingcontenttype = sa.Enum(
        "stories", "carosello", "videofeedback",
        name="marketingcontenttypeenum", create_type=False,
    )

    # --- note_marketing on clienti (idempotent) ---
    conn.execute(sa.text(
        "ALTER TABLE clienti ADD COLUMN IF NOT EXISTS note_marketing TEXT"
    ))

    # --- Tables (idempotent: skip if already exists) ---
    tables_exist = {row[0] for row in conn.execute(sa.text(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
    ))}

    if "cliente_marketing_flags" not in tables_exist:
        op.create_table(
            "cliente_marketing_flags",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("cliente_id", sa.BigInteger(), sa.ForeignKey("clienti.cliente_id", ondelete="CASCADE"), nullable=False),
            sa.Column("flag_type", marketingflagtype, nullable=False),
            sa.Column("checked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("checked_date", sa.Date(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.UniqueConstraint("cliente_id", "flag_type", name="uq_cliente_marketing_flags_cliente_tipo"),
        )
        op.create_index("ix_cliente_marketing_flags_cliente_id", "cliente_marketing_flags", ["cliente_id"])

    if "cliente_marketing_content" not in tables_exist:
        op.create_table(
            "cliente_marketing_content",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("cliente_id", sa.BigInteger(), sa.ForeignKey("clienti.cliente_id", ondelete="CASCADE"), nullable=False),
            sa.Column("content_type", marketingcontenttype, nullable=False),
            sa.Column("checked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("checked_date", sa.Date(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        )
        op.create_index("ix_cliente_marketing_content_cliente_id", "cliente_marketing_content", ["cliente_id"])
        op.create_index("ix_cliente_marketing_content_content_type", "cliente_marketing_content", ["content_type"])

    if "cliente_marketing_influencers" not in tables_exist:
        op.create_table(
            "cliente_marketing_influencers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("marketing_content_id", sa.Integer(), sa.ForeignKey("cliente_marketing_content.id", ondelete="CASCADE"), nullable=False),
            sa.Column("influencer_id", sa.Integer(), sa.ForeignKey("influencers.influencer_id", ondelete="CASCADE"), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.UniqueConstraint("marketing_content_id", "influencer_id", name="uq_marketing_content_influencer"),
        )
        op.create_index("ix_cliente_marketing_influencers_content_id", "cliente_marketing_influencers", ["marketing_content_id"])
        op.create_index("ix_cliente_marketing_influencers_influencer_id", "cliente_marketing_influencers", ["influencer_id"])


def downgrade():
    op.drop_table("cliente_marketing_influencers")
    op.drop_table("cliente_marketing_content")
    op.drop_table("cliente_marketing_flags")
    op.drop_column("clienti", "note_marketing")
    sa.Enum(name="marketingcontenttypeenum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="marketingflagtypeenum").drop(op.get_bind(), checkfirst=True)
