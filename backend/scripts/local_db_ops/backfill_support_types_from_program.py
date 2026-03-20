#!/usr/bin/env python3
"""
Backfill dei campi tipologia supporto cliente a partire da `programma_attuale`.

Uso tipico (DB locale/VPS, legge backend/.env):
    poetry run python scripts/local_db_ops/backfill_support_types_from_program.py --dry-run
    poetry run python scripts/local_db_ops/backfill_support_types_from_program.py

Per default:
- aggiorna `tipologia_supporto_nutrizione` / `tipologia_supporto_coach` solo se vuoti
- aggiorna `tipologia_cliente` solo se vuoto e ricavabile dal pacchetto
- non sovrascrive valori esistenti, a meno di `--overwrite`
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from sqlalchemy import select, update

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import Cliente, TipologiaClienteEnum
from corposostenibile.package_support import parse_package_support


@dataclass
class Stats:
    scanned: int = 0
    matched_program: int = 0
    updated_rows: int = 0
    updated_tipologia_cliente: int = 0
    updated_support_nutrizione: int = 0
    updated_support_coach: int = 0
    unchanged: int = 0
    skipped_no_program: int = 0
    skipped_unparsed: int = 0


def _normalize_tipologia_cliente(value: str | None) -> TipologiaClienteEnum | None:
    if value not in {"a", "b", "c"}:
        return None
    return TipologiaClienteEnum(value)


def _needs_update(current_value, new_value: str | None, overwrite: bool) -> bool:
    if new_value in (None, ""):
        return False
    if overwrite:
        return current_value != new_value
    return current_value in (None, "")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill tipologie supporto cliente da programma_attuale."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Non salva modifiche; stampa solo il riepilogo.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Sovrascrive anche i valori gia' presenti.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limita il numero di clienti processati (0 = nessun limite).",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=10,
        help="Numero di righe aggiornate da stampare in output.",
    )
    args = parser.parse_args()

    app = create_app()
    stats = Stats()
    changed_samples: list[dict[str, object]] = []

    with app.app_context():
        clienti_table = Cliente.__table__
        query = select(
            clienti_table.c.cliente_id,
            clienti_table.c.nome_cognome,
            clienti_table.c.programma_attuale,
            clienti_table.c.tipologia_cliente,
            clienti_table.c.tipologia_supporto_nutrizione,
            clienti_table.c.tipologia_supporto_coach,
        ).order_by(clienti_table.c.cliente_id.asc())
        if args.limit and args.limit > 0:
            query = query.limit(args.limit)

        clienti = db.session.execute(query).all()

        for cliente in clienti:
            stats.scanned += 1
            programma = (cliente.programma_attuale or "").strip()
            if not programma:
                stats.skipped_no_program += 1
                continue

            parsed = parse_package_support(programma)
            support = parsed.get("support_types", {}) or {}
            parsed_tipologia_cliente = parsed.get("client_type")
            parsed_nutrizione = support.get("nutrizione")
            parsed_coach = support.get("coach")

            if not any([parsed_tipologia_cliente, parsed_nutrizione, parsed_coach]):
                stats.skipped_unparsed += 1
                continue

            stats.matched_program += 1
            row_changed = False
            update_values: dict[str, object] = {}
            sample_row = {
                "cliente_id": cliente.cliente_id,
                "nome_cognome": cliente.nome_cognome,
                "programma_attuale": programma,
            }

            if _needs_update(cliente.tipologia_supporto_nutrizione, parsed_nutrizione, args.overwrite):
                sample_row["tipologia_supporto_nutrizione_old"] = cliente.tipologia_supporto_nutrizione
                sample_row["tipologia_supporto_nutrizione_new"] = parsed_nutrizione
                update_values["tipologia_supporto_nutrizione"] = parsed_nutrizione
                stats.updated_support_nutrizione += 1
                row_changed = True

            if _needs_update(cliente.tipologia_supporto_coach, parsed_coach, args.overwrite):
                sample_row["tipologia_supporto_coach_old"] = cliente.tipologia_supporto_coach
                sample_row["tipologia_supporto_coach_new"] = parsed_coach
                update_values["tipologia_supporto_coach"] = parsed_coach
                stats.updated_support_coach += 1
                row_changed = True

            current_tipologia_cliente = (
                cliente.tipologia_cliente.value
                if hasattr(cliente.tipologia_cliente, "value")
                else cliente.tipologia_cliente
            )
            if _needs_update(current_tipologia_cliente, parsed_tipologia_cliente, args.overwrite):
                normalized = _normalize_tipologia_cliente(parsed_tipologia_cliente)
                if normalized is not None:
                    sample_row["tipologia_cliente_old"] = current_tipologia_cliente
                    sample_row["tipologia_cliente_new"] = parsed_tipologia_cliente
                    update_values["tipologia_cliente"] = normalized
                    stats.updated_tipologia_cliente += 1
                    row_changed = True

            if row_changed:
                db.session.execute(
                    update(clienti_table)
                    .where(clienti_table.c.cliente_id == cliente.cliente_id)
                    .values(**update_values)
                )
                stats.updated_rows += 1
                if len(changed_samples) < max(args.sample, 0):
                    changed_samples.append(sample_row)
            else:
                stats.unchanged += 1

        if args.dry_run:
            db.session.rollback()
        else:
            db.session.commit()

    mode = "DRY-RUN" if args.dry_run else "APPLIED"
    print(f"[{mode}] Backfill tipologie supporto da programma_attuale")
    print(f"Scanned: {stats.scanned}")
    print(f"Matched program: {stats.matched_program}")
    print(f"Updated rows: {stats.updated_rows}")
    print(f"Updated tipologia_cliente: {stats.updated_tipologia_cliente}")
    print(f"Updated tipologia_supporto_nutrizione: {stats.updated_support_nutrizione}")
    print(f"Updated tipologia_supporto_coach: {stats.updated_support_coach}")
    print(f"Unchanged: {stats.unchanged}")
    print(f"Skipped no program: {stats.skipped_no_program}")
    print(f"Skipped unparsed: {stats.skipped_unparsed}")

    if changed_samples:
        print("\nSample updated rows:")
        for row in changed_samples:
            print(row)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
