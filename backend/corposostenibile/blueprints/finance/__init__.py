"""
Blueprint Finance
=================
Gestione finanziaria: pacchetti, costi e marginalità
"""

from flask import Blueprint

bp = Blueprint('finance', __name__, 
               url_prefix='/finance',
               template_folder='templates')

def init_app(app):
    """Inizializza il blueprint finance."""
    # Routes removed - no HTML endpoints served by this blueprint
    app.register_blueprint(bp)
    app.logger.info("[finance] Blueprint registrato con successo")