"""Add Trustpilot API fields and indexes

Revision ID: tp01_add_trustpilot_api_fields
Revises: 16225c8cf0a7, b2c3d4e5f6a7, c7f8e9d0a1b2, cb02_durata_servizio_giorni, d8e7f6a5b4c3, e2dd6adb402d
Create Date: 2026-03-14 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "tp01_add_trustpilot_api_fields"
down_revision = (
    "16225c8cf0a7",
    "b2c3d4e5f6a7",
    "c7f8e9d0a1b2",
    "cb02_durata_servizio_giorni",
    "d8e7f6a5b4c3",
    "e2dd6adb402d",
)
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))


def upgrade():
    if not _table_exists("trustpilot_reviews"):
        op.create_table(
            "trustpilot_reviews",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("cliente_id", sa.BigInteger(), sa.ForeignKey("clienti.cliente_id"), nullable=False),
            sa.Column("richiesta_da_professionista_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("data_richiesta", sa.DateTime(), nullable=False),
            sa.Column("invitation_method", sa.String(length=50), nullable=True),
            sa.Column("invitation_status", sa.String(length=50), nullable=True),
            sa.Column("trustpilot_reference_id", sa.String(length=120), nullable=True),
            sa.Column("trustpilot_invitation_id", sa.String(length=120), nullable=True),
            sa.Column("trustpilot_review_id", sa.String(length=120), nullable=True),
            sa.Column("trustpilot_link", sa.Text(), nullable=True),
            sa.Column("pubblicata", sa.Boolean(), nullable=True),
            sa.Column("data_pubblicazione", sa.DateTime(), nullable=True),
            sa.Column("stelle", sa.Integer(), nullable=True),
            sa.Column("testo_recensione", sa.Text(), nullable=True),
            sa.Column("titolo_recensione", sa.String(length=255), nullable=True),
            sa.Column("deleted_at_trustpilot", sa.DateTime(), nullable=True),
            sa.Column("webhook_received_at", sa.DateTime(), nullable=True),
            sa.Column("trustpilot_payload_last", sa.JSON(), nullable=True),
            sa.Column("bonus_distribution", sa.JSON(), nullable=True),
            sa.Column("applied_to_quarter", sa.String(length=10), nullable=True),
            sa.Column("applied_to_week_start", sa.Date(), nullable=True),
            sa.Column("confermata_da_hm_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("data_conferma_hm", sa.DateTime(), nullable=True),
            sa.Column("note_interne", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
    else:
        with op.batch_alter_table("trustpilot_reviews", schema=None) as batch_op:
            if not _column_exists("trustpilot_reviews", "invitation_method"):
                batch_op.add_column(sa.Column("invitation_method", sa.String(length=50), nullable=True))
            if not _column_exists("trustpilot_reviews", "invitation_status"):
                batch_op.add_column(sa.Column("invitation_status", sa.String(length=50), nullable=True))
            if not _column_exists("trustpilot_reviews", "trustpilot_reference_id"):
                batch_op.add_column(sa.Column("trustpilot_reference_id", sa.String(length=120), nullable=True))
            if not _column_exists("trustpilot_reviews", "trustpilot_invitation_id"):
                batch_op.add_column(sa.Column("trustpilot_invitation_id", sa.String(length=120), nullable=True))
            if not _column_exists("trustpilot_reviews", "trustpilot_review_id"):
                batch_op.add_column(sa.Column("trustpilot_review_id", sa.String(length=120), nullable=True))
            if not _column_exists("trustpilot_reviews", "trustpilot_link"):
                batch_op.add_column(sa.Column("trustpilot_link", sa.Text(), nullable=True))
            if not _column_exists("trustpilot_reviews", "titolo_recensione"):
                batch_op.add_column(sa.Column("titolo_recensione", sa.String(length=255), nullable=True))
            if not _column_exists("trustpilot_reviews", "deleted_at_trustpilot"):
                batch_op.add_column(sa.Column("deleted_at_trustpilot", sa.DateTime(), nullable=True))
            if not _column_exists("trustpilot_reviews", "webhook_received_at"):
                batch_op.add_column(sa.Column("webhook_received_at", sa.DateTime(), nullable=True))
            if not _column_exists("trustpilot_reviews", "trustpilot_payload_last"):
                batch_op.add_column(sa.Column("trustpilot_payload_last", sa.JSON(), nullable=True))

    if not _index_exists("trustpilot_reviews", "idx_cliente_review"):
        op.create_index("idx_cliente_review", "trustpilot_reviews", ["cliente_id"], unique=False)
    if not _index_exists("trustpilot_reviews", "idx_richiedente"):
        op.create_index("idx_richiedente", "trustpilot_reviews", ["richiesta_da_professionista_id"], unique=False)
    if not _index_exists("trustpilot_reviews", "idx_quarter"):
        op.create_index("idx_quarter", "trustpilot_reviews", ["applied_to_quarter"], unique=False)
    if not _index_exists("trustpilot_reviews", "idx_pubblicata"):
        op.create_index("idx_pubblicata", "trustpilot_reviews", ["pubblicata"], unique=False)
    if not _index_exists("trustpilot_reviews", "idx_trustpilot_reference"):
        op.create_index("idx_trustpilot_reference", "trustpilot_reviews", ["trustpilot_reference_id"], unique=False)
    if not _index_exists("trustpilot_reviews", "idx_trustpilot_review_id"):
        op.create_index("idx_trustpilot_review_id", "trustpilot_reviews", ["trustpilot_review_id"], unique=False)

    with op.batch_alter_table("trustpilot_reviews", schema=None) as batch_op:
        if not _index_exists("trustpilot_reviews", "ix_trustpilot_reviews_invitation_status"):
            batch_op.create_index(batch_op.f("ix_trustpilot_reviews_invitation_status"), ["invitation_status"], unique=False)
        if not _index_exists("trustpilot_reviews", "ix_trustpilot_reviews_trustpilot_invitation_id"):
            batch_op.create_index(batch_op.f("ix_trustpilot_reviews_trustpilot_invitation_id"), ["trustpilot_invitation_id"], unique=False)
        if not _index_exists("trustpilot_reviews", "ix_trustpilot_reviews_trustpilot_reference_id"):
            batch_op.create_index(batch_op.f("ix_trustpilot_reviews_trustpilot_reference_id"), ["trustpilot_reference_id"], unique=True)
        if not _index_exists("trustpilot_reviews", "ix_trustpilot_reviews_trustpilot_review_id"):
            batch_op.create_index(batch_op.f("ix_trustpilot_reviews_trustpilot_review_id"), ["trustpilot_review_id"], unique=True)


def downgrade():
    if not _table_exists("trustpilot_reviews"):
        return

    with op.batch_alter_table("trustpilot_reviews", schema=None) as batch_op:
        for index_name in (
            "ix_trustpilot_reviews_trustpilot_review_id",
            "ix_trustpilot_reviews_trustpilot_reference_id",
            "ix_trustpilot_reviews_trustpilot_invitation_id",
            "ix_trustpilot_reviews_invitation_status",
        ):
            if _index_exists("trustpilot_reviews", index_name):
                batch_op.drop_index(index_name)

    for index_name in (
        "idx_trustpilot_review_id",
        "idx_trustpilot_reference",
    ):
        if _index_exists("trustpilot_reviews", index_name):
            op.drop_index(index_name, table_name="trustpilot_reviews")

    with op.batch_alter_table("trustpilot_reviews", schema=None) as batch_op:
        for column_name in (
            "trustpilot_payload_last",
            "webhook_received_at",
            "deleted_at_trustpilot",
            "titolo_recensione",
            "trustpilot_link",
            "trustpilot_review_id",
            "trustpilot_invitation_id",
            "trustpilot_reference_id",
            "invitation_status",
            "invitation_method",
        ):
            if _column_exists("trustpilot_reviews", column_name):
                batch_op.drop_column(column_name)
