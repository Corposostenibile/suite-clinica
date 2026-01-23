"""
Blueprint KPI - Sistema KPI e ARR
=================================

Gestisce:
- KPI Aziendali (Tasso Rinnovi, Tasso Referral)
- ARR (Adjusted Renewal Rate) per professionisti
- Dashboard e storico snapshot
"""

from flask import Blueprint, Flask

kpi_bp = Blueprint(
    'kpi',
    __name__,
    template_folder='templates',
    url_prefix='/kpi'
)

from . import routes  # noqa: F401, E402


def init_app(app: Flask) -> None:
    """Registra il blueprint KPI nell'app Flask."""
    app.register_blueprint(kpi_bp)
