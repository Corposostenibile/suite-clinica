"""Blueprint alias per le assegnazioni GHL Sales.

Espone un endpoint pubblico/consumabile sotto `/api/ghl-assignments`
che riusa la stessa sorgente dati di `ghl_integration` per la lista delle
assegnazioni GHL.
"""

from __future__ import annotations

from flask import Blueprint

bp = Blueprint(
    "sales_ghl_assignments",
    __name__,
    template_folder="templates",
    url_prefix="/api/ghl-assignments",
)


# Import routes after blueprint creation to avoid circular imports
from . import routes  # noqa: E402,F401


def init_app(app):
    """Registra il blueprint alias per le assegnazioni GHL Sales."""
    app.register_blueprint(bp)
    app.logger.info("[sales_ghl_assignments] Blueprint registered successfully")
