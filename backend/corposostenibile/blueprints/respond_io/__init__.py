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
    app.register_blueprint(bp)