"""
Health check endpoint per monitoraggio applicazione
"""
from flask import Blueprint, jsonify
from corposostenibile.extensions import db
from sqlalchemy import text
import redis
import os
from datetime import datetime

health_bp = Blueprint('health', __name__)

@health_bp.route('/health')
def health_check():
    """
    Endpoint per verificare lo stato dell'applicazione.
    Usato da Docker healthcheck e monitoring tools.
    """
    status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'services': {}
    }
    
    # Check database
    try:
        # SQLAlchemy 2.0 richiede l'uso di text() per query testuali
        db.session.execute(text('SELECT 1'))
        db.session.remove()
        status['services']['database'] = 'ok'
    except Exception as e:
        status['status'] = 'unhealthy'
        status['services']['database'] = f'error: {str(e)}'
    
    # Check Redis (only if configured)
    redis_url = os.getenv('CELERY_BROKER_URL')
    if redis_url:
        try:
            # Usa from_url che è più robusto del parsing manuale
            r = redis.Redis.from_url(redis_url, socket_connect_timeout=1)
            r.ping()
            status['services']['redis'] = 'ok'
        except Exception as e:
            # Redis is optional, so don't mark as unhealthy
            status['services']['redis'] = f'warning: {str(e)}'
    
    # Return appropriate status code
    status_code = 200 if status['status'] == 'healthy' else 503
    
    return jsonify(status), status_code