
import sys
import os
from datetime import datetime, timedelta
import random

# Add backend root to path (4 levels up from script: scripts -> tasks -> blueprints -> corposostenibile -> backend)
# Current path: backend/corposostenibile/blueprints/tasks/scripts/
# We need to add 'backend' to path so 'import corposostenibile' works.
import sys
import os

# Assuming script is run from project root (suite-clinica)
# We need to add 'backend' to sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import (
    User, Task, TaskCategoryEnum, TaskPriorityEnum, TaskStatusEnum, 
    Cliente, Department, UserRoleEnum, UserSpecialtyEnum, ClientCheckAssignment, CheckForm, 
    ClientCheckResponse, Review
)

def generate_triggers(user_email="bruno.villa@corposostenibile.it"):
    app = create_app()
    with app.app_context():
        # Find target user
        user = User.query.filter_by(email=user_email).first()
        if not user:
            print(f"Utente {user_email} non trovato. Cerco un utente nutrizionista...")
            user = User.query.filter_by(specialty=UserSpecialtyEnum.nutrizionista).first()
        
        if not user:
            print("Nessun utente adeguato trovato.")
            return

        user_full_name = f"{user.first_name} {user.last_name}"
        print(f"Generazione trigger per: {user_full_name} (ID: {user.id})")

        # Find some clients
        clients = Cliente.query.limit(5).all()
        if not clients:
            print("Nessun cliente trovato.")
            return

        # -------------------------------------------------------------------
        # 1. TRIGGER ONBOARDING (Update Cliente)
        # -------------------------------------------------------------------
        print("\n--- Triggering Onboarding Tasks ---")
        client_onboard = clients[0]
        # Simulate assignment by re-assigning or un-assigning then re-assigning
        # To trigger 'has_changes', we must change the value.
        original_nutri = client_onboard.nutrizionista_id
        
        # Temporary remove
        client_onboard.nutrizionista_id = None
        db.session.commit()
        
        # Re-assign to target user triggers 'added'
        client_onboard.nutrizionista_id = user.id
        db.session.commit()
        print(f"Assigning {user_full_name} to {client_onboard.nome_cognome} -> Should create Onboarding Task.")

        # -------------------------------------------------------------------
        # 2. TRIGGER CHECK RECEIVED (Insert ClientCheckResponse)
        # -------------------------------------------------------------------
        print("\n--- Triggering Check Received Tasks ---")
        if len(clients) > 1:
            client_check = clients[1]
            
            # Ensure assignment exists
            # Create a dummy form if needed
            form = CheckForm.query.first()
            if not form:
                form = CheckForm(name="Form Test", form_type="settimanale", created_by_id=user.id, is_active=True)
                db.session.add(form)
                db.session.commit()

            # Create assignment assigned BY user TO client
            assignment = ClientCheckAssignment(
                cliente_id=client_check.cliente_id,
                form_id=form.id,
                assigned_by_id=user.id,
                token=ClientCheckAssignment.generate_token()
            )
            db.session.add(assignment)
            db.session.commit()

            # Create Response triggers task
            response = ClientCheckResponse(
                assignment_id=assignment.id,
                responses={"q1": "Bene", "q2": "Tutto ok"}, 
                created_at=datetime.utcnow()
            )
            db.session.add(response)
            db.session.commit()
            print(f"Client {client_check.nome_cognome} submitted check -> Should create Check Task for {user_full_name}.")

        # -------------------------------------------------------------------
        # 3. TRIGGER TRAINING (Insert Review)
        # -------------------------------------------------------------------
        print("\n--- Triggering Training Tasks ---")
        review = Review(
            title="Training: Gestione Clienti Difficili",
            content="Materiale formativo sulla gestione...",
            reviewer_id=user.id, # Self assigned or by another admin
            reviewee_id=user.id,
            rating=0,
            created_at=datetime.utcnow()
        )
        db.session.add(review)
        db.session.commit()
        print(f"Created Review for {user_full_name} -> Should create Training Task.")
        
        # -------------------------------------------------------------------
        # 4. MANUAL TASKS (Generico, Sollecito, etc.)
        # -------------------------------------------------------------------
        print("\n--- Generating Manual Tasks (Generic, Urgent, etc.) ---")
        
        manual_tasks = []
        
        # Generic Reminder
        manual_tasks.append(Task(
            title="Preparare Report Mensile",
            description="Analizzare i progressi dei clienti del mese corrente.",
            category=TaskCategoryEnum.generico,
            status=TaskStatusEnum.todo,
            priority=TaskPriorityEnum.medium,
            assignee_id=user.id,
            due_date=datetime.utcnow() + timedelta(days=5),
            created_at=datetime.utcnow()
        ))

        # Urgent Solicitation (simulated manual creation for now, usually Celery)
        if len(clients) > 2:
             client_urgent = clients[2]
             manual_tasks.append(Task(
                title=f"URGENTE: Contattare {client_urgent.nome_cognome}",
                description="Il cliente ha richiesto assistenza telefonica immediata.",
                category=TaskCategoryEnum.generico,
                status=TaskStatusEnum.todo,
                priority=TaskPriorityEnum.urgent,
                client_id=client_urgent.cliente_id,
                assignee_id=user.id,
                created_at=datetime.utcnow()
            ))

        # Completed Task
        manual_tasks.append(Task(
            title="Aggiornamento Listino",
            description="Aggiornati i prezzi sul sito.",
            category=TaskCategoryEnum.generico,
            status=TaskStatusEnum.done,
            priority=TaskPriorityEnum.low,
            assignee_id=user.id,
            created_at=datetime.utcnow() - timedelta(days=3)
        ))

        for t in manual_tasks:
            db.session.add(t)
        
        db.session.commit()
        print(f"Created {len(manual_tasks)} manual tasks.")

        # Summary
        total = Task.query.filter_by(assignee_id=user.id).count()
        print(f"\nTerminato. Totale task per {user_full_name}: {total}")


if __name__ == "__main__":
    target_email = sys.argv[1] if len(sys.argv) > 1 else "bruno.villa@corposostenibile.it"
    generate_triggers(target_email)
