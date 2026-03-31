#!/usr/bin/env python3
"""
Import archivio check di esempio da CSV multi-sezione.

Uso:
    cd backend
    poetry run python scripts/import_example_checks.py --file ../esempi_check.csv
    poetry run python scripts/import_example_checks.py --file ../esempi_check.csv --dry-run
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dateutil import parser as date_parser
from unidecode import unidecode

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import Cliente, ExampleCheckEntry, ExampleCheckImportBatch


SECTION_SPLIT_RE = re.compile(r"\n={5,}\n", re.MULTILINE)


@dataclass
class ParsedRow:
    section_name: str
    external_response_id: str
    first_name: str | None
    last_name: str | None
    birth_date_raw: str | None
    submitted_at: datetime | None
    network_id: str | None
    response_type: str | None
    payload: dict[str, Any]
    raw_row_hash: str


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    value = unidecode(value).strip().lower()
    return re.sub(r"\s+", " ", value)


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return date_parser.parse(value)
    except Exception:
        return None


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _pick_field(payload: dict[str, Any], candidates: list[str]) -> str | None:
    normalized_map = {_normalize_text(k): v for k, v in payload.items()}
    for cand in candidates:
        val = normalized_map.get(_normalize_text(cand))
        if isinstance(val, str):
            cleaned = val.strip()
            if cleaned:
                return cleaned
    return None


def _extract_external_id(payload: dict[str, Any]) -> str | None:
    if "#" in payload and str(payload["#"]).strip():
        return str(payload["#"]).strip()
    first_key = next(iter(payload.keys()), None)
    if first_key is not None:
        first_val = str(payload[first_key]).strip()
        if first_val:
            return first_val
    return None


def parse_csv_sections(csv_path: Path) -> list[ParsedRow]:
    raw_content = csv_path.read_text(encoding="utf-8")
    blocks = [b.strip() for b in SECTION_SPLIT_RE.split(raw_content) if b.strip()]
    parsed_rows: list[ParsedRow] = []

    for block in blocks:
        lines = block.splitlines()
        if len(lines) < 2:
            continue

        section_name = lines[0].strip().rstrip(":")
        csv_data = "\n".join(lines[1:])
        reader = csv.DictReader(io.StringIO(csv_data))

        for raw_row in reader:
            payload = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in raw_row.items() if k}
            external_id = _extract_external_id(payload)
            if not external_id:
                continue

            first_name = _pick_field(payload, ["First name", "Nome", "Nome e cognome"])
            last_name = _pick_field(payload, ["Last name", "Cognome"])
            birth_date_raw = _pick_field(payload, ["*Data di nascita*", "Data di nascita", "Data di nascita  "])
            submit_raw = _pick_field(payload, ["Submit Date (UTC)", "Submit Date"])
            network_id = _pick_field(payload, ["Network ID"])
            response_type = _pick_field(payload, ["Response Type"])

            canonical_json = json.dumps(payload, ensure_ascii=True, sort_keys=True)
            parsed_rows.append(
                ParsedRow(
                    section_name=section_name,
                    external_response_id=external_id,
                    first_name=first_name,
                    last_name=last_name,
                    birth_date_raw=birth_date_raw,
                    submitted_at=_parse_date(submit_raw),
                    network_id=network_id,
                    response_type=response_type,
                    payload=payload,
                    raw_row_hash=_sha256_text(f"{section_name}|{external_id}|{canonical_json}"),
                )
            )
    return parsed_rows


def _split_name_if_needed(first_name: str | None, last_name: str | None) -> tuple[str | None, str | None]:
    if first_name and not last_name and " " in first_name:
        parts = [p for p in first_name.split(" ") if p.strip()]
        if len(parts) >= 2:
            return parts[0], " ".join(parts[1:])
    return first_name, last_name


def match_cliente_id(first_name: str | None, last_name: str | None, birth_date_raw: str | None) -> int | None:
    first_name, last_name = _split_name_if_needed(first_name, last_name)
    if not first_name:
        return None

    full_name_norm = _normalize_text(f"{first_name} {last_name or ''}".strip())
    birth_dt = _parse_date(birth_date_raw)

    query = Cliente.query
    if birth_dt:
        query = query.filter(Cliente.data_di_nascita == birth_dt.date())

    candidates = query.all()
    if not candidates:
        return None

    exact_matches = []
    for c in candidates:
        cliente_name_norm = _normalize_text(c.nome_cognome)
        if cliente_name_norm == full_name_norm:
            exact_matches.append(c)

    if len(exact_matches) == 1:
        return int(exact_matches[0].cliente_id)
    if len(exact_matches) > 1:
        return None

    # fallback: contiene entrambi i token principali
    tokens = [t for t in full_name_norm.split(" ") if t]
    relaxed = []
    for c in candidates:
        cliente_name_norm = _normalize_text(c.nome_cognome)
        if all(tok in cliente_name_norm for tok in tokens):
            relaxed.append(c)

    if len(relaxed) == 1:
        return int(relaxed[0].cliente_id)
    return None


def run_import(file_path: Path, dry_run: bool, batch_label: str | None) -> None:
    if not file_path.exists():
        raise FileNotFoundError(f"File non trovato: {file_path}")

    parsed_rows = parse_csv_sections(file_path)
    file_hash = _sha256_text(file_path.read_text(encoding="utf-8"))

    stats = {
        "total_rows": len(parsed_rows),
        "inserted": 0,
        "skipped_existing": 0,
        "matched_cliente": 0,
        "unmatched_cliente": 0,
        "sections": {},
    }

    batch = None
    if not dry_run:
        batch = ExampleCheckImportBatch(
            source_file=str(file_path),
            batch_label=batch_label,
            file_hash=file_hash,
            status="started",
            started_at=datetime.now(timezone.utc),
            stats_json={},
        )
        db.session.add(batch)
        db.session.flush()

    for row in parsed_rows:
        stats["sections"].setdefault(row.section_name, 0)
        stats["sections"][row.section_name] += 1

        existing = (
            ExampleCheckEntry.query.filter_by(
                section_name=row.section_name,
                external_response_id=row.external_response_id,
            ).first()
        )
        if existing:
            stats["skipped_existing"] += 1
            continue

        matched_cliente_id = match_cliente_id(row.first_name, row.last_name, row.birth_date_raw)
        if matched_cliente_id:
            stats["matched_cliente"] += 1
        else:
            stats["unmatched_cliente"] += 1

        if dry_run:
            stats["inserted"] += 1
            continue

        entry = ExampleCheckEntry(
            batch_id=batch.id,
            section_name=row.section_name,
            external_response_id=row.external_response_id,
            first_name=row.first_name,
            last_name=row.last_name,
            birth_date_raw=row.birth_date_raw,
            matched_cliente_id=matched_cliente_id,
            response_payload=row.payload,
            submitted_at=row.submitted_at,
            network_id=row.network_id,
            response_type=row.response_type,
            raw_row_hash=row.raw_row_hash,
        )
        db.session.add(entry)
        stats["inserted"] += 1

    if not dry_run:
        batch.status = "completed"
        batch.completed_at = datetime.now(timezone.utc)
        batch.stats_json = stats
        db.session.commit()

    print("=== Import Example Checks ===")
    print(f"File: {file_path}")
    print(f"Dry run: {dry_run}")
    print(f"Righe totali: {stats['total_rows']}")
    print(f"Inserite: {stats['inserted']}")
    print(f"Skippate (gia presenti): {stats['skipped_existing']}")
    print(f"Match cliente: {stats['matched_cliente']}")
    print(f"No match cliente: {stats['unmatched_cliente']}")
    print("Righe per sezione:")
    for sec, count in sorted(stats["sections"].items()):
        print(f"  - {sec}: {count}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import archivio check di esempio da CSV multi-sezione")
    parser.add_argument("--file", required=True, help="Percorso file CSV da importare")
    parser.add_argument("--dry-run", action="store_true", help="Analizza senza scrivere sul DB")
    parser.add_argument("--batch-label", default=None, help="Etichetta opzionale per tracciare il batch")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        run_import(Path(args.file).resolve(), args.dry_run, args.batch_label)


if __name__ == "__main__":
    main()
