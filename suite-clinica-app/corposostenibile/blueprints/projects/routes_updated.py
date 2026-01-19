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

    # Escludi completati e cancellati se richiesto
    if not request.args.get('show_completed'):
        query = query.filter(DevelopmentProject.status != ProjectStatusEnum.completed)
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
        if form.milestones_data.data:
            try:
                milestones_data = json.loads(form.milestones_data.data)
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