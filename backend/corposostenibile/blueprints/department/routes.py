"""
blueprints/department/routes.py
===============================

- Gestione CRUD dei reparti (Department)
- Kanban board HTML + API XHR per i Task di reparto
- API per ricerca utenti e clienti
- Integrazione con dashboard OKR dipartimentali
- Gestione documenti dipartimento (linee guida, SOP)
"""

from __future__ import annotations

import os
from datetime import datetime
from http import HTTPStatus
from typing import Any, Dict

from flask import (
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename

from corposostenibile.extensions import db
from corposostenibile.models import (
    Cliente,
    Department,
    DepartmentObjective,
    OKRStatusEnum,
    Task,
    TaskPriorityEnum,
    TaskStatusEnum,
    User,
)
from . import dept_bp                       # <─ usa l'istanza già creata in __init__.py
from .forms import DepartmentForm, TaskForm, CommentForm


# ╔════════════════════════════════════════════════════════════════════════╗
# ║ ACL helpers                                                           ║
# ╚════════════════════════════════════════════════════════════════════════╝
def _require_admin() -> None:
    """Consente l'accesso solo agli admin, altrimenti 403."""
    if not (current_user.is_authenticated and current_user.is_admin):
        abort(HTTPStatus.FORBIDDEN)


def _require_dept_write(dept: Department) -> None:
    """
    Permette la modifica dei task a:
      • admin
      • membri del reparto
    """
    if not current_user.is_authenticated:
        abort(HTTPStatus.UNAUTHORIZED)

    if current_user.is_admin or current_user.department_id == dept.id:
        return

    abort(HTTPStatus.FORBIDDEN)


def _can_view_dept(dept: Department) -> bool:
    """
    Verifica se l'utente può visualizzare il dipartimento.
    TUTTI gli utenti autenticati possono vedere TUTTI i dipartimenti.
    """
    return current_user.is_authenticated


def _can_manage_dept_okr(dept: Department) -> bool:
    """
    Verifica se l'utente può gestire gli OKR del dipartimento.
    Solo admin e head del dipartimento possono gestire gli OKR.
    """
    if not current_user.is_authenticated:
        return False
    
    if current_user.is_admin:
        return True
    
    # Head del dipartimento può gestire gli OKR del proprio dipartimento
    if dept.head_id and dept.head_id == current_user.id:
        return True
    
    return False


# ╔════════════════════════════════════════════════════════════════════════╗
# ║ File upload helpers                                                    ║
# ╚════════════════════════════════════════════════════════════════════════╝
def save_department_file(file, dept_id: int, file_type: str) -> str | None:
    """
    Helper per salvare file del dipartimento.
    
    Args:
        file: FileStorage object da Flask
        dept_id: ID del dipartimento
        file_type: Tipo di file ('guidelines', 'sop_members', 'sop_managers')
    
    Returns:
        Path relativo del file salvato o None
    """
    if not file or not file.filename:
        return None
    
    # Sanitizza il filename
    filename = secure_filename(file.filename)
    if not filename:
        return None
    
    # Crea struttura directory: uploads/departments/{dept_id}/
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    dept_folder = os.path.join(upload_folder, 'departments', str(dept_id))
    os.makedirs(dept_folder, exist_ok=True)
    
    # Genera filename unico con timestamp
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    name, ext = os.path.splitext(filename)
    final_filename = f"{file_type}_{timestamp}{ext}"
    filepath = os.path.join(dept_folder, final_filename)
    
    try:
        file.save(filepath)
        # Ritorna path relativo per il database
        return f"departments/{dept_id}/{final_filename}"
    except Exception as e:
        current_app.logger.error(f"Errore salvataggio file: {e}")
        return None


def delete_department_file(file_path: str) -> bool:
    """
    Elimina un file del dipartimento.
    
    Args:
        file_path: Path relativo del file
    
    Returns:
        True se eliminato con successo
    """
    if not file_path:
        return True
    
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    full_path = os.path.join(upload_folder, file_path)
    
    try:
        if os.path.exists(full_path):
            os.remove(full_path)
        return True
    except Exception as e:
        current_app.logger.error(f"Errore eliminazione file: {e}")
        return False


# ╔════════════════════════════════════════════════════════════════════════╗
# ║ CRUD Department                                                       ║
# ╚════════════════════════════════════════════════════════════════════════╝
@dept_bp.route("/", methods=["GET"])
@login_required
def department_list() -> str:
    """Lista dipartimenti con statistiche OKR."""
    # Rimosso _require_admin() - ora tutti possono vedere la lista

    page      = request.args.get("page", 1, type=int)
    per_page  = request.args.get("per_page", 25, type=int)
    q: str    = request.args.get("q", "", type=str).strip()

    stmt = select(Department).order_by(Department.name.asc())
    if q:
        stmt = stmt.where(Department.name.ilike(f"%{q}%"))

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    
    # Aggiungi statistiche OKR per ogni dipartimento
    dept_stats = {}
    for dept in pagination.items:
        # Use query on the relationship to filter
        active_okrs = db.session.query(DepartmentObjective).filter(
            DepartmentObjective.department_id == dept.id,
            DepartmentObjective.status == OKRStatusEnum.active
        ).count()
        
        total_okrs = db.session.query(DepartmentObjective).filter(
            DepartmentObjective.department_id == dept.id
        ).count()
        
        dept_stats[dept.id] = {
            'active_okrs': active_okrs,
            'total_okrs': total_okrs,
            'has_documents': dept.has_any_documents
        }

    return render_template(
        "department/list.html", 
        pagination=pagination, 
        q=q,
        dept_stats=dept_stats
    )

@dept_bp.route("/new", methods=["GET", "POST"])
@login_required
def department_create():
    """Crea nuovo dipartimento con documenti."""
    _require_admin()

    form = DepartmentForm()
    if form.validate_on_submit():
        dept = Department(
            name=form.name.data.strip(),
            head_id=form.head_id.data or None,
            guidelines_text=form.guidelines_text.data.strip() if form.guidelines_text.data else None
        )
        
        # Salva prima il dipartimento per ottenere l'ID
        db.session.add(dept)
        db.session.flush()
        
        # Gestione file upload
        if form.guidelines_pdf.data:
            dept.guidelines_pdf = save_department_file(
                form.guidelines_pdf.data, dept.id, 'guidelines'
            )
            dept.update_document_timestamp('guidelines_pdf')
        
        if form.sop_members_pdf.data:
            dept.sop_members_pdf = save_department_file(
                form.sop_members_pdf.data, dept.id, 'sop_members'
            )
            dept.update_document_timestamp('sop_members_pdf')
        
        if form.sop_managers_pdf.data:
            dept.sop_managers_pdf = save_department_file(
                form.sop_managers_pdf.data, dept.id, 'sop_managers'
            )
            dept.update_document_timestamp('sop_managers_pdf')
        
        db.session.commit()
        flash("Dipartimento creato correttamente.", "success")
        return redirect(url_for("department.department_list"))
    
    return render_template("department/form.html", form=form, mode="create")


@dept_bp.route("/<int:dept_id>/edit", methods=["GET", "POST"])
@login_required
def department_edit(dept_id: int):
    """Modifica dipartimento esistente con gestione documenti."""
    _require_admin()

    dept = Department.query.get_or_404(dept_id)
    form = DepartmentForm(obj=dept)
    
    if form.validate_on_submit():
        dept.name = form.name.data.strip()
        dept.head_id = form.head_id.data or None
        
        # Aggiorna linee guida testuali
        if form.guidelines_text.data != dept.guidelines_text:
            dept.guidelines_text = form.guidelines_text.data.strip() if form.guidelines_text.data else None
            dept.update_document_timestamp('guidelines_text')
        
        # Gestione file PDF linee guida
        if form.remove_guidelines_pdf.data == "true" and dept.guidelines_pdf:
            delete_department_file(dept.guidelines_pdf)
            dept.guidelines_pdf = None
            dept.update_document_timestamp('guidelines_pdf')
        elif form.guidelines_pdf.data:
            # Elimina vecchio file se esiste
            if dept.guidelines_pdf:
                delete_department_file(dept.guidelines_pdf)
            # Salva nuovo file
            dept.guidelines_pdf = save_department_file(
                form.guidelines_pdf.data, dept.id, 'guidelines'
            )
            dept.update_document_timestamp('guidelines_pdf')
        
        # Gestione SOP membri
        if form.remove_sop_members_pdf.data == "true" and dept.sop_members_pdf:
            delete_department_file(dept.sop_members_pdf)
            dept.sop_members_pdf = None
            dept.update_document_timestamp('sop_members_pdf')
        elif form.sop_members_pdf.data:
            if dept.sop_members_pdf:
                delete_department_file(dept.sop_members_pdf)
            dept.sop_members_pdf = save_department_file(
                form.sop_members_pdf.data, dept.id, 'sop_members'
            )
            dept.update_document_timestamp('sop_members_pdf')
        
        # Gestione SOP manager
        if form.remove_sop_managers_pdf.data == "true" and dept.sop_managers_pdf:
            delete_department_file(dept.sop_managers_pdf)
            dept.sop_managers_pdf = None
            dept.update_document_timestamp('sop_managers_pdf')
        elif form.sop_managers_pdf.data:
            if dept.sop_managers_pdf:
                delete_department_file(dept.sop_managers_pdf)
            dept.sop_managers_pdf = save_department_file(
                form.sop_managers_pdf.data, dept.id, 'sop_managers'
            )
            dept.update_document_timestamp('sop_managers_pdf')
        
        db.session.commit()
        flash("Dipartimento aggiornato.", "success")
        return redirect(url_for("department.department_list"))
    
    return render_template("department/form.html", form=form, mode="edit", dept=dept)


@dept_bp.route("/<int:dept_id>/delete", methods=["POST"])
@login_required
def department_delete(dept_id: int):
    """Elimina dipartimento e i suoi documenti."""
    _require_admin()

    dept = Department.query.get_or_404(dept_id)
    
    # Elimina i file associati
    delete_department_file(dept.guidelines_pdf)
    delete_department_file(dept.sop_members_pdf)
    delete_department_file(dept.sop_managers_pdf)
    
    # Elimina la directory del dipartimento se vuota
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    dept_folder = os.path.join(upload_folder, 'departments', str(dept_id))
    try:
        if os.path.exists(dept_folder) and not os.listdir(dept_folder):
            os.rmdir(dept_folder)
    except Exception:
        pass
    
    db.session.delete(dept)
    db.session.commit()
    flash("Dipartimento eliminato.", "info")
    return redirect(url_for("department.department_list"))


# ╔════════════════════════════════════════════════════════════════════════╗
# ║ Document Download Route                                                ║
# ╚════════════════════════════════════════════════════════════════════════╝
@dept_bp.route("/<int:dept_id>/download/<doc_type>")
@login_required
def download_document(dept_id: int, doc_type: str):
    """Scarica documento del dipartimento."""
    dept = Department.query.get_or_404(dept_id)
    
    # Verifica permessi
    if not _can_view_dept(dept):
        abort(HTTPStatus.FORBIDDEN)
    
    # Ottieni il path del documento
    file_path = dept.get_document_path(doc_type)
    
    if not file_path:
        flash("Documento non trovato.", "error")
        return redirect(url_for("department.department_detail", dept_id=dept_id))
    
    # Costruisci path completo
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    full_path = os.path.join(upload_folder, file_path)
    
    if not os.path.exists(full_path):
        flash("File non trovato sul server.", "error")
        return redirect(url_for("department.department_detail", dept_id=dept_id))
    
    # Determina il nome del file per il download
    download_names = {
        'guidelines_pdf': f"Linee_Guida_{dept.name}.pdf",
        'sop_members': f"SOP_Membri_{dept.name}.pdf",
        'sop_managers': f"SOP_Manager_{dept.name}.pdf"
    }
    
    download_name = download_names.get(doc_type, "documento.pdf")
    
    return send_file(
        full_path,
        as_attachment=True,
        download_name=download_name,
        mimetype='application/pdf'
    )


# ╔════════════════════════════════════════════════════════════════════════╗
# ║ DETAIL + Kanban + OKR Integration                                     ║
# ╚════════════════════════════════════════════════════════════════════════╝
@dept_bp.route("/<int:dept_id>", methods=["GET"])
@login_required
def department_detail(dept_id: int) -> str:
    """Dettaglio dipartimento con Kanban e info OKR."""
    dept = Department.query.options(
        db.joinedload(Department.head),
    ).get_or_404(dept_id)
    
    # Verifica permessi di visualizzazione
    if not _can_view_dept(dept):
        abort(HTTPStatus.FORBIDDEN)

    # Raggruppa i task per colonna
    tasks = (
        Task.query
        .filter(Task.department_id == dept.id)
        .order_by(Task.status, Task.priority, Task.created_at)
        .all()
    )
    grouped: dict[str, list[Task]] = {s.value: [] for s in TaskStatusEnum}
    for t in tasks:
        grouped[t.status.value].append(t)
    
    # Statistiche OKR del dipartimento - FIX: use query() instead of direct relationship access
    okr_stats = {
        'total': db.session.query(DepartmentObjective).filter_by(department_id=dept.id).count(),
        'active': db.session.query(DepartmentObjective).filter_by(
            department_id=dept.id, 
            status=OKRStatusEnum.active
        ).count(),
        'completed': db.session.query(DepartmentObjective).filter_by(
            department_id=dept.id, 
            status=OKRStatusEnum.completed
        ).count(),
        'avg_progress': 0
    }
    
    # Calcola progress medio degli obiettivi attivi
    active_objectives = db.session.query(DepartmentObjective).filter_by(
        department_id=dept.id,
        status=OKRStatusEnum.active
    ).all()
    
    if active_objectives:
        # Nessun tracking progress nel modello semplificato
        okr_stats['avg_progress'] = 0
    
    # Recupera obiettivi attivi del trimestre corrente
    from datetime import date
    current_month = date.today().month
    current_quarter = f"q{((current_month - 1) // 3) + 1}"  # q1, q2, q3, q4
    
    current_quarter_objectives = []
    for obj in active_objectives:
        if obj.period and current_quarter in obj.period:
            current_quarter_objectives.append(obj)
    
    # Membri con task assegnati - query corretta per PostgreSQL
    members_task_counts = db.session.query(
        Task.assignee_id,
        db.func.count(Task.id).label('task_count')
    ).filter(
        Task.department_id == dept_id,
        Task.assignee_id.isnot(None)
    ).group_by(Task.assignee_id).all()
    
    # Converti in dizionario per facile accesso nel template
    members_with_tasks = {user_id: count for user_id, count in members_task_counts}
    
    # Controlla se l'utente può modificare gli OKR
    can_edit_okr = _can_manage_dept_okr(dept)

    return render_template(
        "department/detail.html",
        dept=dept,
        kanban_data=grouped,
        okr_stats=okr_stats,
        members_with_tasks=members_with_tasks,
        can_edit_okr=can_edit_okr,
        current_quarter_objectives=current_quarter_objectives,
        current_quarter=current_quarter,
    )

# ╔════════════════════════════════════════════════════════════════════════╗
# ║  ----  TASK Kanban  ----                                              ║
# ╚════════════════════════════════════════════════════════════════════════╝
@dept_bp.route("/<int:dept_id>/tasks/new", methods=["GET", "POST"])
@login_required
def task_create(dept_id: int):
    dept = Department.query.get_or_404(dept_id)
    _require_dept_write(dept)

    form = TaskForm(department=dept)
    if form.validate_on_submit():
        task = Task(
            title=form.title.data.strip(),
            description=form.description.data or None,
            status=TaskStatusEnum(form.status.data),
            priority=TaskPriorityEnum(form.priority.data),
            due_date=form.due_date.data,
            department_id=dept.id,
            assignee_id=int(form.assignee_id.data) if form.assignee_id.data else None,
            client_id=int(form.client_id.data) if form.client_id.data else None,
        )
        db.session.add(task)
        db.session.commit()
        flash("Task creato con successo.", "success")
        return redirect(url_for("department.department_detail", dept_id=dept.id))

    return render_template("task/form.html", form=form, mode="create", dept=dept)


@dept_bp.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def task_edit(task_id: int):
    task = Task.query.get_or_404(task_id)
    dept = task.department
    _require_dept_write(dept)

    form = TaskForm(obj=task, department=dept)
    
    # Precompila i campi search se ci sono valori esistenti
    if task.assignee:
        form.assignee_search.data = task.assignee.full_name
    if task.client:
        form.client_search.data = task.client.nome_cognome
    
    if form.validate_on_submit():
        task.title       = form.title.data.strip()
        task.description = form.description.data or None
        task.status      = TaskStatusEnum(form.status.data)
        task.priority    = TaskPriorityEnum(form.priority.data)
        task.due_date    = form.due_date.data
        task.assignee_id = int(form.assignee_id.data) if form.assignee_id.data else None
        task.client_id   = int(form.client_id.data) if form.client_id.data else None
        db.session.commit()
        flash("Task aggiornato.", "success")
        return redirect(url_for("department.department_detail", dept_id=dept.id))

    return render_template("task/form.html", form=form, mode="edit", dept=dept, task=task)


@dept_bp.route("/tasks/<int:task_id>/delete", methods=["POST"])
@login_required
def task_delete(task_id: int):
    task = Task.query.get_or_404(task_id)
    dept = task.department
    _require_dept_write(dept)

    db.session.delete(task)
    db.session.commit()
    flash("Task eliminato.", "info")
    return redirect(url_for("department.department_detail", dept_id=dept.id))


# ╔════════════════════════════════════════════════════════════════════════╗
# ║  ----  API SEARCH  ----                                               ║
# ╚════════════════════════════════════════════════════════════════════════╝

@dept_bp.route("/api/search/users", methods=["GET"])
@login_required
def api_search_users():
    """API per cercare utenti - TUTTI gli utenti attivi, non filtrati per reparto."""
    query = request.args.get("q", "").strip()
    
    if len(query) < 2:
        return jsonify([])
    
    # Cerca in TUTTI gli utenti attivi (incluso current_user)
    users = (
        db.session.query(User)
        .filter(
            User.is_active.is_(True),
            db.or_(
                User.first_name.ilike(f"%{query}%"),
                User.last_name.ilike(f"%{query}%"),
                db.func.concat(User.first_name, " ", User.last_name).ilike(f"%{query}%")
            )
        )
        .order_by(User.first_name, User.last_name)
        .limit(10)
        .all()
    )
    
    results = [
        {
            "id": user.id,
            "name": user.full_name,
            "department": user.department.name if user.department else "Nessun reparto"
        }
        for user in users
    ]
    
    return jsonify(results)


@dept_bp.route("/api/search/clients", methods=["GET"])
@login_required
def api_search_clients():
    """API per cercare clienti."""
    query = request.args.get("q", "").strip()
    
    if len(query) < 2:
        return jsonify([])
    
    clients = (
        db.session.query(Cliente)
        .filter(Cliente.nome_cognome.ilike(f"%{query}%"))
        .order_by(Cliente.nome_cognome)
        .limit(10)
        .all()
    )
    
    results = [
        {
            "id": client.cliente_id,
            "name": client.nome_cognome,
        }
        for client in clients
    ]
    
    return jsonify(results)


# ─────────────────────── API helpers (drag-and-drop, inline) ─────────────────────── #
@dept_bp.route("/api/tasks/<int:task_id>/status", methods=["PATCH"])
@login_required
def api_task_change_status(task_id: int):
    task = Task.query.get_or_404(task_id)
    dept = task.department
    _require_dept_write(dept)

    data = request.get_json(silent=True) or {}
    new_status = data.get("status")

    if new_status not in TaskStatusEnum.__members__:
        return jsonify({"error": "Status non valido"}), HTTPStatus.BAD_REQUEST

    task.status = TaskStatusEnum[new_status]
    db.session.commit()
    return jsonify(success=True, new_status=task.status.value)


@dept_bp.route("/api/tasks/<int:task_id>/assignee", methods=["PATCH"])
@login_required
def api_task_change_assignee(task_id: int):
    task = Task.query.get_or_404(task_id)
    dept = task.department
    _require_dept_write(dept)

    data = request.get_json(silent=True) or {}
    assignee_id = data.get("assignee_id")

    if assignee_id:
        user = User.query.get(assignee_id)
        if user is None:
            return jsonify(error="Assignee non valido"), HTTPStatus.BAD_REQUEST
        task.assignee_id = assignee_id
    else:
        task.assignee_id = None

    db.session.commit()
    return jsonify(success=True, assignee_id=task.assignee_id)


@dept_bp.route("/api/tasks/<int:task_id>", methods=["PATCH"])
@login_required
def api_task_update(task_id: int):
    task = Task.query.get_or_404(task_id)
    dept = task.department
    _require_dept_write(dept)

    data: Dict[str, Any] = request.get_json(silent=True) or {}

    if "title" in data:
        task.title = data["title"].strip()[:255]
    if "description" in data:
        task.description = data["description"] or None
    if "priority" in data and data["priority"] in TaskPriorityEnum.__members__:
        task.priority = TaskPriorityEnum[data["priority"]]
    if "due_date" in data:          # "" → None
        task.due_date = data["due_date"] or None

    try:
        db.session.commit()
    except SQLAlchemyError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), HTTPStatus.INTERNAL_SERVER_ERROR

    return jsonify(success=True)


@dept_bp.route("/api/tasks/<int:task_id>/comments", methods=["POST"])
@login_required
def api_task_add_comment(task_id: int):
    """
    Commenti non ancora implementati – placeholder per futura TaskComment.
    """
    return jsonify(error="Commenti non ancora implementati."), HTTPStatus.NOT_IMPLEMENTED


# ╔════════════════════════════════════════════════════════════════════════╗
# ║  ----  Organigramma Routes  ----                                      ║
# ╚════════════════════════════════════════════════════════════════════════╝

@dept_bp.route("/organigramma", methods=["GET"])
def organigramma():
    """Vista organigramma aziendale interattivo - accessibile a tutti."""
    return render_template("department/organigramma.html")


@dept_bp.route("/api/organigramma/data", methods=["GET"])
def api_organigramma_data():
    """API per ottenere dati organigramma - accessibile a tutti."""
    try:
        from corposostenibile.models import Team
        def _visible_org_user(user):
            return bool(user and user.is_active and getattr(user, "role", None))

        # Recupera tutti i dipartimenti con head e membri
        departments = Department.query.options(
            db.joinedload(Department.head),
            db.joinedload(Department.members)
        ).all()

        # Conta totale dipendenti unici
        all_employees = set()

        # ═══════════════════════════════════════════════════════════
        # NUOVA STRUTTURA GERARCHICA
        # ═══════════════════════════════════════════════════════════

        # TEAM INTERNO: CCO con Coach, Nutrizione, Psicologia, Health Manager
        TEAM_INTERNO_DEPARTMENTS = ['coach', 'nutrizione', 'psicologia', 'customer success']

        # OPERATIONS: IT, HR, Finance
        OPERATIONS_DEPARTMENTS = ['it', 'hr', 'finance']

        # MARKETING E VENDITA: Marketing, Appointment Setter, Sales
        MARKETING_VENDITA_DEPARTMENTS = ['marketing', 'appointment setter', 'consulenti sales 1', 'consulenti sales 2']

        # Dipartimenti Sales (da raggruppare come sotto-team)
        SALES_DEPARTMENTS = ['consulenti sales 1', 'consulenti sales 2']

        # Dipartimenti da nascondere nell'organigramma
        HIDDEN_DEPARTMENTS = ['nutrizione 2', 'test']

        # Rinomina per visualizzazione
        DISPLAY_NAMES = {
            'customer success': 'Health Manager'
        }

        # Costruisci struttura dati gerarchica
        hierarchy = {
            'ceo': None,
            'cofounder': None,
            'team_interno': {
                'name': 'Team Interno',
                'cco': None,
                'departments': []
            },
            'operations': {
                'name': 'Operations',
                'departments': []
            },
            'marketing_vendita': {
                'name': 'Marketing e Vendita',
                'departments': [],
                'sales': None  # Sales raggruppato con team
            }
        }

        # Dizionario temporaneo per i dipartimenti
        all_depts = {}

        # Identifica tutti i dipartimenti (escludi quelli nascosti)
        for dept in departments:
            # Salta i dipartimenti nascosti
            if dept.name.lower() in HIDDEN_DEPARTMENTS:
                continue

            # Usa nome display se disponibile
            display_name = DISPLAY_NAMES.get(dept.name.lower(), dept.name)

            dept_info = {
                'id': dept.id,
                'name': display_name,
                'original_name': dept.name.lower(),
                'head': None,
                'members': [],
                'teams': []  # Per dipartimenti con team (es. Nutrizione)
            }

            # Head info (escludi utenti test e non attivi dal conteggio)
            if _visible_org_user(dept.head):
                if dept.head.full_name not in ['Matteo Test Manager', 'Matteo Test User']:
                    all_employees.add(dept.head.id)
                dept_info['head'] = {
                    'id': dept.head.id,
                    'full_name': dept.head.full_name,
                    'job_title': dept.head.job_title or dept.name,
                    'avatar_url': dept.head.avatar_url,
                    'email': dept.head.email
                }

            # Se è Nutrizione o Psicologia, gestisci i team separatamente
            if dept.name.lower() in ['nutrizione', 'psicologia'] and dept.teams:
                for team in dept.teams:
                    team_info = {
                        'id': team.id,
                        'name': team.name,
                        'head': None,
                        'members': []
                    }

                    # Team head
                    if _visible_org_user(team.head):
                        if team.head.full_name not in ['Matteo Test Manager', 'Matteo Test User']:
                            all_employees.add(team.head.id)
                        team_info['head'] = {
                            'id': team.head.id,
                            'full_name': team.head.full_name,
                            'job_title': team.head.job_title or f'Responsabile {team.name}',
                            'avatar_url': team.head.avatar_url,
                            'email': team.head.email
                        }

                    # Team members (escludi head)
                    for member in team.members:
                        if not _visible_org_user(member):
                            continue
                        if team.head and member.id == team.head.id:
                            continue
                        if member.full_name not in ['Matteo Test Manager', 'Matteo Test User']:
                            all_employees.add(member.id)
                        team_info['members'].append({
                            'id': member.id,
                            'full_name': member.full_name,
                            'job_title': member.job_title or 'Membro Team',
                            'avatar_url': member.avatar_url,
                            'email': member.email
                        })

                    # Ordina membri alfabeticamente
                    team_info['members'].sort(key=lambda x: x['full_name'])
                    dept_info['teams'].append(team_info)

                # Ordina team per nome
                dept_info['teams'].sort(key=lambda x: x['name'])
            else:
                # Members info per dipartimenti normali
                for member in dept.members:
                    if not _visible_org_user(member):
                        continue
                    if dept.head and member.id == dept.head.id:
                        continue
                    if member.full_name not in ['Matteo Test Manager', 'Matteo Test User']:
                        all_employees.add(member.id)
                    dept_info['members'].append({
                        'id': member.id,
                        'full_name': member.full_name,
                        'job_title': member.job_title or 'Membro Team',
                        'avatar_url': member.avatar_url,
                        'email': member.email
                    })

            all_depts[dept.name.lower()] = dept_info

        # Organizza la gerarchia
        for dept_name, dept_info in all_depts.items():
            if dept_name == 'ceo':
                hierarchy['ceo'] = dept_info
            elif dept_name == 'co-founder':
                hierarchy['cofounder'] = dept_info
            elif dept_name == 'cco':
                # CCO va nel Team Interno
                hierarchy['team_interno']['cco'] = dept_info
            elif dept_name in TEAM_INTERNO_DEPARTMENTS:
                # Dipartimenti del Team Interno (sotto CCO)
                hierarchy['team_interno']['departments'].append(dept_info)
            elif dept_name in OPERATIONS_DEPARTMENTS:
                # Dipartimenti Operations
                hierarchy['operations']['departments'].append(dept_info)
            elif dept_name in MARKETING_VENDITA_DEPARTMENTS and dept_name not in SALES_DEPARTMENTS:
                # Marketing e Appointment Setter
                hierarchy['marketing_vendita']['departments'].append(dept_info)
            # Sales viene gestito separatamente

        # Crea la sezione Sales con i due team (dentro Marketing e Vendita)
        sales_teams = []
        for sales_name in SALES_DEPARTMENTS:
            if sales_name in all_depts:
                dept = all_depts[sales_name]
                # Rinomina per visualizzazione
                team_name = 'Team 1' if '1' in sales_name else 'Team 2'
                sales_teams.append({
                    'id': dept['id'],
                    'name': team_name,
                    'head': dept['head'],
                    'members': dept['members']
                })

        if sales_teams:
            hierarchy['marketing_vendita']['sales'] = {
                'name': 'Sales',
                'teams': sorted(sales_teams, key=lambda x: x['name'])
            }

        # Ordina i dipartimenti alfabeticamente in ogni sezione
        hierarchy['team_interno']['departments'].sort(key=lambda x: x['name'])
        hierarchy['operations']['departments'].sort(key=lambda x: x['name'])
        hierarchy['marketing_vendita']['departments'].sort(key=lambda x: x['name'])

        # Ordina i membri di ogni dipartimento alfabeticamente
        for dept in hierarchy['team_interno']['departments']:
            if dept['members']:
                dept['members'].sort(key=lambda x: x['full_name'])

        for dept in hierarchy['operations']['departments']:
            if dept['members']:
                dept['members'].sort(key=lambda x: x['full_name'])

        for dept in hierarchy['marketing_vendita']['departments']:
            if dept['members']:
                dept['members'].sort(key=lambda x: x['full_name'])

        # Conta dipartimenti totali
        real_departments_count = (
            len(hierarchy['team_interno']['departments']) +
            len(hierarchy['operations']['departments']) +
            len(hierarchy['marketing_vendita']['departments']) +
            (1 if hierarchy['marketing_vendita']['sales'] else 0)  # Sales conta come 1
        )

        return jsonify({
            'hierarchy': hierarchy,
            'total_employees': len(all_employees),
            'departments_count': real_departments_count
        })

    except Exception as e:
        current_app.logger.error(f"Errore in api_organigramma_data: {e}")
        return jsonify({'error': 'Errore nel recupero dei dati'}), HTTPStatus.INTERNAL_SERVER_ERROR


# ╔════════════════════════════════════════════════════════════════════════╗
# ║  ----  OKR Quick Stats API  ----                                      ║
# ╚════════════════════════════════════════════════════════════════════════╝

@dept_bp.route("/api/<int:dept_id>/okr-stats", methods=["GET"])
@login_required
def api_dept_okr_stats(dept_id: int):
    """API per ottenere statistiche OKR del dipartimento in tempo reale."""
    dept = Department.query.get_or_404(dept_id)
    
    if not _can_view_dept(dept):
        return jsonify({"error": "Non autorizzato"}), HTTPStatus.FORBIDDEN
    
    # Calcola statistiche - FIX: use query() instead of direct relationship access
    total = db.session.query(DepartmentObjective).filter_by(department_id=dept.id).count()
    active = db.session.query(DepartmentObjective).filter_by(
        department_id=dept.id, 
        status=OKRStatusEnum.active
    ).count()
    completed = db.session.query(DepartmentObjective).filter_by(
        department_id=dept.id, 
        status=OKRStatusEnum.completed
    ).count()
    
    # Progress medio
    active_objectives = db.session.query(DepartmentObjective).filter_by(
        department_id=dept.id,
        status=OKRStatusEnum.active
    ).all()
    
    # Nessun tracking progress nel modello semplificato
    avg_progress = 0
    
    # Key Results totali e assegnati - FIX: use queries
    all_objectives = db.session.query(DepartmentObjective).filter_by(department_id=dept.id).all()
    total_kr = sum(len(obj.key_results) for obj in all_objectives)
    assigned_kr = sum(
        1 for obj in all_objectives 
        for kr in obj.key_results 
        if kr.assignee_id
    )
    
    return jsonify({
        'total': total,
        'active': active,
        'completed': completed,
        'avg_progress': avg_progress,
        'total_kr': total_kr,
        'assigned_kr': assigned_kr,
        'can_create': active < 5  # Max 5 obiettivi attivi
    })
