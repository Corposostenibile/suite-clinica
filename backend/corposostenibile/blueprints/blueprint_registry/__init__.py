"""Blueprint Registry - Governance e Tracking Blueprint"""
from flask import Blueprint

bp = Blueprint('blueprint_registry', __name__, url_prefix='/blueprint-registry',
               template_folder='templates', static_folder='static')

# Routes removed - no HTML endpoints served by this blueprint
from . import api, metrics  # noqa


def init_app(app):
    """Inizializza il blueprint."""
    app.register_blueprint(bp)
