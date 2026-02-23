#!/usr/bin/env python3
"""
Script per popolare dati di test per la dashboard admin.
Aggiorna stati clienti e crea check responses con ratings.

Uso:
    cd /Users/matteovolpara/Desktop/suite_clinica/suite-clinica-app
    python scripts/populate_dashboard_data.py
"""

import sys
import os
import random
from datetime import datetime, timedelta
from uuid import uuid4

# Aggiungi il path del progetto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import (
    Cliente,
    User,
    WeeklyCheck,
    WeeklyCheckResponse,
)

# Stati possibili
STATI = ['attivo', 'ghost', 'pausa', 'stop']
STATI_WEIGHTS = [0.6, 0.15, 0.15, 0.1]  # 60% attivo, etc.

# Feedback di esempio
FEEDBACKS_POSITIVI = [
    "Ottimo supporto, molto disponibile!",
    "Mi ha aiutato tantissimo questa settimana",
    "Sempre presente e motivante",
    "Consigli utilissimi e pratici",
    "Professionale e competente",
]

FEEDBACKS_NEGATIVI = [
    "Questa settimana ho avuto meno supporto del solito",
    "Avrei preferito più interazione",
    "Tempi di risposta un po' lunghi",
]

WHAT_WORKED = [
    "Ho seguito il piano alimentare al 90%",
    "Sono riuscito ad allenarmi 4 volte",
    "Ho bevuto più acqua del solito",
    "Mi sono sentito più energico",
    "Ho dormito meglio questa settimana",
]

WHAT_DIDNT_WORK = [
    "Ho saltato un allenamento per impegni di lavoro",
    "Ho avuto qualche sgarro nel weekend",
    "Non ho fatto abbastanza passi",
    "Ho dormito poco giovedì e venerdì",
]


def get_random_rating(min_val=5, max_val=10, bias_positive=True):
    """Genera un rating casuale con bias verso valori positivi."""
    if bias_positive:
        # 70% chance di rating >= 7
        if random.random() < 0.7:
            return random.randint(7, max_val)
        else:
            return random.randint(min_val, 6)
    return random.randint(min_val, max_val)


def assign_professionals(clienti, professionisti):
    """Assegna nutrizionista, coach e psicologo ai clienti che non li hanno."""
    # Raggruppa professionisti per specialità
    nutrizionisti = [u for u in professionisti if u.specialty and 'nutri' in u.specialty.lower()]
    coaches = [u for u in professionisti if u.specialty and 'coach' in u.specialty.lower()]
    psicologi = [u for u in professionisti if u.specialty and 'psico' in u.specialty.lower()]

    print(f"\n  Disponibili: {len(nutrizionisti)} nutrizionisti, {len(coaches)} coach, {len(psicologi)} psicologi")

    assigned = 0
    for cliente in clienti:
        changed = False

        # Assegna nutrizionista se mancante
        if not cliente.nutrizionista_id and nutrizionisti:
            cliente.nutrizionista_id = random.choice(nutrizionisti).id
            changed = True

        # Assegna coach se mancante
        if not cliente.coach_id and coaches:
            cliente.coach_id = random.choice(coaches).id
            changed = True

        # Assegna psicologo se mancante
        if not cliente.psicologa_id and psicologi:
            cliente.psicologa_id = random.choice(psicologi).id
            changed = True

        if changed:
            assigned += 1
            print(f"  [{assigned}] {cliente.nome_cognome}: N={cliente.nutrizionista_id}, C={cliente.coach_id}, P={cliente.psicologa_id}")

    return assigned


def update_client_states(clienti):
    """Aggiorna gli stati di nutrizione/coach/psicologia sui clienti."""
    updated = 0
    for cliente in clienti:
        # Assegna stati casuali (con bias verso 'attivo')
        cliente.stato_nutrizione = random.choices(STATI, STATI_WEIGHTS)[0]
        cliente.stato_coach = random.choices(STATI, STATI_WEIGHTS)[0]
        cliente.stato_psicologia = random.choices(STATI, STATI_WEIGHTS)[0]

        # Aggiorna anche stato_cliente principale
        if cliente.stato_nutrizione == 'attivo' or cliente.stato_coach == 'attivo':
            cliente.stato_cliente = 'attivo'
        else:
            cliente.stato_cliente = random.choices(STATI, STATI_WEIGHTS)[0]

        updated += 1
        print(f"  [{updated}] {cliente.nome_cognome}: N={cliente.stato_nutrizione}, C={cliente.stato_coach}, P={cliente.stato_psicologia}")

    return updated


def create_weekly_checks(clienti, professionisti):
    """Crea WeeklyCheck e WeeklyCheckResponse per i clienti."""
    created_checks = 0
    created_responses = 0

    # Raggruppa professionisti per specialità
    nutrizionisti = [u for u in professionisti if u.specialty and 'nutri' in u.specialty.lower()]
    coaches = [u for u in professionisti if u.specialty and 'coach' in u.specialty.lower()]
    psicologi = [u for u in professionisti if u.specialty and 'psico' in u.specialty.lower()]

    print(f"\n  Professionisti trovati: {len(nutrizionisti)} nutrizionisti, {len(coaches)} coach, {len(psicologi)} psicologi")

    for cliente in clienti:
        # Verifica se esiste già un WeeklyCheck per questo cliente
        weekly_check = WeeklyCheck.query.filter_by(cliente_id=cliente.cliente_id).first()

        if not weekly_check:
            # Crea nuovo WeeklyCheck
            weekly_check = WeeklyCheck(
                cliente_id=cliente.cliente_id,
                token=str(uuid4()),
                is_active=True,
                assigned_at=datetime.utcnow()
            )
            db.session.add(weekly_check)
            db.session.flush()  # Per ottenere l'ID
            created_checks += 1

        # Crea 1-4 risposte per ogni cliente (ultime settimane)
        num_responses = random.randint(1, 4)

        for i in range(num_responses):
            # Data del check (ultimi 30 giorni)
            days_ago = random.randint(0, 30)
            submit_date = datetime.utcnow() - timedelta(days=days_ago)

            # Genera ratings
            nutr_rating = get_random_rating(4, 10)
            coach_rating = get_random_rating(4, 10)
            psico_rating = get_random_rating(4, 10)
            progress_rating = get_random_rating(5, 10)

            # Feedback basato sul rating
            nutr_feedback = random.choice(FEEDBACKS_POSITIVI if nutr_rating >= 7 else FEEDBACKS_NEGATIVI)
            coach_feedback = random.choice(FEEDBACKS_POSITIVI if coach_rating >= 7 else FEEDBACKS_NEGATIVI)
            psico_feedback = random.choice(FEEDBACKS_POSITIVI if psico_rating >= 7 else FEEDBACKS_NEGATIVI)

            response = WeeklyCheckResponse(
                weekly_check_id=weekly_check.id,
                submit_date=submit_date,

                # Valutazioni fisiche
                digestion_rating=random.randint(5, 10),
                energy_rating=random.randint(5, 10),
                strength_rating=random.randint(5, 10),
                hunger_rating=random.randint(4, 9),
                sleep_rating=random.randint(5, 10),
                mood_rating=random.randint(5, 10),
                motivation_rating=random.randint(5, 10),

                # Peso
                weight=round(random.uniform(55.0, 95.0), 1),

                # Valutazioni professionisti
                nutritionist_rating=nutr_rating,
                nutritionist_feedback=nutr_feedback,
                coach_rating=coach_rating,
                coach_feedback=coach_feedback,
                psychologist_rating=psico_rating,
                psychologist_feedback=psico_feedback,

                # Valutazione generale
                progress_rating=progress_rating,

                # Domande aperte
                what_worked=random.choice(WHAT_WORKED),
                what_didnt_work=random.choice(WHAT_DIDNT_WORK),
                what_learned="Ho imparato a gestire meglio i pasti fuori casa",
                what_focus_next="Voglio migliorare la costanza negli allenamenti",
                daily_steps=str(random.randint(5000, 12000)),
            )

            db.session.add(response)
            created_responses += 1

    return created_checks, created_responses


def main():
    print("=" * 60)
    print("SCRIPT POPOLAMENTO DATI DASHBOARD")
    print("=" * 60)

    # Crea app Flask
    app = create_app()

    with app.app_context():
        # 1. Recupera totale clienti
        total_clients = Cliente.query.count()
        print(f"\n[1] Trovati {total_clients} clienti nel database (Processing in batches)")

        if total_clients == 0:
            print("ERRORE: Nessun cliente trovato nel database!")
            return

        # 2. Recupera professionisti
        professionisti = User.query.filter(
            User.is_active == True,
            User.specialty.isnot(None)
        ).all()
        print(f"[2] Trovati {len(professionisti)} professionisti attivi")

        # Process in batches
        BATCH_SIZE = 100
        processed = 0
        
        assigned_total = 0
        updated_total = 0
        checks_total = 0
        responses_total = 0

        while processed < total_clients:
            print(f"\n--- Processing batch {processed} to {processed + BATCH_SIZE} ---")
            # Clear session to avoid memory buildup and continuum issues
            # db.session.expunge_all() # Risk of detaching needed objects? Better just query in batch
            
            clienti = Cliente.query.offset(processed).limit(BATCH_SIZE).all()
            if not clienti:
                break
            
            # 3. Assegna professionisti
            assigned = assign_professionals(clienti, professionisti)
            assigned_total += assigned
            
            # 4. Aggiorna stati
            updated = update_client_states(clienti)
            updated_total += updated
            
            # 5. Crea check responses
            checks, responses = create_weekly_checks(clienti, professionisti)
            checks_total += checks
            responses_total += responses
            
            # 6. Commit per batch
            print(f"   Committing batch...")
            db.session.commit()
            
            processed += len(clienti)
            print(f"   Progress: {processed}/{total_clients}")

        print("\nCOMPLETATO!")
        print(f"    Assegnati professionisti a {assigned_total} clienti")
        print(f"    Aggiornati {updated_total} clienti")
        print(f"    Creati {checks_total} WeeklyCheck")
        print(f"    Create {responses_total} WeeklyCheckResponse")

        # 7. Riepilogo
        print("\n" + "=" * 60)
        print("RIEPILOGO")
        print("=" * 60)

        # Conta stati
        attivi_n = Cliente.query.filter_by(stato_nutrizione='attivo').count()
        attivi_c = Cliente.query.filter_by(stato_coach='attivo').count()
        attivi_p = Cliente.query.filter_by(stato_psicologia='attivo').count()

        print(f"Nutrizione attivi: {attivi_n}")
        print(f"Coach attivi: {attivi_c}")
        print(f"Psicologia attivi: {attivi_p}")

        # Conta check
        total_checks = WeeklyCheckResponse.query.count()
        print(f"Totale check responses: {total_checks}")

        print("\n✅ Script completato con successo!")
        print("   Ricarica la dashboard per vedere i dati.")


if __name__ == "__main__":
    main()
