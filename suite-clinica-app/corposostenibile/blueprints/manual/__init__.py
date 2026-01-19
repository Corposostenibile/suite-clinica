"""
Blueprint Manual - Manuale della Suite Corposostenibile
========================================================

Fornisce documentazione completa per ogni modulo della suite,
organizzata per ruolo utente (HR, Finance, Admin, etc.)
"""

from flask import Blueprint

manual_bp = Blueprint(
    "manual",
    __name__,
    template_folder="templates",
    static_folder="static",
    url_prefix="/manual"
)

def init_app(app):
    """
    Inizializza e registra il blueprint manual.
    """
    # Import routes
    from . import routes

    # Registra blueprint
    app.register_blueprint(manual_bp)

    app.logger.info("[manual] Blueprint initialized")
