#!/usr/bin/env python3
"""
Import leads from old suite CSV export into production via webhook endpoint.

Usage:
    python scripts/import_old_suite_leads.py /path/to/export.csv [--dry-run] [--base-url URL]

The CSV must have columns matching the old suite export format.
Each row is transformed into a lead.pending_assignment webhook payload
and POSTed to the /old-suite/webhook endpoint.
"""

import csv
import json
import sys
import time
import argparse
import requests
from datetime import datetime


def parse_json_field(value):
    """Parse a JSON string field from CSV, return {} if empty/invalid."""
    if not value or not value.strip():
        return {}
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}


def build_webhook_payload(row):
    """Transform a CSV row dict into a lead.pending_assignment webhook payload."""
    # Parse check responses
    check1_responses = parse_json_field(row.get('check1_responses', ''))
    check2_responses = parse_json_field(row.get('check2_responses', ''))
    check3_responses = parse_json_field(row.get('check3_responses', ''))

    check1_completed = row.get('check1_completato', '').strip().lower() == 'true'
    check2_completed = row.get('check2_completato', '').strip().lower() == 'true'
    check3_completed = row.get('check3_completato', '').strip().lower() == 'true'

    now_iso = datetime.utcnow().isoformat()

    checks = {}
    if check1_completed or check1_responses:
        checks['check1'] = {
            'completed': check1_completed,
            'responses': check1_responses if check1_responses else None,
            'completed_at': now_iso if check1_completed else None,
        }
    if check2_completed or check2_responses:
        checks['check2'] = {
            'completed': check2_completed,
            'responses': check2_responses if check2_responses else None,
            'completed_at': now_iso if check2_completed else None,
        }
    if check3_completed or check3_responses:
        check3_data = {
            'completed': check3_completed,
            'responses': check3_responses if check3_responses else None,
            'completed_at': now_iso if check3_completed else None,
        }
        score = row.get('check3_score', '').strip()
        if score:
            try:
                check3_data['score'] = int(score)
            except ValueError:
                try:
                    check3_data['score'] = float(score)
                except ValueError:
                    pass
        check3_type = row.get('check3_type', '').strip()
        if check3_type:
            check3_data['type'] = check3_type
        checks['check3'] = check3_data

    # Health manager
    hm_name = row.get('health_manager_name', '').strip()
    hm_email = row.get('health_manager_email', '').strip()
    health_manager = None
    if hm_name:
        health_manager = {'name': hm_name}
        if hm_email:
            health_manager['email'] = hm_email

    # Build lead payload
    lead = {
        'id': row.get('id', '').strip(),
        'unique_code': row.get('unique_code', '').strip(),
        'first_name': row.get('first_name', '').strip(),
        'last_name': row.get('last_name', '').strip(),
        'email': row.get('email', '').strip(),
        'phone': row.get('phone', '').strip(),
        'gender': row.get('gender', '').strip(),
        'birth_date': row.get('birth_date', '').strip() or None,
        'professione': row.get('professione', '').strip(),
        'fiscal_code': row.get('fiscal_code', '').strip(),
        'indirizzo': row.get('indirizzo', '').strip(),
        'paese': row.get('paese', '').strip(),
        'origin': row.get('origin', '').strip(),
        'client_story': row.get('client_story', '').strip(),
        'custom_package_name': row.get('package_name', '').strip(),
        'onboarding_date': row.get('onboarding_date', '').strip() or None,
        'onboarding_time': row.get('onboarding_time', '').strip() or None,
        'checks': checks,
    }

    if health_manager:
        lead['health_manager'] = health_manager

    return {
        'event': 'lead.pending_assignment',
        'lead': lead,
    }


def main():
    parser = argparse.ArgumentParser(description='Import old suite leads via webhook')
    parser.add_argument('csv_file', help='Path to the CSV export file')
    parser.add_argument('--dry-run', action='store_true', help='Print payloads without sending')
    parser.add_argument('--base-url', default='https://clinica.corposostenibile.com',
                        help='Base URL of the target instance')
    parser.add_argument('--delay', type=float, default=0.3,
                        help='Delay between requests in seconds (default: 0.3)')
    args = parser.parse_args()

    webhook_url = f"{args.base_url}/old-suite/webhook"
    headers = {
        'Content-Type': 'application/json',
        'X-Webhook-Source': 'corposostenibile-suite',
    }

    # Read CSV
    with open(args.csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Loaded {len(rows)} leads from {args.csv_file}")
    print(f"Target: {webhook_url}")
    print()

    if args.dry_run:
        print("=== DRY RUN MODE ===\n")

    success = 0
    failed = 0
    skipped = 0

    for i, row in enumerate(rows, 1):
        old_id = row.get('id', '?')
        name = f"{row.get('first_name', '')} {row.get('last_name', '')}".strip()
        pkg = row.get('package_name', '')

        payload = build_webhook_payload(row)

        if args.dry_run:
            print(f"[{i}/{len(rows)}] #{old_id} {name} ({pkg})")
            if i <= 2:
                print(f"  Payload keys: {list(payload['lead'].keys())}")
                checks_info = {k: {'completed': v.get('completed'), 'has_responses': bool(v.get('responses'))}
                               for k, v in payload['lead'].get('checks', {}).items()}
                print(f"  Checks: {checks_info}")
                if payload['lead'].get('health_manager'):
                    print(f"  HM: {payload['lead']['health_manager']}")
            continue

        try:
            resp = requests.post(webhook_url, json=payload, headers=headers, timeout=30)
            data = resp.json()

            if resp.status_code == 200 and data.get('success'):
                print(f"  [{i}/{len(rows)}] OK  #{old_id} {name} → lead_id={data.get('lead_id')}")
                success += 1
            else:
                print(f"  [{i}/{len(rows)}] FAIL #{old_id} {name} → {resp.status_code}: {data.get('message', resp.text[:200])}")
                failed += 1

        except requests.RequestException as e:
            print(f"  [{i}/{len(rows)}] ERR  #{old_id} {name} → {e}")
            failed += 1

        if args.delay and i < len(rows):
            time.sleep(args.delay)

    print()
    print(f"Done! Success: {success} | Failed: {failed} | Total: {len(rows)}")


if __name__ == '__main__':
    main()
