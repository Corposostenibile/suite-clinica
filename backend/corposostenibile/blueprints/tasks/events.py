from sqlalchemy import event, inspect, and_
from sqlalchemy.orm import attributes
from flask_login import user_logged_in
from flask import current_app
from datetime import datetime, timedelta

from corposostenibile.extensions import db
from corposostenibile.models import (
    Cliente, 
    ClientCheckResponse, 
    Review, 
    Task, 
    TaskCategoryEnum, 
    TaskStatusEnum, 
    TaskPriorityEnum
)

# --------------------------------------------------------------------------- #
#  1. ONBOARDING (Assegnazione Cliente)
# --------------------------------------------------------------------------- #
@event.listens_for(Cliente, 'after_update')
def trigger_onboarding_task(mapper, connection, target):
    """
    Genera un task di onboarding quando viene assegnato un professionista.
    """
    # Verifica cambiamenti nei campi professionista
    # create_task_session = db.session.object_session(target) # after_update keeps session?
    # Usiamo Connection per insert diretti o Session? 
    # after_update passa connection. Se vogliamo usare ORM, meglio Session.
    # Ma attenzione a creare oggetti durante il flush (potrebbe dare warning).
    # listeners.py usava before_flush per questo motivo.
    # Proviamo con Session.
    
    session = db.session
    if not session:
        return

    # Helper per creare task
    def create_onboard_task(assignee_id, role_name):
        if not assignee_id:
            return
            
        task = Task(
            title=f"Nuovo Cliente: {target.nome_cognome}",
            description=f"Ti è stato assegnato il cliente {target.nome_cognome} come {role_name}. Mandagli il messaggio di benvenuto e leggi i suoi check!",
            category=TaskCategoryEnum.onboarding,
            status=TaskStatusEnum.todo,
            priority=TaskPriorityEnum.high,
            client_id=target.cliente_id,
            assignee_id=assignee_id,
            created_at=datetime.utcnow()
        )
        session.add(task)

    # Campi da monitorare
    prof_fields = {
        'nutrizionista_id': 'Nutrizionista',
        'coach_id': 'Coach',
        'psicologa_id': 'Psicologo/a',
        'health_manager_id': 'Health Manager'
    }

    state = inspect(target)
    for field, role in prof_fields.items():
        hist = state.attrs.get(field).history
        if hist.has_changes():
            # Nuovo valore assegnato (added[0])
            if hist.added and hist.added[0]:
                create_onboard_task(hist.added[0], role)


# --------------------------------------------------------------------------- #
#  2. CHECK RICEVUTO
# --------------------------------------------------------------------------- #
@event.listens_for(ClientCheckResponse, 'after_insert')
def trigger_check_task(mapper, connection, target):
    """
    Genera un task quando un cliente invia un check.
    """
    session = db.session
    if not session:
        return

    # Recupera il cliente e l'assegnazione
    # target.assignment -> CheckAssignment (link to Cliente)
    # Attenzione: related objects potrebbero non essere caricati in after_insert se non in session.
    # Facciamo query se necessario.
    
    # Per sicurezza, usiamo i pulsanti id
    # target.assignment_id
    
    # Nota: Task deve essere assegnato a chi ha assegnato il check (assigned_by_id in CheckAssignment)
    # o al professionista corrente del cliente.
    
    # Carichiamo assignment
    from corposostenibile.models import ClientCheckAssignment
    assignment = session.query(ClientCheckAssignment).get(target.assignment_id)
    
    if assignment and assignment.cliente:
        task = Task(
            title=f"Check Ricevuto: {assignment.cliente.nome_cognome}",
            description=f"Il cliente {assignment.cliente.nome_cognome} ha compilato il check. Leggilo!",
            category=TaskCategoryEnum.check,
            status=TaskStatusEnum.todo,
            priority=TaskPriorityEnum.high,
            client_id=assignment.cliente_id,
            assignee_id=assignment.assigned_by_id, # Chi ha assegnato il check
            created_at=datetime.utcnow(),
            payload={'check_response_id': target.id}
        )
        session.add(task)


# --------------------------------------------------------------------------- #
#  3. FORMAZIONE (Training)
# --------------------------------------------------------------------------- #
@event.listens_for(Review, 'after_insert')
def trigger_training_task(mapper, connection, target):
    """
    Genera un task quando viene assegnata una Review (Training).
    """
    session = db.session
    if not session:
        return
    
    # Consideriamo Training tutte le review o solo specifici tipi?
    # Per ora tutte, come da richiesta generica "Formazione".
    # target.reviewee_id è il destinatario
    
    task = Task(
        title=f"Nuova Formazione Assegnata",
        description=f"Hai ricevuto una nuova formazione/review: '{target.title}'. Leggila!",
        category=TaskCategoryEnum.formazione,
        status=TaskStatusEnum.todo,
        priority=TaskPriorityEnum.medium,
        assignee_id=target.reviewee_id,
        created_at=datetime.utcnow(),
        payload={'review_id': target.id}
    )
    session.add(task)


