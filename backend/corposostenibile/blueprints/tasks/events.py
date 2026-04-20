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
    WeeklyCheckResponse, WeeklyCheck,
    DCACheckResponse, DCACheck,
    MinorCheckResponse, MinorCheck,
    Review,
    ReviewRequest,
    Task,
    TaskCategoryEnum,
    TaskStatusEnum,
    TaskPriorityEnum,
    User,
    UserSpecialtyEnum,
)
from corposostenibile.blueprints.push_notifications.service import send_task_assigned_push
from corposostenibile.blueprints.tasks.email_service import send_onboarding_task_email

# --------------------------------------------------------------------------- #
#  Whitelist destinatari task
# --------------------------------------------------------------------------- #
# Solo nutrizionisti, coach e psicologi possono ricevere task.
# Esclusi: health manager, consulenti alimentari, medici, admin/CCO e
# qualsiasi utente senza specialty assegnata.
_ELIGIBLE_TASK_SPECIALTIES = frozenset({
    UserSpecialtyEnum.nutrizione,
    UserSpecialtyEnum.nutrizionista,
    UserSpecialtyEnum.coach,
    UserSpecialtyEnum.psicologia,
    UserSpecialtyEnum.psicologo,
})


def _is_eligible_task_recipient(user) -> bool:
    """True se l'utente ha una specialty ammessa a ricevere task."""
    if user is None:
        return False
    return getattr(user, "specialty", None) in _ELIGIBLE_TASK_SPECIALTIES


@event.listens_for(Session, "before_flush")
def drop_tasks_for_ineligible_assignees(session, flush_context, instances):
    """Safety net: scarta i Task diretti a utenti non ammessi.

    Rimuove dalla session i Task pending con assignee_id appartenente a un
    utente che non e' nutrizionista, coach o psicologa. Copre anche i path
    di creazione task che non filtrano esplicitamente (check legacy,
    formazione, creazione manuale via API, future estensioni).
    """
    pending_tasks = [obj for obj in session.new if isinstance(obj, Task)]
    if not pending_tasks:
        return
    with session.no_autoflush:
        for task in pending_tasks:
            if not task.assignee_id:
                continue
            assignee = session.get(User, task.assignee_id)
            if _is_eligible_task_recipient(assignee):
                continue
            specialty = getattr(assignee, "specialty", None) if assignee else None
            logger.info(
                "TASK SKIPPED: assignee_id=%s specialty=%s not eligible (title=%r)",
                task.assignee_id,
                specialty,
                task.title,
            )
            session.expunge(task)


# --------------------------------------------------------------------------- #
#  1. ONBOARDING (Assegnazione Cliente - M2M Lists)
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

# Registra i listener per le collezioni M2M (solo specialty ammesse a ricevere task)
for attr in ['nutrizionisti_multipli', 'coaches_multipli', 'psicologi_multipli']:
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


def _get_cliente_professional_ids(cliente) -> set[int]:
    """Restituisce gli ID dei professionisti del cliente ammessi ai task.

    Include solo nutrizionisti, coach e psicologi (sia M2M sia single-FK legacy).
    Esclude health manager e consulenti alimentari: questi non devono ricevere task.

    Priorita' M2M: le relazioni many-to-many sono la fonte autoritativa;
    i campi singoli vengono usati come fallback solo se nessuna M2M e' popolata.
    """
    prof_ids = set()

    # Fonte autoritativa: relazioni M2M (senza consulenti_multipli)
    m2m_found = False
    for rel in ('nutrizionisti_multipli', 'coaches_multipli', 'psicologi_multipli'):
        for u in (getattr(cliente, rel, None) or []):
            prof_ids.add(u.id)
            m2m_found = True

    # Fallback legacy: campi singoli solo se nessuna M2M e' impostata
    # (senza consulente_alimentare_id, senza health_manager_id)
    if not m2m_found:
        for attr in ('nutrizionista_id', 'coach_id', 'psicologa_id'):
            uid = getattr(cliente, attr, None)
            if uid:
                prof_ids.add(uid)

    return prof_ids


def _create_check_tasks_for_professionals(session, cliente, check_type_label, response_type, response_id):
    """Crea un task per ogni professionista assegnato al cliente."""
    prof_ids = _get_cliente_professional_ids(cliente)
    if not prof_ids:
        logger.warning(f"No professionals found for cliente {cliente.cliente_id}, skipping task creation")
        return
    for pid in prof_ids:
        task = Task(
            title=f"Check {check_type_label} Ricevuto: {cliente.nome_cognome}",
            description=f"Il cliente {cliente.nome_cognome} ha compilato il check {check_type_label.lower()}. Leggilo!",
            category=TaskCategoryEnum.check,
            status=TaskStatusEnum.todo,
            priority=TaskPriorityEnum.high,
            client_id=cliente.cliente_id,
            assignee_id=pid,
            created_at=datetime.utcnow(),
            payload={'response_type': response_type, 'response_id': response_id},
        )
        session.add(task)
    logger.info(f"TASK CREATED: {check_type_label} check tasks for {len(prof_ids)} professionals (cliente {cliente.cliente_id})")


@event.listens_for(WeeklyCheckResponse, 'after_insert')
def trigger_weekly_check_task(mapper, connection, target):
    """Genera task per ogni professionista quando un cliente compila il check settimanale."""
    logger.info(f"EVENT: trigger_weekly_check_task for response {target.id}")
    session = db.session
    if not session:
        return
    check = session.get(WeeklyCheck, target.weekly_check_id)
    if check and check.cliente:
        _create_check_tasks_for_professionals(session, check.cliente, 'Settimanale', 'weekly', target.id)


@event.listens_for(DCACheckResponse, 'after_insert')
def trigger_dca_check_task(mapper, connection, target):
    """Genera task per ogni professionista quando un cliente compila il check DCA."""
    logger.info(f"EVENT: trigger_dca_check_task for response {target.id}")
    session = db.session
    if not session:
        return
    check = session.get(DCACheck, target.dca_check_id)
    if check and check.cliente:
        _create_check_tasks_for_professionals(session, check.cliente, 'DCA', 'dca', target.id)


@event.listens_for(MinorCheckResponse, 'after_insert')
def trigger_minor_check_task(mapper, connection, target):
    """Genera task per ogni professionista quando un cliente compila il check minore."""
    logger.info(f"EVENT: trigger_minor_check_task for response {target.id}")
    session = db.session
    if not session:
        return
    check = session.get(MinorCheck, target.minor_check_id)
    if check and check.cliente:
        _create_check_tasks_for_professionals(session, check.cliente, 'Minore', 'minor', target.id)


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


@event.listens_for(ReviewRequest, 'after_insert')
def trigger_training_request_task(mapper, connection, target):
    """
    Genera un task quando un professionista invia una richiesta di training.
    Task assegnato al destinatario della richiesta.
    """
    logger.info(f"EVENT: trigger_training_request_task for review_request {target.id}")
    session = db.session
    if not session:
        return

    priority_map = {
        'low': TaskPriorityEnum.low,
        'normal': TaskPriorityEnum.medium,
        'high': TaskPriorityEnum.high,
        'urgent': TaskPriorityEnum.urgent,
    }
    task_priority = priority_map.get(str(getattr(target, "priority", "normal") or "normal").lower(), TaskPriorityEnum.medium)

    requester_name = None
    try:
        requester = getattr(target, "requester", None)
        if requester is None and getattr(target, "requester_id", None):
            # In after_insert la relationship puo' non essere caricata: fallback esplicito.
            from corposostenibile.models import User
            requester = session.get(User, target.requester_id) or User.query.get(target.requester_id)
        requester_name = getattr(requester, "full_name", None)
        if not requester_name and requester is not None:
            requester_name = f"{getattr(requester, 'first_name', '')} {getattr(requester, 'last_name', '')}".strip()
    except Exception:
        requester_name = None
    if not requester_name:
        requester_name = f"Utente #{target.requester_id}"

    task = Task(
        title=f"Richiesta training: {target.subject}",
        description=(
            f"{requester_name} ha inviato una richiesta di training"
            + (f": {target.description}" if getattr(target, "description", None) else ".")
        ),
        category=TaskCategoryEnum.formazione,
        status=TaskStatusEnum.todo,
        priority=task_priority,
        assignee_id=target.requested_to_id,
        created_at=datetime.utcnow(),
        payload={
            'review_request_id': target.id,
            'requester_id': target.requester_id,
            'requested_to_id': target.requested_to_id,
            'priority': target.priority,
        }
    )
    session.add(task)
    logger.info(
        "TASK CREATED: Training request task request_id=%s assignee=%s priority=%s",
        target.id,
        target.requested_to_id,
        task_priority.value if hasattr(task_priority, "value") else str(task_priority),
    )


@event.listens_for(Session, "after_flush")
def collect_new_tasks_for_push(session, flush_context):
    pending = session.info.setdefault("pending_task_push", [])
    for obj in session.new:
        if isinstance(obj, Task) and obj.assignee_id:
            category_value = (
                obj.category.value if hasattr(obj.category, "value") else obj.category
            )
            pending.append(
                {
                    "task_id": obj.id,
                    "assignee_id": obj.assignee_id,
                    "title": obj.title,
                    "category": category_value,
                    "client_id": obj.client_id,
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

        # Email addizionale solo per task di onboarding (assegnazione professionista a cliente)
        if item.get("category") == "onboarding":
            try:
                send_onboarding_task_email(
                    task_id=item["task_id"],
                    assignee_id=item["assignee_id"],
                    client_id=item.get("client_id"),
                )
            except Exception as exc:  # pragma: no cover
                logger.warning(
                    "EMAIL ONBOARDING FAILED task_id=%s assignee=%s err=%s",
                    item.get("task_id"),
                    item.get("assignee_id"),
                    exc,
                )


@event.listens_for(Session, "after_rollback")
def clear_pending_task_push_on_rollback(session):
    session.info.pop("pending_task_push", None)
