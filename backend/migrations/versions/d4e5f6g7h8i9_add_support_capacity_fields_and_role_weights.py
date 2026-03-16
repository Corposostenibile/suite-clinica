"""add support capacity fields and role weights

Revision ID: support_capacity_role_weights_01
Revises: capacity_type_weights_01
Create Date: 2026-03-16 11:30:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "support_capacity_role_weights_01"
down_revision = "capacity_type_weights_01"
branch_labels = None
depends_on = None


DEFAULT_ROWS = [
    {"role_type": "nutrizione", "tipo": "a", "peso": 2.0},
    {"role_type": "nutrizione", "tipo": "b", "peso": 1.5},
    {"role_type": "nutrizione", "tipo": "c", "peso": 1.0},
    {"role_type": "nutrizione", "tipo": "secondario", "peso": 0.5},
    {"role_type": "coach", "tipo": "a", "peso": 2.0},
    {"role_type": "coach", "tipo": "b", "peso": 1.5},
    {"role_type": "coach", "tipo": "c", "peso": 1.0},
    {"role_type": "coach", "tipo": "secondario", "peso": 0.5},
]


def upgrade():
    op.add_column(
        "clienti",
        sa.Column(
            "tipologia_supporto_nutrizione",
            sa.String(length=20),
            nullable=True,
            comment="Tipologia supporto nutrizione: a, b, c, secondario",
        ),
    )
    op.add_column(
        "clienti",
        sa.Column(
            "tipologia_supporto_coach",
            sa.String(length=20),
            nullable=True,
            comment="Tipologia supporto coach: a, b, c, secondario",
        ),
    )

    tbl = op.create_table(
        "capacity_role_type_weights",
        sa.Column("role_type", sa.String(length=20), primary_key=True, comment="Area professionale: nutrizione, coach"),
        sa.Column("tipo", sa.String(length=20), primary_key=True, comment="Tipologia supporto: a, b, c, secondario"),
        sa.Column("peso", sa.Float(), nullable=False, server_default="1.0", comment="Peso per il calcolo capienza"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
    )
    op.bulk_insert(tbl, DEFAULT_ROWS)


def downgrade():
    op.drop_table("capacity_role_type_weights")
    op.drop_column("clienti", "tipologia_supporto_coach")
    op.drop_column("clienti", "tipologia_supporto_nutrizione")
