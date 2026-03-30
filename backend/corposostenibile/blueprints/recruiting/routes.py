"""
Routes principali per il modulo Recruiting
"""

from flask import redirect, url_for, flash, request, jsonify, abort, current_app, send_file
from flask_login import login_required, current_user
from corposostenibile.extensions import db
from sqlalchemy import func, and_
from corposostenibile.models import (
    JobOffer, JobQuestion, JobApplication, ApplicationAnswer,
    RecruitingKanban, KanbanStage, ApplicationStageHistory,
    JobOfferStatusEnum, ApplicationSourceEnum, ApplicationStatusEnum, KanbanStageTypeEnum
)
from .forms import JobOfferForm, ScreeningForm
from . import recruiting_bp
from .services.metrics_service import MetricsService, ANALYTICS_START_DATE
import json
import os
from datetime import datetime, timedelta


# ============================================================================
# DASHBOARD & OVERVIEW
# ============================================================================

@recruiting_bp.route("/")
@login_required
def index():
    """Dashboard principale recruiting."""
    abort(404)
@recruiting_bp.route("/dashboard")
@login_required
def unified_dashboard():
    """Dashboard unificata con tab per metriche, offerte e pipeline."""
    abort(404)
@recruiting_bp.route("/offers")
@login_required
def offers_list():
    """Lista offerte di lavoro."""
    abort(404)
@recruiting_bp.route("/offers/new", methods=["GET", "POST"])
@login_required
def offer_create():
    """Crea nuova offerta di lavoro."""
    abort(404)
@recruiting_bp.route("/offers/<int:offer_id>")
@login_required
def offer_detail():
    """Dettaglio offerta di lavoro."""
    abort(404)
@recruiting_bp.route("/offers/<int:offer_id>/edit", methods=["GET", "POST"])
@login_required
def offer_edit():
    """Modifica offerta di lavoro."""
    abort(404)
@recruiting_bp.route("/offers/<int:offer_id>/questions", methods=["GET", "POST"])
@login_required
def offer_questions():
    """Gestione domande del form."""
    abort(404)
@recruiting_bp.route("/offers/<int:offer_id>/questions/create", methods=["POST"])
@login_required
def question_create(offer_id):
    """Crea una singola nuova domanda."""
    offer = JobOffer.query.get_or_404(offer_id)

    try:
        data = request.get_json()
        print(f"[DEBUG] Received data: {data}")

        if not data:
            print("[ERROR] No data received")
            return jsonify({'success': False, 'message': 'Nessun dato ricevuto'}), 400

        # Validate required fields
        if not data.get('question_text'):
            print("[ERROR] Missing question_text")
            return jsonify({'success': False, 'message': 'Testo domanda obbligatorio'}), 400

        if not data.get('question_type'):
            print("[ERROR] Missing question_type")
            return jsonify({'success': False, 'message': 'Tipo domanda obbligatorio'}), 400

        # Get max order
        max_order = db.session.query(db.func.max(JobQuestion.order)).filter_by(job_offer_id=offer.id).scalar() or -1

        question = JobQuestion(
            job_offer_id=offer.id,
            question_text=data.get('question_text', ''),
            question_type=data.get('question_type', 'short_text'),
            options=data.get('options'),
            expected_answer=data.get('expected_answer'),
            expected_options=data.get('expected_options'),
            expected_min=data.get('expected_min'),
            expected_max=data.get('expected_max'),
            expected_match_type=data.get('expected_match_type', 'partial'),
            is_required=data.get('is_required', True),
            weight=data.get('weight', 0),
            order=max_order + 1
        )

        db.session.add(question)
        db.session.commit()

        print(f"[SUCCESS] Question created with ID: {question.id}")
        return jsonify({'success': True, 'message': 'Domanda creata con successo!', 'question_id': question.id})

    except Exception as e:
        db.session.rollback()
        import traceback
        error_detail = traceback.format_exc()
        print(f"[ERROR] Error creating question: {error_detail}")
        return jsonify({'success': False, 'message': f'Errore nella creazione: {str(e)}'}), 500


@recruiting_bp.route("/offers/<int:offer_id>/questions/<int:question_id>", methods=["PUT"])
@login_required
def question_update(offer_id, question_id):
    """Modifica una singola domanda."""
    offer = JobOffer.query.get_or_404(offer_id)
    question = JobQuestion.query.get_or_404(question_id)

    # Verifica che la domanda appartenga all'offerta
    if question.job_offer_id != offer.id:
        return jsonify({'success': False, 'message': 'Domanda non trovata'}), 404

    try:
        data = request.get_json()

        # Aggiorna campi
        question.question_text = data.get('question_text', question.question_text)
        question.question_type = data.get('question_type', question.question_type)
        question.options = data.get('options', question.options)
        question.expected_answer = data.get('expected_answer')
        question.expected_options = data.get('expected_options', [])
        question.expected_min = data.get('expected_min')
        question.expected_max = data.get('expected_max')
        question.expected_match_type = data.get('expected_match_type', 'partial')
        question.is_required = data.get('is_required', question.is_required)
        question.weight = data.get('weight', question.weight)

        db.session.commit()

        return jsonify({'success': True, 'message': 'Domanda aggiornata con successo!'})

    except Exception as e:
        db.session.rollback()
        import traceback
        error_detail = traceback.format_exc()
        print(f"Error updating question: {error_detail}")
        return jsonify({'success': False, 'message': f'Errore nell\'aggiornamento: {str(e)}'}), 500


@recruiting_bp.route("/offers/<int:offer_id>/questions/<int:question_id>", methods=["DELETE"])
@login_required
def question_delete(offer_id, question_id):
    """Elimina una singola domanda."""
    offer = JobOffer.query.get_or_404(offer_id)
    question = JobQuestion.query.get_or_404(question_id)

    # Verifica che la domanda appartenga all'offerta
    if question.job_offer_id != offer.id:
        return jsonify({'success': False, 'message': 'Domanda non trovata'}), 404

    try:
        db.session.delete(question)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Domanda eliminata con successo!'})

    except Exception as e:
        db.session.rollback()
        import traceback
        error_detail = traceback.format_exc()
        print(f"Error deleting question: {error_detail}")
        return jsonify({'success': False, 'message': f'Errore nell\'eliminazione: {str(e)}'}), 500


@recruiting_bp.route("/offers/<int:offer_id>/questions/reorder", methods=["POST"])
@login_required
def questions_reorder(offer_id):
    """Riordina le domande."""
    offer = JobOffer.query.get_or_404(offer_id)

    try:
        data = request.get_json()
        order_data = data.get('order', [])

        for item in order_data:
            question_id = item.get('id')
            new_order = item.get('order')

            question = JobQuestion.query.get(question_id)
            if question and question.job_offer_id == offer.id:
                question.order = new_order

        db.session.commit()

        return jsonify({'success': True, 'message': 'Ordine aggiornato con successo!'})

    except Exception as e:
        db.session.rollback()
        import traceback
        error_detail = traceback.format_exc()
        print(f"Error reordering questions: {error_detail}")
        return jsonify({'success': False, 'message': f'Errore nel riordino: {str(e)}'}), 500


@recruiting_bp.route("/offers/<int:offer_id>/publish", methods=["POST"])
@login_required
def offer_publish(offer_id):
    """Pubblica offerta di lavoro."""
    offer = JobOffer.query.get_or_404(offer_id)
    
    # Verifica che ci siano domande
    if not offer.questions:
        flash("Aggiungi almeno una domanda prima di pubblicare!", "warning")
        return redirect(url_for('recruiting.offer_questions', offer_id=offer.id))
    
    # Verifica che i pesi delle domande sommino a 100
    total_weight = offer.total_questions_weight
    if abs(total_weight - 100) > 0.01:  # Tolleranza per float
        flash(f"Il peso totale delle domande deve essere 100%, attualmente è {total_weight:.1f}%", "warning")
        return redirect(url_for('recruiting.offer_questions', offer_id=offer.id))
    
    offer.status = JobOfferStatusEnum.published
    offer.published_at = datetime.utcnow()
    
    db.session.commit()
    
    flash("Offerta pubblicata con successo!", "success")
    return redirect(url_for('recruiting.offer_detail', offer_id=offer.id))


@recruiting_bp.route("/offers/<int:offer_id>/close", methods=["POST"])
@login_required
def offer_close(offer_id):
    """Chiude offerta di lavoro."""
    offer = JobOffer.query.get_or_404(offer_id)
    
    offer.status = JobOfferStatusEnum.closed
    offer.closed_at = datetime.utcnow()
    
    db.session.commit()
    
    flash("Offerta chiusa.", "info")
    return redirect(url_for('recruiting.offer_detail', offer_id=offer.id))


# ============================================================================
# PUBLIC APPLICATION FORM
# ============================================================================

@recruiting_bp.route("/apply/<link_code>", methods=["GET", "POST"])
def public_apply():
    """Form pubblico di candidatura."""
    abort(404)
@recruiting_bp.route("/applications")
@login_required
def applications_list():
    """Lista tutte le candidature."""
    abort(404)
@recruiting_bp.route("/applications/<int:application_id>")
@login_required
def application_detail():
    """Dettaglio candidatura."""
    abort(404)
@recruiting_bp.route("/offers/<int:offer_id>/applications")
@login_required
def offer_applications():
    """Lista candidature per una specifica offerta."""
    abort(404)
@recruiting_bp.route("/offers/<int:offer_id>/screening", methods=["GET", "POST"])
@login_required
def offer_screening(offer_id):
    """Avvia screening ATS per le candidature."""
    offer = JobOffer.query.get_or_404(offer_id)
    form = ScreeningForm()
    
    if form.validate_on_submit():
        # Importa il modulo ATS
        from .ats import run_screening
        
        # Determina quali candidature analizzare
        if form.screen_all.data:
            applications = offer.applications.all()
        elif form.only_new.data:
            applications = offer.applications.filter_by(status='new').all()
        else:
            applications = offer.applications.all()
        
        # Esegui screening
        results = run_screening(
            applications,
            min_score=form.min_score.data
        )
        
        flash(f"Screening completato! Analizzate {len(results['processed'])} candidature.", "success")
        
        # Reindirizza al kanban se configurato
        if offer.kanban:
            return redirect(url_for('recruiting.kanban_view', kanban_id=offer.kanban.id))
        else:
            return redirect(url_for('recruiting.offer_applications', offer_id=offer.id))
    
    # Statistiche pre-screening
    stats = {
        'total': offer.applications.count(),
        'new': offer.applications.filter_by(status='new').count(),
        'screened': offer.applications.filter(JobApplication.screened_at.isnot(None)).count()
    }
    
    abort(404)


# ============================================================================
# HR METRICS DASHBOARD
# ============================================================================

@recruiting_bp.route("/metrics")
@login_required
def metrics_dashboard():
    """Dashboard generale delle metriche HR."""
    
    # Recupera i parametri di data dalla richiesta o imposta i valori predefiniti
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    else:
        start_date = datetime.now().replace(day=1) # Inizio del mese corrente

    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    else:
        end_date = datetime.now() # Data odierna

    # Utilizza il servizio unificato per calcolare le metriche generali
    metrics_service = MetricsService()
    general_metrics = metrics_service.calculate_metrics(
        offer_id=None,  # None per metriche generali
        start_date=start_date,
        end_date=end_date
    )

    # ===== NUOVE METRICHE: Funnel Analysis e Source Effectiveness =====
    funnel_data = metrics_service.calculate_funnel_analysis(
        offer_id=None,
        start_date=start_date,
        end_date=end_date
    )

    source_effectiveness = metrics_service.calculate_source_effectiveness(
        offer_id=None,
        start_date=start_date,
        end_date=end_date
    )

    # Offerte recenti per mostrare un esempio
    recent_offers = JobOffer.query.order_by(JobOffer.created_at.desc()).limit(5).all()

    abort(404)

@recruiting_bp.route("/offers/<int:offer_id>/metrics")
@login_required
def offer_metrics_dashboard(offer_id):
    """Dashboard delle metriche per una specifica offerta di lavoro con filtri temporali."""
    from dateutil.relativedelta import relativedelta

    # Recupera l'offerta
    offer = JobOffer.query.get_or_404(offer_id)

    # ========== FILTRI DATA (identici a unified_dashboard) ==========
    filter_type = request.args.get('filter_type', 'month')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    today = datetime.now()

    if filter_type == 'month' and not start_date_str:
        start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = today.replace(hour=23, minute=59, second=59)
    elif filter_type == 'quarter' and not start_date_str:
        quarter_month = ((today.month - 1) // 3) * 3 + 1
        start_date = today.replace(month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = today.replace(hour=23, minute=59, second=59)
    elif filter_type == 'year' and not start_date_str:
        start_date = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = today.replace(hour=23, minute=59, second=59)
    elif start_date_str and end_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    else:
        start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = today.replace(hour=23, minute=59, second=59)

    # ========== CALCOLO METRICHE PER SINGOLA OFFERTA ==========

    # Query base candidature per questa offerta nel periodo
    applications_query = JobApplication.query.filter(
        JobApplication.job_offer_id == offer_id,
        JobApplication.created_at >= start_date,
        JobApplication.created_at <= end_date
    )

    # ========== RIGA 1: METRICHE GENERALI ==========
    total_applications = applications_query.count()

    total_hires = applications_query.filter(
        JobApplication.status == ApplicationStatusEnum.hired
    ).count()

    conversion_rate = round((total_hires / total_applications * 100), 2) if total_applications > 0 else 0

    # Tempo medio assunzione
    hired_apps = applications_query.filter(
        JobApplication.status == ApplicationStatusEnum.hired
    ).all()

    time_to_hire_days = 0
    if hired_apps:
        total_days = 0
        count = 0
        for app in hired_apps:
            hired_history = ApplicationStageHistory.query.filter_by(
                application_id=app.id
            ).join(
                KanbanStage,
                ApplicationStageHistory.stage_id == KanbanStage.id
            ).filter(
                KanbanStage.stage_type == KanbanStageTypeEnum.hired
            ).order_by(ApplicationStageHistory.entered_at.asc()).first()

            if hired_history and app.created_at:
                days = (hired_history.entered_at - app.created_at).days
                total_days += days
                count += 1
        time_to_hire_days = round(total_days / count, 1) if count > 0 else 0

    # Score medio generale (escludi None e 0)
    applications_with_score = applications_query.filter(
        JobApplication.total_score.isnot(None),
        JobApplication.total_score > 0
    ).all()

    avg_score = 0
    if applications_with_score:
        total_score = sum(app.total_score for app in applications_with_score)
        avg_score = round(total_score / len(applications_with_score), 1)

    # ========== RIGHE 2-4: METRICHE PER PIATTAFORMA ==========

    # Costi totali per questa offerta (dai campi dell'offerta)
    linkedin_total_cost = offer.costo_totale_speso_linkedin or 0
    facebook_total_cost = offer.costo_totale_speso_facebook or 0
    instagram_total_cost = offer.costo_totale_speso_instagram or 0

    # LINKEDIN
    linkedin_apps = applications_query.filter(JobApplication.source == ApplicationSourceEnum.linkedin).all()
    linkedin_count = len(linkedin_apps)
    linkedin_hires = len([app for app in linkedin_apps if app.status == ApplicationStatusEnum.hired])
    linkedin_cost_per_app = round(linkedin_total_cost / linkedin_count, 2) if linkedin_count > 0 else 0
    linkedin_cost_per_hire = round(linkedin_total_cost / linkedin_hires, 2) if linkedin_hires > 0 else 0

    # Score medio LinkedIn (escludi None e 0)
    linkedin_scores = [app.total_score for app in linkedin_apps if app.total_score is not None and app.total_score > 0]
    linkedin_avg_score = round(sum(linkedin_scores) / len(linkedin_scores), 1) if linkedin_scores else 0

    # FACEBOOK
    facebook_apps = applications_query.filter(JobApplication.source == ApplicationSourceEnum.facebook).all()
    facebook_count = len(facebook_apps)
    facebook_hires = len([app for app in facebook_apps if app.status == ApplicationStatusEnum.hired])
    facebook_cost_per_app = round(facebook_total_cost / facebook_count, 2) if facebook_count > 0 else 0
    facebook_cost_per_hire = round(facebook_total_cost / facebook_hires, 2) if facebook_hires > 0 else 0

    # Score medio Facebook (escludi None e 0)
    facebook_scores = [app.total_score for app in facebook_apps if app.total_score is not None and app.total_score > 0]
    facebook_avg_score = round(sum(facebook_scores) / len(facebook_scores), 1) if facebook_scores else 0

    # INSTAGRAM
    instagram_apps = applications_query.filter(JobApplication.source == ApplicationSourceEnum.instagram).all()
    instagram_count = len(instagram_apps)
    instagram_hires = len([app for app in instagram_apps if app.status == ApplicationStatusEnum.hired])
    instagram_cost_per_app = round(instagram_total_cost / instagram_count, 2) if instagram_count > 0 else 0
    instagram_cost_per_hire = round(instagram_total_cost / instagram_hires, 2) if instagram_hires > 0 else 0

    # Score medio Instagram (escludi None e 0)
    instagram_scores = [app.total_score for app in instagram_apps if app.total_score is not None and app.total_score > 0]
    instagram_avg_score = round(sum(instagram_scores) / len(instagram_scores), 1) if instagram_scores else 0

    abort(404)

def _migrate_applications_to_new_kanban(offer_id, old_kanban_id, new_kanban_id):
    """
    Migra le candidature di un'offerta da una pipeline kanban a un'altra.
    
    Args:
        offer_id: ID dell'offerta
        old_kanban_id: ID del kanban di origine
        new_kanban_id: ID del kanban di destinazione
        
    Returns:
        int: Numero di candidature migrate
    """
    if old_kanban_id == new_kanban_id:
        return 0
    
    # Ottieni gli stage dei due kanban
    old_stages = {stage.stage_type: stage for stage in KanbanStage.query.filter_by(kanban_id=old_kanban_id, is_active=True).all()}
    new_stages = {stage.stage_type: stage for stage in KanbanStage.query.filter_by(kanban_id=new_kanban_id, is_active=True).all()}
    
    # Mapping dei tipi di stage per la migrazione
    stage_mapping = {}
    for stage_type, old_stage in old_stages.items():
        if stage_type in new_stages:
            stage_mapping[old_stage.id] = new_stages[stage_type].id
    
    # Se non ci sono mapping, usa il primo stage del nuovo kanban come fallback
    if not stage_mapping:
        first_new_stage = KanbanStage.query.filter_by(kanban_id=new_kanban_id, is_active=True).order_by(KanbanStage.order).first()
        if first_new_stage:
            # Mappa tutti gli stage vecchi al primo stage nuovo
            for old_stage in old_stages.values():
                stage_mapping[old_stage.id] = first_new_stage.id
    
    # Ottieni le candidature da migrare
    applications = JobApplication.query.filter_by(job_offer_id=offer_id).all()
    migrated_count = 0

    for app in applications:
        if app.kanban_stage_id in stage_mapping:
            old_stage_id = app.kanban_stage_id
            new_stage_id = stage_mapping[app.kanban_stage_id]

            # Aggiorna lo stage
            app.kanban_stage_id = new_stage_id
            migrated_count += 1

            # ===== TRACKING STORICO: Migrazione kanban =====
            # Chiudi il record storico del vecchio stage
            old_history = ApplicationStageHistory.query.filter_by(
                application_id=app.id,
                stage_id=old_stage_id,
                exited_at=None
            ).first()

            if old_history:
                old_history.exited_at = datetime.utcnow()
                old_history.calculate_duration()

            # Crea nuovo record storico per il nuovo stage
            new_history = ApplicationStageHistory(
                application_id=app.id,
                stage_id=new_stage_id,
                previous_stage_id=old_stage_id,
                entered_at=datetime.utcnow(),
                exited_at=None,
                duration_seconds=None,
                changed_by_id=current_user.id if hasattr(current_user, 'id') else None,
                notes=f'Migrato da kanban {old_kanban_id} a kanban {new_kanban_id}'
            )
            db.session.add(new_history)

    return migrated_count


# ============================================================================
# CV DOWNLOAD
# ============================================================================

@recruiting_bp.route("/applications/<int:application_id>/view-cv")
@login_required
def view_cv(application_id):
    """Visualizza il CV inline nel browser."""
    application = JobApplication.query.get_or_404(application_id)

    if not application.cv_file_path:
        abort(404, "Nessun CV disponibile per questa candidatura.")

    # Costruisci il percorso completo del file
    upload_folder = current_app.config['UPLOAD_FOLDER']
    # Rimuovi "uploads/" dal path se presente per evitare duplicazione
    cv_file_path = application.cv_file_path
    if cv_file_path.startswith('uploads/'):
        cv_file_path = cv_file_path[8:]  # Rimuove "uploads/"
    # Risolvi il path assoluto per evitare duplicazioni
    cv_path = os.path.abspath(os.path.join(upload_folder, cv_file_path))

    # Verifica che il file esista
    if not os.path.exists(cv_path):
        current_app.logger.error(f"CV file not found: {cv_path}")
        abort(404, "File CV non trovato.")

    try:
        # Invia il file per visualizzazione inline (non download)
        return send_file(
            cv_path,
            as_attachment=False,
            mimetype='application/pdf'
        )

    except Exception as e:
        current_app.logger.error(f"Error viewing CV for application {application_id}: {str(e)}")
        abort(500, "Errore durante la visualizzazione del CV.")


@recruiting_bp.route("/applications/<int:application_id>/download-cv")
@login_required
def download_cv(application_id):
    """Scarica il CV di una candidatura."""
    application = JobApplication.query.get_or_404(application_id)

    if not application.cv_file_path:
        flash("Nessun CV disponibile per questa candidatura.", "warning")
        return redirect(request.referrer or url_for('recruiting.applications_list'))

    # Costruisci il percorso completo del file
    upload_folder = current_app.config['UPLOAD_FOLDER']
    # Rimuovi "uploads/" dal path se presente per evitare duplicazione
    cv_file_path = application.cv_file_path
    if cv_file_path.startswith('uploads/'):
        cv_file_path = cv_file_path[8:]  # Rimuove "uploads/"
    # Risolvi il path assoluto per evitare duplicazioni
    cv_path = os.path.abspath(os.path.join(upload_folder, cv_file_path))

    # Verifica che il file esista
    if not os.path.exists(cv_path):
        current_app.logger.error(f"CV file not found: {cv_path}")
        flash("File CV non trovato.", "error")
        return redirect(request.referrer or url_for('recruiting.applications_list'))

    try:
        # Estrai il nome del file originale dal percorso
        filename = os.path.basename(cv_path)

        # Se il nome del file non è descrittivo, crea un nome migliore
        if not filename or filename.startswith('cv_'):
            file_ext = os.path.splitext(cv_path)[1]
            filename = f"CV_{application.first_name}_{application.last_name}{file_ext}"

        return send_file(
            cv_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )

    except Exception as e:
        current_app.logger.error(f"Error downloading CV for application {application_id}: {str(e)}")
        flash("Errore durante il download del CV.", "error")
        return redirect(request.referrer or url_for('recruiting.applications_list'))


# ============================================================================
# ADVERTISING COSTS ROUTES
# ============================================================================

@recruiting_bp.route("/offers/<int:offer_id>/advertising")
@login_required
def offer_advertising(offer_id):
    """
    Pagina gestione advertising costs per una specifica offerta.
    Mostra storico costi con filtri e form per aggiungere nuovi costi.
    """
    from corposostenibile.models import JobOfferAdvertisingCost, AdvertisingPlatformEnum, AdvertisingPeriodEnum

    offer = JobOffer.query.get_or_404(offer_id)

    # Filtri dalla query string
    platform_filter = request.args.get('platform')
    year_filter = request.args.get('year', type=int)
    month_filter = request.args.get('month', type=int)

    # Query base
    query = JobOfferAdvertisingCost.query.filter_by(job_offer_id=offer_id)

    # Applica filtri
    if platform_filter:
        try:
            query = query.filter_by(platform=AdvertisingPlatformEnum(platform_filter))
        except ValueError:
            pass

    if year_filter:
        query = query.filter_by(year=year_filter)

    if month_filter:
        query = query.filter_by(month=month_filter)

    # Ordina per data decrescente
    costs = query.order_by(
        JobOfferAdvertisingCost.year.desc(),
        JobOfferAdvertisingCost.month.desc(),
        JobOfferAdvertisingCost.period.desc()
    ).all()

    # Calcola totali per piattaforma
    totals_query = db.session.query(
        JobOfferAdvertisingCost.platform,
        func.sum(JobOfferAdvertisingCost.amount).label('total')
    ).filter_by(job_offer_id=offer_id)

    # Applica stessi filtri ai totali
    if year_filter:
        totals_query = totals_query.filter_by(year=year_filter)
    if month_filter:
        totals_query = totals_query.filter_by(month=month_filter)

    totals = totals_query.group_by(JobOfferAdvertisingCost.platform).all()

    totals_by_platform = {
        t.platform: float(t.total) for t in totals
    }

    grand_total = sum(totals_by_platform.values())

    # Anni disponibili per filtro (dal 2020 all'anno corrente + 1)
    current_year = datetime.now().year
    available_years = list(range(2020, current_year + 2))

    # Mesi (italiano)
    months_it = {
        1: 'Gennaio', 2: 'Febbraio', 3: 'Marzo', 4: 'Aprile',
        5: 'Maggio', 6: 'Giugno', 7: 'Luglio', 8: 'Agosto',
        9: 'Settembre', 10: 'Ottobre', 11: 'Novembre', 12: 'Dicembre'
    }

    abort(404)

@recruiting_bp.route("/advertising")
@login_required
def advertising_global():
    """
    Pagina globale con tutti i costi advertising di tutte le offerte.
    Dashboard con KPI, filtri avanzati e tabella completa.
    """
    from corposostenibile.models import JobOfferAdvertisingCost, AdvertisingPlatformEnum, AdvertisingPeriodEnum

    # Filtri dalla query string
    offer_id_filter = request.args.get('offer_id', type=int)
    platform_filter = request.args.get('platform')
    year_filter = request.args.get('year', type=int)
    month_filter = request.args.get('month', type=int)

    # Paginazione
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    # Query base con join per nome offerta
    query = JobOfferAdvertisingCost.query.join(JobOffer)

    # Applica filtri
    if offer_id_filter:
        query = query.filter(JobOfferAdvertisingCost.job_offer_id == offer_id_filter)

    if platform_filter:
        try:
            query = query.filter(JobOfferAdvertisingCost.platform == AdvertisingPlatformEnum(platform_filter))
        except ValueError:
            pass

    if year_filter:
        query = query.filter(JobOfferAdvertisingCost.year == year_filter)

    if month_filter:
        query = query.filter(JobOfferAdvertisingCost.month == month_filter)

    # Ordina per data decrescente
    query = query.order_by(
        JobOfferAdvertisingCost.year.desc(),
        JobOfferAdvertisingCost.month.desc(),
        JobOfferAdvertisingCost.period.desc()
    )

    # Pagina risultati
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Calcola totali globali (senza filtri paginazione, ma con filtri piattaforma/anno/mese)
    totals_query = db.session.query(
        JobOfferAdvertisingCost.platform,
        func.sum(JobOfferAdvertisingCost.amount).label('total')
    )

    # Applica stessi filtri ai totali
    if offer_id_filter:
        totals_query = totals_query.filter_by(job_offer_id=offer_id_filter)
    if platform_filter:
        try:
            totals_query = totals_query.filter(JobOfferAdvertisingCost.platform == AdvertisingPlatformEnum(platform_filter))
        except ValueError:
            pass
    if year_filter:
        totals_query = totals_query.filter_by(year=year_filter)
    if month_filter:
        totals_query = totals_query.filter_by(month=month_filter)

    totals = totals_query.group_by(JobOfferAdvertisingCost.platform).all()

    totals_by_platform = {
        t.platform: float(t.total) for t in totals
    }

    grand_total = sum(totals_by_platform.values())

    # Top offerte per spesa
    top_offers_query = db.session.query(
        JobOffer.id,
        JobOffer.title,
        func.sum(JobOfferAdvertisingCost.amount).label('total_spent')
    ).join(JobOfferAdvertisingCost).group_by(JobOffer.id, JobOffer.title)

    # Applica filtri anno/mese anche a top offers
    if year_filter:
        top_offers_query = top_offers_query.filter(JobOfferAdvertisingCost.year == year_filter)
    if month_filter:
        top_offers_query = top_offers_query.filter(JobOfferAdvertisingCost.month == month_filter)

    top_offers = top_offers_query.order_by(func.sum(JobOfferAdvertisingCost.amount).desc()).limit(10).all()

    # Lista offerte per filtro dropdown
    all_offers = JobOffer.query.order_by(JobOffer.created_at.desc()).all()

    # Anni disponibili
    current_year = datetime.now().year
    available_years = list(range(2020, current_year + 2))

    # Mesi (italiano)
    months_it = {
        1: 'Gennaio', 2: 'Febbraio', 3: 'Marzo', 4: 'Aprile',
        5: 'Maggio', 6: 'Giugno', 7: 'Luglio', 8: 'Agosto',
        9: 'Settembre', 10: 'Ottobre', 11: 'Novembre', 12: 'Dicembre'
    }

    abort(404)
