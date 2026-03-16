"""Security module for GHL webhook verification."""

import hashlib
import hmac
import os
from functools import wraps

from flask import abort, current_app, request


def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    """
    Verifica la firma HMAC del webhook per garantire che provenga da GHL

    Args:
        payload: Il body del webhook come stringa
        signature: La firma fornita nell'header del webhook
        secret: Il secret condiviso con GHL

    Returns:
        True se la firma è valida, False altrimenti
    """
    if not signature or not secret:
        return False

    # Calcola la firma attesa
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    # Confronto sicuro contro timing attacks
    return hmac.compare_digest(expected_signature, signature)


def _is_signature_verification_optional() -> bool:
    """
    In ambienti locali/shared di sviluppo il secret puo' non essere configurato.

    Il VPS DuckDNS usa ``FLASK_ENV=development`` ma gira con ``debug`` disattivato,
    quindi non possiamo affidarci solo a ``current_app.debug``.
    """
    env_name = str(
        current_app.config.get("FLASK_ENV")
        or current_app.config.get("ENV")
        or os.getenv("FLASK_ENV")
        or ""
    ).strip().lower()

    return bool(
        current_app.testing
        or current_app.debug
        or current_app.config.get("TESTING")
        or current_app.config.get("DEBUG")
        or env_name in {"development", "testing"}
    )


def require_webhook_signature(f):
    """
    Decorator che richiede una firma webhook valida
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Ottieni il secret dalla configurazione
        secret = current_app.config.get('GHL_WEBHOOK_SECRET')

        # Se non c'è secret configurato in development, logga warning ma procedi
        if not secret:
            if _is_signature_verification_optional():
                current_app.logger.warning(
                    '[GHL Security] No webhook secret configured - skipping verification (DEV MODE)'
                )
                return f(*args, **kwargs)
            else:
                current_app.logger.error('[GHL Security] No webhook secret configured')
                abort(500, description="Webhook secret not configured")

        # Ottieni la firma dall'header
        signature = request.headers.get('X-GHL-Signature') or request.headers.get('X-Webhook-Signature')

        # Ottieni il payload raw
        payload = request.get_data(as_text=True)

        # Verifica la firma
        if not verify_webhook_signature(payload, signature, secret):
            current_app.logger.warning(
                f'[GHL Security] Invalid webhook signature from IP: {request.remote_addr}'
            )
            abort(401, description="Invalid webhook signature")

        return f(*args, **kwargs)

    return decorated_function


def require_permission(permission):
    """
    Decorator che richiede un permesso specifico per accedere all'endpoint
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask_login import current_user

            if not current_user.is_authenticated:
                abort(401)

            # Check if user has permission
            if hasattr(current_app, 'acl'):
                if not current_app.acl.check(current_user.role, permission):
                    abort(403, description=f"Permission denied: {permission}")

            return f(*args, **kwargs)
        return decorated_function
    return decorator


class WebhookRateLimiter:
    """
    Limita il rate di webhook per prevenire abusi
    """
    def __init__(self, max_requests=100, window_seconds=60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}

    def is_allowed(self, identifier: str) -> bool:
        """
        Controlla se una richiesta è permessa basandosi sul rate limit
        """
        import time
        now = time.time()

        # Pulisci vecchie entries
        self.requests = {
            k: v for k, v in self.requests.items()
            if now - v < self.window_seconds
        }

        # Conta richieste nell'ultima finestra temporale
        count = sum(1 for t in self.requests.values() if now - t < self.window_seconds)

        if count >= self.max_requests:
            return False

        # Aggiungi questa richiesta
        self.requests[f"{identifier}_{now}"] = now
        return True


# Istanza globale del rate limiter
rate_limiter = WebhookRateLimiter()
