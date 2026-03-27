"""add marketing consents data model

Revision ID: marketing_consents_01
Revises: video_review_requests_01
Create Date: 2026-03-23 11:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "marketing_consents_01"
down_revision = "video_review_requests_01"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("clienti", sa.Column("note_marketing", sa.Text(), nullable=True))
    op.add_column("clienti_version", sa.Column("note_marketing", sa.Text(), nullable=True))

    op.execute(
        "CREATE TYPE public.marketingflagtypeenum AS ENUM "
        "('usabile_marketing', 'stories_editata', 'carosello_editato', 'videofeedback_editato')"
    )
    op.execute(
        "CREATE TYPE public.marketingcontenttypeenum AS ENUM "
        "('stories', 'carosello', 'videofeedback')"
    )

    op.create_table(
        "cliente_marketing_flags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cliente_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "flag_type",
            sa.Enum(
                "usabile_marketing",
                "stories_editata",
                "carosello_editato",
                "videofeedback_editato",
                name="marketingflagtypeenum",
                schema="public",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("checked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("checked_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["cliente_id"], ["clienti.cliente_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cliente_id", "flag_type", name="uq_cliente_marketing_flags_cliente_tipo"),
    )
    op.create_index("ix_cliente_marketing_flags_cliente_id", "cliente_marketing_flags", ["cliente_id"])

    op.create_table(
        "cliente_marketing_content",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cliente_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "content_type",
            sa.Enum(
                "stories",
                "carosello",
                "videofeedback",
                name="marketingcontenttypeenum",
                schema="public",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("checked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("checked_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["cliente_id"], ["clienti.cliente_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cliente_marketing_content_cliente_id", "cliente_marketing_content", ["cliente_id"])
    op.create_index("ix_cliente_marketing_content_content_type", "cliente_marketing_content", ["content_type"])

    op.create_table(
        "cliente_marketing_influencers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("marketing_content_id", sa.Integer(), nullable=False),
        sa.Column("influencer_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["marketing_content_id"], ["cliente_marketing_content.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["influencer_id"], ["influencers.influencer_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("marketing_content_id", "influencer_id", name="uq_marketing_content_influencer"),
    )
    op.create_index("ix_cliente_marketing_influencers_content_id", "cliente_marketing_influencers", ["marketing_content_id"])
    op.create_index("ix_cliente_marketing_influencers_influencer_id", "cliente_marketing_influencers", ["influencer_id"])


def downgrade():
    op.drop_index("ix_cliente_marketing_influencers_influencer_id", table_name="cliente_marketing_influencers")
    op.drop_index("ix_cliente_marketing_influencers_content_id", table_name="cliente_marketing_influencers")
    op.drop_table("cliente_marketing_influencers")

    op.drop_index("ix_cliente_marketing_content_content_type", table_name="cliente_marketing_content")
    op.drop_index("ix_cliente_marketing_content_cliente_id", table_name="cliente_marketing_content")
    op.drop_table("cliente_marketing_content")

    op.drop_index("ix_cliente_marketing_flags_cliente_id", table_name="cliente_marketing_flags")
    op.drop_table("cliente_marketing_flags")

    op.execute("DROP TYPE IF EXISTS public.marketingcontenttypeenum")
    op.execute("DROP TYPE IF EXISTS public.marketingflagtypeenum")
    op.drop_column("clienti_version", "note_marketing")
    op.drop_column("clienti", "note_marketing")
