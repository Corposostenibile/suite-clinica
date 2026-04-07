from flask import Blueprint, jsonify, request, abort, current_app
from flask_login import login_required, current_user
from datetime import datetime, date
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import joinedload

from corposostenibile.models import Task, TaskStatusEnum, TaskCategoryEnum, TaskPriorityEnum, User, UserRoleEnum, Team, db, team_members

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
    if not response_type and payload.get("check_type") in {"weekly", "dca", "minor"}:
        response_type = f"{payload['check_type']}_check"
    if not response_id:
        response_id = payload.get("check_id")

    # Normalizza short form ("weekly" → "weekly_check")
    if response_type in ("weekly", "dca", "minor"):
        response_type = f"{response_type}_check"

    try:
        response_id = int(response_id) if response_id is not None else None
    except (TypeError, ValueError):
        response_id = None

    if response_type not in {"weekly_check", "dca_check", "minor_check"}:
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
        MinorCheckResponse,
    )

    if response_type == "weekly_check":
        response = WeeklyCheckResponse.query.get(response_id)
        cliente = response.assignment.cliente if response and response.assignment else None
    elif response_type == "dca_check":
        response = DCACheckResponse.query.get(response_id)
        cliente = response.assignment.cliente if response and response.assignment else None
    elif response_type == "minor_check":
        response = MinorCheckResponse.query.get(response_id)
        cliente = response.assignment.cliente if response and response.assignment else None
    else:
        return

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


def _apply_visibility_scope(query, user, mine_only: bool = False):
    user_role = getattr(user, 'role', None)

    if mine_only:
        return query.filter(Task.assignee_id == user.id)
    if _can_view_all_tasks(user):
        return query
    if user_role == UserRoleEnum.team_leader:
        team_member_ids = set()
        for team in (user.teams_led or []):
            for member in (team.members or []):
                team_member_ids.add(member.id)
        team_member_ids.add(user.id)
        if team_member_ids:
            return query.filter(Task.assignee_id.in_(list(team_member_ids)))
    return query.filter(Task.assignee_id == user.id)


def _apply_admin_filters(query):
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

    return query


def _build_stats(scope_query):
    # Singola query GROUP BY (status, category) invece di due query separate
    rows = (
        scope_query
        .with_entities(Task.status, Task.category, func.count(Task.id))
        .group_by(Task.status, Task.category)
        .all()
    )

    cat_counts = {c.value: 0 for c in TaskCategoryEnum}
    total_open = 0
    completed_total = 0
    for status, cat, count in rows:
        status_val = status.value if hasattr(status, 'value') else status
        if status_val == TaskStatusEnum.done.value:
            completed_total += count
        elif status_val != TaskStatusEnum.archived.value:
            cat_val = cat.value if hasattr(cat, 'value') else cat
            cat_counts[cat_val] = cat_counts.get(cat_val, 0) + count
            total_open += count

    return {
        'by_category': cat_counts,
        'total_open': total_open,
        'total_completed': completed_total,
    }


def _build_filter_options():
    if not (_can_view_all_tasks(current_user) or getattr(current_user, 'role', None) == UserRoleEnum.team_leader):
        return None

    member_query = User.query.filter(User.role.isnot(None), User.is_active == True)
    if _can_view_all_tasks(current_user):
        pass
    elif getattr(current_user, 'role', None) == UserRoleEnum.team_leader:
        visible_ids = {current_user.id}
        for team in (current_user.teams_led or []):
            for member in (team.members or []):
                visible_ids.add(member.id)
        member_query = member_query.filter(User.id.in_(list(visible_ids)))
    else:
        member_query = member_query.filter(User.id == current_user.id)

    members = (
        member_query
        .with_entities(
            User.id,
            User.first_name,
            User.last_name,
            User.email,
            User.role,
            User.specialty,
        )
        .order_by(User.first_name, User.last_name)
        .all()
    )
    member_ids = [member.id for member in members]

    team_map = {member_id: [] for member_id in member_ids}
    if member_ids:
        memberships = (
            db.session.query(team_members.c.user_id, Team.id, Team.name)
            .join(Team, Team.id == team_members.c.team_id)
            .filter(team_members.c.user_id.in_(member_ids), Team.is_active == True)
            .all()
        )
        for user_id, team_id, team_name in memberships:
            team_map[user_id].append({'id': team_id, 'name': team_name})

    roles = sorted({
        m.role.value if hasattr(m.role, 'value') else m.role
        for m in members
        if m.role
    })
    specialties = sorted({
        m.specialty.value if hasattr(m.specialty, 'value') else m.specialty
        for m in members
        if m.specialty
    })

    teams = []
    if _can_view_all_tasks(current_user):
        team_rows = (
            Team.query
            .filter_by(is_active=True)
            .order_by(Team.name)
            .all()
        )
        teams = [{'id': team.id, 'name': team.name} for team in team_rows]

    assignees = [
        {
            'id': member.id,
            'full_name': ' '.join(part for part in [member.first_name, member.last_name] if part).strip() or member.email,
            'email': member.email,
            'role': member.role.value if hasattr(member.role, 'value') else member.role,
            'specialty': member.specialty.value if hasattr(member.specialty, 'value') else member.specialty,
            'teams': team_map.get(member.id, []),
        }
        for member in members
    ]

    return {
        'teams': teams,
        'assignees': assignees,
        'roles': roles,
        'specialties': specialties,
    }


@bp.route('/', methods=['GET'])
@login_required
def list_tasks():
    """Ritorna la lista dei task, filtrata in base al ruolo."""
    scope_query = _apply_visibility_scope(Task.query, current_user, mine_only=request.args.get('mine', '').lower() == 'true')
    page = max(request.args.get('page', 1, type=int) or 1, 1)
    requested_per_page = request.args.get('per_page', type=int)
    page_size = max(1, min(requested_per_page, 100)) if requested_per_page else 15
    legacy_limit = max(1, min(requested_per_page, 100)) if requested_per_page else 100
    use_paginated_response = request.args.get('paginate', '').lower() == 'true'
    include_summary = request.args.get('include_summary', '').lower() == 'true'
    include_filter_options = request.args.get('include_filter_options', '').lower() == 'true'

    scope_query = _apply_admin_filters(scope_query)
    query = scope_query.options(
        joinedload(Task.assignee),
        joinedload(Task.client),
    )

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

    if use_paginated_response:
        total = query.order_by(None).count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        total_pages = max(1, (total + page_size - 1) // page_size)
        payload = {
            'items': [_serialize_task(t) for t in items],
            'pagination': {
                'page': page,
                'per_page': page_size,
                'total': total,
                'pages': total_pages,
            }
        }
        if include_summary:
            payload['summary'] = _build_stats(scope_query)
        if include_filter_options:
            payload['filter_options'] = _build_filter_options()
        return jsonify(payload)

    # Compatibilità legacy: endpoint che si aspettano una lista semplice.
    tasks = query.limit(legacy_limit).all()

    return jsonify([_serialize_task(t) for t in tasks])

@bp.route('/', methods=['POST'])
@login_required
def create_task():
    """Crea un task manuale."""
    data = request.json
    
    # Validazione base
    if not data.get('title'):
        abort(400, "Title is required")

    requested_assignee_id = data.get('assignee_id', current_user.id)
    user_role = getattr(current_user, 'role', None)
    if _can_view_all_tasks(current_user):
        pass
    elif user_role == UserRoleEnum.team_leader:
        visible_ids = {current_user.id}
        for team in (current_user.teams_led or []):
            for member in (team.members or []):
                visible_ids.add(member.id)
        if int(requested_assignee_id) not in visible_ids:
            abort(403, "Non autorizzato ad assegnare task fuori dal tuo team")
    elif int(requested_assignee_id) != int(current_user.id):
        abort(403, "Puoi creare task solo per te stesso")

    task = Task(
        title=data['title'],
        description=data.get('description', ''),
        category=data.get('category', TaskCategoryEnum.generico),
        priority=data.get('priority', TaskPriorityEnum.medium),
        status=TaskStatusEnum.todo,
        assignee_id=requested_assignee_id, # Default a se stessi se non specificato
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
    scope_query = _apply_visibility_scope(Task.query, current_user)
    scope_query = _apply_admin_filters(scope_query)
    return jsonify(_build_stats(scope_query))


@bp.route('/filter-options', methods=['GET'])
@login_required
def get_filter_options():
    payload = _build_filter_options()
    if payload is None:
        return jsonify({'teams': [], 'assignees': [], 'roles': [], 'specialties': []})
    return jsonify(payload)

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
        'avatar_path': task.assignee.avatar_path if task.assignee else None,
        'avatar_url': task.assignee.avatar_url if task.assignee else None,
        'assignee_role': (task.assignee.role.value if hasattr(task.assignee.role, 'value') else task.assignee.role) if task.assignee else None,
        'assignee_specialty': (task.assignee.specialty.value if getattr(task.assignee, 'specialty', None) and hasattr(task.assignee.specialty, 'value') else str(task.assignee.specialty) if getattr(task.assignee, 'specialty', None) else None),
        'client_name': task.client.nome_cognome if task.client else None,
        'client_id': task.client_id,
        'completed': task.status == TaskStatusEnum.done,
        'payload': task.payload or {}
    }
