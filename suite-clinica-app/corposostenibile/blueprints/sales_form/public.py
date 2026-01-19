"""
Public form endpoints - no authentication required
"""

from datetime import datetime
from flask import render_template, request, jsonify, abort, redirect, url_for, current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from corposostenibile.extensions import db
from corposostenibile.models import (
    SalesFormLink, SalesFormConfig, SalesFormField,
    SalesLead
)
from . import sales_form_bp
from .services import LinkService, LeadService, FormConfigService

# Rate limiter per form pubblici
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)


# La route principale ora è su /welcome-form/<code> registrata nell'app principale
# Questa route su /sales-form/welcome-form/ fa redirect alla nuova
@sales_form_bp.route('/welcome-form/<string:unique_code>', methods=['GET', 'POST'])
@limiter.limit("30 per hour")
def public_form_redirect(unique_code):
    """Redirect dalla vecchia doppia dicitura al nuovo URL pulito"""
    return redirect(url_for('welcome_form', unique_code=unique_code), code=301)


# Funzione principale del form pubblico (chiamata dalla route diretta)
def public_form(unique_code):
    """
    Form pubblico accessibile tramite link univoco.
    Gestisce DUE tipi di link:
    - Link SALES: genera nuova lead
    - Link LEAD_COMPLETION: completa lead esistente
    """
    from flask import current_app

    # Ottieni link e verifica validità
    link = LinkService.get_link_by_code(unique_code)

    if not link or not link.is_active:
        abort(404, "Form non trovato o non più disponibile")

    # Verifica scadenza
    if link.expires_at and link.expires_at < datetime.now():
        abort(410, "Il link è scaduto")

    # Verifica limite submissions
    if link.max_submissions and link.submission_count >= link.max_submissions:
        abort(410, "Limite di invii raggiunto per questo form")

    # Carica configurazione form
    # - Link SALES: usa form config di sistema (ID 1)
    # - Link COMPLETION: usa form config specifico per il check (config_id dal link)
    if link.link_type == 'sales':
        form_config = FormConfigService.get_system_form()
    else:
        # Link di completamento - usa config_id specificato nel link
        if link.config_id:
            form_config = SalesFormConfig.query.get(link.config_id)
            if not form_config:
                abort(404, f"Form config ID {link.config_id} non trovato")
        else:
            # Fallback: usa form config di sistema
            form_config = FormConfigService.get_system_form()

    if not form_config.is_active:
        abort(404, "Form non disponibile")

    # Carica campi del form
    fields = SalesFormField.query.filter_by(config_id=form_config.id)\
        .order_by(SalesFormField.position).all()

    # Organizza campi per sezioni
    sections = {}
    for field in fields:
        section_name = field.section or 'default'
        if section_name not in sections:
            sections[section_name] = {
                'name': section_name,
                'description': field.section_description,
                'fields': []
            }
        sections[section_name]['fields'].append(field)

    # ========================================
    # CASO 1: Link per SALES (crea nuova lead)
    # ========================================
    if link.link_type == 'sales':
        sales_user = link.user

        if request.method == 'POST':
            try:
                # Raccogli tutti i dati del form
                all_form_data = dict(request.form)

                current_app.logger.info(f"[FORM-SALES] Campi ricevuti: {len(all_form_data)}")

                form_data = {
                    'first_name': request.form.get('first_name'),
                    'last_name': request.form.get('last_name'),
                    'email': request.form.get('email'),
                    'phone': request.form.get('phone'),
                    'birth_date': request.form.get('birth_date'),  # Data di nascita
                    'gender': request.form.get('gender'),  # Sesso
                    'professione': request.form.get('professione'),  # Professione
                    'indirizzo': request.form.get('indirizzo'),  # Indirizzo di residenza
                    'paese': request.form.get('paese'),  # Paese di residenza
                    'form_data': {}
                }

                # Normalizza field_name rimuovendo [] e rimuovi campi standard
                for key, value in request.form.items():
                    if key not in ['first_name', 'last_name', 'email', 'phone', 'birth_date', 'gender', 'professione', 'indirizzo', 'paese', 'csrf_token']:
                        # Rimuovi [] dal field_name (es: "privacy_accepted[]" -> "privacy_accepted")
                        normalized_key = key.replace('[]', '')
                        form_data['form_data'][normalized_key] = value

                # Crea NUOVA lead (il form SALES è il Check 1)
                lead = LeadService.create_lead_from_form(form_data, link)

                # IMPORTANTE: Il link SALES è il Check 1!
                # Marca il Check 1 come completato
                lead.check1_completed_at = datetime.now()
                db.session.commit()

                # Incrementa submission count
                link.submission_count = (link.submission_count or 0) + 1
                db.session.commit()

                return render_template(
                    'sales_form/public/success.html',
                    lead=lead,
                    sales_user=sales_user,
                    title='Grazie!',
                    message=form_config.success_message or 'Il tuo form è stato inviato con successo!',
                    redirect_url=form_config.redirect_url,
                    completion_mode=False
                )

            except Exception as e:
                db.session.rollback()
                import traceback
                current_app.logger.error(f"[SALES-FORM-ERROR] {str(e)}\n{traceback.format_exc()}")
                return render_template(
                    'sales_form/public/error.html',
                    title='Errore',
                    message='Si è verificato un errore durante l\'invio del form. Riprova più tardi.',
                    error_details=traceback.format_exc() if request.args.get('debug') else None
                )

        # GET: Mostra form vuoto
        return render_template(
            'sales_form/public/form.html',
            link=link,
            form_config=form_config,
            sections=sections,
            sales_user=sales_user,
            custom_message=link.custom_message,
            prefill_data=None,
            completion_mode=False
        )

    # ========================================
    # CASO 2: Link per LEAD (completa lead esistente con check 1, 2 o 3)
    # ========================================
    elif link.link_type in ['check1', 'check2', 'check3']:
        lead = SalesLead.query.get(link.lead_id)

        if not lead:
            abort(404, "Lead non trovata")

        check_num = link.check_number
        check_name = f"Check Iniziale {check_num}"

        # Verifica se questo check è già stato completato
        check_completed_field = f'check{check_num}_completed_at'
        if getattr(lead, check_completed_field, None):
            # Questo check è già stato completato
            return render_template(
                'sales_form/public/already_completed.html',
                lead=lead,
                message=f"Hai già completato il {check_name}. Grazie!",
                check_number=check_num
            )

        # Sales user (per messaggio personalizzato)
        sales_user = lead.sales_user if lead.sales_user else None

        if request.method == 'POST':
            try:
                # Raccogli tutti i dati del form
                all_form_data = dict(request.form)

                current_app.logger.info(f"[FORM-CHECK{check_num}] Lead {lead.id} - Campi ricevuti: {len(all_form_data)}")

                # Prepara form_responses (TUTTI i campi eccetto csrf_token)
                # IMPORTANTE: Normalizza field_name rimuovendo [] per checkbox
                form_responses = {}
                for key, value in all_form_data.items():
                    if key != 'csrf_token':
                        # Rimuovi [] dal field_name (es: "privacy_accepted[]" -> "privacy_accepted")
                        normalized_key = key.replace('[]', '')
                        form_responses[normalized_key] = value

                # AGGIORNA lead esistente: salva le risposte nel campo specifico del check
                # Ogni check ha il suo campo separato (NON si sovrascrivono)
                if check_num == 1:
                    lead.check1_responses = form_responses
                elif check_num == 2:
                    lead.check2_responses = form_responses
                elif check_num == 3:
                    lead.check3_responses = form_responses

                    # CALCOLA AUTOMATICAMENTE LO SCORE del Check 3
                    try:
                        current_app.logger.info(f"[CHECK3-DEBUG] Inizio calcolo score per lead {lead.id}")
                        scoring_result = LeadService.calculate_check3_score(form_responses)
                        current_app.logger.info(f"[CHECK3-DEBUG] Scoring result: {scoring_result}")

                        lead.check3_score = scoring_result['score']
                        lead.check3_type = scoring_result['type']

                        current_app.logger.info(
                            f"[CHECK3-SCORING] Lead {lead.id} - Score: {scoring_result['score']}, "
                            f"Type: {scoring_result['type']}"
                        )
                    except Exception as score_error:
                        current_app.logger.error(f"[CHECK3-SCORING-ERROR] {str(score_error)}")
                        # Non blocchiamo il salvataggio se lo scoring fallisce
                        lead.check3_score = None
                        lead.check3_type = None

                # Mantieni retrocompatibilità: salva anche in form_responses (ultimo check compilato)
                lead.form_responses = form_responses

                # Aggiorna campi base se forniti (il prospect potrebbe aver corretto dati)
                if request.form.get('first_name'):
                    lead.first_name = request.form.get('first_name')
                if request.form.get('last_name'):
                    lead.last_name = request.form.get('last_name')
                if request.form.get('email'):
                    lead.email = request.form.get('email')
                if request.form.get('phone'):
                    lead.phone = request.form.get('phone')
                if request.form.get('birth_date'):
                    try:
                        lead.birth_date = datetime.strptime(request.form.get('birth_date'), '%Y-%m-%d').date()
                    except (ValueError, TypeError) as e:
                        current_app.logger.warning(f"[FORM-CHECK{check_num}] Invalid birth_date format: {request.form.get('birth_date')} - Error: {str(e)}")
                        # Non bloccare il form per una data invalida, semplicemente skippa
                if request.form.get('gender'):
                    lead.gender = request.form.get('gender')  # Aggiorna sesso (M/F)
                if request.form.get('indirizzo'):
                    lead.indirizzo = request.form.get('indirizzo')  # Aggiorna indirizzo
                if request.form.get('paese'):
                    lead.paese = request.form.get('paese')  # Aggiorna paese

                # ============ GESTIONE FILE UPLOAD ============
                if request.files:
                    import os
                    from werkzeug.utils import secure_filename

                    # Crea directory per i file della lead
                    upload_dir = os.path.join(current_app.root_path, 'uploads', 'lead_files', str(lead.id))
                    os.makedirs(upload_dir, exist_ok=True)

                    # Inizializza form_attachments se non esiste
                    if lead.form_attachments is None:
                        lead.form_attachments = []

                    # Estensioni consentite per sicurezza
                    ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'gif', 'doc', 'docx', 'heic', 'heif'}
                    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

                    files_saved = []

                    for field_name, file in request.files.items():
                        if file and file.filename:
                            # Valida estensione
                            file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''

                            if file_ext not in ALLOWED_EXTENSIONS:
                                current_app.logger.warning(
                                    f"[FILE-UPLOAD] Lead {lead.id} - File {file.filename} ha estensione non valida: {file_ext}"
                                )
                                continue

                            # Valida dimensione
                            file.seek(0, 2)  # Vai alla fine
                            file_size = file.tell()
                            file.seek(0)  # Torna all'inizio

                            if file_size > MAX_FILE_SIZE:
                                current_app.logger.warning(
                                    f"[FILE-UPLOAD] Lead {lead.id} - File {file.filename} troppo grande: {file_size} bytes"
                                )
                                continue

                            # Genera nome file sicuro e univoco
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            safe_filename = secure_filename(file.filename)
                            unique_filename = f"{field_name}_{timestamp}_{safe_filename}"

                            # Salva file
                            file_path = os.path.join(upload_dir, unique_filename)
                            file.save(file_path)

                            # Path relativo per DB
                            relative_path = f"lead_files/{lead.id}/{unique_filename}"

                            # Aggiungi a form_attachments
                            attachment_info = {
                                'field_name': field_name,
                                'filename': safe_filename,
                                'path': relative_path,
                                'size': file_size,
                                'uploaded_at': datetime.now().isoformat(),
                                'check_number': check_num
                            }
                            lead.form_attachments.append(attachment_info)
                            files_saved.append(field_name)

                            current_app.logger.info(
                                f"[FILE-UPLOAD] Lead {lead.id} - Salvato {field_name}: {unique_filename} ({file_size} bytes)"
                            )

                    if files_saved:
                        current_app.logger.info(
                            f"[FILE-UPLOAD] Lead {lead.id} Check {check_num} - {len(files_saved)} file salvati: {', '.join(files_saved)}"
                        )

                        # IMPORTANTE: Forza SQLAlchemy a riconoscere la modifica del campo JSONB
                        from sqlalchemy.orm.attributes import flag_modified
                        flag_modified(lead, 'form_attachments')

                # Traccia completamento di questo specifico check
                setattr(lead, check_completed_field, datetime.now())

                # Log attività
                lead.add_activity_log(
                    f'check{check_num}_completed',
                    f'{check_name} completato tramite link',
                    user_id=lead.sales_user_id
                )

                # Incrementa submission count del link
                link.submission_count = (link.submission_count or 0) + 1

                db.session.commit()

                current_app.logger.info(f"[FORM-CHECK{check_num}] Lead {lead.id} aggiornata con successo")

                return render_template(
                    'sales_form/public/success.html',
                    lead=lead,
                    sales_user=sales_user,
                    title='Grazie!',
                    message=f"Grazie per aver completato il {check_name}! Ti contatteremo presto.",
                    redirect_url=None,
                    check_number=check_num,
                    completion_mode=True
                )

            except Exception as e:
                db.session.rollback()
                import traceback
                error_trace = traceback.format_exc()
                current_app.logger.error(f"[COMPLETION-ERROR] {str(e)}\n{error_trace}")

                # Mostra sempre i dettagli per debug (rimuovere in produzione)
                return render_template(
                    'sales_form/public/error.html',
                    title='Errore',
                    message=f'Si è verificato un errore durante l\'invio: {str(e)}',
                    error_details=error_trace  # Mostra sempre per debug
                )

        # GET: Mostra form PRE-COMPILATO con dati lead
        prefill_data = {
            'first_name': lead.first_name,
            'last_name': lead.last_name,
            'email': lead.email,
            'phone': lead.phone,
            'birth_date': lead.birth_date,  # Data di nascita (oggetto date o None)
            'gender': lead.gender  # Sesso (M/F o None)
        }

        return render_template(
            'sales_form/public/form.html',
            link=link,
            form_config=form_config,
            sections=sections,
            sales_user=sales_user,
            custom_message=link.custom_message,
            prefill_data=prefill_data,
            completion_mode=True,
            lead=lead,
            check_number=check_num,
            check_name=check_name
        )

    # Link type sconosciuto
    abort(500, "Configurazione link non valida")


# REDIRECT PER RETROCOMPATIBILITA' - I vecchi link continuano a funzionare!
@sales_form_bp.route('/f/<string:unique_code>', methods=['GET', 'POST'])
def redirect_old_form(unique_code):
    """Redirect dal vecchio URL /sales-form/f/ al nuovo /welcome-form/"""
    return redirect(url_for('welcome_form', unique_code=unique_code), code=301)


# Redirect anche dal precedente /sales-form/welcome-form/ (doppia dicitura)
# Questo route cattura ENTRAMBI /sales-form/welcome-form/ e /welcome-form/
# perché public_form è registrato su entrambi
def redirect_to_clean_welcome(unique_code):
    """Redirect al nuovo URL pulito /welcome-form/"""
    return redirect(url_for('welcome_form', unique_code=unique_code), code=301)


@sales_form_bp.route('/api/public/config/<string:unique_code>', methods=['GET'])
@limiter.limit("50 per hour")
def api_get_form_config(unique_code):
    """API per ottenere configurazione form (per SPA)"""
    link = LinkService.get_link_by_code(unique_code)

    if not link or not link.is_active:
        return jsonify({'success': False, 'error': 'Form non trovato'}), 404

    # Carica configurazione form unico di sistema
    form_config = FormConfigService.get_system_form()

    if not form_config:
        return jsonify({'success': False, 'error': 'Form non disponibile'}), 404

    # Carica campi
    fields = SalesFormField.query.filter_by(config_id=form_config.id)\
        .order_by(SalesFormField.position).all()

    # Determina il nome del sales person in base al tipo di link
    if link.link_type == 'sales':
        sales_person = link.user.name if link.user else 'Team Corposostenibile'
    else:  # lead_completion
        lead = SalesLead.query.get(link.lead_id)
        sales_person = lead.sales_user.name if lead and lead.sales_user else 'Team Corposostenibile'

    return jsonify({
        'success': True,
        'data': {
            'form_id': form_config.id,
            'form_name': form_config.name,
            'sales_person': sales_person,
            'custom_message': link.custom_message,
            'fields': [
                {
                    'name': f.field_name,
                    'type': f.field_type,
                    'label': f.field_label,
                    'required': f.is_required,
                    'placeholder': f.placeholder,
                    'help_text': f.help_text,
                    'options': f.options,
                    'validation': f.validation_rules,
                    'conditional': f.conditional_logic,
                    'section': f.section
                }
                for f in fields
            ],
            'styling': {
                'primary_color': form_config.primary_color,
                'logo_url': form_config.logo_url,
                'custom_css': form_config.custom_css
            }
        }
    })


@sales_form_bp.route('/api/public/submit', methods=['POST'])
@limiter.limit("5 per hour")
def api_submit_form():
    """Submit del form pubblico"""
    data = request.get_json()

    # Validazione base
    if not data:
        return jsonify({'success': False, 'error': 'Dati mancanti'}), 400

    # Verifica campi obbligatori base
    if not data.get('first_name') or not data.get('last_name') or not data.get('email'):
        return jsonify({
            'success': False,
            'error': 'Nome, cognome ed email sono obbligatori'
        }), 400

    # Ottieni link se fornito
    link = None
    if data.get('form_code'):
        link = SalesFormLink.query.filter_by(
            unique_code=data['form_code'],
            is_active=True
        ).first()

        if not link:
            return jsonify({'success': False, 'error': 'Codice form non valido'}), 400

    # Verifica duplicati email (opzionale)
    existing = SalesLead.query.filter_by(email=data['email']).first()
    if existing and existing.sales_user_id == (link.user_id if link else None):
        # Lead già esistente per questo sales
        if existing.status not in ['LOST', 'ARCHIVED']:
            return jsonify({
                'success': False,
                'error': 'Hai già inviato una richiesta. Ti contatteremo presto!'
            }), 409

    # Prepara dati lead
    form_data = {
        'first_name': data['first_name'],
        'last_name': data['last_name'],
        'email': data['email'],
        'phone': data.get('phone'),
        'custom_fields': data.get('custom_fields', {}),

        # Tracking
        'source_url': request.referrer,
        'utm_source': data.get('utm_source'),
        'utm_medium': data.get('utm_medium'),
        'utm_campaign': data.get('utm_campaign'),
        'utm_term': data.get('utm_term'),
        'utm_content': data.get('utm_content'),

        # Tech info
        'ip_address': request.remote_addr,
        'user_agent': request.user_agent.string
    }

    try:
        # Crea lead
        lead = LeadService.create_lead_from_form(form_data, link)

        # Prepara risposta
        response = {
            'success': True,
            'message': 'Grazie! Ti contatteremo presto.'
        }

        # Usa i messaggi del form di sistema
        form_config = FormConfigService.get_system_form()
        if form_config:
            response['message'] = form_config.success_message or response['message']
            if form_config.redirect_url:
                response['redirect'] = form_config.redirect_url

        return jsonify(response)

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Errore durante l\'invio. Riprova più tardi.'
        }), 500


@sales_form_bp.route('/public/success')
def public_success():
    """Pagina di ringraziamento dopo invio form"""
    return render_template('sales_form/public/success.html')


@sales_form_bp.route('/public/error')
def public_error():
    """Pagina di errore per form pubblico"""
    error_message = request.args.get('message', 'Si è verificato un errore')
    return render_template('sales_form/public/error.html', error_message=error_message)