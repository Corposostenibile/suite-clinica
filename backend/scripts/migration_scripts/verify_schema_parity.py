#!/usr/bin/env python3
"""Fail-fast schema parity check between SQLAlchemy metadata and live DB."""

from __future__ import annotations

import sys
from collections import defaultdict

from sqlalchemy import inspect
from sqlalchemy import text

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import StatoClienteEnum


def _is_public_table(table_key: str) -> bool:
    if "." not in table_key:
        return True
    schema, _ = table_key.split(".", 1)
    return schema == "public"


def _qi(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def main() -> int:
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        db_tables = set(inspector.get_table_names(schema="public"))

        model_tables = {}
        for key, table in db.Model.metadata.tables.items():
            if not _is_public_table(key):
                continue
            model_tables[table.name] = table

        missing_tables = sorted(name for name in model_tables if name not in db_tables)
        missing_columns = defaultdict(list)

        for table_name, table in model_tables.items():
            if table_name not in db_tables:
                continue
            db_cols = {c["name"] for c in inspector.get_columns(table_name, schema="public")}
            model_cols = {c.name for c in table.columns}
            for col in sorted(model_cols - db_cols):
                missing_columns[table_name].append(col)

        total_missing_cols = sum(len(v) for v in missing_columns.values())

        allowed_stato_values = {v.value for v in StatoClienteEnum}
        enum_issues: list[tuple[str, str, str, int]] = []
        enum_cols = db.session.execute(
            text(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND udt_name = 'statoclienteenum'
                ORDER BY table_name, column_name
                """
            )
        ).fetchall()
        for table_name, column_name in enum_cols:
            sql = (
                f"SELECT { _qi(column_name) }::text AS val, count(*) AS cnt "
                f"FROM public.{ _qi(table_name) } "
                f"WHERE { _qi(column_name) } IS NOT NULL "
                f"GROUP BY 1"
            )
            for row in db.session.execute(text(sql)).fetchall():
                val = row[0]
                cnt = int(row[1] or 0)
                if val not in allowed_stato_values:
                    enum_issues.append((table_name, column_name, val, cnt))

        if not missing_tables and total_missing_cols == 0 and not enum_issues:
            print("[schema-parity] OK: schema allineato ai model")
            return 0

        print("[schema-parity] FAIL: schema non allineato ai model")
        if missing_tables:
            print(f"[schema-parity] missing_tables={len(missing_tables)}")
            for name in missing_tables:
                print(f"[schema-parity]   table:{name}")
        if total_missing_cols:
            print(f"[schema-parity] missing_columns={total_missing_cols}")
            for table_name in sorted(missing_columns):
                for col in missing_columns[table_name]:
                    print(f"[schema-parity]   column:{table_name}.{col}")
        if enum_issues:
            print(f"[schema-parity] invalid_enum_values={len(enum_issues)}")
            for table_name, column_name, value, count in enum_issues:
                print(
                    "[schema-parity]   enum:"
                    f"{table_name}.{column_name} value={value} count={count}"
                )
        return 1


if __name__ == "__main__":
    sys.exit(main())
