"""
Service Clienti Dashboard for Professional Assignments
========================================================
Dashboard per il servizio clienti per gestire assegnazioni professionisti
"""

from flask import request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, func

from . import customers_bp as bp
from corposostenibile.extensions import db
from corposostenibile.models import (
    Cliente,
    ServiceClienteAssignment,
    ServiceClienteNote,
    GHLOpportunity,
    User,
    ProfessionistCapacity
)

def _frontend_only(*_args, **_kwargs):
    return jsonify({
        "error": "Backend template route disabled",
        "message": "Use frontend app (corposostenibile-clinica)"
    }), 410


@bp.route('/service-dashboard')
@login_required
def service_dashboard():
    """Dashboard principale servizio clienti per assegnazioni"""

    # Filtri
    search_query = request.args.get('search', '')
    status_filter = request.args.get('status', 'assigning')
    checkup_filter = request.args.get('checkup', 'all')
    urgency_filter = request.args.get('urgency', 'all')

    # Query base: clienti pronti per assegnazione
    query = ServiceClienteAssignment.query.join(
        Cliente, ServiceClienteAssignment.cliente_id == Cliente.cliente_id
    ).outerjoin(
        GHLOpportunity, ServiceClienteAssignment.ghl_opportunity_id == GHLOpportunity.id
    )

    # Applica filtri status
    if status_filter == 'assigning':
        query = query.filter(ServiceClienteAssignment.status.in_(['assigning', 'pending_assignment']))
    elif status_filter == 'fully_assigned':
        query = query.filter(ServiceClienteAssignment.status == 'fully_assigned')
    elif status_filter == 'active':
        query = query.filter(ServiceClienteAssignment.status == 'active')
    else:
        # Mostra tutti i clienti post-finance
        query = query.filter(
            ServiceClienteAssignment.status.in_(['assigning', 'fully_assigned', 'active', 'pending_assignment'])
        )

    # Filtro checkup
    if checkup_filter == 'done':
        query = query.filter(ServiceClienteAssignment.checkup_iniziale_fatto == True)
    elif checkup_filter == 'pending':
        query = query.filter(
            or_(
                ServiceClienteAssignment.checkup_iniziale_fatto == False,
                ServiceClienteAssignment.checkup_iniziale_fatto.is_(None)
            )
        )

    # Filtro urgenza
    if urgency_filter == 'urgent':
        query = query.filter(ServiceClienteAssignment.urgent_flag == True)
    elif urgency_filter == 'normal':
        query = query.filter(
            or_(
                ServiceClienteAssignment.urgent_flag == False,
                ServiceClienteAssignment.urgent_flag.is_(None)
            )
        )

    # Ricerca per nome/email
    if search_query:
        search_pattern = f"%{search_query}%"
        query = query.filter(
            or_(
                Cliente.nome_cognome.ilike(search_pattern),
                Cliente.mail.ilike(search_pattern),
                Cliente.cellulare.ilike(search_pattern)
            )
        )

    # Ordina per priorità e data
    query = query.order_by(
        ServiceClienteAssignment.urgent_flag.desc(),
        ServiceClienteAssignment.priority_level.desc(),
        ServiceClienteAssignment.created_at.asc()  # FIFO per clienti normali
    )

    assignments = query.all()

    # Statistiche
    stats = {
        'da_assegnare': ServiceClienteAssignment.query.filter(
            ServiceClienteAssignment.status.in_(['assigning', 'pending_assignment'])
        ).count(),
        'checkup_pending': ServiceClienteAssignment.query.filter(
            ServiceClienteAssignment.status == 'assigning',
            or_(
                ServiceClienteAssignment.checkup_iniziale_fatto == False,
                ServiceClienteAssignment.checkup_iniziale_fatto.is_(None)
            )
        ).count(),
        'urgent': ServiceClienteAssignment.query.filter(
            ServiceClienteAssignment.status == 'assigning',
            ServiceClienteAssignment.urgent_flag == True
        ).count(),
        'assigned_today': ServiceClienteAssignment.query.filter(
            ServiceClienteAssignment.status == 'fully_assigned',
            ServiceClienteAssignment.updated_at >= datetime.now().replace(hour=0, minute=0, second=0)
        ).count()
    }

    # Carica professionisti disponibili per dropdown
    nutrizionisti = User.query.filter_by(role='nutrizionista', is_active=True).all()
    coaches = User.query.filter_by(role='coach', is_active=True).all()
    psicologhe = User.query.filter_by(role='psicologa', is_active=True).all()

    # Carica capacità per ogni professionista
    capacities = {}
    for prof in nutrizionisti + coaches + psicologhe:
        capacity = ProfessionistCapacity.query.filter_by(
            user_id=prof.id,
            role_type=prof.role
        ).first()
        if capacity:
            capacities[prof.id] = {
                'current': capacity.current_clients or 0,
                'max': capacity.max_clients,
                'available': capacity.is_available,
                'percentage': capacity.availability_percentage
            }

    return _frontend_only()


@bp.route('/service-dashboard/assign/<int:assignment_id>')
@login_required
def assign_professionals(assignment_id):
    """Pagina dettaglio per assegnazione professionisti"""

    assignment = ServiceClienteAssignment.query.get_or_404(assignment_id)
    cliente = assignment.cliente
    opportunity = assignment.ghl_opportunity

    # Carica note esistenti
    notes = ServiceClienteNote.query.filter_by(
        assignment_id=assignment_id
    ).order_by(ServiceClienteNote.created_at.desc()).all()

    # Carica professionisti con capacità
    nutrizionisti = _get_professionals_with_capacity('nutrizionista')
    coaches = _get_professionals_with_capacity('coach')
    psicologhe = _get_professionals_with_capacity('psicologa')

    # Determina quale pacchetto richiede quali professionisti
    package_requirements = _get_package_requirements(opportunity.pacchetto_comprato if opportunity else None)

    return _frontend_only()


@bp.route('/service-dashboard/assign/<int:assignment_id>/save', methods=['POST'])
@login_required
def save_assignment(assignment_id):
    """Salva assegnazione professionisti"""

    assignment = ServiceClienteAssignment.query.get_or_404(assignment_id)

    try:
        # Ottieni assegnazioni dal form
        nutrizionista_id = request.form.get('nutrizionista_id', type=int)
        coach_id = request.form.get('coach_id', type=int)
        psicologa_id = request.form.get('psicologa_id', type=int)

        changes_made = []

        # Inizializza assignment_history se non esiste
        if assignment.assignment_history is None:
            assignment.assignment_history = {'assignments': []}
        elif 'assignments' not in assignment.assignment_history:
            assignment.assignment_history['assignments'] = []

        now = datetime.utcnow()

        # Assegna nutrizionista
        if nutrizionista_id and nutrizionista_id != assignment.nutrizionista_assigned_id:
            old_nutrizionista = assignment.nutrizionista_assigned_id
            assignment.nutrizionista_assigned_id = nutrizionista_id
            assignment.nutrizionista_assigned_by = current_user.id
            assignment.nutrizionista_assigned_at = now

            # Aggiorna capacità
            _update_professional_capacity(nutrizionista_id, 'nutrizionista', 1)
            if old_nutrizionista:
                _update_professional_capacity(old_nutrizionista, 'nutrizionista', -1)

            nutrizionista = User.query.get(nutrizionista_id)
            changes_made.append(f"Nutrizionista: {nutrizionista.nome_cognome}")

            # Aggiungi entry alla timeline
            assignment.assignment_history['assignments'].append({
                'type': 'nutrizionista',
                'professional_id': nutrizionista_id,
                'professional_name': nutrizionista.nome_cognome,
                'assigned_at': now.isoformat(),
                'assigned_by': current_user.id,
                'assigned_by_name': current_user.nome_cognome,
                'action': 'reassigned' if old_nutrizionista else 'assigned',
                'previous_professional_id': old_nutrizionista
            })

        # Assegna coach
        if coach_id and coach_id != assignment.coach_assigned_id:
            old_coach = assignment.coach_assigned_id
            assignment.coach_assigned_id = coach_id
            assignment.coach_assigned_by = current_user.id
            assignment.coach_assigned_at = now

            # Aggiorna capacità
            _update_professional_capacity(coach_id, 'coach', 1)
            if old_coach:
                _update_professional_capacity(old_coach, 'coach', -1)

            coach = User.query.get(coach_id)
            changes_made.append(f"Coach: {coach.nome_cognome}")

            # Aggiungi entry alla timeline
            assignment.assignment_history['assignments'].append({
                'type': 'coach',
                'professional_id': coach_id,
                'professional_name': coach.nome_cognome,
                'assigned_at': now.isoformat(),
                'assigned_by': current_user.id,
                'assigned_by_name': current_user.nome_cognome,
                'action': 'reassigned' if old_coach else 'assigned',
                'previous_professional_id': old_coach
            })

        # Assegna psicologa
        if psicologa_id and psicologa_id != assignment.psicologa_assigned_id:
            old_psicologa = assignment.psicologa_assigned_id
            assignment.psicologa_assigned_id = psicologa_id
            assignment.psicologa_assigned_by = current_user.id
            assignment.psicologa_assigned_at = now

            # Aggiorna capacità
            _update_professional_capacity(psicologa_id, 'psicologa', 1)
            if old_psicologa:
                _update_professional_capacity(old_psicologa, 'psicologa', -1)

            psicologa = User.query.get(psicologa_id)
            changes_made.append(f"Psicologa: {psicologa.nome_cognome}")

            # Aggiungi entry alla timeline
            assignment.assignment_history['assignments'].append({
                'type': 'psicologa',
                'professional_id': psicologa_id,
                'professional_name': psicologa.nome_cognome,
                'assigned_at': now.isoformat(),
                'assigned_by': current_user.id,
                'assigned_by_name': current_user.nome_cognome,
                'action': 'reassigned' if old_psicologa else 'assigned',
                'previous_professional_id': old_psicologa
            })

        # Flag modified per JSONB (importante per SQLAlchemy)
        if changes_made:
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(assignment, 'assignment_history')

        # Verifica se tutte le assegnazioni richieste sono complete
        if _check_all_assigned(assignment):
            assignment.status = 'fully_assigned'

            # Aggiorna anche il cliente
            cliente = assignment.cliente
            cliente.service_status = 'fully_assigned'
            cliente.show_in_clienti_lista = True

            # Assegna anche nella tabella clienti (per retrocompatibilità)
            if nutrizionista_id:
                cliente.nutrizionista_id = nutrizionista_id
            if coach_id:
                cliente.coach_id = coach_id
            if psicologa_id:
                cliente.psicologa_id = psicologa_id

        # Crea nota con i cambiamenti
        if changes_made:
            note = ServiceClienteNote(
                assignment_id=assignment_id,
                cliente_id=assignment.cliente_id,
                note_text=f"Professionisti assegnati: {', '.join(changes_made)}",
                note_type='assignment',
                created_by=current_user.id,
                visible_to_professionals=True
            )
            db.session.add(note)

        # Aggiungi note personalizzata se fornita
        custom_note = request.form.get('assignment_note')
        if custom_note:
            note = ServiceClienteNote(
                assignment_id=assignment_id,
                cliente_id=assignment.cliente_id,
                note_text=custom_note,
                note_type='general',
                created_by=current_user.id,
                visible_to_professionals=True
            )
            db.session.add(note)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Professionisti assegnati con successo!',
            'assignment_id': assignment_id,
            'status': assignment.status
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f"Errore durante l'assegnazione: {str(e)}",
            'assignment_id': assignment_id
        }), 400


@bp.route('/service-dashboard/checkup/<int:assignment_id>', methods=['POST'])
@login_required
def update_checkup_status(assignment_id):
    """Aggiorna stato checkup iniziale"""

    assignment = ServiceClienteAssignment.query.get_or_404(assignment_id)

    checkup_done = request.form.get('checkup_done') == 'true'
    checkup_note = request.form.get('checkup_note', '')

    assignment.checkup_iniziale_fatto = checkup_done
    assignment.checkup_iniziale_data = datetime.utcnow() if checkup_done else None
    assignment.checkup_iniziale_note = checkup_note

    # Resetta alert se checkup fatto
    if checkup_done:
        assignment.checkup_alert_sent = False
        assignment.checkup_alert_count = 0

    # Crea nota
    note_text = f"CheckUp iniziale {'completato' if checkup_done else 'da fare'}"
    if checkup_note:
        note_text += f": {checkup_note}"

    note = ServiceClienteNote(
        assignment_id=assignment_id,
        cliente_id=assignment.cliente_id,
        note_text=note_text,
        note_type='checkup',
        created_by=current_user.id,
        visible_to_professionals=True
    )
    db.session.add(note)

    db.session.commit()

    return jsonify({
        'success': True,
        'checkup_done': checkup_done,
        'message': 'Stato checkup aggiornato'
    })


@bp.route('/service-dashboard/note/<int:assignment_id>', methods=['POST'])
@login_required
def add_service_note(assignment_id):
    """Aggiungi nota di servizio"""

    assignment = ServiceClienteAssignment.query.get_or_404(assignment_id)

    note_text = request.form.get('note_text', '').strip()
    note_type = request.form.get('note_type', 'general')

    if not note_text:
        return jsonify({'success': False, 'error': 'Nota vuota'}), 400

    note = ServiceClienteNote(
        assignment_id=assignment_id,
        cliente_id=assignment.cliente_id,
        note_text=note_text,
        note_type=note_type,
        created_by=current_user.id,
        visible_to_professionals=True,
        visible_to_client=False
    )
    db.session.add(note)
    db.session.commit()

    return jsonify({
        'success': True,
        'note_id': note.id,
        'created_at': note.created_at.strftime('%d/%m/%Y %H:%M'),
        'created_by': current_user.nome_cognome
    })


@bp.route('/service-dashboard/urgent/<int:assignment_id>', methods=['POST'])
@login_required
def toggle_urgent(assignment_id):
    """Toggle flag urgente"""

    assignment = ServiceClienteAssignment.query.get_or_404(assignment_id)

    urgent = request.form.get('urgent') == 'true'
    urgent_reason = request.form.get('urgent_reason', '')

    assignment.urgent_flag = urgent
    assignment.urgent_reason = urgent_reason if urgent else None

    # Aumenta priorità se urgente
    if urgent:
        assignment.priority_level = 10  # Max priority
    else:
        assignment.priority_level = 5  # Normal priority

    db.session.commit()

    return jsonify({
        'success': True,
        'urgent': urgent,
        'message': f"Cliente marcato come {'urgente' if urgent else 'normale'}"
    })


# Helper functions
def _get_professionals_with_capacity(role_type):
    """Ottieni professionisti con info capacità"""
    professionals = User.query.filter_by(role=role_type, is_active=True).all()

    result = []
    for prof in professionals:
        capacity = ProfessionistCapacity.query.filter_by(
            user_id=prof.id,
            role_type=role_type
        ).first()

        if not capacity:
            # Crea capacità default se non esiste
            capacity = ProfessionistCapacity(
                user_id=prof.id,
                role_type=role_type,
                max_clients=30,
                current_clients=0,
                is_available=True
            )
            db.session.add(capacity)
            db.session.commit()

        result.append({
            'user': prof,
            'capacity': capacity,
            'available_slots': capacity.max_clients - (capacity.current_clients or 0),
            'percentage': capacity.availability_percentage
        })

    # Ordina per disponibilità
    result.sort(key=lambda x: x['available_slots'], reverse=True)

    return result


def _get_package_requirements(package_name):
    """Determina quali professionisti sono richiesti per il pacchetto"""
    if not package_name:
        # Default: tutti e 3
        return {
            'nutrizionista': True,
            'coach': True,
            'psicologa': True
        }

    package_lower = package_name.lower()

    # Logica base sui nomi pacchetti comuni
    requirements = {
        'nutrizionista': True,  # Sempre incluso
        'coach': True,  # Quasi sempre incluso
        'psicologa': 'premium' in package_lower or 'vip' in package_lower or 'completo' in package_lower
    }

    return requirements


def _update_professional_capacity(user_id, role_type, delta):
    """Aggiorna capacità professionista"""
    capacity = ProfessionistCapacity.query.filter_by(
        user_id=user_id,
        role_type=role_type
    ).first()

    if capacity:
        capacity.current_clients = max(0, (capacity.current_clients or 0) + delta)
        capacity.updated_at = datetime.utcnow()

        # Aggiorna disponibilità
        if capacity.current_clients >= capacity.max_clients:
            capacity.is_available = False


def _check_all_assigned(assignment):
    """Verifica se tutti i professionisti richiesti sono assegnati"""
    opportunity = assignment.ghl_opportunity
    requirements = _get_package_requirements(
        opportunity.pacchetto_comprato if opportunity else None
    )

    all_assigned = True

    if requirements.get('nutrizionista') and not assignment.nutrizionista_assigned_id:
        all_assigned = False

    if requirements.get('coach') and not assignment.coach_assigned_id:
        all_assigned = False

    if requirements.get('psicologa') and not assignment.psicologa_assigned_id:
        all_assigned = False

    return all_assigned
