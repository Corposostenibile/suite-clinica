"""
blueprints/ticket/email_service.py
==================================

Servizio centralizzato per l'invio email del sistema ticket.
Usa lo stesso pattern del modulo auth per coerenza.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from flask import current_app, render_template_string
from flask_mail import Message

from corposostenibile.extensions import mail
from corposostenibile.models import Ticket, TicketComment, User, TicketStatusChange
from .timezone_utils import get_rome_time, format_rome_datetime


def send_ticket_email(
    subject: str,
    recipients: List[str],
    template_name: str,
    context: dict,
    sender: Optional[str] = None
) -> bool:
    """
    Invia email per il sistema ticket usando template HTML.
    
    Args:
        subject: Oggetto dell'email
        recipients: Lista destinatari
        template_name: Nome del template (senza estensione)
        context: Contesto per il template
        sender: Mittente opzionale
        
    Returns:
        True se inviata con successo
    """
    
    if not recipients:
        current_app.logger.debug("[TicketEmail] SKIP, nessun destinatario")
        return True
    
    if not current_app.config.get('TICKET_EMAIL_ENABLED', False):
        current_app.logger.info(
            f"[TicketEmail] Email simulata (servizio disabilitato): {subject} a {', '.join(recipients)}"
        )
        return True
    
    try:
        # Genera solo versione testuale
        text_body = _generate_text_version(template_name, context)
        
        # Prepara il messaggio (solo testo, senza HTML)
        msg = Message(
            subject=subject,
            recipients=recipients,
            sender=sender or current_app.config.get('MAIL_DEFAULT_SENDER'),
            body=text_body
        )
        
        # Invia
        mail.send(msg)
        
        current_app.logger.info(
            f"[TicketEmail] Email inviata: '{subject}' a {', '.join(recipients)}"
        )
        
        return True
        
    except Exception as e:
        current_app.logger.error(
            f"[TicketEmail] Errore invio email '{subject}': {str(e)}"
        )
        
        if current_app.debug:
            import traceback
            current_app.logger.error(traceback.format_exc())
        
        return False


def _generate_text_version(template_name: str, context: dict) -> str:
    """Genera versione testuale dell'email in base al template."""
    
    if template_name == "ticket_assigned":
        user = context.get('user')
        ticket = context.get('ticket')
        assigned_by = context.get('assigned_by')
        
        # Formatta urgenza in modo più leggibile
        urgency_text = {
            'alta': '🔴 Alta - Da risolvere entro oggi',
            'media': '🟡 Media - Da risolvere entro 2 giorni', 
            'bassa': '🟢 Bassa - Da risolvere entro la settimana'
        }.get(ticket.urgency.value, ticket.urgency.value.capitalize())
        
        # Aggiungi info su altri assegnati se presenti
        other_assigned = context.get('other_assigned_users', [])
        other_assigned_text = ""
        if other_assigned:
            other_assigned_text = f"\nAssegnato anche a: {', '.join(other_assigned)}"
        
        return (
            f"Ciao {user.first_name},\n\n"
            f"Ti è stato assegnato un nuovo ticket da {assigned_by.full_name}.\n\n"
            f"DETTAGLI TICKET:\n"
            f"================\n"
            f"Numero: #{ticket.ticket_number}\n"
            f"Titolo: {ticket.title}\n"
            f"Richiedente: {ticket.requester_first_name} {ticket.requester_last_name}\n"
            f"Dipartimento: {ticket.department.name}\n"
            f"Urgenza: {urgency_text}\n"
            f"Scadenza: {format_rome_datetime(ticket.due_date)}"
            f"{other_assigned_text}\n\n"
            f"DESCRIZIONE:\n"
            f"------------\n"
            f"{ticket.description[:500]}{'...' if len(ticket.description) > 500 else ''}\n\n"
            f"AZIONE RICHIESTA:\n"
            f"Accedi alla piattaforma per gestire il ticket:\n"
            f"{context.get('url')}\n\n"
            f"--\n"
            f"Corposostenibile Suite - Sistema Ticket\n"
            f"Questa è una notifica automatica, non rispondere a questa email."
        )
    
    elif template_name == "status_changed":
        recipient = context.get('recipient')
        ticket = context.get('ticket')
        changed_by = context.get('changed_by')
        old_status = context.get('old_status')
        new_status = context.get('new_status')
        message = context.get('message', '')
        
        # Mappa stati in italiano
        status_map = {
            'nuovo': 'Nuovo',
            'in_lavorazione': 'In Lavorazione',
            'in_attesa': 'In Attesa',
            'chiuso': 'Chiuso'
        }
        
        old_status_text = status_map.get(old_status.value, old_status.value.replace('_', ' ').title())
        new_status_text = status_map.get(new_status.value, new_status.value.replace('_', ' ').title())
        
        # Aggiungi emoji per rendere più chiaro il cambio
        status_emoji = {
            'nuovo': '🆕',
            'in_lavorazione': '🔄',
            'in_attesa': '⏸️',
            'chiuso': '✅'
        }
        
        # Prepara la sezione messaggio separatamente
        message_section = ""
        if message:
            message_section = f"MESSAGGIO:\n{message}\n\n"
        
        return (
            f"Ciao {recipient.first_name},\n\n"
            f"Il ticket #{ticket.ticket_number} ha cambiato stato.\n\n"
            f"AGGIORNAMENTO:\n"
            f"==============\n"
            f"Da: {status_emoji.get(old_status.value, '')} {old_status_text}\n"
            f"A: {status_emoji.get(new_status.value, '')} {new_status_text}\n"
            f"Modificato da: {changed_by.full_name}\n"
            f"Data: {get_rome_time().strftime('%d/%m/%Y alle %H:%M')}\n\n"
            f"{message_section}"
            f"TICKET:\n"
            f"-------\n"
            f"Titolo: {ticket.title}\n"
            f"Richiedente: {ticket.requester_first_name} {ticket.requester_last_name}\n\n"
            f"Per vedere tutti i dettagli:\n"
            f"{context.get('url')}\n\n"
            f"--\n"
            f"Corposostenibile Suite - Sistema Ticket\n"
            f"Questa è una notifica automatica, non rispondere a questa email."
        )
    
    elif template_name == "new_comment":
        recipient = context.get('recipient')
        ticket = context.get('ticket')
        author = context.get('author')
        comment = context.get('comment')
        
        # Limita lunghezza commento per email
        comment_text = comment.content
        if len(comment_text) > 800:
            comment_text = comment_text[:800] + "...\n\n[Commento troncato - accedi al ticket per leggerlo completo]"
        
        return (
            f"Ciao {recipient.first_name},\n\n"
            f"C'è una nuova nota sul ticket #{ticket.ticket_number}.\n\n"
            f"NUOVA NOTA INTERNA:\n"
            f"==================\n"
            f"Autore: {author.full_name}\n"
            f"Data: {format_rome_datetime(comment.created_at)}\n\n"
            f"Messaggio:\n"
            f"----------\n"
            f"{comment_text}\n\n"
            f"TICKET:\n"
            f"-------\n"
            f"Titolo: {ticket.title}\n"
            f"Stato: {ticket.status.value.replace('_', ' ').title()}\n\n"
            f"Per rispondere o vedere la conversazione completa:\n"
            f"{context.get('url')}\n\n"
            f"--\n"
            f"Corposostenibile Suite - Sistema Ticket\n"
            f"Questa è una notifica automatica, non rispondere a questa email.\n"
            f"Le note interne sono visibili solo al team che gestisce il ticket."
        )
    
    else:
        return "Email da Corposostenibile Suite"


def send_assignment_notification(ticket: Ticket, user: User, assigned_by: User) -> bool:
    """Invia notifica di assegnazione ticket."""
    
    # Prepara URL
    ticket_url = _build_ticket_url(ticket)
    
    # Altri utenti assegnati
    other_assigned = [u.full_name for u in ticket.assigned_users if u.id != user.id]
    
    context = {
        'user': user,
        'ticket': ticket,
        'assigned_by': assigned_by,
        'url': ticket_url,
        'other_assigned_users': other_assigned,
        'datetime': __import__('datetime').datetime
    }
    
    return send_ticket_email(
        subject=f"Ticket #{ticket.ticket_number} - Ti è stato assegnato",
        recipients=[user.email],
        template_name='ticket_assigned',
        context=context
    )


def send_status_change_notification(
    ticket: Ticket,
    recipient: User,
    changed_by: User,
    old_status,
    new_status,
    message: Optional[str] = None
) -> bool:
    """Invia notifica di cambio stato ticket."""
    
    context = {
        'recipient': recipient,
        'ticket': ticket,
        'changed_by': changed_by,
        'old_status': old_status,
        'new_status': new_status,
        'message': message,
        'url': _build_ticket_url(ticket),
        'datetime': __import__('datetime').datetime
    }
    
    return send_ticket_email(
        subject=f"Ticket #{ticket.ticket_number} - Aggiornamento stato",
        recipients=[recipient.email],
        template_name='status_changed',
        context=context
    )


def send_comment_notification(
    ticket: Ticket,
    comment: TicketComment,
    recipient: User,
    author: User
) -> bool:
    """Invia notifica per nuovo commento/nota interna."""
    
    context = {
        'recipient': recipient,
        'ticket': ticket,
        'comment': comment,
        'author': author,
        'url': _build_ticket_url(ticket),
        'datetime': __import__('datetime').datetime
    }
    
    return send_ticket_email(
        subject=f"Ticket #{ticket.ticket_number} - Nuova nota interna",
        recipients=[recipient.email],
        template_name='new_comment',
        context=context
    )


def _build_ticket_url(ticket: Ticket) -> str:
    """Costruisce URL completo del ticket."""
    server_name = current_app.config.get('SERVER_NAME', 'localhost')
    if not server_name.startswith(('http://', 'https://')):
        server_name = f"https://{server_name}"
    return f"{server_name}/tickets/{ticket.id}"