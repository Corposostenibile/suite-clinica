"""
Decorators for Sales Form Blueprint
"""

from functools import wraps
from flask import flash, redirect, url_for, abort
from flask_login import current_user


def admin_required(f):
    """Decorator che richiede privilegi admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Devi effettuare il login', 'warning')
            return redirect(url_for('auth.login'))

        # Verifica se l'utente è admin
        if not getattr(current_user, 'is_admin', False):
            flash('Non hai i permessi per accedere a questa pagina', 'error')
            abort(403)

        return f(*args, **kwargs)
    return decorated_function


def department_required(department_ids):
    """Decorator che richiede appartenenza a specifici dipartimenti"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Devi effettuare il login', 'warning')
                return redirect(url_for('auth.login'))

            # Verifica se l'utente è admin (bypass check)
            if getattr(current_user, 'is_admin', False):
                return f(*args, **kwargs)

            # Verifica appartenenza al dipartimento
            user_dept_id = getattr(current_user, 'department_id', None)
            if user_dept_id not in department_ids:
                flash('Non hai i permessi per accedere a questa sezione', 'error')
                abort(403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def sales_required(f):
    """
    Decorator specifico per sales.
    Permette accesso a:
    - Admin (bypass totale)
    - Dipartimenti 5 e 18 (Consulenti Sales)
    - Utenti con SalesFormLink attivo (es. Finance che fa anche Sales)
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Devi effettuare il login', 'warning')
            return redirect(url_for('auth.login'))

        # Admin bypass
        if getattr(current_user, 'is_admin', False):
            return f(*args, **kwargs)

        # Check department (5 o 18)
        user_dept_id = getattr(current_user, 'department_id', None)
        if user_dept_id in [5, 18]:
            return f(*args, **kwargs)

        # Check se ha un SalesFormLink attivo
        from corposostenibile.models import SalesFormLink
        has_sales_link = SalesFormLink.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).filter(
            SalesFormLink.lead_id.is_(None)  # Solo link di tipo "sales", non "check"
        ).first()

        if has_sales_link:
            return f(*args, **kwargs)

        # Nessun permesso
        flash('Non hai i permessi per accedere a questa sezione', 'error')
        abort(403)

    return decorated_function


def finance_required(f):
    """Decorator specifico per finance (dipartimento 19)"""
    return department_required([19])(f)


def health_manager_required(f):
    """Decorator specifico per health manager (dipartimento 13)"""
    return department_required([13])(f)