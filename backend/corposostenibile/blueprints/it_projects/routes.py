"""Routes per IT Projects - Solo Admin"""
from flask import render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from datetime import datetime, date
from sqlalchemy import case, func
from corposostenibile.extensions import db, csrf
from corposostenibile.models import (
    ITProject, ITProblem, ITIdea, ITManualCategory, ITManualArticle,
    User, Department, it_project_members
)
from . import bp


def admin_required(f):
    """Decorator per verificare che l'utente sia admin."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def get_it_department_members():
    """Ottiene i membri del dipartimento IT (ID=1)."""
    return User.query.filter_by(
        department_id=1,
        is_active=True
    ).order_by(User.first_name).all()


@bp.route('/')
@login_required
@admin_required
def index():
    """Lista progetti IT con separazione deadline/senza deadline."""
    # Progetti CON deadline (ordinati per data deadline)
    projects_with_deadline = ITProject.query.filter(
        ITProject.has_deadline == True,
        ITProject.status.notin_(['completed', 'cancelled'])
    ).order_by(ITProject.deadline.asc()).all()

    # Progetti SENZA deadline (ordinati per priority_order manuale)
    projects_without_deadline = ITProject.query.filter(
        ITProject.has_deadline == False,
        ITProject.status.notin_(['completed', 'cancelled'])
    ).order_by(ITProject.priority_order.asc()).all()

    # Progetti completati/annullati (archivio)
    archived_projects = ITProject.query.filter(
        ITProject.status.in_(['completed', 'cancelled'])
    ).order_by(ITProject.updated_at.desc()).limit(10).all()

    # Statistiche
    stats = {
        'total_active': len(projects_with_deadline) + len(projects_without_deadline),
        'with_deadline': len(projects_with_deadline),
        'without_deadline': len(projects_without_deadline),
        'overdue': sum(1 for p in projects_with_deadline if p.is_overdue),
        'total_estimated_hours': sum((p.estimated_hours or 0) for p in projects_with_deadline + projects_without_deadline),
        'total_worked_hours': sum((p.worked_hours or 0) for p in projects_with_deadline + projects_without_deadline),
    }

    return render_template(
        'it_projects/index.html',
        projects_with_deadline=projects_with_deadline,
        projects_without_deadline=projects_without_deadline,
        archived_projects=archived_projects,
        stats=stats
    )


@bp.route('/new', methods=['GET', 'POST'])
@csrf.exempt
@login_required
@admin_required
def new():
    """Crea nuovo progetto IT."""
    if request.method == 'POST':
        try:
            # Dati form
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            specifications = request.form.get('specifications', '').strip()
            adoption_strategy = request.form.get('adoption_strategy', '').strip()
            estimated_hours = request.form.get('estimated_hours', type=float) or 0
            deadline_str = request.form.get('deadline', '').strip()
            status = request.form.get('status', 'planning')
            team_member_ids = request.form.getlist('team_members', type=int)

            # Validazione
            if not title:
                flash('Il titolo è obbligatorio', 'error')
                return redirect(url_for('it_projects.new'))

            # Gestione deadline
            has_deadline = bool(deadline_str)
            deadline = None
            if has_deadline:
                try:
                    deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
                except ValueError:
                    flash('Formato data deadline non valido', 'error')
                    return redirect(url_for('it_projects.new'))

            # Calcola priority_order per progetti senza deadline
            priority_order = 0
            if not has_deadline:
                max_order = db.session.query(func.max(ITProject.priority_order)).filter(
                    ITProject.has_deadline == False
                ).scalar() or 0
                priority_order = max_order + 1

            # Crea progetto
            project = ITProject(
                title=title,
                description=description,
                specifications=specifications,
                adoption_strategy=adoption_strategy,
                estimated_hours=estimated_hours,
                deadline=deadline,
                has_deadline=has_deadline,
                priority_order=priority_order,
                status=status,
                created_by_id=current_user.id
            )

            # Aggiungi membri team
            if team_member_ids:
                team_members = User.query.filter(User.id.in_(team_member_ids)).all()
                project.team_members = team_members

            db.session.add(project)
            db.session.commit()

            flash(f'Progetto "{title}" creato con successo!', 'success')
            return redirect(url_for('it_projects.detail', project_id=project.id))
        except Exception as e:
            db.session.rollback()
            import traceback
            error_details = traceback.format_exc()
            flash(f'Errore: {str(e)}', 'error')
            # Log to file for debugging
            with open('/tmp/it_projects_error.log', 'a') as f:
                f.write(f"\n{'='*50}\n{error_details}\n")
            return redirect(url_for('it_projects.new'))

    # GET: mostra form
    it_members = get_it_department_members()

    return render_template(
        'it_projects/form.html',
        project=None,
        it_members=it_members,
        statuses=[
            ('planning', 'Pianificazione'),
            ('in_progress', 'In Corso'),
            ('review', 'In Review'),
            ('on_hold', 'In Pausa'),
        ]
    )


@bp.route('/<int:project_id>')
@login_required
@admin_required
def detail(project_id):
    """Dettaglio progetto IT."""
    project = ITProject.query.get_or_404(project_id)
    it_members = get_it_department_members()

    return render_template(
        'it_projects/detail.html',
        project=project,
        it_members=it_members
    )


@bp.route('/<int:project_id>/edit', methods=['GET', 'POST'])
@csrf.exempt
@login_required
@admin_required
def edit(project_id):
    """Modifica progetto IT."""
    project = ITProject.query.get_or_404(project_id)

    if request.method == 'POST':
        # Dati form
        project.title = request.form.get('title', '').strip()
        project.description = request.form.get('description', '').strip()
        project.specifications = request.form.get('specifications', '').strip()
        project.adoption_strategy = request.form.get('adoption_strategy', '').strip()
        project.estimated_hours = request.form.get('estimated_hours', type=float) or 0
        project.worked_hours = request.form.get('worked_hours', type=float) or 0
        project.status = request.form.get('status', 'planning')

        deadline_str = request.form.get('deadline', '').strip()
        team_member_ids = request.form.getlist('team_members', type=int)

        # Validazione
        if not project.title:
            flash('Il titolo è obbligatorio', 'error')
            return redirect(url_for('it_projects.edit', project_id=project_id))

        # Gestione deadline
        old_has_deadline = project.has_deadline
        project.has_deadline = bool(deadline_str)

        if project.has_deadline:
            try:
                project.deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Formato data deadline non valido', 'error')
                return redirect(url_for('it_projects.edit', project_id=project_id))
        else:
            project.deadline = None
            # Se passa da con deadline a senza, assegna priority_order
            if old_has_deadline:
                max_order = db.session.query(func.max(ITProject.priority_order)).filter(
                    ITProject.has_deadline == False,
                    ITProject.id != project.id
                ).scalar() or 0
                project.priority_order = max_order + 1

        # Aggiorna membri team
        if team_member_ids:
            team_members = User.query.filter(User.id.in_(team_member_ids)).all()
            project.team_members = team_members
        else:
            project.team_members = []

        db.session.commit()

        flash(f'Progetto "{project.title}" aggiornato!', 'success')
        return redirect(url_for('it_projects.detail', project_id=project.id))

    # GET: mostra form
    it_members = get_it_department_members()

    return render_template(
        'it_projects/form.html',
        project=project,
        it_members=it_members,
        statuses=[
            ('planning', 'Pianificazione'),
            ('in_progress', 'In Corso'),
            ('review', 'In Review'),
            ('completed', 'Completato'),
            ('on_hold', 'In Pausa'),
            ('cancelled', 'Annullato'),
        ]
    )


@bp.route('/<int:project_id>/delete', methods=['POST'])
@csrf.exempt
@login_required
@admin_required
def delete(project_id):
    """Elimina progetto IT."""
    project = ITProject.query.get_or_404(project_id)
    title = project.title

    db.session.delete(project)
    db.session.commit()

    flash(f'Progetto "{title}" eliminato', 'success')
    return redirect(url_for('it_projects.index'))


@bp.route('/archive')
@login_required
@admin_required
def archive():
    """Archivio completo progetti completati/annullati."""
    page = request.args.get('page', 1, type=int)
    per_page = 20

    archived_query = ITProject.query.filter(
        ITProject.status.in_(['completed', 'cancelled'])
    ).order_by(ITProject.updated_at.desc())

    pagination = archived_query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        'it_projects/archive.html',
        projects=pagination.items,
        pagination=pagination
    )


@bp.route('/api/reorder', methods=['POST'])
@csrf.exempt
@login_required
@admin_required
def reorder():
    """API per riordinare progetti senza deadline (drag & drop)."""
    data = request.get_json()

    if not data or 'order' not in data:
        return jsonify({'success': False, 'error': 'Dati mancanti'}), 400

    order = data['order']  # Lista di project_id nell'ordine desiderato

    try:
        for index, project_id in enumerate(order):
            project = ITProject.query.get(project_id)
            if project and not project.has_deadline:
                project.priority_order = index

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/<int:project_id>/update-hours', methods=['POST'])
@csrf.exempt
@login_required
@admin_required
def update_hours(project_id):
    """API per aggiornare rapidamente le ore lavorate."""
    project = ITProject.query.get_or_404(project_id)
    data = request.get_json()

    if 'worked_hours' in data:
        project.worked_hours = float(data['worked_hours'])
        db.session.commit()
        return jsonify({
            'success': True,
            'worked_hours': project.worked_hours,
            'progress': project.progress_percentage
        })

    return jsonify({'success': False, 'error': 'Dati mancanti'}), 400


@bp.route('/api/<int:project_id>/update-status', methods=['POST'])
@csrf.exempt
@login_required
@admin_required
def update_status(project_id):
    """API per aggiornare rapidamente lo stato."""
    project = ITProject.query.get_or_404(project_id)
    data = request.get_json()

    if 'status' in data:
        valid_statuses = ['planning', 'in_progress', 'review', 'completed', 'on_hold', 'cancelled']
        if data['status'] in valid_statuses:
            project.status = data['status']
            db.session.commit()
            return jsonify({
                'success': True,
                'status': project.status,
                'status_label': project.status_label,
                'status_color': project.status_color
            })

    return jsonify({'success': False, 'error': 'Stato non valido'}), 400


# ============================================================================ #
#                           IT PROBLEMS - SEGNALAZIONI                          #
# ============================================================================ #

CRITICALITY_CHOICES = [
    ('blocking', 'Bloccante'),
    ('non_blocking', 'Non Bloccante')
]

TOOL_CHOICES = [
    ('suite', 'Corposostenibile Suite'),
    ('ghl', 'Go High Level'),
    ('respond_io', 'Respond.io'),
    ('other', 'Altro')
]

STATUS_CHOICES = [
    ('open', 'Aperto'),
    ('in_progress', 'In Lavorazione'),
    ('resolved', 'Risolto')
]


@bp.route('/problems')
@login_required
@admin_required
def problems_list():
    """Lista problemi IT (solo admin)."""
    # Filtri
    criticality = request.args.get('criticality', '')
    tool = request.args.get('tool', '')
    status = request.args.get('status', '')

    query = ITProblem.query

    if criticality:
        query = query.filter(ITProblem.criticality == criticality)
    if tool:
        query = query.filter(ITProblem.tool == tool)
    if status:
        query = query.filter(ITProblem.status == status)
    else:
        # Default: mostra solo aperti e in lavorazione
        query = query.filter(ITProblem.status.in_(['open', 'in_progress']))

    # Ordinamento: bloccanti prima, poi per data creazione
    query = query.order_by(
        case((ITProblem.criticality == 'blocking', 0), else_=1),
        ITProblem.created_at.desc()
    )

    problems = query.all()

    # Statistiche
    stats = {
        'total_open': ITProblem.query.filter(ITProblem.status.in_(['open', 'in_progress'])).count(),
        'blocking': ITProblem.query.filter(ITProblem.status.in_(['open', 'in_progress']), ITProblem.criticality == 'blocking').count(),
        'non_blocking': ITProblem.query.filter(ITProblem.status.in_(['open', 'in_progress']), ITProblem.criticality == 'non_blocking').count(),
        'resolved_this_month': ITProblem.query.filter(
            ITProblem.status == 'resolved',
            ITProblem.resolved_at >= datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
        ).count(),
    }

    # Calcola tempo medio risoluzione
    resolved_problems = ITProblem.query.filter(ITProblem.resolved_at.isnot(None)).all()
    if resolved_problems:
        total_hours = sum(p.resolution_time_hours or 0 for p in resolved_problems)
        stats['avg_resolution_hours'] = round(total_hours / len(resolved_problems), 1)
    else:
        stats['avg_resolution_hours'] = 0

    return render_template(
        'it_projects/problems/list.html',
        problems=problems,
        stats=stats,
        criticality_choices=CRITICALITY_CHOICES,
        tool_choices=TOOL_CHOICES,
        status_choices=STATUS_CHOICES,
        current_filters={
            'criticality': criticality,
            'tool': tool,
            'status': status
        }
    )


@bp.route('/problems/new', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def problems_new():
    """Segnala nuovo problema (accessibile a tutti gli utenti loggati)."""
    if request.method == 'POST':
        try:
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            criticality = request.form.get('criticality', 'non_blocking')
            tool = request.form.get('tool', 'suite')

            if not title:
                flash('Il titolo è obbligatorio', 'error')
                return redirect(url_for('it_projects.problems_new'))

            if not description:
                flash('La descrizione è obbligatoria', 'error')
                return redirect(url_for('it_projects.problems_new'))

            problem = ITProblem(
                title=title,
                description=description,
                criticality=criticality,
                tool=tool,
                reported_by_id=current_user.id
            )

            db.session.add(problem)
            db.session.commit()

            flash('Problema segnalato con successo! Il team IT lo prenderà in carico.', 'success')
            return redirect(url_for('it_projects.problems_my'))
        except Exception as e:
            db.session.rollback()
            import traceback
            traceback.print_exc()
            flash(f'Errore durante la creazione: {str(e)}', 'error')
            return redirect(url_for('it_projects.problems_new'))

    return render_template(
        'it_projects/problems/new.html',
        criticality_choices=CRITICALITY_CHOICES,
        tool_choices=TOOL_CHOICES
    )


@bp.route('/problems/my')
@login_required
def problems_my():
    """I miei problemi segnalati."""
    problems = ITProblem.query.filter(
        ITProblem.reported_by_id == current_user.id
    ).order_by(ITProblem.created_at.desc()).all()

    return render_template(
        'it_projects/problems/my.html',
        problems=problems
    )


@bp.route('/problems/<int:problem_id>')
@login_required
@admin_required
def problems_detail(problem_id):
    """Dettaglio problema (solo admin)."""
    problem = ITProblem.query.get_or_404(problem_id)
    it_members = get_it_department_members()

    return render_template(
        'it_projects/problems/detail.html',
        problem=problem,
        it_members=it_members,
        status_choices=STATUS_CHOICES
    )


@bp.route('/problems/<int:problem_id>/edit', methods=['GET', 'POST'])
@csrf.exempt
@login_required
@admin_required
def problems_edit(problem_id):
    """Modifica problema (solo admin)."""
    problem = ITProblem.query.get_or_404(problem_id)

    if request.method == 'POST':
        problem.title = request.form.get('title', '').strip()
        problem.description = request.form.get('description', '').strip()
        problem.criticality = request.form.get('criticality', 'non_blocking')
        problem.tool = request.form.get('tool', 'suite')
        problem.status = request.form.get('status', 'open')
        problem.resolution_notes = request.form.get('resolution_notes', '').strip()

        assigned_to_id = request.form.get('assigned_to_id', type=int)
        problem.assigned_to_id = assigned_to_id if assigned_to_id else None

        # Se stato cambia a resolved, imposta resolved_at
        if problem.status == 'resolved' and not problem.resolved_at:
            problem.resolved_at = datetime.utcnow()
        elif problem.status != 'resolved':
            problem.resolved_at = None

        db.session.commit()
        flash('Problema aggiornato!', 'success')
        return redirect(url_for('it_projects.problems_detail', problem_id=problem.id))

    it_members = get_it_department_members()

    return render_template(
        'it_projects/problems/edit.html',
        problem=problem,
        it_members=it_members,
        criticality_choices=CRITICALITY_CHOICES,
        tool_choices=TOOL_CHOICES,
        status_choices=STATUS_CHOICES
    )


@bp.route('/problems/<int:problem_id>/delete', methods=['POST'])
@csrf.exempt
@login_required
@admin_required
def problems_delete(problem_id):
    """Elimina problema (solo admin)."""
    problem = ITProblem.query.get_or_404(problem_id)
    title = problem.title

    db.session.delete(problem)
    db.session.commit()

    flash(f'Problema "{title}" eliminato', 'success')
    return redirect(url_for('it_projects.problems_list'))


@bp.route('/api/problems/<int:problem_id>/update-status', methods=['POST'])
@csrf.exempt
@login_required
@admin_required
def problems_update_status(problem_id):
    """API per aggiornare rapidamente lo stato del problema."""
    problem = ITProblem.query.get_or_404(problem_id)
    data = request.get_json()

    if 'status' in data:
        valid_statuses = ['open', 'in_progress', 'resolved']
        if data['status'] in valid_statuses:
            old_status = problem.status
            problem.status = data['status']

            # Se passa a resolved, imposta resolved_at
            if problem.status == 'resolved' and old_status != 'resolved':
                problem.resolved_at = datetime.utcnow()
            elif problem.status != 'resolved':
                problem.resolved_at = None

            db.session.commit()
            return jsonify({
                'success': True,
                'status': problem.status,
                'status_label': problem.status_label,
                'status_color': problem.status_color,
                'resolution_time_hours': problem.resolution_time_hours
            })

    return jsonify({'success': False, 'error': 'Stato non valido'}), 400


@bp.route('/api/problems/<int:problem_id>/assign', methods=['POST'])
@csrf.exempt
@login_required
@admin_required
def problems_assign(problem_id):
    """API per assegnare rapidamente un problema."""
    problem = ITProblem.query.get_or_404(problem_id)
    data = request.get_json()

    assigned_to_id = data.get('assigned_to_id')

    if assigned_to_id:
        user = User.query.get(assigned_to_id)
        if not user:
            return jsonify({'success': False, 'error': 'Utente non trovato'}), 404
        problem.assigned_to_id = assigned_to_id
        # Se assegnato, passa automaticamente a in_progress
        if problem.status == 'open':
            problem.status = 'in_progress'
    else:
        problem.assigned_to_id = None

    db.session.commit()

    return jsonify({
        'success': True,
        'assigned_to': problem.assigned_to.full_name if problem.assigned_to else None,
        'status': problem.status,
        'status_label': problem.status_label
    })


# ============================================================================ #
#                              IT IDEAS - PROPOSTE                              #
# ============================================================================ #

IDEA_STATUS_CHOICES = [
    ('pending', 'In Attesa'),
    ('approved', 'Approvata'),
    ('rejected', 'Rifiutata'),
    ('converted', 'Convertita in Progetto')
]


@bp.route('/ideas')
@login_required
@admin_required
def ideas_list():
    """Lista idee (solo admin)."""
    status = request.args.get('status', '')

    query = ITIdea.query

    if status:
        query = query.filter(ITIdea.status == status)

    # Ordinamento: pending prima, poi per data
    query = query.order_by(
        case((ITIdea.status == 'pending', 0), else_=1),
        ITIdea.created_at.desc()
    )

    ideas = query.all()

    # Statistiche
    stats = {
        'total': ITIdea.query.count(),
        'pending': ITIdea.query.filter_by(status='pending').count(),
        'approved': ITIdea.query.filter_by(status='approved').count(),
        'converted': ITIdea.query.filter_by(status='converted').count(),
    }

    return render_template(
        'it_projects/ideas/list.html',
        ideas=ideas,
        stats=stats,
        status_choices=IDEA_STATUS_CHOICES,
        current_status=status
    )


@bp.route('/ideas/new', methods=['GET', 'POST'])
@csrf.exempt
@login_required
def ideas_new():
    """Proponi nuova idea (accessibile a tutti gli utenti loggati)."""
    if request.method == 'POST':
        try:
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()

            if not title:
                flash('Il titolo è obbligatorio', 'error')
                return redirect(url_for('it_projects.ideas_new'))

            if not description:
                flash('La descrizione è obbligatoria', 'error')
                return redirect(url_for('it_projects.ideas_new'))

            idea = ITIdea(
                title=title,
                description=description,
                proposed_by_id=current_user.id
            )

            db.session.add(idea)
            db.session.commit()

            flash('Idea proposta con successo! Grazie per il tuo contributo.', 'success')
            return redirect(url_for('it_projects.ideas_my'))
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante la creazione: {str(e)}', 'error')
            return redirect(url_for('it_projects.ideas_new'))

    return render_template('it_projects/ideas/new.html')


@bp.route('/ideas/my')
@login_required
def ideas_my():
    """Le mie idee proposte."""
    ideas = ITIdea.query.filter(
        ITIdea.proposed_by_id == current_user.id
    ).order_by(ITIdea.created_at.desc()).all()

    return render_template(
        'it_projects/ideas/my.html',
        ideas=ideas
    )


@bp.route('/ideas/<int:idea_id>')
@login_required
@admin_required
def ideas_detail(idea_id):
    """Dettaglio idea (solo admin)."""
    idea = ITIdea.query.get_or_404(idea_id)

    return render_template(
        'it_projects/ideas/detail.html',
        idea=idea,
        status_choices=IDEA_STATUS_CHOICES
    )


@bp.route('/ideas/<int:idea_id>/edit', methods=['GET', 'POST'])
@csrf.exempt
@login_required
@admin_required
def ideas_edit(idea_id):
    """Modifica idea (solo admin)."""
    idea = ITIdea.query.get_or_404(idea_id)

    if request.method == 'POST':
        idea.title = request.form.get('title', '').strip()
        idea.description = request.form.get('description', '').strip()
        idea.status = request.form.get('status', 'pending')
        idea.admin_notes = request.form.get('admin_notes', '').strip()

        db.session.commit()
        flash('Idea aggiornata!', 'success')
        return redirect(url_for('it_projects.ideas_detail', idea_id=idea.id))

    return render_template(
        'it_projects/ideas/edit.html',
        idea=idea,
        status_choices=IDEA_STATUS_CHOICES
    )


@bp.route('/ideas/<int:idea_id>/delete', methods=['POST'])
@csrf.exempt
@login_required
@admin_required
def ideas_delete(idea_id):
    """Elimina idea (solo admin)."""
    idea = ITIdea.query.get_or_404(idea_id)
    title = idea.title

    db.session.delete(idea)
    db.session.commit()

    flash(f'Idea "{title}" eliminata', 'success')
    return redirect(url_for('it_projects.ideas_list'))


@bp.route('/ideas/<int:idea_id>/convert', methods=['GET', 'POST'])
@csrf.exempt
@login_required
@admin_required
def ideas_convert(idea_id):
    """Converti idea in progetto (solo admin)."""
    idea = ITIdea.query.get_or_404(idea_id)

    if not idea.is_convertible:
        flash('Questa idea non può essere convertita in progetto', 'error')
        return redirect(url_for('it_projects.ideas_detail', idea_id=idea.id))

    if request.method == 'POST':
        # Crea nuovo progetto
        project = ITProject(
            title=request.form.get('title', idea.title).strip(),
            description=request.form.get('description', idea.description).strip(),
            specifications=request.form.get('specifications', '').strip(),
            estimated_hours=float(request.form.get('estimated_hours', 0) or 0),
            created_by_id=current_user.id
        )

        db.session.add(project)
        db.session.flush()  # Per ottenere l'ID del progetto

        # Aggiorna idea
        idea.status = 'converted'
        idea.converted_to_project_id = project.id
        idea.converted_at = datetime.utcnow()
        idea.converted_by_id = current_user.id

        db.session.commit()

        flash(f'Idea convertita in progetto "{project.title}"!', 'success')
        return redirect(url_for('it_projects.detail', project_id=project.id))

    # GET: mostra form di conversione
    it_members = get_it_department_members()

    return render_template(
        'it_projects/ideas/convert.html',
        idea=idea,
        it_members=it_members,
        statuses=[
            ('planning', 'Pianificazione'),
            ('in_progress', 'In Corso'),
            ('review', 'In Review'),
            ('on_hold', 'In Pausa')
        ]
    )


@bp.route('/api/ideas/<int:idea_id>/update-status', methods=['POST'])
@csrf.exempt
@login_required
@admin_required
def ideas_update_status(idea_id):
    """API per aggiornare rapidamente lo stato dell'idea."""
    idea = ITIdea.query.get_or_404(idea_id)
    data = request.get_json()

    if 'status' in data:
        valid_statuses = ['pending', 'approved', 'rejected']
        if data['status'] in valid_statuses:
            idea.status = data['status']
            db.session.commit()
            return jsonify({
                'success': True,
                'status': idea.status,
                'status_label': idea.status_label,
                'status_color': idea.status_color
            })

    return jsonify({'success': False, 'error': 'Stato non valido'}), 400


# ============================================================================ #
#                         IT MANUALS - MANUALI E GUIDE                          #
# ============================================================================ #

PLATFORM_CONFIG = {
    'suite': {
        'name': 'Corposostenibile Suite',
        'description': 'Guide e manuali per utilizzare al meglio la piattaforma gestionale',
        'icon': 'ri-dashboard-line',
        'color': '#6366f1',
        'gradient': 'bg-gradient-end-1'
    },
    'ghl': {
        'name': 'Go High Level',
        'description': 'Tutorial e procedure per CRM, automazioni e funnel marketing',
        'icon': 'ri-rocket-line',
        'color': '#f59e0b',
        'gradient': 'bg-gradient-end-2'
    },
    'respond_io': {
        'name': 'Respond.io',
        'description': 'Guide per gestione conversazioni, workflow e integrazioni',
        'icon': 'ri-message-3-line',
        'color': '#10b981',
        'gradient': 'bg-gradient-end-3'
    },
    'loom': {
        'name': 'Loom',
        'description': 'Tutorial per registrazione video, condivisione e best practices',
        'icon': 'ri-video-line',
        'color': '#8b5cf6',
        'gradient': 'bg-gradient-end-4'
    }
}


def generate_slug(title: str) -> str:
    """Genera uno slug da un titolo."""
    import re
    slug = title.lower().strip()
    slug = re.sub(r'[àáâãäå]', 'a', slug)
    slug = re.sub(r'[èéêë]', 'e', slug)
    slug = re.sub(r'[ìíîï]', 'i', slug)
    slug = re.sub(r'[òóôõö]', 'o', slug)
    slug = re.sub(r'[ùúûü]', 'u', slug)
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')


@bp.route('/manuals')
@login_required
def manuals_index():
    """Pagina principale Manuali - Selezione piattaforma."""
    # Statistiche per ogni piattaforma
    platforms_stats = {}
    for platform_key in PLATFORM_CONFIG.keys():
        articles_count = ITManualArticle.query.filter_by(
            platform=platform_key,
            is_published=True
        ).count()
        categories_count = ITManualCategory.query.filter_by(
            platform=platform_key,
            is_active=True
        ).count()
        platforms_stats[platform_key] = {
            'articles': articles_count,
            'categories': categories_count
        }

    return render_template(
        'it_projects/manuals/index.html',
        platforms=PLATFORM_CONFIG,
        stats=platforms_stats
    )


@bp.route('/manuals/<platform>')
@login_required
def manuals_platform(platform):
    """Lista manuali per piattaforma specifica."""
    if platform not in PLATFORM_CONFIG:
        abort(404)

    platform_info = PLATFORM_CONFIG[platform]

    # Categorie con articoli
    categories = ITManualCategory.query.filter_by(
        platform=platform,
        is_active=True
    ).order_by(ITManualCategory.order_index).all()

    # Articoli in evidenza
    featured_articles = ITManualArticle.query.filter_by(
        platform=platform,
        is_published=True,
        is_featured=True
    ).order_by(ITManualArticle.order_index).limit(5).all()

    # Articoli senza categoria
    uncategorized = ITManualArticle.query.filter_by(
        platform=platform,
        is_published=True,
        category_id=None
    ).order_by(ITManualArticle.order_index).all()

    # Statistiche
    stats = {
        'total_articles': ITManualArticle.query.filter_by(platform=platform, is_published=True).count(),
        'total_categories': len(categories),
        'total_videos': ITManualArticle.query.filter(
            ITManualArticle.platform == platform,
            ITManualArticle.is_published == True,
            ITManualArticle.loom_url.isnot(None)
        ).count()
    }

    return render_template(
        'it_projects/manuals/platform.html',
        platform=platform,
        platform_info=platform_info,
        categories=categories,
        featured_articles=featured_articles,
        uncategorized=uncategorized,
        stats=stats
    )


@bp.route('/manuals/<platform>/article/<int:article_id>')
@bp.route('/manuals/<platform>/article/<int:article_id>/<slug>')
@login_required
def manuals_article(platform, article_id, slug=None):
    """Visualizza singolo articolo/guida."""
    if platform not in PLATFORM_CONFIG:
        abort(404)

    article = ITManualArticle.query.get_or_404(article_id)

    # Verifica che l'articolo appartenga alla piattaforma
    if article.platform != platform:
        abort(404)

    # Verifica pubblicazione (admin può vedere bozze)
    if not article.is_published and not current_user.is_admin:
        abort(404)

    # Incrementa visualizzazioni
    article.views_count += 1
    db.session.commit()

    # Articoli correlati (stessa categoria o piattaforma)
    related_query = ITManualArticle.query.filter(
        ITManualArticle.platform == platform,
        ITManualArticle.is_published == True,
        ITManualArticle.id != article.id
    )
    if article.category_id:
        related_query = related_query.filter(ITManualArticle.category_id == article.category_id)
    related_articles = related_query.limit(3).all()

    # Navigazione prev/next
    if article.category_id:
        prev_article = ITManualArticle.query.filter(
            ITManualArticle.category_id == article.category_id,
            ITManualArticle.is_published == True,
            ITManualArticle.order_index < article.order_index
        ).order_by(ITManualArticle.order_index.desc()).first()

        next_article = ITManualArticle.query.filter(
            ITManualArticle.category_id == article.category_id,
            ITManualArticle.is_published == True,
            ITManualArticle.order_index > article.order_index
        ).order_by(ITManualArticle.order_index.asc()).first()
    else:
        prev_article = None
        next_article = None

    return render_template(
        'it_projects/manuals/article.html',
        platform=platform,
        platform_info=PLATFORM_CONFIG[platform],
        article=article,
        related_articles=related_articles,
        prev_article=prev_article,
        next_article=next_article
    )


# ─────────────────────── ADMIN: GESTIONE MANUALI ─────────────────────── #

@bp.route('/manuals/admin')
@login_required
@admin_required
def manuals_admin():
    """Dashboard admin per gestione manuali."""
    # Statistiche generali
    stats = {
        'total_articles': ITManualArticle.query.count(),
        'published': ITManualArticle.query.filter_by(is_published=True).count(),
        'drafts': ITManualArticle.query.filter_by(is_published=False).count(),
        'total_categories': ITManualCategory.query.count(),
        'total_views': db.session.query(func.sum(ITManualArticle.views_count)).scalar() or 0
    }

    # Articoli recenti
    recent_articles = ITManualArticle.query.order_by(
        ITManualArticle.updated_at.desc()
    ).limit(10).all()

    # Articoli più visti
    popular_articles = ITManualArticle.query.filter_by(
        is_published=True
    ).order_by(ITManualArticle.views_count.desc()).limit(5).all()

    return render_template(
        'it_projects/manuals/admin/dashboard.html',
        stats=stats,
        recent_articles=recent_articles,
        popular_articles=popular_articles,
        platforms=PLATFORM_CONFIG
    )


@bp.route('/manuals/admin/articles')
@login_required
@admin_required
def manuals_admin_articles():
    """Lista tutti gli articoli (admin)."""
    platform_filter = request.args.get('platform', '')
    status_filter = request.args.get('status', '')

    query = ITManualArticle.query

    if platform_filter:
        query = query.filter(ITManualArticle.platform == platform_filter)
    if status_filter == 'published':
        query = query.filter(ITManualArticle.is_published == True)
    elif status_filter == 'draft':
        query = query.filter(ITManualArticle.is_published == False)

    articles = query.order_by(ITManualArticle.updated_at.desc()).all()

    return render_template(
        'it_projects/manuals/admin/articles_list.html',
        articles=articles,
        platforms=PLATFORM_CONFIG,
        current_filters={
            'platform': platform_filter,
            'status': status_filter
        }
    )


@bp.route('/manuals/admin/articles/new', methods=['GET', 'POST'])
@csrf.exempt
@login_required
@admin_required
def manuals_admin_article_new():
    """Crea nuovo articolo."""
    if request.method == 'POST':
        try:
            title = request.form.get('title', '').strip()
            platform = request.form.get('platform', '').strip()
            summary = request.form.get('summary', '').strip()
            content = request.form.get('content', '').strip()
            category_id = request.form.get('category_id', type=int)
            loom_url = request.form.get('loom_url', '').strip()
            is_published = request.form.get('is_published') == 'on'
            is_featured = request.form.get('is_featured') == 'on'

            if not title:
                flash('Il titolo è obbligatorio', 'error')
                return redirect(url_for('it_projects.manuals_admin_article_new'))

            if not platform or platform not in PLATFORM_CONFIG:
                flash('Seleziona una piattaforma valida', 'error')
                return redirect(url_for('it_projects.manuals_admin_article_new'))

            if not content:
                flash('Il contenuto è obbligatorio', 'error')
                return redirect(url_for('it_projects.manuals_admin_article_new'))

            # Genera slug unico
            base_slug = generate_slug(title)
            slug = base_slug
            counter = 1
            while ITManualArticle.query.filter_by(slug=slug).first():
                slug = f"{base_slug}-{counter}"
                counter += 1

            # Calcola order_index
            max_order = db.session.query(func.max(ITManualArticle.order_index)).filter(
                ITManualArticle.platform == platform,
                ITManualArticle.category_id == category_id
            ).scalar() or 0

            article = ITManualArticle(
                title=title,
                slug=slug,
                platform=platform,
                summary=summary,
                content=content,
                category_id=category_id if category_id else None,
                loom_url=loom_url if loom_url else None,
                is_published=is_published,
                is_featured=is_featured,
                published_at=datetime.utcnow() if is_published else None,
                author_id=current_user.id,
                order_index=max_order + 1
            )

            db.session.add(article)
            db.session.commit()

            flash(f'Articolo "{title}" creato con successo!', 'success')
            return redirect(url_for('it_projects.manuals_admin_article_edit', article_id=article.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Errore: {str(e)}', 'error')
            return redirect(url_for('it_projects.manuals_admin_article_new'))

    # GET: mostra form
    categories = ITManualCategory.query.filter_by(is_active=True).order_by(
        ITManualCategory.platform, ITManualCategory.order_index
    ).all()

    return render_template(
        'it_projects/manuals/admin/article_form.html',
        article=None,
        platforms=PLATFORM_CONFIG,
        categories=categories
    )


@bp.route('/manuals/admin/articles/<int:article_id>/edit', methods=['GET', 'POST'])
@csrf.exempt
@login_required
@admin_required
def manuals_admin_article_edit(article_id):
    """Modifica articolo esistente."""
    article = ITManualArticle.query.get_or_404(article_id)

    if request.method == 'POST':
        try:
            article.title = request.form.get('title', '').strip()
            article.platform = request.form.get('platform', '').strip()
            article.summary = request.form.get('summary', '').strip()
            article.content = request.form.get('content', '').strip()
            article.loom_url = request.form.get('loom_url', '').strip() or None

            category_id = request.form.get('category_id', type=int)
            article.category_id = category_id if category_id else None

            was_published = article.is_published
            article.is_published = request.form.get('is_published') == 'on'
            article.is_featured = request.form.get('is_featured') == 'on'

            # Se passa da bozza a pubblicato, imposta published_at
            if article.is_published and not was_published:
                article.published_at = datetime.utcnow()

            article.last_editor_id = current_user.id

            db.session.commit()
            flash('Articolo aggiornato!', 'success')
            return redirect(url_for('it_projects.manuals_admin_article_edit', article_id=article.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Errore: {str(e)}', 'error')

    categories = ITManualCategory.query.filter_by(is_active=True).order_by(
        ITManualCategory.platform, ITManualCategory.order_index
    ).all()

    return render_template(
        'it_projects/manuals/admin/article_form.html',
        article=article,
        platforms=PLATFORM_CONFIG,
        categories=categories
    )


@bp.route('/manuals/admin/articles/<int:article_id>/delete', methods=['POST'])
@csrf.exempt
@login_required
@admin_required
def manuals_admin_article_delete(article_id):
    """Elimina articolo."""
    article = ITManualArticle.query.get_or_404(article_id)
    title = article.title

    db.session.delete(article)
    db.session.commit()

    flash(f'Articolo "{title}" eliminato', 'success')
    return redirect(url_for('it_projects.manuals_admin_articles'))


# ─────────────────────── ADMIN: GESTIONE CATEGORIE ─────────────────────── #

@bp.route('/manuals/admin/categories')
@login_required
@admin_required
def manuals_admin_categories():
    """Lista categorie (admin)."""
    platform_filter = request.args.get('platform', '')

    query = ITManualCategory.query

    if platform_filter:
        query = query.filter(ITManualCategory.platform == platform_filter)

    categories = query.order_by(
        ITManualCategory.platform, ITManualCategory.order_index
    ).all()

    return render_template(
        'it_projects/manuals/admin/categories_list.html',
        categories=categories,
        platforms=PLATFORM_CONFIG,
        current_platform=platform_filter
    )


@bp.route('/manuals/admin/categories/new', methods=['GET', 'POST'])
@csrf.exempt
@login_required
@admin_required
def manuals_admin_category_new():
    """Crea nuova categoria."""
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            platform = request.form.get('platform', '').strip()
            description = request.form.get('description', '').strip()
            icon = request.form.get('icon', '').strip() or 'ri-folder-line'
            color = request.form.get('color', '').strip() or '#6c757d'

            if not name:
                flash('Il nome è obbligatorio', 'error')
                return redirect(url_for('it_projects.manuals_admin_category_new'))

            if not platform or platform not in PLATFORM_CONFIG:
                flash('Seleziona una piattaforma valida', 'error')
                return redirect(url_for('it_projects.manuals_admin_category_new'))

            # Calcola order_index
            max_order = db.session.query(func.max(ITManualCategory.order_index)).filter(
                ITManualCategory.platform == platform
            ).scalar() or 0

            category = ITManualCategory(
                name=name,
                platform=platform,
                description=description,
                icon=icon,
                color=color,
                order_index=max_order + 1
            )

            db.session.add(category)
            db.session.commit()

            flash(f'Categoria "{name}" creata!', 'success')
            return redirect(url_for('it_projects.manuals_admin_categories'))

        except Exception as e:
            db.session.rollback()
            flash(f'Errore: {str(e)}', 'error')

    return render_template(
        'it_projects/manuals/admin/category_form.html',
        category=None,
        platforms=PLATFORM_CONFIG
    )


@bp.route('/manuals/admin/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@csrf.exempt
@login_required
@admin_required
def manuals_admin_category_edit(category_id):
    """Modifica categoria."""
    category = ITManualCategory.query.get_or_404(category_id)

    if request.method == 'POST':
        try:
            category.name = request.form.get('name', '').strip()
            category.platform = request.form.get('platform', '').strip()
            category.description = request.form.get('description', '').strip()
            category.icon = request.form.get('icon', '').strip() or 'ri-folder-line'
            category.color = request.form.get('color', '').strip() or '#6c757d'
            category.is_active = request.form.get('is_active') == 'on'

            db.session.commit()
            flash('Categoria aggiornata!', 'success')
            return redirect(url_for('it_projects.manuals_admin_categories'))

        except Exception as e:
            db.session.rollback()
            flash(f'Errore: {str(e)}', 'error')

    return render_template(
        'it_projects/manuals/admin/category_form.html',
        category=category,
        platforms=PLATFORM_CONFIG
    )


@bp.route('/manuals/admin/categories/<int:category_id>/delete', methods=['POST'])
@csrf.exempt
@login_required
@admin_required
def manuals_admin_category_delete(category_id):
    """Elimina categoria."""
    category = ITManualCategory.query.get_or_404(category_id)
    name = category.name

    # Gli articoli verranno scollegati (category_id = NULL) grazie a ondelete="SET NULL"
    db.session.delete(category)
    db.session.commit()

    flash(f'Categoria "{name}" eliminata', 'success')
    return redirect(url_for('it_projects.manuals_admin_categories'))


# ─────────────────────── API MANUALI ─────────────────────── #

@bp.route('/api/manuals/categories/<platform>')
@login_required
def api_manuals_categories(platform):
    """API per ottenere categorie di una piattaforma (per select dinamiche)."""
    if platform not in PLATFORM_CONFIG:
        return jsonify([])

    categories = ITManualCategory.query.filter_by(
        platform=platform,
        is_active=True
    ).order_by(ITManualCategory.order_index).all()

    return jsonify([
        {'id': c.id, 'name': c.name}
        for c in categories
    ])
