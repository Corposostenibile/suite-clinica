"""add_marketing_fields_to_cliente

Aggiunge 11 colonne marketing_* alla tabella clienti (e a clienti_version
per sqlalchemy-continuum). Tutte nullable o con default sicuro per non
impattare righe esistenti.

Revision ID: mk02_cliente_marketing_flags
Revises: mk01_add_marketing_user_role
Create Date: 2026-04-24
"""
from alembic import op
import sqlalchemy as sa


revision = "mk02_cliente_marketing_flags"
down_revision = "mk01_add_marketing_user_role"
branch_labels = None
depends_on = None


BOOL_COLS = [
    "marketing_videofeedback",
    "marketing_videofeedback_richiesto",
    "marketing_videofeedback_svolto",
    "marketing_videofeedback_condiviso",
    "marketing_trasformazione_fisica",
    "marketing_trasformazione_fisica_condivisa",
    "marketing_trasformazione",
    "marketing_exit_call_richiesta",
    "marketing_exit_call_svolta",
    "marketing_exit_call_condivisa",
]


def _table_exists(conn, table: str) -> bool:
    row = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = :t"
        ),
        {"t": table},
    ).fetchone()
    return row is not None


def upgrade() -> None:
    conn = op.get_bind()

    for table in ("clienti", "clienti_version"):
        if not _table_exists(conn, table):
            # clienti_version potrebbe non esistere su setup minimali — skip safe
            continue

        for col in BOOL_COLS:
            # Su clienti_version i default non si applicano (è una tabella di storia);
            # nullable=True ovunque per evitare problemi su righe gia esistenti.
            default_clause = " DEFAULT FALSE" if table == "clienti" else ""
            conn.execute(
                sa.text(
                    f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} BOOLEAN{default_clause}'
                )
            )


def downgrade() -> None:
    conn = op.get_bind()

    for table in ("clienti_version", "clienti"):
        if not _table_exists(conn, table):
            continue
        for col in BOOL_COLS:
            conn.execute(
                sa.text(f'ALTER TABLE {table} DROP COLUMN IF EXISTS {col}')
            )
