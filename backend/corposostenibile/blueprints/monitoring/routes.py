"""
monitoring/routes.py
====================
API endpoints per la dashboard di monitoring.
Accessibili solo da utenti admin.
"""
from flask import jsonify, request, abort
from flask_login import login_required, current_user

from corposostenibile.blueprints.monitoring import bp
from corposostenibile.blueprints.monitoring.service import (
    get_monitoring_data,
    get_infrastructure_data,
)


def _require_admin() -> None:
    if not getattr(current_user, 'is_admin', False):
        abort(403, 'Accesso riservato agli amministratori')


@bp.route('/metrics', methods=['GET'])
@login_required
def get_metrics():
    """
    GET /api/monitoring/metrics?days=7&include_static=0&per_day_limit=300

    Fetch parallelo per giorno (un thread per giorno), 300 entry/giorno di campione.
    """
    _require_admin()

    days          = request.args.get('days', 7, type=int)
    include_static = request.args.get('include_static', 0, type=int)
    per_day_limit = request.args.get('per_day_limit', 300, type=int)

    days          = min(max(days, 1), 30)
    per_day_limit = min(max(per_day_limit, 50), 2000)

    data = get_monitoring_data(
        days=days,
        include_static=bool(include_static),
        per_day_limit=per_day_limit,
    )
    return jsonify(data)


@bp.route('/infrastructure', methods=['GET'])
@login_required
def get_infrastructure():
    """GET /api/monitoring/infrastructure"""
    _require_admin()
    data = get_infrastructure_data()
    return jsonify(data)
