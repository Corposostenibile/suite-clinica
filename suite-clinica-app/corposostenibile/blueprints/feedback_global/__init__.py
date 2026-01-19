"""
Feedback Global Blueprint - Sistema feedback democratico per tutti gli utenti.

FASE 1: Form globali per suggerire idee e segnalare problemi
FASE 2: Dashboard contributi personali + email notifications con motivazioni

Permette a TUTTI gli utenti di contribuire al miglioramento della suite
selezionando il modulo di destinazione.
"""
from flask import Blueprint

bp = Blueprint(
    'feedback_global',
    __name__,
    url_prefix='/feedback',
    template_folder='templates',
    static_folder='static'
)

# Import routes per registrarle
from . import routes  # noqa


def init_app(app):
    """Inizializza il blueprint nell'app Flask."""
    app.register_blueprint(bp)
    app.logger.info('[feedback_global] Blueprint registered - Democratic feedback system enabled')
