"""
Respond.io Integration Blueprint
================================

Tracking completo del funnel di conversione per origine WhatsApp.
Gestione orari di lavoro e assegnazioni automatiche contatti.
"""

from flask import Blueprint

bp = Blueprint('respond_io', __name__, 
               url_prefix='/respond-io',
               template_folder='templates',
               static_folder='static')

def init_app(app):
    """Inizializza il blueprint respond.io con l'app Flask."""
    # COMMENTATO: Disabilita tutte le funzionalità del blueprint respond_io
    # from . import routes, webhooks, api_routes, schedule_routes, calendar_routes, assignment_routes, websocket_routes, user_shifts_routes, assignment_monitoring_routes, webhook_monitoring_routes
    # from .timestamp_assignment_service import TimestampAssignmentService
    
    app.register_blueprint(bp)
    
    # # COMMENTATO: Registra webhook handlers
    # webhooks.register_webhook_handlers(app)
    
    # # COMMENTATO: Inizializza il client API (se necessario per future integrazioni)
    # from .client import RespondIOClient
    # app.respond_io_client = RespondIOClient(app.config)
    
    # # COMMENTATO: Inizializza servizio assegnazioni
    # from .assignment_service import ContactAssignmentService
    # app.contact_assignment_service = ContactAssignmentService(app.respond_io_client)
    
    # # COMMENTATO: Inizializza servizio assegnazioni basato su timbrature
    # app.timestamp_assignment_service = TimestampAssignmentService(app.respond_io_client)
    
    # NOTA: Rimosso lo scheduler automatico ogni 10 minuti
    # Le assegnazioni ora sono triggerate solo dalle timbrature