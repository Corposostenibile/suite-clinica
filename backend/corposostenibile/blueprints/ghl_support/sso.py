"""
SSO lightweight per utenti GHL (Opzione A — Custom Menu Link).

Pattern:
1. Il Custom Menu Link GHL punta al frontend Suite con placeholder in query:
   https://<tunnel>/ghl-embed/tickets?user_id={{user.id}}&user_email=...&...
2. Il React embed page chiama POST /api/ghl-support/sso/exchange con i param.
3. Questo modulo valida i dati minimi e firma un JWT HS256 con
   GHL_SSO_SIGNING_KEY (lifetime 8 ore).
4. Tutte le API successive usano header Authorization: Bearer <jwt>.
   Il decorator `@ghl_session_required` valida il JWT e popola g.ghl_user.

Nota sicurezza: NON c'è verifica crittografica che la request arrivi davvero
da GHL. Un utente che conosce l'URL può spacciarsi per un altro. Adeguato
solo per staff interno fidato (come da requisito esplicito del progetto).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Dict, Optional

from flask import abort, current_app, g, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

logger = logging.getLogger(__name__)


SESSION_LIFETIME_SECONDS = 8 * 3600  # 8 ore
SALT = "ghl-support-session-v1"


@dataclass
class GHLSessionUser:
    """Contesto utente GHL attivo nella request corrente."""
    user_id: str
    email: Optional[str]
    name: Optional[str]
    role: Optional[str]
    location_id: Optional[str]
    location_name: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "location_id": self.location_id,
            "location_name": self.location_name,
        }


# ─── Token sign/verify ─────────────────────────────────────────────────────


def _get_serializer() -> URLSafeTimedSerializer:
    secret = (
        current_app.config.get("GHL_SSO_SIGNING_KEY")
        or current_app.config.get("SECRET_KEY")
    )
    if not secret:
        raise RuntimeError(
            "Nessuna chiave di firma: imposta GHL_SSO_SIGNING_KEY o SECRET_KEY"
        )
    return URLSafeTimedSerializer(secret, salt=SALT)


def create_session_token(ghl_user: GHLSessionUser) -> str:
    """Firma un token di sessione opaco dall'utente GHL validato."""
    return _get_serializer().dumps(ghl_user.to_dict())


def decode_session_token(token: str) -> Optional[GHLSessionUser]:
    """Decodifica + valida scadenza. Ritorna None se invalido/scaduto."""
    try:
        data = _get_serializer().loads(token, max_age=SESSION_LIFETIME_SECONDS)
    except SignatureExpired:
        logger.info("[ghl_support/sso] token scaduto")
        return None
    except BadSignature:
        logger.warning("[ghl_support/sso] token firma invalida")
        return None
    except Exception:
        logger.exception("[ghl_support/sso] errore decode token")
        return None

    if not isinstance(data, dict) or not data.get("user_id"):
        return None

    return GHLSessionUser(
        user_id=str(data.get("user_id")),
        email=data.get("email"),
        name=data.get("name"),
        role=data.get("role"),
        location_id=data.get("location_id"),
        location_name=data.get("location_name"),
    )


# ─── Exchange helper (usato da routes /sso/exchange) ───────────────────────


def build_user_from_query_params(payload: Dict[str, Any]) -> GHLSessionUser:
    """Valida e costruisce GHLSessionUser dai placeholder GHL."""
    user_id = (payload.get("user_id") or "").strip()
    if not user_id:
        abort(422, description="user_id obbligatorio")

    return GHLSessionUser(
        user_id=user_id,
        email=(payload.get("user_email") or "").strip() or None,
        name=(payload.get("user_name") or "").strip() or None,
        role=(payload.get("role") or "").strip() or None,
        location_id=(payload.get("location_id") or "").strip() or None,
        location_name=(payload.get("location_name") or "").strip() or None,
    )


# ─── Decorator per proteggere le API ───────────────────────────────────────


def ghl_session_required(fn: Callable) -> Callable:
    """
    Decorator: legge Authorization: Bearer <jwt>, valida, popola
    `g.ghl_user: GHLSessionUser`. 401 se token mancante/invalido.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = (request.headers.get("Authorization") or "").strip()
        if not auth_header.lower().startswith("bearer "):
            abort(401, description="Sessione GHL mancante")
        token = auth_header[7:].strip()
        if not token:
            abort(401, description="Token GHL vuoto")

        session_user = decode_session_token(token)
        if not session_user:
            abort(401, description="Sessione GHL invalida o scaduta")

        g.ghl_user = session_user
        return fn(*args, **kwargs)

    return wrapper
