"""Dev Tracker - Development Team Management & Sprint Tracking"""
from flask import Blueprint

bp = Blueprint(
    'dev_tracker',
    __name__,
    url_prefix='/dev-tracker',
    template_folder='templates',
    static_folder='static'
)

from . import routes  # noqa


def init_app(app):
    """Inizializza il blueprint."""
    app.register_blueprint(bp)
