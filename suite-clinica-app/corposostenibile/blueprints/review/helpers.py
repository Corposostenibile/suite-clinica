"""
Helper functions per il sistema di Review
"""

from corposostenibile.models import Review, ReviewAcknowledgment, ReviewMessage, ReviewRequest, Department
from sqlalchemy import or_


def get_unread_reviews_count(user):
    """
    Conta il numero di review non ancora confermate per un utente.
    ESCLUDE le review private (che non sono visibili al destinatario).
    
    Args:
        user: L'oggetto User per cui contare le review non lette
        
    Returns:
        int: Numero di review non confermate (escluse le private)
    """
    if not user or not user.is_authenticated:
        return 0
    
    # Query per trovare le review ricevute dall'utente
    # che non sono bozze, non sono cancellate, non sono private e non sono ancora confermate
    unread_count = Review.query.filter(
        Review.reviewee_id == user.id,
        Review.is_draft == False,
        Review.is_private == False,  # ESCLUDI review private
        Review.deleted_at == None
    ).outerjoin(
        ReviewAcknowledgment, 
        ReviewAcknowledgment.review_id == Review.id
    ).filter(
        ReviewAcknowledgment.id == None
    ).count()
    
    return unread_count


def has_unread_reviews(user):
    """
    Verifica se un utente ha review non lette.
    
    Args:
        user: L'oggetto User da verificare
        
    Returns:
        bool: True se ci sono review non lette, False altrimenti
    """
    return get_unread_reviews_count(user) > 0


def get_unread_messages_count(user):
    """
    Conta il numero di messaggi non letti per un utente in tutte le sue review.
    
    Args:
        user: L'oggetto User per cui contare i messaggi non letti
        
    Returns:
        int: Numero totale di messaggi non letti
    """
    if not user or not user.is_authenticated:
        return 0
    
    # Trova tutte le review dove l'utente è reviewer o reviewee
    reviews = Review.query.filter(
        or_(
            Review.reviewer_id == user.id,
            Review.reviewee_id == user.id
        ),
        Review.deleted_at == None
    ).all()
    
    review_ids = [r.id for r in reviews]
    
    if not review_ids:
        return 0
    
    # Conta i messaggi non letti in queste review
    # (escludi i messaggi inviati dall'utente stesso)
    unread_count = ReviewMessage.query.filter(
        ReviewMessage.review_id.in_(review_ids),
        ReviewMessage.is_read == False,
        ReviewMessage.sender_id != user.id,
        ReviewMessage.deleted_at == None
    ).count()
    
    return unread_count


def get_total_unread_count(user):
    """
    Conta il numero totale di notifiche non lette (review + messaggi).
    
    Args:
        user: L'oggetto User per cui contare le notifiche
        
    Returns:
        int: Numero totale di notifiche non lette
    """
    if not user or not user.is_authenticated:
        return 0
    
    reviews_count = get_unread_reviews_count(user)
    messages_count = get_unread_messages_count(user)
    
    return reviews_count + messages_count


def has_unread_notifications(user):
    """
    Verifica se un utente ha notifiche non lette (review o messaggi).
    
    Args:
        user: L'oggetto User da verificare
        
    Returns:
        bool: True se ci sono notifiche non lette, False altrimenti
    """
    return get_total_unread_count(user) > 0


def get_review_unread_messages_count(user, review):
    """
    Conta i messaggi non letti per una specifica review.
    
    Args:
        user: L'oggetto User che sta leggendo
        review: L'oggetto Review da controllare
        
    Returns:
        int: Numero di messaggi non letti in questa review
    """
    if not user or not user.is_authenticated or not review:
        return 0
    
    # L'utente può vedere i messaggi solo se è reviewer, reviewee, admin o HR
    if not (user.is_admin or (hasattr(user, 'department_id') and user.department_id == 17) or
            user.id == review.reviewer_id or user.id == review.reviewee_id):
        return 0
    
    # Conta messaggi non letti (non inviati dall'utente)
    unread_count = ReviewMessage.query.filter_by(
        review_id=review.id,
        is_read=False,
        deleted_at=None
    ).filter(
        ReviewMessage.sender_id != user.id
    ).count()
    
    return unread_count


def get_pending_requests_count(user):
    """
    Conta il numero di richieste di training pending per un utente.
    Include:
    - Richieste ricevute se l'utente è un responsabile
    - Richieste inviate se l'utente è un membro normale
    
    Args:
        user: L'oggetto User per cui contare le richieste
        
    Returns:
        int: Numero di richieste pending
    """
    if not user or not user.is_authenticated:
        return 0
    
    count = 0
    
    # Se è un responsabile, admin o HR, conta le richieste ricevute pending
    if user.is_admin or (hasattr(user, 'department_id') and user.department_id == 17):
        count = ReviewRequest.query.filter_by(
            requested_to_id=user.id,
            status='pending'
        ).count()
    else:
        # Verifica se è head di un dipartimento
        department = Department.query.filter_by(head_id=user.id).first()
        if department:
            count = ReviewRequest.query.filter_by(
                requested_to_id=user.id,
                status='pending'
            ).count()
    
    return count


def get_my_pending_requests_count(user):
    """
    Conta le richieste inviate dall'utente che sono ancora pending.
    
    Args:
        user: L'oggetto User per cui contare le richieste
        
    Returns:
        int: Numero di richieste inviate pending
    """
    if not user or not user.is_authenticated:
        return 0
    
    return ReviewRequest.query.filter_by(
        requester_id=user.id,
        status='pending'
    ).count()


def get_total_review_notifications(user):
    """
    Conta tutte le notifiche del modulo review:
    - Review non lette
    - Messaggi non letti
    - Richieste pending (se responsabile)
    
    Args:
        user: L'oggetto User per cui contare le notifiche
        
    Returns:
        int: Numero totale di notifiche
    """
    if not user or not user.is_authenticated:
        return 0
    
    total = 0
    total += get_unread_reviews_count(user)
    total += get_unread_messages_count(user)
    total += get_pending_requests_count(user)
    
    return total