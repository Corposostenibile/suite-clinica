"""
Routes for GHL webhook endpoints
"""

from flask import request, jsonify, render_template, current_app, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from typing import Any, Dict
import json

from . import bp
from .security import require_webhook_signature, require_permission, rate_limiter
from .validators import WebhookValidator
from .tasks import process_acconto_open_webhook, process_chiuso_won_webhook, retry_failed_webhook
from corposostenibile.extensions import db, csrf
from corposostenibile.models import (
    GHLOpportunity,
    GHLOpportunityData,
    ServiceClienteAssignment,
    Cliente,
    Team,
    User,
    UserRoleEnum,
    Meeting,
    team_members,
)


# ============================================================================
# WEBHOOK ENDPOINTS
# ============================================================================


def _normalize_custom_data(raw_custom_data: Any) -> Dict[str, Any]:
    """Normalizza customData GHL in un dizionario key->value."""
    if isinstance(raw_custom_data, dict):
        return raw_custom_data

    if isinstance(raw_custom_data, list):
        normalized: Dict[str, Any] = {}
        for item in raw_custom_data:
            if not isinstance(item, dict):
                continue
            key = (
                item.get("key")
                or item.get("field")
                or item.get("fieldName")
                or item.get("name")
                or item.get("id")
            )
            if not key:
                continue
            value = (
                item.get("value")
                if "value" in item
                else item.get("field_value")
                if "field_value" in item
                else item.get("val")
            )
            normalized[str(key)] = value
        return normalized

    return {}


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
            continue
        return value
    return None


def _extract_opportunity_contact_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "email": "",
            "lead_phone": None,
            "health_manager_email": None,
            "custom_data": {},
        }

    custom_data = _normalize_custom_data(payload.get("customData", {}))
    contact = payload.get("contact", {}) if isinstance(payload.get("contact"), dict) else {}

    email = _first_non_empty(
        custom_data.get("email"),
        payload.get("email"),
        contact.get("email"),
    )

    lead_phone = _first_non_empty(
        custom_data.get("telefono"),
        custom_data.get("phone"),
        custom_data.get("cellulare"),
        custom_data.get("telefono_cliente"),
        custom_data.get("phone_number"),
        custom_data.get("numero_telefono"),
        custom_data.get("mobile"),
        payload.get("telefono"),
        payload.get("phone"),
        payload.get("cellulare"),
        payload.get("telefono_cliente"),
        payload.get("phone_number"),
        payload.get("numero_telefono"),
        payload.get("mobile"),
        contact.get("phone"),
        contact.get("mobile"),
    )

    health_manager_email = _first_non_empty(
        custom_data.get("health_manager_email"),
        custom_data.get("healthmanager_email"),
        custom_data.get("email_health_manager"),
        custom_data.get("hm_email"),
        custom_data.get("health_manager_mail"),
        custom_data.get("mail_health_manager"),
        payload.get("health_manager_email"),
        payload.get("healthmanager_email"),
        payload.get("email_health_manager"),
        payload.get("hm_email"),
        payload.get("health_manager_mail"),
        payload.get("mail_health_manager"),
    )

    if isinstance(health_manager_email, str):
        health_manager_email = health_manager_email.strip().lower() or None

    return {
        "email": email or "",
        "lead_phone": lead_phone,
        "health_manager_email": health_manager_email,
        "custom_data": custom_data,
    }


def _is_team_leader_user(user) -> bool:
    role = getattr(user, "role", None)
    role_val = role.value if hasattr(role, "value") else str(role or "")
    return role_val == UserRoleEnum.team_leader.value


def _get_team_leader_member_ids(user_id: int) -> set[int]:
    team_ids = db.session.query(Team.id).filter(
        Team.head_id == user_id,
        Team.is_active == True,
    )
    rows = db.session.query(team_members.c.user_id).filter(
        team_members.c.team_id.in_(team_ids)
    ).distinct().all()
    return {int(row[0]) for row in rows}


def _assignment_in_team_leader_scope(assignment: ServiceClienteAssignment, allowed_ids: set[int]) -> bool:
    if not assignment:
        return False
    assignee_ids = {
        assignment.nutrizionista_assigned_id,
        assignment.coach_assigned_id,
        assignment.psicologa_assigned_id,
    }
    return any(pid in allowed_ids for pid in assignee_ids if pid is not None)


def _serialize_opportunity_data_row(d: GHLOpportunityData) -> Dict[str, Any]:
    raw_payload = d.raw_payload or {}
    extracted = _extract_opportunity_contact_fields(raw_payload)
    resolved_email = (d.email or extracted["email"] or "").strip().lower()
    cliente_id = None
    if resolved_email:
        cliente = Cliente.query.filter(Cliente.mail.ilike(resolved_email)).first()
        if cliente:
            cliente_id = cliente.cliente_id
    # Resolve health manager
    hm = d.health_manager
    health_manager = None
    if hm:
        health_manager = {
            "id": hm.id,
            "full_name": hm.full_name,
            "avatar_url": hm.avatar_url,
        }

    return {
        "id": d.id,
        "cliente_id": cliente_id,
        "nome": d.nome,
        "email": d.email or extracted["email"],
        "lead_phone": d.lead_phone or extracted["lead_phone"],
        "health_manager_email": d.health_manager_email or extracted["health_manager_email"],
        "health_manager": health_manager,
        "storia": d.storia,
        "pacchetto": d.pacchetto,
        "durata": d.durata,
        "received_at": d.received_at.isoformat() if d.received_at else None,
        "ip_address": d.ip_address,
        "processed": d.processed,
    }


def _save_opportunity_data_payload(payload: Dict[str, Any], client_ip: str) -> GHLOpportunityData:
    extracted = _extract_opportunity_contact_fields(payload)
    custom_data = extracted["custom_data"]

    nome = (
        custom_data.get("nome")
        or payload.get("nome")
        or payload.get("full_name")
        or payload.get("opportunity_name")
        or f"{payload.get('first_name', '')} {payload.get('last_name', '')}".strip()
        or "N/D"
    )
    storia = custom_data.get("storia") or payload.get("storia") or ""
    pacchetto = (
        custom_data.get("pacchetto")
        or custom_data.get("package")
        or custom_data.get("plan")
        or payload.get("pacchetto")
        or payload.get("package")
        or payload.get("plan")
        or "N/D"
    )
    durata = (
        custom_data.get("durata")
        or custom_data.get("durata_in_giorni")
        or payload.get("durata")
        or payload.get("durata_in_giorni")
        or "0"
    )

    # Resolve health manager by email
    hm_email = extracted["health_manager_email"]
    hm_id = None
    if hm_email:
        hm_user = User.query.filter(
            User.email.ilike(hm_email.strip()),
            User.is_active == True,
        ).first()
        if hm_user:
            hm_id = hm_user.id
            current_app.logger.info(
                "[GHL Webhook] Resolved HM email %s -> User #%s (%s)",
                hm_email, hm_user.id, hm_user.full_name,
            )
        else:
            current_app.logger.warning(
                "[GHL Webhook] HM email %s not found in database", hm_email,
            )

    opp_data = GHLOpportunityData(
        nome=nome,
        email=extracted["email"] or None,
        lead_phone=extracted["lead_phone"] or None,
        health_manager_email=hm_email or None,
        health_manager_id=hm_id,
        storia=storia,
        pacchetto=pacchetto,
        durata=durata,
        ip_address=client_ip,
        raw_payload=payload,
    )
    db.session.add(opp_data)
    db.session.commit()

    current_app.logger.info(
        "[GHL Webhook] Saved opportunity data: %s - %s (ID: %s, phone=%s, hm_id=%s)",
        opp_data.nome,
        opp_data.pacchetto,
        opp_data.id,
        opp_data.lead_phone,
        opp_data.health_manager_id,
    )

    return opp_data

@bp.route('/webhook/acconto-open', methods=['POST'])
@csrf.exempt
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



@csrf.exempt
@bp.route('/webhook/nuovo-cliente', methods=['POST'])
@require_webhook_signature
def webhook_nuovo_cliente():
    """
    Riceve webhook quando un nuovo cliente viene creato da GHL.
    Alias di acconto-open per maggiore chiarezza.
    
    Endpoint: /ghl/webhook/nuovo-cliente
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
            f"[GHL Webhook] Received nuovo_cliente webhook for contact: {payload.get('contact', {}).get('name')}"
        )

        # Queue il task per processing asincrono
        task = process_acconto_open_webhook.delay(payload)

        # Rispondi immediatamente a GHL
        return jsonify({
            'success': True,
            'message': 'Nuovo cliente ricevuto e in elaborazione',
            'task_id': task.id
        }), 200

    except Exception as e:
        current_app.logger.error(f"[GHL Webhook] Error in nuovo_cliente endpoint: {e}")
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
        test_email = request.form.get('email', f'test-{datetime.now().timestamp()}@example.com')
        test_phone = request.form.get('telefono', '+39 123 456 7890')
        test_hm_email = request.form.get('health_manager_email', 'hm.test@corposostenibile.com')

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
                'email': test_email,
                'phone': test_phone,
                'source': request.form.get('source', 'test')
            }
        }

        # Payload test dedicato per endpoint opportunity-data
        opportunity_payload = {
            'nome': request.form.get('nome', 'Test User'),
            'storia': request.form.get('note', 'Lead di test inviato dalla pagina GHL interna'),
            'pacchetto': request.form.get('pacchetto', 'NCP'),
            'durata': '90',
            'customData': {
                'nome': request.form.get('nome', 'Test User'),
                'email': test_email,
                'telefono': test_phone,
                'health_manager_email': test_hm_email,
                'pacchetto': request.form.get('pacchetto', 'NCP'),
                'storia': request.form.get('note', 'Lead di test inviato dalla pagina GHL interna'),
            },
            'contact': {
                'email': test_email,
                'phone': test_phone,
            },
        }

        # Processa direttamente (bypass security per test)
        if webhook_type == 'opportunity_data':
            opp_data = _save_opportunity_data_payload(opportunity_payload, request.remote_addr or '127.0.0.1')
            if opp_data.email and str(opp_data.email).strip():
                from .opportunity_bridge import process_opportunity_data_bridge
                process_opportunity_data_bridge(opp_data)
            flash(f'Webhook opportunity-data test salvato! ID: {opp_data.id}', 'success')
            return redirect(url_for('ghl_integration.webhook_status'))

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
        'pacchetto': opp.pacchetto_comprato,
        'storia': opp.cliente.storia_cliente if opp.cliente else opp.note_cliente,
        'cliente_id': opp.cliente_id,
        'assignment_id': opp.cliente.service_assignment[0].id if opp.cliente and opp.cliente.service_assignment.count() > 0 else None,
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
    API endpoint per ottenere le assegnazioni servizio clienti.
    Include email e telefono del cliente (da Cliente.mail) per contatto.
    status=all: tutte le assegnazioni.
    """
    status = request.args.get('status', 'pending_finance')

    query = ServiceClienteAssignment.query
    if status != 'all':
        query = query.filter_by(status=status)
    assignments = query.order_by(
        ServiceClienteAssignment.created_at.desc()
    ).limit(300).all()

    if _is_team_leader_user(current_user) and not current_user.is_admin:
        allowed_ids = _get_team_leader_member_ids(current_user.id) | {current_user.id}
        assignments = [a for a in assignments if _assignment_in_team_leader_scope(a, allowed_ids)]

    assignments = assignments[:100]

    data = [{
        'id': ass.id,
        'cliente_id': ass.cliente_id,
        'cliente_nome': ass.cliente.nome_cognome if ass.cliente else None,
        'cliente_email': getattr(ass.cliente, 'mail', None) if ass.cliente else None,
        'cliente_cellulare': getattr(ass.cliente, 'cellulare', None) or getattr(ass.cliente, 'numero_telefono', None) if ass.cliente else None,
        'status': ass.status,
        'finance_approved': ass.finance_approved,
        'checkup_iniziale_fatto': ass.checkup_iniziale_fatto,
        'nutrizionista_assigned': ass.nutrizionista_assigned_id is not None,
        'coach_assigned': ass.coach_assigned_id is not None,
        'psicologa_assigned': ass.psicologa_assigned_id is not None,
        'ai_analysis': ass.ai_analysis,
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

@bp.route('/api/calendar/team-members', methods=['GET'])
@login_required
def api_get_calendar_team_members():
    """
    Restituisce i membri del team visibili dall'utente corrente per il filtro calendario.

    - admin / cco: tutti gli utenti con ghl_user_id
    - team_leader: solo i membri dei propri team (+ se stesso)
    - professionista: solo se stesso (nessun filtro mostrato)
    """
    is_admin = current_user.is_admin
    is_tl = _is_team_leader_user(current_user)

    if not is_admin and not is_tl:
        # Professionista normale: nessun membro da mostrare
        return jsonify({'success': True, 'members': []})

    if is_admin:
        # Admin vede tutti gli utenti con GHL configurato
        users = User.query.filter(
            User.is_active == True,
            User.ghl_user_id.isnot(None),
            User.ghl_user_id != '',
        ).order_by(User.first_name, User.last_name).all()
    else:
        # Team leader: membri dei propri team + se stesso
        member_ids = _get_team_leader_member_ids(current_user.id) | {current_user.id}
        users = User.query.filter(
            User.id.in_(member_ids),
            User.is_active == True,
            User.ghl_user_id.isnot(None),
            User.ghl_user_id != '',
        ).order_by(User.first_name, User.last_name).all()

    members = []
    for u in users:
        role_val = u.role.value if u.role and hasattr(u.role, 'value') else str(u.role or '')
        spec_val = u.specialty.value if u.specialty and hasattr(u.specialty, 'value') else str(u.specialty or '')
        members.append({
            'id': u.id,
            'full_name': u.full_name or f"{u.first_name} {u.last_name}".strip(),
            'avatar_path': u.avatar_path,
            'role': role_val,
            'specialty': spec_val,
        })

    return jsonify({'success': True, 'members': members})


@bp.route('/api/calendar/events', methods=['GET'])
@login_required
def api_get_calendar_events():
    """
    Ottiene gli eventi calendario.
    Accetta ?user_id= opzionale per admin e team_leader.
    Con auto-match clienti Suite Clinica.
    """
    # Parametri date
    start = request.args.get('start')
    end = request.args.get('end')
    target_user_id = request.args.get('user_id', type=int)

    if not start or not end:
        # Default: mese corrente
        today = datetime.utcnow()
        start = today.replace(day=1).strftime('%Y-%m-%d')
        end = (today.replace(day=1) + timedelta(days=32)).replace(day=1).strftime('%Y-%m-%d')

    # Determina per quale utente caricare gli eventi
    if target_user_id and target_user_id != current_user.id:
        # Verifica permesso di visualizzare il calendario di un altro utente
        is_admin = current_user.is_admin
        is_tl = _is_team_leader_user(current_user)

        if not is_admin and not is_tl:
            return jsonify({
                'success': False,
                'message': 'Non hai i permessi per vedere questo calendario',
                'events': []
            }), 403

        if is_tl and not is_admin:
            allowed_ids = _get_team_leader_member_ids(current_user.id) | {current_user.id}
            if target_user_id not in allowed_ids:
                return jsonify({
                    'success': False,
                    'message': 'Utente non nel tuo team',
                    'events': []
                }), 403

        view_user = User.query.get(target_user_id)
        if not view_user:
            return jsonify({
                'success': False,
                'message': 'Utente non trovato',
                'events': []
            }), 404
    else:
        view_user = current_user
        target_user_id = current_user.id

    try:
        from .calendar_service import get_ghl_calendar_service
        service = get_ghl_calendar_service()

        if not service.is_configured():
            return jsonify({
                'success': False,
                'message': 'GHL non configurato',
                'events': []
            })

        # Verifica che l'utente target abbia un calendario O un utente GHL associato
        if not view_user.ghl_calendar_id and not view_user.ghl_user_id:
            return jsonify({
                'success': False,
                'message': 'Calendario GHL non configurato per questo utente',
                'events': []
            })

        # Ottieni eventi
        events = service.get_events_for_user(target_user_id, start, end)

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
    Ottiene gli slot disponibili per il calendario dell'utente corrente 
    o di un altro utente (se si hanno i permessi).
    """
    start = request.args.get('start')
    end = request.args.get('end')
    user_id_param = request.args.get('user_id')

    if not start or not end:
        # Default: prossimi 30 giorni
        today = datetime.utcnow()
        start = today.strftime('%Y-%m-%d')
        end = (today + timedelta(days=30)).strftime('%Y-%m-%d')

    target_user = current_user
    if user_id_param:
        try:
            target_id = int(user_id_param)
            if target_id != current_user.id:
                is_admin = current_user.is_admin or getattr(current_user, 'role', '') == 'admin'
                is_cco = str(getattr(current_user, 'specialty', '')).lower() == 'cco'
                is_team_leader = getattr(current_user, 'role', '') == 'team_leader'
                
                # Se è Team Leader, permettiamo la visualizzazione se target fa parte del suo team
                can_view = False
                if is_admin or is_cco:
                    can_view = True
                elif is_team_leader:
                    allowed_ids = _get_team_leader_member_ids(current_user.id)
                    if target_id in allowed_ids:
                        can_view = True

                if can_view:
                    user_obj = User.query.get(target_id)
                    if user_obj:
                        target_user = user_obj
                else:
                    return jsonify({'success': False, 'message': 'Non autorizzato a visualizzare questo utente'}), 403
        except ValueError:
            pass

    try:
        from .calendar_service import get_ghl_calendar_service
        service = get_ghl_calendar_service()

        if not service.is_configured():
            return jsonify({
                'success': False,
                'message': 'GHL non configurato'
            })

        if not target_user.ghl_calendar_id:
            return jsonify({
                'success': False,
                'message': 'Calendario GHL non configurato per questo utente'
            })

        slots = service.get_free_slots(
            target_user.ghl_calendar_id,
            start,
            end,
            user_id=target_user.ghl_user_id
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


def _parse_iso_datetime(value: str | None) -> datetime | None:
    """Parse ISO datetime string with basic Z support."""
    if not value or not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace('Z', '+00:00'))
    except ValueError:
        return None


@bp.route('/api/calendar/appointments', methods=['POST'])
@csrf.exempt
@login_required
def api_create_calendar_appointment():
    """
    Crea una prenotazione GHL dal frontend Suite Clinica.

    Flusso pensato per professionista loggato: usa il suo account GHL
    (calendar/user mapping personale) come default, oppure quello specificato
    da user_id nel payload se autorizzato.
    """
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({'success': False, 'message': 'Payload non valido'}), 400

    start_time = _parse_iso_datetime(data.get('start_time'))
    end_time = _parse_iso_datetime(data.get('end_time'))
    if not start_time:
        return jsonify({'success': False, 'message': 'start_time richiesto (ISO 8601)'}), 400
    if not end_time:
        duration_minutes = data.get('duration_minutes', 30)
        try:
            duration_minutes = int(duration_minutes)
        except (TypeError, ValueError):
            duration_minutes = 30
        if duration_minutes <= 0:
            duration_minutes = 30
        end_time = start_time + timedelta(minutes=duration_minutes)
    if end_time <= start_time:
        return jsonify({'success': False, 'message': 'end_time deve essere successivo a start_time'}), 400

    target_user = current_user
    user_id_param = data.get('user_id')
    if user_id_param:
        try:
            target_id = int(user_id_param)
            if target_id != current_user.id:
                is_admin = current_user.is_admin or getattr(current_user, 'role', '') == 'admin'
                is_cco = str(getattr(current_user, 'specialty', '')).lower() == 'cco'
                is_team_leader = getattr(current_user, 'role', '') == 'team_leader'
                
                can_view = False
                if is_admin or is_cco:
                    can_view = True
                elif is_team_leader:
                    allowed_ids = _get_team_leader_member_ids(current_user.id)
                    if target_id in allowed_ids:
                        can_view = True

                if can_view:
                    user_obj = User.query.get(target_id)
                    if user_obj:
                        target_user = user_obj
                else:
                    return jsonify({'success': False, 'message': 'Non autorizzato a prenotare per questo utente'}), 403
        except ValueError:
            pass

    try:
        from .calendar_service import get_ghl_calendar_service
        service = get_ghl_calendar_service()

        if not service.is_configured():
            return jsonify({'success': False, 'message': 'GHL non configurato'}), 400

        requested_calendar_id = (data.get('calendar_id') or '').strip()
        user_calendar_id = (target_user.ghl_calendar_id or '').strip()
        calendar_id = requested_calendar_id or user_calendar_id

        if not calendar_id:
            return jsonify({
                'success': False,
                'message': 'Nessun calendario GHL associato. Configura ghl_calendar_id per questo utente.'
            }), 400

        # Vincolo: il professionista usa il proprio calendario (o quello impostato di default).
        if requested_calendar_id and not current_user.is_admin and user_calendar_id and requested_calendar_id != user_calendar_id:
            return jsonify({
                'success': False,
                'message': 'Non autorizzato a prenotare su un calendario diverso da quello assegnato.'
            }), 403

        contact_id = (data.get('contact_id') or '').strip()
        cliente_id = data.get('cliente_id')

        cliente = None
        if not contact_id and cliente_id is not None:
            cliente = Cliente.query.get(cliente_id)
            if not cliente:
                return jsonify({'success': False, 'message': 'Cliente non trovato'}), 404

            if cliente.ghl_contact_id:
                contact_id = str(cliente.ghl_contact_id).strip()
            else:
                # Fallback: prova match su contatti GHL usando mail/telefono cliente.
                email = (getattr(cliente, 'mail', None) or '').strip()
                phone = (getattr(cliente, 'numero_telefono', None) or '').strip()
                matches = service.search_contacts(email=email or None, phone=phone or None, limit=5)
                if len(matches) == 1 and matches[0].get('id'):
                    contact_id = str(matches[0]['id']).strip()
                    cliente.ghl_contact_id = contact_id
                    db.session.commit()

        if not contact_id:
            return jsonify({
                'success': False,
                'message': 'contact_id o cliente_id con contatto GHL associato richiesto'
            }), 400

        timezone = (data.get('timezone') or 'Europe/Rome').strip()
        title = (data.get('title') or '').strip() or None
        notes = (data.get('notes') or '').strip() or None

        appointment = service.create_appointment(
            calendar_id=calendar_id,
            contact_id=contact_id,
            start_time=start_time,
            end_time=end_time,
            title=title,
            notes=notes,
            timezone=timezone,
            assigned_user_id=current_user.ghl_user_id or None,
            appointment_status='confirmed',
        )

        appointment_id = (
            appointment.get('id')
            or appointment.get('appointment', {}).get('id')
            if isinstance(appointment, dict) else None
        )

        # Persistiamo un Meeting locale minimo per tracciamento interno.
        if appointment_id and not Meeting.query.filter_by(ghl_event_id=appointment_id).first():
            meeting = Meeting(
                ghl_event_id=appointment_id,
                title=title or 'Meeting GHL',
                start_time=start_time,
                end_time=end_time,
                cliente_id=cliente.cliente_id if cliente else None,
                user_id=current_user.id,
                status='scheduled',
            )
            db.session.add(meeting)
            db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Appuntamento creato con successo',
            'appointment': appointment,
            'calendar_id': calendar_id,
            'contact_id': contact_id
        }), 201

    except Exception as e:
        current_app.logger.error(f"[GHL] Error creating appointment: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Errore durante creazione appuntamento',
            'details': str(e),
        }), 500


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


# ============================================================================
# LOOM INTEGRATION API
# ============================================================================

@bp.route('/api/meeting/loom', methods=['POST'])
@csrf.exempt
@login_required
def save_ghl_meeting_loom():
    """
    Salva link Loom per un evento GHL.
    Crea o aggiorna record Meeting locale associato all'evento GHL.

    Expected payload:
    {
        "ghl_event_id": "xxx",
        "loom_link": "https://www.loom.com/share/xxx",
        "title": "Call con Mario Rossi",
        "start_time": "2024-01-15T10:00:00",
        "end_time": "2024-01-15T11:00:00",
        "cliente_id": 123,  // opzionale
        "ghl_calendar_id": "yyy"  // opzionale
    }
    """
    from corposostenibile.models import Meeting

    try:
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'message': 'Dati non forniti'}), 400

        # Dati richiesti
        ghl_event_id = data.get('ghl_event_id')
        loom_link = data.get('loom_link')

        if not ghl_event_id:
            return jsonify({'success': False, 'message': 'ghl_event_id richiesto'}), 400

        if not loom_link:
            return jsonify({'success': False, 'message': 'loom_link richiesto'}), 400

        # Dati opzionali per creare Meeting se non esiste
        title = data.get('title', 'Meeting GHL')
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')
        cliente_id = data.get('cliente_id')

        # Cerca Meeting esistente con ghl_event_id
        meeting = Meeting.query.filter_by(ghl_event_id=ghl_event_id).first()

        if meeting:
            # Aggiorna solo loom_link
            meeting.loom_link = loom_link
            current_app.logger.info(f"[GHL Loom] Updated loom_link for existing meeting {meeting.id}")
        else:
            # Crea nuovo Meeting
            # Parse delle date
            start_time = None
            end_time = None

            if start_time_str:
                try:
                    start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                except ValueError:
                    start_time = datetime.utcnow()
            else:
                start_time = datetime.utcnow()

            if end_time_str:
                try:
                    end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                except ValueError:
                    end_time = start_time + timedelta(minutes=30)
            else:
                end_time = start_time + timedelta(minutes=30)

            meeting = Meeting(
                ghl_event_id=ghl_event_id,
                title=title,
                start_time=start_time,
                end_time=end_time,
                cliente_id=cliente_id if cliente_id else None,
                user_id=current_user.id,
                loom_link=loom_link,
                status='completed'
            )
            db.session.add(meeting)
            current_app.logger.info(f"[GHL Loom] Created new meeting for GHL event {ghl_event_id}")

        db.session.commit()

        return jsonify({
            'success': True,
            'meeting_id': meeting.id,
            'message': 'Link Loom salvato con successo'
        })

    except Exception as e:
        current_app.logger.error(f"[GHL Loom] Error saving loom link: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/api/meeting/loom/<ghl_event_id>', methods=['GET'])
@login_required
def get_ghl_meeting_loom(ghl_event_id):
    """
    Ottiene il link Loom per un evento GHL.
    """
    from corposostenibile.models import Meeting

    meeting = Meeting.query.filter_by(ghl_event_id=ghl_event_id).first()

    if meeting:
        return jsonify({
            'success': True,
            'meeting_id': meeting.id,
            'loom_link': meeting.loom_link,
            'has_loom': bool(meeting.loom_link)
        })
    else:
        return jsonify({
            'success': True,
            'meeting_id': None,
            'loom_link': None,
            'has_loom': False
        })


# ============================================================================
# WEBHOOK OPPORTUNITY DATA - CON DATABASE
# ============================================================================

@csrf.exempt
@bp.route('/webhook/opportunity-data', methods=['POST'])
def webhook_opportunity_data():
    """
    Riceve webhook con dati opportunity semplificati da GHL.
    Salva nel database per persistenza.

    Expected payload:
    {
        "nome": "Mario Rossi",
        "storia": "Storia del cliente...",
        "pacchetto": "Premium 3 mesi",
        "durata": "90"
    }

    Endpoint: /ghl/webhook/opportunity-data
    """
    try:
        client_ip = request.remote_addr
        if not rate_limiter.is_allowed(f"webhook_opp_{client_ip}"):
            current_app.logger.warning(f"[GHL Webhook] Rate limit exceeded for IP: {client_ip}")
            return jsonify({'error': 'Rate limit exceeded'}), 429

        # Ottieni il payload (supporta sia JSON che form data)
        if request.is_json:
            payload = request.get_json()
        else:
            payload = request.form.to_dict()

        if not payload:
            return jsonify({'error': 'No payload provided'}), 400

        opp_data = _save_opportunity_data_payload(payload, client_ip)

        # Bridge: se email presente, crea Cliente, assegna Check iniziali e invia email
        if opp_data.email and str(opp_data.email).strip():
            try:
                from .opportunity_bridge import process_opportunity_data_bridge
                bridge_result = process_opportunity_data_bridge(opp_data)
                current_app.logger.info(
                    f"[GHL Webhook] Bridge opportunity-data: {bridge_result}"
                )
            except Exception as bridge_err:
                current_app.logger.error(
                    f"[GHL Webhook] Bridge opportunity-data fallito: {bridge_err}"
                )
                import traceback
                current_app.logger.error(traceback.format_exc())

        return jsonify({
            'success': True,
            'message': 'Dati ricevuti con successo',
            'id': opp_data.id
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[GHL Webhook] Error in opportunity_data endpoint: {e}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500


@bp.route('/api/opportunity-data', methods=['GET'])
@login_required
def api_get_opportunity_data():
    """Recupera tutti i dati opportunity dal database."""
    try:
        data = GHLOpportunityData.query.order_by(GHLOpportunityData.received_at.desc()).limit(200).all()
        if _is_team_leader_user(current_user) and not current_user.is_admin:
            allowed_ids = _get_team_leader_member_ids(current_user.id) | {current_user.id}
            scoped_rows = []
            for d in data:
                assignments = _get_current_assignments_for_opp(d)
                assigned_ids = {
                    assignments.get('nutritionist_id'),
                    assignments.get('coach_id'),
                    assignments.get('psychologist_id'),
                }
                if any(pid in allowed_ids for pid in assigned_ids if pid is not None):
                    scoped_rows.append((d, assignments))
            data_with_assignments = scoped_rows[:100]
        else:
            data_with_assignments = [(d, _get_current_assignments_for_opp(d)) for d in data[:100]]

        return jsonify({
            'success': True,
            'data': [
                {
                    **_serialize_opportunity_data_row(d),
                    'ai_analysis': d.ai_analysis,
                    'assignments': assignments,
                }
                for d, assignments in data_with_assignments
            ],
            'total': len(data_with_assignments)
        })
    except Exception as e:
        current_app.logger.error(f"[GHL API] Error fetching opportunity data: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/api/webhook-urls', methods=['GET'])
def api_webhook_urls():
    """
    Restituisce gli URL webhook per questo backend (porta dinamica per sviluppatore).
    Usato dalla pagina Assegnazioni AI per mostrare l'URL corretto da configurare in GHL.
    """
    base = current_app.config.get('BASE_URL', 'http://localhost:5001')
    base = base.rstrip('/')
    return jsonify({
        'success': True,
        'base_url': base,
        'opportunity_data_url': f'{base}/ghl/webhook/opportunity-data',
        'acconto_open_url': f'{base}/ghl/webhook/acconto-open',
    })


# DEBUG ENDPOINT - Pubblico per test (rimuovere in produzione)
def _get_current_assignments_for_opp(opp_data):
    """Recupera le assegnazioni correnti per un'opportunità GHL."""
    from corposostenibile.models import Cliente, ServiceClienteAssignment
    
    # Trova email nel payload
    payload = opp_data.raw_payload or {}
    email = payload.get('email') or payload.get('contact', {}).get('email')
    
    if not email:
        return {}
        
    cliente = Cliente.query.filter_by(mail=email).first()
    if not cliente:
        return {}
        
    assignment = ServiceClienteAssignment.query.filter_by(cliente_id=cliente.cliente_id).first()
    if not assignment:
        return {}
        
    return {
        'nutritionist_id': assignment.nutrizionista_assigned_id,
        'coach_id': assignment.coach_assigned_id,
        'psychologist_id': assignment.psicologa_assigned_id
    }


@bp.route('/api/opportunity-data-debug', methods=['GET'])
def api_get_opportunity_data_debug():
    """DEBUG: Recupera dati senza autenticazione."""
    try:
        data = GHLOpportunityData.query.order_by(GHLOpportunityData.received_at.desc()).limit(100).all()
        return jsonify({
            'success': True,
            'data': [
                {
                    **_serialize_opportunity_data_row(d),
                    'ai_analysis': d.ai_analysis,
                    'assignments': _get_current_assignments_for_opp(d),
                }
                for d in data
            ],
            'total': len(data)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/api/opportunity-data/<int:item_id>', methods=['GET'])
@login_required
def api_get_opportunity_data_single(item_id):
    """Recupera un singolo record opportunity."""
    try:
        d = GHLOpportunityData.query.get(item_id)
        if not d:
            return jsonify({'success': False, 'message': 'Non trovato'}), 404
        return jsonify({
            'success': True,
            'data': {
                **_serialize_opportunity_data_row(d),
                'ai_analysis': d.ai_analysis,
                'raw_payload': d.raw_payload,
                'assignments': _get_current_assignments_for_opp(d),
            },
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/api/opportunity-data/clear', methods=['POST'])
@login_required
def api_clear_opportunity_data():
    """Pulisce tutti i dati (solo admin)."""
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Non autorizzato'}), 403
    try:
        GHLOpportunityData.query.delete()
        db.session.commit()
        return jsonify({'success': True, 'message': 'Dati cancellati'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================================
# CALL BONUS SALE WEBHOOK (GHL → Suite)
# ============================================================================

@bp.route('/webhook/call-bonus-sale', methods=['POST'])
@csrf.exempt
def webhook_call_bonus_sale():
    """
    Riceve webhook da GHL quando l'HM completa la vendita call bonus.

    Payload atteso:
        Giorni (int)  - giorni acquistati
        Nome   (str)  - nome cognome del cliente
    """
    from corposostenibile.models import (
        CallBonus, CallBonusStatusEnum, TipoProfessionistaEnum,
    )
    from datetime import date, timedelta

    # GHL può mandare JSON o form-data
    payload = request.get_json(silent=True) or {}
    if not payload:
        payload = request.form.to_dict()
    if not payload:
        payload = request.values.to_dict()

    current_app.logger.info(
        '[GHL] call-bonus-sale RAW payload: %s (content-type: %s)',
        payload, request.content_type,
    )

    custom = payload.get('customData') or {}
    if isinstance(custom, str):
        import json as _json
        try:
            custom = _json.loads(custom)
        except (ValueError, TypeError):
            custom = {}
    giorni_raw = custom.get('Giorni') or payload.get('Giorni')
    nome = (custom.get('Nome') or payload.get('full_name') or payload.get('Nome') or '').strip()

    current_app.logger.info(
        '[GHL] call-bonus-sale webhook received: Nome=%s Giorni=%s',
        nome, giorni_raw,
    )

    if not nome:
        return jsonify({'success': False, 'message': 'Campo Nome mancante'}), 400

    try:
        giorni = int(giorni_raw)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Campo Giorni non valido'}), 400

    # 1. Trova il cliente per nome_cognome
    cliente = Cliente.query.filter(
        db.func.lower(Cliente.nome_cognome) == nome.lower()
    ).first()
    if not cliente:
        current_app.logger.warning('[GHL] call-bonus-sale: cliente non trovato per Nome=%s', nome)
        return jsonify({'success': False, 'message': f'Cliente non trovato: {nome}'}), 404

    # 2. Trova la call bonus "interessato" più recente per questo cliente
    call_bonus = (
        CallBonus.query
        .filter(
            CallBonus.cliente_id == cliente.cliente_id,
            CallBonus.status == CallBonusStatusEnum.interessato,
        )
        .order_by(CallBonus.data_interesse.desc())
        .first()
    )
    if not call_bonus:
        current_app.logger.warning(
            '[GHL] call-bonus-sale: nessuna call bonus "interessato" per cliente_id=%s',
            cliente.cliente_id,
        )
        return jsonify({'success': False, 'message': 'Nessuna call bonus interessato trovata'}), 404

    prof = call_bonus.professionista
    if not prof:
        return jsonify({'success': False, 'message': 'Professionista non trovato nella call bonus'}), 404

    tipo = call_bonus.tipo_professionista
    today = date.today()
    scadenza = today + timedelta(days=giorni)

    # 3. Assegna il professionista al cliente (multipli)
    tipo_value = tipo.value if hasattr(tipo, 'value') else str(tipo)
    if tipo_value == 'nutrizionista':
        if prof not in cliente.nutrizionisti_multipli:
            cliente.nutrizionisti_multipli.append(prof)
        cliente.data_inizio_nutrizione = today
        cliente.durata_nutrizione_giorni = giorni
        cliente.recalc_scadenza_servizio('nutrizione')
    elif tipo_value == 'coach':
        if prof not in cliente.coaches_multipli:
            cliente.coaches_multipli.append(prof)
        cliente.data_inizio_coach = today
        cliente.durata_coach_giorni = giorni
        cliente.recalc_scadenza_servizio('coach')
    elif tipo_value == 'psicologa':
        if prof not in cliente.psicologi_multipli:
            cliente.psicologi_multipli.append(prof)
        cliente.data_inizio_psicologia = today
        cliente.durata_psicologia_giorni = giorni
        cliente.recalc_scadenza_servizio('psicologia')
    else:
        return jsonify({'success': False, 'message': f'Tipo professionista non gestito: {tipo_value}'}), 400

    # 4. Aggiorna status call bonus → confermata
    call_bonus.status = CallBonusStatusEnum.confermata
    call_bonus.confermata_hm = True
    call_bonus.data_conferma_hm = today

    db.session.commit()

    current_app.logger.info(
        '[GHL] call-bonus-sale OK: cliente=%s prof=%s tipo=%s giorni=%d scadenza=%s',
        cliente.nome_cognome, prof.full_name, tipo_value, giorni, scadenza.isoformat(),
    )

    return jsonify({
        'success': True,
        'message': f'Professionista {prof.full_name} assegnato a {cliente.nome_cognome}',
        'data': {
            'cliente_id': cliente.cliente_id,
            'professionista': prof.full_name,
            'tipo': tipo_value,
            'data_inizio': today.isoformat(),
            'data_scadenza': scadenza.isoformat(),
            'call_bonus_id': call_bonus.id,
        },
    })


# ============================================================================
# GHOST RECOVERY WEBHOOK (GHL → Suite)
# ============================================================================

@bp.route('/webhook/ghost-recovery', methods=['POST'])
@csrf.exempt
def webhook_ghost_recovery():
    """
    Riceve webhook da GHL quando l'HM recupera un cliente ghost.
    Rimette lo stato cliente a "attivo".

    Payload atteso (in customData):
        Nome (str) - nome cognome del cliente
    """
    from corposostenibile.models import StatoClienteEnum

    payload = request.get_json(silent=True) or {}
    if not payload:
        payload = request.form.to_dict()
    if not payload:
        payload = request.values.to_dict()

    current_app.logger.info(
        '[GHL] ghost-recovery RAW payload: %s (content-type: %s)',
        payload, request.content_type,
    )

    custom = payload.get('customData') or {}
    if isinstance(custom, str):
        try:
            custom = json.loads(custom)
        except (ValueError, TypeError):
            custom = {}

    nome = (custom.get('Nome') or payload.get('full_name') or payload.get('Nome') or '').strip()

    if not nome:
        return jsonify({'success': False, 'message': 'Campo Nome mancante'}), 400

    cliente = Cliente.query.filter(
        db.func.lower(Cliente.nome_cognome) == nome.lower()
    ).first()
    if not cliente:
        current_app.logger.warning('[GHL] ghost-recovery: cliente non trovato per Nome=%s', nome)
        return jsonify({'success': False, 'message': f'Cliente non trovato: {nome}'}), 404

    old_status = cliente.stato_cliente.value if cliente.stato_cliente else None
    cliente.stato_cliente = StatoClienteEnum.attivo

    # Riattiva gli stati per ogni professionista assegnato (con storico)
    reactivated = []
    if cliente.nutrizionisti_multipli or cliente.nutrizionista_id:
        cliente.update_stato_servizio('nutrizione', StatoClienteEnum.attivo)
        reactivated.append('nutrizione')
    if cliente.coaches_multipli or cliente.coach_id:
        cliente.update_stato_servizio('coach', StatoClienteEnum.attivo)
        reactivated.append('coach')
    if cliente.psicologi_multipli or cliente.psicologa_id:
        cliente.update_stato_servizio('psicologia', StatoClienteEnum.attivo)
        reactivated.append('psicologia')

    db.session.commit()

    current_app.logger.info(
        '[GHL] ghost-recovery OK: cliente=%s stato %s → attivo, professionisti: %s',
        cliente.nome_cognome, old_status, reactivated,
    )

    return jsonify({
        'success': True,
        'message': f'Cliente {cliente.nome_cognome} riportato ad attivo',
        'data': {
            'cliente_id': cliente.cliente_id,
            'old_status': old_status,
            'new_status': 'attivo',
            'professionisti_riattivati': reactivated,
        },
    })


# ============================================================================
# PAUSA SERVIZIO WEBHOOK (GHL → Suite)
# ============================================================================

# Mapping nomi GHL → nomi servizio interni
_GHL_PROF_MAP = {
    'nutrizionista': 'nutrizione',
    'nutrizione': 'nutrizione',
    'coach': 'coach',
    'coaching': 'coach',
    'psicologo': 'psicologia',
    'psicologa': 'psicologia',
    'psicologia': 'psicologia',
}


@bp.route('/webhook/pausa-servizio', methods=['POST'])
@csrf.exempt
def webhook_pausa_servizio():
    """
    Riceve webhook da GHL quando l'HM registra una pausa per un cliente.

    Payload atteso (in customData):
        Nome                    (str)  - nome cognome del cliente
        Professionisti in Pausa (str)  - multi-select: "Nutrizionista, Coach, Psicologo"
        Durata Pausa In Giorni  (int)  - giorni di pausa
        Data Inizio Pausa       (str)  - data inizio pausa (ISO o GHL format)
    """
    from corposostenibile.models import StatoClienteEnum
    from datetime import date, timedelta
    from dateutil import parser as dateparser

    payload = request.get_json(silent=True) or {}
    if not payload:
        payload = request.form.to_dict()
    if not payload:
        payload = request.values.to_dict()

    current_app.logger.info(
        '[GHL] pausa-servizio RAW payload: %s', payload,
    )

    custom = payload.get('customData') or {}
    if isinstance(custom, str):
        try:
            custom = json.loads(custom)
        except (ValueError, TypeError):
            custom = {}

    nome = (custom.get('Nome') or payload.get('full_name') or payload.get('Nome') or '').strip()
    prof_raw = custom.get('Professionisti in Pausa') or custom.get('professionisti_in_pausa') or ''
    giorni_raw = custom.get('Durata Pausa In Giorni') or custom.get('durata_pausa_in_giorni')
    data_inizio_raw = custom.get('Data Inizio Pausa') or custom.get('data_inizio_pausa') or ''

    if not nome:
        return jsonify({'success': False, 'message': 'Campo Nome mancante'}), 400

    # Parse giorni
    try:
        giorni = int(giorni_raw)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': f'Durata Pausa non valida: {giorni_raw}'}), 400

    # Parse data inizio pausa
    data_inizio = None
    if data_inizio_raw:
        try:
            data_inizio = dateparser.parse(str(data_inizio_raw)).date()
        except (ValueError, TypeError):
            data_inizio = None
    if not data_inizio:
        data_inizio = date.today()

    # Parse professionisti selezionati
    if isinstance(prof_raw, list):
        prof_list = prof_raw
    else:
        prof_list = [p.strip() for p in str(prof_raw).split(',') if p.strip()]

    servizi = []
    for p in prof_list:
        s = _GHL_PROF_MAP.get(p.lower())
        if s:
            servizi.append(s)

    if not servizi:
        return jsonify({'success': False, 'message': f'Nessun servizio riconosciuto: {prof_raw}'}), 400

    # Trova cliente
    cliente = Cliente.query.filter(
        db.func.lower(Cliente.nome_cognome) == nome.lower()
    ).first()
    if not cliente:
        current_app.logger.warning('[GHL] pausa-servizio: cliente non trovato per Nome=%s', nome)
        return jsonify({'success': False, 'message': f'Cliente non trovato: {nome}'}), 404

    # Aggiorna ogni servizio selezionato
    paused = []
    durata_map = {
        'nutrizione': 'durata_nutrizione_giorni',
        'coach': 'durata_coach_giorni',
        'psicologia': 'durata_psicologia_giorni',
    }
    for servizio in servizi:
        # Metti in pausa (con storico)
        cliente.update_stato_servizio(servizio, StatoClienteEnum.pausa)

        # Estendi la durata del servizio di N giorni → ricalcola scadenza
        durata_attr = durata_map.get(servizio)
        if durata_attr:
            current_durata = getattr(cliente, durata_attr, None) or 0
            setattr(cliente, durata_attr, current_durata + giorni)
            cliente.recalc_scadenza_servizio(servizio)

        paused.append(servizio)

    # Estendi la durata globale
    cliente.durata_programma_giorni = (cliente.durata_programma_giorni or 0) + giorni

    db.session.commit()

    # Schedula auto-riattivazione dopo N giorni
    from .tasks import reactivate_after_pausa
    eta_date = data_inizio + timedelta(days=giorni)
    eta_datetime = datetime(eta_date.year, eta_date.month, eta_date.day, 8, 0, 0)  # alle 8:00
    reactivate_after_pausa.apply_async(
        kwargs={
            'cliente_id': cliente.cliente_id,
            'servizi': paused,
        },
        eta=eta_datetime,
    )

    current_app.logger.info(
        '[GHL] pausa-servizio OK: cliente=%s servizi=%s giorni=%d data_inizio=%s riattivazione=%s',
        cliente.nome_cognome, paused, giorni, data_inizio.isoformat(), eta_date.isoformat(),
    )

    return jsonify({
        'success': True,
        'message': f'Pausa registrata per {cliente.nome_cognome}',
        'data': {
            'cliente_id': cliente.cliente_id,
            'servizi_in_pausa': paused,
            'giorni': giorni,
            'data_inizio_pausa': data_inizio.isoformat(),
            'riattivazione_prevista': eta_date.isoformat(),
        },
    })
