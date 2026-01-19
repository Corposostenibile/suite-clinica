"""
blueprints/ticket/email_templates.py
====================================

Template HTML per le email del sistema ticketing.
"""

from __future__ import annotations

from typing import Optional

from flask import url_for

from corposostenibile.models import (
    Department,
    Ticket,
    TicketStatusChange,
    User,
)


def get_email_base_template() -> str:
    """Template base HTML per tutte le email."""
    
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                background-color: #f5f5f5;
                margin: 0;
                padding: 0;
            }
            .container {
                max-width: 600px;
                margin: 20px auto;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            .header {
                background: #2c3e50;
                color: white;
                padding: 20px;
                text-align: center;
            }
            .header h1 {
                margin: 0;
                font-size: 24px;
            }
            .content {
                padding: 30px;
            }
            .ticket-info {
                background: #f8f9fa;
                border-radius: 6px;
                padding: 20px;
                margin: 20px 0;
            }
            .ticket-info h2 {
                margin-top: 0;
                color: #2c3e50;
                font-size: 18px;
            }
            .info-row {
                display: flex;
                justify-content: space-between;
                padding: 8px 0;
                border-bottom: 1px solid #e9ecef;
            }
            .info-row:last-child {
                border-bottom: none;
            }
            .info-label {
                font-weight: 600;
                color: #6c757d;
            }
            .urgency-alta {
                color: #dc3545;
                font-weight: bold;
            }
            .urgency-media {
                color: #ffc107;
                font-weight: bold;
            }
            .urgency-bassa {
                color: #28a745;
                font-weight: bold;
            }
            .status-badge {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 14px;
                font-weight: 500;
            }
            .status-nuovo {
                background: #dc3545;
                color: white;
            }
            .status-in_lavorazione {
                background: #ffc107;
                color: #333;
            }
            .status-in_attesa {
                background: #17a2b8;
                color: white;
            }
            .status-chiuso {
                background: #28a745;
                color: white;
            }
            .message-box {
                background: #e3f2fd;
                border-left: 4px solid #2196f3;
                padding: 15px;
                margin: 20px 0;
            }
            .button {
                display: inline-block;
                padding: 12px 24px;
                background: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                font-weight: 500;
                margin: 20px 0;
            }
            .button:hover {
                background: #0056b3;
            }
            .footer {
                background: #f8f9fa;
                padding: 20px;
                text-align: center;
                color: #6c757d;
                font-size: 14px;
            }
            .description {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 4px;
                margin: 15px 0;
                white-space: pre-wrap;
            }
        </style>
    </head>
    <body>
        <div class="container">
            {{ content }}
        </div>
    </body>
    </html>
    """


def get_new_ticket_email(ticket: Ticket, is_requester: bool = True) -> str:
    """
    Template email per nuovo ticket.
    
    Args:
        ticket: Il ticket creato
        is_requester: True se destinato al richiedente, False se al dipartimento
        
    Returns:
        HTML dell'email
    """
    
    urgency_class = f"urgency-{ticket.urgency.value}"
    
    if is_requester:
        # Email per il richiedente
        content = f"""
        <div class="header">
            <h1>Ticket Ricevuto</h1>
        </div>
        <div class="content">
            <p>Gentile {ticket.requester_first_name} {ticket.requester_last_name},</p>
            
            <p>Abbiamo ricevuto la tua richiesta e l'abbiamo inoltrata al dipartimento 
            <strong>{ticket.department.name}</strong>.</p>
            
            <div class="ticket-info">
                <h2>Dettagli del Ticket</h2>
                <div class="info-row">
                    <span class="info-label">Numero Ticket:</span>
                    <span><strong>#{ticket.ticket_number}</strong></span>
                </div>
                <div class="info-row">
                    <span class="info-label">Oggetto:</span>
                    <span>{ticket.title}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Urgenza:</span>
                    <span class="{urgency_class}">{ticket.urgency_label}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Tempo di risoluzione previsto:</span>
                    <span>{ticket.due_date.strftime('%d/%m/%Y ore %H:%M')}</span>
                </div>
            </div>
            
            <p>Riceverai aggiornamenti via email quando lo stato del ticket cambierà.</p>
            
            <div class="footer">
                <p>Questa è un'email automatica, ti preghiamo di non rispondere.</p>
            </div>
        </div>
        """
    else:
        # Email per il dipartimento
        client_info = ""
        if ticket.related_client_name:
            client_info = f"""
                <div class="info-row">
                    <span class="info-label">Cliente/Lead:</span>
                    <span>{ticket.related_client_name}</span>
                </div>
            """
        
        content = f"""
        <div class="header">
            <h1>Nuovo Ticket Assegnato</h1>
        </div>
        <div class="content">
            <p>È stato ricevuto un nuovo ticket per il dipartimento <strong>{ticket.department.name}</strong>.</p>
            
            <div class="ticket-info">
                <h2>Informazioni Ticket</h2>
                <div class="info-row">
                    <span class="info-label">Numero:</span>
                    <span><strong>#{ticket.ticket_number}</strong></span>
                </div>
                <div class="info-row">
                    <span class="info-label">Richiedente:</span>
                    <span>{ticket.requester_first_name} {ticket.requester_last_name} 
                    ({ticket.requester_email})</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Dipartimento richiedente:</span>
                    <span>{ticket.requester_department or 'Non specificato'}</span>
                </div>
                {client_info}
                <div class="info-row">
                    <span class="info-label">Urgenza:</span>
                    <span class="{urgency_class}">{ticket.urgency_label}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Scadenza:</span>
                    <span><strong>{ticket.due_date.strftime('%d/%m/%Y ore %H:%M')}</strong></span>
                </div>
            </div>
            
            <h3>Oggetto</h3>
            <p><strong>{ticket.title}</strong></p>
            
            <h3>Descrizione</h3>
            <div class="description">{ticket.description}</div>
            
            
        </div>
        """
    
    template = get_email_base_template()
    return template.replace("{{ content }}", content)


def get_status_change_email(ticket: Ticket, status_change: TicketStatusChange) -> str:
    """
    Template email per cambio stato ticket.
    
    Args:
        ticket: Il ticket aggiornato
        status_change: Il cambio di stato
        
    Returns:
        HTML dell'email
    """
    
    status_class = f"status-{ticket.status.value}"
    
    content = f"""
    <div class="header">
        <h1>Aggiornamento Ticket #{ticket.ticket_number}</h1>
    </div>
    <div class="content">
        <p>Il ticket <strong>#{ticket.ticket_number}</strong> è stato aggiornato.</p>
        
        <div class="ticket-info">
            <h2>Stato Aggiornato</h2>
            <div class="info-row">
                <span class="info-label">Nuovo stato:</span>
                <span class="{status_class} status-badge">{ticket.status.value.replace('_', ' ').title()}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Aggiornato da:</span>
                <span>{status_change.changed_by.full_name}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Data aggiornamento:</span>
                <span>{status_change.created_at.strftime('%d/%m/%Y alle %H:%M')}</span>
            </div>
        </div>
        
        <div class="message-box">
            <strong>Messaggio di aggiornamento:</strong><br>
            {status_change.message}
        </div>
        
        <div class="ticket-info">
            <h2>Riepilogo Ticket</h2>
            <div class="info-row">
                <span class="info-label">Oggetto:</span>
                <span>{ticket.title}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Dipartimento:</span>
                <span>{ticket.department.name}</span>
            </div>
        </div>
        
        <div class="footer">
            <p>Questa è un'email automatica di aggiornamento.</p>
        </div>
    </div>
    """
    
    template = get_email_base_template()
    return template.replace("{{ content }}", content)


def get_ticket_shared_email(
    ticket: Ticket,
    department: Department,
    shared_by: User,
    message: Optional[str] = None
) -> str:
    """
    Template email per ticket condiviso con nuovo dipartimento.
    
    Args:
        ticket: Il ticket condiviso
        department: Il dipartimento con cui è stato condiviso
        shared_by: L'utente che ha condiviso
        message: Messaggio opzionale
        
    Returns:
        HTML dell'email
    """
    
    urgency_class = f"urgency-{ticket.urgency.value}"
    
    message_section = ""
    if message:
        message_section = f"""
        <div class="message-box">
            <strong>Messaggio da {shared_by.full_name}:</strong><br>
            {message}
        </div>
        """
    
    content = f"""
    <div class="header">
        <h1>Ticket Condiviso con il tuo Dipartimento</h1>
    </div>
    <div class="content">
        <p>Il ticket <strong>#{ticket.ticket_number}</strong> è stato condiviso con il 
        dipartimento <strong>{department.name}</strong>.</p>
        
        {message_section}
        
        <div class="ticket-info">
            <h2>Dettagli Ticket</h2>
            <div class="info-row">
                <span class="info-label">Numero:</span>
                <span><strong>#{ticket.ticket_number}</strong></span>
            </div>
            <div class="info-row">
                <span class="info-label">Oggetto:</span>
                <span>{ticket.title}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Richiedente:</span>
                <span>{ticket.requester_first_name} {ticket.requester_last_name}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Dipartimento principale:</span>
                <span>{ticket.department.name}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Urgenza:</span>
                <span class="{urgency_class}">{ticket.urgency_label}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Stato attuale:</span>
                <span>{ticket.status.value.replace('_', ' ').title()}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Condiviso da:</span>
                <span>{shared_by.full_name} ({shared_by.department.name if shared_by.department else 'N/A'})</span>
            </div>
        </div>
        
        <h3>Descrizione</h3>
        <div class="description">{ticket.description}</div>
        
    
    </div>
    """
    
    template = get_email_base_template()
    return template.replace("{{ content }}", content)