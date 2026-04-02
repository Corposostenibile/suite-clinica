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
    GET /api/monitoring/metrics?days=7&include_static=0&limit=10000

    Ritorna tutte le metriche aggregate:
    - endpoints: lista con avg/day, latenza, distribuzione oraria/settimanale
    - errors: log errori raggruppati
    - classificazione: internal vs external_call
    """
    _require_admin()

    days = request.args.get('days', 7, type=int)
    include_static = request.args.get('include_static', 0, type=int)
    limit = request.args.get('limit', 2000, type=int)

    # Limiti di sicurezza
    days = min(max(days, 1), 30)
    limit = min(max(limit, 100), 10000)

    data = get_monitoring_data(
        days=days,
        include_static=bool(include_static),
        max_entries=limit,
    )
    return jsonify(data)


@bp.route('/infrastructure', methods=['GET'])
@login_required
def get_infrastructure():
    """
    GET /api/monitoring/infrastructure

    Ritorna metriche infrastrutturali live:
    - pods_metrics: CPU e memoria per pod (kubectl top pods)
    - nodes_metrics: CPU e memoria per nodo (kubectl top nodes)
    - hpa: stato HPA (min/max replicas, CPU/memory %)
    - deployment: info deployment (replicas, strategy, image, resources)
    - pods_status: stato dei pod (ready, restarts, phase)
    - cloud_sql: info Cloud SQL (tier, disk, version, state)
    """
    _require_admin()
    data = get_infrastructure_data()
    return jsonify(data)
