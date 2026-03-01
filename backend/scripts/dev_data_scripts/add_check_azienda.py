
"""
Script per popolare la pagina /check-azienda con dati dummy.
Crea WeeklyCheckResponse per i clienti attivi negli ultimi 30 giorni.

Usage:
    python corposostenibile/scripts/add_check_azienda.py
"""
import sys
import os
import random
from datetime import datetime, timedelta

# Aggiungi la root del progetto al path per importare i moduli app
sys.path.append(os.getcwd())

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import (
    User, Cliente, WeeklyCheck, WeeklyCheckResponse, 
    StatoClienteEnum, ClientCheckReadConfirmation
)

def create_dummy_data():
    app = create_app()
    with app.app_context():
        print("Inizio popolamento dati per Check Azienda...")
        
        # 1. Recupera clienti attivi
        # Includiamo anche quelli in pausa per avere più dati
        clienti = Cliente.query.filter(
            Cliente.stato_cliente.in_([StatoClienteEnum.attivo, StatoClienteEnum.pausa])
        ).all()
        
        print(f"Trovati {len(clienti)} clienti attivi/pausa.")
        
        count_responses = 0
        
        # Recupera alcuni professionisti per simulare le conferme di lettura
        professionisti = User.query.limit(5).all()
        prof_ids = [p.id for p in professionisti]
        
        for cliente in clienti:
            # 2. Assicurati che abbia un WeeklyCheck assignment
            assignment = WeeklyCheck.query.filter_by(cliente_id=cliente.cliente_id).first()
            if not assignment:
                # Crea assignment se manca
                import secrets
                token = secrets.token_urlsafe(32)
                assignment = WeeklyCheck(
                    cliente_id=cliente.cliente_id,
                    token=token,
                    is_active=True,
                    assigned_by_id=1,  # Admin ID (assumiamo esista)
                    assigned_at=datetime.utcnow() - timedelta(days=60)
                )
                db.session.add(assignment)
                db.session.flush() # Per avere l'ID
                print(f"  Creato assignment WeeklyCheck per {cliente.nome_cognome}")
            
            # 3. Genera 0-3 risposte random negli ultimi 30 giorni
            num_responses = random.randint(0, 3)
            
            # Date base: oggi, 7 giorni fa, 14 giorni fa, 21 giorni fa
            base_dates = [
                datetime.utcnow(),
                datetime.utcnow() - timedelta(days=7),
                datetime.utcnow() - timedelta(days=14),
                datetime.utcnow() - timedelta(days=21)
            ]
            
            for i in range(num_responses):
                # Data con leggera variazione casuale di orario
                submit_date = base_dates[i] - timedelta(hours=random.randint(0, 12), minutes=random.randint(0, 59))
                
                # Genera valutazioni casuali (più alte per simulare clienti felici, ma qualche basso)
                is_happy = random.random() > 0.2 # 80% felici
                base_rating = random.randint(7, 10) if is_happy else random.randint(3, 6)
                
                response = WeeklyCheckResponse(
                    weekly_check_id=assignment.id,
                    submit_date=submit_date,
                    ip_address="127.0.0.1",
                    
                    # Ratings
                    nutritionist_rating=max(1, min(10, base_rating + random.randint(-1, 1))),
                    psychologist_rating=max(1, min(10, base_rating + random.randint(-1, 1))),
                    coach_rating=max(1, min(10, base_rating + random.randint(-1, 1))),
                    progress_rating=max(1, min(10, base_rating + random.randint(-1, 1))),
                    
                    digestion_rating=random.randint(5, 10),
                    energy_rating=random.randint(5, 10),
                    strength_rating=random.randint(5, 10),
                    hunger_rating=random.randint(5, 10),
                    sleep_rating=random.randint(5, 10),
                    mood_rating=random.randint(5, 10),
                    motivation_rating=random.randint(5, 10),
                    
                    # Text fields dummy
                    what_worked="Mi sono allenato con costanza e ho seguito la dieta.",
                    what_didnt_work="Poco sonno nel weekend.",
                    what_learned="L'importanza del riposo.",
                    what_focus_next="Migliorare la qualità del sonno.",
                    
                    weight=70.5 + random.uniform(-2.0, 2.0)
                )
                
                db.session.add(response)
                db.session.flush() # Per avere l'ID
                
                # Nota: response_count e last_response_date sono property calcolate su WeeklyCheck,
                # quindi non dobbiamo aggiornarle manualmente.
                
                # 4. Simula Lettura da parte dei professionisti (random)
                # 50% di probabilità che sia stato letto da qualcuno
                if random.random() > 0.5 and prof_ids:
                    # Scegli 1-2 professionisti a caso che hanno letto
                    readers = random.sample(prof_ids, k=random.randint(1, min(2, len(prof_ids))))
                    for reader_id in readers:
                        confirmation = ClientCheckReadConfirmation(
                            response_type='weekly_check',
                            response_id=response.id,
                            user_id=reader_id,
                            read_at=submit_date + timedelta(hours=random.randint(1, 48))
                        )
                        db.session.add(confirmation)
                
                count_responses += 1
        
        db.session.commit()
        print(f"Completato! Generate {count_responses} risposte per {len(clienti)} clienti.")

if __name__ == "__main__":
    create_dummy_data()
