"""
blueprints/ticket/api_routes.py
===============================

API endpoints AJAX per operazioni sui ticket.
"""

from __future__ import annotations

from datetime import datetime
from http import HTTPStatus

from flask import jsonify, request
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_, func

from corposostenibile.extensions import db
from corposostenibile.models import (
    Cliente,
    Department,
    Ticket,
    TicketComment,
    TicketStatusEnum,
    TicketUrgencyEnum,
    TicketCategoryEnum,
    User,
)
from .timezone_utils import get_utc_now

from . import ticket_bp
from .permissions import (
    can_edit_ticket,
    can_view_ticket,
    get_user_accessible_tickets_query,
)
from .services import TicketService



# ────────────────────────────────────────────────────────────────────
#  API per ricerca clienti (autocomplete)
# ────────────────────────────────────────────────────────────────────

@ticket_bp.route("/api/search-clients")
@login_required
def search_clients():
    """Ricerca clienti per autocomplete."""

    query = request.args.get('q', '').strip()

    if len(query) < 2:
        return jsonify([])

    # Cerca clienti per nome
    clients = Cliente.query.filter(
        Cliente.nome_cognome.ilike(f'%{query}%')
    ).limit(10).all()

    results = []
    for client in clients:
        results.append({
            'id': client.cliente_id,
            'nome': client.nome_cognome,
            'programma': client.programma_attuale or client.storico_programma or 'N/D',
            'stato': client.stato_cliente.value if client.stato_cliente else 'N/D'
        })

    return jsonify(results)


@ticket_bp.route("/api/cliente/<int:cliente_id>/health-manager")
@login_required
def get_cliente_health_manager(cliente_id):
    """Ritorna l'health manager del cliente (se esiste)."""

    cliente = Cliente.query.get_or_404(cliente_id)

    if cliente.health_manager_id and cliente.health_manager_user:
        # Il cliente ha un health manager assegnato
        hm = cliente.health_manager_user
        return jsonify({
            'has_health_manager': True,
            'health_manager_id': hm.id,
            'health_manager_name': hm.full_name,
            'health_manager_email': hm.email
        })
    else:
        # Il cliente NON ha un health manager assegnato
        return jsonify({
            'has_health_manager': False,
            'health_manager_id': None,
            'health_manager_name': None,
            'health_manager_email': None
        })


@ticket_bp.route("/api/cliente/<int:cliente_id>/consulente-alimentare")
@login_required
def get_cliente_consulente_alimentare(cliente_id):
    """Ritorna il consulente alimentare del cliente (se esiste)."""

    cliente = Cliente.query.get_or_404(cliente_id)

    # Controlla prima i consulenti multipli (relazione many-to-many)
    if cliente.consulenti_multipli and len(cliente.consulenti_multipli) > 0:
        # Prendi il primo consulente alimentare dalla lista
        ca = cliente.consulenti_multipli[0]
        return jsonify({
            'has_consulente_alimentare': True,
            'consulente_alimentare_id': ca.id,
            'consulente_alimentare_name': ca.full_name,
            'consulente_alimentare_email': ca.email
        })
    elif cliente.consulente_alimentare_id and cliente.consulente_user:
        # Fallback: relazione singola (legacy)
        ca = cliente.consulente_user
        return jsonify({
            'has_consulente_alimentare': True,
            'consulente_alimentare_id': ca.id,
            'consulente_alimentare_name': ca.full_name,
            'consulente_alimentare_email': ca.email
        })
    else:
        # Il cliente NON ha un consulente alimentare assegnato
        return jsonify({
            'has_consulente_alimentare': False,
            'consulente_alimentare_id': None,
            'consulente_alimentare_name': None,
            'consulente_alimentare_email': None
        })


# ────────────────────────────────────────────────────────────────────
#  API per membri dipartimento
# ────────────────────────────────────────────────────────────────────

@ticket_bp.route("/api/department/<int:department_id>/members")
@login_required
def get_department_members(department_id):
    """Ritorna i membri di un dipartimento in formato JSON."""
    
    department = Department.query.get_or_404(department_id)
    
    # Controllo speciale per Consulenti Sales: unifica Consulenti Sales 1 e Consulenti Sales 2
    if department.name in ['Consulenti Sales 1', 'Consulenti Sales 2']:
        # Ottieni entrambi i dipartimenti Consulenti Sales
        sales_departments = Department.query.filter(
            Department.name.in_(['Consulenti Sales 1', 'Consulenti Sales 2'])
        ).all()
        
        # Raccogli tutti i membri di entrambi i dipartimenti
        members = []
        heads = []  # Lista separata per i responsabili
        
        for dept in sales_departments:
            dept_members = User.query.filter_by(
                department_id=dept.id,
                is_active=True
            ).order_by(User.first_name, User.last_name).all()
            
            for member in dept_members:
                if member.id == dept.head_id:
                    heads.append(member)  # Aggiungi alla lista dei responsabili
                else:
                    members.append(member)  # Aggiungi alla lista normale
        
        # Ordina: prima i responsabili, poi gli altri membri
        all_members = heads + members
        
    else:
        # Comportamento normale per gli altri dipartimenti
        members = User.query.filter_by(
            department_id=department_id,
            is_active=True
        ).order_by(User.first_name, User.last_name).all()
        
        # IMPORTANTE: Aggiungi anche l'HEAD del dipartimento se non è già membro
        # Questo permette agli HEAD di ricevere ticket anche se non sono membri diretti
        head = None
        if department.head_id:
            head = User.query.filter_by(
                id=department.head_id,
                is_active=True
            ).first()
        
        # Riordina mettendo il responsabile per primo
        other_members = []
        head_found_in_members = False
        
        for member in members:
            if head and member.id == head.id:
                head_found_in_members = True
            else:
                other_members.append(member)
        
        # Costruisci la lista con il responsabile per primo
        all_members = []
        if head:
            all_members.append(head)  # Aggiungi sempre l'head se esiste
        
        # Aggiungi gli altri membri (evitando duplicati se l'head era già nei membri)
        all_members.extend(other_members)
    
    # Formatta per JSON
    members_data = []
    for member in all_members:
        # Genera URL avatar
        avatar_url = None
        if member.avatar_path:
            avatar_url = member.avatar_url
        
        members_data.append({
            'id': member.id,
            'name': member.full_name,
            'email': member.email,
            'is_head': False,  # Non mostriamo più l'indicazione di responsabile
            'avatar_url': avatar_url
        })
    
    return jsonify({
        'department_id': department_id,
        'department_name': 'Sales Team' if department.name in ['Consulenti Sales 1', 'Consulenti Sales 2'] else department.name,
        'members': members_data
    })


# ────────────────────────────────────────────────────────────────────
#  Helper per applicare filtri
# ────────────────────────────────────────────────────────────────────

def apply_dashboard_filters(query, request_args, user):
    """
    Applica i filtri della dashboard alla query.
    
    Args:
        query: Query base
        request_args: request.args
        user: Utente corrente
        
    Returns:
        Query filtrata
    """
    # Filtro stato
    status_filter = request_args.get('status', '').strip()
    if status_filter:
        try:
            query = query.filter(Ticket.status == TicketStatusEnum(status_filter))
        except ValueError:
            pass
    
    # Filtro urgenza
    urgency_filter = request_args.get('urgency', '').strip()
    if urgency_filter:
        try:
            query = query.filter(Ticket.urgency == TicketUrgencyEnum(urgency_filter))
        except ValueError:
            pass

    # Filtro categoria (solo per admin e dept 13)
    category_filter = request_args.get('category', '').strip()
    if category_filter:
        try:
            query = query.filter(Ticket.category == TicketCategoryEnum(category_filter))
        except ValueError:
            pass

    # Filtro ricerca
    search_term = request_args.get('search', '').strip()
    if search_term:
        search_pattern = f"%{search_term}%"
        query = query.filter(
            or_(
                Ticket.ticket_number.ilike(search_pattern),
                Ticket.title.ilike(search_pattern),
                Ticket.requester_email.ilike(search_pattern),
                Ticket.requester_first_name.ilike(search_pattern),
                Ticket.requester_last_name.ilike(search_pattern),
                Ticket.description.ilike(search_pattern),
                Ticket.related_client_name.ilike(search_pattern),
                # Ricerca negli utenti assegnati (nome e cognome separatamente)
                Ticket.assigned_users.any(User.first_name.ilike(search_pattern)),
                Ticket.assigned_users.any(User.last_name.ilike(search_pattern)),
                # Ricerca negli utenti assegnati (nome completo concatenato)
                Ticket.assigned_users.any(
                    func.concat(User.first_name, ' ', User.last_name).ilike(search_pattern)
                ),
                # Ricerca negli utenti assegnati (cognome nome)
                Ticket.assigned_users.any(
                    func.concat(User.last_name, ' ', User.first_name).ilike(search_pattern)
                )
            )
        )
    
    # Filtro dipartimento (solo per admin)
    if user.is_admin:
        dept_id = request_args.get('department_id', type=int)
        if dept_id:
            query = query.filter(
                or_(
                    Ticket.department_id == dept_id,
                    Ticket.shared_departments.any(Department.id == dept_id)
                )
            )
    
    # Filtro date
    date_from = request_args.get('date_from', '').strip()
    if date_from:
        try:
            date_from_parsed = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Ticket.created_at >= date_from_parsed)
        except ValueError:
            pass
    
    date_to = request_args.get('date_to', '').strip()
    if date_to:
        try:
            date_to_parsed = datetime.strptime(date_to, '%Y-%m-%d')
            date_to_parsed = date_to_parsed.replace(hour=23, minute=59, second=59)
            query = query.filter(Ticket.created_at <= date_to_parsed)
        except ValueError:
            pass
    
    # Includi/escludi chiusi
    include_closed_value = request_args.get('include_closed', '').lower()
    include_closed = include_closed_value in ['on', 'y', 'yes', 'true', '1']
    if not include_closed:
        query = query.filter(Ticket.status != TicketStatusEnum.chiuso)
    
    return query


# ────────────────────────────────────────────────────────────────────
#  Status Update AJAX
# ────────────────────────────────────────────────────────────────────

@ticket_bp.route("/api/<int:ticket_id>/status", methods=["PATCH"])
@login_required
def api_update_status(ticket_id: int):
    """API per cambio stato veloce del ticket."""
    
    ticket = Ticket.query.get_or_404(ticket_id)
    
    if not can_edit_ticket(current_user, ticket):
        return jsonify({'error': 'Non autorizzato'}), HTTPStatus.FORBIDDEN
    
    data = request.get_json()
    
    if not data or 'status' not in data:
        return jsonify({'error': 'Stato mancante'}), HTTPStatus.BAD_REQUEST
    
    try:
        new_status = TicketStatusEnum(data['status'])
        message = data.get('message', f'Stato cambiato in {new_status.value}')
        
        service = TicketService()
        service.change_status(
            ticket=ticket,
            new_status=new_status,
            changed_by=current_user,
            message=message,
            notify_requester=data.get('notify', True)
        )
        
        return jsonify({
            'success': True,
            'new_status': new_status.value,
            'status_label': new_status.value.replace('_', ' ').title(),
            'updated_at': get_utc_now().isoformat(),
            'updated_by': current_user.full_name
        })
        
    except ValueError:
        return jsonify({'error': 'Stato non valido'}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


# ────────────────────────────────────────────────────────────────────
#  Assegnazione AJAX
# ────────────────────────────────────────────────────────────────────

@ticket_bp.route("/api/<int:ticket_id>/assign", methods=["PATCH"])
@login_required
def api_assign_user(ticket_id: int):
    """API per assegnare ticket a utente."""
    
    ticket = Ticket.query.get_or_404(ticket_id)
    
    if not can_edit_ticket(current_user, ticket):
        return jsonify({'error': 'Non autorizzato'}), HTTPStatus.FORBIDDEN
    
    data = request.get_json()
    user_id = data.get('user_id')
    
    if user_id:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'Utente non trovato'}), HTTPStatus.NOT_FOUND
        
        # Verifica che l'utente sia di un dipartimento coinvolto
        valid_departments = [ticket.department_id]
        valid_departments.extend([d.id for d in ticket.shared_departments])
        
        if user.department_id not in valid_departments:
            return jsonify({
                'error': 'Utente non appartiene ai dipartimenti coinvolti'
            }), HTTPStatus.BAD_REQUEST
        
        ticket.assigned_to = user
        assigned_to_name = user.full_name
        
        # Auto-cambio stato se nuovo
        if ticket.status == TicketStatusEnum.nuovo:
            service = TicketService()
            service.change_status(
                ticket=ticket,
                new_status=TicketStatusEnum.in_lavorazione,
                changed_by=current_user,
                message=f"Preso in carico da {user.full_name}",
                notify_requester=False
            )
    else:
        ticket.assigned_to = None
        assigned_to_name = None
    
    try:
        db.session.commit()
        
        return jsonify({
            'success': True,
            'assigned_to_id': ticket.assigned_to_id,
            'assigned_to_name': assigned_to_name,
            'status': ticket.status.value
        })
        
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


# ────────────────────────────────────────────────────────────────────
#  Ricerca Utenti per Assegnazione
# ────────────────────────────────────────────────────────────────────

@ticket_bp.route("/api/<int:ticket_id>/assignable-users")
@login_required
def api_assignable_users(ticket_id: int):
    """API per ottenere lista utenti assegnabili al ticket."""
    
    ticket = Ticket.query.get_or_404(ticket_id)
    
    if not can_view_ticket(current_user, ticket):
        return jsonify({'error': 'Non autorizzato'}), HTTPStatus.FORBIDDEN
    
    # Dipartimenti coinvolti
    department_ids = [ticket.department_id]
    department_ids.extend([d.id for d in ticket.shared_departments])
    
    # Utenti dei dipartimenti
    users = User.query.filter(
        User.department_id.in_(department_ids),
        User.is_active == True
    ).order_by(User.first_name, User.last_name).all()
    
    return jsonify({
        'users': [
            {
                'id': u.id,
                'name': u.full_name,
                'department': u.department.name if u.department else '',
                'is_assigned': u.id == ticket.assigned_to_id
            }
            for u in users
        ]
    })


# ────────────────────────────────────────────────────────────────────
#  Commenti AJAX
# ────────────────────────────────────────────────────────────────────

@ticket_bp.route("/api/<int:ticket_id>/comments", methods=["GET"])
@login_required
def api_get_comments(ticket_id: int):
    """API per ottenere commenti del ticket."""
    
    ticket = Ticket.query.get_or_404(ticket_id)
    
    if not can_view_ticket(current_user, ticket):
        return jsonify({'error': 'Non autorizzato'}), HTTPStatus.FORBIDDEN
    
    # Solo commenti visibili all'utente
    comments = ticket.comments
    if not current_user.is_admin and current_user.id != ticket.assigned_to_id:
        # Filtra solo commenti non interni per utenti normali
        comments = [c for c in comments if not c.is_internal]
    
    return jsonify({
        'comments': [
            {
                'id': c.id,
                'author': c.author.full_name,
                'author_avatar': c.author.avatar_url,
                'content': c.content,
                'is_internal': c.is_internal,
                'created_at': c.created_at.isoformat(),
                'created_at_human': c.created_at.strftime('%d/%m/%Y %H:%M')
            }
            for c in comments
        ]
    })


@ticket_bp.route("/api/<int:ticket_id>/comments", methods=["POST"])
@login_required
def api_add_comment(ticket_id: int):
    """API per aggiungere commento al ticket."""
    
    ticket = Ticket.query.get_or_404(ticket_id)
    
    if not can_view_ticket(current_user, ticket):
        return jsonify({'error': 'Non autorizzato'}), HTTPStatus.FORBIDDEN
    
    data = request.get_json()
    
    if not data or not data.get('content'):
        return jsonify({'error': 'Contenuto mancante'}), HTTPStatus.BAD_REQUEST
    
    try:
        comment = TicketComment(
            ticket_id=ticket_id,
            author_id=current_user.id,
            content=data['content'],
            is_internal=True  # Sempre interno
        )
        
        db.session.add(comment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'comment': {
                'id': comment.id,
                'author': comment.author.full_name,
                'author_avatar': comment.author.avatar_url,
                'content': comment.content,
                'is_internal': comment.is_internal,
                'created_at': comment.created_at.isoformat(),
                'created_at_human': comment.created_at.strftime('%d/%m/%Y %H:%M')
            }
        }), HTTPStatus.CREATED
        
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


# ────────────────────────────────────────────────────────────────────
#  Dashboard Stats AJAX (CON FILTRI)
# ────────────────────────────────────────────────────────────────────

@ticket_bp.route("/api/dashboard-stats")
@login_required
def api_dashboard_stats():
    """API per statistiche real-time dashboard con filtri applicati."""
    
    # Query base con permessi
    base_query = get_user_accessible_tickets_query(current_user)
    
    # Applica gli stessi filtri della dashboard
    filtered_query = apply_dashboard_filters(base_query, request.args, current_user)
    
    # Calcola statistiche sui ticket filtrati
    stats = {
        'total': filtered_query.count(),
        'open': filtered_query.filter(
            Ticket.status != TicketStatusEnum.chiuso
        ).count(),
        'new': filtered_query.filter(
            Ticket.status == TicketStatusEnum.nuovo
        ).count(),
        'in_progress': filtered_query.filter(
            Ticket.status == TicketStatusEnum.in_lavorazione
        ).count(),
        'waiting': filtered_query.filter(
            Ticket.status == TicketStatusEnum.in_attesa
        ).count(),
        'closed': filtered_query.filter(
            Ticket.status == TicketStatusEnum.chiuso
        ).count(),
        'overdue': filtered_query.filter(
            Ticket.status != TicketStatusEnum.chiuso,
            Ticket.due_date.isnot(None),
            Ticket.due_date < get_utc_now()
        ).count(),
        'high_priority': filtered_query.filter(
            Ticket.urgency == TicketUrgencyEnum.alta,
            Ticket.status != TicketStatusEnum.chiuso
        ).count(),
    }
    
    return jsonify(stats)


# ────────────────────────────────────────────────────────────────────
#  Timeline AJAX
# ────────────────────────────────────────────────────────────────────

@ticket_bp.route("/api/<int:ticket_id>/timeline")
@login_required
def api_ticket_timeline(ticket_id: int):
    """API per timeline attività del ticket."""
    
    ticket = Ticket.query.get_or_404(ticket_id)
    
    if not can_view_ticket(current_user, ticket):
        return jsonify({'error': 'Non autorizzato'}), HTTPStatus.FORBIDDEN
    
    timeline = []
    
    # Creazione ticket
    timeline.append({
        'type': 'created',
        'timestamp': ticket.created_at.isoformat(),
        'timestamp_human': ticket.created_at.strftime('%d/%m/%Y %H:%M'),
        'description': f'Ticket creato da {ticket.requester_first_name} {ticket.requester_last_name}',
        'icon': 'plus-circle',
        'color': 'primary'
    })
    
    # Cambi di stato
    for change in ticket.status_changes:
        timeline.append({
            'type': 'status_change',
            'timestamp': change.created_at.isoformat(),
            'timestamp_human': change.created_at.strftime('%d/%m/%Y %H:%M'),
            'description': f'{change.changed_by.full_name}: {change.message}',
            'from_status': change.from_status.value if change.from_status else None,
            'to_status': change.to_status.value,
            'icon': 'activity',
            'color': 'warning'
        })
    
    # Commenti (solo non interni o se autorizzato)
    for comment in ticket.comments:
        if comment.is_internal and not current_user.is_admin:
            continue
        
        timeline.append({
            'type': 'comment',
            'timestamp': comment.created_at.isoformat(),
            'timestamp_human': comment.created_at.strftime('%d/%m/%Y %H:%M'),
            'description': f'{comment.author.full_name}: {comment.content[:100]}...' 
                          if len(comment.content) > 100 else comment.content,
            'is_internal': comment.is_internal,
            'icon': 'message-circle',
            'color': 'info'
        })
    
    # Ordina per timestamp
    timeline.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return jsonify({'timeline': timeline})
