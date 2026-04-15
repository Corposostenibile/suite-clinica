"""
blueprints.it_support
=====================

Sistema di ticketing IT con sync bidirezionale verso ClickUp.

Gli utenti della Suite aprono ticket da una pagina dedicata accessibile dal
SupportWidget. I ticket vengono replicati come Task su ClickUp (List dedicata
del team IT); stato e commenti sono sincronizzati bidirezionalmente.

Blueprint:
- ``it_support_bp``      → ``/api/it-support``   (REST API, auth richiesta)
- ``it_support_hooks_bp`` → ``/webhooks/clickup`` (CSRF exempt, HMAC-verified)
"""

from __future__ import annotations

from flask import Blueprint

it_support_bp = Blueprint("it_support", __name__)
it_support_hooks_bp = Blueprint("it_support_hooks", __name__)


def init_app(app):
    """Registra i blueprint, CSRF exempt sul webhook, ACL minimale."""
    app.register_blueprint(it_support_bp, url_prefix="/api/it-support")
    app.register_blueprint(it_support_hooks_bp, url_prefix="/webhooks")

    # CSRF exempt
    from corposostenibile.extensions import csrf
    try:
        csrf.exempt(it_support_hooks_bp)
        csrf.exempt(it_support_bp)  # API JSON autenticata via cookie session + Bearer
    except Exception:
        app.logger.warning("[it_support] impossibile esentare CSRF, verifica configurazione")

    # ACL
    if hasattr(app, "acl"):
        acl = app.acl
        acl.allow("admin", "it_support:manage_all")
        acl.allow("admin", "it_support:view_all")
        # Ogni utente autenticato può aprire/vedere i propri ticket:
        # gestito inline nelle route.

    # CLI commands (flask it-support ...)
    from .cli import register_cli_commands
    register_cli_commands(app)

    app.logger.info("[it_support] Blueprint registered (prefix /api/it-support)")


# Import routes + tasks Celery (in fondo per evitare import circolari)
from . import routes, webhooks, tasks  # noqa: E402,F401
