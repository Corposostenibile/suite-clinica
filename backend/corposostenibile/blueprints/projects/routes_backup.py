"""
Routes per la gestione dei progetti di sviluppo.
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
    
    # Ordina per priorità e data
    projects = query.order_by(
        DevelopmentProject.priority.desc(),
        DevelopmentProject.estimated_end_date.asc()
    ).all()
    
    # Calcola statistiche
    stats = {
        'total': len(projects),
        'in_progress': len([p for p in projects if p.status == ProjectStatusEnum.in_progress]),
        'planning': len([p for p in projects if p.status == ProjectStatusEnum.planning]),
        'testing': len([p for p in projects if p.status == ProjectStatusEnum.testing]),
        'on_hold': len([p for p in projects if p.status == ProjectStatusEnum.on_hold]),
        'overdue': len([p for p in projects if p.is_overdue]),
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
    
    # Popola le scelte
    users = User.query.filter_by(is_active=True).order_by(User.first_name).all()
    form.project_manager_id.choices = [(u.id, u.full_name) for u in users]
    
    departments = Department.query.order_by(Department.name).all()
    form.department_id.choices = [(0, '--- Nessuno (progetto aziendale) ---')]
    form.department_id.choices.extend([(d.id, d.name) for d in departments])
    
    if form.validate_on_submit():
        project = DevelopmentProject(
            name=form.name.data,
            description=form.description.data,
            objective=form.objective.data,
            project_type=form.project_type.data,
            priority=form.priority.data,
            status=form.status.data,
            start_date=form.start_date.data,
            estimated_end_date=form.estimated_end_date.data,
            project_manager_id=form.project_manager_id.data,
            department_id=form.department_id.data if form.department_id.data != 0 else None,
            is_company_wide=form.is_company_wide.data,
            repository_url=form.repository_url.data or None,
            estimated_hours=form.estimated_hours.data,
            budget_allocated=form.budget_allocated.data,
            tags=json.loads(form.tags.data) if form.tags.data else []
        )
        
        db.session.add(project)
        db.session.commit()
        
        # Aggiungi il project manager come membro del team
        team_member = ProjectTeamMember(
            project_id=project.id,
            user_id=form.project_manager_id.data,
            role='Project Manager',
            allocation_percentage=100
        )
        db.session.add(team_member)
        
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
    
    # Default date
    if not form.start_date.data:
        form.start_date.data = date.today()
        form.estimated_end_date.data = date.today() + timedelta(days=30)
    
    return render_template('projects/form.html', form=form, title='Nuovo Progetto')


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
            'date': milestone.due_date.isoformat(),
            'title': milestone.name,
            'status': milestone.status.value,
            'assignee': milestone.assignee.full_name if milestone.assignee else 'Non assegnata',
            'progress': milestone.progress_percentage,
            'is_overdue': milestone.is_overdue
        })
    
    # Aggiungi updates alla timeline
    for update in project.updates[:10]:  # Ultimi 10 aggiornamenti
        timeline_data.append({
            'type': 'update',
            'date': update.created_at.date().isoformat(),
            'title': update.title,
            'content': update.content[:200] + '...' if len(update.content) > 200 else update.content,
            'author': update.author.full_name,
            'update_type': update.update_type,
            'is_important': update.is_important
        })
    
    # Ordina timeline per data
    timeline_data.sort(key=lambda x: x['date'], reverse=True)
    
    return render_template(
        'projects/detail.html',
        project=project,
        timeline_data=json.dumps(timeline_data)
    )


@bp.route('/<int:project_id>/edit', methods=['GET', 'POST'])
@it_department_required
def edit(project_id):
    """Modifica un progetto."""
    project = DevelopmentProject.query.get_or_404(project_id)
    form = ProjectForm(obj=project)
    
    # Popola le scelte
    users = User.query.filter_by(is_active=True).order_by(User.first_name).all()
    form.project_manager_id.choices = [(u.id, u.full_name) for u in users]
    
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
        project.start_date = form.start_date.data
        project.estimated_end_date = form.estimated_end_date.data
        project.project_manager_id = form.project_manager_id.data
        project.department_id = form.department_id.data if form.department_id.data != 0 else None
        project.is_company_wide = form.is_company_wide.data
        project.repository_url = form.repository_url.data or None
        project.estimated_hours = form.estimated_hours.data
        project.budget_allocated = form.budget_allocated.data
        
        if form.tags.data:
            project.tags = json.loads(form.tags.data)
        
        # Se lo stato è cambiato, aggiungi un aggiornamento
        if old_status != project.status:
            update = ProjectUpdate(
                project_id=project.id,
                author_id=current_user.id,
                update_type='status_change',
                title=f'Stato cambiato: {old_status} → {project.status}',
                content=f'Lo stato del progetto è passato da {old_status} a {project.status}',
                data={'old_status': old_status, 'new_status': project.status},
                is_important=True
            )
            db.session.add(update)
            
            # Se completato, imposta actual_end_date
            if project.status == ProjectStatusEnum.completed:
                project.actual_end_date = date.today()
        
        db.session.commit()
        
        flash('Progetto aggiornato con successo!', 'success')
        return redirect(url_for('projects.detail', project_id=project.id))
    
    # Pre-popola i tags
    if project.tags:
        form.tags.data = json.dumps(project.tags)
    
    return render_template('projects/form.html', form=form, title='Modifica Progetto', project=project)


@bp.route('/<int:project_id>/milestone/add', methods=['GET', 'POST'])
@it_department_required
def add_milestone(project_id):
    """Aggiungi una milestone al progetto."""
    project = DevelopmentProject.query.get_or_404(project_id)
    form = MilestoneForm()
    
    # Popola assegnee
    team_members = ProjectTeamMember.query.filter_by(
        project_id=project_id, 
        is_active=True
    ).all()
    form.assignee_id.choices = [(0, '--- Non assegnata ---')]
    form.assignee_id.choices.extend([
        (tm.user_id, tm.user.full_name) for tm in team_members
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
            progress_percentage=form.progress_percentage.data,
            notes=form.notes.data
        )
        
        # Parse JSON fields
        if form.deliverables.data:
            milestone.deliverables = json.loads(form.deliverables.data)
        if form.success_criteria.data:
            milestone.success_criteria = json.loads(form.success_criteria.data)
        if form.blockers.data:
            milestone.blockers = json.loads(form.blockers.data)
        
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
            is_important=form.is_important.data,
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
    
    # Ottieni utenti non già nel team
    existing_member_ids = [tm.user_id for tm in project.team_members]
    available_users = User.query.filter(
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
    milestone = ProjectMilestone.query.get_or_404(milestone_id)
    
    data = request.get_json()
    new_status = data.get('status')
    progress = data.get('progress', milestone.progress_percentage)
    
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
    
    overdue_projects = []
    for project in DevelopmentProject.query.filter(
        DevelopmentProject.status != ProjectStatusEnum.completed,
        DevelopmentProject.status != ProjectStatusEnum.cancelled
    ).all():
        if project.is_overdue:
            overdue_projects.append(project)
    
    # Progetti per dipartimento
    dept_stats = db.session.query(
        Department.name,
        db.func.count(DevelopmentProject.id)
    ).join(
        DevelopmentProject, Department.id == DevelopmentProject.department_id
    ).group_by(Department.name).all()
    
    # Progetti per tipo
    type_stats = db.session.query(
        DevelopmentProject.project_type,
        db.func.count(DevelopmentProject.id)
    ).group_by(DevelopmentProject.project_type).all()
    
    # Top contributors (più aggiornamenti)
    top_contributors = db.session.query(
        User.first_name,
        User.last_name,
        db.func.count(ProjectUpdate.id).label('updates_count')
    ).join(
        ProjectUpdate, User.id == ProjectUpdate.author_id
    ).group_by(User.id).order_by(db.text('updates_count DESC')).limit(10).all()
    
    return render_template(
        'projects/stats.html',
        total_projects=total_projects,
        active_projects=active_projects,
        overdue_projects=overdue_projects,
        dept_stats=dept_stats,
        type_stats=type_stats,
        top_contributors=top_contributors
    )