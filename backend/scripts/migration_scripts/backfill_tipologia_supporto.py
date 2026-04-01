"""
Backfill tipologia_supporto_nutrizione e tipologia_supporto_coach per tutti i clienti.

Logica:
  1. Parsa `programma_attuale` per determinare quali ruoli (N, C, P) sono previsti
  2. Il primo ruolo nel programma è il PRIMARIO → prende la tipologia (a, b, c)
  3. I ruoli successivi sono SECONDARI → prendono "secondario"
  4. La tipologia viene estratta dal pacchetto; se non presente, fallback a `tipologia_cliente`
  5. Solo i ruoli previsti nel programma vengono valorizzati

Uso:
  cd backend
  python scripts/migration_scripts/backfill_tipologia_supporto.py            # dry-run
  python scripts/migration_scripts/backfill_tipologia_supporto.py --commit   # applica
  python scripts/migration_scripts/backfill_tipologia_supporto.py --commit --only-empty
"""

import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR))

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import Cliente, TipologiaClienteEnum
from corposostenibile.package_support import parse_package_support

BATCH_SIZE = 200


def backfill(commit: bool = False, only_empty: bool = False):
    app = create_app()
    with app.app_context():
        # Query leggera: solo le colonne necessarie, no ORM objects in memoria
        cols = [
            Cliente.cliente_id,
            Cliente.nome_cognome,
            Cliente.programma_attuale,
            Cliente.tipologia_cliente,
            Cliente.tipologia_supporto_nutrizione,
            Cliente.tipologia_supporto_coach,
        ]
        query = db.session.query(*cols)

        if only_empty:
            query = query.filter(
                db.or_(
                    Cliente.tipologia_supporto_nutrizione.is_(None),
                    Cliente.tipologia_supporto_coach.is_(None),
                )
            )

        rows = query.all()
        total = len(rows)

        updated = 0
        skipped_no_programma = 0
        skipped_no_roles = 0
        skipped_no_type = 0
        skipped_unchanged = 0
        changes = []

        for row in rows:
            programma = row.programma_attuale
            if not programma or not str(programma).strip():
                skipped_no_programma += 1
                continue

            parsed = parse_package_support(programma)
            ordered_roles = parsed.get("ordered_roles", [])
            support_roles = [r for r in ordered_roles if r in ("nutrizione", "coach")]

            # Se nel programma non ci sono né N né C, skip
            if not support_roles:
                skipped_no_roles += 1
                continue

            # Tipologia dal pacchetto; fallback a tipologia_cliente
            client_type = parsed.get("client_type")
            if client_type is None and row.tipologia_cliente:
                if row.tipologia_cliente.value in {"a", "b", "c"}:
                    client_type = row.tipologia_cliente.value

            # Nessuna tipologia disponibile → skip
            if client_type is None:
                skipped_no_type += 1
                continue

            # Calcola: primario prende la tipologia, secondari prendono "secondario"
            new_nutri = None
            new_coach = None
            primary = support_roles[0]
            if primary == "nutrizione":
                new_nutri = client_type
            else:
                new_coach = client_type
            for sec in support_roles[1:]:
                if sec == "nutrizione":
                    new_nutri = "secondario"
                else:
                    new_coach = "secondario"

            old_nutri = row.tipologia_supporto_nutrizione
            old_coach = row.tipologia_supporto_coach

            if only_empty:
                if old_nutri is not None:
                    new_nutri = old_nutri
                if old_coach is not None:
                    new_coach = old_coach

            if old_nutri == new_nutri and old_coach == new_coach:
                skipped_unchanged += 1
                continue

            changes.append({
                "id": row.cliente_id,
                "nome": row.nome_cognome,
                "programma": programma,
                "tipologia_cliente": row.tipologia_cliente.value if row.tipologia_cliente else None,
                "old_nutri": old_nutri,
                "new_nutri": new_nutri,
                "old_coach": old_coach,
                "new_coach": new_coach,
            })
            updated += 1

        # Report
        print(f"\n{'=' * 70}")
        print(f"BACKFILL TIPOLOGIA SUPPORTO — {'COMMIT' if commit else 'DRY-RUN'}")
        print(f"{'=' * 70}")
        print(f"Clienti totali analizzati:     {total}")
        print(f"Aggiornati:                    {updated}")
        print(f"Skip (no programma):           {skipped_no_programma}")
        print(f"Skip (no ruoli N/C):           {skipped_no_roles}")
        print(f"Skip (no tipologia a/b/c):     {skipped_no_type}")
        print(f"Skip (già corretto):           {skipped_unchanged}")
        print(f"{'=' * 70}\n")

        if changes:
            print(f"{'ID':<8} {'Nome':<30} {'Programma':<20} {'Tipo':<6} "
                  f"{'Nutri old':<12} {'Nutri new':<12} {'Coach old':<12} {'Coach new':<12}")
            print("-" * 120)
            for ch in changes:
                print(f"{ch['id']:<8} {(ch['nome'] or '')[:28]:<30} "
                      f"{(ch['programma'] or '')[:18]:<20} {(ch['tipologia_cliente'] or '-'):<6} "
                      f"{(ch['old_nutri'] or '-'):<12} {(ch['new_nutri'] or '-'):<12} "
                      f"{(ch['old_coach'] or '-'):<12} {(ch['new_coach'] or '-'):<12}")

        # Applica in batch via UPDATE diretto (no ORM load)
        if commit and changes:
            for i in range(0, len(changes), BATCH_SIZE):
                batch = changes[i:i + BATCH_SIZE]
                for ch in batch:
                    db.session.execute(
                        db.update(Cliente)
                        .where(Cliente.cliente_id == ch["id"])
                        .values(
                            tipologia_supporto_nutrizione=ch["new_nutri"],
                            tipologia_supporto_coach=ch["new_coach"],
                        )
                    )
                db.session.commit()
                print(f"  Batch {i // BATCH_SIZE + 1}: {len(batch)} righe scritte.")
            print(f"\n✓ {updated} clienti aggiornati nel database.")
        elif not commit:
            print(f"\n→ Dry-run completato. Usa --commit per applicare le modifiche.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Backfill tipologia_supporto_nutrizione e tipologia_supporto_coach"
    )
    parser.add_argument(
        "--commit", action="store_true",
        help="Applica le modifiche al database (default: dry-run)",
    )
    parser.add_argument(
        "--only-empty", action="store_true",
        help="Aggiorna solo clienti con campi vuoti (non sovrascrive valori esistenti)",
    )
    args = parser.parse_args()
    backfill(commit=args.commit, only_empty=args.only_empty)
