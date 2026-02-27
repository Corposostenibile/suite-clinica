"""
Applica in modo idempotente le colonne durata_*_giorni su:
- clienti
- clienti_version

Serve quando lo schema DB è indietro rispetto ai modelli (UndefinedColumn) ma
non è possibile eseguire le migrazioni Alembic standard per mismatch storico.

Eseguire da backend:
  cd backend && FLASK_APP=corposostenibile poetry run python scripts/local_db_ops/apply_durata_servizio_giorni_columns.py
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
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=:t AND column_name=:c"
        ),
        {"t": table, "c": column},
    )
    return r.fetchone() is not None


def ensure_int_column(session, table: str, column: str) -> None:
    if column_exists(session, table, column):
        print(f"Colonna {table}.{column} già presente")
        return
    session.execute(db.text(f"ALTER TABLE {table} ADD COLUMN {column} INTEGER"))
    print(f"Aggiunta colonna {table}.{column}")


def populate_from_dates(session) -> None:
    # Per colonne DATE: (date2 - date1) -> integer days in Postgres
    session.execute(
        db.text(
            """
            UPDATE clienti
            SET durata_nutrizione_giorni = (data_scadenza_nutrizione - data_inizio_nutrizione)
            WHERE durata_nutrizione_giorni IS NULL
              AND data_inizio_nutrizione IS NOT NULL
              AND data_scadenza_nutrizione IS NOT NULL
            """
        )
    )
    session.execute(
        db.text(
            """
            UPDATE clienti
            SET durata_coach_giorni = (data_scadenza_coach - data_inizio_coach)
            WHERE durata_coach_giorni IS NULL
              AND data_inizio_coach IS NOT NULL
              AND data_scadenza_coach IS NOT NULL
            """
        )
    )
    session.execute(
        db.text(
            """
            UPDATE clienti
            SET durata_psicologia_giorni = (data_scadenza_psicologia - data_inizio_psicologia)
            WHERE durata_psicologia_giorni IS NULL
              AND data_inizio_psicologia IS NOT NULL
              AND data_scadenza_psicologia IS NOT NULL
            """
        )
    )


def main() -> int:
    app = create_app()
    with app.app_context():
        session = db.session
        for table in ("clienti", "clienti_version"):
            ensure_int_column(session, table, "durata_nutrizione_giorni")
            ensure_int_column(session, table, "durata_coach_giorni")
            ensure_int_column(session, table, "durata_psicologia_giorni")

        populate_from_dates(session)
        session.commit()
        print("[ok] Colonne durata_*_giorni applicate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

