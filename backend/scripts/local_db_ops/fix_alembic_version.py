"""
Aggiorna la tabella alembic_version da una revisione inesistente (cebcc3042e2d)
a una revisione valida (f688901c582d) così da poter eseguire poi:
  poetry run flask db upgrade b8c9d0e1f2a3

Eseguire dalla root del backend:
  cd backend && FLASK_APP=corposostenibile poetry run python scripts/local_db_ops/fix_alembic_version.py
"""
from __future__ import annotations

import os
import sys

# Assicura che backend sia nel path e che FLASK_APP sia impostato
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
os.chdir(backend_dir)
if not os.environ.get("FLASK_APP"):
    os.environ["FLASK_APP"] = "corposostenibile"

from corposostenibile import create_app
from corposostenibile.extensions import db


def main() -> int:
    app = create_app()
    with app.app_context():
        # Revisione attualmente nel DB (inesistente nei file)
        old_rev = "cebcc3042e2d"
        # Revisione valida da cui ripartire (prima della nostra migrazione + merge)
        new_rev = "f688901c582d"
        result = db.session.execute(
            db.text("UPDATE alembic_version SET version_num = :new WHERE version_num = :old"),
            {"new": new_rev, "old": old_rev},
        )
        db.session.commit()
        if result.rowcount == 0:
            # Prova senza WHERE per DB con una sola riga
            r2 = db.session.execute(db.text("SELECT version_num FROM alembic_version"))
            rows = r2.fetchall()
            if not rows:
                print("Nessuna riga in alembic_version.", file=sys.stderr)
                return 1
            print(f"Revisione attuale in DB: {rows[0][0]}")
            if rows[0][0] != old_rev:
                print(f"Non era {old_rev}. Imposta manualmente a {new_rev} se necessario.", file=sys.stderr)
                return 1
            db.session.execute(db.text("UPDATE alembic_version SET version_num = :new"), {"new": new_rev})
            db.session.commit()
        print(f"alembic_version aggiornata: {old_rev} -> {new_rev}")
        print("Ora esegui: poetry run flask db upgrade b8c9d0e1f2a3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
