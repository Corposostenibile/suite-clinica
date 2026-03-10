"""
Blueprint per la gestione dei Rimborsi clienti.
"""

from flask import Blueprint

bp = Blueprint('rimborsi', __name__, url_prefix='/api/rimborsi')


def init_app(app):
    """Inizializza il blueprint rimborsi."""
    from . import routes  # noqa
    app.register_blueprint(bp)
    app.logger.info("[rimborsi] Blueprint registrato con successo")
