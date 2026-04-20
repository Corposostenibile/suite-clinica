"""
Backfill Cliente.tipologia_check_assegnato in base ai check periodici attivi.

Regole:
  - WeeklyCheck attivo  -> regolare
  - DCACheck attivo     -> dca
  - MinorCheck attivo   -> minori
  - Nessun check attivo -> NULL
  - >= 2 tipologie attive -> warning ambiguita', non sovrascrive (default)

Uso:
  cd backend
  python scripts/migration_scripts/backfill_tipologia_check_assegnato.py
  python scripts/migration_scripts/backfill_tipologia_check_assegnato.py --commit
"""

import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import Cliente, DCACheck, MinorCheck, TipologiaCheckEnum, WeeklyCheck


def _active_types(cliente_id: int) -> list[str]:
    active = []
    if db.session.query(WeeklyCheck.id).filter_by(cliente_id=cliente_id, is_active=True).first():
        active.append("regolare")
    if db.session.query(DCACheck.id).filter_by(cliente_id=cliente_id, is_active=True).first():
        active.append("dca")
    if db.session.query(MinorCheck.id).filter_by(cliente_id=cliente_id, is_active=True).first():
        active.append("minori")
    return active


def run_backfill(commit: bool = False) -> None:
    app = create_app()
    with app.app_context():
        rows = db.session.query(Cliente.cliente_id, Cliente.nome_cognome, Cliente.tipologia_check_assegnato).all()

        to_update: list[tuple[int, TipologiaCheckEnum | None]] = []
        warnings: list[str] = []
        unchanged = 0
        empty = 0
        ambiguous = 0

        for cliente_id, nome_cognome, current_tipologia in rows:
            active = _active_types(cliente_id)
            if not active:
                desired = None
                empty += 1
            elif len(active) == 1:
                desired = TipologiaCheckEnum(active[0])
            else:
                ambiguous += 1
                warnings.append(
                    f"[WARN] Cliente {cliente_id} ({nome_cognome or '-'}) con check attivi multipli: {', '.join(active)}"
                )
                continue

            if current_tipologia == desired:
                unchanged += 1
                continue
            to_update.append((cliente_id, desired))

        print("\n" + "=" * 72)
        print(f"BACKFILL TIPOLOGIA CHECK ASSEGNATO - {'COMMIT' if commit else 'DRY-RUN'}")
        print("=" * 72)
        print(f"Clienti analizzati:                 {len(rows)}")
        print(f"Aggiornamenti previsti:            {len(to_update)}")
        print(f"Senza check attivi (NULL):         {empty}")
        print(f"Casi ambigui (warning):            {ambiguous}")
        print(f"Invariati:                         {unchanged}")
        print("=" * 72 + "\n")

        for warning in warnings:
            print(warning)

        if not commit:
            print("\nDry-run completato. Usa --commit per applicare le modifiche.")
            return

        for cliente_id, desired in to_update:
            db.session.execute(
                db.update(Cliente)
                .where(Cliente.cliente_id == cliente_id)
                .values(tipologia_check_assegnato=desired)
            )
        db.session.commit()
        print(f"\nOK: aggiornati {len(to_update)} clienti.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill tipologia_check_assegnato")
    parser.add_argument("--commit", action="store_true", help="Applica modifiche al DB")
    args = parser.parse_args()
    run_backfill(commit=args.commit)
