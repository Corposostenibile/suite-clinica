"""
Knowledge Base Permissions
==========================
Sistema di permessi per la gestione della documentazione.
"""

from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user
from corposostenibile.models import KBArticle, Department, User


def is_kb_admin(user: User = None) -> bool:
    """
    Verifica se l'utente è admin KB (admin globale o HEAD di qualsiasi dipartimento).
    """
    user = user or current_user
    if not user.is_authenticated:
        return False
    
    if user.is_admin:
        return True
    
    # Controlla se è HEAD di almeno un dipartimento
    if user.department and user.department.head_id == user.id:
        return True
    
    return False


def is_department_head(department_id: int, user: User = None) -> bool:
    """
    Verifica se l'utente è HEAD del dipartimento specificato.
    """
    user = user or current_user
    if not user.is_authenticated:
        return False
    
    if user.is_admin:
        return True
    
    if user.department_id == department_id and user.department.head_id == user.id:
        return True
    
    return False


def can_create_article(department_id: int, user: User = None) -> bool:
    """
    Verifica se l'utente può creare articoli nel dipartimento.
    """
    user = user or current_user
    if not user.is_authenticated:
        return False
    
    # Admin può creare ovunque
    if user.is_admin:
        return True
    
    # HEAD può creare nel proprio dipartimento
    if is_department_head(department_id, user):
        return True
    
    return False


def can_edit_article(article: KBArticle, user: User = None) -> bool:
    """
    Verifica se l'utente può modificare un articolo.
    """
    user = user or current_user
    if not user.is_authenticated:
        return False
    
    # Usa il metodo del modello
    return article.can_edit(user)


def can_view_article(article: KBArticle, user: User = None) -> bool:
    """
    Verifica se l'utente può visualizzare un articolo.
    """
    user = user or current_user
    if not user.is_authenticated:
        return False
    
    # Usa il metodo del modello
    return article.can_view(user)


def can_manage_categories(department_id: int, user: User = None) -> bool:
    """
    Verifica se l'utente può gestire le categorie del dipartimento.
    """
    user = user or current_user
    if not user.is_authenticated:
        return False
    
    # Solo admin e HEAD del dipartimento
    return user.is_admin or is_department_head(department_id, user)


def can_view_analytics(department_id: int, user: User = None) -> bool:
    """
    Verifica se l'utente può vedere gli analytics del dipartimento.
    """
    user = user or current_user
    if not user.is_authenticated:
        return False
    
    # Solo admin e HEAD del dipartimento
    return user.is_admin or is_department_head(department_id, user)


def can_manage_storage(department_id: int, user: User = None) -> bool:
    """
    Verifica se l'utente può gestire lo storage del dipartimento.
    """
    user = user or current_user
    if not user.is_authenticated:
        return False
    
    # Solo admin globali
    return user.is_admin


# Decoratori per le route
def kb_admin_required(f):
    """Richiede privilegi admin KB (admin o HEAD)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_kb_admin():
            flash('Accesso negato. Richiesti privilegi amministrativi.', 'danger')
            return redirect(url_for('kb.index'))
        return f(*args, **kwargs)
    return decorated_function


def department_head_required(f):
    """Richiede che l'utente sia HEAD del dipartimento specificato."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        department_id = kwargs.get('department_id')
        if not department_id:
            abort(400, "ID dipartimento mancante")
        
        if not is_department_head(department_id):
            flash('Accesso negato. Solo il responsabile del dipartimento può accedere.', 'danger')
            return redirect(url_for('kb.department_view', department_id=department_id))
        
        return f(*args, **kwargs)
    return decorated_function


def article_edit_permission_required(f):
    """Richiede permessi di modifica per l'articolo."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        article_id = kwargs.get('article_id')
        if not article_id:
            abort(400, "ID articolo mancante")
        
        article = KBArticle.query.get_or_404(article_id)
        
        if not can_edit_article(article):
            flash('Non hai i permessi per modificare questo articolo.', 'danger')
            return redirect(url_for('kb.article_view', article_id=article_id))
        
        kwargs['article'] = article  # Passa l'articolo alla funzione
        return f(*args, **kwargs)
    return decorated_function


def article_view_permission_required(f):
    """Richiede permessi di visualizzazione per l'articolo."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        article_id = kwargs.get('article_id')
        if not article_id:
            abort(400, "ID articolo mancante")
        
        article = KBArticle.query.get_or_404(article_id)
        
        if not can_view_article(article):
            flash('Non hai i permessi per visualizzare questo articolo.', 'danger')
            return redirect(url_for('kb.index'))
        
        kwargs['article'] = article  # Passa l'articolo alla funzione
        return f(*args, **kwargs)
    return decorated_function