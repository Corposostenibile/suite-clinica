from flask import Blueprint, jsonify, request, abort, current_app
from flask_login import login_required, current_user
from datetime import datetime, date
from sqlalchemy import desc, func, or_

from corposostenibile.models import Task, TaskStatusEnum, TaskCategoryEnum, TaskPriorityEnum, User, UserRoleEnum, db

bp = Blueprint('tasks', __name__, url_prefix='/api/tasks')


def _is_done_status(value) -> bool:
    if value == TaskStatusEnum.done:
        return True
    raw = value.value if hasattr(value, "value") else value
    return raw == "done"


def _normalize_check_task_payload(payload: dict | None):
    """Estrae il riferimento check dal payload task in formati legacy/nuovi."""
    if not isinstance(payload, dict):
        return None, None

    response_type = payload.get("response_type") or payload.get("check_response_type")
    response_id = payload.get("response_id") or payload.get("check_response_id")

    # Compatibilità con payload tipo {"check_type":"weekly","check_id":123}
    if not response_type and payload.get("check_type") in {"weekly", "dca"}:
        response_type = f"{payload['check_type']}_check"
    if not response_id:
        response_id = payload.get("check_id")

    try:
        response_id = int(response_id) if response_id is not None else None
    except (TypeError, ValueError):
        response_id = None

    if response_type not in {"weekly_check", "dca_check"}:
        return None, None
    if not response_id:
        return response_type, None
    return response_type, response_id


def _mark_check_as_read_from_task_if_needed(task: Task) -> None:
    """Se il task è un task check con payload compatibile, marca il check come letto per l'assignee."""
    if task.category != TaskCategoryEnum.check:
        return

    response_type, response_id = _normalize_check_task_payload(task.payload or {})
    if not response_type or not response_id:
        current_app.logger.info(
            "[TASKS] Task check %s completato senza payload compatibile per conferma lettura",
            task.id,
        )
        return

    from corposostenibile.models import (
        ClientCheckReadConfirmation,
        WeeklyCheckResponse,
        DCACheckResponse,
    )

    if response_type == "weekly_check":
        response = WeeklyCheckResponse.query.get(response_id)
        cliente = response.assignment.cliente if response and response.assignment else None
    else:
        response = DCACheckResponse.query.get(response_id)
        cliente = response.assignment.cliente if response and response.assignment else None

    if not response or not cliente:
        current_app.logger.warning(
            "[TASKS] Task check %s: response %s:%s non trovata o senza cliente",
            task.id, response_type, response_id
        )
        return

    # Il task completato vale come "letto" solo per il professionista assegnatario del task.
    assignee = task.assignee_id
    if not assignee:
        return

    # Verifica accesso al cliente per sicurezza (task legacy/storici incoerenti non devono scrivere letture).
    from corposostenibile.blueprints.client_checks.routes import _can_access_cliente_checks
    if assignee != current_user.id or not _can_access_cliente_checks(cliente.cliente_id):
        current_app.logger.warning(
            "[TASKS] Task check %s: skip conferma lettura per assignee=%s current_user=%s cliente=%s",
            task.id, assignee, getattr(current_user, "id", None), getattr(cliente, "cliente_id", None)
        )
        return

    existing = ClientCheckReadConfirmation.query.filter_by(
        response_type=response_type,
        response_id=response_id,
        user_id=assignee,
    ).first()
    if existing:
        return

    db.session.add(ClientCheckReadConfirmation(
        response_type=response_type,
        response_id=response_id,
        user_id=assignee,
        read_at=datetime.utcnow(),
    ))
    current_app.logger.info(
        "[TASKS] Check marcato come letto via completamento task: task=%s %s:%s user=%s",
        task.id, response_type, response_id, assignee
    )


def _is_cco_user(user) -> bool:
    specialty = getattr(user, 'specialty', None)
    if hasattr(specialty, 'value'):
        specialty = specialty.value
    return str(specialty).strip().lower() == 'cco' if specialty else False


def _can_view_all_tasks(user) -> bool:
    user_role = getattr(user, 'role', None)
    return bool(user.is_admin or user_role == UserRoleEnum.admin or _is_cco_user(user))


@bp.route('/', methods=['GET'])
@login_required
def list_tasks():
    """Ritorna la lista dei task, filtrata in base al ruolo."""
    query = Task.query
    
    user_role = getattr(current_user, 'role', None)
    
    # Filtro base per ruolo
    if _can_view_all_tasks(current_user):
        # Admin / CCO: vede tutto
        pass
    elif user_role == UserRoleEnum.team_leader:
        # Team Leader: vede task propri e dei membri del team
        team_member_ids = set()
        for team in (current_user.teams_led or []):
            for member in (team.members or []):
                team_member_ids.add(member.id)
        team_member_ids.add(current_user.id)
        
        if team_member_ids:
            query = query.filter(Task.assignee_id.in_(list(team_member_ids)))
        else:
            query = query.filter(Task.assignee_id == current_user.id)
    else:
        # Professionista o altro: solo i propri task
        query = query.filter(Task.assignee_id == current_user.id)

    # Filtri
    category = request.args.get('category')
    if category and category != 'all':
        query = query.filter(Task.category == category)

    status = request.args.get('status')
    if status:
        query = query.filter(Task.status == status)
    
    # Filtro completed: true mostra solo completati, false solo non completati
    completed = request.args.get('completed')
    if completed == 'true':
        query = query.filter(Task.status == TaskStatusEnum.done)
    elif completed == 'false':
        query = query.filter(Task.status != TaskStatusEnum.done)

    assignee_id = request.args.get('assignee_id', type=int)
    if assignee_id:
        query = query.filter(Task.assignee_id == assignee_id)

    assignee_role = request.args.get('assignee_role', '').strip()
    if assignee_role:
        query = query.filter(Task.assignee.has(User.role == assignee_role))

    assignee_specialty = request.args.get('assignee_specialty', '').strip()
    if assignee_specialty:
        query = query.filter(Task.assignee.has(User.specialty == assignee_specialty))

    team_id = request.args.get('team_id', type=int)
    if team_id:
        query = query.filter(Task.assignee.has(User.teams.any(id=team_id)))

    search_query = request.args.get('q', '').strip()
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            or_(
                Task.title.ilike(search_term),
                Task.description.ilike(search_term)
            )
        )

    # Ordinamento
    query = query.order_by(
        # Prima per priorità (se mappata su int) o custom logic
        # Qui usiamo status done in fondo, poi data, poi priority
        Task.status == TaskStatusEnum.done, # False (0) prima di True (1) se ordinamento ascendente... aspetta.
        # Vogliamo i non completati prima. 
        # (Task.status == 'done') restituisce true/false. Ordine asc: False (0) -> True (1). OK.
        desc(Task.created_at)
    )

    tasks = query.limit(100).all()

    return jsonify([_serialize_task(t) for t in tasks])

@bp.route('/', methods=['POST'])
@login_required
def create_task():
    """Crea un task manuale."""
    data = request.json
    
    # Validazione base
    if not data.get('title'):
        abort(400, "Title is required")

    task = Task(
        title=data['title'],
        description=data.get('description', ''),
        category=data.get('category', TaskCategoryEnum.generico),
        priority=data.get('priority', TaskPriorityEnum.medium),
        status=TaskStatusEnum.todo,
        assignee_id=data.get('assignee_id', current_user.id), # Default a se stessi se non specificato
        client_id=data.get('client_id'),
        due_date=datetime.strptime(data['due_date'], '%Y-%m-%d').date() if data.get('due_date') else None,
        department_id=getattr(current_user, 'department_id', None) # Optional, contestuale
    )

    db.session.add(task)
    db.session.commit()

    return jsonify(_serialize_task(task)), 201

@bp.route('/<int:task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    """Aggiorna un task (stato o completamento)."""
    task = Task.query.get_or_404(task_id)

    # Check permessi: assignee o creatore (se ci fosse created_by) o admin
    if task.assignee_id != current_user.id and not current_user.is_admin:
        abort(403)

    data = request.json

    previous_status = task.status

    if 'status' in data:
        task.status = data['status']
    
    if 'completed' in data:
        # Toggle rapido
        task.status = TaskStatusEnum.done if data['completed'] else TaskStatusEnum.todo

    if 'archive' in data and data['archive']:
        task.status = TaskStatusEnum.archived

    became_done = _is_done_status(task.status) and not _is_done_status(previous_status)
    if became_done:
        try:
            _mark_check_as_read_from_task_if_needed(task)
        except Exception:
            current_app.logger.error(
                "[TASKS] Errore nel sync task->check letto per task_id=%s",
                task.id,
                exc_info=True,
            )

    db.session.commit()
    return jsonify(_serialize_task(task))

@bp.route('/stats', methods=['GET'])
@login_required
def get_stats():
    """Ritorna conteggi per la dashboard."""
    query = db.session.query(Task.category, func.count(Task.id))
    
    user_role = getattr(current_user, 'role', None) 
    
    # Appliciamo la stessa logica di filtraggio di list_tasks
    if _can_view_all_tasks(current_user):
        pass
    elif user_role == UserRoleEnum.team_leader:
        team_member_ids = set()
        for team in (current_user.teams_led or []):
            for member in (team.members or []):
                team_member_ids.add(member.id)
        team_member_ids.add(current_user.id)
        
        if team_member_ids:
            query = query.filter(Task.assignee_id.in_(list(team_member_ids)))
        else:
            query = query.filter(Task.assignee_id == current_user.id)
    else:
        query = query.filter(Task.assignee_id == current_user.id)
    
    # Filtri standard
    query = query.filter(Task.status != TaskStatusEnum.done).\
                  filter(Task.status != TaskStatusEnum.archived).\
                  group_by(Task.category)

    categories = query.all()
    
    cat_counts = {c.value: 0 for c in TaskCategoryEnum}
    
    # Fill con i dati reali
    total_open = 0
    for cat, count in categories:
        val = cat.value if hasattr(cat, 'value') else cat
        cat_counts[val] = count
        total_open += count

    return jsonify({
        'by_category': cat_counts,
        'total_open': total_open
    })

def _serialize_task(task):
    return {
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'category': task.category.value if hasattr(task.category, 'value') else task.category,
        'status': task.status.value if hasattr(task.status, 'value') else task.status,
        'priority': task.priority.value if hasattr(task.priority, 'value') else task.priority,
        'due_date': task.due_date.isoformat() if task.due_date else None,
        'created_at': task.created_at.isoformat() if task.created_at else None,
        'assignee_id': task.assignee_id,
        'assignee_name': task.assignee.full_name if task.assignee else None,
        'assignee_role': (task.assignee.role.value if hasattr(task.assignee.role, 'value') else task.assignee.role) if task.assignee else None,
        'assignee_specialty': (task.assignee.specialty.value if getattr(task.assignee, 'specialty', None) and hasattr(task.assignee.specialty, 'value') else str(task.assignee.specialty) if getattr(task.assignee, 'specialty', None) else None),
        'client_name': task.client.nome_cognome if task.client else None,
        'client_id': task.client_id,
        'completed': task.status == TaskStatusEnum.done,
        'payload': task.payload or {}
    }
