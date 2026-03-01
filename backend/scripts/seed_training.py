"""
seed_training.py
================
Popola il DB con dati di formazione finti (Review, ReviewAcknowledgment,
ReviewRequest, ReviewMessage) per test.

Uso:
    cd backend && poetry run python scripts/seed_training.py
"""

import os
import sys
import random
from datetime import datetime, timedelta

# Aggiungi il path del backend al PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import User, UserRoleEnum

app = create_app()

# ─── Training topics (admin → professionisti) ─────────────────────────────────
TRAININGS = [
    {
        "title": "Protocollo di accoglienza nuovo paziente",
        "content": (
            "Formazione sul protocollo standard di accoglienza dei nuovi pazienti. "
            "Abbiamo rivisto i passaggi dalla prima call conoscitiva fino alla consegna "
            "del piano personalizzato, incluse le tempistiche da rispettare e la "
            "documentazione da compilare."
        ),
        "review_type": "formazione",
        "rating": 4,
        "strengths": "Ottima comprensione del protocollo e puntualità nella consegna della documentazione.",
        "improvements": "Migliorare la gestione dei tempi durante la call iniziale.",
        "goals": "Ridurre il tempo medio di onboarding del 15% entro il prossimo trimestre.",
        "sample_size": 40,
    },
    {
        "title": "Gestione pazienti ghost e strategie di recupero",
        "content": (
            "Training sulla gestione dei pazienti ghost: come identificarli precocemente, "
            "strategie di ri-engagement via WhatsApp e chiamata, escalation al team leader. "
            "Analisi dei casi di successo nel recupero pazienti."
        ),
        "review_type": "formazione",
        "rating": 5,
        "strengths": "Buona proattività nel contattare i pazienti a rischio.",
        "improvements": "Documentare meglio i tentativi di contatto nel CRM.",
        "goals": "Portare il tasso di recupero ghost al 40% entro 2 mesi.",
        "sample_size": 50,
    },
    {
        "title": "Utilizzo della piattaforma Suite Clinica",
        "content": (
            "Sessione formativa sull'utilizzo corretto della piattaforma Suite Clinica: "
            "compilazione schede paziente, gestione check settimanali, invio solleciti, "
            "utilizzo del planner interno e gestione ticket."
        ),
        "review_type": "formazione",
        "rating": 4,
        "strengths": "Rapido apprendimento delle funzionalità base.",
        "improvements": "Esplorare le funzionalità avanzate di reportistica.",
        "goals": "Completare tutti i check settimanali entro il venerdì di ogni settimana.",
        "sample_size": 60,
    },
    {
        "title": "Comunicazione empatica con il paziente",
        "content": (
            "Workshop sulla comunicazione empatica: tecniche di ascolto attivo, "
            "gestione delle obiezioni, comunicazione di risultati negativi, "
            "motivazione del paziente nei momenti di difficoltà."
        ),
        "review_type": "formazione",
        "rating": 5,
        "strengths": "Eccellente capacità di ascolto e creazione del rapporto di fiducia.",
        "improvements": "Lavorare sulla gestione delle situazioni conflittuali.",
        "goals": "Aumentare il NPS dei pazienti seguiti del 10%.",
        "sample_size": 45,
    },
    {
        "title": "Procedure di emergenza e segnalazione",
        "content": (
            "Formazione sulle procedure da seguire in caso di emergenza: "
            "segnalazione DCA grave, ideazione suicidaria, crisi d'ansia acuta. "
            "Protocolli di escalation e numeri di riferimento."
        ),
        "review_type": "formazione",
        "rating": 4,
        "strengths": "Conoscenza adeguata dei protocolli di emergenza.",
        "improvements": "Esercitarsi con simulazioni pratiche più frequenti.",
        "goals": "Zero ritardi nelle segnalazioni di emergenza.",
        "sample_size": 55,
    },
    {
        "title": "Aggiornamento linee guida nutrizionali 2025",
        "content": (
            "Presentazione delle nuove linee guida nutrizionali aggiornate per il 2025. "
            "Focus su diete personalizzate per patologie metaboliche, intolleranze "
            "alimentari e nuovi protocolli per pazienti con DCA."
        ),
        "review_type": "formazione",
        "rating": 4,
        "strengths": "Ottimo aggiornamento professionale e applicazione pratica.",
        "improvements": "Approfondire i casi clinici complessi con supervisione.",
        "goals": "Applicare le nuove linee guida a tutti i nuovi piani entro 30 giorni.",
        "sample_size": 35,
    },
    {
        "title": "Team building e collaborazione interprofessionale",
        "content": (
            "Sessione di team building focalizzata sulla collaborazione tra nutrizionisti, "
            "coach e psicologi. Come condividere informazioni sul paziente in modo efficace, "
            "riunioni di equipe, casi clinici condivisi."
        ),
        "review_type": "formazione",
        "rating": 5,
        "strengths": "Forte spirito di squadra e disponibilità alla collaborazione.",
        "improvements": "Standardizzare il formato delle note condivise tra professionisti.",
        "goals": "Implementare riunioni di equipe settimanali per i casi NCP.",
        "sample_size": 50,
    },
    {
        "title": "Privacy e GDPR nella gestione dati sanitari",
        "content": (
            "Formazione obbligatoria su privacy e GDPR: trattamento dati sanitari, "
            "consenso informato, conservazione documenti, diritto all'oblio. "
            "Casi pratici e errori comuni da evitare."
        ),
        "review_type": "formazione",
        "rating": 3,
        "strengths": "Consapevolezza dell'importanza della protezione dati.",
        "improvements": "Prestare maggiore attenzione alla gestione dei consensi.",
        "goals": "Raggiungere il 100% di compliance GDPR entro il prossimo audit.",
        "sample_size": 60,
    },
]

# ─── Review request topics (professionisti → admin) ───────────────────────────
REQUESTS = [
    {
        "subject": "Richiesta supervisione caso DCA complesso",
        "description": (
            "Ho un paziente con DCA restrittivo che non risponde al protocollo standard. "
            "Vorrei una supervisione per valutare approcci alternativi."
        ),
        "priority": "high",
        "count": 4,
    },
    {
        "subject": "Formazione su nuovi integratori",
        "description": (
            "Vorrei ricevere formazione sui nuovi integratori disponibili e le "
            "evidenze scientifiche a supporto del loro utilizzo nei piani nutrizionali."
        ),
        "priority": "normal",
        "count": 3,
    },
    {
        "subject": "Aggiornamento protocollo pazienti pediatrici",
        "description": (
            "Serve un aggiornamento sulle linee guida per la gestione dei pazienti "
            "in età pediatrica, in particolare per quanto riguarda la comunicazione con i genitori."
        ),
        "priority": "normal",
        "count": 2,
    },
    {
        "subject": "Workshop gestione burnout professionale",
        "description": (
            "Propongo un workshop sulla prevenzione del burnout per il team. "
            "Molti colleghi mostrano segni di stanchezza e sarebbe utile avere strumenti concreti."
        ),
        "priority": "high",
        "count": 5,
    },
    {
        "subject": "Certificazione coaching motivazionale",
        "description": (
            "Vorrei frequentare il corso di certificazione in coaching motivazionale. "
            "Chiedo approvazione e supporto per la partecipazione."
        ),
        "priority": "low",
        "count": 3,
    },
    {
        "subject": "Revisione template check settimanale",
        "description": (
            "Il template attuale del check settimanale è troppo lungo e alcuni pazienti "
            "non lo compilano. Propongo di rivederlo insieme per semplificarlo."
        ),
        "priority": "normal",
        "count": 4,
    },
]

# ─── Messages templates ───────────────────────────────────────────────────────
MESSAGES_FROM_REVIEWER = [
    "Ottimo lavoro, continua così!",
    "Ho notato dei miglioramenti significativi, complimenti.",
    "Ti consiglio di rivedere la sezione sulla documentazione.",
    "Pianifichiamo un follow-up tra due settimane per verificare i progressi.",
    "Hai domande su quanto discusso durante la formazione?",
]

MESSAGES_FROM_REVIEWEE = [
    "Grazie per il feedback, molto utile!",
    "Ho preso nota di tutti i punti, lavorerò sui miglioramenti.",
    "Possiamo approfondire il tema della comunicazione empatica?",
    "Ho già iniziato ad applicare quanto appreso, vedo risultati positivi.",
    "Vorrei fissare un incontro per discutere un caso specifico.",
]

REQUEST_RESPONSE_NOTES = [
    "Ottima proposta, organizziamo a breve.",
    "Richiesta accettata, programmiamo per la prossima settimana.",
    "Approvo la richiesta, coordiniamoci con il team.",
    "Purtroppo al momento non è possibile, rimandiamo al prossimo trimestre.",
    "Richiesta completata con successo, buon lavoro!",
]


def run():
    with app.app_context():
        # Trova Matteo Volpara (admin)
        admin = User.query.filter_by(is_admin=True).first()
        if not admin:
            print("ERRORE: Nessun admin trovato!")
            return
        print(f"Admin trovato: {admin.first_name} {admin.last_name} (id={admin.id})")

        # Tutti i professionisti (non admin, non HM)
        professionisti = User.query.filter(
            User.role.in_([UserRoleEnum.professionista, UserRoleEnum.team_leader]),
            User.is_admin.is_(False),
            User.id != admin.id,
        ).all()
        print(f"Professionisti trovati: {len(professionisti)}")

        if not professionisti:
            print("ERRORE: Nessun professionista trovato!")
            return

        from corposostenibile.models import Review, ReviewAcknowledgment, ReviewRequest, ReviewMessage

        # Pulizia dati esistenti
        print("Pulizia dati formazione esistenti...")
        ReviewMessage.query.delete()
        ReviewAcknowledgment.query.delete()
        ReviewRequest.query.delete()
        Review.query.delete()
        db.session.commit()
        print("Pulizia completata.")

        now = datetime.utcnow()
        review_count = 0
        ack_count = 0
        msg_count = 0

        # ─── 1. Crea Reviews (formazione erogata) ─────────────────────────
        print("\nCreazione formazioni erogate...")
        for i, t in enumerate(TRAININGS):
            sample = random.sample(professionisti, min(t["sample_size"], len(professionisti)))
            days_ago = random.randint(7, 120)
            base_date = now - timedelta(days=days_ago)

            for prof in sample:
                review = Review(
                    reviewer_id=admin.id,
                    reviewee_id=prof.id,
                    title=t["title"],
                    content=t["content"],
                    review_type=t["review_type"],
                    rating=t["rating"],
                    period_start=(base_date - timedelta(days=30)).date(),
                    period_end=base_date.date(),
                    strengths=t["strengths"],
                    improvements=t["improvements"],
                    goals=t["goals"],
                    is_draft=False,
                    is_private=False,
                    created_at=base_date,
                    updated_at=base_date,
                )
                db.session.add(review)
                db.session.flush()  # get review.id
                review_count += 1

                # 80% acknowledgment
                if random.random() < 0.80:
                    ack = ReviewAcknowledgment(
                        review_id=review.id,
                        acknowledged_by=prof.id,
                        acknowledged_at=base_date + timedelta(hours=random.randint(1, 72)),
                        notes=random.choice([None, "Preso atto, grazie.", "Ricevuto.", None]),
                    )
                    db.session.add(ack)
                    ack_count += 1

                # 25% messages
                if random.random() < 0.25:
                    msg1 = ReviewMessage(
                        review_id=review.id,
                        sender_id=admin.id,
                        content=random.choice(MESSAGES_FROM_REVIEWER),
                        is_read=True,
                        read_at=base_date + timedelta(hours=random.randint(2, 48)),
                        read_by=prof.id,
                        created_at=base_date + timedelta(hours=1),
                    )
                    db.session.add(msg1)
                    msg_count += 1

                    # 60% di chi riceve messaggio risponde
                    if random.random() < 0.60:
                        msg2 = ReviewMessage(
                            review_id=review.id,
                            sender_id=prof.id,
                            content=random.choice(MESSAGES_FROM_REVIEWEE),
                            is_read=True,
                            read_at=base_date + timedelta(hours=random.randint(24, 96)),
                            read_by=admin.id,
                            created_at=base_date + timedelta(hours=random.randint(4, 24)),
                        )
                        db.session.add(msg2)
                        msg_count += 1

            # Commit per ogni training topic (batch)
            db.session.commit()
            print(f"  [{i+1}/{len(TRAININGS)}] \"{t['title']}\" → {len(sample)} professionisti")

        print(f"\nTotale: {review_count} reviews, {ack_count} acknowledgments, {msg_count} messaggi")

        # ─── 2. Crea ReviewRequests (richieste dai professionisti) ─────────
        print("\nCreazione richieste di formazione...")
        req_count = 0
        statuses = ["pending", "accepted", "rejected", "completed"]

        for j, r in enumerate(REQUESTS):
            requesters = random.sample(professionisti, min(r["count"], len(professionisti)))

            for prof in requesters:
                days_ago = random.randint(3, 60)
                req_date = now - timedelta(days=days_ago)
                status = random.choice(statuses)

                rr = ReviewRequest(
                    requester_id=prof.id,
                    requested_to_id=admin.id,
                    subject=r["subject"],
                    description=r["description"],
                    status=status,
                    priority=r["priority"],
                    created_at=req_date,
                    updated_at=req_date,
                )

                if status in ("accepted", "rejected", "completed"):
                    rr.responded_at = req_date + timedelta(hours=random.randint(2, 48))
                    rr.response_notes = random.choice(REQUEST_RESPONSE_NOTES)

                db.session.add(rr)
                req_count += 1

            db.session.commit()
            print(f"  [{j+1}/{len(REQUESTS)}] \"{r['subject']}\" → {len(requesters)} richieste")

        print(f"\nTotale richieste: {req_count}")
        print("\n✓ Seed formazione completato con successo!")


if __name__ == "__main__":
    run()
