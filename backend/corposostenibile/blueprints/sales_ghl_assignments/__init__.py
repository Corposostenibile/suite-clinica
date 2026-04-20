"""Sales GHL assignments blueprint.

Questo package espone:
- `bp` → `/api/ghl-assignments` (lista SalesLead provenienti da GHL)
- `sales_ghl_hooks_bp` → `/webhooks/ghl-leads/new` (webhook inbound HMAC)

La sorgente dati canonica è `SalesLead` con `source_system='ghl'`.
"""

from __future__ import annotations

from flask import Blueprint

bp = Blueprint(
    "sales_ghl_assignments",
    __name__,
    template_folder="templates",
    url_prefix="/api/ghl-assignments",
)

sales_ghl_hooks_bp = Blueprint(
    "sales_ghl_assignments_hooks",
    __name__,
    url_prefix="/webhooks",
)


# Import routes/hooks after blueprint creation to avoid circular imports
from . import routes, hooks  # noqa: E402,F401


def init_app(app):
    """Registra i blueprint Sales GHL."""
    app.register_blueprint(bp)
    app.register_blueprint(sales_ghl_hooks_bp)

    # CSRF exempt — API + webhook HMAC
    from corposostenibile.extensions import csrf
    try:
        csrf.exempt(bp)
        csrf.exempt(sales_ghl_hooks_bp)
    except Exception:
        app.logger.warning(
            "[sales_ghl_assignments] impossibile esentare CSRF, verifica configurazione"
        )

    app.logger.info(
        "[sales_ghl_assignments] Blueprint registered successfully (prefix /api/ghl-assignments, /webhooks/ghl-leads/new)"
    )
