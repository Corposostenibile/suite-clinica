from flask import Blueprint, jsonify, request, abort, current_app
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import desc, asc, func, or_, case, extract
from collections import defaultdict

from corposostenibile.models import Task, TaskStatusEnum, TaskCategoryEnum, TaskPriorityEnum, User, UserRoleEnum, UserSpecialtyEnum, Team, db

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


@bp.route('/', methods=['GET'])
@login_required
def list_tasks():
    """Ritorna la lista dei task, filtrata in base al ruolo."""
    query = Task.query
    
    user_role = getattr(current_user, 'role', None)
    
    # Parametro mine=true → forza solo task dell'utente corrente (usato dalla sidebar)
    mine_only = request.args.get('mine', '').lower() == 'true'

    if mine_only:
        query = query.filter(Task.assignee_id == current_user.id)
    elif _can_view_all_tasks(current_user):
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

def _normalize_specialty_to_department(specialty_val):
    """Normalizza specialty utente (nutrizionista/psicologo/etc.) a dipartimento (nutrizione/coach/psicologia)."""
    mapping = {
        'nutrizione': 'nutrizione',
        'nutrizionista': 'nutrizione',
        'coach': 'coach',
        'psicologia': 'psicologia',
        'psicologo': 'psicologia',
    }
    return mapping.get(str(specialty_val).lower(), str(specialty_val).lower() if specialty_val else None)


@bp.route('/admin-dashboard-stats', methods=['GET'])
@login_required
def admin_dashboard_stats():
    """Statistiche task per la dashboard admin: task stale + ranking velocità professionisti."""
    if not _can_view_all_tasks(current_user):
        abort(403, "Accesso riservato ad admin/CCO")

    now = datetime.utcnow()
    three_days_ago = now - timedelta(days=3)

    # ── Pre-load ALL team memberships (user_id → list of teams) ──
    all_teams = Team.query.filter(Team.is_active == True).all()
    user_team_map = {}  # user_id → {team_name, team_type}
    for team in all_teams:
        t_type = team.team_type.value if hasattr(team.team_type, 'value') else str(team.team_type)
        for member in (team.members or []):
            user_team_map[member.id] = {'team_name': team.name, 'team_type': t_type}

    # ── 1. Task stale: non completate dopo 3+ giorni dalla creazione ──
    stale_query = (
        Task.query
        .filter(Task.status.notin_([TaskStatusEnum.done, TaskStatusEnum.archived]))
        .filter(Task.created_at <= three_days_ago)
        .order_by(asc(Task.created_at))
        .limit(100)
    )
    stale_tasks = stale_query.all()

    stale_list = []
    for t in stale_tasks:
        days_old = (now - t.created_at).days if t.created_at else 0
        team_info = user_team_map.get(t.assignee_id, {})
        # Se non è in un team, ricava il dipartimento dalla specialty dell'utente
        dept = team_info.get('team_type')
        if not dept and t.assignee:
            spec_val = t.assignee.specialty.value if t.assignee.specialty and hasattr(t.assignee.specialty, 'value') else str(t.assignee.specialty) if t.assignee.specialty else None
            dept = _normalize_specialty_to_department(spec_val)
        stale_list.append({
            **_serialize_task(t),
            'days_old': days_old,
            'team_name': team_info.get('team_name'),
            'team_type': dept,
        })

    # ── 2. Ranking velocità: tempo medio di completamento per professionista ──
    # Per task completati (done), updated_at ≈ completion time
    # Includiamo TUTTE le specialty cliniche (nutrizionista, nutrizione, coach, psicologo, psicologia)
    clinical_specialties = [
        UserSpecialtyEnum.nutrizione, UserSpecialtyEnum.nutrizionista,
        UserSpecialtyEnum.coach,
        UserSpecialtyEnum.psicologia, UserSpecialtyEnum.psicologo,
    ]
    completed_tasks = (
        Task.query
        .join(User, Task.assignee_id == User.id)
        .filter(Task.status == TaskStatusEnum.done)
        .filter(Task.created_at.isnot(None))
        .filter(Task.updated_at.isnot(None))
        .filter(User.is_active == True)
        .filter(User.specialty.in_(clinical_specialties))
        .with_entities(
            Task.assignee_id,
            User.first_name,
            User.last_name,
            User.specialty,
            User.avatar_path,
            Task.created_at,
            Task.updated_at,
        )
        .all()
    )

    # Aggreghiamo in Python per flessibilità
    prof_stats = defaultdict(lambda: {'total_hours': 0.0, 'count': 0, 'name': '', 'specialty': '', 'department': '', 'avatar_path': None})
    for row in completed_tasks:
        uid = row.assignee_id
        delta = row.updated_at - row.created_at
        hours = delta.total_seconds() / 3600.0
        entry = prof_stats[uid]
        entry['total_hours'] += hours
        entry['count'] += 1
        entry['name'] = f"{row.first_name} {row.last_name}"
        spec = row.specialty
        spec_val = spec.value if hasattr(spec, 'value') else str(spec) if spec else ''
        entry['specialty'] = spec_val
        entry['department'] = _normalize_specialty_to_department(spec_val)
        entry['avatar_path'] = row.avatar_path
        # Enrichisci con team info
        if uid in user_team_map:
            entry['team_name'] = user_team_map[uid]['team_name']

    # Calcola media e raggruppa per DIPARTIMENTO normalizzato (nutrizione/coach/psicologia)
    # Soglia minima: 1 task (così vediamo tutti)
    rankings = defaultdict(list)
    for uid, data in prof_stats.items():
        if data['count'] < 1:
            continue
        avg_hours = data['total_hours'] / data['count']
        entry = {
            'user_id': uid,
            'name': data['name'],
            'specialty': data['department'],  # normalizzato
            'avatar_path': data['avatar_path'],
            'avg_hours': round(avg_hours, 1),
            'tasks_completed': data['count'],
            'team_name': data.get('team_name'),
        }
        rankings[data['department']].append(entry)

    # Ordina per specialty: i più veloci prima
    result_rankings = {}
    for dept, members in rankings.items():
        if not dept:
            continue
        sorted_members = sorted(members, key=lambda x: x['avg_hours'])
        result_rankings[dept] = {
            'fastest': sorted_members[:5],
            'slowest': list(reversed(sorted_members[-5:])) if len(sorted_members) > 1 else [],
        }

    # ── 3. Ranking per team ──
    team_stats_agg = defaultdict(lambda: {'total_hours': 0.0, 'count': 0, 'name': '', 'team_type': ''})
    for uid, data in prof_stats.items():
        if data['count'] < 1:
            continue
        if uid in user_team_map:
            t_info = user_team_map[uid]
            t_key = t_info['team_name']  # use name as key (unique per type)
            entry = team_stats_agg[t_key]
            entry['total_hours'] += data['total_hours']
            entry['count'] += data['count']
            entry['name'] = t_info['team_name']
            entry['team_type'] = t_info['team_type']

    team_rankings = {}
    for t_key, data in team_stats_agg.items():
        if data['count'] == 0:
            continue
        avg_hours = data['total_hours'] / data['count']
        team_type = data['team_type']
        if team_type not in team_rankings:
            team_rankings[team_type] = []
        team_rankings[team_type].append({
            'team_name': data['name'],
            'avg_hours': round(avg_hours, 1),
            'tasks_completed': data['count'],
        })

    for team_type in team_rankings:
        team_rankings[team_type] = sorted(team_rankings[team_type], key=lambda x: x['avg_hours'])

    # ── 4. KPI riassuntivi ──
    total_open = Task.query.filter(
        Task.status.notin_([TaskStatusEnum.done, TaskStatusEnum.archived])
    ).count()
    total_stale = len(stale_list)
    completed_today = Task.query.filter(
        Task.status == TaskStatusEnum.done,
        func.date(Task.updated_at) == date.today()
    ).count()
    total_overdue = Task.query.filter(
        Task.status.notin_([TaskStatusEnum.done, TaskStatusEnum.archived]),
        Task.due_date < date.today()
    ).count()

    # ── 5. Lista team disponibili (per i filtri frontend) ──
    available_teams = []
    for team in all_teams:
        t_type = team.team_type.value if hasattr(team.team_type, 'value') else str(team.team_type)
        available_teams.append({'name': team.name, 'team_type': t_type})

    return jsonify({
        'kpi': {
            'total_open': total_open,
            'total_stale': total_stale,
            'completed_today': completed_today,
            'total_overdue': total_overdue,
        },
        'stale_tasks': stale_list,
        'rankings_by_specialty': result_rankings,
        'rankings_by_team': team_rankings,
        'available_teams': available_teams,
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
        'avatar_path': task.assignee.avatar_path if task.assignee else None,
        'avatar_url': task.assignee.avatar_url if task.assignee else None,
        'assignee_role': (task.assignee.role.value if hasattr(task.assignee.role, 'value') else task.assignee.role) if task.assignee else None,
        'assignee_specialty': (task.assignee.specialty.value if getattr(task.assignee, 'specialty', None) and hasattr(task.assignee.specialty, 'value') else str(task.assignee.specialty) if getattr(task.assignee, 'specialty', None) else None),
        'client_name': task.client.nome_cognome if task.client else None,
        'client_id': task.client_id,
        'completed': task.status == TaskStatusEnum.done,
        'payload': task.payload or {}
    }
