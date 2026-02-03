#!/usr/bin/env python3
"""
Script di popolamento per la sezione Formazione.
Crea dati realistici e coerenti con il frontend (Formazione.jsx).

Tipi di training (review_type):
- general: Generale
- performance: Performance
- progetto: Progetto
- monthly: Mensile
- annual: Annuale
"""

import sys
import os
import random
from datetime import datetime, timedelta, date

# Aggiungi il path del backend per gli import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================
# CONFIGURAZIONE
# ============================================================

OGGI = datetime.now()
MIN_TRAINING = 2
MAX_TRAINING = 6

# Tipi attesi dal frontend
REVIEW_TYPES = ['general', 'performance', 'progetto', 'monthly', 'annual']
REVIEW_TYPE_WEIGHTS = [30, 25, 20, 15, 10]

# Priorità richieste
PRIORITIES = ['low', 'normal', 'high', 'urgent']
PRIORITY_WEIGHTS = [20, 50, 20, 10]

# ============================================================
# TEMPLATE DATI
# ============================================================

TRAINING_TITLES = {
    'nutrizionista': [
        "Analisi protocolli Nutrizione Avanzata",
        "Gestione pazienti con insulino-resistenza",
        "Comunicazione e persuasione nel counseling",
        "Ottimizzazione piani alimentari sportivi",
        "Revisione mensile obiettivi clinici",
        "Focus Group: DCA e approccio integrato",
        "Update: Nuovi integratori in commercio",
    ],
    'coach': [
        "Metodologie di ipertrofia applicata",
        "Prevenzione infortuni nella pesistica",
        "Coaching motivazionale: strategie di retention",
        "Programmazione annuale atleti elite",
        "Performance review: Q1 2026",
        "Utilizzo avanzato della piattaforma di tracking",
    ],
    'psicologo': [
        "Tecniche di rilassamento progressivo",
        "Gestione dello stress nel paziente obeso",
        "Mindful Eating: protocollo clinico",
        "Supervisione casi clinici complessi",
        "Valutazione psicometrica periodica",
        "Psicologia della motivazione al cambiamento",
    ],
    'default': [
        "Welcome Training: Procedure Aziendali",
        "Corso Privacy e GDPR",
        "Utilizzo strumenti di comunicazione interna",
        "Allineamento Valori Aziendali",
        "Performance Review Annuale",
    ]
}

TRAINING_CONTENTS = {
    'general': [
        "Questo training copre le basi del nostro approccio multidisciplinare. È fondamentale che ogni professionista comprenda come collaborare con gli altri dipartimenti per il benessere del cliente.",
        "Update sulle procedure interne di comunicazione. Abbiamo introdotto nuove linee guida per i messaggi verso i clienti per garantire uno standard qualitativo elevato.",
    ],
    'performance': [
        "Analisi delle tue performance del periodo. Hai dimostrato un'ottima gestione dei casi, ma c'è margine di miglioramento nella puntualità della documentazione.\n\nKPI analizzati:\n- Retention rate\n- Feedback clienti\n- Update settimanali",
        "Sessione di feedback sulle competenze tecniche. Hai padroneggiato i nuovi protocolli con velocità, ottimo lavoro!",
    ],
    'progetto': [
        "Briefing per il nuovo progetto 'Nutrizione 2.0'. Il tuo ruolo sarà quello di validare i nuovi menu per i pazienti sportivi.",
        "Formazione specifica per l'implementazione del modulo 'Check-in Automatico' nella tua area di competenza.",
    ],
    'monthly': [
        "Review mensile standard. Abbiamo analizzato l'andamento del portafoglio clienti e i risultati medi ottenuti. Ottimo il feedback qualitativo ricevuto dai pazienti.",
        "Incontro di allineamento mensile. Focus sulla gestione dei carichi di lavoro e bilanciamento vita-privata.",
    ],
    'annual': [
        "Valutazione annuale 2025. Un anno di grandi traguardi e crescita professionale. Abbiamo definito il tuo percorso di sviluppo per il 2026.",
        "Annual Career Review. Discussione sulle aspirazioni di crescita e piano formativo per il prossimo anno solare.",
    ]
}

STRENGTHS = [
    "Eccellente capacità empatica con i pazienti più difficili.",
    "Precisione tecnica impeccabile nella stesura dei piani.",
    "Grande spirito di squadra e supporto ai colleghi junior.",
    "Proattività nell'identificare soluzioni ai problemi organizzativi.",
    "Ottima padronanza degli strumenti digitali aziendali.",
]

IMPROVEMENTS = [
    "Cercare di essere più concisi nella documentazione dei check-in.",
    "Migliorare la velocità di risposta ai messaggi non urgenti.",
    "Approfondire le conoscenze teoriche su casi di patologie rare.",
    "Organizzare meglio la transizione tra un appuntamento e l'altro.",
    "Partecipare più attivamente ai meeting di dipartimento.",
]

GOALS = [
    "Completare la certificazione avanzata entro marzo.",
    "Mantenere un rating medio clienti sopra il 4.8/5.",
    "Ridurre il churn rate del proprio portafoglio del 5%.",
    "Prendere in carico 2 casi complessi come lead professionista.",
    "Automatizzare la riscossione dei feedback mensili.",
]

CHAT_REVIEWER = [
    "Ottimo inizio su questo punto. Fammi sapere se incontri difficoltà.",
    "Ho caricato il materiale aggiuntivo nella cartella condivisa.",
    "Possiamo vederci 10 minuti domani per approfondire il punto 3?",
    "Grazie per aver completato gli obiettivi prefissati!",
]

CHAT_REVIEWEE = [
    "Ricevuto, approfondirò sicuramente quel manuale.",
    "Ho qualche dubbio sulla procedura X, ne parliamo in supervisione?",
    "Grazie per i consigli, sono stati molto utili con il paziente odierno.",
    "Feedback molto chiaro, mi metto subito al lavoro.",
]

def get_random_date_range():
    start = OGGI - timedelta(days=random.randint(30, 365))
    end = start + timedelta(days=random.randint(7, 30))
    return start.date(), end.date()

def main():
    from corposostenibile import create_app
    from corposostenibile.extensions import db
    from corposostenibile.models import User, Review, ReviewRequest, ReviewAcknowledgment, ReviewMessage

    app = create_app()

    with app.app_context():
        print("🚀 Avvio popolamento dati Formazione...")

        # 1. Carica Professionisti e Trainer
        professionals = User.query.filter(User.is_active == True, User.specialty != None).all()
        admins = User.query.filter(User.is_active == True, (User.is_admin == True) | (User.role == 'team_leader')).all()

        if not professionals or not admins:
            print("❌ Errore: Nessun utente trovato nel database.")
            return

        print(f"📋 Trovati {len(professionals)} professionisti e {len(admins)} potenziali trainer.")

        # 2. Pulizia (Opzionale, ma sicura per test)
        print("🗑️  Pulizia record esistenti (Review, Requests, Messages)...")
        # Invece di cancellare tutto, usiamo un approccio soft o selettivo se preferito, 
        # ma per popolamento test di solito si resetta.
        ReviewMessage.query.delete()
        ReviewAcknowledgment.query.delete()
        ReviewRequest.query.delete()
        Review.query.delete()
        db.session.commit()

        # 3. Generazione Training (Reviews)
        reviews_count = 0
        for prof in professionals:
            num = random.randint(MIN_TRAINING, MAX_TRAINING)
            spec = str(prof.specialty.value) if hasattr(prof.specialty, 'value') else str(prof.specialty)
            titles = TRAINING_TITLES.get(spec, TRAINING_TITLES['default'])

            for _ in range(num):
                trainer = random.choice(admins)
                if trainer.id == prof.id: continue # Non auto-training
                
                rtype = random.choices(REVIEW_TYPES, weights=REVIEW_TYPE_WEIGHTS)[0]
                p_start, p_end = get_random_date_range()
                
                review = Review(
                    reviewer_id=trainer.id,
                    reviewee_id=prof.id,
                    title=random.choice(titles),
                    content=random.choice(TRAINING_CONTENTS[rtype]),
                    review_type=rtype,
                    rating=random.randint(3, 5),
                    period_start=p_start,
                    period_end=p_end,
                    strengths=random.choice(STRENGTHS),
                    improvements=random.choice(IMPROVEMENTS),
                    goals=random.choice(GOALS),
                    is_draft=False,
                    is_private=random.random() < 0.1,
                    created_at=OGGI - timedelta(days=random.randint(1, 60))
                )
                db.session.add(review)
                db.session.flush() # Ottieni ID
                reviews_count += 1

                # Acknowledgment (Conferma) - 70% probabilità
                if random.random() < 0.7:
                    ack = ReviewAcknowledgment(
                        review_id=review.id,
                        acknowledged_by=prof.id,
                        acknowledged_at=review.created_at + timedelta(days=random.randint(1, 5)),
                        notes=random.choice(["Letto e compreso.", "Grazie per il feedback!", "Metto in pratica subito."]) if random.random() > 0.5 else None
                    )
                    db.session.add(ack)

                # Messaggi in chat
                if random.random() < 0.6:
                    for _ in range(random.randint(1, 3)):
                        msg1 = ReviewMessage(
                            review_id=review.id,
                            sender_id=trainer.id,
                            content=random.choice(CHAT_REVIEWER),
                            created_at=review.created_at + timedelta(hours=random.randint(1, 48))
                        )
                        db.session.add(msg1)
                        
                        if random.random() > 0.3:
                            msg2 = ReviewMessage(
                                review_id=review.id,
                                sender_id=prof.id,
                                content=random.choice(CHAT_REVIEWEE),
                                created_at=msg1.created_at + timedelta(hours=random.randint(1, 12))
                            )
                            db.session.add(msg2)

        # 4. Generazione Richieste (ReviewRequests)
        requests_count = 0
        for prof in professionals:
            if random.random() < 0.4: # 40% degli utenti fa richieste
                for _ in range(random.randint(1, 2)):
                    trainer = random.choice(admins)
                    if trainer.id == prof.id: continue

                    priority = random.choices(PRIORITIES, weights=PRIORITY_WEIGHTS)[0]
                    status = random.choice(['pending', 'accepted', 'completed', 'rejected'])
                    
                    req = ReviewRequest(
                        requester_id=prof.id,
                        requested_to_id=trainer.id,
                        subject=f"Richiesta {priority} per supporto su {prof.specialty.value if hasattr(prof.specialty, 'value') else prof.specialty}",
                        description="Sento la necessità di approfondire alcuni aspetti tecnici relativi alle ultime linee guida. Sarebbe possibile programmare una breve sessione di training?",
                        priority=priority,
                        status=status,
                        created_at=OGGI - timedelta(days=random.randint(1, 30))
                    )
                    
                    if status != 'pending':
                        req.responded_at = req.created_at + timedelta(days=random.randint(1, 7))
                        req.response_notes = "Richiesta gestita. Vediamoci mercoledì per approfondire."

                    db.session.add(req)
                    requests_count += 1


        # 5. Creazione/Garanzia Utente Demo TEAM LEADER
        print("👤 Verifica utente DEMO Team Leader...")
        demo_email = "teamleader@demo.com"
        demo_password = "password123!"
        
        demo_user = User.query.filter_by(email=demo_email).first()
        if not demo_user:
            demo_user = User(
                email=demo_email,
                first_name="Marco",
                last_name="Rossi (TL)",
                role='team_leader',
                specialty='coach',
                is_active=True,
                is_admin=True,
                trial_stage=3
            )
            demo_user.set_password(demo_password)
            db.session.add(demo_user)
            db.session.commit()
            print(f"   - Creato nuovo utente: {demo_email}")
        else:
            # Assicuriamoci che sia attivo e con ruolo giusto
            demo_user.is_active = True
            demo_user.role = 'team_leader'
            demo_user.specialty = 'coach' # Così vede anche i training ricevuti
            demo_user.is_admin = True
            # Opzionale: update password se necessario, ma meglio non resettare password di utenti esistenti se non richiesto
            # demo_user.set_password(demo_password) 
            db.session.commit()
            print(f"   - Utente esistente trovato: {demo_email}")

        # 6. Generazione dati specifici per il DEMO user
        print(f"🎁 Generazione dati per utente DEMO ({demo_email})...")
        
        # Training RICEVUTI dal demo user
        trainer = random.choice([u for u in admins if u.id != demo_user.id])
        for _ in range(3):
            rtype = random.choice(REVIEW_TYPES)
            p_start, p_end = get_random_date_range()
            rev = Review(
                reviewer_id=trainer.id,
                reviewee_id=demo_user.id,
                title=f"Training Demo: {rtype.capitalize()}",
                content=f"Contenuto di prova per verificare l'interfaccia. Tipo: {rtype}.",
                review_type=rtype,
                rating=5,
                period_start=p_start,
                period_end=p_end,
                strengths="Punti di forza demo",
                improvements="Miglioramenti demo",
                goals="Obiettivi demo",
                is_draft=False,
                is_private=False,
                created_at=OGGI - timedelta(days=random.randint(1, 10))
            )
            db.session.add(rev)
        
        # Richieste INVIATE dal demo user
        req = ReviewRequest(
            requester_id=demo_user.id,
            requested_to_id=trainer.id,
            subject="Richiesta Demo",
            description="Questa è una richiesta di prova generata dallo script.",
            priority='high',
            status='pending',
            created_at=OGGI
        )
        db.session.add(req)

        # Training SCRITTI dal demo user (se vogliamo testare lato erogatore)
        # ... opzionale

        db.session.commit()

        print(f"✅ Popolamento completato!")
        print(f"   - {reviews_count} Training creati (generale)")
        print(f"   - {requests_count} Richieste create (generale)")
        print(f"==================================================")
        print(f"🔐 CREDENZIALI DI ACCESSO DI TEST")
        print(f"   Email:    {demo_email}")
        print(f"   Password: {demo_password} (se creato ora, altrimenti password esistente)")
        print(f"==================================================")

if __name__ == "__main__":
    main()
