#!/usr/bin/env python3
"""C.2 - Backfill storico HM da SalesLead old-suite a ClienteProfessionistaHistory.

Scopo
-----
Materializzare in `ClienteProfessionistaHistory` lo storico assegnazioni HM
pregresse salvate nel flusso Assegnazioni v1 (`SalesLead` con source_system='old_suite').

Regole (safe)
-------------
- NON modifica le assegnazioni operative correnti.
- NON tocca il pannello pubblico sales.
- Crea solo record history attivi mancanti per il ruolo HM (`tipo_professionista='health_manager'`).

Origine dati
------------
1) locale: `SalesLead` old_suite con HM assegnato
2) fallback: produzione (`PRODUCTION_DATABASE_URL` o `PROD_DATABASE_URL`) se nel DB locale non ci sono lead utili

Target
------
`ClienteProfessionistaHistory`

Uso
---
cd backend
poetry run python scripts/seed_hm_history_from_saleslead.py --dry-run
poetry run python scripts/seed_hm_history_from_saleslead.py --apply
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

# Permette import corposostenibile quando eseguito da backend/scripts/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from corposostenibile import create_app  # noqa: E402
from corposostenibile.extensions import db  # noqa: E402
from corposostenibile.models import (  # noqa: E402
    Cliente,
    ClienteProfessionistaHistory,
    SalesLead,
    User,
)


HM_TIPO = "health_manager"


@dataclass
class Counters:
    leads_scanned: int = 0
    missing_cliente: int = 0
    missing_professionista: int = 0
    existing_active: int = 0
    to_create: int = 0
    created: int = 0
    from_local: int = 0
    from_production: int = 0


@dataclass
class LeadSeedRow:
    id: int
    converted_to_client_id: int
    health_manager_id: int
    assigned_by: int | None
    converted_by: int | None
    assigned_at: datetime | None
    converted_at: datetime | None
    created_at: datetime | None
    unique_code: str | None
    source_label: str


def _pick_default_assigned_by_id() -> int | None:
    admin = User.query.filter(User.is_admin.is_(True)).order_by(User.id.asc()).first()
    if admin:
        return int(admin.id)
    first_user = User.query.order_by(User.id.asc()).first()
    return int(first_user.id) if first_user else None


def _is_valid_user_id(user_id: int | None) -> bool:
    if not user_id:
        return False
    return db.session.get(User, int(user_id)) is not None


def _resolve_assigned_by_id(row: LeadSeedRow, *, default_assigned_by_id: int | None) -> int:
    for candidate in (row.assigned_by, row.converted_by, row.health_manager_id, default_assigned_by_id):
        if candidate and _is_valid_user_id(int(candidate)):
            return int(candidate)
    raise RuntimeError(
        f"Impossibile risolvere assegnato_da_id per lead id={row.id}. "
        "Nessun utente valido disponibile."
    )


def _resolve_data_dal(row: LeadSeedRow):
    dt = row.assigned_at or row.converted_at or row.created_at or datetime.now(timezone.utc)
    return dt.date()


def _iter_local_candidate_leads() -> Iterable[LeadSeedRow]:
    leads = (
        SalesLead.query.filter(
            SalesLead.source_system == "old_suite",
            SalesLead.converted_to_client_id.isnot(None),
            SalesLead.health_manager_id.isnot(None),
        )
        .order_by(SalesLead.id.asc())
        .all()
    )

    return [
        LeadSeedRow(
            id=int(lead.id),
            converted_to_client_id=int(lead.converted_to_client_id),
            health_manager_id=int(lead.health_manager_id),
            assigned_by=int(lead.assigned_by) if lead.assigned_by else None,
            converted_by=int(lead.converted_by) if lead.converted_by else None,
            assigned_at=lead.assigned_at,
            converted_at=lead.converted_at,
            created_at=lead.created_at,
            unique_code=lead.unique_code,
            source_label="local",
        )
        for lead in leads
    ]


def _iter_production_candidate_leads() -> Iterable[LeadSeedRow]:
    db_url = (os.getenv("PRODUCTION_DATABASE_URL") or os.getenv("PROD_DATABASE_URL") or "").strip()
    if not db_url:
        print("[INFO] Nessun URL produzione configurato (PRODUCTION_DATABASE_URL / PROD_DATABASE_URL).")
        return []

    try:
        import psycopg2  # type: ignore
    except Exception as exc:  # pragma: no cover
        print(f"[WARN] psycopg2 non disponibile, salto fallback produzione: {exc}")
        return []

    sql_with_source_system = """
        SELECT
            id,
            converted_to_client_id,
            health_manager_id,
            assigned_by,
            converted_by,
            assigned_at,
            converted_at,
            created_at,
            unique_code
        FROM sales_leads
        WHERE source_system = 'old_suite'
          AND converted_to_client_id IS NOT NULL
          AND health_manager_id IS NOT NULL
        ORDER BY id ASC
    """

    # Compat: alcuni dump/DB produzione storici non hanno la colonna source_system.
    sql_without_source_system = """
        SELECT
            id,
            converted_to_client_id,
            health_manager_id,
            assigned_by,
            converted_by,
            assigned_at,
            converted_at,
            created_at,
            unique_code
        FROM sales_leads
        WHERE converted_to_client_id IS NOT NULL
          AND health_manager_id IS NOT NULL
        ORDER BY id ASC
    """

    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'sales_leads'
                      AND column_name = 'source_system'
                )
                """
            )
            has_source_system = bool(cur.fetchone()[0])
            cur.execute(sql_with_source_system if has_source_system else sql_without_source_system)
            rows = cur.fetchall()
    except Exception as exc:
        print(f"[WARN] Impossibile leggere SalesLead da produzione: {exc}")
        return []
    finally:
        try:
            conn.close()  # type: ignore[name-defined]
        except Exception:
            pass

    out: list[LeadSeedRow] = []
    for r in rows:
        out.append(
            LeadSeedRow(
                id=int(r[0]),
                converted_to_client_id=int(r[1]),
                health_manager_id=int(r[2]),
                assigned_by=int(r[3]) if r[3] else None,
                converted_by=int(r[4]) if r[4] else None,
                assigned_at=r[5],
                converted_at=r[6],
                created_at=r[7],
                unique_code=r[8],
                source_label="production",
            )
        )

    return out


def run(*, apply: bool) -> int:
    app = create_app()
    counters = Counters()

    with app.app_context():
        default_assigned_by_id = _pick_default_assigned_by_id()

        leads = list(_iter_local_candidate_leads())
        if leads:
            counters.from_local = len(leads)
            print(f"Lead candidate locali trovate: {len(leads)}")
        else:
            print("Lead candidate locali con HM non trovate. Provo fallback da produzione...")
            leads = list(_iter_production_candidate_leads())
            counters.from_production = len(leads)
            print(f"Lead candidate produzione trovate: {len(leads)}")

        if not leads:
            print("Nessun dato da processare.")
            return 0

        for row in leads:
            counters.leads_scanned += 1
            cliente_id = int(row.converted_to_client_id)

            cliente = db.session.get(Cliente, cliente_id)
            if not cliente:
                counters.missing_cliente += 1
                print(f"[WARN] Cliente mancante per lead_id={row.id} cliente_id={cliente_id}")
                continue

            hm_user_id = int(row.health_manager_id)
            if not _is_valid_user_id(hm_user_id):
                counters.missing_professionista += 1
                print(
                    f"[WARN] HM mancante: lead_id={row.id} cliente_id={cliente_id} "
                    f"tipo={HM_TIPO} user_id={hm_user_id}"
                )
                continue

            existing_active = ClienteProfessionistaHistory.query.filter_by(
                cliente_id=cliente_id,
                user_id=hm_user_id,
                tipo_professionista=HM_TIPO,
                is_active=True,
            ).first()

            if existing_active:
                counters.existing_active += 1
                continue

            counters.to_create += 1
            data_dal = _resolve_data_dal(row)
            motivazione = (
                "Backfill C.2 HM da SalesLead old_suite "
                f"(source={row.source_label}, lead_id={row.id}, unique_code={row.unique_code or 'N/D'})"
            )
            assegnato_da_id = _resolve_assigned_by_id(
                row,
                default_assigned_by_id=default_assigned_by_id,
            )

            history_row = ClienteProfessionistaHistory(
                cliente_id=cliente_id,
                user_id=hm_user_id,
                tipo_professionista=HM_TIPO,
                data_dal=data_dal,
                motivazione_aggiunta=motivazione,
                assegnato_da_id=assegnato_da_id,
                is_active=True,
            )
            db.session.add(history_row)

            if apply:
                counters.created += 1
                print(
                    f"[CREATE] cliente_id={cliente_id} tipo={HM_TIPO} user_id={hm_user_id} "
                    f"lead_id={row.id} data_dal={data_dal} source={row.source_label}"
                )
            else:
                print(
                    f"[DRY]    cliente_id={cliente_id} tipo={HM_TIPO} user_id={hm_user_id} "
                    f"lead_id={row.id} data_dal={data_dal} source={row.source_label}"
                )

        if apply:
            db.session.commit()
        else:
            db.session.rollback()

        print("\n=== SUMMARY C.2 HM ===")
        print(f"Leads scansionate:       {counters.leads_scanned}")
        print(f"Leads da locale:         {counters.from_local}")
        print(f"Leads da produzione:     {counters.from_production}")
        print(f"History attive già ok:   {counters.existing_active}")
        print(f"History da creare:       {counters.to_create}")
        print(f"History create:          {counters.created if apply else 0}")
        print(f"Clienti mancanti:        {counters.missing_cliente}")
        print(f"HM mancanti:             {counters.missing_professionista}")
        print(f"Modalità:                {'APPLY' if apply else 'DRY-RUN'}")

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill C.2 storico HM da SalesLead old_suite")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Esegue simulazione senza scrivere su DB")
    mode.add_argument("--apply", action="store_true", help="Applica modifiche su DB")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    apply = bool(args.apply)
    return run(apply=apply)


if __name__ == "__main__":
    raise SystemExit(main())
