"""
Routes per la gestione dei progetti di sviluppo - VERSIONE AGGIORNATA.
"""
from flask import render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
import json

from corposostenibile.extensions import db
from corposostenibile.models import (
    DevelopmentProject, ProjectMilestone, ProjectTeamMember,
    ProjectUpdate, User, Department,
    ProjectStatusEnum, ProjectPriorityEnum, MilestoneStatusEnum, ProjectTypeEnum
)
from . import bp
from .forms import (
    ProjectForm, MilestoneForm, ProjectUpdateForm,
    TeamMemberForm, ProjectFilterForm
)


def it_department_required(f):
    """Decorator per richiedere accesso al dipartimento IT (id=1) o admin."""
    from functools import wraps
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        # Permetti accesso se admin o membro del dipartimento IT (id=1)
        if not (current_user.is_admin or current_user.department_id == 1):
            flash('Accesso riservato al dipartimento IT.', 'warning')
            return redirect(url_for('welcome.index'))
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/')
@it_department_required
def dashboard():
    """Dashboard principale dei progetti."""
    # Form filtri
    filter_form = ProjectFilterForm()

    # Popola le scelte dei dipartimenti
    departments = Department.query.order_by(Department.name).all()
    filter_form.department_id.choices = [(0, 'Tutti i dipartimenti')]
    filter_form.department_id.choices.extend([(d.id, d.name) for d in departments])

    # Query base
    query = DevelopmentProject.query

    # Applica filtri
    if request.args.get('status'):
        query = query.filter_by(status=request.args.get('status'))

    if request.args.get('priority'):
        query = query.filter_by(priority=request.args.get('priority'))

    if request.args.get('project_type'):
        query = query.filter_by(project_type=request.args.get('project_type'))

    dept_id = request.args.get('department_id', type=int)
    if dept_id and dept_id > 0:
        query = query.filter_by(department_id=dept_id)

    # Escludi cancellati se non esplicitamente richiesto
    # Mostra sempre i completati, nascondi solo i cancellati di default
    if not request.args.get('show_cancelled'):
        query = query.filter(DevelopmentProject.status != ProjectStatusEnum.cancelled)

    # Ordina per priorità
    projects = query.order_by(
        DevelopmentProject.priority.desc()
    ).all()

    # Calcola statistiche
    stats = {
        'total': len(projects),
        'in_progress': len([p for p in projects if p.status == ProjectStatusEnum.in_progress]),
        'planning': len([p for p in projects if p.status == ProjectStatusEnum.planning]),
        'testing': len([p for p in projects if p.status == ProjectStatusEnum.testing]),
        'on_hold': len([p for p in projects if p.status == ProjectStatusEnum.on_hold]),
        'critical': len([p for p in projects if p.priority == ProjectPriorityEnum.critical])
    }

    # Aggiorna progresso per ogni progetto
    for project in projects:
        project.progress_percentage = project.calculate_progress()
        db.session.add(project)
    db.session.commit()

    return render_template(
        'projects/dashboard.html',
        projects=projects,
        stats=stats,
        filter_form=filter_form
    )


@bp.route('/create', methods=['GET', 'POST'])
@it_department_required
def create():
    """Crea un nuovo progetto."""
    form = ProjectForm()

    # Popola membri del team IT (dipartimento id=1)
    it_members = User.query.filter_by(
        department_id=1,
        is_active=True
    ).order_by(User.first_name).all()
    form.team_members.choices = [(u.id, u.full_name) for u in it_members]

    # Popola i dipartimenti
    departments = Department.query.order_by(Department.name).all()
    form.department_id.choices = [(0, '--- Nessuno (progetto aziendale) ---')]
    form.department_id.choices.extend([(d.id, d.name) for d in departments])

    if form.validate_on_submit():
        # Debug: mostra tutti i dati del form
        print(f"DEBUG: Form data received:")
        print(f"  - milestones_data: {form.milestones_data.data}")
        print(f"  - request.form milestones_data: {request.form.get('milestones_data')}")

        # Crea il progetto con Matteo Volpara (id=1) come project manager
        project = DevelopmentProject(
            name=form.name.data,
            description=form.description.data,
            objective=form.objective.data,
            project_type=form.project_type.data,
            priority=form.priority.data,
            status=form.status.data,
            project_manager_id=1,  # Matteo Volpara fisso
            department_id=form.department_id.data if form.department_id.data != 0 else None,
            is_company_wide=form.is_company_wide.data,
            repository_url=form.repository_url.data or None
        )

        db.session.add(project)
        db.session.flush()  # Per ottenere l'ID del progetto

        # Aggiungi Matteo Volpara come Project Manager
        pm_member = ProjectTeamMember(
            project_id=project.id,
            user_id=1,
            role='Project Manager',
            allocation_percentage=100
        )
        db.session.add(pm_member)

        # Aggiungi i membri del team selezionati
        for user_id in form.team_members.data:
            if user_id != 1:  # Evita duplicazione del PM
                team_member = ProjectTeamMember(
                    project_id=project.id,
                    user_id=user_id,
                    role='Developer',
                    allocation_percentage=100
                )
                db.session.add(team_member)

        # Gestisci le milestone se presenti
        milestones_json = form.milestones_data.data or request.form.get('milestones_data')
        if milestones_json and milestones_json != '':
            try:
                print(f"DEBUG: Milestones JSON received: {milestones_json}")
                milestones_data = json.loads(milestones_json)
                print(f"DEBUG: Parsed {len(milestones_data)} milestones")
                for idx, milestone_data in enumerate(milestones_data):
                    milestone = ProjectMilestone(
                        project_id=project.id,
                        name=milestone_data['name'],
                        description=milestone_data.get('description', ''),
                        due_date=datetime.strptime(milestone_data['due_date'], '%Y-%m-%d').date(),
                        order_index=idx,
                        assignee_id=milestone_data.get('assignee_id'),
                        status=MilestoneStatusEnum.pending
                    )
                    db.session.add(milestone)
                    print(f"DEBUG: Added milestone: {milestone.name} for date {milestone.due_date}")
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                flash(f'Errore nel processare le milestone: {e}', 'warning')

        # Aggiungi primo aggiornamento
        update = ProjectUpdate(
            project_id=project.id,
            author_id=current_user.id,
            update_type='status_change',
            title='Progetto creato',
            content=f'Il progetto "{project.name}" è stato creato.',
            data={'status': 'planning'},
            is_important=True
        )
        db.session.add(update)

        db.session.commit()

        # Debug: verifica milestone create
        milestone_count = ProjectMilestone.query.filter_by(project_id=project.id).count()
        print(f"DEBUG: Project {project.id} has {milestone_count} milestones after creation")

        flash(f'Progetto "{project.name}" creato con successo!', 'success')
        return redirect(url_for('projects.detail', project_id=project.id))

    return render_template('projects/form.html', form=form, title='Nuovo Progetto')


@bp.route('/<int:project_id>/edit', methods=['GET', 'POST'])
@it_department_required
def edit(project_id):
    """Modifica un progetto esistente."""
    project = DevelopmentProject.query.get_or_404(project_id)
    form = ProjectForm()

    # Popola membri del team IT (dipartimento id=1)
    it_members = User.query.filter_by(
        department_id=1,
        is_active=True
    ).order_by(User.first_name).all()
    form.team_members.choices = [(u.id, u.full_name) for u in it_members]

    # Popola i dipartimenti
    departments = Department.query.order_by(Department.name).all()
    form.department_id.choices = [(0, '--- Nessuno (progetto aziendale) ---')]
    form.department_id.choices.extend([(d.id, d.name) for d in departments])

    if form.validate_on_submit():
        old_status = project.status

        project.name = form.name.data
        project.description = form.description.data
        project.objective = form.objective.data
        project.project_type = form.project_type.data
        project.priority = form.priority.data
        project.status = form.status.data
        project.department_id = form.department_id.data if form.department_id.data != 0 else None
        project.is_company_wide = form.is_company_wide.data
        project.repository_url = form.repository_url.data or None

        # Gestisci membri del team
        # Rimuovi membri esistenti (tranne il PM)
        ProjectTeamMember.query.filter(
            ProjectTeamMember.project_id == project.id,
            ProjectTeamMember.role != 'Project Manager'
        ).delete()

        # Aggiungi nuovi membri
        for user_id in form.team_members.data:
            if user_id != 1:  # Evita duplicazione del PM
                team_member = ProjectTeamMember(
                    project_id=project.id,
                    user_id=user_id,
                    role='Developer',
                    allocation_percentage=100
                )
                db.session.add(team_member)

        # Gestisci le milestone
        milestones_json = form.milestones_data.data or request.form.get('milestones_data')
        if milestones_json and milestones_json != '':
            try:
                print(f"DEBUG EDIT: Milestones JSON received: {milestones_json}")
                milestones_data = json.loads(milestones_json)
                print(f"DEBUG EDIT: Parsed {len(milestones_data)} milestones")

                # Rimuovi le milestone esistenti
                ProjectMilestone.query.filter_by(project_id=project.id).delete()

                # Aggiungi le nuove milestone
                for idx, milestone_data in enumerate(milestones_data):
                    milestone = ProjectMilestone(
                        project_id=project.id,
                        name=milestone_data['name'],
                        description=milestone_data.get('description', ''),
                        due_date=datetime.strptime(milestone_data['due_date'], '%Y-%m-%d').date(),
                        order_index=idx,
                        assignee_id=milestone_data.get('assignee_id'),
                        status=MilestoneStatusEnum.pending
                    )
                    db.session.add(milestone)
                    print(f"DEBUG EDIT: Added milestone: {milestone.name} for date {milestone.due_date}")
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                flash(f'Errore nel processare le milestone: {e}', 'warning')
                print(f"DEBUG EDIT: Error processing milestones: {e}")

        # Se lo stato è cambiato, aggiungi un aggiornamento
        if old_status != project.status:
            update = ProjectUpdate(
                project_id=project.id,
                author_id=current_user.id,
                update_type='status_change',
                title='Stato progetto aggiornato',
                content=f'Stato cambiato da {old_status.value} a {project.status.value}',
                data={'old_status': old_status.value, 'new_status': project.status.value},
                is_important=True
            )
            db.session.add(update)

        db.session.commit()

        # Debug: verifica milestone dopo l'aggiornamento
        milestone_count = ProjectMilestone.query.filter_by(project_id=project.id).count()
        print(f"DEBUG EDIT: Project {project.id} has {milestone_count} milestones after update")

        flash('Progetto aggiornato con successo!', 'success')
        return redirect(url_for('projects.detail', project_id=project.id))

    elif request.method == 'GET':
        # Popola il form con i dati esistenti
        form.name.data = project.name
        form.description.data = project.description
        form.objective.data = project.objective
        form.project_type.data = project.project_type.value
        form.priority.data = project.priority.value
        form.status.data = project.status.value
        form.department_id.data = project.department_id or 0
        form.is_company_wide.data = project.is_company_wide
        form.repository_url.data = project.repository_url

        # Preseleziona i membri del team esistenti
        current_member_ids = [m.user_id for m in project.team_members if m.role != 'Project Manager']
        form.team_members.data = current_member_ids

    return render_template(
        'projects/form.html',
        form=form,
        title=f'Modifica Progetto: {project.name}',
        project=project
    )


@bp.route('/<int:project_id>/delete', methods=['POST'])
@it_department_required
def delete(project_id):
    """Elimina un progetto."""
    project = DevelopmentProject.query.get_or_404(project_id)

    # Solo admin o il project manager possono eliminare
    if not (current_user.is_admin or current_user.id == project.project_manager_id):
        flash('Non hai i permessi per eliminare questo progetto.', 'danger')
        return redirect(url_for('projects.detail', project_id=project_id))

    project_name = project.name

    # Elimina il progetto (le relazioni cascade elimineranno anche milestones, membri, updates)
    db.session.delete(project)
    db.session.commit()

    flash(f'Progetto "{project_name}" eliminato con successo.', 'info')
    return redirect(url_for('projects.dashboard'))


@bp.route('/<int:project_id>')
@it_department_required
def detail(project_id):
    """Vista dettaglio del progetto con timeline."""
    project = DevelopmentProject.query.get_or_404(project_id)

    # Debug: verifica milestone
    print(f"DEBUG: Project {project_id} has {len(project.milestones)} milestones")
    for m in project.milestones:
        print(f"  - Milestone: {m.name} (status: {m.status.value})")

    # Aggiorna progresso
    project.progress_percentage = project.calculate_progress()
    db.session.commit()

    # Prepara dati per la timeline
    timeline_data = []

    # Aggiungi milestones alla timeline
    for milestone in project.milestones:
        timeline_data.append({
            'type': 'milestone',
            'date': milestone.due_date.isoformat() if milestone.due_date else None,
            'title': milestone.name,
            'status': milestone.status.value,
            'assignee': milestone.assignee.full_name if milestone.assignee else 'Non assegnata',
            'progress': milestone.progress_percentage,
            'is_overdue': milestone.is_overdue if hasattr(milestone, 'is_overdue') else False
        })

    # Aggiungi updates alla timeline
    for update in project.updates[:10]:  # Ultimi 10 aggiornamenti
        timeline_data.append({
            'type': 'update',
            'date': update.created_at.date().isoformat(),
            'title': update.title,
            'content': update.content[:200],
            'author': update.author.full_name,
            'update_type': update.update_type
        })

    # Ordina timeline per data
    timeline_data.sort(key=lambda x: x['date'] if x['date'] else '', reverse=True)

    # Check permessi per modifiche
    can_edit = current_user.is_admin or current_user.id == project.project_manager_id or current_user.department_id == 1
    can_delete = current_user.is_admin or current_user.id == project.project_manager_id

    return render_template(
        'projects/detail.html',
        project=project,
        timeline_data=timeline_data,
        can_edit=can_edit,
        can_delete=can_delete
    )


@bp.route('/<int:project_id>/milestone/add', methods=['GET', 'POST'])
@it_department_required
def add_milestone(project_id):
    """Aggiungi una milestone al progetto."""
    project = DevelopmentProject.query.get_or_404(project_id)
    form = MilestoneForm()

    # Popola assegnee (solo membri del team IT)
    it_members = User.query.filter_by(
        department_id=1,
        is_active=True
    ).order_by(User.first_name).all()
    form.assignee_id.choices = [(0, '--- Non assegnata ---')]
    form.assignee_id.choices.extend([
        (u.id, u.full_name) for u in it_members
    ])

    if form.validate_on_submit():
        # Calcola order_index
        max_order = db.session.query(db.func.max(ProjectMilestone.order_index))\
            .filter_by(project_id=project_id).scalar() or 0

        milestone = ProjectMilestone(
            project_id=project_id,
            name=form.name.data,
            description=form.description.data,
            due_date=form.due_date.data,
            status=form.status.data,
            assignee_id=form.assignee_id.data if form.assignee_id.data != 0 else None,
            order_index=max_order + 1,
            progress_percentage=form.progress_percentage.data
        )

        # Parse JSON fields
        if form.deliverables.data:
            milestone.deliverables = json.loads(form.deliverables.data)
        if form.success_criteria.data:
            milestone.success_criteria = json.loads(form.success_criteria.data)

        db.session.add(milestone)

        # Aggiungi aggiornamento
        update = ProjectUpdate(
            project_id=project_id,
            author_id=current_user.id,
            update_type='milestone',
            title=f'Milestone aggiunta: {milestone.name}',
            content=f'Nuova milestone "{milestone.name}" con scadenza {milestone.due_date}',
            data={'milestone_name': milestone.name, 'due_date': milestone.due_date.isoformat()}
        )
        db.session.add(update)

        # Aggiorna progresso progetto
        db.session.commit()
        project.progress_percentage = project.calculate_progress()

        db.session.commit()

        flash('Milestone aggiunta con successo!', 'success')
        return redirect(url_for('projects.detail', project_id=project_id))

    return render_template('projects/milestone_form.html', form=form, project=project)


@bp.route('/<int:project_id>/update/add', methods=['GET', 'POST'])
@it_department_required
def add_update(project_id):
    """Aggiungi un aggiornamento al progetto."""
    project = DevelopmentProject.query.get_or_404(project_id)
    form = ProjectUpdateForm()

    if form.validate_on_submit():
        update = ProjectUpdate(
            project_id=project_id,
            author_id=current_user.id,
            update_type=form.update_type.data,
            title=form.title.data,
            content=form.content.data,
            is_public=form.is_public.data
        )

        db.session.add(update)
        db.session.commit()

        flash('Aggiornamento aggiunto con successo!', 'success')
        return redirect(url_for('projects.detail', project_id=project_id))

    return render_template('projects/update_form.html', form=form, project=project)


@bp.route('/<int:project_id>/team/add', methods=['GET', 'POST'])
@it_department_required
def add_team_member(project_id):
    """Aggiungi un membro al team del progetto."""
    project = DevelopmentProject.query.get_or_404(project_id)
    form = TeamMemberForm()

    # Ottieni utenti IT non già nel team
    existing_member_ids = [tm.user_id for tm in project.team_members]
    available_users = User.query.filter(
        User.department_id == 1,  # Solo dipartimento IT
        User.is_active == True,
        ~User.id.in_(existing_member_ids) if existing_member_ids else True
    ).order_by(User.first_name).all()

    form.user_id.choices = [(u.id, u.full_name) for u in available_users]

    if form.validate_on_submit():
        # Verifica che non sia già membro
        existing = ProjectTeamMember.query.filter_by(
            project_id=project_id,
            user_id=form.user_id.data
        ).first()

        if existing:
            flash('Questo utente è già nel team del progetto.', 'warning')
        else:
            member = ProjectTeamMember(
                project_id=project_id,
                user_id=form.user_id.data,
                role=form.role.data,
                allocation_percentage=form.allocation_percentage.data
            )

            db.session.add(member)

            # Aggiungi aggiornamento
            user = User.query.get(form.user_id.data)
            update = ProjectUpdate(
                project_id=project_id,
                author_id=current_user.id,
                update_type='progress',
                title=f'Nuovo membro del team',
                content=f'{user.full_name} si è unito al team come {form.role.data}'
            )
            db.session.add(update)

            db.session.commit()

            flash(f'{user.full_name} aggiunto al team!', 'success')

        return redirect(url_for('projects.detail', project_id=project_id))

    return render_template('projects/team_member_form.html', form=form, project=project)


@bp.route('/milestone/<int:milestone_id>/update', methods=['POST'])
@it_department_required
def update_milestone_status(milestone_id):
    """Aggiorna lo stato di una milestone (AJAX)."""
    print(f"DEBUG: Updating milestone {milestone_id}")
    print(f"DEBUG: Request method: {request.method}")
    print(f"DEBUG: Request data: {request.get_json()}")

    milestone = ProjectMilestone.query.get_or_404(milestone_id)

    data = request.get_json()
    new_status = data.get('status')
    progress = data.get('progress', milestone.progress_percentage)
    print(f"DEBUG: New status: {new_status}, Progress: {progress}")

    if new_status and new_status in [s.value for s in MilestoneStatusEnum]:
        old_status = milestone.status
        milestone.status = new_status
        milestone.progress_percentage = progress

        # Se completata, imposta data completamento
        if new_status == 'completed':
            milestone.completed_date = date.today()
            milestone.progress_percentage = 100

        # Aggiungi aggiornamento
        update = ProjectUpdate(
            project_id=milestone.project_id,
            author_id=current_user.id,
            update_type='milestone',
            title=f'Milestone "{milestone.name}" aggiornata',
            content=f'Stato: {old_status} → {new_status}, Progresso: {progress}%',
            data={'milestone_id': milestone.id, 'old_status': old_status, 'new_status': new_status}
        )
        db.session.add(update)

        # Aggiorna progresso progetto
        project = milestone.project
        project.progress_percentage = project.calculate_progress()

        db.session.commit()

        return jsonify({
            'success': True,
            'project_progress': project.progress_percentage
        })

    return jsonify({'success': False, 'error': 'Stato non valido'}), 400


@bp.route('/<int:project_id>/request-review', methods=['POST'])
@it_department_required
def request_review(project_id):
    """Richiedi una review per il progetto completato."""
    project = DevelopmentProject.query.get_or_404(project_id)

    # Verifica che tutte le milestone siano complete
    if not project.all_milestones_completed:
        flash('Devi completare tutte le milestone prima di richiedere una review.', 'warning')
        return redirect(url_for('projects.detail', project_id=project_id))

    # Ottieni i dati dal form
    branch_name = request.form.get('branch_name')
    developer_notes = request.form.get('developer_notes')

    # Aggiorna lo stato del progetto a "review"
    project.status = ProjectStatusEnum.review

    # Salva i dati della review request nel campo settings (JSONB)
    if not project.settings:
        project.settings = {}

    # Inizializza l'array delle review se non esiste
    if 'reviews' not in project.settings:
        project.settings['reviews'] = []

    # Aggiungi la nuova richiesta di review
    review_request = {
        'type': 'request',
        'requested_by': current_user.full_name,
        'requested_at': datetime.now().isoformat(),
        'branch_name': branch_name,
        'developer_notes': developer_notes,
        'iteration': len([r for r in project.settings.get('reviews', []) if r.get('type') == 'request']) + 1
    }
    project.settings['reviews'].append(review_request)

    # Mantieni compatibilità per template
    project.settings['review_request'] = review_request

    # IMPORTANTE: Segnala a SQLAlchemy che il campo JSONB è stato modificato
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(project, 'settings')

    # Aggiungi un aggiornamento
    update = ProjectUpdate(
        project_id=project_id,
        author_id=current_user.id,
        update_type='status_change',
        title='Richiesta Review',
        content=f'Review richiesta per il branch: {branch_name}',
        data={
            'status': 'review',
            'branch': branch_name,
            'notes': developer_notes
        },
        is_important=True
    )
    db.session.add(update)

    db.session.commit()

    flash('Richiesta di review inviata con successo al Project Manager!', 'success')
    return redirect(url_for('projects.detail', project_id=project_id))


@bp.route('/<int:project_id>/submit-review', methods=['POST'])
@it_department_required
def submit_review(project_id):
    """Il PM invia la sua review del progetto."""
    project = DevelopmentProject.query.get_or_404(project_id)

    # Solo il PM può fare la review
    if current_user.id != project.project_manager_id and not current_user.is_admin:
        flash('Solo il Project Manager può effettuare la review.', 'danger')
        return redirect(url_for('projects.detail', project_id=project_id))

    # Usa i nomi dei campi corretti dal form
    feedback = request.form.get('feedback', '')
    approved = request.form.get('approved', 'false')  # 'true' o 'false' come stringa

    if not project.settings:
        project.settings = {}

    # Inizializza l'array delle review se non esiste
    if 'reviews' not in project.settings:
        project.settings['reviews'] = []

    # Trova l'ultima richiesta di review a cui rispondere
    last_request_index = None
    for i in range(len(project.settings['reviews']) - 1, -1, -1):
        if project.settings['reviews'][i].get('type') == 'request':
            last_request_index = i
            break

    # Aggiungi la risposta alla review
    review_response = {
        'type': 'response',
        'reviewed_by': current_user.full_name,
        'reviewed_at': datetime.now().isoformat(),
        'feedback': feedback,
        'approved': approved == 'true',
        'response_to_iteration': project.settings['reviews'][last_request_index].get('iteration') if last_request_index is not None else 1
    }
    project.settings['reviews'].append(review_response)

    # Mantieni compatibilità per template
    project.settings['review_response'] = review_response

    # IMPORTANTE: Segnala a SQLAlchemy che il campo JSONB è stato modificato
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(project, 'settings')

    # Aggiorna lo stato del progetto
    if approved == 'true':
        project.status = ProjectStatusEnum.completed
        status_text = 'Progetto approvato e completato!'
    else:
        project.status = ProjectStatusEnum.in_progress
        status_text = 'Richieste modifiche al progetto.'

    # Aggiungi un aggiornamento
    feedback_preview = feedback[:200] + '...' if feedback and len(feedback) > 200 else feedback
    update = ProjectUpdate(
        project_id=project_id,
        author_id=current_user.id,
        update_type='completion' if approved == 'true' else 'blocker',
        title='Review Completata',
        content=f'{status_text}\n\nFeedback: {feedback_preview}' if feedback else status_text,
        data={
            'approved': approved == 'true',
            'feedback': feedback
        },
        is_important=True
    )
    db.session.add(update)

    db.session.commit()

    flash(f'Review completata. {status_text}', 'success')
    return redirect(url_for('projects.detail', project_id=project_id))


@bp.route('/stats')
@it_department_required
def stats():
    """Vista statistiche globali dei progetti."""
    # Raccogli statistiche
    total_projects = DevelopmentProject.query.count()
    active_projects = DevelopmentProject.query.filter(
        DevelopmentProject.status.in_([
            ProjectStatusEnum.in_progress,
            ProjectStatusEnum.testing,
            ProjectStatusEnum.review
        ])
    ).count()

    # Progetti per stato
    by_status = db.session.query(
        DevelopmentProject.status,
        db.func.count(DevelopmentProject.id)
    ).group_by(DevelopmentProject.status).all()

    # Progetti per priorità
    by_priority = db.session.query(
        DevelopmentProject.priority,
        db.func.count(DevelopmentProject.id)
    ).group_by(DevelopmentProject.priority).all()

    # Team members più attivi
    top_contributors = db.session.query(
        User,
        db.func.count(ProjectUpdate.id).label('updates_count')
    ).join(ProjectUpdate, User.id == ProjectUpdate.author_id)\
     .group_by(User.id)\
     .order_by(db.text('updates_count DESC'))\
     .limit(10).all()

    # Milestone in ritardo
    overdue_milestones = ProjectMilestone.query.filter(
        ProjectMilestone.due_date < date.today(),
        ProjectMilestone.status != MilestoneStatusEnum.completed,
        ProjectMilestone.status != MilestoneStatusEnum.cancelled
    ).count()

    stats_data = {
        'total_projects': total_projects,
        'active_projects': active_projects,
        'by_status': dict(by_status),
        'by_priority': dict(by_priority),
        'top_contributors': top_contributors,
        'overdue_milestones': overdue_milestones
    }

    return render_template('projects/stats.html', stats=stats_data)