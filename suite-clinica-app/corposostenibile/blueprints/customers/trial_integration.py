"""
Integrazione del sistema Trial Users con il modulo Customers
"""
from flask_login import current_user
from sqlalchemy import and_
from corposostenibile.models import Cliente, trial_user_clients


def apply_trial_user_filter(query):
    """
    Applica filtro per trial users alla query clienti.

    Args:
        query: SQLAlchemy query su Cliente

    Returns:
        Query filtrata per trial users o query originale per users normali
    """
    if not current_user.is_authenticated:
        # Non autenticato, nessun risultato
        return query.filter(False)

    # User normale o admin: accesso completo
    if not current_user.is_trial or current_user.is_admin:
        return query

    # Trial user stage 1: nessun cliente
    if current_user.trial_stage < 2:
        return query.filter(False)

    # Trial user stage 2: solo clienti assegnati
    if current_user.trial_stage == 2:
        # Ottieni IDs dei clienti assegnati
        assigned_ids = [c.cliente_id for c in current_user.trial_assigned_clients]

        if assigned_ids:
            return query.filter(Cliente.cliente_id.in_(assigned_ids))
        else:
            # Nessun cliente assegnato
            return query.filter(False)

    # Stage 3 o superiore (non dovrebbe arrivare qui, ma per sicurezza)
    return query


def can_view_cliente(cliente):
    """
    Verifica se l'utente corrente può visualizzare un cliente specifico.

    Args:
        cliente: Istanza di Cliente o cliente_id

    Returns:
        bool: True se può visualizzare, False altrimenti
    """
    if not current_user.is_authenticated:
        return False

    # Admin o user normale: accesso completo
    if not current_user.is_trial or current_user.is_admin:
        return True

    # Trial user stage 1: nessun accesso
    if current_user.trial_stage < 2:
        return False

    # Estrai cliente_id se è un oggetto
    if hasattr(cliente, 'cliente_id'):
        cliente_id = cliente.cliente_id
    else:
        cliente_id = cliente

    # Stage 2: verifica se è assegnato
    return current_user.can_view_client(cliente_id)


def can_edit_cliente(cliente):
    """
    Verifica se l'utente corrente può modificare un cliente.
    Per ora, i trial users NON possono modificare clienti.

    Args:
        cliente: Istanza di Cliente o cliente_id

    Returns:
        bool: True se può modificare, False altrimenti
    """
    if not current_user.is_authenticated:
        return False

    # Solo admin e users normali possono modificare
    return not current_user.is_trial or current_user.is_admin


def get_trial_user_stats():
    """
    Ottiene statistiche per un trial user.

    Returns:
        dict: Statistiche del trial user
    """
    if not current_user.is_authenticated or not current_user.is_trial:
        return {}

    stats = {
        'stage': current_user.trial_stage,
        'stage_description': current_user.trial_stage_description,
        'supervisor': current_user.trial_supervisor.full_name if current_user.trial_supervisor else None,
        'started_at': current_user.trial_started_at,
        'clients_assigned': 0,
        'clients_active': 0
    }

    if current_user.trial_stage >= 2:
        assigned_clients = current_user.trial_assigned_clients
        stats['clients_assigned'] = len(assigned_clients)
        stats['clients_active'] = sum(1 for c in assigned_clients if c.stato_cliente == 'attivo')

    return stats