"""
blueprints/ticket/permissions.py
================================

Helper per gestione permessi del sistema ticketing.
"""

from __future__ import annotations

from typing import Optional

from flask_login import current_user
from sqlalchemy import and_, or_

from corposostenibile.models import (
    Department,
    Ticket,
    TicketStatusEnum,
    User,
    db,
)


def is_department_head(user: User, department: Department) -> bool:
    """
    Verifica se l'utente è capo del dipartimento specificato.
    
    Args:
        user: Utente da verificare
        department: Dipartimento
        
    Returns:
        True se l'utente è il capo
    """
    return department.head_id == user.id


def is_department_member(user: User, department: Department) -> bool:
    """
    Verifica se l'utente è membro del dipartimento.
    
    Args:
        user: Utente da verificare
        department: Dipartimento
        
    Returns:
        True se l'utente appartiene al dipartimento
    """
    return user.department_id == department.id


def can_view_ticket(user: User, ticket: Ticket) -> bool:
    """
    Verifica se un utente può visualizzare un ticket.
    
    Un utente può vedere un ticket se:
    - È admin
    - È il creatore del ticket
    - È capo del dipartimento principale o condiviso
    - È capo del dipartimento e il ticket è stato creato da un membro del suo team
    - È assegnato al ticket (vecchio campo o nuovo assigned_users)
    
    Args:
        user: Utente che richiede accesso
        ticket: Ticket da visualizzare
        
    Returns:
        True se l'utente può vedere il ticket
    """
    
    if not user or not user.is_authenticated:
        return False
    
    # Admin può vedere tutto
    if user.is_admin:
        return True
    
    # Creatore del ticket può sempre vederlo
    if ticket.created_by_id == user.id:
        return True
    
    # Capo del dipartimento principale
    if ticket.department and is_department_head(user, ticket.department):
        return True
    
    # Capo di un dipartimento condiviso
    for dept in ticket.shared_departments:
        if is_department_head(user, dept):
            return True
    
    # NUOVO: Se l'utente è head di un dipartimento, può vedere i ticket creati dai membri
    if ticket.created_by_id:
        # Ottieni i dipartimenti di cui l'utente è capo
        departments_led = Department.query.filter(Department.head_id == user.id).all()
        if departments_led:
            # Verifica se il creatore del ticket è membro di uno dei dipartimenti gestiti
            ticket_creator = User.query.get(ticket.created_by_id)
            if ticket_creator and ticket_creator.department_id in [d.id for d in departments_led]:
                return True
    
    # Assegnato al ticket (vecchio sistema)
    if ticket.assigned_to_id == user.id:
        return True
    
    # Assegnato al ticket (nuovo sistema multi-utente)
    if user in ticket.assigned_users:
        return True
    
    return False


def can_edit_ticket(user: User, ticket: Ticket) -> bool:
    """
    Verifica se un utente può modificare un ticket.
    
    Un utente può modificare un ticket se:
    - È admin
    - È capo del dipartimento principale
    - È capo di un dipartimento condiviso
    - È assegnato al ticket (vecchio o nuovo sistema)
    
    Args:
        user: Utente che richiede accesso
        ticket: Ticket da modificare
        
    Returns:
        True se l'utente può modificare il ticket
    """
    
    if not can_view_ticket(user, ticket):
        return False
    
    # Admin può modificare tutto
    if user.is_admin:
        return True
    
    # Assegnato al ticket (vecchio sistema)
    if ticket.assigned_to_id == user.id:
        return True
    
    # Assegnato al ticket (nuovo sistema multi-utente)
    if user in ticket.assigned_users:
        return True
    
    # Capo del dipartimento principale
    if ticket.department and is_department_head(user, ticket.department):
        return True
    
    # Capo di un dipartimento condiviso
    for dept in ticket.shared_departments:
        if is_department_head(user, dept):
            return True
    
    return False


def can_share_ticket(user: User, ticket: Ticket) -> bool:
    """
    Verifica se un utente può condividere un ticket con altri dipartimenti.
    
    - Admin: può condividere tutti i ticket
    - Head: può condividere i ticket del proprio dipartimento
    - User: può condividere i ticket a lui assegnati
    
    Args:
        user: Utente che vuole condividere
        ticket: Ticket da condividere
        
    Returns:
        True se l'utente può condividere il ticket
    """
    
    if not user or not user.is_authenticated:
        return False
    
    # Admin può condividere tutto
    if user.is_admin:
        return True
    
    # Head può condividere i ticket del proprio dipartimento
    if ticket.department and is_department_head(user, ticket.department):
        return True
    
    # User può condividere i ticket a lui assegnati
    if user in ticket.assigned_users:
        return True
    
    return False


def can_close_ticket(user: User, ticket: Ticket) -> bool:
    """
    Verifica se un utente può chiudere un ticket.
    
    Args:
        user: Utente che vuole chiudere
        ticket: Ticket da chiudere
        
    Returns:
        True se l'utente può chiudere il ticket
    """
    
    # Stessi permessi di modifica
    return can_edit_ticket(user, ticket)


def can_delete_ticket(user: User, ticket: Ticket) -> bool:
    """
    Verifica se un utente può eliminare un ticket.
    
    Solo admin e capi del dipartimento principale possono eliminare.
    Il ticket non deve essere chiuso da più di 7 giorni.
    
    Args:
        user: Utente che vuole eliminare
        ticket: Ticket da eliminare
        
    Returns:
        True se l'utente può eliminare il ticket
    """
    
    if not user or not user.is_authenticated:
        return False
    
    # Admin può eliminare tutto
    if user.is_admin:
        return True
    
    # Solo il capo del dipartimento principale può eliminare
    if ticket.department and is_department_head(user, ticket.department):
        # Non permettere eliminazione di ticket chiusi da più di 7 giorni
        if ticket.status == TicketStatusEnum.chiuso and ticket.closed_at:
            from datetime import datetime, timedelta
            import pytz
            rome_tz = pytz.timezone('Europe/Rome')
            now_rome = datetime.now(rome_tz)
            closed_rome = pytz.utc.localize(ticket.closed_at).astimezone(rome_tz)
            days_closed = (now_rome - closed_rome).days
            if days_closed > 7:
                return False
        return True
    
    return False


def can_assign_ticket(user: User, ticket: Ticket, target_user: User) -> bool:
    """
    Verifica se un utente può assegnare un ticket a un altro utente.
    
    Solo i capi dipartimento possono assegnare ticket ai membri del loro team.
    
    Args:
        user: Utente che vuole assegnare
        ticket: Ticket da assegnare
        target_user: Utente target dell'assegnazione
        
    Returns:
        True se l'assegnazione è permessa
    """
    
    # Admin può assegnare a chiunque
    if user.is_admin:
        return True
    
    # Deve essere capo del dipartimento del ticket
    if not (ticket.department and is_department_head(user, ticket.department)):
        # Oppure capo di un dipartimento condiviso
        is_head_of_shared = False
        for dept in ticket.shared_departments:
            if is_department_head(user, dept):
                is_head_of_shared = True
                break
        
        if not is_head_of_shared:
            return False
    
    # L'utente target deve essere del dipartimento del capo
    departments_led = Department.query.filter(Department.head_id == user.id).all()
    dept_ids_led = [d.id for d in departments_led]
    
    return target_user.department_id in dept_ids_led


def get_user_accessible_tickets_query(user: User):
    """
    Ritorna una query per tutti i ticket accessibili all'utente nella dashboard.
    
    Regole di accesso:
    - Admin: vede TUTTO
    - Head di dipartimento: vede TUTTI i ticket del suo dipartimento (anche non assegnati) 
      E tutti i ticket CREATI dai membri del suo dipartimento
    - User normale: vede SOLO i ticket assegnati a lui personalmente
    
    NOTA: I ticket creati dall'utente sono visibili nella pagina "I miei ticket"
    
    Args:
        user: Utente corrente
        
    Returns:
        SQLAlchemy Query object
    """
    
    if not user or not user.is_authenticated:
        # Nessun ticket per utenti non autenticati
        return Ticket.query.filter(Ticket.id == -1)
    
    if user.is_admin:
        # Admin vede tutto
        return Ticket.query
    
    # Costruisci condizioni di accesso
    conditions = []
    
    # Se l'utente è capo di un dipartimento
    departments_led = Department.query.filter(Department.head_id == user.id).all()
    
    # Debug logging
    from flask import current_app
    current_app.logger.debug(f"User {user.email} - Is head of departments: {[d.name for d in departments_led]}")
    
    if departments_led:
        # Head vede TUTTI i ticket del suo dipartimento
        for dept in departments_led:
            # Ticket del dipartimento di cui è capo
            conditions.append(Ticket.department_id == dept.id)
            
            # Ticket condivisi con dipartimenti di cui è capo
            conditions.append(
                Ticket.shared_departments.any(
                    Department.id == dept.id
                )
            )
            
            # NUOVO: Ticket CREATI dai membri del dipartimento di cui è capo
            # Ottieni tutti i membri del dipartimento
            dept_member_ids = db.session.query(User.id).filter(
                User.department_id == dept.id
            ).subquery()
            
            # Aggiungi condizione per ticket creati dai membri
            conditions.append(
                Ticket.created_by_id.in_(dept_member_ids)
            )
    
    # Per TUTTI gli utenti (head e normali): aggiungi ticket assegnati personalmente
    # Ticket assegnati (vecchio sistema)
    conditions.append(Ticket.assigned_to_id == user.id)
    
    # Ticket assegnati (nuovo sistema multi-utente)
    conditions.append(
        Ticket.assigned_users.any(
            User.id == user.id
        )
    )
    
    # IMPORTANTE: utenti normali (non head) vedranno SOLO i ticket assegnati a loro
    # perché non avranno altre condizioni aggiunte sopra
    
    if not conditions:
        # Nessun accesso
        return Ticket.query.filter(Ticket.id == -1)
    
    query = Ticket.query.filter(or_(*conditions))
    current_app.logger.debug(f"Query conditions for {user.email}: {len(conditions)} conditions")
    
    return query


def get_user_departments(user: User) -> list[Department]:
    """
    Ottiene tutti i dipartimenti a cui l'utente ha accesso.
    
    Args:
        user: Utente
        
    Returns:
        Lista di dipartimenti
    """
    
    if user.is_admin:
        return Department.query.order_by(Department.name).all()
    
    departments = []
    
    # Il proprio dipartimento
    if user.department:
        departments.append(user.department)
    
    # I dipartimenti di cui è capo
    departments_led = Department.query.filter(Department.head_id == user.id).all()
    departments.extend(departments_led)
    
    # Rimuovi duplicati mantenendo l'ordine
    seen = set()
    unique_departments = []
    for dept in departments:
        if dept.id not in seen:
            seen.add(dept.id)
            unique_departments.append(dept)
    
    return sorted(unique_departments, key=lambda d: d.name)


def can_view_all_tickets(user: User) -> bool:
    """
    Verifica se l'utente può vedere tutti i ticket del sistema.
    
    Args:
        user: Utente
        
    Returns:
        True se può vedere tutti i ticket
    """
    return user.is_authenticated and user.is_admin


def can_view_department_tickets(user: User, department: Department) -> bool:
    """
    Verifica se l'utente può vedere i ticket di un dipartimento.
    
    Args:
        user: Utente
        department: Dipartimento
        
    Returns:
        True se può vedere i ticket del dipartimento
    """
    
    if not user or not user.is_authenticated:
        return False
    
    if user.is_admin:
        return True
    
    # Può vedere se è membro del dipartimento
    if is_department_member(user, department):
        return True
    
    # NUOVO: Può vedere se è capo del dipartimento
    if is_department_head(user, department):
        return True
    
    return False


def get_user_created_tickets_query(user: User):
    """
    Ritorna una query per tutti i ticket creati dall'utente.
    Usata per la pagina "I miei ticket".
    
    Args:
        user: Utente corrente
        
    Returns:
        SQLAlchemy Query object
    """
    
    if not user or not user.is_authenticated:
        return Ticket.query.filter(Ticket.id == -1)
    
    return Ticket.query.filter(Ticket.created_by_id == user.id)


def get_assignable_users_for_ticket(user: User, ticket: Ticket) -> list[User]:
    """
    Ottiene la lista degli utenti a cui si può assegnare il ticket.
    Mette i responsabili per primi nella lista.
    
    Args:
        user: Utente che vuole assegnare
        ticket: Ticket da assegnare
        
    Returns:
        Lista di utenti assegnabili (responsabili per primi)
    """
    
    if not user or not user.is_authenticated:
        return []
    
    # Determina i dipartimenti da cui prendere gli utenti
    dept_ids = []
    
    if user.is_admin:
        # Admin può assegnare a tutti gli utenti del dipartimento del ticket
        # Gestione speciale per Consulenti Sales
        if ticket.department and ticket.department.name in ['Consulenti Sales 1', 'Consulenti Sales 2']:
            # Prendi membri da entrambi i Consulenti Sales
            sales_depts = Department.query.filter(
                Department.name.in_(['Consulenti Sales 1', 'Consulenti Sales 2'])
            ).all()
            dept_ids = [d.id for d in sales_depts]
        else:
            dept_ids = [ticket.department_id]
    else:
        # Capi dipartimento possono assegnare solo ai membri del loro team
        departments_led = Department.query.filter(Department.head_id == user.id).all()
        if not departments_led:
            return []
        dept_ids = [d.id for d in departments_led]
    
    # Ottieni tutti i membri attivi
    users = User.query.filter(
        User.department_id.in_(dept_ids),
        User.is_active == True
    ).all()
    
    # Ottieni i dipartimenti per identificare i responsabili
    departments = Department.query.filter(Department.id.in_(dept_ids)).all()
    head_ids = [d.head_id for d in departments if d.head_id]
    
    # IMPORTANTE: Aggiungi anche gli HEAD che non sono membri diretti
    # Questo permette di assegnare ticket agli HEAD anche se non sono nel dipartimento
    for head_id in head_ids:
        if head_id and not any(u.id == head_id for u in users):
            head_user = User.query.filter_by(id=head_id, is_active=True).first()
            if head_user:
                users.append(head_user)
    
    # Separa responsabili dagli altri membri
    heads = []
    members = []
    
    for u in users:
        if u.id in head_ids:
            heads.append(u)
        else:
            members.append(u)
    
    # Ordina separatamente
    heads.sort(key=lambda u: (u.first_name, u.last_name))
    members.sort(key=lambda u: (u.first_name, u.last_name))
    
    # Ritorna prima i responsabili, poi gli altri
    return heads + members


def get_ticket_stats_for_user(user: User) -> dict:
    """
    Calcola statistiche ticket visibili all'utente.
    
    Args:
        user: Utente
        
    Returns:
        Dizionario con statistiche
    """
    
    from corposostenibile.models import TicketStatusEnum
    
    query = get_user_accessible_tickets_query(user)
    
    return {
        'total': query.count(),
        'open': query.filter(
            Ticket.status != TicketStatusEnum.chiuso
        ).count(),
        'assigned_to_me': query.filter(
            or_(
                Ticket.assigned_to_id == user.id,
                Ticket.assigned_users.any(User.id == user.id)
            )
        ).count() if user.is_authenticated else 0,
        'overdue': query.filter(
            Ticket.status != TicketStatusEnum.chiuso,
            Ticket.due_date < db.func.now()
        ).count(),
        'created_by_me': get_user_created_tickets_query(user).count() if user.is_authenticated else 0,
    }