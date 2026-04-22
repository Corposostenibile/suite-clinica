"""
backfill_scadenze.py
====================

Popola i campi *cache* di scadenza sui clienti esistenti che hanno
``data_inizio_*`` + ``durata_*_giorni`` valorizzati ma il campo target ``NULL``.

Campi interessati:

* ``data_rinnovo``             = ``data_inizio_abbonamento + durata_programma_giorni``
* ``data_scadenza_nutrizione`` = ``data_inizio_nutrizione + durata_nutrizione_giorni``
* ``data_scadenza_coach``      = ``data_inizio_coach + durata_coach_giorni``
* ``data_scadenza_psicologia`` = ``data_inizio_psicologia + durata_psicologia_giorni``

**Safety**: l'UPDATE tocca solo righe dove il campo target e` NULL; non sovrascrive
mai valori gia` impostati (override manuali, rinnovi custom, ecc.).

**Nota**: usa SQL raw (non ORM), quindi le modifiche non sono tracciate in
SQLAlchemy-Continuum. E` un backfill one-shot; la prevenzione delle future
regressioni e` demandata al listener in ``customers.events``.

Uso
---

::

    # dry-run (default: mostra conteggi, nessuna modifica)
    python backend/scripts/migration_scripts/backfill_scadenze.py

    # apply reale
    python backend/scripts/migration_scripts/backfill_scadenze.py --apply

In produzione, via kubectl::

    kubectl exec -i deployment/suite-clinica-backend -c backend -- \
        bash -lc 'PYTHONPATH=/app python /app/scripts/migration_scripts/backfill_scadenze.py'
    # poi, se i conteggi sono ok:
    kubectl exec -i deployment/suite-clinica-backend -c backend -- \
        bash -lc 'PYTHONPATH=/app python /app/scripts/migration_scripts/backfill_scadenze.py --apply'
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

from sqlalchemy import text

from corposostenibile import create_app
from corposostenibile.extensions import db


@dataclass(frozen=True)
class Campo:
    target: str
    inizio: str
    durata: str


CAMPI: tuple[Campo, ...] = (
    Campo("data_rinnovo",             "data_inizio_abbonamento", "durata_programma_giorni"),
    Campo("data_scadenza_nutrizione", "data_inizio_nutrizione",  "durata_nutrizione_giorni"),
    Campo("data_scadenza_coach",      "data_inizio_coach",       "durata_coach_giorni"),
    Campo("data_scadenza_psicologia", "data_inizio_psicologia",  "durata_psicologia_giorni"),
)


def _count_calcolabili(conn, c: Campo) -> int:
    sql = text(
        f"""
        SELECT COUNT(*) FROM clienti
        WHERE {c.target} IS NULL
          AND {c.inizio} IS NOT NULL
          AND {c.durata} IS NOT NULL
          AND {c.durata} > 0
        """
    )
    return int(conn.execute(sql).scalar_one())


def _count_target_null(conn, c: Campo) -> int:
    sql = text(f"SELECT COUNT(*) FROM clienti WHERE {c.target} IS NULL")
    return int(conn.execute(sql).scalar_one())


def _apply_update(conn, c: Campo) -> int:
    # In PostgreSQL DATE + INTEGER = DATE (somma giorni).
    sql = text(
        f"""
        UPDATE clienti
        SET {c.target} = {c.inizio} + {c.durata}
        WHERE {c.target} IS NULL
          AND {c.inizio} IS NOT NULL
          AND {c.durata} IS NOT NULL
          AND {c.durata} > 0
        """
    )
    return conn.execute(sql).rowcount


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill campi cache di scadenza su Cliente"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Applica le UPDATE al DB (default: dry-run, nessuna modifica).",
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        mode = "APPLY" if args.apply else "DRY-RUN"
        print(f"Backfill scadenze — modalita': {mode}\n")

        # Engine.begin() apre una transazione e committa all'uscita (o rollback su errore).
        with db.engine.begin() as conn:
            print("Stato pre-update:")
            for campo in CAMPI:
                null_count = _count_target_null(conn, campo)
                calc = _count_calcolabili(conn, campo)
                print(
                    f"  {campo.target:30s}  NULL totali: {null_count:6d}   "
                    f"di cui calcolabili: {calc:6d}"
                )

            totale_calcolabili = sum(_count_calcolabili(conn, c) for c in CAMPI)
            print(f"\n  TOTALE righe candidate all'update: {totale_calcolabili}")

            if not args.apply:
                print("\nDry-run: nessuna modifica eseguita. Rilancia con --apply.")
                return 0

            print("\nApplicazione UPDATE...")
            totale_modificati = 0
            for campo in CAMPI:
                n = _apply_update(conn, campo)
                print(f"  {campo.target:30s}  aggiornati: {n}")
                totale_modificati += n

            print(f"\n  TOTALE righe aggiornate: {totale_modificati}")

            print("\nStato post-update:")
            for campo in CAMPI:
                null_count = _count_target_null(conn, campo)
                calc = _count_calcolabili(conn, campo)
                print(
                    f"  {campo.target:30s}  NULL rimasti: {null_count:6d}   "
                    f"calcolabili residui: {calc:6d}"
                )

    return 0


if __name__ == "__main__":
    sys.exit(main())
