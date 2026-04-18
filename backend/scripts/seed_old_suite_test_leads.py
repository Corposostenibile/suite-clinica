#!/usr/bin/env python3
"""
Seed lead di test per il pannello Assegnazioni Old Suite.

Crea 4 SalesLead con source_system='old_suite' per testare la nuova
funzionalità di inserimento manuale storia + assegnazione professionisti:

  1. Lead senza storia - pacchetto N/C/P (tutti e 3 i ruoli)
  2. Lead senza storia - pacchetto N/C (solo nutrizione + coach)
  3. Lead con storia già presente - pacchetto N/C/P (per testare "Modifica Storia")
  4. Lead parzialmente assegnato (nutrizione già assegnata) - pacchetto N/C

Usage:
    cd backend
    poetry run python scripts/seed_old_suite_test_leads.py

Per rimuovere i lead di test:
    poetry run python scripts/seed_old_suite_test_leads.py --clean
"""

import os
import sys
from datetime import date, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import SalesLead, User, LeadStatusEnum

app = create_app()

TEST_UNIQUE_CODES = [
    'TEST-OLD-001',
    'TEST-OLD-002',
    'TEST-OLD-003',
    'TEST-OLD-004',
]

LEADS = [
    {
        'unique_code': 'TEST-OLD-001',
        'old_suite_id': 99001,
        'first_name': 'Mario',
        'last_name': 'Rossi',
        'email': 'mario.rossi.test@esempio.it',
        'phone': '333 1234567',
        'custom_package_name': 'N/C/P-90gg-C',
        'client_story': None,
        'onboarding_date': date(2026, 4, 20),
        'onboarding_time': time(10, 30),
        '_desc': 'Senza storia - N/C/P (tutti i ruoli)',
    },
    {
        'unique_code': 'TEST-OLD-002',
        'old_suite_id': 99002,
        'first_name': 'Giulia',
        'last_name': 'Bianchi',
        'email': 'giulia.bianchi.test@esempio.it',
        'phone': '348 9876543',
        'custom_package_name': 'N/C-90gg-C',
        'client_story': None,
        'onboarding_date': date(2026, 4, 21),
        'onboarding_time': time(14, 0),
        '_desc': 'Senza storia - N/C (nutrizione + coach)',
    },
    {
        'unique_code': 'TEST-OLD-003',
        'old_suite_id': 99003,
        'first_name': 'Luca',
        'last_name': 'Verdi',
        'email': 'luca.verdi.test@esempio.it',
        'phone': '339 5551234',
        'custom_package_name': 'N/C/P-90gg-C',
        'client_story': (
            'Luca, 34 anni, imprenditore. Sovrappeso da circa 5 anni, ha provato varie diete '
            'senza risultati stabili. Soffre di stress cronico e ha difficoltà con il sonno. '
            'Obiettivo principale: perdita di peso (15 kg) e miglioramento dell\'energia. '
            'Attività fisica: camminate, nessuna palestra. Motivazione alta.'
        ),
        'onboarding_date': date(2026, 4, 22),
        'onboarding_time': time(11, 0),
        '_desc': 'Con storia già presente - N/C/P (per testare "Modifica Storia")',
    },
    {
        'unique_code': 'TEST-OLD-004',
        'old_suite_id': 99004,
        'first_name': 'Anna',
        'last_name': 'Neri',
        'email': 'anna.neri.test@esempio.it',
        'phone': '340 7778899',
        'custom_package_name': 'N/C-90gg-C',
        'client_story': None,
        '_assigned_nutrition': True,
        'onboarding_date': date(2026, 4, 19),
        'onboarding_time': time(9, 0),
        '_desc': 'Parzialmente assegnata (nutrizione già assegnata) - N/C',
    },
]


def seed(clean=False):
    with app.app_context():
        if clean:
            deleted = SalesLead.query.filter(
                SalesLead.unique_code.in_(TEST_UNIQUE_CODES)
            ).delete(synchronize_session=False)
            db.session.commit()
            print(f"Rimossi {deleted} lead di test.")
            return

        # Trova un nutrizionista attivo per il lead parzialmente assegnato
        nutritionist = User.query.filter(
            User.is_active == True,
            User.specialty.cast(db.String).in_(['nutrizione', 'nutrizionista']),
        ).first()

        created = 0
        updated = 0
        for lead_data in LEADS:
            desc = lead_data.pop('_desc')
            assign_nutrition = lead_data.pop('_assigned_nutrition', False)

            existing = SalesLead.query.filter_by(
                unique_code=lead_data['unique_code']
            ).first()

            if existing:
                print(f"  [SKIP] {lead_data['first_name']} {lead_data['last_name']} già presente (id={existing.id})")
                updated += 1
                continue

            lead = SalesLead(
                source_system='old_suite',
                status=LeadStatusEnum.NEW,
                form_responses={},
                **{k: v for k, v in lead_data.items() if not k.startswith('_')},
            )

            if assign_nutrition and nutritionist:
                lead.assigned_nutritionist_id = nutritionist.id
                print(f"  [INFO] Nutrizionista assegnata a Anna Neri: {nutritionist.first_name} {nutritionist.last_name}")

            db.session.add(lead)
            created += 1
            print(f"  [OK] {lead_data['first_name']} {lead_data['last_name']} — {desc}")

        db.session.commit()
        print(f"\nDone: {created} lead creati, {updated} già esistenti.")
        print("\nAprire /assegnazioni-old-suite per verificare i lead di test.")
        print("Consiglio: disattivare il filtro 'Da assegnare' per vedere anche Anna Neri (parziale).")


if __name__ == '__main__':
    clean = '--clean' in sys.argv
    seed(clean=clean)
