"""API endpoints Blueprint Registry"""
from flask import jsonify, request
from flask_login import login_required
from corposostenibile.extensions import db
from corposostenibile.models import BlueprintRegistry
from . import bp
from .metrics import calculate_adoption_metrics, get_adoption_level, get_metrics_history_30d


@bp.route('/api/<string:code>/metrics')
@login_required
def api_metrics(code):
    """Ottieni metriche blueprint."""
    metrics = calculate_adoption_metrics(code)
    return jsonify(metrics)


@bp.route('/api/<string:code>/update-adoption', methods=['POST'])
@login_required
def api_update_adoption(code):
    """Aggiorna adoption level automaticamente."""
    blueprint = BlueprintRegistry.query.filter_by(code=code).first_or_404()

    metrics = calculate_adoption_metrics(code)
    adoption_level = get_adoption_level(metrics['adoption_rate'])

    blueprint.adoption_level = adoption_level
    blueprint.metrics = metrics

    db.session.commit()

    return jsonify({
        'success': True,
        'adoption_level': adoption_level,
        'metrics': metrics
    })


@bp.route('/api/<string:code>/metrics-history')
@login_required
def get_metrics_history(code):
    """Ottieni storico metriche ultimi 30 giorni per grafici."""
    history = get_metrics_history_30d(code)
    return jsonify(history)
