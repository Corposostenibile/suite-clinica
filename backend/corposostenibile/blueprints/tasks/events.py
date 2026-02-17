from sqlalchemy import event, inspect, and_
from sqlalchemy.orm import Session
from sqlalchemy.orm import attributes
from flask_login import user_logged_in
from flask import current_app
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

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
from corposostenibile.blueprints.push_notifications.service import send_task_assigned_push

# --------------------------------------------------------------------------- #
#  1. ONBOARDING (Assegnazione Cliente)
# --------------------------------------------------------------------------- #
@event.listens_for(Cliente, 'after_update')
def trigger_onboarding_task(mapper, connection, target):
    """
    Genera un task di onboarding quando viene assegnato un professionista.
    """
    # logger.info(f"EVENT: trigger_onboarding_task for client {target.cliente_id} - {target.nome_cognome}")
    # Verifica cambiamenti nei campi professionista
    # create_task_session = db.session.object_session(target) # after_update keeps session?
    # Usiamo Connection per insert diretti o Session? 
    # after_update passa connection. Se vogliamo usare ORM, meglio Session.
    # Ma attenzione a creare oggetti durante il flush (potrebbe dare warning).
    # listeners.py usava before_flush per questo motivo.
    # Proviamo con Session.
    
    session = db.session
    if not session:
        logger.warning("EVENT: trigger_onboarding_task - NO SESSION FOUND")
        return
    # logger.info("EVENT: trigger_onboarding_task - Session OK")

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
        logger.info(f"TASK CREATED: Onboarding task for assignee {assignee_id} (role: {role_name})")

    # Campi da monitorare (SOLO CAMPI SINGOLI/SCALAR)
    # health_manager_id è ancora un campo singolo
    prof_fields = {
        'health_manager_id': 'Health Manager'
    }

    state = inspect(target)
    # logger.info(f"INSPECTING STATE for {target} (Scalar Fields)")
    
    for field, role in prof_fields.items():
        hist = state.attrs.get(field).history
        # logger.info(f"CHECK SCALAR FIELD {field}: has_changes={hist.has_changes()}")
        
        if hist.has_changes():
            # Nuovo valore assegnato (added[0])
            if hist.added and hist.added[0]:
                logger.info(f"MATCH SCALAR! Creating task for {role} (id: {hist.added[0]})")
                create_onboard_task(hist.added[0], role)


# --------------------------------------------------------------------------- #
#  1b. ONBOARDING (Assegnazione Cliente - M2M Lists)
# --------------------------------------------------------------------------- #
def trigger_professional_assignment(target, value, initiator):
    """
    Genera un task quando viene aggiunto un professionista a una lista M2M.
    Triggered by: append event on collections
    """
    if not value:
        return
        
    session = db.session
    if not session:
        logger.warning("EVENT: trigger_professional_assignment - NO SESSION FOUND")
        return

    # Determina il ruolo in base al nome dell'attributo che ha scatenato l'evento
    # initiator.key è il nome dell'attributo (es. 'nutrizionisti_multipli')
    role_map = {
        'nutrizionisti_multipli': 'Nutrizionista',
        'coaches_multipli': 'Coach',
        'psicologi_multipli': 'Psicologo/a',
        'consulenti_multipli': 'Consulente Alimentare'
    }
    
    attr_name = initiator.key
    role_name = role_map.get(attr_name, 'Professionista')
    
    logger.info(f"EVENT: M2M Append - {attr_name} -> Assigning to {value.id} as {role_name}")

    try:
        task = Task(
            title=f"Nuovo Cliente: {target.nome_cognome}",
            description=f"Ti è stato assegnato il cliente {target.nome_cognome} come {role_name}. Mandagli il messaggio di benvenuto e leggi i suoi check!",
            category=TaskCategoryEnum.onboarding,
            status=TaskStatusEnum.todo,
            priority=TaskPriorityEnum.high,
            client_id=target.cliente_id,
            assignee_id=value.id,
            created_at=datetime.utcnow()
        )
        session.add(task)
        # Flush per garantire che l'ID del task sia generato? Non necessario per l'insert, 
        # ma l'evento è sincrono.
        logger.info(f"TASK CREATED (M2M): Onboarding task for assignee {value.id}")
    except Exception as e:
        logger.error(f"ERROR creating task in M2M listener: {e}")

# Registra i listener per le collezioni M2M
for attr in ['nutrizionisti_multipli', 'coaches_multipli', 'psicologi_multipli', 'consulenti_multipli']:
    event.listen(getattr(Cliente, attr), 'append', trigger_professional_assignment)


# --------------------------------------------------------------------------- #
#  2. CHECK RICEVUTO
# --------------------------------------------------------------------------- #
@event.listens_for(ClientCheckResponse, 'after_insert')
def trigger_check_task(mapper, connection, target):
    """
    Genera un task quando un cliente invia un check.
    """
    logger.info(f"EVENT: trigger_check_task for response {target.id}")
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
        logger.info(f"TASK CREATED: Check task for assignee {assignment.assigned_by_id}")


# --------------------------------------------------------------------------- #
#  3. FORMAZIONE (Training)
# --------------------------------------------------------------------------- #
@event.listens_for(Review, 'after_insert')
def trigger_training_task(mapper, connection, target):
    """
    Genera un task quando viene assegnata una Review (Training).
    """
    logger.info(f"EVENT: trigger_training_task for review {target.id}")
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
    logger.info(f"TASK CREATED: Training task for assignee {target.reviewee_id}")


@event.listens_for(Session, "after_flush")
def collect_new_tasks_for_push(session, flush_context):
    pending = session.info.setdefault("pending_task_push", [])
    for obj in session.new:
        if isinstance(obj, Task) and obj.assignee_id:
            pending.append(
                {
                    "task_id": obj.id,
                    "assignee_id": obj.assignee_id,
                    "title": obj.title,
                }
            )


@event.listens_for(Session, "after_commit")
def dispatch_task_push_after_commit(session):
    pending = session.info.pop("pending_task_push", [])
    for item in pending:
        try:
            send_task_assigned_push(
                task_id=item["task_id"],
                assignee_id=item["assignee_id"],
                task_title=item["title"],
            )
        except Exception as exc:  # pragma: no cover
            logger.warning(
                "PUSH TASK FAILED task_id=%s assignee=%s err=%s",
                item.get("task_id"),
                item.get("assignee_id"),
                exc,
            )


@event.listens_for(Session, "after_rollback")
def clear_pending_task_push_on_rollback(session):
    session.info.pop("pending_task_push", None)
