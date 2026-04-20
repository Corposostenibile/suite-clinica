"""add_tipologia_check_assegnato_to_clienti_version

Revision ID: tip_chk_cli_ver_01
Revises: tipologia_check_assegnato_01
Create Date: 2026-04-20 11:25:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "tip_chk_cli_ver_01"
down_revision = "tipologia_check_assegnato_01"
branch_labels = None
depends_on = None


def _existing_columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if table_name not in tables:
        return set()
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade():
    existing = _existing_columns("clienti_version")
    if not existing:
        return

    if "tipologia_check_assegnato" not in existing:
        op.add_column(
            "clienti_version",
            sa.Column(
                "tipologia_check_assegnato",
                sa.Enum(
                    "regolare",
                    "minori",
                    "dca",
                    name="tipologiacheckenum",
                    create_type=False,
                ),
                nullable=True,
            ),
        )


def downgrade():
    existing = _existing_columns("clienti_version")
    if not existing:
        return

    if "tipologia_check_assegnato" in existing:
        op.drop_column("clienti_version", "tipologia_check_assegnato")
