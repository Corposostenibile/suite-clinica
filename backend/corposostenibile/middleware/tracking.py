"""
Middleware per tracking automatico attività blueprint e monitoraggio performance.

Ogni richiesta viene:
- misurata in millisecondi (via flask.g)
- salvata su DB nella tabella GlobalActivityLog
- loggata su console/file se supera la soglia SLOW_REQUEST_THRESHOLD_MS
  o se restituisce un errore HTTP 5xx

La soglia è configurabile in config.py (default 1000ms) e sovrascrivibile
via variabile d'ambiente SLOW_REQUEST_THRESHOLD_MS.
"""
import logging
import time
from datetime import datetime

from flask import g, request
from flask_login import current_user
from sqlalchemy import insert

from corposostenibile.extensions import db
from corposostenibile.models import GlobalActivityLog

logger = logging.getLogger("perf")

# Blueprint che non ha senso tracciare (asset statici, health check, PWA manifest)
_SKIP_BLUEPRINTS = frozenset({"static", "pwa", "health"})


def setup_tracking_middleware(app):
    """Configura il tracking automatico e il logging delle richieste lente."""

    @app.before_request
    def _start_timer():
        """Registra il timestamp di inizio su flask.g.

        flask.g è un namespace che vive esattamente per la durata di una
        singola richiesta: viene creato fresco ad ogni request e distrutto
        dopo teardown_request. È il modo idiomatico Flask per passare dati
        tra before_request e after_request senza usare variabili globali.
        """
        g.start_time = time.monotonic()

    @app.after_request
    def _track_request(response):
        """Misura il tempo, logga le richieste lente/errate e salva su DB.

        Viene eseguito dopo ogni endpoint, riceve la Response e deve
        restituirla (eventualmente modificata). Non deve mai sollevare
        eccezioni: un errore qui non deve bloccare la risposta al client.
        """
        try:
            # Calcola durata in ms con monotonic (non risente dei salti di orologio)
            elapsed_ms: int | None = None
            if hasattr(g, "start_time"):
                elapsed_ms = int((time.monotonic() - g.start_time) * 1000)

            blueprint = request.blueprint

            # --- Log su console/file -----------------------------------------
            # Logga sempre gli errori server (5xx) e le richieste lente,
            # indipendentemente dal blueprint. Questo è separato dal salvataggio
            # su DB e funziona anche se il DB è irraggiungibile.
            threshold_ms = app.config.get("SLOW_REQUEST_THRESHOLD_MS", 1000)

            if elapsed_ms is not None:
                is_slow = elapsed_ms > threshold_ms
                is_server_error = response.status_code >= 500

                if is_slow or is_server_error:
                    log_level = logging.ERROR if is_server_error else logging.WARNING
                    label = "SERVER_ERROR" if is_server_error else "SLOW_REQUEST"
                    logger.log(
                        log_level,
                        "%s  endpoint=%-45s  method=%s  status=%d  duration_ms=%d",
                        label,
                        request.endpoint or request.path,
                        request.method,
                        response.status_code,
                        elapsed_ms,
                    )

            # --- Salvataggio su DB -------------------------------------------
            # Salta blueprint irrilevanti (static, pwa, health)
            if not blueprint or blueprint in _SKIP_BLUEPRINTS:
                return response

            user_id = current_user.id if current_user.is_authenticated else None

            payload = {
                "user_id": user_id,
                "blueprint": blueprint,
                "action_type": request.endpoint,
                "http_method": request.method,
                "http_status": response.status_code,
                "response_time_ms": elapsed_ms,
                "ip_address": request.remote_addr,
                "user_agent": request.headers.get("User-Agent", "")[:255],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            # Usa una connessione separata dalla sessione della request:
            # se la request è in stato aborted (rollback), il tracking resta
            # funzionante perché opera su una transazione indipendente.
            with db.engine.begin() as conn:
                conn.execute(insert(GlobalActivityLog.__table__).values(**payload))

        except Exception as exc:
            try:
                db.session.rollback()
            except Exception:
                pass
            # Il tracking non deve mai bloccare la response al client
            app.logger.warning("Failed to log activity: %s", exc)

        return response
