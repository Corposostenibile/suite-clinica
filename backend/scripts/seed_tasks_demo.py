#!/usr/bin/env python3
"""
Seed 2-3 task per ogni categoria (onboarding, check, reminder, formazione, sollecito, generico).
Assegna a un utente reale e linka a clienti reali.

Usage:
    cd backend
    poetry run python scripts/seed_tasks_demo.py
"""

import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import (
    Task, TaskStatusEnum, TaskPriorityEnum, TaskCategoryEnum,
    User, Cliente,
)

app = create_app()

TASKS = [
    # ── ONBOARDING ──
    {
        "title": "Completare questionario iniziale",
        "description": "Il cliente deve compilare il questionario di anamnesi alimentare e sportiva prima della prima visita.",
        "category": TaskCategoryEnum.onboarding,
        "priority": TaskPriorityEnum.high,
        "due_days": 2,
    },
    {
        "title": "Inviare kit di benvenuto",
        "description": "Preparare e inviare via email il pacchetto informativo con le istruzioni di accesso all'app e i contatti del team.",
        "category": TaskCategoryEnum.onboarding,
        "priority": TaskPriorityEnum.medium,
        "due_days": 1,
    },
    {
        "title": "Primo contatto telefonico",
        "description": "Chiamare il nuovo cliente per presentarsi, spiegare il percorso e rispondere a eventuali domande iniziali.",
        "category": TaskCategoryEnum.onboarding,
        "priority": TaskPriorityEnum.urgent,
        "due_days": 0,
    },

    # ── CHECK ──
    {
        "title": "Verificare weekly check mancante",
        "description": "Il cliente non ha compilato il weekly check di questa settimana. Verificare se ci sono problemi tecnici o motivazionali.",
        "category": TaskCategoryEnum.check,
        "priority": TaskPriorityEnum.high,
        "due_days": 0,
    },
    {
        "title": "Revisione DCA check",
        "description": "Analizzare le risposte del DCA check compilato ieri e valutare se necessario un intervento della psicologa.",
        "category": TaskCategoryEnum.check,
        "priority": TaskPriorityEnum.medium,
        "due_days": 3,
    },
    {
        "title": "Confronto misurazioni mensili",
        "description": "Comparare le misurazioni antropometriche dell'ultimo mese con quelle precedenti per aggiornare il piano.",
        "category": TaskCategoryEnum.check,
        "priority": TaskPriorityEnum.low,
        "due_days": 5,
    },

    # ── REMINDER ──
    {
        "title": "Ricordare appuntamento di domani",
        "description": "Inviare un promemoria al cliente per l'appuntamento di nutrizione programmato per domani mattina.",
        "category": TaskCategoryEnum.reminder,
        "priority": TaskPriorityEnum.medium,
        "due_days": 0,
    },
    {
        "title": "Scadenza piano alimentare",
        "description": "Il piano alimentare attuale scade tra 5 giorni. Programmare la revisione e il rinnovo con il cliente.",
        "category": TaskCategoryEnum.reminder,
        "priority": TaskPriorityEnum.high,
        "due_days": 5,
    },

    # ── FORMAZIONE ──
    {
        "title": "Completare modulo nutrizione sportiva",
        "description": "Completare il modulo di formazione interna sulla nutrizione sportiva e superare il quiz finale.",
        "category": TaskCategoryEnum.formazione,
        "priority": TaskPriorityEnum.low,
        "due_days": 14,
    },
    {
        "title": "Revisione protocollo DCA",
        "description": "Leggere e prendere visione dell'aggiornamento del protocollo DCA pubblicato questa settimana.",
        "category": TaskCategoryEnum.formazione,
        "priority": TaskPriorityEnum.medium,
        "due_days": 7,
    },
    {
        "title": "Webinar gestione ghost client",
        "description": "Partecipare al webinar interno sulle best practice per il recupero dei clienti ghost e le strategie di re-engagement.",
        "category": TaskCategoryEnum.formazione,
        "priority": TaskPriorityEnum.low,
        "due_days": 10,
    },

    # ── SOLLECITO ──
    {
        "title": "Sollecito pagamento fattura",
        "description": "Il cliente ha una fattura scaduta da 15 giorni. Inviare un sollecito gentile via WhatsApp.",
        "category": TaskCategoryEnum.sollecito,
        "priority": TaskPriorityEnum.urgent,
        "due_days": -2,  # scaduto
    },
    {
        "title": "Sollecito compilazione diario alimentare",
        "description": "Il cliente non compila il diario alimentare da 10 giorni. Contattarlo per capire le difficolta e motivarlo.",
        "category": TaskCategoryEnum.sollecito,
        "priority": TaskPriorityEnum.high,
        "due_days": -1,  # scaduto ieri
    },
    {
        "title": "Follow-up cliente inattivo",
        "description": "Il cliente non accede alla piattaforma da 3 settimane. Pianificare una chiamata di follow-up.",
        "category": TaskCategoryEnum.sollecito,
        "priority": TaskPriorityEnum.medium,
        "due_days": 1,
    },

    # ── GENERICO ──
    {
        "title": "Aggiornare note cliniche",
        "description": "Completare le note cliniche della sessione di oggi e caricare i documenti allegati nella scheda cliente.",
        "category": TaskCategoryEnum.generico,
        "priority": TaskPriorityEnum.low,
        "due_days": 2,
    },
    {
        "title": "Preparare report mensile",
        "description": "Compilare il report mensile di attivita con il riepilogo dei clienti seguiti, check ricevuti e obiettivi raggiunti.",
        "category": TaskCategoryEnum.generico,
        "priority": TaskPriorityEnum.medium,
        "due_days": 4,
    },
]


with app.app_context():
    print("=" * 60)
    print("SEED: Task demo (2-3 per categoria)")
    print("=" * 60)

    # Trova un utente assegnatario (il primo professionista attivo)
    assignee = (
        User.query
        .filter(User.is_active.is_(True), User.role != "admin")
        .first()
    )
    if not assignee:
        assignee = User.query.filter(User.is_active.is_(True)).first()

    if not assignee:
        print("ERRORE: nessun utente attivo trovato nel DB.")
        sys.exit(1)

    print(f"Assegnatario: {assignee.full_name} (id={assignee.id})")

    # Prendi alcuni clienti per associarli
    clients = Cliente.query.limit(10).all()
    print(f"Clienti disponibili: {len(clients)}")

    created = 0
    for i, t in enumerate(TASKS):
        client = clients[i % len(clients)] if clients else None
        due = date.today() + timedelta(days=t["due_days"])

        task = Task(
            title=t["title"],
            description=t["description"],
            category=t["category"],
            priority=t["priority"],
            status=TaskStatusEnum.todo,
            assignee_id=assignee.id,
            client_id=client.cliente_id if client else None,
            due_date=due,
            payload={"client_id": client.cliente_id} if client else {},
        )
        db.session.add(task)
        created += 1
        cat = t["category"].value
        pri = t["priority"].value
        cl = client.nome_cognome if client else "-"
        print(f"  [{cat:12}] {pri:6} | {t['title'][:50]:50} | {cl}")

    db.session.commit()
    print(f"\nCreate {created} task con successo!")
    print("=" * 60)
