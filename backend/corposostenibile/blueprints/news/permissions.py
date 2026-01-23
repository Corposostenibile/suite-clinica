"""
Permissions per il blueprint News.

Regole:
- ADMIN (tutti): possono creare, modificare, eliminare TUTTE le news
- CREATOR SPECIALI (user_id: 10, 95, 6, 28): possono creare news, modificare/eliminare SOLO le proprie
- ALTRI UTENTI: possono solo leggere, commentare, mettere like
"""

from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user

# Lista degli user ID con permessi di creazione/modifica
ALLOWED_CREATOR_IDS = [10, 95, 6, 28]


def can_create_news(user=None):
    """
    Verifica se l'utente può creare news.

    Returns:
        bool: True se admin o user_id in ALLOWED_CREATOR_IDS
    """
    if user is None:
        user = current_user

    if not user.is_authenticated:
        return False

    # Admin possono sempre creare
    if user.is_admin:
        return True

    # Creator speciali possono creare
    if user.id in ALLOWED_CREATOR_IDS:
        return True

    return False


def can_edit_news(news, user=None):
    """
    Verifica se l'utente può modificare una specifica news.

    Args:
        news: Oggetto News
        user: Oggetto User (default: current_user)

    Returns:
        bool: True se admin o autore della news
    """
    if user is None:
        user = current_user

    if not user.is_authenticated:
        return False

    # Admin possono modificare tutto
    if user.is_admin:
        return True

    # Creator speciali possono modificare solo le proprie news
    if user.id in ALLOWED_CREATOR_IDS and news.author_id == user.id:
        return True

    return False


def can_delete_news(news, user=None):
    """
    Verifica se l'utente può eliminare una specifica news.

    Args:
        news: Oggetto News
        user: Oggetto User (default: current_user)

    Returns:
        bool: True se admin o autore della news
    """
    if user is None:
        user = current_user

    if not user.is_authenticated:
        return False

    # Admin possono eliminare tutto
    if user.is_admin:
        return True

    # Creator speciali possono eliminare solo le proprie news
    if user.id in ALLOWED_CREATOR_IDS and news.author_id == user.id:
        return True

    return False


def can_pin_news(user=None):
    """
    Verifica se l'utente può mettere/togliere in evidenza le news.
    Solo admin possono pinnare.

    Returns:
        bool: True se admin
    """
    if user is None:
        user = current_user

    if not user.is_authenticated:
        return False

    return user.is_admin


def can_publish_news(user=None):
    """
    Verifica se l'utente può pubblicare/nascondere news.
    Solo admin possono gestire la pubblicazione.

    Returns:
        bool: True se admin
    """
    if user is None:
        user = current_user

    if not user.is_authenticated:
        return False

    return user.is_admin


# ──────────────────────────── DECORATORS ─────────────────────────────


def create_news_required(f):
    """
    Decorator per route che richiedono permesso di creazione news.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not can_create_news():
            flash('❌ Non hai i permessi per creare novità.', 'danger')
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def edit_news_required(f):
    """
    Decorator per route che richiedono permesso di modifica news.
    Nota: il controllo effettivo avviene dentro la route con can_edit_news(news)
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('❌ Devi essere autenticato.', 'danger')
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def admin_only(f):
    """
    Decorator per route riservate solo agli admin.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('❌ Solo gli amministratori possono accedere a questa funzione.', 'danger')
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
