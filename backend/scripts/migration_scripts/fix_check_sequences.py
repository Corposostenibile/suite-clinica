#!/usr/bin/env python3
"""
Fix PostgreSQL sequences for check-related tables.

After data imports/migrations with explicit IDs, the auto-increment sequences
can get out of sync, causing UniqueViolation errors on INSERT.

This script resets all check-related sequences to MAX(id) + 1.

Usage (standalone — reads DATABASE_URL from backend/.env):
  cd backend
  poetry run python scripts/migration_scripts/fix_check_sequences.py

Usage (with explicit DB URL):
  poetry run python scripts/migration_scripts/fix_check_sequences.py \
    --database-url postgresql://user:pass@host:5432/dbname

Usage (via Flask shell — production):
  flask shell
  >>> from scripts.migration_scripts.fix_check_sequences import fix_all_sequences
  >>> fix_all_sequences()
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Tables whose sequences need fixing
TABLES_TO_FIX = [
    "weekly_checks",
    "weekly_check_responses",
    "weekly_check_link_assignments",
    "dca_checks",
    "dca_check_responses",
    "minor_checks",
    "minor_check_responses",
]


def fix_all_sequences(connection=None):
    """
    Reset sequences for all check-related tables.

    If `connection` is None, uses SQLAlchemy's current db.session (Flask context).
    Otherwise uses the provided DBAPI connection.
    """
    if connection is None:
        # Flask context — use db.session
        from corposostenibile import db
        _fix_with_session(db.session)
    else:
        _fix_with_connection(connection)


def _fix_with_session(session):
    """Fix sequences using Flask-SQLAlchemy session."""
    from sqlalchemy import text

    for table in TABLES_TO_FIX:
        seq_name = f"{table}_id_seq"
        result = session.execute(
            text(f"SELECT MAX(id) FROM {table}")
        ).scalar()
        max_id = result or 0

        session.execute(
            text(f"SELECT setval(:seq, GREATEST(:max_id, 1), true)"),
            {"seq": seq_name, "max_id": max_id},
        )
        print(f"  {seq_name}: reset to {max(max_id, 1)}")

    session.commit()
    print("\nAll sequences fixed.")


def _fix_with_connection(conn):
    """Fix sequences using a raw DBAPI/psycopg2 connection."""
    cur = conn.cursor()
    for table in TABLES_TO_FIX:
        seq_name = f"{table}_id_seq"
        cur.execute(f"SELECT MAX(id) FROM {table}")
        row = cur.fetchone()
        max_id = row[0] if row and row[0] else 0

        cur.execute(
            "SELECT setval(%s, GREATEST(%s, 1), true)",
            (seq_name, max_id),
        )
        print(f"  {seq_name}: reset to {max(max_id, 1)}")

    conn.commit()
    cur.close()
    print("\nAll sequences fixed.")


def _load_database_url() -> str | None:
    """Read DATABASE_URL from backend/.env."""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return None
    for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        if key.strip() == "DATABASE_URL":
            return val.strip().strip("'").strip('"')
    return None


def main():
    parser = argparse.ArgumentParser(description="Fix check-related PK sequences")
    parser.add_argument("--database-url", help="PostgreSQL connection string")
    args = parser.parse_args()

    db_url = args.database_url or _load_database_url()
    if not db_url:
        print("ERROR: No DATABASE_URL found. Pass --database-url or set it in .env")
        sys.exit(1)

    print(f"Connecting to: {db_url.split('@')[-1]}")  # hide credentials
    print(f"Fixing sequences for: {', '.join(TABLES_TO_FIX)}\n")

    import psycopg2
    conn = psycopg2.connect(db_url)
    try:
        _fix_with_connection(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
