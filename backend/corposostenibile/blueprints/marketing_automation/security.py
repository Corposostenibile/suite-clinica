"""
Verifica firma webhook Frame.io (V4).

Frame.io invia:
- X-Frameio-Request-Timestamp: timestamp epoca
- X-Frameio-Signature: firma HMAC SHA256 nel formato "v0=<hex_digest>"

Messaggio firmato: v0:{timestamp}:{body_raw}
"""

import hmac
import hashlib
from functools import wraps

from flask import request, abort, current_app


def verify_frameio_signature(body_raw: str, timestamp: str, signature: str, secret: str) -> bool:
    """
    Verifica la firma HMAC del webhook Frame.io.

    Args:
        body_raw: body della richiesta come stringa (JSON raw)
        timestamp: valore header X-Frameio-Request-Timestamp
        signature: valore header X-Frameio-Signature (formato v0=...)
        secret: webhook secret restituito alla creazione del webhook

    Returns:
        True se la firma è valida.
    """
    if not signature or not secret:
        return False
    if not timestamp:
        return False

    message = f"v0:{timestamp}:{body_raw}"
    expected_hex = hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    expected_sig = f"v0={expected_hex}"

    return hmac.compare_digest(expected_sig, signature)


def require_frameio_webhook_signature(f):
    """Decorator che richiede firma webhook Frame.io valida."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        secret = current_app.config.get("FRAMEIO_WEBHOOK_SECRET")

        if not secret:
            if current_app.debug or current_app.config.get("FLASK_ENV") == "development":
                current_app.logger.warning(
                    "[Marketing Automation] FRAMEIO_WEBHOOK_SECRET non configurato - skip verifica (DEV)"
                )
                return f(*args, **kwargs)
            current_app.logger.error("[Marketing Automation] FRAMEIO_WEBHOOK_SECRET mancante")
            abort(500, description="Webhook secret not configured")

        timestamp = request.headers.get("X-Frameio-Request-Timestamp")
        signature = request.headers.get("X-Frameio-Signature")
        body = request.get_data(as_text=True)

        if not verify_frameio_signature(body, timestamp or "", signature or "", secret):
            current_app.logger.warning(
                f"[Marketing Automation] Firma webhook Frame.io non valida da {request.remote_addr}"
            )
            abort(401, description="Invalid webhook signature")

        return f(*args, **kwargs)

    return decorated_function
