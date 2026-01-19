"""
Kanban management for recruiting pipeline
"""

from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from corposostenibile.extensions import db
from corposostenibile.models import (
    RecruitingKanban, KanbanStage, JobApplication,
    ApplicationStatusEnum, KanbanStageTypeEnum, ApplicationStageHistory
)
from .forms import KanbanForm, KanbanStageForm
from .permissions import recruiting_required, recruiting_manage_required
from . import recruiting_bp
from datetime import datetime


# ============================================================================
# KANBAN VIEWS
# ============================================================================

@recruiting_bp.route("/kanban")
@login_required
@recruiting_required
def kanban_list():
    """Lista di tutti i kanban configurati."""
    kanbans = RecruitingKanban.query.filter_by(is_active=True).all()
    
    return render_template(
        "recruiting/kanban/list_modern.html",
        kanbans=kanbans
    )


@recruiting_bp.route("/kanban/new", methods=["GET", "POST"])
@login_required
def kanban_create():
    """Crea nuovo kanban."""
    form = KanbanForm()
    
    if form.validate_on_submit():
        # Se è default, rimuovi default da altri
        if form.is_default.data:
            RecruitingKanban.query.update({'is_default': False})
        
        kanban = RecruitingKanban(
            name=form.name.data,
            description=form.description.data,
            is_default=form.is_default.data,
            is_active=form.is_active.data,
            auto_reject_days=form.auto_reject_days.data,
            created_by_id=current_user.id
        )
        
        # Aggiungi stage di default
        default_stages = [
            ("Candidatura", KanbanStageTypeEnum.applied, "#6c757d", 0),
            ("Screening", KanbanStageTypeEnum.screening, "#17a2b8", 1),
            ("Videocandidatura", KanbanStageTypeEnum.phone_interview, "#ffc107", 2),
            ("Colloquio HR", KanbanStageTypeEnum.hr_interview, "#20c997", 3),
            ("Colloquio Responsabile", KanbanStageTypeEnum.technical_interview, "#6f42c1", 4),
            ("Offerta", KanbanStageTypeEnum.offer, "#007bff", 5),
            ("Assunto", KanbanStageTypeEnum.hired, "#28a745", 6),
            ("Rifiutato", KanbanStageTypeEnum.rejected, "#dc3545", 7),
            ("Declinato", KanbanStageTypeEnum.rejected, "#fd7e14", 8),
        ]
        
        for name, stage_type, color, order in default_stages:
            stage = KanbanStage(
                name=name,
                stage_type=stage_type,
                color=color,
                order=order,
                is_active=True,
                is_final=(name in ["Assunto", "Rifiutato", "Declinato"])
            )
            kanban.stages.append(stage)
        
        db.session.add(kanban)
        db.session.commit()
        
        flash("Kanban creato con successo!", "success")
        return redirect(url_for('recruiting.kanban_list'))
    
    return render_template(
        "recruiting/kanban/create_modern.html",
        form=form
    )


@recruiting_bp.route("/kanban/<int:kanban_id>")
@login_required
def kanban_view(kanban_id):
    """Visualizza kanban generale (tutti i candidati)."""
    kanban = RecruitingKanban.query.get_or_404(kanban_id)
    
    # Ottieni tutte le offerte che usano questo kanban
    from corposostenibile.models import JobOffer
    job_offers = JobOffer.query.filter_by(kanban_id=kanban_id).all()
    
    # Prepara gli stage con le applicazioni
    stages = []
    total_candidates = 0
    in_review = 0
    scheduled_interviews = 0

    # Calcola il numero totale di candidati nella fase iniziale
    initial_stage = next((s for s in kanban.stages if s.stage_type == KanbanStageTypeEnum.applied), None)
    if initial_stage:
        initial_candidates = JobApplication.query.filter_by(kanban_stage_id=initial_stage.id).count()
    else:
        initial_candidates = 0

    # Ordina gli stage attivi per order
    sorted_stages = sorted([s for s in kanban.stages if s.is_active], key=lambda x: x.order if x.order is not None else 9999)

    for idx, stage in enumerate(sorted_stages):
        # Candidati in questo stage, ordinati per score dal più alto al più basso
        applications = JobApplication.query.filter_by(
            kanban_stage_id=stage.id
        ).order_by(JobApplication.total_score.desc().nullslast()).all()

        # IMPORTANTE: NON usare stage.applications (è un relationship backref!)
        # Usa un attributo temporaneo per non interferire con il backref
        stage.filtered_applications = applications

        # Calcola la percentuale rispetto alla fase iniziale
        if initial_candidates > 0:
            stage.percentage = (len(applications) / initial_candidates) * 100
        else:
            stage.percentage = 0

        # SISTEMA SEMAFORO: Calcola il prossimo stage (per pulsante verde)
        # Se non è l'ultimo stage e il prossimo non è finale, assegna next_stage
        if idx < len(sorted_stages) - 1:
            next_stage_candidate = sorted_stages[idx + 1]
            # Non mostrare pulsante verde se il prossimo stage è finale
            stage.next_stage = next_stage_candidate if not next_stage_candidate.is_final else None
        else:
            stage.next_stage = None

        stages.append(stage)

        # Calcola statistiche
        total_candidates += len(applications)

        # Conta candidati in valutazione (screening, interview stages)
        if stage.stage_type in [KanbanStageTypeEnum.screening,
                               KanbanStageTypeEnum.phone_interview,
                               KanbanStageTypeEnum.hr_interview,
                               KanbanStageTypeEnum.technical_interview,
                               KanbanStageTypeEnum.final_interview]:
            in_review += len(applications)

        # Conta colloqui programmati (interview stages con data futura)
        if stage.stage_type in [KanbanStageTypeEnum.phone_interview,
                               KanbanStageTypeEnum.hr_interview,
                               KanbanStageTypeEnum.technical_interview,
                               KanbanStageTypeEnum.final_interview]:
            scheduled_interviews += len(applications)

    # Trova gli stage finali per il sistema semaforo (pulsante rosso)
    final_stages = [s for s in kanban.stages if s.is_final and s.is_active]

    return render_template(
        "recruiting/kanban/board.html",
        kanban=kanban,
        stages=stages,
        job_offers=job_offers,
        total_candidates=total_candidates,
        in_review=in_review,
        scheduled_interviews=scheduled_interviews,
        final_stages=final_stages  # Stage finali per pulsante rosso
    )


@recruiting_bp.route("/offers/<int:offer_id>/kanban")
@login_required  
def offer_kanban_view(offer_id):
    """Visualizza kanban specifico per una singola offerta di lavoro."""
    from corposostenibile.models import JobOffer
    offer = JobOffer.query.get_or_404(offer_id)
    
    if not offer.kanban_id:
        flash("Questa offerta non ha un kanban configurato", "warning")
        return redirect(url_for('recruiting.offer_detail', offer_id=offer_id))
    
    kanban = offer.kanban
    
    # Prepara gli stage con le applicazioni per questa offerta
    stages = []
    total_candidates = 0
    in_review = 0
    scheduled_interviews = 0

    # Calcola il numero totale di candidati nella fase iniziale per questa offerta
    initial_stage = next((s for s in kanban.stages if s.stage_type == KanbanStageTypeEnum.applied), None)
    if initial_stage:
        initial_candidates = JobApplication.query.filter_by(job_offer_id=offer_id, kanban_stage_id=initial_stage.id).count()
    else:
        initial_candidates = 0

    # Ordina gli stage attivi per order
    sorted_stages = sorted([s for s in kanban.stages if s.is_active], key=lambda x: x.order if x.order is not None else 9999)

    for idx, stage in enumerate(sorted_stages):
        # Solo candidati di questa offerta in questo stage, ordinati per score dal più alto al più basso
        applications = JobApplication.query.filter_by(
            job_offer_id=offer_id,
            kanban_stage_id=stage.id
        ).order_by(JobApplication.total_score.desc().nullslast()).all()

        # IMPORTANTE: NON usare stage.applications (è un relationship backref!)
        # Usa un attributo temporaneo per non interferire con il backref
        stage.filtered_applications = applications

        # Calcola la percentuale rispetto alla fase iniziale
        if initial_candidates > 0:
            stage.percentage = (len(applications) / initial_candidates) * 100
        else:
            stage.percentage = 0

        # SISTEMA SEMAFORO: Calcola il prossimo stage (per pulsante verde)
        # Se non è l'ultimo stage e il prossimo non è finale, assegna next_stage
        if idx < len(sorted_stages) - 1:
            next_stage_candidate = sorted_stages[idx + 1]
            # Non mostrare pulsante verde se il prossimo stage è finale
            stage.next_stage = next_stage_candidate if not next_stage_candidate.is_final else None
        else:
            stage.next_stage = None

        stages.append(stage)

        # Calcola statistiche
        total_candidates += len(applications)

        # Conta candidati in valutazione (screening, interview stages)
        if stage.stage_type in [KanbanStageTypeEnum.screening,
                               KanbanStageTypeEnum.phone_interview,
                               KanbanStageTypeEnum.hr_interview,
                               KanbanStageTypeEnum.technical_interview,
                               KanbanStageTypeEnum.final_interview]:
            in_review += len(applications)

        # Conta colloqui programmati (interview stages con data futura)
        if stage.stage_type in [KanbanStageTypeEnum.phone_interview,
                               KanbanStageTypeEnum.hr_interview,
                               KanbanStageTypeEnum.technical_interview,
                               KanbanStageTypeEnum.final_interview]:
            scheduled_interviews += len(applications)

    # Trova gli stage finali per il sistema semaforo (pulsante rosso)
    final_stages = [s for s in kanban.stages if s.is_final and s.is_active]

    return render_template(
        "recruiting/kanban/board.html",
        kanban=kanban,
        stages=stages,
        job_offers=[offer],  # Solo questa offerta
        current_offer=offer,  # Per identificare che siamo in vista singola offerta
        total_candidates=total_candidates,
        in_review=in_review,
        scheduled_interviews=scheduled_interviews,
        final_stages=final_stages  # Stage finali per pulsante rosso
    )


@recruiting_bp.route("/kanban/<int:kanban_id>/configure", methods=["GET", "POST"])
@login_required
def kanban_configure(kanban_id):
    """Configura stages del kanban."""
    kanban = RecruitingKanban.query.get_or_404(kanban_id)
    
    if request.method == "POST":
        # Gestione stages via AJAX
        pass
    
    return render_template(
        "recruiting/kanban/configure_modern.html",
        kanban=kanban,
        stages=kanban.stages
    )


@recruiting_bp.route("/kanban/<int:kanban_id>/edit", methods=["GET", "POST"])
@login_required
def kanban_edit(kanban_id):
    """Modifica kanban."""
    kanban = RecruitingKanban.query.get_or_404(kanban_id)
    form = KanbanForm(obj=kanban)
    
    if form.validate_on_submit():
        # Se è default, rimuovi default da altri
        if form.is_default.data and not kanban.is_default:
            RecruitingKanban.query.filter(
                RecruitingKanban.id != kanban_id
            ).update({'is_default': False})
        
        form.populate_obj(kanban)
        db.session.commit()
        
        flash("Kanban aggiornato con successo!", "success")
        return redirect(url_for('recruiting.kanban_list'))
    
    return render_template(
        "recruiting/kanban/edit_modern.html",
        form=form,
        kanban=kanban
    )


# ============================================================================
# KANBAN STAGE MANAGEMENT
# ============================================================================

@recruiting_bp.route("/kanban/<int:kanban_id>/stages/add", methods=["GET", "POST"])
@login_required
def stage_add(kanban_id):
    """Aggiungi stage al kanban."""
    kanban = RecruitingKanban.query.get_or_404(kanban_id)
    form = KanbanStageForm()
    
    # Popola choices per stage_type
    form.stage_type.choices = [
        (t.value, t.value.replace('_', ' ').title())
        for t in KanbanStageTypeEnum
    ]
    
    if form.validate_on_submit():
        stage = KanbanStage(
            kanban_id=kanban_id,
            name=form.name.data,
            stage_type=form.stage_type.data,
            description=form.description.data,
            color=form.color.data,
            icon=form.icon.data,
            order=form.order.data,
            is_active=form.is_active.data,
            is_final=form.is_final.data,
            auto_email_template=form.auto_email_template.data
        )
        
        db.session.add(stage)
        db.session.commit()
        
        flash("Stage aggiunto con successo!", "success")
        return redirect(url_for('recruiting.kanban_configure', kanban_id=kanban_id))
    
    return render_template(
        "recruiting/kanban/stage_form.html",
        form=form,
        kanban=kanban,
        action="add"
    )


@recruiting_bp.route("/kanban/stages/<int:stage_id>/edit", methods=["GET", "POST"])
@login_required
def stage_edit(stage_id):
    """Modifica stage."""
    stage = KanbanStage.query.get_or_404(stage_id)
    form = KanbanStageForm(obj=stage)
    
    # Popola choices per stage_type
    form.stage_type.choices = [
        (t.value, t.value.replace('_', ' ').title())
        for t in KanbanStageTypeEnum
    ]
    
    if form.validate_on_submit():
        form.populate_obj(stage)
        db.session.commit()
        
        flash("Stage aggiornato con successo!", "success")
        return redirect(url_for('recruiting.kanban_configure', kanban_id=stage.kanban_id))

    if request.method == "GET":
        form.stage_type.data = stage.stage_type.value
        form.color.data = stage.color
    
    return render_template(
        "recruiting/kanban/stage_form.html",
        form=form,
        stage=stage,
        kanban=stage.kanban,
        action="edit"
    )


@recruiting_bp.route("/kanban/stages/<int:stage_id>/delete", methods=["POST"])
@login_required
def stage_delete(stage_id):
    """Elimina stage."""
    stage = KanbanStage.query.get_or_404(stage_id)
    kanban_id = stage.kanban_id
    
    # Verifica che non ci siano candidati
    if stage.applications:
        flash("Non puoi eliminare uno stage con candidati!", "warning")
    else:
        db.session.delete(stage)
        db.session.commit()
        flash("Stage eliminato.", "info")
    
    return redirect(url_for('recruiting.kanban_configure', kanban_id=kanban_id))


# ============================================================================
# KANBAN API (for drag & drop)
# ============================================================================

@recruiting_bp.route("/api/kanban/move", methods=["POST"])
@login_required
def api_kanban_move():
    """API per spostare candidato tra stages."""
    data = request.get_json()
    
    application_id = data.get('application_id')
    new_stage_id = data.get('stage_id')
    new_order = data.get('order', 0)
    
    if not application_id or not new_stage_id:
        return jsonify({'error': 'Missing parameters'}), 400
    
    application = JobApplication.query.get_or_404(application_id)
    new_stage = KanbanStage.query.get_or_404(new_stage_id)
    
    # Verifica permessi (TODO: implementare controllo ACL)
    
    # Aggiorna posizione
    old_stage_id = application.kanban_stage_id
    application.kanban_stage_id = new_stage_id
    application.kanban_order = new_order
    
    # Aggiorna stato se necessario
    stage_status_map = {
        KanbanStageTypeEnum.applied: ApplicationStatusEnum.new,
        KanbanStageTypeEnum.screening: ApplicationStatusEnum.screening,
        KanbanStageTypeEnum.phone_interview: ApplicationStatusEnum.interview_scheduled,
        KanbanStageTypeEnum.technical_interview: ApplicationStatusEnum.interview_scheduled,
        KanbanStageTypeEnum.final_interview: ApplicationStatusEnum.interviewed,
        KanbanStageTypeEnum.offer: ApplicationStatusEnum.offer_sent,
        KanbanStageTypeEnum.hired: ApplicationStatusEnum.hired,
        KanbanStageTypeEnum.rejected: ApplicationStatusEnum.rejected,
    }
    
    if new_stage.stage_type in stage_status_map:
        application.status = stage_status_map[new_stage.stage_type]
    
    # Se lo stage ha un template email automatico, prepara l'invio
    if new_stage.auto_email_template:
        # TODO: Implementare invio email
        pass
    
    # ===== TRACKING STORICO MOVIMENTI STAGE =====
    # Registra il movimento in ApplicationStageHistory solo se cambia stage
    if old_stage_id and old_stage_id != new_stage_id:
        # 1. Chiudi il record storico attivo del vecchio stage
        old_history = ApplicationStageHistory.query.filter_by(
            application_id=application_id,
            stage_id=old_stage_id,
            exited_at=None  # Solo record attivi
        ).first()

        if old_history:
            old_history.exited_at = datetime.utcnow()
            old_history.calculate_duration()  # Calcola durata in secondi

        # 2. Crea nuovo record storico per il nuovo stage
        new_history = ApplicationStageHistory(
            application_id=application_id,
            stage_id=new_stage_id,
            previous_stage_id=old_stage_id,
            entered_at=datetime.utcnow(),
            exited_at=None,  # Ancora attivo
            duration_seconds=None,
            changed_by_id=current_user.id,
            notes=f'Spostato da drag&drop da "{KanbanStage.query.get(old_stage_id).name}" a "{new_stage.name}"'
        )
        db.session.add(new_history)
    elif not old_stage_id and new_stage_id:
        # Prima assegnazione: crea record storico iniziale
        new_history = ApplicationStageHistory(
            application_id=application_id,
            stage_id=new_stage_id,
            previous_stage_id=None,
            entered_at=datetime.utcnow(),
            exited_at=None,
            duration_seconds=None,
            changed_by_id=current_user.id,
            notes=f'Prima assegnazione stage: "{new_stage.name}"'
        )
        db.session.add(new_history)

    # Riordina altri candidati nello stesso stage
    if old_stage_id != new_stage_id:
        # Riordina vecchio stage
        old_apps = JobApplication.query.filter_by(
            kanban_stage_id=old_stage_id
        ).order_by(JobApplication.kanban_order).all()

        for idx, app in enumerate(old_apps):
            app.kanban_order = idx
    
    # Riordina nuovo stage
    new_apps = JobApplication.query.filter(
        JobApplication.kanban_stage_id == new_stage_id,
        JobApplication.id != application_id
    ).order_by(JobApplication.kanban_order).all()
    
    # Inserisci nella posizione corretta
    for app in new_apps:
        if app.kanban_order >= new_order:
            app.kanban_order += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Candidato spostato in {new_stage.name}',
        'new_status': application.status.value if application.status else None
    })


@recruiting_bp.route("/api/kanban/stages/reorder", methods=["POST"])
@login_required
def api_stages_reorder():
    """API per riordinare gli stages."""
    data = request.get_json()
    stage_ids = data.get('stage_ids', [])

    if not stage_ids:
        return jsonify({'error': 'No stages provided'}), 400

    # Aggiorna ordine
    for idx, stage_id in enumerate(stage_ids):
        stage = KanbanStage.query.get(stage_id)
        if stage:
            stage.order = idx

    db.session.commit()

    return jsonify({'success': True, 'message': 'Stages riordinati'})


@recruiting_bp.route("/api/kanban/<int:kanban_id>/stages/add", methods=["POST"])
@login_required
def api_stage_add_simple(kanban_id):
    """API semplificata per aggiungere stage solo con nome."""
    kanban = RecruitingKanban.query.get_or_404(kanban_id)
    data = request.get_json()

    name = data.get('name')
    if not name:
        return jsonify({'error': 'Nome fase obbligatorio'}), 400

    # Conta gli stage esistenti per l'ordine
    existing_stages = KanbanStage.query.filter_by(kanban_id=kanban_id).count()

    # Crea nuovo stage con valori di default
    stage = KanbanStage(
        kanban_id=kanban_id,
        name=name,
        stage_type=KanbanStageTypeEnum.applied,  # Default type
        description=data.get('description', ''),
        color=data.get('color', '#487FFF'),
        order=data.get('order', existing_stages + 1),
        is_active=data.get('is_active', True),
        is_final=data.get('is_final', False)
    )

    db.session.add(stage)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Fase aggiunta con successo',
        'stage_id': stage.id
    })


@recruiting_bp.route("/api/kanban/stages/<int:stage_id>/update", methods=["POST"])
@login_required
def api_stage_update(stage_id):
    """API per aggiornare una fase."""
    stage = KanbanStage.query.get_or_404(stage_id)
    data = request.get_json()

    # Aggiorna i campi
    if 'name' in data:
        stage.name = data['name']
    if 'description' in data:
        stage.description = data['description']
    if 'color' in data:
        stage.color = data['color']
    if 'order' in data:
        stage.order = data['order']
    if 'is_active' in data:
        stage.is_active = data['is_active']
    if 'is_final' in data:
        stage.is_final = data['is_final']

    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Fase aggiornata con successo'
    })


@recruiting_bp.route("/api/kanban/application/<int:application_id>/notes", methods=["POST"])
@login_required
def api_application_notes(application_id):
    """API per aggiungere note a una candidatura."""
    application = JobApplication.query.get_or_404(application_id)
    
    data = request.get_json()
    notes = data.get('notes', '')
    
    application.internal_notes = notes
    application.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Note aggiornate',
        'notes': notes
    })


@recruiting_bp.route("/api/kanban/bulk-move", methods=["POST"])
@login_required
def api_bulk_move():
    """API per spostare più candidati contemporaneamente."""
    data = request.get_json()
    
    application_ids = data.get('application_ids', [])
    new_stage_id = data.get('stage_id')
    
    if not application_ids or not new_stage_id:
        return jsonify({'error': 'Missing parameters'}), 400
    
    new_stage = KanbanStage.query.get_or_404(new_stage_id)
    
    moved_count = 0
    for app_id in application_ids:
        application = JobApplication.query.get(app_id)
        if application:
            application.kanban_stage_id = new_stage_id
            application.kanban_order = moved_count
            moved_count += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'{moved_count} candidati spostati in {new_stage.name}'
    })


# ============================================================================
# KANBAN ANALYTICS
# ============================================================================

@recruiting_bp.route("/kanban/<int:kanban_id>/analytics")
@login_required
def kanban_analytics(kanban_id):
    """Analytics avanzate del kanban per identificare colli di bottiglia."""
    from .services.metrics_service import MetricsService

    kanban = RecruitingKanban.query.get_or_404(kanban_id)

    # Ottieni la soglia bottleneck dai parametri della query (default: 35.0)
    bottleneck_threshold = request.args.get('bottleneck_threshold', 35.0, type=float)

    # Usa il servizio centralizzato per calcolare le metriche
    metrics_service = MetricsService()
    metrics = metrics_service.calculate_kanban_analytics(kanban_id, bottleneck_threshold=bottleneck_threshold)

    # Ottieni le spiegazioni dei calcoli
    explanations = metrics_service.get_kanban_calculation_explanations()

    return render_template(
        "recruiting/kanban/analytics.html",
        kanban=kanban,
        metrics=metrics,
        explanations=explanations
    )


@recruiting_bp.route("/api/applications/<int:application_id>/timeline")
@login_required
def api_application_timeline(application_id):
    """API per recuperare la timeline di una candidatura."""
    application = JobApplication.query.get_or_404(application_id)

    events = []

    # 1. Candidatura ricevuta
    events.append({
        'title': 'Candidatura Ricevuta',
        'description': f'Candidatura inviata per {application.job_offer.title if application.job_offer else "offerta sconosciuta"}',
        'date': application.created_at.isoformat() if application.created_at else datetime.utcnow().isoformat(),
        'duration': None
    })

    # 2. Screening ATS
    if application.screened_at:
        events.append({
            'title': 'Screening ATS Completato',
            'description': f'CV analizzato - Score: {application.cv_score:.1f}%' if application.cv_score else 'CV analizzato',
            'date': application.screened_at.isoformat(),
            'duration': None
        })

    # 3. Storia movimenti tra stage
    stage_history = ApplicationStageHistory.query.filter_by(
        application_id=application_id
    ).order_by(ApplicationStageHistory.entered_at).all()

    for history in stage_history:
        stage = KanbanStage.query.get(history.stage_id)
        prev_stage = KanbanStage.query.get(history.previous_stage_id) if history.previous_stage_id else None

        # Calcola durata se disponibile
        duration_text = None
        if history.duration_seconds:
            days = history.duration_seconds // 86400
            hours = (history.duration_seconds % 86400) // 3600
            minutes = (history.duration_seconds % 3600) // 60

            duration_parts = []
            if days > 0:
                duration_parts.append(f"{int(days)} giorni")
            if hours > 0:
                duration_parts.append(f"{int(hours)} ore")
            if minutes > 0 and days == 0:
                duration_parts.append(f"{int(minutes)} minuti")

            duration_text = ", ".join(duration_parts) if duration_parts else "< 1 minuto"

        # Titolo e descrizione
        if prev_stage:
            title = f'Spostato da {prev_stage.name} a {stage.name}' if stage else 'Cambio Stage'
            description = history.notes or f'Candidato spostato da "{prev_stage.name}" a "{stage.name}"' if stage else ''
        else:
            title = f'Assegnato a {stage.name}' if stage else 'Primo Stage'
            description = history.notes or f'Prima assegnazione allo stage "{stage.name}"' if stage else ''

        events.append({
            'title': title,
            'description': description,
            'date': history.entered_at.isoformat() if history.entered_at else datetime.utcnow().isoformat(),
            'duration': duration_text
        })

    # Ordina eventi per data (dal più recente al più vecchio)
    events.sort(key=lambda x: x['date'], reverse=True)

    return jsonify({
        'success': True,
        'events': events
    })