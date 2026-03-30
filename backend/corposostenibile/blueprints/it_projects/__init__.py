"""IT Projects - Gestione Progetti Dipartimento IT"""
from flask import Blueprint

bp = Blueprint(
    'it_projects',
    __name__,
    url_prefix='/it-projects',
    template_folder='templates'
)

# Routes removed - no HTML endpoints served by this blueprint


def init_app(app):
    """Inizializza il blueprint."""
    app.register_blueprint(bp)
