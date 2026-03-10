"""
Marketing Automation Blueprint
=============================

Integrazione Frame.io → Airtable:
- Webhook Frame.io (metadata.value.updated) per video approvati
- Verifica firma HMAC, GET dettagli file (API v2/v4)
- Creazione record in Airtable; l’AI di Airtable (automation Generate with AI) genera la caption
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
