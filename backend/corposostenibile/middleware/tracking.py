"""
Middleware per tracking automatico attività blueprint
"""
import time
from datetime import datetime
from flask import g, request
from flask_login import current_user
from corposostenibile.extensions import db
from corposostenibile.models import GlobalActivityLog
from sqlalchemy import insert


def setup_tracking_middleware(app):
    """Configura il tracking automatico per tutti i blueprint."""

    @app.before_request
    def start_timer():
        """Salva il tempo di inizio richiesta."""
        g.start_time = time.time()

    @app.after_request
    def track_request(response):
        """Traccia automaticamente ogni richiesta ai blueprint."""
        # Solo se abbiamo un blueprint
        if not request.blueprint:
            return response

        # Skip per blueprint che non vogliamo tracciare
        skip_blueprints = ['static', 'pwa', 'health']
        if request.blueprint in skip_blueprints:
            return response

        # Calcola response time
        response_time_ms = None
        if hasattr(g, 'start_time'):
            response_time_ms = int((time.time() - g.start_time) * 1000)

        # Ottieni user_id
        user_id = current_user.id if current_user.is_authenticated else None

        # Salva log (in modo asincrono per non rallentare la response)
        try:
            # Usa una transazione separata dalla sessione della request:
            # se la request è in stato aborted, il tracking resta funzionante.
            payload = {
                "user_id": user_id,
                "blueprint": request.blueprint,
                "action_type": request.endpoint,
                "http_method": request.method,
                "http_status": response.status_code,
                "response_time_ms": response_time_ms,
                "ip_address": request.remote_addr,
                "user_agent": request.headers.get('User-Agent', '')[:255],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            with db.engine.begin() as conn:
                conn.execute(insert(GlobalActivityLog.__table__).values(**payload))
        except Exception as e:
            # Non interrompere la request se il logging fallisce
            app.logger.warning(f"Failed to log activity: {e}")

        return response
