"""
Aggiunge le colonne professional_comment* alle tabelle check responses (solo se mancano)
e imposta alembic_version a b8c9d0e1f2a3 (merge head).

Usare quando il DB è già "avanti" rispetto ai file (es. revisione cebcc3042e2d)
e upgrade fallisce per colonne già esistenti.

Eseguire da backend:
  cd backend && FLASK_APP=corposostenibile poetry run python scripts/local_db_ops/apply_professional_comment_columns_and_stamp.py
"""
from __future__ import annotations

import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
os.chdir(backend_dir)
if not os.environ.get("FLASK_APP"):
    os.environ["FLASK_APP"] = "corposostenibile"

from corposostenibile import create_app
from corposostenibile.extensions import db


def column_exists(session, table: str, column: str) -> bool:
    r = session.execute(
        db.text(
            "SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    )
    return r.fetchone() is not None


def main() -> int:
    app = create_app()
    with app.app_context():
        session = db.session
        tables_columns = [
            ("weekly_check_responses", ["professional_comment", "professional_comment_by_id", "professional_comment_at"]),
            ("dca_check_responses", ["professional_comment", "professional_comment_by_id", "professional_comment_at"]),
            ("minor_check_responses", ["professional_comment", "professional_comment_by_id", "professional_comment_at"]),
        ]
        for table, columns in tables_columns:
            for col in columns:
                if not column_exists(session, table, col):
                    if col == "professional_comment":
                        session.execute(db.text(f'ALTER TABLE {table} ADD COLUMN {col} TEXT'))
                    elif col == "professional_comment_by_id":
                        session.execute(db.text(f'ALTER TABLE {table} ADD COLUMN {col} INTEGER REFERENCES users(id)'))
                    else:
                        session.execute(db.text(f'ALTER TABLE {table} ADD COLUMN {col} TIMESTAMP'))
                    print(f"Aggiunta colonna {table}.{col}")
                else:
                    print(f"Colonna {table}.{col} già presente")
        # FK names (se le colonne sono state appena create, le FK potrebbero mancare)
        fks = [
            ("weekly_check_responses", "professional_comment_by_id", "fk_weekly_check_responses_professional_comment_by_id_users"),
            ("dca_check_responses", "professional_comment_by_id", "fk_dca_check_responses_professional_comment_by_id_users"),
            ("minor_check_responses", "professional_comment_by_id", "fk_minor_check_responses_professional_comment_by_id_users"),
        ]
        for table, col, fk_name in fks:
            if not column_exists(session, table, col):
                continue
            r = session.execute(
                db.text(
                    "SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = :n AND table_schema = 'public'"
                ),
                {"n": fk_name},
            )
            if r.fetchone() is None:
                session.execute(
                    db.text(
                        f"ALTER TABLE {table} ADD CONSTRAINT {fk_name} FOREIGN KEY ({col}) REFERENCES users(id)"
                    )
                )
                print(f"Aggiunta FK {fk_name}")
        session.commit()
        # Imposta revisione a merge head
        session.execute(db.text("DELETE FROM alembic_version"))
        session.execute(db.text("INSERT INTO alembic_version (version_num) VALUES ('b8c9d0e1f2a3')"))
        session.commit()
        print("alembic_version impostata a b8c9d0e1f2a3 (merge head).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
