"""
Routes for GHL webhook endpoints
"""

from flask import request, jsonify, render_template, current_app, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import json

from . import bp
from .security import require_webhook_signature, require_permission, rate_limiter
from .validators import WebhookValidator
from .tasks import process_acconto_open_webhook, process_chiuso_won_webhook, retry_failed_webhook
from corposostenibile.extensions import db, csrf
from corposostenibile.models import GHLOpportunity, ServiceClienteAssignment, Cliente


# ============================================================================
# WEBHOOK ENDPOINTS
# ============================================================================

@bp.route('/webhook/acconto-open', methods=['POST'])
@require_webhook_signature
def webhook_acconto_open():
    """
    Riceve webhook quando un'opportunità passa a Acconto-Open in GHL

    Expected payload:
    {
        "event_type": "opportunity.status_changed",
        "opportunity": {
            "id": "xxx",
            "status": "acconto_open",
            ...
        },
        "contact": {
            "id": "yyy",
            "name": "Mario Rossi",
            "email": "mario@example.com",
            ...
        }
    }
    """
    try:
        # Rate limiting
        client_ip = request.remote_addr
        if not rate_limiter.is_allowed(f"webhook_{client_ip}"):
            current_app.logger.warning(f"[GHL Webhook] Rate limit exceeded for IP: {client_ip}")
            return jsonify({'error': 'Rate limit exceeded'}), 429

        # Ottieni il payload
        payload = request.get_json()

        if not payload:
            return jsonify({'error': 'No payload provided'}), 400

        # Log del webhook ricevuto
        current_app.logger.info(
            f"[GHL Webhook] Received acconto_open webhook for opportunity: {payload.get('opportunity', {}).get('id')}"
        )

        # Queue il task per processing asincrono
        task = process_acconto_open_webhook.delay(payload)

        # Rispondi immediatamente a GHL
        return jsonify({
            'success': True,
            'message': 'Webhook received and queued for processing',
            'task_id': task.id
        }), 200

    except Exception as e:
        current_app.logger.error(f"[GHL Webhook] Error in acconto_open endpoint: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/webhook/calendario-prenotato', methods=['POST'])
@require_webhook_signature
def webhook_calendario_prenotato():
    """
    Riceve webhook quando un cliente prenota con calendario GHL

    Questo ci dice CHI è il servizio clienti assegnato basandosi sul calendario usato:
    - Calendario "Daniela Mattina" → Daniela owner
    - Calendario "Marianna Pomeriggio" → Marianna owner
    """
    try:
        # Rate limiting
        client_ip = request.remote_addr
        if not rate_limiter.is_allowed(f"webhook_{client_ip}"):
            current_app.logger.warning(f"[GHL Webhook] Rate limit exceeded for IP: {client_ip}")
            return jsonify({'error': 'Rate limit exceeded'}), 429

        payload = request.get_json()
        if not payload:
            return jsonify({'error': 'No payload provided'}), 400

        # Log webhook
        current_app.logger.info(
            f"[GHL Webhook] Received calendario webhook for contact: {payload.get('contact', {}).get('id')}"
        )

        # Estrai dati importanti
        calendar_name = payload.get('calendar', {}).get('name', '')
        contact_id = payload.get('contact', {}).get('id')
        appointment_date = payload.get('appointment', {}).get('date')

        # Determina il servizio clienti owner basandosi sul calendario
        servizio_clienti_owner = None
        servizio_clienti_id = None

        # Mapping calendari → servizio clienti
        calendar_mapping = {
            'daniela mattina': ('Daniela', 'daniela@corposostenibile.com'),
            'daniela pomeriggio': ('Daniela', 'daniela@corposostenibile.com'),
            'marianna mattina': ('Marianna', 'marianna@corposostenibile.com'),
            'marianna pomeriggio': ('Marianna', 'marianna@corposostenibile.com'),
        }

        calendar_lower = calendar_name.lower()
        for pattern, (name, email) in calendar_mapping.items():
            if pattern in calendar_lower:
                servizio_clienti_owner = name
                # Trova l'ID dell'utente
                from corposostenibile.models import User
                user = User.query.filter_by(email=email).first()
                if user:
                    servizio_clienti_id = user.id
                break

        if not servizio_clienti_owner:
            current_app.logger.warning(f"[GHL Webhook] Calendario non riconosciuto: {calendar_name}")
            servizio_clienti_owner = 'Non assegnato'

        # Trova il cliente tramite GHL contact ID
        from corposostenibile.models import Cliente, ServiceClienteAssignment
        cliente = Cliente.query.filter_by(ghl_contact_id=contact_id).first()

        if cliente:
            # Aggiorna l'assignment con il servizio clienti owner
            assignment = ServiceClienteAssignment.query.filter_by(
                cliente_id=cliente.cliente_id
            ).first()

            if assignment:
                assignment.servizio_clienti_owner = servizio_clienti_id
                assignment.servizio_clienti_assigned_at = datetime.utcnow()
                assignment.calendario_used = calendar_name

                # Aggiorna anche nella tabella clienti
                cliente.assigned_service_rep = servizio_clienti_id
                cliente.service_assignment_date = datetime.utcnow()
                cliente.service_assignment_method = 'ghl_calendar'

                db.session.commit()

                current_app.logger.info(
                    f"[GHL Webhook] Cliente {cliente.nome_cognome} assegnato a {servizio_clienti_owner} tramite calendario {calendar_name}"
                )
            else:
                current_app.logger.warning(f"[GHL Webhook] No assignment found for cliente {cliente.cliente_id}")
        else:
            current_app.logger.warning(f"[GHL Webhook] No cliente found with GHL contact ID: {contact_id}")

        return jsonify({
            'success': True,
            'message': 'Calendar webhook processed',
            'servizio_clienti': servizio_clienti_owner
        }), 200

    except Exception as e:
        current_app.logger.error(f"[GHL Webhook] Error in calendario endpoint: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/webhook/chiuso-won', methods=['POST'])
@require_webhook_signature
def webhook_chiuso_won():
    """
    Riceve webhook quando un'opportunità passa a Chiuso-Won in GHL

    Expected payload simile a acconto-open ma con status "chiuso_won"
    """
    try:
        # Rate limiting
        client_ip = request.remote_addr
        if not rate_limiter.is_allowed(f"webhook_{client_ip}"):
            current_app.logger.warning(f"[GHL Webhook] Rate limit exceeded for IP: {client_ip}")
            return jsonify({'error': 'Rate limit exceeded'}), 429

        # Ottieni il payload
        payload = request.get_json()

        if not payload:
            return jsonify({'error': 'No payload provided'}), 400

        # Log del webhook ricevuto
        current_app.logger.info(
            f"[GHL Webhook] Received chiuso_won webhook for opportunity: {payload.get('opportunity', {}).get('id')}"
        )

        # Queue il task per processing asincrono
        task = process_chiuso_won_webhook.delay(payload)

        # Rispondi immediatamente a GHL
        return jsonify({
            'success': True,
            'message': 'Webhook received and queued for processing',
            'task_id': task.id
        }), 200

    except Exception as e:
        current_app.logger.error(f"[GHL Webhook] Error in chiuso_won endpoint: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# MONITORING & MANAGEMENT ENDPOINTS
# ============================================================================

@bp.route('/webhook/status')
@login_required
@require_permission('ghl:view_logs')
def webhook_status():
    """
    Mostra lo stato dei webhook processati
    """
    # Ultimi 50 webhook
    recent_webhooks = GHLOpportunity.query.order_by(
        GHLOpportunity.created_at.desc()
    ).limit(50).all()

    # Statistiche
    stats = {
        'total': GHLOpportunity.query.count(),
        'processed': GHLOpportunity.query.filter_by(processed=True).count(),
        'failed': GHLOpportunity.query.filter(
            GHLOpportunity.error_message.isnot(None)
        ).count(),
        'pending': GHLOpportunity.query.filter_by(processed=False).count()
    }

    return render_template(
        'ghl_integration/webhook_status.html',
        webhooks=recent_webhooks,
        stats=stats
    )


@bp.route('/webhook/retry/<int:webhook_id>', methods=['POST'])
@login_required
@require_permission('ghl:manage')
def retry_webhook(webhook_id):
    """
    Riprova a processare un webhook fallito
    """
    opportunity = GHLOpportunity.query.get_or_404(webhook_id)

    if opportunity.processed:
        flash('Webhook già processato con successo', 'warning')
    else:
        retry_failed_webhook.delay(webhook_id)
        flash('Webhook messo in coda per retry', 'success')

    return redirect(url_for('ghl_integration.webhook_status'))


# ============================================================================
# TESTING ENDPOINTS
# ============================================================================

@bp.route('/test')
@login_required
@require_permission('ghl:test_webhooks')
def test_page():
    """
    Pagina per testare i webhook
    """
    return render_template('ghl_integration/test_webhook.html')


@bp.route('/test/send', methods=['POST'])
@login_required
@require_permission('ghl:test_webhooks')
def send_test_webhook():
    """
    Invia un webhook di test
    """
    try:
        webhook_type = request.form.get('type', 'acconto_open')

        # Prepara payload di test
        test_payload = {
            'event_type': 'opportunity.status_changed',
            'timestamp': datetime.utcnow().isoformat(),
            'opportunity': {
                'id': f'TEST-{datetime.now().strftime("%Y%m%d%H%M%S")}',
                'status': webhook_type.replace('-', '_'),
                'pipeline_stage_id': 'test_stage',
                'pipeline_name': 'Test Pipeline',
                'custom_fields': {
                    'acconto_pagato': request.form.get('acconto', '500'),
                    'importo_totale': request.form.get('totale', '1500'),
                    'pacchetto': request.form.get('pacchetto', 'Test Package'),
                    'modalita_pagamento': request.form.get('pagamento', 'bonifico'),
                    'sales_consultant': request.form.get('consultant', 'Test Sales'),
                    'note': request.form.get('note', 'Test note')
                }
            },
            'contact': {
                'id': f'CONTACT-{datetime.now().strftime("%Y%m%d%H%M%S")}',
                'name': request.form.get('nome', 'Test User'),
                'email': request.form.get('email', f'test-{datetime.now().timestamp()}@example.com'),
                'phone': request.form.get('telefono', '+39 123 456 7890'),
                'source': request.form.get('source', 'test')
            }
        }

        # Processa direttamente (bypass security per test)
        if webhook_type == 'acconto_open':
            task = process_acconto_open_webhook.delay(test_payload)
        else:
            task = process_chiuso_won_webhook.delay(test_payload)

        flash(f'Webhook di test inviato! Task ID: {task.id}', 'success')
        return redirect(url_for('ghl_integration.webhook_status'))

    except Exception as e:
        current_app.logger.error(f"[GHL Test] Error sending test webhook: {e}")
        flash(f'Errore nell\'invio del webhook di test: {str(e)}', 'danger')
        return redirect(url_for('ghl_integration.test_page'))


# ============================================================================
# API ENDPOINTS
# ============================================================================

@bp.route('/api/opportunities')
@login_required
@require_permission('ghl:view_logs')
def api_opportunities():
    """
    API endpoint per ottenere le opportunità in formato JSON
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')

    query = GHLOpportunity.query

    if status:
        query = query.filter_by(status=status)

    pagination = query.order_by(
        GHLOpportunity.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    opportunities = [{
        'id': opp.id,
        'ghl_opportunity_id': opp.ghl_opportunity_id,
        'status': opp.status,
        'nome_cognome': opp.nome_cognome,
        'email': opp.email,
        'acconto_pagato': float(opp.acconto_pagato) if opp.acconto_pagato else None,
        'importo_totale': float(opp.importo_totale) if opp.importo_totale else None,
        'processed': opp.processed,
        'error_message': opp.error_message,
        'created_at': opp.created_at.isoformat() if opp.created_at else None,
        'updated_at': opp.updated_at.isoformat() if opp.updated_at else None
    } for opp in pagination.items]

    return jsonify({
        'opportunities': opportunities,
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    })


@bp.route('/api/assignments')
@login_required
@require_permission('ghl:view_assignments')
def api_assignments():
    """
    API endpoint per ottenere le assegnazioni servizio clienti
    """
    status = request.args.get('status', 'pending_finance')

    assignments = ServiceClienteAssignment.query.filter_by(
        status=status
    ).order_by(
        ServiceClienteAssignment.created_at.desc()
    ).limit(100).all()

    data = [{
        'id': ass.id,
        'cliente_id': ass.cliente_id,
        'cliente_nome': ass.cliente.nome_cognome if ass.cliente else None,
        'status': ass.status,
        'finance_approved': ass.finance_approved,
        'checkup_iniziale_fatto': ass.checkup_iniziale_fatto,
        'nutrizionista_assigned': ass.nutrizionista_assigned_id is not None,
        'coach_assigned': ass.coach_assigned_id is not None,
        'psicologa_assigned': ass.psicologa_assigned_id is not None,
        'created_at': ass.created_at.isoformat() if ass.created_at else None
    } for ass in assignments]

    return jsonify({
        'assignments': data,
        'total': len(data)
    })


# ============================================================================
# GHL CALENDAR INTEGRATION API
# ============================================================================

@bp.route('/api/config', methods=['GET'])
@login_required
def api_get_config():
    """
    Ottiene la configurazione GHL corrente (solo admin).
    """
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Non autorizzato'}), 403

    from corposostenibile.models import GHLConfig
    config = GHLConfig.get_config()

    return jsonify({
        'success': True,
        'config': {
            'location_id': config.location_id,
            'is_active': config.is_active,
            'has_api_key': bool(config.api_key),
            'last_sync_at': config.last_sync_at.isoformat() if config.last_sync_at else None,
            'last_error': config.last_error
        }
    })


@bp.route('/api/config', methods=['POST'])
@csrf.exempt
@login_required
def api_update_config():
    """
    Aggiorna la configurazione GHL (solo admin).
    """
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Non autorizzato'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Dati non validi'}), 400

    from corposostenibile.models import GHLConfig
    config = GHLConfig.get_config()

    # Aggiorna i campi
    if 'api_key' in data:
        config.api_key = data['api_key']
    if 'location_id' in data:
        config.location_id = data['location_id']
    if 'is_active' in data:
        config.is_active = data['is_active']

    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Configurazione aggiornata'
    })


@bp.route('/api/config/test', methods=['POST'])
@csrf.exempt
@login_required
def api_test_config():
    """
    Testa la connessione GHL (solo admin).
    """
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Non autorizzato'}), 403

    try:
        from .calendar_service import get_ghl_calendar_service
        service = get_ghl_calendar_service()

        if not service.is_configured():
            return jsonify({
                'success': False,
                'message': 'GHL non configurato. Inserisci API Key e Location ID.'
            })

        # Prova a ottenere i calendari come test
        calendars = service.get_calendars()

        # Aggiorna last_sync
        from corposostenibile.models import GHLConfig
        config = GHLConfig.get_config()
        config.last_sync_at = datetime.utcnow()
        config.last_error = None
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Connessione OK! Trovati {len(calendars)} calendari.',
            'calendars_count': len(calendars)
        })

    except Exception as e:
        # Salva l'errore
        from corposostenibile.models import GHLConfig
        config = GHLConfig.get_config()
        config.last_error = str(e)
        db.session.commit()

        current_app.logger.error(f"[GHL] Config test failed: {e}")
        return jsonify({
            'success': False,
            'message': f'Errore di connessione: {str(e)}'
        })


@bp.route('/api/calendars', methods=['GET'])
@login_required
def api_get_calendars():
    """
    Ottiene la lista dei calendari GHL.
    """
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Non autorizzato'}), 403

    try:
        from .calendar_service import get_ghl_calendar_service
        service = get_ghl_calendar_service()

        if not service.is_configured():
            return jsonify({
                'success': False,
                'message': 'GHL non configurato'
            })

        calendars = service.get_calendars()

        return jsonify({
            'success': True,
            'calendars': calendars
        })

    except Exception as e:
        current_app.logger.error(f"[GHL] Error fetching calendars: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })


@bp.route('/api/users', methods=['GET'])
@login_required
def api_get_ghl_users():
    """
    Ottiene la lista degli utenti GHL (team members).
    """
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Non autorizzato'}), 403

    try:
        from .calendar_service import get_ghl_calendar_service
        service = get_ghl_calendar_service()

        if not service.is_configured():
            return jsonify({
                'success': False,
                'message': 'GHL non configurato'
            })

        users = service.get_users()

        return jsonify({
            'success': True,
            'users': users,
            'count': len(users)
        })

    except Exception as e:
        current_app.logger.error(f"[GHL] Error fetching users: {e}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': str(e)
        })


@bp.route('/api/calendars/debug', methods=['GET'])
@login_required
def api_debug_calendars():
    """
    Debug: mostra la struttura dei calendari GHL per capire come estrarre team members.
    """
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Non autorizzato'}), 403

    try:
        from .calendar_service import get_ghl_calendar_service
        service = get_ghl_calendar_service()

        if not service.is_configured():
            return jsonify({'success': False, 'message': 'GHL non configurato'})

        calendars = service.get_calendars()

        # Prendi i primi 3 calendari per analisi
        samples = calendars[:3] if len(calendars) >= 3 else calendars

        return jsonify({
            'success': True,
            'total_calendars': len(calendars),
            'sample_calendars': samples,
            'all_keys': list(samples[0].keys()) if samples else []
        })

    except Exception as e:
        current_app.logger.error(f"[GHL] Debug calendars error: {e}")
        return jsonify({'success': False, 'message': str(e)})


@bp.route('/api/mapping', methods=['GET'])
@login_required
def api_get_mapping():
    """
    Ottiene il mapping utenti Suite Clinica → calendari GHL.
    """
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Non autorizzato'}), 403

    from corposostenibile.models import User

    # Ottieni tutti gli utenti professionisti (non admin puri)
    users = User.query.filter(
        User.is_active == True
    ).order_by(User.first_name, User.last_name).all()

    mapping = [{
        'user_id': u.id,
        'full_name': u.full_name,
        'email': u.email,
        'role': u.role.value if u.role else None,
        'specialty': u.specialty.value if u.specialty else None,
        'ghl_calendar_id': u.ghl_calendar_id,
        'ghl_user_id': u.ghl_user_id
    } for u in users]

    return jsonify({
        'success': True,
        'mapping': mapping
    })


@bp.route('/api/mapping', methods=['POST'])
@csrf.exempt
@login_required
def api_update_mapping():
    """
    Aggiorna il mapping utente → calendario GHL.
    """
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Non autorizzato'}), 403

    data = request.get_json()
    if not data or 'user_id' not in data:
        return jsonify({'success': False, 'message': 'user_id richiesto'}), 400

    from corposostenibile.models import User
    user = User.query.get(data['user_id'])

    if not user:
        return jsonify({'success': False, 'message': 'Utente non trovato'}), 404

    # Aggiorna mapping
    if 'ghl_calendar_id' in data:
        user.ghl_calendar_id = data['ghl_calendar_id'] if data['ghl_calendar_id'] else None
    if 'ghl_user_id' in data:
        user.ghl_user_id = data['ghl_user_id'] if data['ghl_user_id'] else None

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Mapping aggiornato per {user.full_name}'
    })


@bp.route('/api/mapping/bulk', methods=['POST'])
@csrf.exempt
@login_required
def api_update_mapping_bulk():
    """
    Aggiorna il mapping per più utenti contemporaneamente.
    """
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Non autorizzato'}), 403

    data = request.get_json()
    if not data or 'mappings' not in data:
        return jsonify({'success': False, 'message': 'mappings richiesto'}), 400

    from corposostenibile.models import User
    updated = 0

    for mapping in data['mappings']:
        user_id = mapping.get('user_id')
        if not user_id:
            continue

        user = User.query.get(user_id)
        if not user:
            continue

        if 'ghl_calendar_id' in mapping:
            user.ghl_calendar_id = mapping['ghl_calendar_id'] if mapping['ghl_calendar_id'] else None
        if 'ghl_user_id' in mapping:
            user.ghl_user_id = mapping['ghl_user_id'] if mapping['ghl_user_id'] else None

        updated += 1

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Aggiornati {updated} mapping'
    })


# ============================================================================
# CALENDAR EVENTS API (per il frontend calendario)
# ============================================================================

@bp.route('/api/calendar/events', methods=['GET'])
@login_required
def api_get_calendar_events():
    """
    Ottiene gli eventi calendario per l'utente corrente.
    Con auto-match clienti Suite Clinica.
    """
    # Parametri date
    start = request.args.get('start')
    end = request.args.get('end')

    if not start or not end:
        # Default: mese corrente
        today = datetime.utcnow()
        start = today.replace(day=1).strftime('%Y-%m-%d')
        end = (today.replace(day=1) + timedelta(days=32)).replace(day=1).strftime('%Y-%m-%d')

    try:
        from .calendar_service import get_ghl_calendar_service
        service = get_ghl_calendar_service()

        if not service.is_configured():
            return jsonify({
                'success': False,
                'message': 'GHL non configurato',
                'events': []
            })

        # Verifica che l'utente abbia un calendario O un utente GHL associato
        if not current_user.ghl_calendar_id and not current_user.ghl_user_id:
            return jsonify({
                'success': False,
                'message': 'Calendario GHL non configurato per questo utente',
                'events': []
            })

        # Ottieni eventi
        events = service.get_events_for_user(current_user.id, start, end)

        return jsonify({
            'success': True,
            'events': events
        })

    except Exception as e:
        current_app.logger.error(f"[GHL] Error fetching events: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'events': []
        })


@bp.route('/api/calendar/free-slots', methods=['GET'])
@login_required
def api_get_free_slots():
    """
    Ottiene gli slot disponibili per il calendario dell'utente corrente.
    """
    start = request.args.get('start')
    end = request.args.get('end')

    if not start or not end:
        # Default: prossimi 30 giorni
        today = datetime.utcnow()
        start = today.strftime('%Y-%m-%d')
        end = (today + timedelta(days=30)).strftime('%Y-%m-%d')

    try:
        from .calendar_service import get_ghl_calendar_service
        service = get_ghl_calendar_service()

        if not service.is_configured():
            return jsonify({
                'success': False,
                'message': 'GHL non configurato'
            })

        if not current_user.ghl_calendar_id:
            return jsonify({
                'success': False,
                'message': 'Calendario GHL non configurato per questo utente'
            })

        slots = service.get_free_slots(
            current_user.ghl_calendar_id,
            start,
            end,
            user_id=current_user.ghl_user_id
        )

        return jsonify({
            'success': True,
            'slots': slots
        })

    except Exception as e:
        current_app.logger.error(f"[GHL] Error fetching free slots: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })


@bp.route('/api/calendar/connection-status', methods=['GET'])
@login_required
def api_calendar_connection_status():
    """
    Verifica lo stato della connessione GHL per l'utente corrente.
    Considera connesso se ha ghl_user_id (tutti i calendari) O ghl_calendar_id (singolo).
    """
    from corposostenibile.models import GHLConfig

    config = GHLConfig.get_config()
    is_configured = config.is_active and config.api_key and config.location_id
    # Connesso se ha user_id (tutti i calendari) O calendar_id (singolo calendario)
    user_has_ghl = bool(current_user.ghl_user_id or current_user.ghl_calendar_id)

    # Debug logging
    current_app.logger.info(f"[GHL] Connection status check for user {current_user.id} ({current_user.email})")
    current_app.logger.info(f"[GHL] ghl_user_id: {current_user.ghl_user_id}, ghl_calendar_id: {current_user.ghl_calendar_id}")
    current_app.logger.info(f"[GHL] is_configured: {is_configured}, user_has_ghl: {user_has_ghl}")

    return jsonify({
        'success': True,
        'is_connected': is_configured and user_has_ghl,
        'ghl_configured': is_configured,
        'user_calendar_linked': user_has_ghl,
        'ghl_calendar_id': current_user.ghl_calendar_id,
        'ghl_user_id': current_user.ghl_user_id,
        'message': (
            'Connesso a GHL' if is_configured and user_has_ghl
            else 'Utente GHL non associato' if is_configured
            else 'GHL non configurato'
        )
    })