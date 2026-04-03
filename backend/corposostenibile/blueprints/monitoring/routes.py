"""
monitoring/routes.py
===================
API endpoints per la dashboard di monitoring.
Accessibili solo da utenti admin.

Miglioramenti:
- Utilizza Cloud Logging API nativa (più veloce)
- Caching Redis per ridurre chiamate API
- Recupera tutti i dati senza limiti di campionamento
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
    GET /api/monitoring/metrics?days=7&include_static=0&per_day_limit=0&use_cache=1&cache_ttl=300
    
    Usa Cloud Logging API nativa per recuperare TUTTI i dati senza limiti di campionamento.
    
    Parametri:
    - days: 1-30 (default 7)
    - include_static: 0/1 (default 0)
    - per_day_limit: 0 (tutti i dati) o 100-50000 (default 0 = tutti i dati)
    - use_cache: 0/1 (default 1, usa Redis cache)
    - cache_ttl: 60-3600 (default 300 secondi = 5 minuti)
    
    Metriche fornite:
    1. Numero di chiamate medie al giorno per API
    2. Tempo medio per la chiamata API
    3. Numero medio di chiamate in fascia oraria per API
    4. Numero medio di chiamate in giornata per API (lun, mar, mer, ecc.)
    """
    _require_admin()

    days           = request.args.get('days', 7, type=int)
    include_static = request.args.get('include_static', 0, type=int)
    per_day_limit  = request.args.get('per_day_limit', 10000, type=int)
    use_cache      = request.args.get('use_cache', 1, type=int)
    cache_ttl      = request.args.get('cache_ttl', 300, type=int)

    # Validazione
    days          = min(max(days, 1), 30)
    # per_day_limit=0 significa "tutti i dati" (nessun limite)
    if per_day_limit != 0:
        per_day_limit = min(max(per_day_limit, 100), 50000)  # Limite massimo 50k per giorno
    cache_ttl     = min(max(cache_ttl, 60), 3600)

    data = get_monitoring_data(
        days=days,
        include_static=bool(include_static),
        per_day_limit=per_day_limit,
        use_cache=bool(use_cache),
        cache_ttl=cache_ttl,
    )
    
    # Aggiungi header cache per il browser
    response = jsonify(data)
    if use_cache:
        response.headers['Cache-Control'] = f'public, max-age={cache_ttl}'
    else:
        response.headers['Cache-Control'] = 'no-store'
    
    return response


@bp.route('/infrastructure', methods=['GET'])
@login_required
def get_infrastructure():
    """
    GET /api/monitoring/infrastructure?use_cache=1&cache_ttl=60
    
    Metriche infrastrutturali in tempo reale (Kubernetes API).
    
    Parametri:
    - use_cache: 0/1 (default 1, usa Redis cache)
    - cache_ttl: 10-300 (default 60 secondi)
    """
    _require_admin()
    
    use_cache = request.args.get('use_cache', 1, type=int)
    cache_ttl = request.args.get('cache_ttl', 60, type=int)
    
    cache_ttl = min(max(cache_ttl, 10), 300)
    
    data = get_infrastructure_data(
        use_cache=bool(use_cache),
        cache_ttl=cache_ttl
    )
    
    # Aggiungi header cache per il browser
    response = jsonify(data)
    if use_cache:
        response.headers['Cache-Control'] = f'public, max-age={cache_ttl}'
    else:
        response.headers['Cache-Control'] = 'no-store'
    
    return response
