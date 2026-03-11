"""
Old Suite Integration Blueprint (TEMPORANEO)
=============================================

Gestisce l'integrazione temporanea con la vecchia suite CRM
(suite.corposostenibile.com) fino a quando GHL non sarà operativo.

- Webhook receiver per lead.pending_assignment e lead.check_completed
- API per il frontend Assegnazioni Old Suite
- Conversione lead → cliente al momento dell'assegnazione
"""

from flask import Blueprint

bp = Blueprint(
    'old_suite_integration',
    __name__,
    url_prefix='/old-suite'
)

# Import routes after blueprint creation to avoid circular imports
from . import routes  # noqa: F401, E402

def init_app(app):
    """Initialize Old Suite integration with app"""
    app.register_blueprint(bp)
    app.logger.info('[Old Suite Integration] Blueprint registered successfully (TEMPORANEO)')
