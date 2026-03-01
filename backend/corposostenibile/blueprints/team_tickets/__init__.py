"""
blueprints.team_tickets
=======================

Blueprint per il sistema ticket interno del team.
I manager gestiscono dalla Suite Amministrativa,
i membri del team interagiscono tramite Microsoft Teams bot.

- team_tickets_bp: ``/api/team-tickets`` (REST API per admin frontend)
- teams_bot_bp: ``/api/teams-bot`` (webhook Bot Framework, CSRF exempt)
"""

from __future__ import annotations

from flask import Blueprint

# ────────────────────────────────────────────────────────────────────────────
# Istanze Blueprint
# ────────────────────────────────────────────────────────────────────────────

# REST API per admin frontend
team_tickets_bp = Blueprint("team_tickets", __name__)

# Teams bot webhook (CSRF exempt)
teams_bot_bp = Blueprint("teams_bot", __name__)


# ────────────────────────────────────────────────────────────────────────────
# Factory-helper (richiamato dall'application-factory)
# ────────────────────────────────────────────────────────────────────────────

def init_app(app):
    """
    Registra i blueprint team_tickets e teams_bot.
    Chiamato da ``corposostenibile/__init__.py``.
    """
    app.register_blueprint(team_tickets_bp, url_prefix="/api/team-tickets")
    app.register_blueprint(teams_bot_bp, url_prefix="/api/teams-bot")

    # CSRF exempt per il webhook Teams
    from corposostenibile.extensions import csrf
    csrf.exempt(teams_bot_bp)

    app.logger.info("[team_tickets] Blueprint registered")


# ────────────────────────────────────────────────────────────────────────────
# Import delle route (deve restare *in fondo*)
# ────────────────────────────────────────────────────────────────────────────

from .routes import api_routes, bot_routes  # noqa: E402,F401
