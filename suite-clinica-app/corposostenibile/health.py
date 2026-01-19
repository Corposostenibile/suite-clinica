"""
Health check endpoint per monitoraggio applicazione
"""
from flask import Blueprint, jsonify
from corposostenibile.extensions import db
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
        db.session.execute('SELECT 1')
        db.session.remove()
        status['services']['database'] = 'ok'
    except Exception as e:
        status['status'] = 'unhealthy'
        status['services']['database'] = f'error: {str(e)}'
    
    # Check Redis (only if configured)
    redis_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    if redis_url:
        try:
            # Parse Redis URL
            if redis_url.startswith('redis://'):
                host = redis_url.split('//')[1].split(':')[0]
                port = int(redis_url.split(':')[-1].split('/')[0])
            else:
                host = 'localhost'
                port = 6379
                
            r = redis.Redis(host=host, port=port, decode_responses=True, socket_connect_timeout=1)
            r.ping()
            status['services']['redis'] = 'ok'
        except Exception as e:
            # Redis is optional, so don't mark as unhealthy
            status['services']['redis'] = f'warning: {str(e)}'
    
    # Return appropriate status code
    status_code = 200 if status['status'] == 'healthy' else 503
    
    return jsonify(status), status_code