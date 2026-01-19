"""
Blueprint Recruiting - Sistema ATS completo con Onboarding
=========================================================

Gestisce l'intero processo di recruiting:
- Form builder per offerte di lavoro
- Sistema ATS con screening automatico
- Kanban configurabile per pipeline
- Modulo onboarding post-assunzione
"""

from flask import Blueprint

recruiting_bp = Blueprint(
    "recruiting",
    __name__,
    template_folder="templates",
    static_folder="static",
)

def init_app(app):
    """
    Inizializza e registra il blueprint recruiting.
    """
    # Import routes e componenti
    from . import routes, forms, ats, kanban, onboarding, api

    # Registra blueprint principale
    app.register_blueprint(recruiting_bp, url_prefix="/recruiting")

    # Registra CLI commands
    from .cli import recruiting_cli
    app.cli.add_command(recruiting_cli)

    # Configura ACL
    if hasattr(app, "acl"):
        app.acl.allow("admin", "recruiting:manage")
        app.acl.allow("hr", "recruiting:manage")
        app.acl.allow("hr", "recruiting:view")
        app.acl.allow("manager", "recruiting:view")
        # Permessi per dipartimento HR (ID 17)
        app.acl.allow("department_17", "recruiting:manage")
        app.acl.allow("department_17", "recruiting:view")
        # Permessi per dipartimento 19
        app.acl.allow("department_19", "recruiting:manage")
        app.acl.allow("department_19", "recruiting:view")
        app.logger.debug("[recruiting] ACL rules registered")

    # Registra helper per context processor (verifica accesso recruiting)
    @app.context_processor
    def recruiting_helpers():
        """Helper per verificare accesso recruiting nei template."""
        def can_access_recruiting(user):
            if not user or not user.is_authenticated:
                return False
            # Admin ha sempre accesso
            if user.is_admin:
                return True
            # Membri dipartimento 17 (HR) hanno accesso
            if user.department_id == 17:
                return True
            # Membri dipartimento 19 hanno accesso
            if user.department_id == 19:
                return True
            return False

        return dict(can_access_recruiting=can_access_recruiting)

    app.logger.info("[recruiting] Blueprint initialized")