"""
blueprints.ghl_support
======================

Sistema di ticketing IT aperto dall'interno di GoHighLevel tramite Custom Menu
Link (iframe embedded). I ticket vengono replicati come Task su ClickUp
(workspace dedicato "Go High Level - Ticket"); stato e commenti sono
sincronizzati bidirezionalmente.

Identità utente: NON c'è login Suite. L'utente GHL è identificato dai
placeholder passati in query string al Custom Menu Link (user.id, user.email,
location.id, …) e validato tramite JWT HS256 di sessione (vedi `embed.py`).

Blueprint:
- ``ghl_support_bp``        → ``/api/ghl-support``   (REST API, JWT richiesta)
- ``ghl_support_hooks_bp``  → ``/webhooks/clickup-ghl`` (HMAC)

Il frontend React serve la pagina iframe (route ``/ghl-embed/tickets``), legge
i placeholder GHL dal query string, chiama ``POST /api/ghl-support/sso/exchange``
per ottenere un JWT di sessione, e lo salva in sessionStorage.
"""

from __future__ import annotations

from flask import Blueprint

ghl_support_bp = Blueprint("ghl_support", __name__)
ghl_support_hooks_bp = Blueprint("ghl_support_hooks", __name__)


def init_app(app):
    """Registra i blueprint, CSRF exempt, CLI."""
    app.register_blueprint(ghl_support_bp, url_prefix="/api/ghl-support")
    app.register_blueprint(ghl_support_hooks_bp, url_prefix="/webhooks")

    # CSRF exempt — API JWT Bearer, webhook HMAC
    from corposostenibile.extensions import csrf
    try:
        csrf.exempt(ghl_support_bp)
        csrf.exempt(ghl_support_hooks_bp)
    except Exception:
        app.logger.warning(
            "[ghl_support] impossibile esentare CSRF, verifica configurazione"
        )

    # CLI commands (flask ghl-support ...)
    from .cli import register_cli_commands
    register_cli_commands(app)

    app.logger.info(
        "[ghl_support] Blueprint registered "
        "(prefix /api/ghl-support, /webhooks/clickup-ghl)"
    )


# Import routes + webhooks + tasks Celery (in fondo per evitare import circolari)
from . import routes, webhooks, tasks  # noqa: E402,F401
