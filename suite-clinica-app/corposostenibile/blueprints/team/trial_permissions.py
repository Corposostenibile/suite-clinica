"""
Sistema di permessi per Trial Users
"""
from functools import wraps
from flask import abort, redirect, url_for, flash
from flask_login import current_user


def check_trial_access(section):
    """
    Decorator per verificare l'accesso dei trial users alle sezioni.

    Usage:
        @check_trial_access('customers')
        def customer_view():
            ...
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))

            # User normale o admin: accesso completo
            if not current_user.is_trial or current_user.is_admin:
                return f(*args, **kwargs)

            # Verifica accesso per trial user
            if not current_user.can_access_section(section):
                flash(f'Non hai accesso alla sezione {section}. Sei attualmente in {current_user.trial_stage_description}', 'warning')
                return redirect(url_for('welcome.dashboard'))

            return f(*args, **kwargs)
        return wrapper
    return decorator


def check_client_access(cliente_id_param='cliente_id'):
    """
    Decorator per verificare che un trial user possa accedere a un cliente specifico.

    Usage:
        @check_client_access('cliente_id')
        def customer_detail(cliente_id):
            ...
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))

            # User normale o admin: accesso completo
            if not current_user.is_trial or current_user.is_admin:
                return f(*args, **kwargs)

            # Estrai cliente_id dai kwargs o args
            cliente_id = kwargs.get(cliente_id_param)
            if not cliente_id and args:
                # Prova a prendere il primo argomento
                cliente_id = args[0] if args else None

            if not cliente_id:
                abort(400)  # Bad request

            # Verifica accesso al cliente specifico
            if not current_user.can_view_client(cliente_id):
                flash('Non hai accesso a questo cliente', 'warning')
                return redirect(url_for('customers.list_view'))

            return f(*args, **kwargs)
        return wrapper
    return decorator


def filter_clients_for_trial_user(query):
    """
    Filtra una query di clienti per mostrare solo quelli accessibili a un trial user.

    Usage:
        query = Cliente.query.filter_by(stato_cliente='attivo')
        query = filter_clients_for_trial_user(query)
        clienti = query.all()
    """
    if not current_user.is_authenticated:
        return query.filter(False)  # Query vuota

    # User normale o admin: tutti i clienti
    if not current_user.is_trial or current_user.is_admin or current_user.trial_stage >= 3:
        return query

    # Stage 1: nessun cliente
    if current_user.trial_stage < 2:
        return query.filter(False)  # Query vuota

    # Stage 2: solo clienti assegnati
    from corposostenibile.models import Cliente, trial_user_clients
    assigned_ids = [c.cliente_id for c in current_user.trial_assigned_clients]

    if assigned_ids:
        return query.filter(Cliente.cliente_id.in_(assigned_ids))
    else:
        return query.filter(False)  # Query vuota se nessun cliente assegnato


def get_trial_user_menu_items():
    """
    Ritorna le voci di menu disponibili per un trial user basandosi sul suo stage.
    """
    if not current_user.is_authenticated or not current_user.is_trial:
        return []

    menu_items = []

    # Stage 1: Dashboard e Training
    if current_user.trial_stage >= 1:
        menu_items.extend([
            {
                'label': 'Dashboard',
                'url': url_for('welcome.dashboard'),
                'icon': 'ri-dashboard-line'
            },
            {
                'label': 'Training',
                'url': url_for('review.index'),
                'icon': 'ri-book-open-line'
            }
        ])

    # Stage 2: Aggiungi Clienti
    if current_user.trial_stage >= 2:
        menu_items.append({
            'label': 'Clienti Assegnati',
            'url': url_for('customers.list_view'),
            'icon': 'ri-user-3-line',
            'badge': len(current_user.trial_assigned_clients)
        })

    return menu_items


def is_trial_user_supervisor():
    """Verifica se l'utente corrente è supervisor di trial users"""
    if not current_user.is_authenticated:
        return False

    if current_user.is_admin:
        return True

    # Verifica se supervisiona qualche trial user
    from corposostenibile.models import User
    return User.query.filter_by(
        trial_supervisor_id=current_user.id,
        is_trial=True
    ).count() > 0