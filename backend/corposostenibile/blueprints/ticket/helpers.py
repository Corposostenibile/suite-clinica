"""
blueprints/ticket/helpers.py
============================

Helper functions per il sistema ticket.
"""

from flask import Flask
from urllib.parse import urlencode
from datetime import datetime
from corposostenibile.models import db, Ticket, TicketStatusEnum, User


def get_open_tickets_count(user: User) -> int:
    """
    Conta i ticket aperti (non chiusi) assegnati all'utente.

    Args:
        user: L'oggetto User per cui contare i ticket aperti

    Returns:
        int: Numero di ticket aperti assegnati all'utente
    """
    if not user or not user.is_authenticated:
        return 0

    # I ticket usano una relazione many-to-many tramite ticket_assigned_users
    # Conta tutti i ticket assegnati all'utente che non sono chiusi
    open_tickets = Ticket.query.join(
        db.metadata.tables['ticket_assigned_users']
    ).filter(
        db.metadata.tables['ticket_assigned_users'].c.user_id == user.id,
        Ticket.status != TicketStatusEnum.chiuso
    ).count()

    return open_tickets


def register_template_filters(app: Flask) -> None:
    """Registra filtri template personalizzati per ticket."""
    
    @app.template_filter('ticket_status_label')
    def ticket_status_label(status):
        """Converte enum status in label leggibile."""
        if not status:
            return ""
        if hasattr(status, 'value'):
            return status.value.replace('_', ' ').title()
        return str(status).replace('_', ' ').title()
    
    @app.template_filter('ticket_urgency_icon')
    def ticket_urgency_icon(urgency):
        """Ritorna icona per urgenza."""
        icons = {
            '1': '🔴',  # alta
            '2': '🟡',  # media  
            '3': '🟢',  # bassa
        }
        if hasattr(urgency, 'value'):
            return icons.get(urgency.value, '')
        return icons.get(str(urgency), '')
    
    @app.template_filter('ticket_urgency_label')
    def ticket_urgency_label(urgency):
        """Converte urgenza in label leggibile."""
        labels = {
            '1': 'Alta',
            '2': 'Media',
            '3': 'Bassa'
        }
        if hasattr(urgency, 'value'):
            return labels.get(urgency.value, urgency.value)
        return labels.get(str(urgency), str(urgency))
    
    @app.template_filter('ticket_status_badge_class')
    def ticket_status_badge_class(status):
        """Ritorna classe CSS per badge status."""
        classes = {
            'nuovo': 'badge-danger',
            'in_lavorazione': 'badge-warning',
            'in_attesa': 'badge-info',
            'chiuso': 'badge-success'
        }
        if hasattr(status, 'value'):
            return classes.get(status.value, 'badge-secondary')
        return classes.get(str(status), 'badge-secondary')
    
    @app.template_filter('update_query_params')
    def update_query_params(existing_args, **kwargs):
        """
        Aggiorna i parametri query string mantenendo quelli esistenti.
        
        Args:
            existing_args: Dizionario dei parametri esistenti
            **kwargs: Nuovi parametri da aggiungere/aggiornare
            
        Returns:
            Query string aggiornata
        """
        # Copia i parametri esistenti
        params = dict(existing_args)
        
        # Aggiorna con i nuovi parametri
        for key, value in kwargs.items():
            if value is not None:
                params[key] = value
            elif key in params:
                # Se il valore è None, rimuovi il parametro
                del params[key]
        
        # Rimuovi parametri vuoti
        params = {k: v for k, v in params.items() if v}
        
        return urlencode(params)
    
    # Registra context processor per rendere disponibili le funzioni nei template
    @app.context_processor
    def inject_ticket_permissions():
        """Inietta le funzioni di permesso nei template."""
        from .permissions import can_edit_ticket, can_view_ticket, can_delete_ticket
        return dict(
            can_edit_ticket=can_edit_ticket,
            can_view_ticket=can_view_ticket,
            can_delete_ticket=can_delete_ticket,
            datetime=datetime
        )