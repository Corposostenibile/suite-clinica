"""
Marketing Automation Blueprint
=============================

Integrazione Frame.io → Claude → Airtable:
- Webhook Frame.io (metadata.value.updated) per video approvati
- Verifica firma HMAC, GET dettagli file (API v2/v4), lettura trascrizione (Notes/Transcript)
- Generazione caption con Claude API (linee guida placeholder o da PDF)
- Creazione record in Airtable con Caption già compilata
"""

from flask import Blueprint

bp = Blueprint(
    "marketing_automation",
    __name__,
    url_prefix="/marketing-automation",
)


# Import routes per registrare le view
from . import routes  # noqa: E402, F401

def init_app(app):
    """Registra il blueprint e applica CSRF exempt al webhook."""
    app.register_blueprint(bp)

    from corposostenibile.extensions import csrf
    csrf.exempt(bp)

    app.logger.info("[Marketing Automation] Blueprint registered successfully")
