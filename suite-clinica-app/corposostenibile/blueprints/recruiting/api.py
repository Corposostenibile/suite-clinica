"""
API endpoints for Recruiting module
"""

from flask import request, jsonify, abort, current_app
from flask_login import login_required, current_user
from corposostenibile.extensions import db
from corposostenibile.models import (
    JobOffer, JobQuestion, JobApplication, ApplicationAnswer,
    ApplicationSourceEnum, JobOfferStatusEnum, ApplicationStatusEnum,
    KanbanStage, KanbanStageTypeEnum
)
from . import recruiting_bp
from datetime import datetime
import os
from werkzeug.utils import secure_filename


# ============================================================================
# PUBLIC API (for application forms)
# ============================================================================

@recruiting_bp.route("/api/apply", methods=["POST"])
def api_apply():
    """API pubblica per inviare candidatura."""
    data = request.get_json()
    
    # Validazione base
    required_fields = ['link_code', 'first_name', 'last_name', 'email']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Campo richiesto: {field}'}), 400
    
    link_code = data['link_code']
    
    # Trova offerta dal link
    offer = JobOffer.query.filter(
        db.or_(
            JobOffer.linkedin_link == link_code,
            JobOffer.facebook_link == link_code,
            JobOffer.instagram_link == link_code
        )
    ).first()
    
    if not offer:
        return jsonify({'error': 'Link non valido'}), 404
    
    if offer.status != JobOfferStatusEnum.published:
        return jsonify({'error': 'Offerta non disponibile'}), 400
    
    # Determina source
    if offer.linkedin_link == link_code:
        source = ApplicationSourceEnum.linkedin
    elif offer.facebook_link == link_code:
        source = ApplicationSourceEnum.facebook
    else:
        source = ApplicationSourceEnum.instagram
    
    # Verifica se email già candidata
    existing = JobApplication.query.filter_by(
        job_offer_id=offer.id,
        email=data['email']
    ).first()
    
    if existing:
        return jsonify({'error': 'Ti sei già candidato per questa posizione'}), 400
    
    # Crea application
    application = JobApplication(
        job_offer_id=offer.id,
        first_name=data['first_name'],
        last_name=data['last_name'],
        email=data['email'],
        phone=data.get('phone'),
        linkedin_profile=data.get('linkedin_profile'),
        portfolio_url=data.get('portfolio_url'),
        cover_letter=data.get('cover_letter'),
        source=source,
        source_link=link_code
    )
    
    # Gestisci CV upload (sarà inviato separatamente via form-data)
    # Questo è gestito in api_upload_cv
    
    # Salva risposte alle domande
    answers_data = data.get('answers', {})
    for question in offer.questions:
        answer_value = answers_data.get(str(question.id))
        
        if question.is_required and not answer_value:
            return jsonify({'error': f'Domanda obbligatoria: {question.question_text}'}), 400
        
        if answer_value:
            answer = ApplicationAnswer(
                question_id=question.id,
                answer_text=answer_value if isinstance(answer_value, str) else None,
                answer_json=answer_value if isinstance(answer_value, (list, dict)) else None
            )
            application.answers.append(answer)
    
    # Incrementa counter
    offer.applications_count += 1
    
    # Assegna a primo stage del kanban
    if offer.kanban:
        first_stage = min(offer.kanban.stages, key=lambda s: s.order)
        if first_stage:
            application.kanban_stage_id = first_stage.id

    db.session.add(application)
    db.session.flush()  # Ottieni l'ID dell'application prima del commit

    # ===== TRACCIAMENTO AUTOMATICO HISTORY (ANALYTICS 10/10) =====
    # Crea record storico per tracking fin dal primo stage
    if application.kanban_stage_id:
        from corposostenibile.models import ApplicationStageHistory
        initial_history = ApplicationStageHistory(
            application_id=application.id,
            stage_id=application.kanban_stage_id,
            previous_stage_id=None,
            entered_at=datetime.utcnow(),
            exited_at=None,
            duration_seconds=None,
            changed_by_id=None,  # auto-assigned dalla form pubblica
            notes='Candidatura ricevuta - assegnazione automatica al primo stage'
        )
        db.session.add(initial_history)

    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Candidatura inviata con successo!',
        'application_id': application.id
    })


@recruiting_bp.route("/api/apply/upload-cv", methods=["POST"])
def api_upload_cv():
    """Upload CV per candidatura."""
    application_id = request.form.get('application_id', type=int)
    
    if not application_id:
        return jsonify({'error': 'Application ID richiesto'}), 400
    
    application = JobApplication.query.get_or_404(application_id)
    
    if 'cv' not in request.files:
        return jsonify({'error': 'Nessun file CV'}), 400
    
    file = request.files['cv']
    if file.filename == '':
        return jsonify({'error': 'File non selezionato'}), 400
    
    # Verifica estensione
    allowed_extensions = {'pdf', 'doc', 'docx', 'txt'}
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    
    if ext not in allowed_extensions:
        return jsonify({'error': f'Formato non supportato. Usa: {", ".join(allowed_extensions)}'}), 400
    
    # Salva file
    filename = secure_filename(f"{application.id}_{application.last_name}_{file.filename}")
    upload_path = os.path.join(
        current_app.config['UPLOAD_FOLDER'],
        'recruiting',
        'cvs',
        str(application.job_offer_id)
    )
    
    os.makedirs(upload_path, exist_ok=True)
    
    file_path = os.path.join(upload_path, filename)
    file.save(file_path)
    
    # Salva path relativo
    application.cv_file_path = os.path.relpath(file_path, current_app.config['UPLOAD_FOLDER'])
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'CV caricato con successo'
    })


# ============================================================================
# INTERNAL API (authenticated)
# ============================================================================

@recruiting_bp.route("/api/offers/<int:offer_id>/stats")
@login_required
def api_offer_stats(offer_id):
    """Statistiche per offerta di lavoro."""
    offer = JobOffer.query.get_or_404(offer_id)
    
    stats = {
        'views': offer.views_count,
        'applications': offer.applications_count,
        'conversion_rate': (offer.applications_count / offer.views_count * 100) 
                          if offer.views_count > 0 else 0,
        'by_source': {},
        'by_status': {},
        'by_stage': {},
        'score_distribution': {
            '0-20': 0,
            '20-40': 0,
            '40-60': 0,
            '60-80': 0,
            '80-100': 0
        }
    }
    
    # Analizza applications
    for app in offer.applications:
        # Per source
        source = app.source.value if app.source else 'direct'
        stats['by_source'][source] = stats['by_source'].get(source, 0) + 1
        
        # Per status
        status = app.status.value if app.status else 'new'
        stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
        
        # Per stage kanban
        if app.kanban_stage:
            stage_name = app.kanban_stage.name
            stats['by_stage'][stage_name] = stats['by_stage'].get(stage_name, 0) + 1
        
        # Distribuzione score
        if app.total_score is not None:
            if app.total_score < 20:
                stats['score_distribution']['0-20'] += 1
            elif app.total_score < 40:
                stats['score_distribution']['20-40'] += 1
            elif app.total_score < 60:
                stats['score_distribution']['40-60'] += 1
            elif app.total_score < 80:
                stats['score_distribution']['60-80'] += 1
            else:
                stats['score_distribution']['80-100'] += 1
    
    return jsonify(stats)


@recruiting_bp.route("/api/questions/validate", methods=["POST"])
@login_required
def api_validate_questions():
    """Valida configurazione domande."""
    data = request.get_json()
    questions = data.get('questions', [])
    
    errors = []
    total_weight = 0
    
    for idx, q in enumerate(questions):
        # Validazione base
        if not q.get('question_text'):
            errors.append(f"Domanda {idx+1}: testo richiesto")
        
        if not q.get('question_type'):
            errors.append(f"Domanda {idx+1}: tipo richiesto")
        
        # Validazione peso
        weight = q.get('weight', 0)
        try:
            weight = float(weight)
            if weight < 0 or weight > 100:
                errors.append(f"Domanda {idx+1}: peso deve essere tra 0 e 100")
            total_weight += weight
        except (TypeError, ValueError):
            errors.append(f"Domanda {idx+1}: peso non valido")
        
        # Validazione per tipo
        q_type = q.get('question_type')
        
        if q_type in ['select', 'multiselect', 'radio', 'checkbox']:
            options = q.get('options', [])
            if not options:
                errors.append(f"Domanda {idx+1}: opzioni richieste per tipo {q_type}")
        
        if q_type == 'number':
            if q.get('expected_min') is not None and q.get('expected_max') is not None:
                try:
                    min_val = float(q['expected_min'])
                    max_val = float(q['expected_max'])
                    if min_val > max_val:
                        errors.append(f"Domanda {idx+1}: min > max")
                except (TypeError, ValueError):
                    errors.append(f"Domanda {idx+1}: valori min/max non validi")
    
    # Verifica peso totale
    if abs(total_weight - 100) > 0.01:
        errors.append(f"Il peso totale deve essere 100%, attualmente è {total_weight:.1f}%")
    
    if errors:
        return jsonify({
            'valid': False,
            'errors': errors
        }), 400
    
    return jsonify({
        'valid': True,
        'message': 'Configurazione valida',
        'total_weight': total_weight
    })


@recruiting_bp.route("/api/applications/<int:application_id>/reject", methods=["POST"])
@login_required
def api_reject_application(application_id):
    """Rifiuta candidatura."""
    application = JobApplication.query.get_or_404(application_id)
    
    data = request.get_json()
    reason = data.get('reason', '')
    
    application.status = ApplicationStatusEnum.rejected
    application.rejection_reason = reason
    
    # Sposta a stage rejected se esiste
    if application.job_offer.kanban:
        rejected_stage = KanbanStage.query.filter_by(
            kanban_id=application.job_offer.kanban_id,
            stage_type=KanbanStageTypeEnum.rejected
        ).first()
        
        if rejected_stage:
            application.kanban_stage_id = rejected_stage.id
    
    db.session.commit()
    
    # TODO: Invia email di rifiuto se configurato
    
    return jsonify({
        'success': True,
        'message': 'Candidatura rifiutata'
    })


@recruiting_bp.route("/api/applications/<int:application_id>/schedule-interview", methods=["POST"])
@login_required
def api_schedule_interview(application_id):
    """Programma colloquio per candidatura."""
    application = JobApplication.query.get_or_404(application_id)
    
    data = request.get_json()
    
    # Validazione
    if not data.get('interview_date'):
        return jsonify({'error': 'Data colloquio richiesta'}), 400
    
    try:
        interview_date = datetime.fromisoformat(data['interview_date'])
    except ValueError:
        return jsonify({'error': 'Formato data non valido'}), 400
    
    # Aggiorna application
    application.interview_date = interview_date
    application.status = ApplicationStatusEnum.interview_scheduled
    application.notes = data.get('notes', '')
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Colloquio programmato con successo',
        'interview_date': interview_date.isoformat()
    })


@recruiting_bp.route("/api/applications/<int:application_id>/approve", methods=["POST"])
@login_required
def api_approve_application(application_id):
    """Approva e assume candidatura."""
    current_app.logger.error(f"[ATS-API] ===== APPROVAZIONE CANDIDATURA =====")
    current_app.logger.error(f"[ATS-API] Application ID: {application_id}")
    current_app.logger.error(f"[ATS-API] Utente richiedente: {current_user.email if current_user else 'N/A'}")
    
    application = JobApplication.query.get_or_404(application_id)
    current_app.logger.error(f"[ATS-API] Candidato: {application.full_name}")
    current_app.logger.error(f"[ATS-API] Offerta: {application.job_offer.title if application.job_offer else 'N/A'}")
    
    data = request.get_json() or {}
    notes = data.get('notes', '')
    start_date = data.get('start_date')
    
    current_app.logger.error(f"[ATS-API] Note approvazione: {notes[:100] if notes else 'Nessuna nota'}")
    current_app.logger.error(f"[ATS-API] Data inizio proposta: {start_date or 'Non specificata'}")
    
    try:
        # Aggiorna status a hired
        application.status = ApplicationStatusEnum.hired
        application.hired_at = datetime.utcnow()
        application.internal_notes = f"{application.internal_notes or ''}\n[APPROVATO] {notes}".strip()
        
        if start_date:
            try:
                application.start_date = datetime.fromisoformat(start_date)
                current_app.logger.error(f"[ATS-API] ✅ Data inizio impostata: {start_date}")
            except ValueError:
                current_app.logger.warning(f"[ATS-API] ⚠️ Formato data inizio non valido: {start_date}")
        
        # Sposta a stage hired se esiste nel kanban
        if application.job_offer and application.job_offer.kanban:
            from corposostenibile.models import KanbanStage, KanbanStageTypeEnum
            hired_stage = KanbanStage.query.filter_by(
                kanban_id=application.job_offer.kanban_id,
                stage_type=KanbanStageTypeEnum.hired
            ).first()
            
            if hired_stage:
                application.kanban_stage_id = hired_stage.id
                current_app.logger.error(f"[ATS-API] ✅ Spostato nel kanban stage: {hired_stage.name}")
            else:
                current_app.logger.warning(f"[ATS-API] ⚠️ Stage 'hired' non trovato nel kanban")
        
        db.session.commit()
        current_app.logger.error(f"[ATS-API] ✅ Candidatura approvata con successo")
        
        # TODO: Invia email di conferma assunzione
        # TODO: Avvia processo di onboarding automatico
        
        return jsonify({
            'success': True,
            'message': f'Candidatura di {application.full_name} approvata! Procedi con l\'onboarding.',
            'application_id': application.id,
            'onboarding_url': f'/recruiting/onboarding/start/{application.id}'
        })
        
    except Exception as e:
        current_app.logger.error(f"[ATS-API] ❌ Errore nell'approvazione: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Errore nell\'approvazione: {str(e)}'
        }), 500


@recruiting_bp.route("/api/applications/<int:application_id>/send-offer", methods=["POST"])
@login_required
def api_send_offer(application_id):
    """Invia offerta di lavoro al candidato."""
    current_app.logger.error(f"[ATS-API] ===== INVIO OFFERTA =====")
    current_app.logger.error(f"[ATS-API] Application ID: {application_id}")
    current_app.logger.error(f"[ATS-API] Utente richiedente: {current_user.email if current_user else 'N/A'}")
    
    application = JobApplication.query.get_or_404(application_id)
    current_app.logger.error(f"[ATS-API] Candidato: {application.full_name}")
    current_app.logger.error(f"[ATS-API] Email candidato: {application.email}")
    
    data = request.get_json() or {}
    salary_offer = data.get('salary_offer')
    start_date = data.get('start_date')
    message = data.get('message', '')
    
    current_app.logger.error(f"[ATS-API] Offerta salariale: {salary_offer or 'Non specificata'}")
    current_app.logger.error(f"[ATS-API] Data inizio: {start_date or 'Non specificata'}")
    current_app.logger.error(f"[ATS-API] Messaggio personalizzato: {message[:100] if message else 'Nessun messaggio'}")
    
    try:
        # Aggiorna status
        application.status = ApplicationStatusEnum.offer_sent
        application.offer_sent_at = datetime.utcnow()
        application.salary_offer = salary_offer
        
        if start_date:
            try:
                application.start_date = datetime.fromisoformat(start_date)
                current_app.logger.error(f"[ATS-API] ✅ Data inizio impostata: {start_date}")
            except ValueError:
                current_app.logger.warning(f"[ATS-API] ⚠️ Formato data inizio non valido: {start_date}")
        
        # Aggiorna note interne
        offer_note = f"[OFFERTA INVIATA] Salario: {salary_offer or 'N/A'}, Inizio: {start_date or 'N/A'}"
        if message:
            offer_note += f", Messaggio: {message}"
        application.internal_notes = f"{application.internal_notes or ''}\n{offer_note}".strip()
        
        # Sposta nel kanban se esiste
        if application.job_offer and application.job_offer.kanban:
            from corposostenibile.models import KanbanStage, KanbanStageTypeEnum
            offer_stage = KanbanStage.query.filter_by(
                kanban_id=application.job_offer.kanban_id,
                stage_type=KanbanStageTypeEnum.offer_sent
            ).first()
            
            if offer_stage:
                application.kanban_stage_id = offer_stage.id
                current_app.logger.error(f"[ATS-API] ✅ Spostato nel kanban stage: {offer_stage.name}")
        
        db.session.commit()
        current_app.logger.error(f"[ATS-API] ✅ Offerta registrata con successo")
        
        # TODO: Invia email con template offerta
        # TODO: Genera PDF contratto se configurato
        
        return jsonify({
            'success': True,
            'message': f'Offerta inviata a {application.full_name}',
            'application_id': application.id
        })
        
    except Exception as e:
        current_app.logger.error(f"[ATS-API] ❌ Errore nell'invio offerta: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Errore nell\'invio offerta: {str(e)}'
        }), 500


@recruiting_bp.route("/api/applications/<int:application_id>/request-info", methods=["POST"])
@login_required
def api_request_info(application_id):
    """Richiedi informazioni aggiuntive al candidato."""
    current_app.logger.error(f"[ATS-API] ===== RICHIESTA INFORMAZIONI =====")
    current_app.logger.error(f"[ATS-API] Application ID: {application_id}")
    current_app.logger.error(f"[ATS-API] Utente richiedente: {current_user.email if current_user else 'N/A'}")
    
    application = JobApplication.query.get_or_404(application_id)
    current_app.logger.error(f"[ATS-API] Candidato: {application.full_name}")
    current_app.logger.error(f"[ATS-API] Email candidato: {application.email}")
    
    data = request.get_json() or {}
    subject = data.get('subject', 'Richiesta informazioni aggiuntive')
    message = data.get('message', '')
    info_type = data.get('info_type', 'general')  # general, documents, references, etc.
    
    current_app.logger.error(f"[ATS-API] Oggetto: {subject}")
    current_app.logger.error(f"[ATS-API] Tipo informazioni: {info_type}")
    current_app.logger.error(f"[ATS-API] Messaggio: {message[:100] if message else 'Nessun messaggio'}")
    
    if not message.strip():
        return jsonify({
            'success': False,
            'message': 'Il messaggio è obbligatorio'
        }), 400
    
    try:
        # Aggiorna note interne
        info_note = f"[INFO RICHIESTE] Tipo: {info_type}, Oggetto: {subject}"
        application.internal_notes = f"{application.internal_notes or ''}\n{info_note}".strip()
        
        # Aggiorna timestamp ultima comunicazione
        application.last_contact_at = datetime.utcnow()
        
        db.session.commit()
        current_app.logger.error(f"[ATS-API] ✅ Richiesta informazioni registrata")
        
        # TODO: Invia email con richiesta informazioni
        # TODO: Crea task di follow-up automatico
        
        return jsonify({
            'success': True,
            'message': f'Richiesta informazioni inviata a {application.full_name}',
            'application_id': application.id
        })
        
    except Exception as e:
        current_app.logger.error(f"[ATS-API] ❌ Errore nella richiesta informazioni: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Errore nella richiesta informazioni: {str(e)}'
        }), 500


@recruiting_bp.route("/api/applications/<int:application_id>/screen", methods=["POST"])
@login_required
def api_screen_application(application_id):
    """Avvia screening ATS per una singola candidatura (permette re-screening)."""
    current_app.logger.error(f"[ATS-API] ===== SCREENING SINGOLA CANDIDATURA =====")
    current_app.logger.error(f"[ATS-API] Application ID richiesta: {application_id}")
    current_app.logger.error(f"[ATS-API] Utente richiedente: {current_user.email if current_user else 'N/A'}")
    
    application = JobApplication.query.get_or_404(application_id)
    current_app.logger.error(f"[ATS-API] Candidatura trovata: {application.first_name} {application.last_name} ({application.email})")
    current_app.logger.error(f"[ATS-API] Job Offer: {application.job_offer.title if application.job_offer else 'N/A'}")
    current_app.logger.error(f"[ATS-API] Status attuale: {application.status}")
    
    # Permetti re-screening - rimuovi il controllo che bloccava candidature già screenate
    if application.screened_at:
        current_app.logger.error(f"[ATS-API] ⚠️ Candidatura già sottoposta a screening il {application.screened_at} - procedo con re-screening")
    else:
        current_app.logger.error(f"[ATS-API] Candidatura non ancora sottoposta a screening, procedo...")
    
    try:
        # Importa il modulo ATS
        current_app.logger.error(f"[ATS-API] Import modulo ATS...")
        from .ats import ATSAnalyzer
        
        # Crea analyzer e esegui analisi
        current_app.logger.error(f"[ATS-API] Creazione ATSAnalyzer per candidatura {application_id}")
        analyzer = ATSAnalyzer(application)
        
        current_app.logger.error(f"[ATS-API] Avvio analisi ATS...")
        analysis_results = analyzer.analyze()
        current_app.logger.error(f"[ATS-API] Analisi ATS completata")
        
        # Calcola e salva punteggi
        current_app.logger.error(f"[ATS-API] Calcolo punteggi finali...")
        application.calculate_scores()
        application.screened_at = datetime.utcnow()
        current_app.logger.error(f"[ATS-API] Punteggi calcolati - Total: {application.total_score}%, CV: {application.cv_score}%, Form: {application.form_score}%")
        
        # Aggiorna status se necessario
        if application.status.value == 'new':
            current_app.logger.error(f"[ATS-API] Aggiornamento status da 'new' a 'reviewed'")
            from corposostenibile.models import ApplicationStatusEnum
            application.status = ApplicationStatusEnum.reviewed
        
        # Se c'è un kanban, sposta alla fase appropriata
        if application.job_offer and application.job_offer.kanban:
            current_app.logger.error(f"[ATS-API] Kanban presente, ricerca stage di screening...")
            from corposostenibile.models import KanbanStage, KanbanStageTypeEnum
            
            # Trova la fase di screening o reviewed
            screening_stage = KanbanStage.query.filter_by(
                kanban_id=application.job_offer.kanban_id,
                stage_type=KanbanStageTypeEnum.screening
            ).first()
            
            if screening_stage:
                current_app.logger.error(f"[ATS-API] Stage di screening trovato (ID: {screening_stage.id}), spostamento candidatura")
                application.kanban_stage_id = screening_stage.id
            else:
                current_app.logger.warning(f"[ATS-API] Stage di screening non trovato nel kanban")
        else:
            current_app.logger.error(f"[ATS-API] Nessun kanban associato al job offer")
        
        current_app.logger.error(f"[ATS-API] Salvataggio nel database...")
        db.session.commit()
        current_app.logger.error(f"[ATS-API] ✅ Screening singola candidatura completato con successo")
        
        return jsonify({
            'success': True,
            'message': 'Screening ATS completato con successo',
            'scores': {
                'total_score': application.total_score,
                'form_score': application.form_score,
                'cv_score': application.cv_score
            },
            'analysis': analysis_results
        })
        
    except Exception as e:
        current_app.logger.error(f"[ATS-API] ❌ ERRORE durante screening ATS candidatura {application_id}: {str(e)}")
        current_app.logger.error(f"[ATS-API] Exception type: {type(e).__name__}")
        import traceback
        current_app.logger.error(f"[ATS-API] Traceback: {traceback.format_exc()}")
        
        db.session.rollback()
        current_app.logger.error(f"[ATS-API] Database rollback completato")
        
        return jsonify({
            'success': False,
            'message': f'Errore durante lo screening: {str(e)}'
        }), 500


@recruiting_bp.route("/api/offers/active")
@login_required
def api_active_offers():
    """Lista offerte attive per screening ATS."""
    offers = JobOffer.query.filter_by(
        status=JobOfferStatusEnum.published
    ).order_by(JobOffer.title).all()
    
    offers_data = []
    for offer in offers:
        # Conta candidature non ancora analizzate
        unscreened_count = offer.applications.filter(
            JobApplication.screened_at.is_(None)
        ).count()
        
        offers_data.append({
            'id': offer.id,
            'title': offer.title,
            'department': offer.department.name if offer.department else 'N/A',
            'total_applications': offer.applications.count(),
            'unscreened_applications': unscreened_count,
            'created_at': offer.created_at.isoformat()
        })
    
    return jsonify({
        'success': True,
        'offers': offers_data
    })


@recruiting_bp.route("/api/offers/<int:offer_id>/applications/unscreened")
@login_required
def api_offer_unscreened_applications(offer_id):
    """Lista candidature non ancora analizzate per un'offerta."""
    offer = JobOffer.query.get_or_404(offer_id)
    
    applications = offer.applications.filter(
        JobApplication.screened_at.is_(None)
    ).all()
    
    applications_data = []
    for app in applications:
        applications_data.append({
            'id': app.id,
            'full_name': f"{app.first_name} {app.last_name}",
            'email': app.email,
            'source': app.source.value if app.source else 'direct',
            'created_at': app.created_at.isoformat(),
            'status': app.status.value if hasattr(app.status, 'value') else str(app.status)
        })
    
    return jsonify({
        'success': True,
        'offer_title': offer.title,
        'applications': applications_data
    })


@recruiting_bp.route("/api/offers/<int:offer_id>/screen-all", methods=["POST"])
@login_required
def api_screen_all_applications(offer_id):
    """Avvia screening ATS per tutte le candidature di un'offerta."""
    current_app.logger.error(f"[ATS-API] ===== SCREENING BATCH CANDIDATURE =====")
    current_app.logger.error(f"[ATS-API] Offer ID richiesta: {offer_id}")
    current_app.logger.error(f"[ATS-API] Utente richiedente: {current_user.email if current_user else 'N/A'}")
    
    offer = JobOffer.query.get_or_404(offer_id)
    current_app.logger.error(f"[ATS-API] Job Offer trovata: {offer.title}")
    current_app.logger.error(f"[ATS-API] Dipartimento: {offer.department.name if offer.department else 'N/A'}")
    
    data = request.get_json()
    screening_type = data.get('screening_type', 'all')  # 'all', 'new', o 'rescreen_all'
    auto_reject = data.get('auto_reject', False)
    min_score = data.get('min_score', 40)
    max_batch_size = data.get('max_batch_size', 3)  # Limite RIDOTTO a 3 per evitare timeout (AI ~30s/candidatura)
    
    current_app.logger.error(f"[ATS-API] Parametri screening:")
    current_app.logger.error(f"[ATS-API] - Tipo screening: {screening_type}")
    current_app.logger.error(f"[ATS-API] - Auto reject: {auto_reject}")
    current_app.logger.error(f"[ATS-API] - Punteggio minimo: {min_score}%")
    current_app.logger.error(f"[ATS-API] - Max batch size: {max_batch_size}")
    
    # Determina quali candidature analizzare
    if screening_type == 'new':
        current_app.logger.error(f"[ATS-API] Filtro candidature: solo status 'new' non ancora screened")
        from corposostenibile.models import ApplicationStatusEnum
        applications = offer.applications.filter(
            JobApplication.screened_at.is_(None),
            JobApplication.status == ApplicationStatusEnum.new
        ).all()
    elif screening_type == 'rescreen_all':
        current_app.logger.error(f"[ATS-API] Filtro candidature: TUTTE le candidature (incluse quelle già screened)")
        applications = offer.applications.all()
    else:
        current_app.logger.error(f"[ATS-API] Filtro candidature: tutte quelle non ancora screened")
        applications = offer.applications.filter(
            JobApplication.screened_at.is_(None)
        ).all()
    
    current_app.logger.error(f"[ATS-API] Candidature trovate da processare: {len(applications)}")

    if not applications:
        current_app.logger.warning(f"[ATS-API] ❌ Nessuna candidatura da analizzare")
        return jsonify({
            'success': False,
            'message': 'Nessuna candidatura da analizzare'
        }), 400

    # IMPORTANTE: Limita il batch per evitare timeout
    total_applications = len(applications)
    if len(applications) > max_batch_size:
        current_app.logger.error(f"[ATS-API] ⚠️ Batch troppo grande ({total_applications}), limitato a {max_batch_size} candidature")
        current_app.logger.error(f"[ATS-API] ⚠️ Esegui lo screening multiple volte per processare tutte le candidature")
        applications = applications[:max_batch_size]
    
    # Log dettagli candidature
    for i, app in enumerate(applications):
        current_app.logger.error(f"[ATS-API] Candidatura {i+1}/{len(applications)}: ID {app.id}, {app.first_name} {app.last_name}, Status: {app.status}")
    
    results = {
        'processed': 0,
        'success': 0,
        'errors': 0,
        'scores': [],
        'rejected': 0
    }
    
    try:
        # Importa il modulo ATS
        current_app.logger.error(f"[ATS-API] Import moduli ATS...")
        from .ats import ATSAnalyzer
        from corposostenibile.models import ApplicationStatusEnum, KanbanStage, KanbanStageTypeEnum
        
        current_app.logger.error(f"[ATS-API] ===== INIZIO PROCESSING BATCH =====")
        
        for i, application in enumerate(applications):
            current_app.logger.error(f"[ATS-API] ===== PROCESSING CANDIDATURA {i+1}/{len(applications)} - ID {application.id} =====")
            current_app.logger.error(f"[ATS-API] Candidato: {application.first_name} {application.last_name} ({application.email})")
            
            try:
                # Crea analyzer e esegui analisi
                current_app.logger.error(f"[ATS-API] Creazione ATSAnalyzer per candidatura {application.id}")
                analyzer = ATSAnalyzer(application)
                
                current_app.logger.error(f"[ATS-API] Avvio analisi ATS...")
                analysis_results = analyzer.analyze()
                current_app.logger.error(f"[ATS-API] Analisi ATS completata")
                
                # Calcola e salva punteggi
                current_app.logger.error(f"[ATS-API] Calcolo punteggi finali...")
                application.calculate_scores()
                application.screened_at = datetime.utcnow()
                current_app.logger.error(f"[ATS-API] Punteggi calcolati - Total: {application.total_score}%, CV: {application.cv_score}%, Form: {application.form_score}%")
                
                # Aggiorna status se necessario
                if hasattr(application.status, 'value') and application.status.value == 'new':
                    current_app.logger.error(f"[ATS-API] Aggiornamento status da 'new' a 'reviewed'")
                    application.status = ApplicationStatusEnum.reviewed
                
                # Se c'è un kanban, sposta alla fase appropriata
                if offer.kanban:
                    current_app.logger.error(f"[ATS-API] Kanban presente, ricerca stage di screening...")
                    # Trova la fase di screening o reviewed
                    screening_stage = KanbanStage.query.filter_by(
                        kanban_id=offer.kanban_id,
                        stage_type=KanbanStageTypeEnum.screening
                    ).first()
                    
                    if screening_stage:
                        current_app.logger.error(f"[ATS-API] Stage di screening trovato (ID: {screening_stage.id}), spostamento candidatura")
                        application.kanban_stage_id = screening_stage.id
                    else:
                        current_app.logger.warning(f"[ATS-API] Stage di screening non trovato nel kanban")
                else:
                    current_app.logger.error(f"[ATS-API] Nessun kanban associato al job offer")
                
                # Auto-reject se richiesto e punteggio basso
                if auto_reject and application.total_score and application.total_score < min_score:
                    current_app.logger.error(f"[ATS-API] ❌ AUTO-REJECT: punteggio {application.total_score}% < {min_score}%")
                    application.status = ApplicationStatusEnum.rejected
                    application.rejection_reason = f"Rifiutato automaticamente: punteggio {application.total_score}% < {min_score}%"
                    results['rejected'] += 1
                else:
                    current_app.logger.error(f"[ATS-API] ✅ Candidatura processata con successo")
                
                results['success'] += 1
                if application.total_score:
                    results['scores'].append(application.total_score)
                
            except Exception as e:
                current_app.logger.error(f"[ATS-API] ❌ ERRORE screening candidatura {application.id}: {str(e)}")
                current_app.logger.error(f"[ATS-API] Exception type: {type(e).__name__}")
                import traceback
                current_app.logger.error(f"[ATS-API] Traceback: {traceback.format_exc()}")
                results['errors'] += 1

                # IMPORTANTE: Marca come screened anche in caso di errore per evitare loop infinito!
                application.screened_at = datetime.utcnow()

                # Salva l'errore nelle note interne
                error_message = f"[ERRORE SCREENING {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}]\n{type(e).__name__}: {str(e)}"
                if application.internal_notes:
                    application.internal_notes = f"{application.internal_notes}\n\n{error_message}"
                else:
                    application.internal_notes = error_message
                current_app.logger.error(f"[ATS-API] ⚠️ Candidatura {application.id} marcata come screened con errore per evitare riprocessamento")

                # Se è un errore di file CV non trovato, interrompi il processo e ritorna l'errore al frontend
                if isinstance(e, FileNotFoundError) and "CV file not found" in str(e):
                    current_app.logger.error(f"[ATS-API] ❌ ERRORE CRITICO: CV file non trovato per candidatura {application.id}")
                    db.session.rollback()
                    return jsonify({
                        'success': False,
                        'message': f'Errore: CV file non trovato per la candidatura {application.id}. Percorso: {str(e)}',
                        'error_type': 'cv_file_not_found',
                        'application_id': application.id
                    }), 400
            
            results['processed'] += 1
            current_app.logger.error(f"[ATS-API] Candidatura {application.id} processata ({results['processed']}/{len(applications)})")
        
        current_app.logger.error(f"[ATS-API] ===== FINE PROCESSING BATCH =====")
        current_app.logger.error(f"[ATS-API] Salvataggio risultati nel database...")
        db.session.commit()
        current_app.logger.error(f"[ATS-API] ✅ Database commit completato")
        
        # Calcola statistiche finali
        avg_score = sum(results['scores']) / len(results['scores']) if results['scores'] else 0
        current_app.logger.error(f"[ATS-API] ===== STATISTICHE FINALI =====")
        current_app.logger.error(f"[ATS-API] Candidature processate: {results['processed']}")
        current_app.logger.error(f"[ATS-API] Successi: {results['success']}")
        current_app.logger.error(f"[ATS-API] Errori: {results['errors']}")
        current_app.logger.error(f"[ATS-API] Auto-reject: {results['rejected']}")
        current_app.logger.error(f"[ATS-API] Punteggio medio: {round(avg_score, 1)}%")
        
        # Calcola quante candidature rimangono
        remaining = total_applications - results['processed']

        message = f'Screening completato! Analizzate {results["processed"]} candidature.'
        if remaining > 0:
            message += f' Rimangono {remaining} candidature da processare - esegui nuovamente lo screening.'

        return jsonify({
            'success': True,
            'message': message,
            'results': {
                'processed': results['processed'],
                'success': results['success'],
                'errors': results['errors'],
                'rejected': results['rejected'],
                'avg_score': round(avg_score, 1),
                'remaining': remaining,
                'total_found': total_applications
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"[ATS-API] ❌ ERRORE CRITICO durante screening batch: {str(e)}")
        current_app.logger.error(f"[ATS-API] Exception type: {type(e).__name__}")
        import traceback
        current_app.logger.error(f"[ATS-API] Traceback: {traceback.format_exc()}")
        
        db.session.rollback()
        current_app.logger.error(f"[ATS-API] Database rollback completato")
        
        return jsonify({
            'success': False,
            'message': f'Errore durante lo screening: {str(e)}'
        }), 500


@recruiting_bp.route("/api/dashboard/stats")
@login_required
def api_dashboard_stats():
    """Statistiche generali recruiting."""
    # Query ottimizzate per dashboard
    from sqlalchemy import func
    
    stats = {
        'offers': {
            'total': JobOffer.query.count(),
            'active': JobOffer.query.filter_by(status=JobOfferStatusEnum.published).count(),
            'draft': JobOffer.query.filter_by(status=JobOfferStatusEnum.draft).count(),
            'closed': JobOffer.query.filter_by(status=JobOfferStatusEnum.closed).count()
        },
        'applications': {
            'total': JobApplication.query.count(),
            'this_month': JobApplication.query.filter(
                JobApplication.created_at >= datetime.utcnow().replace(day=1)
            ).count(),
            'pending_review': JobApplication.query.filter_by(status=ApplicationStatusEnum.new).count(),
            'in_pipeline': JobApplication.query.filter(
                JobApplication.status.notin_([
                    ApplicationStatusEnum.hired,
                    ApplicationStatusEnum.rejected
                ])
            ).count()
        },
        'hiring': {
            'hired_this_month': JobApplication.query.filter(
                JobApplication.status == ApplicationStatusEnum.hired,
                JobApplication.updated_at >= datetime.utcnow().replace(day=1)
            ).count(),
            'conversion_rate': 0  # Calcolato sotto
        },
        'onboarding': {
            'active': OnboardingChecklist.query.filter(
                OnboardingChecklist.completed_at.is_(None)
            ).count()
        }
    }
    
    # Calcola conversion rate
    total = stats['applications']['total']
    hired = JobApplication.query.filter_by(status=ApplicationStatusEnum.hired).count()
    
    if total > 0:
        stats['hiring']['conversion_rate'] = round((hired / total) * 100, 2)
    
    # Top sources
    top_sources = db.session.query(
        JobApplication.source,
        func.count(JobApplication.id).label('count')
    ).group_by(JobApplication.source).order_by(func.count(JobApplication.id).desc()).limit(5).all()
    
    stats['top_sources'] = [
        {'source': s.source.value if s.source else 'direct', 'count': s.count}
        for s in top_sources
    ]

    return jsonify(stats)


# ============================================================================
# ADVERTISING COSTS API
# ============================================================================

@recruiting_bp.route('/api/offers/<int:offer_id>/advertising', methods=['GET'])
def api_get_advertising_costs(offer_id):
    """
    Lista costi advertising per una specifica offerta con filtri opzionali.

    Query params:
    - platform: linkedin/facebook/instagram
    - year: anno
    - month: mese (1-12)
    - period: 1-10/11-20/21-30
    """
    from corposostenibile.models import JobOfferAdvertisingCost, AdvertisingPlatformEnum, AdvertisingPeriodEnum

    # Verifica offerta esiste
    offer = JobOffer.query.get_or_404(offer_id)

    # Query base
    query = JobOfferAdvertisingCost.query.filter_by(job_offer_id=offer_id)

    # Filtri opzionali
    if platform := request.args.get('platform'):
        try:
            query = query.filter_by(platform=AdvertisingPlatformEnum(platform))
        except ValueError:
            return jsonify({'error': f'Invalid platform: {platform}'}), 400

    if year := request.args.get('year'):
        query = query.filter_by(year=int(year))

    if month := request.args.get('month'):
        query = query.filter_by(month=int(month))

    if period := request.args.get('period'):
        try:
            query = query.filter_by(period=AdvertisingPeriodEnum(period))
        except ValueError:
            return jsonify({'error': f'Invalid period: {period}'}), 400

    # Ordina per data decrescente
    costs = query.order_by(
        JobOfferAdvertisingCost.year.desc(),
        JobOfferAdvertisingCost.month.desc(),
        JobOfferAdvertisingCost.period.desc()
    ).all()

    # Serializza
    costs_data = []
    for cost in costs:
        costs_data.append({
            'id': cost.id,
            'job_offer_id': cost.job_offer_id,
            'platform': cost.platform,
            'year': cost.year,
            'month': cost.month,
            'period': cost.period,
            'amount': float(cost.amount),
            'notes': cost.notes,
            'created_at': cost.created_at.isoformat(),
            'created_by_id': cost.created_by_id
        })

    # Calcola totali per piattaforma
    totals = db.session.query(
        JobOfferAdvertisingCost.platform,
        func.sum(JobOfferAdvertisingCost.amount).label('total')
    ).filter_by(job_offer_id=offer_id).group_by(JobOfferAdvertisingCost.platform).all()

    totals_by_platform = {
        t.platform: float(t.total) for t in totals
    }

    return jsonify({
        'costs': costs_data,
        'total_costs': len(costs),
        'totals_by_platform': totals_by_platform,
        'grand_total': sum(totals_by_platform.values())
    })


@recruiting_bp.route('/api/offers/<int:offer_id>/advertising', methods=['POST'])
@login_required
def api_create_advertising_cost(offer_id):
    """
    Crea un nuovo costo advertising per l'offerta.

    Body JSON:
    {
        "platform": "linkedin",
        "year": 2025,
        "month": 11,
        "period": "1-10",
        "amount": 150.50,
        "notes": "Campagna novembre prima decade"
    }
    """
    from corposostenibile.models import JobOfferAdvertisingCost
    from flask_login import current_user

    try:
        # Verifica offerta esiste
        offer = JobOffer.query.get_or_404(offer_id)

        data = request.get_json()
        current_app.logger.info(f"[API] Creating advertising cost for offer {offer_id}: {data}")

        # Validazione campi obbligatori
        required_fields = ['platform', 'year', 'month', 'period', 'amount']
        missing = [f for f in required_fields if f not in data]
        if missing:
            return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

        # Validazione platform (manteniamo come stringa senza convertire in enum)
        platform = data['platform']
        if platform not in ['linkedin', 'facebook', 'instagram']:
            return jsonify({'error': f'Invalid platform: {platform}. Must be: linkedin, facebook, instagram'}), 400

        # Validazione period (manteniamo come stringa senza convertire in enum)
        period = data['period']
        if period not in ['1-10', '11-20', '21-30']:
            return jsonify({'error': f'Invalid period: {period}. Must be: 1-10, 11-20, 21-30'}), 400

        # Validazione month
        month = int(data['month'])
        if not 1 <= month <= 12:
            return jsonify({'error': 'Month must be between 1 and 12'}), 400

        # Validazione year
        year = int(data['year'])
        if year < 2020 or year > 2100:
            return jsonify({'error': 'Year must be between 2020 and 2100'}), 400

        # Validazione amount
        try:
            amount = float(data['amount'])
            if amount < 0:
                return jsonify({'error': 'Amount must be positive'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid amount'}), 400

        # Crea record - Passa le stringhe direttamente, SQLAlchemy le convertirà negli enum del DB
        cost = JobOfferAdvertisingCost(
            job_offer_id=offer_id,
            platform=platform,  # Stringa: "linkedin"
            year=year,
            month=month,
            period=period,      # Stringa: "1-10"
            amount=amount,
            notes=data.get('notes'),
            created_by_id=current_user.id if current_user.is_authenticated else None
        )

        db.session.add(cost)
        db.session.commit()

        current_app.logger.info(f"[API] Successfully created advertising cost {cost.id}")

        return jsonify({
            'message': 'Advertising cost created successfully',
            'cost': {
                'id': cost.id,
                'job_offer_id': cost.job_offer_id,
                'platform': cost.platform,
                'year': cost.year,
                'month': cost.month,
                'period': cost.period,
                'amount': float(cost.amount),
                'notes': cost.notes,
                'created_at': cost.created_at.isoformat()
            }
        }), 201

    except Exception as e:
        current_app.logger.error(f"[API] Error creating advertising cost: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500


@recruiting_bp.route('/api/advertising/<int:cost_id>', methods=['PUT'])
@login_required
def api_update_advertising_cost(cost_id):
    """
    Aggiorna un costo advertising esistente.
    """
    from corposostenibile.models import JobOfferAdvertisingCost

    cost = JobOfferAdvertisingCost.query.get_or_404(cost_id)
    data = request.get_json()

    # Aggiorna platform se fornito (valida e passa come stringa)
    if 'platform' in data:
        if data['platform'] not in ['linkedin', 'facebook', 'instagram']:
            return jsonify({'error': f'Invalid platform: {data["platform"]}. Must be: linkedin, facebook, instagram'}), 400
        cost.platform = data['platform']

    # Aggiorna period se fornito (valida e passa come stringa)
    if 'period' in data:
        if data['period'] not in ['1-10', '11-20', '21-30']:
            return jsonify({'error': f'Invalid period: {data["period"]}. Must be: 1-10, 11-20, 21-30'}), 400
        cost.period = data['period']

    # Aggiorna altri campi
    if 'year' in data:
        cost.year = int(data['year'])

    if 'month' in data:
        month = int(data['month'])
        if not 1 <= month <= 12:
            return jsonify({'error': 'Month must be between 1 and 12'}), 400
        cost.month = month

    if 'amount' in data:
        try:
            amount = float(data['amount'])
            if amount < 0:
                return jsonify({'error': 'Amount must be positive'}), 400
            cost.amount = amount
        except ValueError:
            return jsonify({'error': 'Invalid amount'}), 400

    if 'notes' in data:
        cost.notes = data['notes']

    db.session.commit()

    return jsonify({
        'message': 'Advertising cost updated successfully',
        'cost': {
            'id': cost.id,
            'job_offer_id': cost.job_offer_id,
            'platform': cost.platform,
            'year': cost.year,
            'month': cost.month,
            'period': cost.period,
            'amount': float(cost.amount),
            'notes': cost.notes,
            'updated_at': cost.updated_at.isoformat()
        }
    })


@recruiting_bp.route('/api/advertising/<int:cost_id>', methods=['DELETE'])
@login_required
def api_delete_advertising_cost(cost_id):
    """
    Elimina un costo advertising.
    """
    from corposostenibile.models import JobOfferAdvertisingCost

    cost = JobOfferAdvertisingCost.query.get_or_404(cost_id)

    db.session.delete(cost)
    db.session.commit()

    return jsonify({'message': 'Advertising cost deleted successfully'}), 200


@recruiting_bp.route('/api/advertising', methods=['GET'])
def api_get_all_advertising_costs():
    """
    Lista GLOBALE di tutti i costi advertising (tutte le offerte).

    Query params:
    - offer_id: filtra per offerta
    - platform: linkedin/facebook/instagram
    - year: anno
    - month: mese (1-12)
    - period: 1-10/11-20/21-30
    - page: pagina (default 1)
    - per_page: record per pagina (default 50)
    """
    from corposostenibile.models import JobOfferAdvertisingCost, AdvertisingPlatformEnum, AdvertisingPeriodEnum

    # Query base con join per nome offerta
    query = JobOfferAdvertisingCost.query.join(JobOffer)

    # Filtri opzionali
    if offer_id := request.args.get('offer_id'):
        query = query.filter(JobOfferAdvertisingCost.job_offer_id == int(offer_id))

    if platform := request.args.get('platform'):
        try:
            query = query.filter(JobOfferAdvertisingCost.platform == AdvertisingPlatformEnum(platform))
        except ValueError:
            return jsonify({'error': f'Invalid platform: {platform}'}), 400

    if year := request.args.get('year'):
        query = query.filter(JobOfferAdvertisingCost.year == int(year))

    if month := request.args.get('month'):
        query = query.filter(JobOfferAdvertisingCost.month == int(month))

    if period := request.args.get('period'):
        try:
            query = query.filter(JobOfferAdvertisingCost.period == AdvertisingPeriodEnum(period))
        except ValueError:
            return jsonify({'error': f'Invalid period: {period}'}), 400

    # Paginazione
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    # Ordina per data decrescente
    query = query.order_by(
        JobOfferAdvertisingCost.year.desc(),
        JobOfferAdvertisingCost.month.desc(),
        JobOfferAdvertisingCost.period.desc()
    )

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Serializza
    costs_data = []
    for cost in pagination.items:
        costs_data.append({
            'id': cost.id,
            'job_offer_id': cost.job_offer_id,
            'job_offer_title': cost.job_offer.title,
            'platform': cost.platform,
            'year': cost.year,
            'month': cost.month,
            'period': cost.period,
            'amount': float(cost.amount),
            'notes': cost.notes,
            'created_at': cost.created_at.isoformat()
        })

    # Calcola totali globali (senza paginazione)
    totals = db.session.query(
        JobOfferAdvertisingCost.platform,
        func.sum(JobOfferAdvertisingCost.amount).label('total')
    ).group_by(JobOfferAdvertisingCost.platform).all()

    totals_by_platform = {
        t.platform: float(t.total) for t in totals
    }

    return jsonify({
        'costs': costs_data,
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages
        },
        'totals_by_platform': totals_by_platform,
        'grand_total': sum(totals_by_platform.values())
    })