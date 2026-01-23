"""
blueprints.ticket
=================

Blueprint per la gestione del sistema di ticketing aziendale.
Permette la creazione di ticket da form pubblico e la gestione
inter-dipartimentale delle richieste.

- URL-prefix: ``/tickets`` (autenticato) e ``/public/ticket`` (pubblico)
- ACL: basato su ruoli department head e membership
"""

from __future__ import annotations

from flask import Blueprint

# ────────────────────────────────────────────────────────────────────────────
# Istanze Blueprint
# ────────────────────────────────────────────────────────────────────────────

# Blueprint principale (richiede autenticazione)
ticket_bp = Blueprint(
    "ticket",
    __name__,
    template_folder="templates",
    static_folder="static",
)

# Blueprint pubblico (no autenticazione)
public_ticket_bp = Blueprint(
    "public_ticket",
    __name__,
    template_folder="templates",
    static_folder="static",
)

# ────────────────────────────────────────────────────────────────────────────
# Factory-helper (richiamato dall'application-factory)
# ────────────────────────────────────────────────────────────────────────────

def init_app(app):
    """
    Registra i blueprint ticket e configura l'ACL.
    Chiamato da ``corposostenibile/__init__.py``.
    """
    # Mount dei blueprint
    app.register_blueprint(ticket_bp, url_prefix="/tickets")
    app.register_blueprint(public_ticket_bp, url_prefix="/public/ticket")
    
    # ACL – department heads possono gestire ticket del loro dipartimento
    if hasattr(app, "acl"):
        # Admin può tutto
        if not app.acl.permitted("admin", "ticket:manage_all"):
            app.acl.allow("admin", "ticket:manage_all")
        
        # Department head può gestire ticket del proprio dipartimento
        if not app.acl.permitted("department_head", "ticket:manage_department"):
            app.acl.allow("department_head", "ticket:manage_department")
        
        # Membri possono vedere ticket del loro dipartimento
        if not app.acl.permitted("member", "ticket:view_department"):
            app.acl.allow("member", "ticket:view_department")
        
        app.logger.debug(
            "[ticket] ACL rules registered"
        )
    
    # Registra filtri template personalizzati
    from .helpers import register_template_filters
    register_template_filters(app)
    
    # Configura email service se abilitato
    if app.config.get('TICKET_EMAIL_ENABLED', False):
        from .services import TicketEmailService
        TicketEmailService.init_app(app)
        app.logger.info("[ticket] Email service initialized")

# ────────────────────────────────────────────────────────────────────────────
# Import delle route (deve restare *in fondo*)
# ────────────────────────────────────────────────────────────────────────────

from . import routes, public_routes, api_routes  # noqa: E402,F401