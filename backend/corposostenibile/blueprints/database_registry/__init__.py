"""Database Registry - Analisi e Statistics modelli DB"""
from flask import Blueprint

bp = Blueprint('database_registry', __name__, url_prefix='/database-registry',
               template_folder='templates', static_folder='static')

from . import routes  # noqa


def init_app(app):
    """Inizializza il blueprint."""
    app.register_blueprint(bp)
