"""
Old Suite Integration Routes (TEMPORANEO)

Webhook receiver + API endpoints per il frontend Assegnazioni Old Suite.
"""

import logging
from datetime import datetime

from flask import request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import func

from corposostenibile.extensions import db, csrf
from corposostenibile.models import (
    SalesLead, User, Cliente, ServiceClienteAssignment,
    ClienteProfessionistaHistory, ServiceClienteNote,
    TipologiaClienteEnum,
)
from . import bp
from .package_parser import parse_package_name

logger = logging.getLogger(__name__)


# =============================================================================
# Helpers
# =============================================================================

def _resolve_user_by_name(full_name: str):
    """Trova un User per nome completo (case-insensitive). Fallback per cognome."""
    if not full_name:
        return None

    name = full_name.strip()

    # Match esatto su first_name + last_name
    user = User.query.filter(
        func.lower(func.concat(User.first_name, ' ', User.last_name)) == name.lower()
    ).first()
    if user:
        return user

    # Fallback: match per cognome (ultima parola)
    parts = name.split()
    if len(parts) >= 2:
        last_name = parts[-1]
        user = User.query.filter(
            func.lower(User.last_name) == last_name.lower()
        ).first()
        if user:
            return user

    return None


def _serialize_lead(lead, parsed_pkg=None):
    """Serializza un SalesLead per il frontend."""
    if parsed_pkg is None:
        parsed_pkg = parse_package_name(lead.custom_package_name)

    hm = None
    if lead.health_manager:
        hm = {
            'id': lead.health_manager.id,
            'full_name': f"{lead.health_manager.first_name} {lead.health_manager.last_name}",
            'avatar_url': (
                lead.health_manager.avatar_path.replace('avatars/', '/uploads/avatars/', 1)
                if lead.health_manager.avatar_path and lead.health_manager.avatar_path.startswith('avatars/')
                else '/static/assets/immagini/logo_user.png'
            ),
        }

    # Check status
    checks = {}
    for idx in (1, 2, 3):
        completed_at = getattr(lead, f'check{idx}_completed_at', None)
        responses = getattr(lead, f'check{idx}_responses', None)
        form_url = None

        # form_url salvato in form_responses sotto chiave check{idx}_form_url
        if lead.form_responses and isinstance(lead.form_responses, dict):
            form_url = lead.form_responses.get(f'check{idx}_form_url')

        check_data = {
            'completed': completed_at is not None or (responses is not None and len(responses) > 0),
            'completed_at': completed_at.isoformat() if completed_at else None,
            'has_responses': responses is not None and len(responses) > 0 if responses else False,
            'form_url': form_url,
        }

        if idx == 3:
            check_data['score'] = lead.check3_score
            check_data['type'] = lead.check3_type

        checks[f'check_{idx}'] = check_data

    # Assignment flags
    assignments = {
        'nutritionist_id': lead.assigned_nutritionist_id,
        'coach_id': lead.assigned_coach_id,
        'psychologist_id': lead.assigned_psychologist_id,
    }

    return {
        'id': lead.id,
        'unique_code': lead.unique_code,
        'full_name': lead.full_name,
        'email': lead.email,
        'phone': lead.phone,
        'client_story': lead.client_story,
        'package_name': lead.custom_package_name,
        'package_code': parsed_pkg.get('code', ''),
        'package_roles': parsed_pkg.get('roles', {}),
        'duration_days': parsed_pkg.get('duration_days', 0),
        'health_manager': hm,
        'health_manager_name': lead.form_responses.get('health_manager_name', '') if lead.form_responses else '',
        'onboarding_date': lead.onboarding_date.isoformat() if lead.onboarding_date else None,
        'onboarding_time': lead.onboarding_time.strftime('%H:%M') if lead.onboarding_time else None,
        'onboarding_notes': lead.onboarding_notes,
        'loom_link': lead.loom_link,
        'checks': checks,
        'assignments': assignments,
        'ai_analysis': lead.ai_analysis,
        'converted': lead.converted_to_client_id is not None,
        'received_at': lead.created_at.isoformat() if lead.created_at else None,
    }


# =============================================================================
# WEBHOOK ENDPOINT (CSRF-exempt, public)
# =============================================================================

@bp.route("/webhook", methods=["POST"])
@csrf.exempt
def webhook_receiver():
    """
    Riceve webhook dalla vecchia suite CRM.
    Gestisce: lead.pending_assignment e lead.check_completed
    """
    # Validazione header
    source = request.headers.get('X-Webhook-Source', '')
    if source != 'corposostenibile-suite':
        logger.warning(f"Webhook ricevuto con source non valido: {source}")
        return jsonify({'success': False, 'message': 'Invalid source'}), 400

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'success': False, 'message': 'No JSON payload'}), 400

    event = data.get('event')

    if event == 'lead.pending_assignment':
        return _handle_pending_assignment(data)
    elif event == 'lead.check_completed':
        return _handle_check_completed(data)
    else:
        logger.warning(f"Evento webhook sconosciuto: {event}")
        return jsonify({'success': False, 'message': f'Unknown event: {event}'}), 400


def _handle_pending_assignment(data):
    """Gestisce l'evento lead.pending_assignment: crea/aggiorna SalesLead."""
    lead_data = data.get('lead', {})
    old_suite_id = lead_data.get('id')
    unique_code = lead_data.get('unique_code')

    if not old_suite_id:
        return jsonify({'success': False, 'message': 'Missing lead.id'}), 400

    try:
        # Upsert: cerca per old_suite_id
        lead = SalesLead.query.filter_by(
            source_system='old_suite',
            old_suite_id=old_suite_id
        ).first()

        if not lead:
            lead = SalesLead(
                source_system='old_suite',
                old_suite_id=old_suite_id,
                first_name=lead_data.get('first_name', ''),
                last_name=lead_data.get('last_name', ''),
                email=lead_data.get('email', ''),
            )
            db.session.add(lead)

        # Dati anagrafici
        lead.first_name = lead_data.get('first_name', lead.first_name)
        lead.last_name = lead_data.get('last_name', lead.last_name)
        lead.email = lead_data.get('email', lead.email)
        lead.phone = lead_data.get('phone', lead.phone)
        lead.unique_code = unique_code or lead.unique_code
        lead.gender = lead_data.get('gender', lead.gender)
        lead.professione = lead_data.get('professione', lead.professione)
        lead.fiscal_code = lead_data.get('fiscal_code', lead.fiscal_code)
        lead.indirizzo = lead_data.get('indirizzo', lead.indirizzo)
        lead.paese = lead_data.get('paese', lead.paese)
        lead.origin = lead_data.get('origin', lead.origin)

        if lead_data.get('birth_date'):
            try:
                lead.birth_date = datetime.strptime(lead_data['birth_date'], '%Y-%m-%d').date()
            except (ValueError, TypeError):
                pass

        # Storia e note
        lead.client_story = lead_data.get('client_story', lead.client_story)
        lead.sales_notes = lead_data.get('sales_notes', lead.sales_notes)
        lead.admin_notes = lead_data.get('admin_notes', lead.admin_notes)

        # Pacchetto
        package_info = lead_data.get('package', {})
        if package_info:
            lead.custom_package_name = package_info.get('name', lead.custom_package_name)
        if lead_data.get('custom_package_name'):
            lead.custom_package_name = lead_data['custom_package_name']

        # Importi
        lead.total_amount = lead_data.get('total_amount', lead.total_amount)
        lead.discount_amount = lead_data.get('discount_amount', lead.discount_amount)
        lead.final_amount = lead_data.get('final_amount', lead.final_amount)
        lead.paid_amount = lead_data.get('paid_amount', lead.paid_amount)

        # Finance
        lead.finance_approved = lead_data.get('finance_approved', lead.finance_approved)
        if lead_data.get('finance_approved_at'):
            try:
                lead.finance_approved_at = datetime.fromisoformat(lead_data['finance_approved_at'])
            except (ValueError, TypeError):
                pass
        lead.finance_notes = lead_data.get('finance_notes', lead.finance_notes)
        lead.payment_verified = lead_data.get('payment_verified', lead.payment_verified)

        # Health Manager (match per nome)
        hm_data = lead_data.get('health_manager', {})
        if hm_data and hm_data.get('name'):
            hm_user = _resolve_user_by_name(hm_data['name'])
            if hm_user:
                lead.health_manager_id = hm_user.id
            # Salva il nome originale per fallback display
            if not lead.form_responses:
                lead.form_responses = {}
            lead.form_responses['health_manager_name'] = hm_data.get('name', '')
            lead.form_responses['health_manager_email_old'] = hm_data.get('email', '')

        # Sales User (match per nome)
        sales_data = lead_data.get('sales_user', {})
        if sales_data and sales_data.get('name'):
            sales_user = _resolve_user_by_name(sales_data['name'])
            if sales_user:
                lead.sales_user_id = sales_user.id

        # Onboarding
        if lead_data.get('onboarding_date'):
            try:
                lead.onboarding_date = datetime.strptime(lead_data['onboarding_date'], '%Y-%m-%d').date()
            except (ValueError, TypeError):
                pass
        if lead_data.get('onboarding_time'):
            try:
                from datetime import time as dt_time
                parts = lead_data['onboarding_time'].split(':')
                lead.onboarding_time = dt_time(int(parts[0]), int(parts[1]))
            except (ValueError, TypeError, IndexError):
                pass

        # Tracking
        lead.source_campaign = lead_data.get('source_campaign', lead.source_campaign)
        lead.source_medium = lead_data.get('source_medium', lead.source_medium)
        lead.utm_source = lead_data.get('utm_source', lead.utm_source)
        lead.utm_medium = lead_data.get('utm_medium', lead.utm_medium)
        lead.utm_campaign = lead_data.get('utm_campaign', lead.utm_campaign)

        # Tags e priorità
        if lead_data.get('tags'):
            lead.tags = lead_data['tags']
        if lead_data.get('priority'):
            lead.priority = lead_data['priority']

        # Checks
        checks_data = lead_data.get('checks', {})
        _update_checks_from_payload(lead, checks_data)

        # Form responses extra
        if lead_data.get('form_responses'):
            if not lead.form_responses:
                lead.form_responses = {}
            lead.form_responses.update(lead_data['form_responses'])

        # Status
        lead.status = 'PENDING_ASSIGNMENT'

        db.session.commit()

        logger.info(f"[Old Suite] Lead {lead.id} (old_suite_id={old_suite_id}) salvata: {lead.full_name}")

        return jsonify({
            'success': True,
            'lead_id': lead.id,
            'message': 'Lead salvata con successo'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"[Old Suite] Errore salvataggio lead: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


def _handle_check_completed(data):
    """Gestisce l'evento lead.check_completed: aggiorna check di un lead esistente."""
    old_suite_id = data.get('lead_id')
    unique_code = data.get('unique_code')
    check_number = data.get('check_number')
    completed_at = data.get('completed_at')
    responses = data.get('responses')

    if not check_number or check_number not in (1, 2, 3):
        return jsonify({'success': False, 'message': 'Invalid check_number'}), 400

    try:
        # Cerca lead per old_suite_id o unique_code
        lead = None
        if old_suite_id:
            lead = SalesLead.query.filter_by(
                source_system='old_suite',
                old_suite_id=old_suite_id
            ).first()
        if not lead and unique_code:
            lead = SalesLead.query.filter_by(
                source_system='old_suite',
                unique_code=unique_code
            ).first()

        if not lead:
            return jsonify({'success': False, 'message': 'Lead non trovata'}), 404

        # Aggiorna check
        setattr(lead, f'check{check_number}_responses', responses)
        if completed_at:
            try:
                setattr(lead, f'check{check_number}_completed_at',
                        datetime.fromisoformat(completed_at))
            except (ValueError, TypeError):
                setattr(lead, f'check{check_number}_completed_at', datetime.utcnow())

        # Campi extra per check 3
        if check_number == 3:
            if data.get('check3_score') is not None:
                lead.check3_score = data['check3_score']
            if data.get('check3_type') is not None:
                lead.check3_type = data['check3_type']

        db.session.commit()

        logger.info(f"[Old Suite] Check {check_number} completato per lead {lead.id}")

        return jsonify({
            'success': True,
            'lead_id': lead.id,
            'check_number': check_number,
            'message': f'Check {check_number} aggiornato'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"[Old Suite] Errore aggiornamento check: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


def _update_checks_from_payload(lead, checks_data):
    """Aggiorna i campi check del SalesLead dal payload webhook."""
    for idx in (1, 2, 3):
        check_key = f'check{idx}'
        check = checks_data.get(check_key, {})
        if not check:
            continue

        if check.get('completed') and check.get('responses'):
            setattr(lead, f'check{idx}_responses', check['responses'])
            if check.get('completed_at'):
                try:
                    setattr(lead, f'check{idx}_completed_at',
                            datetime.fromisoformat(check['completed_at']))
                except (ValueError, TypeError):
                    pass

        # Salva form_url se presente (per check non compilati)
        if check.get('form_url'):
            if not lead.form_responses:
                lead.form_responses = {}
            lead.form_responses[f'check{idx}_form_url'] = check['form_url']

        # Check 3 extra fields
        if idx == 3:
            if check.get('score') is not None:
                lead.check3_score = check['score']
            if check.get('type') is not None:
                lead.check3_type = check['type']


# =============================================================================
# API ENDPOINTS (login_required)
# =============================================================================

@bp.route("/api/leads", methods=["GET"])
@login_required
def api_get_leads():
    """Lista lead dalla vecchia suite, non ancora convertite."""
    try:
        leads = (
            SalesLead.query
            .filter_by(source_system='old_suite')
            .filter(SalesLead.converted_to_client_id.is_(None))
            .order_by(SalesLead.created_at.desc())
            .all()
        )

        result = []
        for lead in leads:
            parsed = parse_package_name(lead.custom_package_name)
            result.append(_serialize_lead(lead, parsed))

        return jsonify({'success': True, 'data': result, 'total': len(result)})

    except Exception as e:
        logger.error(f"[Old Suite] Errore lista leads: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route("/api/leads/<int:lead_id>", methods=["GET"])
@login_required
def api_get_lead(lead_id):
    """Dettaglio singola lead."""
    lead = SalesLead.query.filter_by(id=lead_id, source_system='old_suite').first()
    if not lead:
        return jsonify({'success': False, 'message': 'Lead non trovata'}), 404

    parsed = parse_package_name(lead.custom_package_name)
    return jsonify({'success': True, 'data': _serialize_lead(lead, parsed)})


@bp.route("/api/leads/<int:lead_id>/check/<int:check_number>", methods=["GET"])
@login_required
def api_get_check_detail(lead_id, check_number):
    """Dettaglio risposte di un check specifico."""
    if check_number not in (1, 2, 3):
        return jsonify({'success': False, 'message': 'Check number non valido'}), 400

    lead = SalesLead.query.filter_by(id=lead_id, source_system='old_suite').first()
    if not lead:
        return jsonify({'success': False, 'message': 'Lead non trovata'}), 404

    responses = getattr(lead, f'check{check_number}_responses', None) or {}
    completed_at = getattr(lead, f'check{check_number}_completed_at', None)

    check_names = {1: 'Check 1 - Nutrizione & Sport', 2: 'Check 2 - Stile di Vita', 3: 'Check 3 - Psicologico'}

    data = {
        'lead_id': lead.id,
        'lead_name': lead.full_name,
        'check_number': check_number,
        'form_name': check_names.get(check_number, f'Check {check_number}'),
        'completed_at': completed_at.isoformat() if completed_at else None,
        'responses': [
            {'label': k, 'value': v}
            for k, v in responses.items()
        ] if isinstance(responses, dict) else [],
    }

    if check_number == 3:
        data['score'] = lead.check3_score
        data['type'] = lead.check3_type

    return jsonify({'success': True, 'data': data})


@bp.route("/api/leads/<int:lead_id>/story", methods=["PATCH"])
@login_required
def api_update_lead_story(lead_id):
    """Aggiornamento manuale della storia del cliente su una lead."""
    lead = SalesLead.query.filter_by(id=lead_id, source_system='old_suite').first()
    if not lead:
        return jsonify({'success': False, 'message': 'Lead non trovata'}), 404
    data = request.get_json() or {}
    story = data.get('client_story', '').strip()
    if not story:
        return jsonify({'success': False, 'message': 'Storia vuota'}), 400
    lead.client_story = story
    db.session.commit()
    return jsonify({'success': True, 'client_story': lead.client_story})


@bp.route("/api/confirm-assignment", methods=["POST"])
@login_required
def api_confirm_assignment():
    """
    Conferma assegnazione professionista per una lead dalla vecchia suite.
    Salva l'assegnazione sulla SalesLead. Crea il Cliente SOLO quando tutti
    i ruoli richiesti dal pacchetto sono stati assegnati.
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Dati mancanti'}), 400

    lead_id = data.get('lead_id')
    if not lead_id:
        return jsonify({'success': False, 'message': 'lead_id mancante'}), 400

    try:
        lead = SalesLead.query.filter_by(id=lead_id, source_system='old_suite').first()
        if not lead:
            return jsonify({'success': False, 'message': 'Lead non trovata'}), 404

        nutritionist_id = data.get('nutritionist_id')
        coach_id = data.get('coach_id')
        psychologist_id = data.get('psychologist_id')

        if not nutritionist_id and not coach_id and not psychologist_id:
            return jsonify({'success': False, 'message': 'Nessun professionista selezionato'}), 400

        # 1. Aggiorna assegnazioni sulla lead (accumula ruolo per ruolo)
        if nutritionist_id:
            lead.assigned_nutritionist_id = int(nutritionist_id)
        if coach_id:
            lead.assigned_coach_id = int(coach_id)
        if psychologist_id:
            lead.assigned_psychologist_id = int(psychologist_id)
        lead.assigned_by = current_user.id
        lead.assigned_at = datetime.utcnow()
        if data.get('notes'):
            lead.assignment_notes = data['notes']
        if data.get('onboarding_notes'):
            lead.onboarding_notes = data['onboarding_notes']
        if data.get('loom_link'):
            lead.loom_link = data['loom_link']

        # Salva AI analysis
        if data.get('ai_analysis'):
            if not lead.ai_analysis:
                lead.ai_analysis = {}
            # Merge: non sovrascrivere analisi di altri ruoli
            if isinstance(data['ai_analysis'], dict):
                current_ai = dict(lead.ai_analysis) if lead.ai_analysis else {}
                current_ai.update(data['ai_analysis'])
                lead.ai_analysis = current_ai
            else:
                lead.ai_analysis = data['ai_analysis']
            lead.ai_analyzed_at = datetime.utcnow()

        # 2. Verifica se TUTTI i ruoli richiesti dal pacchetto sono assegnati
        parsed_pkg = parse_package_name(lead.custom_package_name)
        roles = parsed_pkg.get('roles', {})

        all_assigned = True
        if roles.get('nutrition') and not lead.assigned_nutritionist_id:
            all_assigned = False
        if roles.get('coach') and not lead.assigned_coach_id:
            all_assigned = False
        if roles.get('psychology') and not lead.assigned_psychologist_id:
            all_assigned = False

        assigned_count = sum([
            1 for r, needed in [('nutrition', roles.get('nutrition')), ('coach', roles.get('coach')), ('psychology', roles.get('psychology'))]
            if needed and getattr(lead, f'assigned_{"nutritionist" if r == "nutrition" else ("coach" if r == "coach" else "psychologist")}_id')
        ])
        required_count = sum(1 for v in roles.values() if v)

        if not all_assigned:
            # Salva solo l'assegnazione parziale sulla lead
            db.session.commit()

            logger.info(
                f"[Old Suite] Assegnazione parziale: lead {lead.id} ({assigned_count}/{required_count} ruoli)"
            )

            return jsonify({
                'success': True,
                'message': f'Professionista assegnato ({assigned_count}/{required_count}). Completa gli altri ruoli per creare il paziente.',
                'all_assigned': False,
                'assigned_count': assigned_count,
                'required_count': required_count,
            })

        # 3. Tutti i ruoli assegnati → Crea Cliente
        cliente = None
        if lead.converted_to_client_id:
            cliente = Cliente.query.get(lead.converted_to_client_id)

        if not cliente:
            cliente = Cliente.query.filter_by(mail=lead.email).first() if lead.email else None

        if not cliente:
            # Deriva tipologia supporto dal pacchetto
            support = parsed_pkg.get('support_types', {})
            parsed_tipologia = parsed_pkg.get('client_type')
            tipologia_enum = None
            if parsed_tipologia in {'a', 'b', 'c'}:
                tipologia_enum = TipologiaClienteEnum(parsed_tipologia)

            cliente = Cliente(
                nome_cognome=lead.full_name,
                mail=lead.email,
                numero_telefono=lead.phone,
                data_di_nascita=lead.birth_date,
                genere=lead.gender,
                professione=lead.professione,
                indirizzo=lead.indirizzo,
                paese=lead.paese,
                storia_cliente=lead.client_story,
                programma_attuale=lead.custom_package_name,
                durata_programma_giorni=parsed_pkg.get('duration_days') or None,
                tipologia_cliente=tipologia_enum,
                tipologia_supporto_nutrizione=support.get('nutrizione'),
                tipologia_supporto_coach=support.get('coach'),
                note_criticita_iniziali=lead.onboarding_notes,
                loom_link=lead.loom_link,
                health_manager_id=lead.health_manager_id,
                consulente_alimentare_id=lead.sales_user_id,
                data_inizio_abbonamento=lead.onboarding_date,
                tipo_iniziale=lead.check3_type,
                tipo_attuale=lead.check3_type,
                acquisition_source='old_suite_webhook',
                acquisition_channel=lead.origin,
                acquisition_campaign=lead.source_campaign,
                acquisition_date=lead.created_at,
                service_status='pending_assignment',
                show_in_clienti_lista=False,
                created_at=datetime.utcnow(),
            )
            db.session.add(cliente)
            db.session.flush()

            lead.converted_to_client_id = cliente.cliente_id
            lead.converted_at = datetime.utcnow()
            lead.converted_by = current_user.id

        # 4. Crea/aggiorna ServiceClienteAssignment
        assignment = ServiceClienteAssignment.query.filter_by(
            cliente_id=cliente.cliente_id
        ).first()

        if not assignment:
            assignment = ServiceClienteAssignment(
                cliente_id=cliente.cliente_id,
                status='pending_assignment',
                created_at=datetime.utcnow(),
            )
            db.session.add(assignment)
            db.session.flush()

        # 5. Assegna TUTTI i professionisti al Cliente
        motivazione = "Assegnazione da pannello Old Suite (temporaneo)"
        data_inizio = datetime.utcnow().date()

        if lead.assigned_nutritionist_id:
            assignment.nutrizionista_assigned_id = lead.assigned_nutritionist_id
            assignment.nutrizionista_assigned_at = datetime.utcnow()
            assignment.nutrizionista_assigned_by = current_user.id

            h = ClienteProfessionistaHistory(
                cliente_id=cliente.cliente_id,
                user_id=lead.assigned_nutritionist_id,
                tipo_professionista='nutrizionista',
                data_dal=data_inizio,
                motivazione_aggiunta=motivazione,
                assegnato_da_id=current_user.id,
                is_active=True,
            )
            db.session.add(h)

            nutri = User.query.get(lead.assigned_nutritionist_id)
            if nutri and nutri not in cliente.nutrizionisti_multipli:
                cliente.nutrizionisti_multipli.append(nutri)
            # Aggiorna FK legacy per backward compatibility
            if not cliente.nutrizionista_id:
                cliente.nutrizionista_id = lead.assigned_nutritionist_id

        if lead.assigned_coach_id:
            assignment.coach_assigned_id = lead.assigned_coach_id
            assignment.coach_assigned_at = datetime.utcnow()
            assignment.coach_assigned_by = current_user.id

            h = ClienteProfessionistaHistory(
                cliente_id=cliente.cliente_id,
                user_id=lead.assigned_coach_id,
                tipo_professionista='coach',
                data_dal=data_inizio,
                motivazione_aggiunta=motivazione,
                assegnato_da_id=current_user.id,
                is_active=True,
            )
            db.session.add(h)

            coach = User.query.get(lead.assigned_coach_id)
            if coach and coach not in cliente.coaches_multipli:
                cliente.coaches_multipli.append(coach)
            # Aggiorna FK legacy per backward compatibility
            if not cliente.coach_id:
                cliente.coach_id = lead.assigned_coach_id

        if lead.assigned_psychologist_id:
            assignment.psicologa_assigned_id = lead.assigned_psychologist_id
            assignment.psicologa_assigned_at = datetime.utcnow()
            assignment.psicologa_assigned_by = current_user.id

            h = ClienteProfessionistaHistory(
                cliente_id=cliente.cliente_id,
                user_id=lead.assigned_psychologist_id,
                tipo_professionista='psicologa',
                data_dal=data_inizio,
                motivazione_aggiunta=motivazione,
                assegnato_da_id=current_user.id,
                is_active=True,
            )
            db.session.add(h)

            psico = User.query.get(lead.assigned_psychologist_id)
            if psico and psico not in cliente.psicologi_multipli:
                cliente.psicologi_multipli.append(psico)
            # Aggiorna FK legacy per backward compatibility
            if not cliente.psicologa_id:
                cliente.psicologa_id = lead.assigned_psychologist_id

        # Update status
        assignment.update_status()

        # Note
        if data.get('notes'):
            note = ServiceClienteNote(
                assignment_id=assignment.id,
                cliente_id=cliente.cliente_id,
                note_text=data['notes'],
                note_type='assignment',
                created_by=current_user.id,
            )
            db.session.add(note)

        # Aggiorna cliente status
        cliente.service_status = 'assigned'
        cliente.show_in_clienti_lista = True

        db.session.commit()

        logger.info(
            f"[Old Suite] Assegnazione completata: lead {lead.id} → cliente {cliente.cliente_id} ({required_count}/{required_count} ruoli)"
        )

        return jsonify({
            'success': True,
            'message': 'Tutti i professionisti assegnati! Paziente creato con successo.',
            'all_assigned': True,
            'assigned_count': required_count,
            'required_count': required_count,
            'cliente_id': cliente.cliente_id,
            'status': assignment.status,
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"[Old Suite] Errore conferma assegnazione: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
