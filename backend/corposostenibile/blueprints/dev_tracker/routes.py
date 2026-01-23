"""Routes for Dev Tracker"""
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import func, desc
from corposostenibile.extensions import db
from corposostenibile.models import (
    User, Department, DevWorkLog, DevCommit, DevCodeReview,
    DevSprint, DevSprintIntervention, BlueprintIntervention,
    WorkTypeEnum, CodeReviewStatusEnum, SprintStatusEnum, TaskStatusEnum
)
from . import bp
from .analytics import (
    get_developer_stats, get_team_stats, get_sprint_velocity,
    get_workload_distribution, get_recent_activity
)


@bp.route('/')
@login_required
def index():
    """Dashboard globale Dev Tracker."""
    # Se non admin, redirect a dashboard personale
    if not current_user.is_admin:
        return redirect(url_for('dev_tracker.developer_dashboard', user_id=current_user.id))

    # Dipartimento IT (ID = 1)
    it_department = Department.query.get(1)

    if not it_department:
        flash('Dipartimento IT non trovato', 'error')
        return redirect(url_for('main.index'))

    # Stats globali team
    team_stats = get_team_stats(it_department.id, days=30)

    # Team members
    team_members = User.query.filter_by(
        department_id=it_department.id,
        is_active=True
    ).order_by(User.first_name).all()

    # Workload distribution
    team_ids = [m.id for m in team_members]
    workload = get_workload_distribution(team_ids)

    # Sprint attivo
    active_sprint = db.session.query(DevSprint).filter(
        DevSprint.department_id == it_department.id,
        DevSprint.status == SprintStatusEnum.active
    ).first()

    # Velocity chart data
    velocity_data = get_sprint_velocity(it_department.id, sprint_count=5)

    # Interventions critici (bloccati o overdue)
    critical_interventions = db.session.query(BlueprintIntervention).filter(
        BlueprintIntervention.assigned_to_id.in_(team_ids),
        BlueprintIntervention.status == TaskStatusEnum.in_progress,
        BlueprintIntervention.blockers.isnot(None)
    ).order_by(BlueprintIntervention.due_date).limit(10).all()

    # Pending code reviews
    pending_reviews = db.session.query(DevCodeReview).filter(
        DevCodeReview.reviewer_id.in_(team_ids),
        DevCodeReview.status == CodeReviewStatusEnum.pending
    ).order_by(DevCodeReview.created_at).limit(10).all()

    return render_template(
        'dev_tracker/index.html',
        department=it_department,
        team_stats=team_stats,
        team_members=team_members,
        workload=workload,
        active_sprint=active_sprint,
        velocity_data=velocity_data,
        critical_interventions=critical_interventions,
        pending_reviews=pending_reviews
    )


@bp.route('/developer/<int:user_id>')
@login_required
def developer_dashboard(user_id):
    """Dashboard personale developer."""
    # Solo admin o se stesso
    if not current_user.is_admin and current_user.id != user_id:
        flash('Non hai permesso di vedere questa dashboard', 'error')
        return redirect(url_for('dev_tracker.index'))

    developer = User.query.get_or_404(user_id)

    # Stats 30 giorni
    stats_30d = get_developer_stats(user_id, days=30)

    # Stats 7 giorni
    stats_7d = get_developer_stats(user_id, days=7)

    # Interventions attivi
    active_interventions = db.session.query(BlueprintIntervention).filter(
        BlueprintIntervention.assigned_to_id == user_id,
        BlueprintIntervention.status.in_([TaskStatusEnum.todo, TaskStatusEnum.in_progress])
    ).order_by(BlueprintIntervention.due_date).all()

    # Interventions completati recenti
    completed_interventions = db.session.query(BlueprintIntervention).filter(
        BlueprintIntervention.assigned_to_id == user_id,
        BlueprintIntervention.status == TaskStatusEnum.done
    ).order_by(desc(BlueprintIntervention.completed_at)).limit(10).all()

    # Recent work logs
    recent_worklogs = db.session.query(DevWorkLog).filter(
        DevWorkLog.user_id == user_id
    ).order_by(desc(DevWorkLog.date)).limit(10).all()

    # Recent commits
    recent_commits = db.session.query(DevCommit).filter(
        DevCommit.user_id == user_id
    ).order_by(desc(DevCommit.committed_at)).limit(10).all()

    # Code reviews pending
    reviews_pending = db.session.query(DevCodeReview).filter(
        DevCodeReview.reviewer_id == user_id,
        DevCodeReview.status == CodeReviewStatusEnum.pending
    ).order_by(DevCodeReview.created_at).all()

    # Sprint corrente
    current_sprint = db.session.query(DevSprint).join(
        DevSprintIntervention
    ).join(BlueprintIntervention).filter(
        BlueprintIntervention.assigned_to_id == user_id,
        DevSprint.status == SprintStatusEnum.active
    ).first()

    # Recent activity
    recent_activity = get_recent_activity(user_id, limit=10)

    return render_template(
        'dev_tracker/developer_dashboard.html',
        developer=developer,
        stats_30d=stats_30d,
        stats_7d=stats_7d,
        active_interventions=active_interventions,
        completed_interventions=completed_interventions,
        recent_worklogs=recent_worklogs,
        recent_commits=recent_commits,
        reviews_pending=reviews_pending,
        current_sprint=current_sprint,
        recent_activity=recent_activity
    )


@bp.route('/team/<int:department_id>')
@login_required
def team_dashboard(department_id):
    """Dashboard team."""
    if not current_user.is_admin:
        flash('Solo admin possono vedere la dashboard team', 'error')
        return redirect(url_for('dev_tracker.index'))

    department = Department.query.get_or_404(department_id)

    # Team stats
    team_stats = get_team_stats(department_id, days=30)

    # Team members
    team_members = User.query.filter_by(
        department_id=department_id,
        is_active=True
    ).order_by(User.first_name).all()

    team_ids = [m.id for m in team_members]

    # Workload
    workload = get_workload_distribution(team_ids)

    # Velocity
    velocity_data = get_sprint_velocity(department_id, sprint_count=5)

    # Sprints attivi e prossimi
    active_sprints = db.session.query(DevSprint).filter(
        DevSprint.department_id == department_id,
        DevSprint.status == SprintStatusEnum.active
    ).order_by(DevSprint.start_date).all()

    upcoming_sprints = db.session.query(DevSprint).filter(
        DevSprint.department_id == department_id,
        DevSprint.status == SprintStatusEnum.planning
    ).order_by(DevSprint.start_date).limit(3).all()

    # Pending reviews
    pending_reviews = db.session.query(DevCodeReview).filter(
        DevCodeReview.reviewer_id.in_(team_ids),
        DevCodeReview.status == CodeReviewStatusEnum.pending
    ).order_by(DevCodeReview.created_at).limit(10).all()

    return render_template(
        'dev_tracker/team_dashboard.html',
        department=department,
        team_stats=team_stats,
        team_members=team_members,
        workload=workload,
        velocity_data=velocity_data,
        active_sprints=active_sprints,
        upcoming_sprints=upcoming_sprints,
        pending_reviews=pending_reviews
    )


# ═══════════════════════════════════════════════════════════════════════════
#                    🏃 SPRINT MANAGEMENT ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@bp.route('/sprint/create', methods=['GET', 'POST'])
@login_required
def create_sprint():
    """Crea nuovo sprint."""
    if not current_user.is_admin:
        flash('Solo gli admin possono creare sprint', 'error')
        return redirect(url_for('dev_tracker.index'))

    if request.method == 'POST':
        try:
            sprint = DevSprint(
                name=request.form['name'],
                description=request.form.get('description'),
                department_id=request.form.get('department_id', 1, type=int),
                start_date=datetime.strptime(request.form['start_date'], '%Y-%m-%d').date(),
                end_date=datetime.strptime(request.form['end_date'], '%Y-%m-%d').date(),
                goal=request.form.get('goal'),
                status=SprintStatusEnum[request.form.get('status', 'planning')]
            )
            db.session.add(sprint)
            db.session.commit()

            flash(f'Sprint "{sprint.name}" creato con successo', 'success')
            return redirect(url_for('dev_tracker.sprint_detail', sprint_id=sprint.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Errore: {str(e)}', 'error')

    departments = Department.query.all()
    return render_template('dev_tracker/sprint_form.html',
                         sprint=None,
                         departments=departments,
                         is_edit=False)


@bp.route('/sprint/<int:sprint_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_sprint(sprint_id):
    """Modifica sprint esistente."""
    if not current_user.is_admin:
        flash('Solo gli admin possono modificare sprint', 'error')
        return redirect(url_for('dev_tracker.index'))

    sprint = DevSprint.query.get_or_404(sprint_id)

    if request.method == 'POST':
        try:
            sprint.name = request.form['name']
            sprint.description = request.form.get('description')
            sprint.start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
            sprint.end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
            sprint.goal = request.form.get('goal')
            sprint.status = SprintStatusEnum[request.form['status']]

            db.session.commit()

            flash(f'Sprint "{sprint.name}" aggiornato', 'success')
            return redirect(url_for('dev_tracker.sprint_detail', sprint_id=sprint.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Errore: {str(e)}', 'error')

    departments = Department.query.all()
    return render_template('dev_tracker/sprint_form.html',
                         sprint=sprint,
                         departments=departments,
                         is_edit=True)


@bp.route('/sprint/<int:sprint_id>')
@login_required
def sprint_detail(sprint_id):
    """Pagina dettaglio completo sprint con gestione."""
    sprint = DevSprint.query.get_or_404(sprint_id)

    # Interventions dello sprint
    interventions = db.session.query(BlueprintIntervention, DevSprintIntervention).join(
        DevSprintIntervention
    ).filter(
        DevSprintIntervention.sprint_id == sprint_id
    ).all()

    # Raggruppa per status
    todo_interventions = [(i, si) for i, si in interventions if i.status == TaskStatusEnum.todo]
    in_progress_interventions = [(i, si) for i, si in interventions if i.status == TaskStatusEnum.in_progress]
    done_interventions = [(i, si) for i, si in interventions if i.status == TaskStatusEnum.done]

    # Team members per assegnazione
    team_members = User.query.filter_by(
        department_id=sprint.department_id,
        is_active=True
    ).order_by(User.first_name).all()

    # Available interventions (non ancora nello sprint)
    assigned_intervention_ids = [i.id for i, _ in interventions]
    available_interventions = BlueprintIntervention.query.filter(
        BlueprintIntervention.status != TaskStatusEnum.done,
        ~BlueprintIntervention.id.in_(assigned_intervention_ids) if assigned_intervention_ids else True
    ).order_by(BlueprintIntervention.created_at.desc()).limit(20).all()

    # Stats
    total_sp = sum(si.story_points for _, si in interventions)
    completed_sp = sum(si.story_points for i, si in done_interventions)

    return render_template('dev_tracker/sprint_detail.html',
                         sprint=sprint,
                         todo_interventions=todo_interventions,
                         in_progress_interventions=in_progress_interventions,
                         done_interventions=done_interventions,
                         team_members=team_members,
                         available_interventions=available_interventions,
                         total_sp=total_sp,
                         completed_sp=completed_sp)


@bp.route('/sprints/<int:sprint_id>')
@login_required
def sprint_board(sprint_id):
    """Sprint board Kanban."""
    sprint = DevSprint.query.get_or_404(sprint_id)

    # Interventions del sprint raggruppati per status
    interventions_query = db.session.query(
        BlueprintIntervention, DevSprintIntervention.story_points
    ).join(DevSprintIntervention).filter(
        DevSprintIntervention.sprint_id == sprint_id
    )

    todo = interventions_query.filter(
        BlueprintIntervention.status == TaskStatusEnum.todo
    ).all()

    in_progress = interventions_query.filter(
        BlueprintIntervention.status == TaskStatusEnum.in_progress
    ).all()

    done = interventions_query.filter(
        BlueprintIntervention.status == TaskStatusEnum.done
    ).all()

    # Stats sprint
    total_interventions = len(todo) + len(in_progress) + len(done)
    completed_count = len(done)
    completion_percentage = (completed_count / total_interventions * 100) if total_interventions > 0 else 0

    return render_template(
        'dev_tracker/sprint_board.html',
        sprint=sprint,
        todo=todo,
        in_progress=in_progress,
        done=done,
        total_interventions=total_interventions,
        completed_count=completed_count,
        completion_percentage=round(completion_percentage, 1)
    )


@bp.route('/worklog/add', methods=['GET', 'POST'])
@login_required
def add_worklog():
    """Form per aggiungere work log."""
    if request.method == 'POST':
        intervention_id = request.form.get('intervention_id') or None
        date_str = request.form.get('date')
        hours = request.form.get('hours_worked')
        description = request.form.get('description')
        work_type = request.form.get('work_type')

        # Validazione
        if not date_str or not hours or not work_type:
            flash('Data, ore e tipo di lavoro sono obbligatori', 'error')
            return redirect(url_for('dev_tracker.add_worklog'))

        try:
            log_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            hours_worked = float(hours)

            if hours_worked <= 0 or hours_worked > 24:
                flash('Ore non valide (deve essere tra 0 e 24)', 'error')
                return redirect(url_for('dev_tracker.add_worklog'))

            worklog = DevWorkLog(
                user_id=current_user.id,
                intervention_id=int(intervention_id) if intervention_id else None,
                date=log_date,
                hours_worked=hours_worked,
                description=description,
                work_type=WorkTypeEnum[work_type]
            )

            db.session.add(worklog)
            db.session.commit()

            flash(f'Work log aggiunto: {hours_worked}h su {log_date}', 'success')
            return redirect(url_for('dev_tracker.developer_dashboard', user_id=current_user.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Errore: {str(e)}', 'error')
            return redirect(url_for('dev_tracker.add_worklog'))

    # GET - mostra form
    # My active interventions per select
    my_interventions = db.session.query(BlueprintIntervention).filter(
        BlueprintIntervention.assigned_to_id == current_user.id,
        BlueprintIntervention.status.in_([TaskStatusEnum.todo, TaskStatusEnum.in_progress])
    ).order_by(BlueprintIntervention.title).all()

    return render_template(
        'dev_tracker/worklog_form.html',
        my_interventions=my_interventions,
        work_types=WorkTypeEnum
    )


@bp.route('/commit/add', methods=['GET', 'POST'])
@login_required
def add_commit():
    """Form per aggiungere commit manuale."""
    if request.method == 'POST':
        intervention_id = request.form.get('intervention_id')
        commit_hash = request.form.get('commit_hash')
        commit_message = request.form.get('commit_message')
        branch = request.form.get('branch')
        files_changed = request.form.get('files_changed') or None
        additions = request.form.get('additions') or None
        deletions = request.form.get('deletions') or None
        github_url = request.form.get('github_url') or None

        if not intervention_id or not commit_message:
            flash('Intervention e commit message sono obbligatori', 'error')
            return redirect(url_for('dev_tracker.add_commit'))

        try:
            commit = DevCommit(
                intervention_id=int(intervention_id),
                user_id=current_user.id,
                commit_hash=commit_hash,
                commit_message=commit_message,
                branch=branch,
                files_changed=int(files_changed) if files_changed else None,
                additions=int(additions) if additions else None,
                deletions=int(deletions) if deletions else None,
                github_url=github_url,
                committed_at=datetime.utcnow()
            )

            db.session.add(commit)
            db.session.commit()

            flash('Commit aggiunto con successo', 'success')
            return redirect(url_for('dev_tracker.developer_dashboard', user_id=current_user.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Errore: {str(e)}', 'error')
            return redirect(url_for('dev_tracker.add_commit'))

    # GET
    my_interventions = db.session.query(BlueprintIntervention).filter(
        BlueprintIntervention.assigned_to_id == current_user.id,
        BlueprintIntervention.status.in_([TaskStatusEnum.todo, TaskStatusEnum.in_progress])
    ).order_by(BlueprintIntervention.title).all()

    return render_template(
        'dev_tracker/commit_form.html',
        my_interventions=my_interventions
    )


@bp.route('/intervention/<int:intervention_id>')
@login_required
def intervention_detail(intervention_id):
    """Pagina dettaglio completo intervention."""
    intervention = BlueprintIntervention.query.get_or_404(intervention_id)

    # Work logs
    worklogs = db.session.query(DevWorkLog).filter(
        DevWorkLog.intervention_id == intervention_id
    ).order_by(desc(DevWorkLog.date)).all()

    # Commits
    commits = db.session.query(DevCommit).filter(
        DevCommit.intervention_id == intervention_id
    ).order_by(desc(DevCommit.committed_at)).all()

    # Code reviews
    code_reviews = db.session.query(DevCodeReview).filter(
        DevCodeReview.intervention_id == intervention_id
    ).order_by(desc(DevCodeReview.created_at)).all()

    # Sprint assignments
    sprint_assignments = db.session.query(DevSprint, DevSprintIntervention).join(
        DevSprintIntervention
    ).filter(
        DevSprintIntervention.intervention_id == intervention_id
    ).all()

    # Total hours
    total_hours = db.session.query(func.sum(DevWorkLog.hours_worked)).filter(
        DevWorkLog.intervention_id == intervention_id
    ).scalar() or 0

    # Team members (per assegnazione)
    team_members = User.query.filter_by(
        department_id=1,  # IT department
        is_active=True
    ).order_by(User.first_name).all()

    # Active sprints (per assegnazione)
    active_sprints = DevSprint.query.filter(
        DevSprint.status.in_([SprintStatusEnum.planning, SprintStatusEnum.active])
    ).order_by(desc(DevSprint.start_date)).all()

    return render_template('dev_tracker/intervention_detail.html',
                         intervention=intervention,
                         worklogs=worklogs,
                         commits=commits,
                         code_reviews=code_reviews,
                         sprint_assignments=sprint_assignments,
                         total_hours=total_hours,
                         team_members=team_members,
                         active_sprints=active_sprints)


@bp.route('/intervention/<int:intervention_id>/timeline')
@login_required
def intervention_timeline(intervention_id):
    """Timeline dettagliata di un intervention."""
    intervention = BlueprintIntervention.query.get_or_404(intervention_id)

    # Work logs
    worklogs = db.session.query(DevWorkLog).filter(
        DevWorkLog.intervention_id == intervention_id
    ).order_by(DevWorkLog.date).all()

    # Commits
    commits = db.session.query(DevCommit).filter(
        DevCommit.intervention_id == intervention_id
    ).order_by(DevCommit.committed_at).all()

    # Code reviews
    code_reviews = db.session.query(DevCodeReview).filter(
        DevCodeReview.intervention_id == intervention_id
    ).order_by(DevCodeReview.created_at).all()

    # Sprint assignments
    sprint_assignments = db.session.query(DevSprint, DevSprintIntervention).join(
        DevSprintIntervention
    ).filter(
        DevSprintIntervention.intervention_id == intervention_id
    ).all()

    # Total hours
    total_hours = db.session.query(func.sum(DevWorkLog.hours_worked)).filter(
        DevWorkLog.intervention_id == intervention_id
    ).scalar() or 0

    # Total commits
    total_commits = len(commits)

    return render_template(
        'dev_tracker/intervention_timeline.html',
        intervention=intervention,
        worklogs=worklogs,
        commits=commits,
        code_reviews=code_reviews,
        sprint_assignments=sprint_assignments,
        total_hours=float(total_hours),
        total_commits=total_commits
    )


# ═══════════════════════════════════════════════════════════════════════════
#               🔧 INTERVENTION MANAGEMENT ROUTES
# ═══════════════════════════════════════════════════════════════════════════

@bp.route('/intervention/<int:intervention_id>/update-status', methods=['POST'])
@login_required
def update_intervention_status(intervention_id):
    """Aggiorna status di un intervention."""
    intervention = BlueprintIntervention.query.get_or_404(intervention_id)

    new_status = request.form.get('status')
    progress = request.form.get('progress_percentage', type=int)

    try:
        if new_status:
            intervention.status = TaskStatusEnum[new_status]
        if progress is not None:
            intervention.progress_percentage = max(0, min(100, progress))

        # Se completato, setta completed_at
        if intervention.status == TaskStatusEnum.done and not intervention.completed_at:
            intervention.completed_at = datetime.utcnow()

        db.session.commit()
        flash('Status aggiornato con successo', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Errore: {str(e)}', 'error')

    return redirect(url_for('dev_tracker.intervention_detail', intervention_id=intervention_id))


@bp.route('/intervention/<int:intervention_id>/assign', methods=['POST'])
@login_required
def assign_intervention(intervention_id):
    """Assegna un intervention a un developer."""
    intervention = BlueprintIntervention.query.get_or_404(intervention_id)

    user_id = request.form.get('assigned_to_id', type=int)

    try:
        intervention.assigned_to_id = user_id if user_id else None
        db.session.commit()
        flash('Assegnazione aggiornata con successo', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Errore: {str(e)}', 'error')

    return redirect(url_for('dev_tracker.intervention_detail', intervention_id=intervention_id))


@bp.route('/intervention/<int:intervention_id>/add-to-sprint', methods=['POST'])
@login_required
def add_intervention_to_sprint(intervention_id):
    """Aggiungi intervention a uno sprint."""
    intervention = BlueprintIntervention.query.get_or_404(intervention_id)

    sprint_id = request.form.get('sprint_id', type=int)
    story_points = request.form.get('story_points', 0, type=int)

    if not sprint_id:
        flash('Seleziona uno sprint', 'error')
        return redirect(url_for('dev_tracker.intervention_detail', intervention_id=intervention_id))

    try:
        # Verifica se già assegnato
        existing = DevSprintIntervention.query.filter_by(
            sprint_id=sprint_id,
            intervention_id=intervention_id
        ).first()

        if existing:
            flash('Intervention già assegnato a questo sprint', 'warning')
        else:
            assignment = DevSprintIntervention(
                sprint_id=sprint_id,
                intervention_id=intervention_id,
                story_points=story_points
            )
            db.session.add(assignment)

            # Aggiorna total_story_points dello sprint
            sprint = DevSprint.query.get(sprint_id)
            if sprint:
                sprint.total_story_points = (sprint.total_story_points or 0) + story_points

            db.session.commit()
            flash('Intervention aggiunto allo sprint', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Errore: {str(e)}', 'error')

    return redirect(url_for('dev_tracker.intervention_detail', intervention_id=intervention_id))


@bp.route('/intervention/<int:intervention_id>/update-notes', methods=['POST'])
@login_required
def update_intervention_notes(intervention_id):
    """Aggiorna note o blockers di un intervention."""
    intervention = BlueprintIntervention.query.get_or_404(intervention_id)

    notes = request.form.get('notes')
    blockers = request.form.get('blockers')

    try:
        if notes is not None:
            intervention.notes = notes
        if blockers is not None:
            intervention.blockers = blockers

        db.session.commit()
        flash('Note aggiornate con successo', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Errore: {str(e)}', 'error')

    return redirect(url_for('dev_tracker.intervention_detail', intervention_id=intervention_id))


@bp.route('/analytics')
@login_required
def analytics():
    """Analytics dashboard avanzata."""
    if not current_user.is_admin:
        flash('Solo admin possono vedere analytics', 'error')
        return redirect(url_for('dev_tracker.index'))

    # Department IT
    it_department = Department.query.get(1)
    if not it_department:
        flash('Dipartimento IT non trovato', 'error')
        return redirect(url_for('dev_tracker.index'))

    team_members = User.query.filter_by(
        department_id=it_department.id,
        is_active=True
    ).all()

    team_ids = [m.id for m in team_members]

    # Developer performance comparison
    developer_performance = []
    for member in team_members:
        stats = get_developer_stats(member.id, days=30)
        developer_performance.append({
            'user_id': member.id,
            'name': f"{member.first_name} {member.last_name}",
            'total_hours': stats['total_hours'],
            'total_commits': stats['total_commits'],
            'completed_interventions': stats['completed_interventions'],
            'reviews_given': stats['reviews_given'],
        })

    # Velocity trend
    velocity_data = get_sprint_velocity(it_department.id, sprint_count=10)

    # Hours by work type (team aggregate)
    hours_by_type = db.session.query(
        DevWorkLog.work_type,
        func.sum(DevWorkLog.hours_worked)
    ).filter(
        DevWorkLog.user_id.in_(team_ids),
        DevWorkLog.date >= date.today() - timedelta(days=30)
    ).group_by(DevWorkLog.work_type).all()

    hours_breakdown = {wt.value: 0 for wt in WorkTypeEnum}
    for work_type, hours in hours_by_type:
        hours_breakdown[work_type.value] = float(hours or 0)

    return render_template(
        'dev_tracker/analytics.html',
        department=it_department,
        developer_performance=developer_performance,
        velocity_data=velocity_data,
        hours_breakdown=hours_breakdown
    )


# ═════════════════════ API ENDPOINTS (JSON) ═════════════════════

@bp.route('/api/developer/<int:user_id>/stats')
@login_required
def api_developer_stats(user_id):
    """API: Stats developer."""
    if not current_user.is_admin and current_user.id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    days = request.args.get('days', 30, type=int)
    stats = get_developer_stats(user_id, days=days)
    return jsonify(stats)


@bp.route('/api/team/<int:department_id>/stats')
@login_required
def api_team_stats(department_id):
    """API: Stats team."""
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    days = request.args.get('days', 30, type=int)
    stats = get_team_stats(department_id, days=days)
    return jsonify(stats)


@bp.route('/api/sprint/<int:sprint_id>/velocity')
@login_required
def api_sprint_velocity(sprint_id):
    """API: Sprint velocity."""
    sprint = DevSprint.query.get_or_404(sprint_id)
    velocity_data = get_sprint_velocity(sprint.department_id, sprint_count=5)
    return jsonify(velocity_data)
