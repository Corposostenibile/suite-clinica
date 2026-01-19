"""
blueprints.department
=====================

Blueprint per la gestione dei **reparti** aziendali.

• URL-prefix: ``/departments``  
• ACL: la permission ``department:manage`` è concessa agli *admin*
"""

from __future__ import annotations

from flask import Blueprint

# ────────────────────────────────────────────────────────────────────────────
#  Istanza Blueprint
# ────────────────────────────────────────────────────────────────────────────
dept_bp = Blueprint(
    "department",
    __name__,
    template_folder="templates",
    static_folder="static",
)

# ────────────────────────────────────────────────────────────────────────────
#  Factory-helper (richiamato dall'application-factory)
# ────────────────────────────────────────────────────────────────────────────
def init_app(app):  # noqa: D401
    """
    Registra il blueprint e configura l'ACL.

    Chiamato da ``corposostenibile/__init__.py``.
    """
    # Mount del blueprint
    app.register_blueprint(dept_bp, url_prefix="/departments")

    # ACL – gli *admin* possono gestire i reparti
    if hasattr(app, "acl") and not app.acl.permitted("admin", "department:manage"):
        app.acl.allow("admin", "department:manage")
        app.logger.debug(               # ← usa *app*, non *current_app*
            "[department] ACL rule registered (admin → department:manage)"
        )

    # Registra i filtri template personalizzati
    from .helpers import register_template_filters
    register_template_filters(app)

# ────────────────────────────────────────────────────────────────────────────
#  Import delle route (deve restare *in fondo*)
# ────────────────────────────────────────────────────────────────────────────
from . import routes, okr_routes, team_routes  # noqa: E402,F401