"""Routes principali Blueprint Registry"""
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, desc
from datetime import datetime, timedelta, date

from corposostenibile.extensions import db
from corposostenibile.models import (
    BlueprintRegistry, BlueprintIssue, BlueprintImprovement, BlueprintIntervention,
    User, Department,
    BlueprintStatusEnum, AdoptionLevelEnum, IssueSeverityEnum, TaskStatusEnum
)
from . import bp
from .metrics import calculate_adoption_metrics, get_metrics_history_30d


@bp.route('/')
@login_required
def index():
    """Dashboard principale Blueprint Registry."""
    # Parametro per mostrare/nascondere blueprint archived
    show_hidden = request.args.get('show_hidden', 'false').lower() == 'true'

    # Query base
    query = BlueprintRegistry.query

    # Filtra blueprint nascosti (archived) se show_hidden=False
    if not show_hidden:
        query = query.filter(BlueprintRegistry.status != BlueprintStatusEnum.archived)

    blueprints = query.order_by(BlueprintRegistry.name).all()

    # Conta blueprint nascosti
    hidden_count = BlueprintRegistry.query.filter_by(status=BlueprintStatusEnum.archived).count()

    # Statistiche generali (solo blueprint visibili)
    stats = {
        'total': len(blueprints),
        'active': sum(1 for b in blueprints if b.status == BlueprintStatusEnum.active),
        'beta': sum(1 for b in blueprints if b.status == BlueprintStatusEnum.beta),
        'deprecated': sum(1 for b in blueprints if b.status == BlueprintStatusEnum.deprecated),
        'hidden': hidden_count,
        'total_issues': BlueprintIssue.query.filter_by(status='open').count(),
        'critical_issues': BlueprintIssue.query.filter_by(
            status='open', severity='critical'
        ).count(),
        'in_progress_interventions': BlueprintIntervention.query.filter_by(
            status='in_progress'
        ).count()
    }

    return render_template('blueprint_registry/index.html',
                         blueprints=blueprints, stats=stats, show_hidden=show_hidden)


@bp.route('/<string:code>')
@login_required
def detail(code):
    """Dettaglio blueprint."""
    blueprint = BlueprintRegistry.query.filter_by(code=code).first_or_404()

    # Issues aperte
    issues = BlueprintIssue.query.filter_by(
        blueprint_id=blueprint.id
    ).order_by(desc(BlueprintIssue.severity), desc(BlueprintIssue.created_at)).limit(10).all()

    # Improvements
    improvements = BlueprintImprovement.query.filter_by(
        blueprint_id=blueprint.id
    ).order_by(desc(BlueprintImprovement.priority)).limit(10).all()

    # Interventions attivi
    interventions = BlueprintIntervention.query.filter_by(
        blueprint_id=blueprint.id,
        status='in_progress'
    ).order_by(desc(BlueprintIntervention.created_at)).all()

    # Metriche correnti (calcola al volo)
    current_metrics = calculate_adoption_metrics(code)

    # Dati storici per chart (ultimi 30 giorni)
    chart_data = get_metrics_history_30d(code)

    return render_template('blueprint_registry/detail.html',
                         blueprint=blueprint,
                         issues=issues,
                         improvements=improvements,
                         interventions=interventions,
                         current_metrics=current_metrics,
                         chart_data=chart_data)


@bp.route('/<string:code>/issues/add', methods=['POST'])
@login_required
def add_issue(code):
    """Aggiungi issue."""
    blueprint = BlueprintRegistry.query.filter_by(code=code).first_or_404()

    issue = BlueprintIssue(
        blueprint_id=blueprint.id,
        title=request.form['title'],
        description=request.form.get('description'),
        severity=request.form.get('severity', 'minor'),
        reported_by_id=current_user.id
    )
    db.session.add(issue)
    db.session.commit()

    flash('Issue aggiunta con successo', 'success')
    return redirect(url_for('blueprint_registry.detail', code=code))


@bp.route('/<string:code>/improvements/add', methods=['POST'])
@login_required
def add_improvement(code):
    """Aggiungi improvement."""
    blueprint = BlueprintRegistry.query.filter_by(code=code).first_or_404()

    improvement = BlueprintImprovement(
        blueprint_id=blueprint.id,
        title=request.form['title'],
        description=request.form.get('description'),
        priority=request.form.get('priority', 'medium'),
        proposed_by_id=current_user.id
    )
    db.session.add(improvement)
    db.session.commit()

    flash('Idea di miglioramento aggiunta', 'success')
    return redirect(url_for('blueprint_registry.detail', code=code))


@bp.route('/<string:code>/interventions/add', methods=['POST'])
@login_required
def add_intervention(code):
    """Aggiungi intervento."""
    blueprint = BlueprintRegistry.query.filter_by(code=code).first_or_404()

    intervention = BlueprintIntervention(
        blueprint_id=blueprint.id,
        title=request.form['title'],
        description=request.form.get('description'),
        intervention_type=request.form.get('intervention_type'),
        assigned_to_id=request.form.get('assigned_to_id')
    )
    db.session.add(intervention)
    db.session.commit()

    flash('Intervento creato', 'success')
    return redirect(url_for('blueprint_registry.detail', code=code))


@bp.route('/<string:code>/toggle-visibility', methods=['POST'])
@login_required
def toggle_visibility(code):
    """Toggle visibility blueprint (active <-> archived)."""
    blueprint = BlueprintRegistry.query.filter_by(code=code).first_or_404()

    # Toggle tra active e archived
    if blueprint.status == BlueprintStatusEnum.archived:
        blueprint.status = BlueprintStatusEnum.active
        flash(f'Blueprint "{blueprint.name}" è ora visibile', 'success')
    else:
        blueprint.status = BlueprintStatusEnum.archived
        flash(f'Blueprint "{blueprint.name}" è stato nascosto', 'info')

    db.session.commit()

    return redirect(url_for('blueprint_registry.index'))


@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Crea nuovo blueprint."""
    # Solo admin possono creare blueprint
    if not current_user.is_admin:
        flash('Solo gli admin possono creare blueprint', 'error')
        return redirect(url_for('blueprint_registry.index'))

    if request.method == 'POST':
        code = request.form.get('code')
        name = request.form.get('name')
        description = request.form.get('description')
        status = request.form.get('status', 'active')
        adoption_level = request.form.get('adoption_level', 'none')
        owner_id = request.form.get('owner_id') or None
        department_id = request.form.get('department_id') or 1  # Default IT
        readme_url = request.form.get('readme_url') or None
        current_version = request.form.get('current_version') or None

        # Validazione
        if not code or not name:
            flash('Code e Name sono obbligatori', 'error')
            return redirect(url_for('blueprint_registry.create'))

        # Verifica che il code non esista già
        existing = BlueprintRegistry.query.filter_by(code=code).first()
        if existing:
            flash(f'Blueprint con code "{code}" già esistente', 'error')
            return redirect(url_for('blueprint_registry.create'))

        try:
            blueprint = BlueprintRegistry(
                code=code,
                name=name,
                description=description,
                status=BlueprintStatusEnum[status],
                adoption_level=AdoptionLevelEnum[adoption_level],
                owner_id=int(owner_id) if owner_id else None,
                department_id=int(department_id),
                readme_url=readme_url,
                current_version=current_version,
                last_major_update=datetime.utcnow()
            )

            db.session.add(blueprint)
            db.session.commit()

            flash(f'Blueprint "{name}" creato con successo', 'success')
            return redirect(url_for('blueprint_registry.detail', code=code))

        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante la creazione: {str(e)}', 'error')
            return redirect(url_for('blueprint_registry.create'))

    # GET - mostra form
    users = User.query.filter_by(is_active=True).order_by(User.first_name).all()
    departments = Department.query.order_by(Department.name).all()

    return render_template('blueprint_registry/form.html',
                         blueprint=None,
                         users=users,
                         departments=departments,
                         statuses=BlueprintStatusEnum,
                         adoption_levels=AdoptionLevelEnum,
                         is_edit=False)


@bp.route('/<string:code>/edit', methods=['GET', 'POST'])
@login_required
def edit(code):
    """Modifica blueprint esistente."""
    # Solo admin possono modificare blueprint
    if not current_user.is_admin:
        flash('Solo gli admin possono modificare blueprint', 'error')
        return redirect(url_for('blueprint_registry.index'))

    blueprint = BlueprintRegistry.query.filter_by(code=code).first_or_404()

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        status = request.form.get('status')
        adoption_level = request.form.get('adoption_level')
        owner_id = request.form.get('owner_id') or None
        department_id = request.form.get('department_id') or 1
        readme_url = request.form.get('readme_url') or None
        current_version = request.form.get('current_version') or None

        # Validazione
        if not name:
            flash('Name è obbligatorio', 'error')
            return redirect(url_for('blueprint_registry.edit', code=code))

        try:
            blueprint.name = name
            blueprint.description = description
            blueprint.status = BlueprintStatusEnum[status]
            blueprint.adoption_level = AdoptionLevelEnum[adoption_level]
            blueprint.owner_id = int(owner_id) if owner_id else None
            blueprint.department_id = int(department_id)
            blueprint.readme_url = readme_url
            blueprint.current_version = current_version
            blueprint.last_major_update = datetime.utcnow()

            db.session.commit()

            flash(f'Blueprint "{name}" aggiornato con successo', 'success')
            return redirect(url_for('blueprint_registry.detail', code=code))

        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante l\'aggiornamento: {str(e)}', 'error')
            return redirect(url_for('blueprint_registry.edit', code=code))

    # GET - mostra form
    users = User.query.filter_by(is_active=True).order_by(User.first_name).all()
    departments = Department.query.order_by(Department.name).all()

    return render_template('blueprint_registry/form.html',
                         blueprint=blueprint,
                         users=users,
                         departments=departments,
                         statuses=BlueprintStatusEnum,
                         adoption_levels=AdoptionLevelEnum,
                         is_edit=True)


# ═══════════════════════════════════════════════════════════════════════════
#                    🔗 INTEGRAZIONE DEV TRACKER
# ═══════════════════════════════════════════════════════════════════════════

@bp.route('/<string:code>/issues/<int:issue_id>/convert-to-intervention', methods=['POST'])
@login_required
def convert_issue_to_intervention(code, issue_id):
    """Converte un Issue in Intervention per tracciamento nel Dev Tracker."""
    blueprint = BlueprintRegistry.query.filter_by(code=code).first_or_404()
    issue = BlueprintIssue.query.filter_by(id=issue_id, blueprint_id=blueprint.id).first_or_404()

    # Verifica che l'issue non abbia già un intervention collegato
    if issue.intervention_id:
        flash('Questo issue è già collegato a un intervention', 'warning')
        return redirect(url_for('blueprint_registry.detail', code=code))

    try:
        # Crea nuovo intervention
        intervention = BlueprintIntervention(
            blueprint_id=blueprint.id,
            title=f"Fix: {issue.title}",
            description=issue.description or "",
            intervention_type='bugfix',
            status=TaskStatusEnum.todo,
            assigned_to_id=issue.assigned_to_id or current_user.id,
            progress_percentage=0
        )
        db.session.add(intervention)
        db.session.flush()  # Get intervention ID

        # Collega issue a intervention
        issue.intervention_id = intervention.id

        db.session.commit()

        flash(f'Intervention creato con successo per issue "{issue.title}"', 'success')
        return redirect(url_for('dev_tracker.intervention_detail', intervention_id=intervention.id))

    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante la creazione dell\'intervention: {str(e)}', 'error')
        return redirect(url_for('blueprint_registry.detail', code=code))


@bp.route('/<string:code>/improvements/<int:improvement_id>/convert-to-intervention', methods=['POST'])
@login_required
def convert_improvement_to_intervention(code, improvement_id):
    """Converte un Improvement in Intervention per tracciamento nel Dev Tracker."""
    blueprint = BlueprintRegistry.query.filter_by(code=code).first_or_404()
    improvement = BlueprintImprovement.query.filter_by(id=improvement_id, blueprint_id=blueprint.id).first_or_404()

    # Verifica che l'improvement non abbia già un intervention collegato
    if improvement.intervention_id:
        flash('Questo improvement è già collegato a un intervention', 'warning')
        return redirect(url_for('blueprint_registry.detail', code=code))

    try:
        # Crea nuovo intervention
        intervention = BlueprintIntervention(
            blueprint_id=blueprint.id,
            title=f"Feature: {improvement.title}",
            description=improvement.description or "",
            intervention_type='feature',
            status=TaskStatusEnum.todo,
            assigned_to_id=improvement.proposed_by_id or current_user.id,
            progress_percentage=0,
            due_date=improvement.target_completion_date
        )
        db.session.add(intervention)
        db.session.flush()  # Get intervention ID

        # Collega improvement a intervention
        improvement.intervention_id = intervention.id

        db.session.commit()

        flash(f'Intervention creato con successo per improvement "{improvement.title}"', 'success')
        return redirect(url_for('dev_tracker.intervention_detail', intervention_id=intervention.id))

    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante la creazione dell\'intervention: {str(e)}', 'error')
        return redirect(url_for('blueprint_registry.detail', code=code))
