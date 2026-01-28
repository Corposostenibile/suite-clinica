from flask import Blueprint, jsonify, request, abort, current_app
from flask_login import login_required, current_user
from datetime import datetime, date
from sqlalchemy import desc, func

from corposostenibile.models import Task, TaskStatusEnum, TaskCategoryEnum, TaskPriorityEnum, User, UserRoleEnum, db

bp = Blueprint('tasks', __name__, url_prefix='/api/tasks')

@bp.route('/', methods=['GET'])
@login_required
def list_tasks():
    """Ritorna la lista dei task, filtrata in base al ruolo."""
    query = Task.query
    
    user_role = getattr(current_user, 'role', None)
    
    # Filtro base per ruolo
    if request.args.get('all_users') == 'true' and current_user.is_admin:
        # Admin con all_users=true: nessun filtro
        pass
    elif user_role == UserRoleEnum.admin or current_user.is_admin:
        # Admin: vede tutto
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
        department_id=current_user.department_id # Optional, contestuale
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

    if 'status' in data:
        task.status = data['status']
    
    if 'completed' in data:
        # Toggle rapido
        task.status = TaskStatusEnum.done if data['completed'] else TaskStatusEnum.todo

    if 'archive' in data and data['archive']:
        task.status = TaskStatusEnum.archived

    db.session.commit()
    return jsonify(_serialize_task(task))

@bp.route('/stats', methods=['GET'])
@login_required
def get_stats():
    """Ritorna conteggi per la dashboard."""
    base_query = Task.query.filter(Task.assignee_id == current_user.id)
    
    # Counts per category (solo non completati)
    categories = db.session.query(Task.category, func.count(Task.id)).\
        filter(Task.assignee_id == current_user.id).\
        filter(Task.status != TaskStatusEnum.done).\
        filter(Task.status != TaskStatusEnum.archived).\
        group_by(Task.category).all()
    
    cat_counts = {c.value: 0 for c in TaskCategoryEnum}
    
    # Fill con i dati reali
    total_open = 0
    for cat, count in categories:
        # cat è un Enum o stringa a seconda del driver DB, assumiamo enum o string
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
        'client_name': task.client.nome_cognome if task.client else None,
        'client_id': task.client_id,
        'completed': task.status == TaskStatusEnum.done,
        'payload': task.payload or {}
    }
