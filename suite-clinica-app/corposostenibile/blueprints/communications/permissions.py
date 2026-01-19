"""
Gestione permessi per il blueprint communications.
"""

from flask_login import current_user
from corposostenibile.models import Communication, Department, User


def can_create_communication(user: User) -> bool:
    """Verifica se l'utente può creare comunicazioni."""
    if not user or not user.is_active:
        return False
    
    # Admin possono sempre creare
    if user.is_admin:
        return True
    
    # Head di dipartimento possono creare per il loro dipartimento
    if user.department and user.department.head_id == user.id:
        return True
    
    return False


def can_create_for_all_departments(user: User) -> bool:
    """Verifica se l'utente può creare comunicazioni per tutti i dipartimenti."""
    return user and user.is_active and user.is_admin


def can_view_all_communications(user: User) -> bool:
    """Verifica se l'utente può vedere tutte le comunicazioni."""
    return user and user.is_active and user.is_admin


def can_view_communication(user: User, communication: Communication) -> bool:
    """Verifica se l'utente può vedere una specifica comunicazione."""
    if not user or not user.is_active:
        return False
    
    # Admin possono vedere tutto
    if user.is_admin:
        return True
    
    # L'autore può sempre vedere le proprie comunicazioni
    if communication.author_id == user.id:
        return True
    
    # Se è per tutti i dipartimenti, tutti possono vederla
    if communication.is_for_all_departments:
        return True
    
    # Altrimenti, solo se il dipartimento dell'utente è tra i destinatari
    if user.department:
        return user.department in communication.departments
    
    return False


def can_see_statistics(user: User, communication: Communication) -> bool:
    """Verifica se l'utente può vedere le statistiche di una comunicazione."""
    if not user or not user.is_active:
        return False
    
    # Admin possono vedere tutte le statistiche
    if user.is_admin:
        return True
    
    # L'autore può vedere le statistiche delle proprie comunicazioni
    if communication.author_id == user.id:
        return True
    
    return False


def get_user_accessible_communications(user: User):
    """Ottiene le comunicazioni accessibili all'utente."""
    from sqlalchemy import or_
    
    if not user or not user.is_active:
        return Communication.query.filter_by(id=-1)  # Query vuota
    
    # Admin vedono tutto
    if user.is_admin:
        return Communication.query
    
    # Head vedono le proprie comunicazioni
    if user.department and user.department.head_id == user.id:
        # Query per comunicazioni create dall'utente o destinate al suo dipartimento
        return Communication.query.filter(
            or_(
                Communication.author_id == user.id,
                Communication.is_for_all_departments == True,
                Communication.departments.any(Department.id == user.department_id)
            )
        )
    
    # Utenti normali vedono solo quelle del loro dipartimento o per tutti
    if user.department:
        return Communication.query.filter(
            or_(
                Communication.is_for_all_departments == True,
                Communication.departments.any(Department.id == user.department_id)
            )
        )
    
    # Se l'utente non ha dipartimento, vede solo quelle per tutti
    return Communication.query.filter_by(is_for_all_departments=True)


def get_unread_communications_count(user: User) -> int:
    """Conta le comunicazioni non lette per l'utente."""
    if not user or not user.is_active:
        return 0
    
    # Se è l'autore, non conta come non letta
    accessible = get_user_accessible_communications(user)
    
    # Filtra solo quelle che l'utente deve leggere (non è autore)
    to_read = accessible.filter(Communication.author_id != user.id)
    
    # Conta quelle non lette
    unread_count = 0
    for comm in to_read.all():
        if not comm.has_read(user):
            unread_count += 1
    
    return unread_count