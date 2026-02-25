#!/usr/bin/env python3
"""
Script di seed per creare Training/Formazione per i professionisti.

Crea:
- Review (Training ricevuti/erogati)
- ReviewRequest (Richieste di training)
- ReviewAcknowledgment (Conferme)
- ReviewMessage (Chat)

Ogni professionista riceve 3-8 training nel tempo.
I team leader danno training ai membri del team.
"""

import sys
import os
import random
from datetime import datetime, timedelta, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================
# CONFIGURAZIONE
# ============================================================

BATCH_SIZE = 100
OGGI = date(2026, 1, 22)

# Range training per professionista
MIN_TRAINING = 3
MAX_TRAINING = 8

# Review types
REVIEW_TYPES = ['settimanale', 'mensile', 'progetto', 'miglioramento']
REVIEW_TYPE_WEIGHTS = [40, 35, 15, 10]  # settimanale più comune

# Priorità richieste
PRIORITIES = ['low', 'normal', 'high', 'urgent']
PRIORITY_WEIGHTS = [15, 50, 25, 10]

# ============================================================
# TEMPLATE TRAINING
# ============================================================

# Titoli training per specialità
TRAINING_TITLES = {
    'nutrizionista': [
        "Aggiornamento protocolli nutrizionali",
        "Gestione pazienti con DCA",
        "Comunicazione efficace con i clienti",
        "Nuove linee guida alimentari",
        "Gestione casi complessi",
        "Miglioramento compliance alimentare",
        "Tecniche di counseling nutrizionale",
        "Gestione intolleranze alimentari",
        "Approccio multidisciplinare",
        "Feedback mensile performance",
    ],
    'coach': [
        "Tecniche di motivazione avanzate",
        "Programmazione allenamento personalizzato",
        "Gestione infortuni e prevenzione",
        "Comunicazione con clienti difficili",
        "Nuovi protocolli di allenamento",
        "Periodizzazione e progressione",
        "Coaching online efficace",
        "Gestione aspettative clienti",
        "Feedback mensile performance",
        "Aggiornamento strumenti digitali",
    ],
    'psicologo': [
        "Tecniche CBT per DCA",
        "Gestione crisi emotiva",
        "Approccio motivazionale",
        "Supervisione casi clinici",
        "Nuovi protocolli terapeutici",
        "Gestione burnout professionale",
        "Comunicazione empatica avanzata",
        "Lavoro di equipe multidisciplinare",
        "Feedback mensile performance",
        "Mindfulness e alimentazione",
    ],
    'default': [
        "Aggiornamento procedure aziendali",
        "Comunicazione interna efficace",
        "Gestione del tempo",
        "Feedback performance trimestrale",
        "Obiettivi e KPI",
    ],
}

# Contenuti training
TRAINING_CONTENTS = {
    'settimanale': [
        "Questa settimana abbiamo discusso i seguenti punti:\n\n1. Revisione casi della settimana\n2. Feedback sui progressi dei clienti\n3. Aree di miglioramento identificate\n4. Obiettivi per la prossima settimana",
        "Incontro settimanale per allineamento:\n\n- Analisi delle difficoltà emerse\n- Condivisione best practices\n- Pianificazione attività\n- Supporto su casi specifici",
        "Sessione di supervisione settimanale:\n\n• Discussione casi prioritari\n• Verifica rispetto protocolli\n• Feedback bidirezionale\n• Azioni correttive concordate",
    ],
    'mensile': [
        "Revisione mensile delle performance:\n\n📊 KPI del mese:\n- Clienti seguiti: ottimo\n- Feedback clienti: positivo\n- Rispetto tempistiche: buono\n\n🎯 Obiettivi raggiunti:\n- Miglioramento comunicazione\n- Riduzione tempi risposta\n\n📝 Aree di sviluppo:\n- Approfondire casi complessi",
        "Feedback mensile:\n\nPunti di forza evidenziati questo mese:\n✓ Eccellente rapporto con i clienti\n✓ Proattività nella risoluzione problemi\n✓ Collaborazione con il team\n\nAree di miglioramento:\n→ Documentazione più dettagliata\n→ Gestione del tempo",
    ],
    'progetto': [
        "Formazione su nuovo progetto aziendale:\n\nObiettivi del progetto:\n1. Implementazione nuovo protocollo\n2. Formazione team su nuove procedure\n3. Monitoraggio risultati\n\nRuolo assegnato e responsabilità discusse in dettaglio.",
        "Briefing progetto speciale:\n\nDescrizione iniziativa e aspettative.\nTimeline e milestone definiti.\nRisorse disponibili e supporto previsto.",
    ],
    'miglioramento': [
        "Piano di miglioramento concordato:\n\nAree identificate:\n- Gestione del tempo\n- Comunicazione scritta\n- Documentazione casi\n\nAzioni concrete:\n1. Corso time management\n2. Template standardizzati\n3. Check-in settimanali",
        "Percorso di sviluppo personalizzato:\n\nObiettivi SMART definiti per il prossimo trimestre.\nRisorse formative assegnate.\nMentor identificato per supporto.",
    ],
}

# Punti di forza
STRENGTHS = [
    "Ottima capacità di comunicazione con i clienti. Empatia e ascolto attivo.",
    "Professionalità e puntualità nel rispetto delle scadenze.",
    "Eccellente collaborazione con il team multidisciplinare.",
    "Proattività nella risoluzione dei problemi.",
    "Competenze tecniche solide e aggiornate.",
    "Capacità di motivare i clienti anche nei momenti difficili.",
    "Flessibilità e adattamento alle esigenze dei clienti.",
    "Precisione nella documentazione e nel follow-up.",
    "Creatività nell'approccio ai casi complessi.",
    "Affidabilità e costanza nel lavoro quotidiano.",
]

# Aree di miglioramento
IMPROVEMENTS = [
    "Migliorare la gestione del tempo tra i vari clienti.",
    "Approfondire la documentazione dei casi.",
    "Lavorare sulla comunicazione scritta con i clienti.",
    "Sviluppare maggiore assertività nelle situazioni difficili.",
    "Migliorare la gestione dello stress lavorativo.",
    "Approfondire le competenze su casi specifici (DCA, patologie).",
    "Ottimizzare l'organizzazione del proprio lavoro.",
    "Migliorare la puntualità nelle risposte ai clienti.",
    "Sviluppare capacità di delega quando necessario.",
    "Lavorare sull'equilibrio vita-lavoro.",
]

# Obiettivi
GOALS = [
    "Ridurre i tempi di risposta ai clienti del 20% entro il prossimo mese.",
    "Completare il corso di aggiornamento professionale entro fine trimestre.",
    "Migliorare il tasso di retention clienti del 10%.",
    "Implementare le nuove procedure entro 2 settimane.",
    "Partecipare attivamente a 3 sessioni di supervisione.",
    "Documentare almeno 5 casi studio per condivisione team.",
    "Raggiungere un rating medio clienti di 4.5/5.",
    "Completare la formazione sui nuovi strumenti digitali.",
    "Sviluppare 2 nuovi template per la comunicazione.",
    "Aumentare le sessioni di follow-up del 15%.",
]

# Soggetti richieste training
REQUEST_SUBJECTS = [
    "Richiesta formazione su casi DCA",
    "Supporto gestione cliente difficile",
    "Aggiornamento su nuovi protocolli",
    "Richiesta supervisione caso specifico",
    "Formazione strumenti digitali",
    "Supporto per migliorare comunicazione",
    "Richiesta feedback su performance",
    "Formazione su nuove linee guida",
    "Supervisione casi complessi",
    "Richiesta mentoring",
]

# Descrizioni richieste
REQUEST_DESCRIPTIONS = [
    "Vorrei ricevere formazione specifica su questo argomento per migliorare le mie competenze.",
    "Ho bisogno di supporto per gestire al meglio una situazione complessa con un cliente.",
    "Richiedo un aggiornamento sulle ultime novità in ambito professionale.",
    "Vorrei discutere alcuni casi che mi stanno dando difficoltà.",
    "Ho bisogno di formazione sui nuovi strumenti che stiamo implementando.",
    None,  # Nessuna descrizione
    "Gradirei un momento di confronto per ricevere feedback costruttivo.",
    None,
]

# Messaggi chat
CHAT_MESSAGES = {
    'reviewer': [
        "Grazie per l'impegno dimostrato. Continua così!",
        "Ho aggiunto alcune note. Fammi sapere se hai domande.",
        "Ottimo lavoro questa settimana.",
        "Ricordati di implementare quanto discusso.",
        "Sono disponibile per un ulteriore confronto se necessario.",
    ],
    'reviewee': [
        "Grazie per il feedback, molto utile!",
        "Ho preso nota di tutti i punti discussi.",
        "Procederò come concordato.",
        "Grazie per il supporto, apprezzo molto.",
        "Ho alcune domande sul punto 2, possiamo approfondire?",
    ],
}

# Note acknowledgment
ACKNOWLEDGMENT_NOTES = [
    "Preso visione. Grazie per il feedback costruttivo.",
    "Ho letto attentamente. Procederò come indicato.",
    "Grazie, molto utile per il mio percorso di crescita.",
    "",  # Nessuna nota
    "Confermo la presa visione del training.",
    "Grazie per il tempo dedicato.",
    None,
]


def get_random_date_range(start_year=2024, end_date=OGGI):
    """Genera un periodo casuale per il training"""
    # Data inizio casuale
    start = date(start_year, random.randint(1, 12), random.randint(1, 28))
    if start > end_date:
        start = end_date - timedelta(days=random.randint(30, 180))

    # Durata periodo (1-4 settimane tipicamente)
    duration = random.randint(7, 28)
    end = start + timedelta(days=duration)

    if end > end_date:
        end = end_date

    return start, end


def main():
    from corposostenibile import create_app
    from corposostenibile.extensions import db
    from corposostenibile.models import User, Review, ReviewRequest, ReviewAcknowledgment, ReviewMessage

    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("SEED PROFESSIONALS - Training/Formazione")
        print("=" * 60)

        # ============================================================
        # PULIZIA DATI PRECEDENTI
        # ============================================================
        print("\n🗑️  Pulizia training precedenti...")

        deleted_messages = ReviewMessage.query.delete()
        deleted_ack = ReviewAcknowledgment.query.delete()
        deleted_requests = ReviewRequest.query.delete()
        deleted_reviews = Review.query.delete()
        db.session.commit()

        print(f"   Eliminati {deleted_messages} ReviewMessage")
        print(f"   Eliminati {deleted_ack} ReviewAcknowledgment")
        print(f"   Eliminati {deleted_requests} ReviewRequest")
        print(f"   Eliminati {deleted_reviews} Review")

        # ============================================================
        # CARICA UTENTI
        # ============================================================
        print("\n📋 Caricamento utenti...")

        # Professionisti attivi
        professionals = User.query.filter(
            User.is_active == True,
            User.specialty.in_(['nutrizionista', 'coach', 'psicologo'])
        ).all()
        print(f"   Professionisti attivi: {len(professionals)}")

        # Team leader e admin (possono dare training)
        trainers = User.query.filter(
            User.is_active == True,
            User.role.in_(['admin', 'team_leader'])
        ).all()

        # Se non ci sono abbastanza trainer, usa anche professionisti senior
        if len(trainers) < 10:
            senior_profs = User.query.filter(
                User.is_active == True,
                User.id < 50  # Primi utenti come senior
            ).limit(20).all()
            trainers.extend(senior_profs)

        trainers = list(set(trainers))  # Rimuovi duplicati
        print(f"   Trainer disponibili: {len(trainers)}")

        if not professionals or not trainers:
            print("❌ Mancano professionisti o trainer!")
            return

        # ============================================================
        # CREAZIONE TRAINING
        # ============================================================
        print(f"\n📝 Generazione Training per {len(professionals)} professionisti...")

        start_time = datetime.now()
        reviews_created = 0
        requests_created = 0
        acks_created = 0
        messages_created = 0

        for idx, prof in enumerate(professionals):
            specialty = str(prof.specialty.value) if prof.specialty else 'default'
            titles = TRAINING_TITLES.get(specialty, TRAINING_TITLES['default'])

            # Numero training per questo professionista
            num_training = random.randint(MIN_TRAINING, MAX_TRAINING)

            # Seleziona trainer (preferibilmente stesso team/dipartimento)
            available_trainers = [t for t in trainers if t.id != prof.id]
            if not available_trainers:
                available_trainers = trainers

            for _ in range(num_training):
                trainer = random.choice(available_trainers)
                review_type = random.choices(REVIEW_TYPES, weights=REVIEW_TYPE_WEIGHTS)[0]

                period_start, period_end = get_random_date_range()

                # Seleziona contenuto appropriato
                contents = TRAINING_CONTENTS.get(review_type, TRAINING_CONTENTS['settimanale'])

                review = Review(
                    reviewer_id=trainer.id,
                    reviewee_id=prof.id,
                    title=random.choice(titles),
                    content=random.choice(contents),
                    review_type=review_type,
                    rating=random.randint(3, 5),  # Rating positivi (3-5)
                    period_start=period_start,
                    period_end=period_end,
                    strengths=random.choice(STRENGTHS),
                    improvements=random.choice(IMPROVEMENTS),
                    goals=random.choice(GOALS),
                    is_draft=False,
                    is_private=random.random() < 0.1,  # 10% privati
                    created_at=datetime.combine(period_end, datetime.min.time()) + timedelta(days=random.randint(1, 7)),
                )
                db.session.add(review)
                db.session.flush()  # Per ottenere ID
                reviews_created += 1

                # Acknowledgment (80% dei training sono stati confermati)
                if random.random() < 0.80:
                    ack_notes = random.choice(ACKNOWLEDGMENT_NOTES)
                    ack = ReviewAcknowledgment(
                        review_id=review.id,
                        acknowledged_by=prof.id,
                        acknowledged_at=review.created_at + timedelta(days=random.randint(0, 3)),
                        notes=ack_notes if ack_notes else None,
                    )
                    db.session.add(ack)
                    acks_created += 1

                # Messaggi chat (50% dei training hanno messaggi)
                if random.random() < 0.50:
                    num_messages = random.randint(1, 4)
                    msg_date = review.created_at

                    for m in range(num_messages):
                        # Alterna tra reviewer e reviewee
                        if m % 2 == 0:
                            sender_id = trainer.id
                            content = random.choice(CHAT_MESSAGES['reviewer'])
                        else:
                            sender_id = prof.id
                            content = random.choice(CHAT_MESSAGES['reviewee'])

                        msg_date = msg_date + timedelta(hours=random.randint(1, 48))

                        msg = ReviewMessage(
                            review_id=review.id,
                            sender_id=sender_id,
                            content=content,
                            is_read=random.random() < 0.70,
                            created_at=msg_date,
                        )
                        db.session.add(msg)
                        messages_created += 1

            # Richieste training (30% dei professionisti ha fatto richieste)
            if random.random() < 0.30:
                num_requests = random.randint(1, 3)
                for _ in range(num_requests):
                    req_trainer = random.choice(available_trainers)
                    priority = random.choices(PRIORITIES, weights=PRIORITY_WEIGHTS)[0]

                    # Status distribuzione realistica
                    status_roll = random.random()
                    if status_roll < 0.20:
                        status = 'pending'
                        responded_at = None
                        response_notes = None
                    elif status_roll < 0.60:
                        status = 'completed'
                        responded_at = datetime.now() - timedelta(days=random.randint(7, 90))
                        response_notes = "Formazione erogata come richiesto."
                    elif status_roll < 0.85:
                        status = 'accepted'
                        responded_at = datetime.now() - timedelta(days=random.randint(1, 14))
                        response_notes = "Accettata. Pianificheremo a breve."
                    else:
                        status = 'rejected'
                        responded_at = datetime.now() - timedelta(days=random.randint(7, 60))
                        response_notes = "Al momento non è possibile. Riprova tra qualche settimana."

                    description = random.choice(REQUEST_DESCRIPTIONS)

                    request = ReviewRequest(
                        requester_id=prof.id,
                        requested_to_id=req_trainer.id,
                        subject=random.choice(REQUEST_SUBJECTS),
                        description=description,
                        priority=priority,
                        status=status,
                        responded_at=responded_at,
                        response_notes=response_notes,
                        created_at=datetime.now() - timedelta(days=random.randint(1, 120)),
                    )
                    db.session.add(request)
                    requests_created += 1

            # Commit ogni batch
            if (idx + 1) % BATCH_SIZE == 0:
                db.session.commit()
                progress = (idx + 1) / len(professionals) * 100
                elapsed = (datetime.now() - start_time).total_seconds()
                print(f"  ✅ {idx+1}/{len(professionals)} ({progress:.1f}%) - Reviews: {reviews_created} | Requests: {requests_created}")

        # Commit finale
        db.session.commit()

        # ============================================================
        # RIEPILOGO
        # ============================================================
        elapsed_total = (datetime.now() - start_time).total_seconds()

        print("\n" + "=" * 60)
        print("RIEPILOGO")
        print("=" * 60)

        print(f"\n⏱️  Tempo totale: {elapsed_total:.1f} secondi")

        print(f"\n📊 RECORD CREATI:")
        print(f"   Review (Training): {reviews_created:,}")
        print(f"   ReviewRequest (Richieste): {requests_created:,}")
        print(f"   ReviewAcknowledgment (Conferme): {acks_created:,}")
        print(f"   ReviewMessage (Messaggi): {messages_created:,}")

        avg_training = reviews_created / len(professionals) if professionals else 0
        print(f"\n   Media training per professionista: {avg_training:.1f}")

        # Statistiche per tipo
        print(f"\n📊 DISTRIBUZIONE REVIEW TYPE:")
        for rt in REVIEW_TYPES:
            count = Review.query.filter_by(review_type=rt).count()
            pct = count / reviews_created * 100 if reviews_created > 0 else 0
            print(f"   {rt:15}: {count:,} ({pct:.1f}%)")

        # Sample
        print("\n📋 Esempio training:")
        sample = Review.query.first()
        if sample:
            reviewer = User.query.get(sample.reviewer_id)
            reviewee = User.query.get(sample.reviewee_id)
            print(f"\n   Titolo: {sample.title}")
            print(f"   Da: {reviewer.first_name} {reviewer.last_name}")
            print(f"   A: {reviewee.first_name} {reviewee.last_name}")
            print(f"   Tipo: {sample.review_type}")
            print(f"   Rating: {'⭐' * sample.rating}")
            print(f"   Periodo: {sample.period_start} - {sample.period_end}")

        print("\n✅ TRAINING SEED COMPLETATO!")


if __name__ == '__main__':
    main()
