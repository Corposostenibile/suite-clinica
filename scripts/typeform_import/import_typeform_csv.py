#!/usr/bin/env python3
"""
Script per importare risposte Typeform da CSV nel sistema.
Versione ottimizzata con bulk insert.
"""

import sys
import csv
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher

# Add backend to path
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Import directly without full Flask app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

# Database connection - legge da environment o usa default dev
import os
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://suite_clinica:password@localhost:5432/suite_clinica_dev_manu')

engine = create_engine(DATABASE_URL, poolclass=NullPool)
Session = sessionmaker(bind=engine)


def normalize_name(name: str) -> str:
    """Normalizza un nome per il matching."""
    if not name:
        return ""
    name = name.lower().strip()
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    name = re.sub(r'[^a-z0-9\s]', '', name)
    name = ' '.join(name.split())
    return name


def build_name_cache():
    """Costruisce una cache dei nomi normalizzati per matching veloce."""
    from corposostenibile.models import Cliente
    
    session = Session()
    try:
        cache = {}
        clienti = session.query(Cliente).all()
        for c in clienti:
            norm = normalize_name(c.nome_cognome or "")
            if norm:
                if norm not in cache:
                    cache[norm] = []
                cache[norm].append(c)
        return cache
    finally:
        session.close()


def fuzzy_match(name: str, cache: dict) -> tuple:
    """Trova match fuzzy usando la cache pre-costruita."""
    norm_name = normalize_name(name)
    if not norm_name:
        return None, None
    
    # Exact match nella cache
    if norm_name in cache:
        return cache[norm_name][0], "exact"
    
    # Fuzzy match
    best_match = None
    best_ratio = 0
    
    for cached_name, clienti_list in cache.items():
        ratio = SequenceMatcher(None, norm_name, cached_name).ratio()
        if ratio > best_ratio and ratio >= 0.85:
            best_ratio = ratio
            best_match = clienti_list[0]
    
    return best_match, "fuzzy" if best_match else None


def parse_date(date_str: str) -> datetime | None:
    """Parse various date formats from Typeform."""
    if not date_str:
        return None
    date_str = date_str.strip()
    formats = [
        '%Y-%m-%dT%H:%M:%S.%fZ',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def import_csv_file(csv_path: Path, name_cache: dict, dry_run: bool = True) -> dict:
    """Importa un singolo file CSV Typeform."""
    from corposostenibile.models import TypeFormResponse
    
    stats = {'total': 0, 'imported': 0, 'skipped': 0, 'matched': 0, 'unmatched': 0, 'errors': 0}
    
    session = Session()
    try:
        # Get existing typeform_ids per evitare duplicati
        existing_ids = set(
            r[0] for r in session.query(TypeFormResponse.typeform_id).all()
        )
        
        responses_to_add = []
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row_num, row in enumerate(reader, start=2):
                stats['total'] += 1
                try:
                    tf_id = row.get('#', '').strip()
                    first_name = row.get('First name', '').strip()
                    last_name = row.get('Last name', '').strip()
                    
                    if not tf_id:
                        stats['skipped'] += 1
                        continue
                    
                    # Check if already exists
                    if tf_id in existing_ids:
                        stats['skipped'] += 1
                        continue
                    
                    # Parse submit date
                    submit_date = None
                    for date_field in ['Submit Date (UTC)', 'Stage Date (UTC)', 'Start Date (UTC)']:
                        if row.get(date_field):
                            submit_date = parse_date(row.get(date_field, ''))
                            if submit_date:
                                break
                    
                    # Match cliente
                    cliente = None
                    if first_name and last_name:
                        full_name = f"{first_name} {last_name}"
                        cliente, _ = fuzzy_match(full_name, name_cache)
                    
                    # Build raw response data
                    metadata_cols = {
                        '#', 'First name', 'Last name', 'Phone number', 'Email', 'Company',
                        'Start Date (UTC)', 'Stage Date (UTC)', 'Submit Date (UTC)', 
                        'Network ID', 'Response Type', 'Tags', 'Ending',
                        'counter_65419427_41c3_40d9_b477_b934dc4b9911',
                        'counter_eaeafa90_309a_410a_9d95_b3003152470b',
                        'counter_f119cde9_f35f_4c77_94fc_bc6baae99905',
                        'Score', 'variable_0'
                    }
                    raw_data = {k: v for k, v in row.items() if k not in metadata_cols and v.strip()}
                    
                    # Extract weight
                    peso = None
                    for key in row:
                        if 'peso' in key.lower() and row[key].strip():
                            try:
                                peso = float(row[key].replace(',', '.').replace(' kg', '').strip())
                            except ValueError:
                                pass
                    
                    response = TypeFormResponse(
                        typeform_id=tf_id,
                        first_name=first_name,
                        last_name=last_name,
                        submit_date=submit_date,
                        raw_response_data=raw_data,
                        cliente_id=cliente.cliente_id if cliente else None,
                        is_matched=cliente is not None,
                        weight=peso,
                    )
                    responses_to_add.append(response)
                    existing_ids.add(tf_id)  # Evita duplicati nello stesso file
                    
                    if cliente:
                        stats['matched'] += 1
                    else:
                        stats['unmatched'] += 1
                        if stats['unmatched'] <= 5:
                            print(f"  Row {row_num}: No match for '{first_name} {last_name}'")
                    
                    stats['imported'] += 1
                    
                except Exception as e:
                    stats['errors'] += 1
                    print(f"  ERROR Row {row_num}: {e}")
        
        # Bulk insert
        if responses_to_add and not dry_run:
            session.bulk_save_objects(responses_to_add)
            session.commit()
            print(f"  Bulk inserted {len(responses_to_add)} responses")
        
        return stats
    finally:
        session.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Import Typeform CSV responses')
    parser.add_argument('--dry-run', action='store_true', default=True, help='Dry run mode (default)')
    parser.add_argument('--no-dry-run', action='store_false', dest='dry_run', help='Actually import data')
    parser.add_argument('--folder', type=str, default='../typeforms_checks', help='Folder with CSV files')
    args = parser.parse_args()
    
    # Build name cache once
    print("Building client name cache...")
    name_cache = build_name_cache()
    print(f"Cache built with {len(name_cache)} unique names")
    
    folder = Path(args.folder)
    if not folder.exists():
        print(f"Folder not found: {folder}")
        sys.exit(1)
    
    csv_files = sorted(folder.glob("*.csv"))
    if not csv_files:
        print(f"No CSV files found in: {folder}")
        sys.exit(1)
    
    print(f"\nFound {len(csv_files)} CSV files:")
    for f in csv_files:
        print(f"  - {f.name}")
    print(f"\nMode: {'DRY RUN' if args.dry_run else 'LIVE IMPORT'}")
    print("-" * 50)
    
    total_stats = {'total': 0, 'imported': 0, 'skipped': 0, 'matched': 0, 'unmatched': 0, 'errors': 0}
    
    for csv_path in csv_files:
        print(f"\nProcessing: {csv_path.name}")
        stats = import_csv_file(csv_path, name_cache, dry_run=args.dry_run)
        for k in ['total', 'imported', 'skipped', 'matched', 'unmatched', 'errors']:
            total_stats[k] += stats[k]
        print(f"  Total: {stats['total']}, Imported: {stats['imported']}, Skipped: {stats['skipped']}")
        print(f"  Matched: {stats['matched']}, Unmatched: {stats['unmatched']}, Errors: {stats['errors']}")
    
    print("\n" + "=" * 50)
    print("OVERALL STATISTICS:")
    print(f"  Total rows: {total_stats['total']}")
    print(f"  Imported: {total_stats['imported']}")
    print(f"  Skipped (existing): {total_stats['skipped']}")
    print(f"  Matched to cliente: {total_stats['matched']}")
    print(f"  Unmatched: {total_stats['unmatched']}")
    print(f"  Errors: {total_stats['errors']}")
    
    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No changes were saved.")
        print("   Run with --no-dry-run to actually import data.")


if __name__ == '__main__':
    main()
