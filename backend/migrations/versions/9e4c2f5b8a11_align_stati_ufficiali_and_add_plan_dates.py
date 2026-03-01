"""align_stati_ufficiali_and_add_plan_dates

Revision ID: 9e4c2f5b8a11
Revises: 16225c8cf0a7
Create Date: 2026-02-13

Allinea gli stati ufficiali cliente rimuovendo i legacy "insoluto"/"freeze"
e aggiunge le date inizio/scadenza per piano (nutrizione/coach/psicologia).
"""

from __future__ import annotations

import re

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9e4c2f5b8a11"
down_revision = "16225c8cf0a7"
branch_labels = None
depends_on = None


PLAN_DATE_COLUMNS = (
    ("data_inizio_nutrizione", sa.Date()),
    ("data_scadenza_nutrizione", sa.Date()),
    ("data_inizio_coach", sa.Date()),
    ("data_scadenza_coach", sa.Date()),
    ("data_inizio_psicologia", sa.Date()),
    ("data_scadenza_psicologia", sa.Date()),
)


def _q(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _extract_enum_default_value(column_default: str | None) -> str | None:
    if not column_default:
        return None
    match = re.search(r"'([^']+)'::", column_default)
    if not match:
        return None
    return match.group(1)


def _normalize_stato(value: str) -> str:
    mapping = {
        "insoluto": "stop",
        "freeze": "pausa",
    }
    return mapping.get(value, value)


def _add_plan_date_columns() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {c["name"] for c in inspector.get_columns("clienti")}

    for name, coltype in PLAN_DATE_COLUMNS:
        if name not in existing_cols:
            op.add_column("clienti", sa.Column(name, coltype, nullable=True))


def _drop_plan_date_columns() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_cols = {c["name"] for c in inspector.get_columns("clienti")}

    for name, _ in reversed(PLAN_DATE_COLUMNS):
        if name in existing_cols:
            op.drop_column("clienti", name)


def _upgrade_postgres_enum() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT
                table_schema,
                table_name,
                column_name,
                column_default
            FROM information_schema.columns
            WHERE lower(udt_name) = 'statoclienteenum'
              AND table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY table_schema, table_name, ordinal_position
            """
        )
    ).fetchall()

    if not rows:
        return

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'statoclienteenum_new') THEN
                CREATE TYPE statoclienteenum_new AS ENUM ('attivo', 'ghost', 'pausa', 'stop');
            END IF;
        END
        $$;
        """
    )

    for row in rows:
        schema_q = _q(row.table_schema)
        table_q = _q(row.table_name)
        col_q = _q(row.column_name)
        full_table = f"{schema_q}.{table_q}"

        default_value = _extract_enum_default_value(row.column_default)
        normalized_default = _normalize_stato(default_value) if default_value else None

        op.execute(sa.text(f"ALTER TABLE {full_table} ALTER COLUMN {col_q} DROP DEFAULT"))

        op.execute(
            sa.text(
                f"""
                UPDATE {full_table}
                SET {col_q} = CASE
                    WHEN {col_q}::text = 'insoluto' THEN 'stop'::statoclienteenum
                    WHEN {col_q}::text = 'freeze' THEN 'pausa'::statoclienteenum
                    ELSE {col_q}
                END
                WHERE {col_q}::text IN ('insoluto', 'freeze')
                """
            )
        )

        op.execute(
            sa.text(
                f"""
                ALTER TABLE {full_table}
                ALTER COLUMN {col_q} TYPE statoclienteenum_new
                USING CASE
                    WHEN {col_q}::text = 'insoluto' THEN 'stop'
                    WHEN {col_q}::text = 'freeze' THEN 'pausa'
                    ELSE {col_q}::text
                END::statoclienteenum_new
                """
            )
        )

        if normalized_default:
            op.execute(
                sa.text(
                    f"ALTER TABLE {full_table} ALTER COLUMN {col_q} "
                    f"SET DEFAULT '{normalized_default}'::statoclienteenum_new"
                )
            )

    op.execute("DROP TYPE statoclienteenum")
    op.execute("ALTER TYPE statoclienteenum_new RENAME TO statoclienteenum")


def _downgrade_postgres_enum() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT
                table_schema,
                table_name,
                column_name,
                column_default
            FROM information_schema.columns
            WHERE lower(udt_name) = 'statoclienteenum'
              AND table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY table_schema, table_name, ordinal_position
            """
        )
    ).fetchall()

    if not rows:
        return

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'statoclienteenum_old') THEN
                CREATE TYPE statoclienteenum_old AS ENUM ('attivo', 'ghost', 'pausa', 'stop', 'insoluto', 'freeze');
            END IF;
        END
        $$;
        """
    )

    for row in rows:
        schema_q = _q(row.table_schema)
        table_q = _q(row.table_name)
        col_q = _q(row.column_name)
        full_table = f"{schema_q}.{table_q}"

        default_value = _extract_enum_default_value(row.column_default)
        op.execute(sa.text(f"ALTER TABLE {full_table} ALTER COLUMN {col_q} DROP DEFAULT"))

        op.execute(
            sa.text(
                f"""
                ALTER TABLE {full_table}
                ALTER COLUMN {col_q} TYPE statoclienteenum_old
                USING {col_q}::text::statoclienteenum_old
                """
            )
        )

        if default_value:
            op.execute(
                sa.text(
                    f"ALTER TABLE {full_table} ALTER COLUMN {col_q} "
                    f"SET DEFAULT '{default_value}'::statoclienteenum_old"
                )
            )

    op.execute("DROP TYPE statoclienteenum")
    op.execute("ALTER TYPE statoclienteenum_old RENAME TO statoclienteenum")


def upgrade():
    _add_plan_date_columns()
    if op.get_bind().dialect.name == "postgresql":
        _upgrade_postgres_enum()


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        _downgrade_postgres_enum()
    _drop_plan_date_columns()

