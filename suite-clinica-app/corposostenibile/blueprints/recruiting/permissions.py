"""
Permissions helper for Recruiting module
"""

from functools import wraps
from flask import abort, current_app
from flask_login import current_user


def can_access_recruiting(user=None):
    """
    Verifica se l'utente può accedere al modulo recruiting.

    Args:
        user: User object (default: current_user)

    Returns:
        bool: True se l'utente ha accesso
    """
    if user is None:
        user = current_user

    if not user or not user.is_authenticated:
        return False

    # Admin ha sempre accesso completo
    if user.is_admin:
        return True

    # Membri del dipartimento 17 (HR) hanno accesso
    if user.department_id == 17:
        return True

    # Membri del dipartimento 19 hanno accesso
    if user.department_id == 19:
        return True

    # Utenti specifici con accesso (user ID 59)
    if user.id == 59:
        return True

    return False


def can_manage_recruiting(user=None):
    """
    Verifica se l'utente può gestire (create/edit/delete) recruiting.

    Args:
        user: User object (default: current_user)

    Returns:
        bool: True se l'utente può gestire
    """
    if user is None:
        user = current_user

    if not user or not user.is_authenticated:
        return False

    # Admin ha sempre accesso completo
    if user.is_admin:
        return True

    # Membri del dipartimento 17 (HR) possono gestire
    if user.department_id == 17:
        return True

    # Membri del dipartimento 19 possono gestire
    if user.department_id == 19:
        return True

    # Utenti specifici con accesso (user ID 59)
    if user.id == 59:
        return True

    return False


def recruiting_required(f):
    """
    Decorator per route che richiedono accesso recruiting.

    Usage:
        @recruiting_bp.route("/offers")
        @login_required
        @recruiting_required
        def offers_list():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not can_access_recruiting():
            current_app.logger.warning(
                f"[recruiting] Access denied for user {current_user.id} - department {current_user.department_id}"
            )
            abort(403, description="Non hai i permessi per accedere a questa sezione")
        return f(*args, **kwargs)
    return decorated_function


def recruiting_manage_required(f):
    """
    Decorator per route che richiedono permessi di gestione recruiting.

    Usage:
        @recruiting_bp.route("/offers/new", methods=["POST"])
        @login_required
        @recruiting_manage_required
        def offer_create():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not can_manage_recruiting():
            current_app.logger.warning(
                f"[recruiting] Manage access denied for user {current_user.id} - department {current_user.department_id}"
            )
            abort(403, description="Non hai i permessi per gestire questa sezione")
        return f(*args, **kwargs)
    return decorated_function
