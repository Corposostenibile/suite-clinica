"""
Onboarding module for new hires
"""

from flask import redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from corposostenibile.extensions import db
from corposostenibile.models import (
    OnboardingTemplate, OnboardingTask, OnboardingChecklist,
    OnboardingProgress, JobApplication, Department, User,
    OnboardingTaskTypeEnum, OnboardingTaskStatusEnum,
    ApplicationStatusEnum, KanbanStageTypeEnum
)
from .forms import OnboardingTemplateForm, OnboardingTaskForm
from .permissions import recruiting_required, recruiting_manage_required
from . import recruiting_bp
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash


# ============================================================================
# ONBOARDING TEMPLATES
# ============================================================================

@recruiting_bp.route("/onboarding/templates")
@login_required
@recruiting_required
def onboarding_templates():
    """Lista template onboarding."""
    templates = OnboardingTemplate.query.filter_by(is_active=True).all()
    
    # Raggruppa per dipartimento
    by_department = {}
    for template in templates:
        dept_name = template.department.name if template.department else "Senza Dipartimento"
        if dept_name not in by_department:
            by_department[dept_name] = []
        by_department[dept_name].append(template)
    
    abort(404)

@recruiting_bp.route("/onboarding/templates/new", methods=["GET", "POST"])
@login_required
def onboarding_template_create():
    """Crea nuovo template onboarding."""
    form = OnboardingTemplateForm()
    
    if form.validate_on_submit():
        template = OnboardingTemplate(
            name=form.name.data,
            department_id=form.department_id.data,
            description=form.description.data,
            duration_days=form.duration_days.data,
            is_active=form.is_active.data
        )
        
        # Non creiamo task di default in fase di creazione template.
        
        db.session.add(template)
        db.session.commit()
        
        flash("Template onboarding creato con successo!", "success")
        return redirect(url_for('recruiting.onboarding_template_detail', template_id=template.id))
    
    abort(404)

@recruiting_bp.route("/onboarding/templates/<int:template_id>")
@login_required
def onboarding_template_detail(template_id):
    """Dettaglio template onboarding."""
    template = OnboardingTemplate.query.get_or_404(template_id)
    
    # Raggruppa task per tipo
    tasks_by_type = {}
    for task in template.tasks:
        if task.task_type not in tasks_by_type:
            tasks_by_type[task.task_type] = []
        tasks_by_type[task.task_type].append(task)
    
    # Conta checklist attive
    active_checklists = OnboardingChecklist.query.filter_by(
        template_id=template_id
    ).filter(OnboardingChecklist.actual_end_date.is_(None)).count()
    
    abort(404)

@recruiting_bp.route("/onboarding/templates/<int:template_id>/edit", methods=["GET", "POST"])
@login_required
def onboarding_template_edit(template_id):
    """Modifica template onboarding."""
    template = OnboardingTemplate.query.get_or_404(template_id)
    form = OnboardingTemplateForm(obj=template)
    
    if form.validate_on_submit():
        form.populate_obj(template)
        db.session.commit()
        
        flash("Template aggiornato con successo!", "success")
        return redirect(url_for('recruiting.onboarding_template_detail', template_id=template.id))
    
    abort(404)

@recruiting_bp.route("/onboarding/templates/<int:template_id>/tasks/add", methods=["GET", "POST"])
@login_required
def onboarding_task_add(template_id):
    """Aggiungi task al template."""
    template = OnboardingTemplate.query.get_or_404(template_id)
    form = OnboardingTaskForm()
    
    if form.validate_on_submit():
        task = OnboardingTask(
            template_id=template_id,
            name=form.name.data,
            description=form.description.data,
            task_type=form.task_type.data,
            order=form.order.data,
            due_after_days=form.due_after_days.data,
            is_required=form.is_required.data,
            assigned_role=form.assigned_role.data
        )
        
        db.session.add(task)
        db.session.commit()
        
        flash("Task aggiunto con successo!", "success")
        return redirect(url_for('recruiting.onboarding_template_detail', template_id=template_id))
    
    abort(404)

@recruiting_bp.route("/onboarding/tasks/<int:task_id>/edit", methods=["GET", "POST"])
@login_required
def onboarding_task_edit(task_id):
    """Modifica task onboarding."""
    task = OnboardingTask.query.get_or_404(task_id)
    form = OnboardingTaskForm(obj=task)
    
    if form.validate_on_submit():
        form.populate_obj(task)
        db.session.commit()
        
        flash("Task aggiornato con successo!", "success")
        return redirect(url_for('recruiting.onboarding_template_detail', template_id=task.template_id))
    
    abort(404)

# ============================================================================
# ONBOARDING CHECKLISTS
# ============================================================================

@recruiting_bp.route("/onboarding/checklists")
@login_required
def onboarding_checklists():
    """Lista checklist onboarding attive."""
    # Checklist in corso
    active_checklists = OnboardingChecklist.query.filter(
        OnboardingChecklist.actual_end_date.is_(None)
    ).order_by(OnboardingChecklist.start_date.desc()).all()
    
    # Checklist completate (ultime 30)
    completed_checklists = OnboardingChecklist.query.filter(
        OnboardingChecklist.actual_end_date.isnot(None)
    ).order_by(OnboardingChecklist.actual_end_date.desc()).limit(30).all()
    
    abort(404)

@recruiting_bp.route("/onboarding/checklists/<int:checklist_id>")
@login_required
def onboarding_checklist_detail(checklist_id):
    """Dettaglio checklist onboarding."""
    checklist = OnboardingChecklist.query.get_or_404(checklist_id)
    
    # Raggruppa progress per stato
    progress_by_status = {
        'pending': [],
        'in_progress': [],
        'completed': [],
        'blocked': []
    }
    
    for progress in checklist.progress_items:
        status_key = progress.status.value if progress.status else 'pending'
        if status_key in progress_by_status:
            progress_by_status[status_key].append(progress)
    
    # Calcola statistiche
    stats = {
        'total': len(checklist.progress_items),
        'completed': len(progress_by_status['completed']),
        'pending': len(progress_by_status['pending']),
        'in_progress': len(progress_by_status['in_progress']),
        'blocked': len(progress_by_status['blocked']),
        'progress_percent': checklist.progress_percentage
    }
    
    abort(404)

@recruiting_bp.route("/onboarding/start/<int:application_id>", methods=["GET", "POST"])
@login_required
def onboarding_start(application_id):
    """Inizia onboarding per un candidato assunto."""
    application = JobApplication.query.get_or_404(application_id)
    
    # Verifica che sia stato assunto
    if application.status != ApplicationStatusEnum.hired:
        flash("Il candidato deve essere nello stato 'Assunto' per iniziare l'onboarding.", "warning")
        return redirect(url_for('recruiting.application_detail', application_id=application_id))
    
    # Verifica che non abbia già un onboarding
    if application.onboarding_checklist:
        flash("Questo candidato ha già un onboarding in corso.", "info")
        return redirect(url_for('recruiting.onboarding_checklist_detail', 
                              checklist_id=application.onboarding_checklist.id))
    
    if request.method == "POST":
        template_id = request.form.get('template_id', type=int)
        start_date = request.form.get('start_date')
        
        if not template_id:
            flash("Seleziona un template onboarding.", "warning")
        else:
            template = OnboardingTemplate.query.get_or_404(template_id)
            
            # Crea checklist
            checklist = template.create_checklist_for(application_id)
            
            if start_date:
                checklist.start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            
            db.session.add(checklist)
            db.session.commit()
            
            flash(f"Onboarding iniziato per {application.full_name}!", "success")
            return redirect(url_for('recruiting.onboarding_checklist_detail', 
                                  checklist_id=checklist.id))
    
    # GET: mostra form selezione template
    # Template disponibili per il dipartimento dell'offerta
    templates = []
    if application.job_offer and application.job_offer.department_id:
        templates = OnboardingTemplate.query.filter_by(
            department_id=application.job_offer.department_id,
            is_active=True
        ).all()
    
    # Se non ci sono template per il dipartimento, mostra tutti
    if not templates:
        templates = OnboardingTemplate.query.filter_by(is_active=True).all()
    
    abort(404)

# ============================================================================
# ONBOARDING PROGRESS API
# ============================================================================

@recruiting_bp.route("/api/onboarding/progress/<int:progress_id>/update", methods=["POST"])
@login_required
def api_progress_update(progress_id):
    """Aggiorna stato di un task onboarding."""
    progress = OnboardingProgress.query.get_or_404(progress_id)
    
    data = request.get_json()
    new_status = data.get('status')
    notes = data.get('notes')
    
    if new_status:
        try:
            progress.status = OnboardingTaskStatusEnum(new_status)
            
            if new_status == 'in_progress' and not progress.started_at:
                progress.started_at = datetime.utcnow()
            elif new_status == 'completed':
                progress.mark_completed(current_user.id)
            
        except ValueError:
            return jsonify({'error': 'Invalid status'}), 400
    
    if notes is not None:
        progress.notes = notes
    
    progress.updated_at = datetime.utcnow()
    db.session.commit()
    
    # Verifica se checklist è completata
    checklist = progress.checklist
    if checklist.is_completed and not checklist.actual_end_date:
        checklist.actual_end_date = date.today()
        db.session.commit()
        
        # TODO: Trigger creazione utente
        _create_user_from_application(checklist.application)
    
    return jsonify({
        'success': True,
        'status': progress.status.value if progress.status else None,
        'checklist_completed': checklist.is_completed,
        'checklist_progress': checklist.progress_percentage
    })


@recruiting_bp.route("/api/onboarding/progress/<int:progress_id>/upload", methods=["POST"])
@login_required
def api_progress_upload(progress_id):
    """Upload file per task onboarding."""
    progress = OnboardingProgress.query.get_or_404(progress_id)
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Salva file
    from werkzeug.utils import secure_filename
    import os
    
    filename = secure_filename(file.filename)
    upload_path = os.path.join(
        current_app.config['UPLOAD_FOLDER'],
        'onboarding',
        str(progress.checklist_id),
        str(progress_id)
    )
    
    os.makedirs(upload_path, exist_ok=True)
    
    file_path = os.path.join(upload_path, filename)
    file.save(file_path)
    
    # Aggiungi a uploaded_files
    if not progress.uploaded_files:
        progress.uploaded_files = []
    
    relative_path = os.path.relpath(file_path, current_app.config['UPLOAD_FOLDER'])
    progress.uploaded_files.append({
        'filename': filename,
        'path': relative_path,
        'uploaded_at': datetime.utcnow().isoformat(),
        'uploaded_by': current_user.id
    })
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'filename': filename,
        'message': 'File caricato con successo'
    })


# ============================================================================
# ONBOARDING COMPLETION
# ============================================================================

@recruiting_bp.route("/onboarding/complete/<int:checklist_id>", methods=["POST"])
@login_required
def onboarding_complete(checklist_id):
    """Completa onboarding e crea utente."""
    checklist = OnboardingChecklist.query.get_or_404(checklist_id)
    
    if not checklist.is_completed:
        flash("Non tutti i task obbligatori sono stati completati.", "warning")
        return redirect(url_for('recruiting.onboarding_checklist_detail', checklist_id=checklist_id))
    
    if checklist.created_user_id:
        flash("L'utente è già stato creato per questo onboarding.", "info")
        return redirect(url_for('team.user_detail', user_id=checklist.created_user_id))
    
    # Crea utente
    user = _create_user_from_application(checklist.application)
    
    if user:
        checklist.created_user_id = user.id
        checklist.actual_end_date = date.today()
        db.session.commit()
        
        flash(f"Onboarding completato! Utente {user.email} creato con successo.", "success")
        return redirect(url_for('team.user_detail', user_id=user.id))
    else:
        flash("Errore nella creazione dell'utente.", "danger")
        return redirect(url_for('recruiting.onboarding_checklist_detail', checklist_id=checklist_id))


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_default_onboarding_tasks(department: Department) -> list:
    """Ritorna task di default per tipo di dipartimento."""
    # Task comuni a tutti
    common_tasks = [
        {
            'name': 'Firma contratto',
            'description': 'Firma del contratto di lavoro',
            'task_type': OnboardingTaskTypeEnum.document,
            'order': 0,
            'due_after_days': 0,
            'is_required': True,
            'assigned_role': 'HR'
        },
        {
            'name': 'Documenti identità',
            'description': 'Raccolta documenti di identità e codice fiscale',
            'task_type': OnboardingTaskTypeEnum.document,
            'order': 1,
            'due_after_days': 0,
            'is_required': True,
            'assigned_role': 'HR'
        },
        {
            'name': 'Creazione account email',
            'description': 'Creazione account email aziendale',
            'task_type': OnboardingTaskTypeEnum.system_access,
            'order': 2,
            'due_after_days': 1,
            'is_required': True,
            'assigned_role': 'IT'
        },
        {
            'name': 'Accesso sistemi',
            'description': 'Configurazione accessi ai sistemi aziendali',
            'task_type': OnboardingTaskTypeEnum.system_access,
            'order': 3,
            'due_after_days': 1,
            'is_required': True,
            'assigned_role': 'IT'
        },
        {
            'name': 'Presentazione team',
            'description': 'Meeting di presentazione con il team',
            'task_type': OnboardingTaskTypeEnum.meeting,
            'order': 4,
            'due_after_days': 2,
            'is_required': True,
            'assigned_role': 'Manager'
        },
        {
            'name': 'Formazione sicurezza',
            'description': 'Corso formazione sicurezza sul lavoro',
            'task_type': OnboardingTaskTypeEnum.training,
            'order': 5,
            'due_after_days': 7,
            'is_required': True,
            'assigned_role': 'HR'
        },
        {
            'name': 'Policy aziendali',
            'description': 'Lettura e accettazione policy aziendali',
            'task_type': OnboardingTaskTypeEnum.compliance,
            'order': 6,
            'due_after_days': 3,
            'is_required': True,
            'assigned_role': 'HR'
        }
    ]
    
    # Task specifici per tipo di dipartimento
    if department and 'IT' in department.name.upper():
        common_tasks.extend([
            {
                'name': 'Setup workstation',
                'description': 'Configurazione postazione di lavoro e strumenti sviluppo',
                'task_type': OnboardingTaskTypeEnum.equipment,
                'order': 10,
                'due_after_days': 1,
                'is_required': True,
                'assigned_role': 'IT'
            },
            {
                'name': 'Accesso repository',
                'description': 'Configurazione accesso Git/GitHub/GitLab',
                'task_type': OnboardingTaskTypeEnum.system_access,
                'order': 11,
                'due_after_days': 2,
                'is_required': True,
                'assigned_role': 'Tech Lead'
            }
        ])
    
    return common_tasks


def _create_user_from_application(application: JobApplication) -> User:
    """Crea un User dal JobApplication."""
    try:
        # Genera email se non presente
        email = application.email
        
        # Verifica che email non esista già
        existing = User.query.filter_by(email=email).first()
        if existing:
            return existing
        
        # Crea user
        user = User(
            email=email,
            first_name=application.first_name,
            last_name=application.last_name,
            password_hash=generate_password_hash('ChangeMe123!'),  # Password temporanea
            department_id=application.job_offer.department_id if application.job_offer else None,
            job_title=application.job_offer.title if application.job_offer else None,
            mobile=application.phone,
            hired_at=datetime.utcnow()
        )
        
        db.session.add(user)
        db.session.commit()
        
        # TODO: Invia email con credenziali
        
        return user
        
    except Exception as e:
        current_app.logger.error(f"Error creating user from application: {e}")
        db.session.rollback()
        return None
