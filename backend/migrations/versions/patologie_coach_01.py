"""add coaching pathology fields and PatologiaCoachLog table

Revision ID: patologie_coach_01
Revises: rinnovo_referral_version_fix_01
Create Date: 2026-04-01 02:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "patologie_coach_01"
down_revision = "rinnovo_referral_version_fix_01"
branch_labels = None
depends_on = None


_COACH_BOOL_COLUMNS = [
    "nessuna_patologia_coach",
    "patologia_coach_dca",
    "patologia_coach_ipertensione",
    "patologia_coach_pcos",
    "patologia_coach_sindrome_metabolica",
    "patologia_coach_endometriosi",
    "patologia_coach_osteoporosi",
    "patologia_coach_menopausa",
    "patologia_coach_artrosi",
    "patologia_coach_artrite",
    "patologia_coach_sclerosi_multipla",
    "patologia_coach_fibromialgia",
    "patologia_coach_lipedema",
    "patologia_coach_linfedema",
    "patologia_coach_gravidanza",
    "patologia_coach_riabilitazione_anca",
    "patologia_coach_riabilitazione_spalla",
    "patologia_coach_riabilitazione_ginocchio",
    "patologia_coach_lombalgia",
    "patologia_coach_spondilolistesi",
    "patologia_coach_spondilolisi",
]


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # --- Add coaching pathology boolean columns to clienti ---
    existing_clienti = {col["name"] for col in inspector.get_columns("clienti")}
    for col_name in _COACH_BOOL_COLUMNS:
        if col_name not in existing_clienti:
            op.add_column("clienti", sa.Column(col_name, sa.Boolean(), server_default=sa.text("false"), nullable=True))

    if "patologia_coach_altro" not in existing_clienti:
        op.add_column("clienti", sa.Column("patologia_coach_altro", sa.Text(), nullable=True))

    # --- Add same columns to clienti_version (SQLAlchemy-Continuum) ---
    if inspector.has_table("clienti_version"):
        existing_version = {col["name"] for col in inspector.get_columns("clienti_version")}
        for col_name in _COACH_BOOL_COLUMNS:
            if col_name not in existing_version:
                op.add_column("clienti_version", sa.Column(col_name, sa.Boolean(), nullable=True))
        if "patologia_coach_altro" not in existing_version:
            op.add_column("clienti_version", sa.Column("patologia_coach_altro", sa.Text(), nullable=True))

    # --- Create PatologiaCoachLog table ---
    if not inspector.has_table("patologia_coach_log"):
        op.create_table(
            "patologia_coach_log",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("cliente_id", sa.Integer(), sa.ForeignKey("clienti.cliente_id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("patologia", sa.String(100), nullable=False, index=True),
            sa.Column("patologia_nome", sa.String(200), nullable=False),
            sa.Column("azione", sa.String(20), nullable=False),
            sa.Column("data_inizio", sa.DateTime(), nullable=False),
            sa.Column("data_fine", sa.DateTime(), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )


def downgrade():
    op.drop_table("patologia_coach_log")

    for col_name in reversed(_COACH_BOOL_COLUMNS):
        op.drop_column("clienti", col_name)
    op.drop_column("clienti", "patologia_coach_altro")

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("clienti_version"):
        for col_name in reversed(_COACH_BOOL_COLUMNS):
            op.drop_column("clienti_version", col_name)
        op.drop_column("clienti_version", "patologia_coach_altro")
