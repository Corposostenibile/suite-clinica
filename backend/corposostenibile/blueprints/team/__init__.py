# corposostenibile/blueprints/team/__init__.py
from __future__ import annotations

from flask import Blueprint

team_bp = Blueprint(
    "team",
    __name__,
    static_folder="static",
)

# --------------------------------------------------------------------------- #
def init_app(app):  # noqa: D401
    """
    Collega blueprint, CLI e ACL all'app principale.
    Da invocare nella application-factory.
    """
    # 1️⃣ importa le view prima della registrazione
    from . import routes, forms, okr_routes, trial_routes, trial_api, anonymous_survey_routes, team_payments_routes   # noqa: F401,E402
    from .weekly_report_routes import weekly_report_bp   # noqa: F401,E402
    from .api import team_api_bp, users_api_bp   # noqa: F401,E402

    # 2️⃣ registra il blueprint principale
    app.register_blueprint(team_bp, url_prefix="/team")

    # 2️⃣.1 registra il sub-blueprint per i report settimanali
    app.register_blueprint(weekly_report_bp)

    # 2️⃣.2 registra il sub-blueprint API per React frontend
    app.register_blueprint(team_api_bp)
    app.register_blueprint(users_api_bp)

    # 3️⃣ CLI helper
    from .cli import team_cli     # noqa: F401,E402
    app.cli.add_command(team_cli)

    # 4️⃣ ACL (se l'app espone SimpleACL)
    if hasattr(app, "acl"):
        app.acl.allow("admin", "team:manage")        # type: ignore[attr-defined]
        app.logger.debug("[team] ACL rule registered (admin → team:manage)")
    
    # 5️⃣ Inizializza task schedulati per report settimanali
    with app.app_context():
        from corposostenibile.extensions import is_scheduler_available
        if is_scheduler_available():
            from .weekly_report_tasks import schedule_weekly_report_reminders
            try:
                schedule_weekly_report_reminders()
                app.logger.info("[team] Weekly report reminders scheduled")
            except Exception as e:
                app.logger.error(f"[team] Failed to schedule weekly report reminders: {e}")
