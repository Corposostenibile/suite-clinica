"""
blueprints/ticket/public_routes.py
==================================

Route pubbliche per apertura ticket senza autenticazione.
"""

from __future__ import annotations

from flask import (
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy.exc import SQLAlchemyError

from corposostenibile.extensions import db
from corposostenibile.models import (
    Department,
    Ticket,
    TicketUrgencyEnum,
)

from . import public_ticket_bp
from .forms import PublicTicketForm
from .services import TicketService


# ────────────────────────────────────────────────────────────────────
#  Form Pubblico
# ────────────────────────────────────────────────────────────────────

@public_ticket_bp.route("/new", methods=["GET", "POST"])
def new_ticket():
    """Form pubblico per creare un nuovo ticket."""
    
    form = PublicTicketForm()
    
    if form.validate_on_submit():
        try:
            # Crea ticket tramite service
            service = TicketService()
            
            ticket = service.create_ticket(
                requester_first_name=form.first_name.data.strip(),
                requester_last_name=form.last_name.data.strip(),
                requester_email=form.email.data.strip().lower(),
                requester_department=None,  # Campo rimosso
                department_id=form.department_id.data,
                title=form.title.data.strip(),
                description=form.description.data.strip(),
                urgency=TicketUrgencyEnum(form.urgency.data),
                related_client_name=form.related_client_name.data.strip() if form.related_client_name.data else None,
                attachment=form.attachment.data if hasattr(form, 'attachment') else None  # Passa l'allegato se presente
            )
            
            # Salva ticket number in sessione per pagina conferma
            session['last_ticket_number'] = ticket.ticket_number
            session['last_ticket_email'] = ticket.requester_email
            
            return redirect(url_for("public_ticket.success"))
            
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(
                "Si è verificato un errore durante l'invio. Riprova più tardi.",
                "danger"
            )
            # Log errore
            from flask import current_app
            current_app.logger.error(f"Errore creazione ticket pubblico: {str(e)}")
    
    # Pre-compila form se ci sono dati in query string (es. da link diretto)
    if request.method == 'GET':
        if request.args.get('department'):
            dept = Department.query.filter_by(
                name=request.args.get('department')
            ).first()
            if dept:
                form.department_id.data = dept.id
        
        if request.args.get('client'):
            form.related_client_name.data = request.args.get('client')
    
    return render_template(
        "ticket/public/form.html",
        form=form
    )


# ────────────────────────────────────────────────────────────────────
#  Pagina Conferma
# ────────────────────────────────────────────────────────────────────

@public_ticket_bp.route("/success")
def success():
    """Pagina di conferma dopo creazione ticket."""
    
    # Recupera dati dalla sessione
    ticket_number = session.pop('last_ticket_number', None)
    ticket_email = session.pop('last_ticket_email', None)
    
    if not ticket_number:
        # Se non c'è ticket in sessione, redirect al form
        return redirect(url_for("public_ticket.new_ticket"))
    
    return render_template(
        "ticket/public/success.html",
        ticket_number=ticket_number,
        ticket_email=ticket_email
    )


# ────────────────────────────────────────────────────────────────────
#  Tracking Pubblico
# ────────────────────────────────────────────────────────────────────

@public_ticket_bp.route("/track")
def track():
    """Form per tracciare stato ticket con numero e email."""
    
    ticket_number = request.args.get('number', '').strip()
    email = request.args.get('email', '').strip()
    
    ticket = None
    error = None
    
    if ticket_number and email:
        # Cerca ticket
        ticket = Ticket.query.filter_by(
            ticket_number=ticket_number.upper(),
            requester_email=email.lower()
        ).first()
        
        if not ticket:
            error = "Ticket non trovato. Verifica il numero e l'email."
    
    return render_template(
        "ticket/public/track.html",
        ticket=ticket,
        ticket_number=ticket_number,
        email=email,
        error=error
    )


# ────────────────────────────────────────────────────────────────────
#  Info/FAQ
# ────────────────────────────────────────────────────────────────────

@public_ticket_bp.route("/info")
def info():
    """Pagina informativa sul sistema ticket."""
    
    departments = Department.query.order_by(Department.name).all()
    
    # Info urgenze
    urgency_info = [
        {
            'level': TicketUrgencyEnum.alta,
            'label': 'Alta',
            'icon': '🔴',
            'description': 'Per problemi urgenti che bloccano il lavoro',
            'sla': 'Entro la giornata lavorativa'
        },
        {
            'level': TicketUrgencyEnum.media,
            'label': 'Media',
            'icon': '🟡',
            'description': 'Per richieste importanti ma non bloccanti',
            'sla': 'Entro 2 giorni lavorativi'
        },
        {
            'level': TicketUrgencyEnum.bassa,
            'label': 'Bassa',
            'icon': '🟢',
            'description': 'Per richieste di informazioni o miglioramenti',
            'sla': 'Entro una settimana'
        }
    ]
    
    return render_template(
        "ticket/public/info.html",
        departments=departments,
        urgency_info=urgency_info
    )