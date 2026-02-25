#!/usr/bin/env python3
"""
Seed dati di test per la tab "Check Associati" in team-dettaglio/:id.

Garantisce:
- Un professionista (es. user_id=4) con specialty definita (nutrizionista/coach/psicologo)
- Almeno un cliente assegnato a quel professionista
- Almeno un check settimanale (WeeklyCheckResponse) con valutazioni, negli ultimi 30 giorni,
  così che GET /team/members/:id/checks restituisca dati e la UI mostri solo la valutazione
  del professionista e il clic apra il modal.

Uso (da backend/):
  python scripts/dev_data_scripts/seed_team_check_associati_test.py

Verifica manuale:
  - Apri http://<host>/team-dettaglio/4
  - Tab "Check Associati"
  - Controlla: un solo badge media (es. Nutri: X), colonna Valutazioni con solo quel ruolo, clic riga apre modal con sola quella valutazione
"""

import sys
import os
import secrets
from datetime import datetime, timedelta, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Professionista da usare per il test (team-dettaglio/4)
TARGET_USER_ID = 4
# Specialty da assegnare se manca (deve essere nutrizionista, coach o psicologo per mapping rating)
DEFAULT_SPECIALTY = 'nutrizionista'


def main():
    from corposostenibile import create_app
    from corposostenibile.extensions import db
    from corposostenibile.models import (
        Cliente,
        User,
        WeeklyCheck,
        WeeklyCheckResponse,
    )

    app = create_app()

    with app.app_context():
        print('=' * 60)
        print('SEED: Team Check Associati (dati di test)')
        print('=' * 60)

        user = User.query.get(TARGET_USER_ID)
        if not user:
            print(f'\n⚠️  User id={TARGET_USER_ID} non trovato. Crea prima un utente con quel id.')
            return

        # Assicura specialty per mapping rating in UI
        from corposostenibile.models import UserSpecialtyEnum
        spec_val = user.specialty.value if hasattr(user.specialty, 'value') else str(user.specialty or '')
        if spec_val not in ('nutrizione', 'nutrizionista', 'coach', 'psicologia', 'psicologo'):
            try:
                user.specialty = getattr(UserSpecialtyEnum, DEFAULT_SPECIALTY, UserSpecialtyEnum.nutrizionista)
                db.session.commit()
                print(f'\n✅ User {TARGET_USER_ID} ({user.email}) impostato specialty={user.specialty}')
            except Exception as e:
                print(f'\n⚠️  Impossibile impostare specialty: {e}')

        # Cliente assegnato a questo professionista (nutrizionista_id, coach_id o psicologa_id)
        cliente = (
            Cliente.query.filter(Cliente.nutrizionista_id == TARGET_USER_ID).first()
            or Cliente.query.filter(Cliente.coach_id == TARGET_USER_ID).first()
            or Cliente.query.filter(Cliente.psicologa_id == TARGET_USER_ID).first()
        )

        if not cliente:
            # Assegna il primo cliente disponibile a questo utente come nutrizionista
            cliente = Cliente.query.filter(Cliente.show_in_clienti_lista.is_(True)).first()
            if not cliente:
                print('\n⚠️  Nessun cliente in lista. Crea prima dei clienti.')
                return
            cliente.nutrizionista_id = TARGET_USER_ID
            db.session.commit()
            print(f'\n✅ Cliente {cliente.cliente_id} ({cliente.nome_cognome}) assegnato a user_id={TARGET_USER_ID} (nutrizionista_id)')
        else:
            print(f'\n✅ Cliente esistente assegnato: {cliente.cliente_id} ({cliente.nome_cognome})')

        # WeeklyCheck per questo cliente
        weekly_check = WeeklyCheck.query.filter_by(cliente_id=cliente.cliente_id).first()
        if not weekly_check:
            admin = User.query.filter_by(is_admin=True).first() or User.query.first()
            weekly_check = WeeklyCheck(
                cliente_id=cliente.cliente_id,
                token=secrets.token_urlsafe(32),
                is_active=True,
                assigned_by_id=admin.id if admin else None,
                assigned_at=datetime.utcnow() - timedelta(days=60),
            )
            db.session.add(weekly_check)
            db.session.flush()
            print(f'\n✅ Creato WeeklyCheck id={weekly_check.id} per cliente {cliente.cliente_id}')
        else:
            print(f'\n✅ WeeklyCheck esistente id={weekly_check.id}')

        # Almeno una risposta negli ultimi 30 giorni con rating
        today = date.today()
        start_date = today - timedelta(days=30)
        existing = (
            WeeklyCheckResponse.query.filter(
                WeeklyCheckResponse.weekly_check_id == weekly_check.id,
                WeeklyCheckResponse.submit_date >= datetime.combine(start_date, datetime.min.time()),
            ).first()
        )
        if not existing:
            base = 7
            resp = WeeklyCheckResponse(
                weekly_check_id=weekly_check.id,
                submit_date=datetime.combine(today - timedelta(days=5), datetime.min.time()),
                what_worked='Test: cosa ha funzionato.',
                what_didnt_work='Test: cosa non ha funzionato.',
                what_learned='Test: cosa ho imparato.',
                what_focus_next='Test: focus prossima settimana.',
                progress_rating=base,
                nutritionist_rating=base + 1 if cliente.nutrizionista_id else None,
                psychologist_rating=base if cliente.psicologa_id else None,
                coach_rating=base - 1 if cliente.coach_id else None,
                nutritionist_feedback='Feedback nutrizionista test.',
                psychologist_feedback='Feedback psicologo test.',
                coach_feedback='Feedback coach test.',
                weight=72.5,
                digestion_rating=7,
                energy_rating=8,
                strength_rating=7,
                hunger_rating=6,
                sleep_rating=7,
                mood_rating=8,
                motivation_rating=7,
            )
            db.session.add(resp)
            db.session.commit()
            print(f'\n✅ Creata WeeklyCheckResponse id={resp.id} (ultimi 30 gg) con valutazioni')
        else:
            print(f'\n✅ Esiste già una risposta recente (id={existing.id})')

        print('\n' + '=' * 60)
        print('Verifica: apri /team-dettaglio/4 → tab "Check Associati"')
        print('=' * 60)


if __name__ == '__main__':
    main()
