"""
Blueprint per la gestione dei progetti di sviluppo aziendale.
"""
from flask import Blueprint

bp = Blueprint(
    'projects', 
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/static/projects'
)

from . import routes


def init_app(app):
    """Inizializza il blueprint projects nell'app Flask."""
    app.register_blueprint(bp, url_prefix='/projects')