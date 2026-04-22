"""SSO JWT adapter sales per il blueprint sales_ghl_assignments.

Questo adapter consente ai sales di entrare nella Suite tramite GHL usando
un JWT HS256 firmato dal backend.

Flusso:
1. GHL passa l'email del sales nel link/menu custom.
2. Il backend risolve l'utente via match esatto su `User.email`.
3. Viene emesso un JWT con `scope='sales'` e `sales_user_id`.
4. Le API sales possono accettare sia JWT Bearer sia sessione Flask-Login.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable, Dict, Optional

import jwt as pyjwt
from flask import abort, current_app, g, request
from flask_login import current_user
from sqlalchemy import func

from corposostenibile.extensions import db
from corposostenibile.models import User

logger = logging.getLogger(__name__)

SALES_SCOPE = "sales"
JWT_ISSUER = "suite-clinica-sales-ghl"
JWT_LIFETIME_HOURS = 8


@dataclass
class SalesSessionUser:
    """Contesto utente sales valido per la sessione GHL."""

    sales_user_id: int
    email: Optional[str]
    name: Optional[str]
    role: Optional[str]
    scope: str = SALES_SCOPE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sales_user_id": self.sales_user_id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "scope": self.scope,
        }


def _get_signing_key() -> str:
    secret = current_app.config.get("GHL_SSO_SIGNING_KEY") or current_app.secret_key
    if not secret:
        raise RuntimeError("Nessuna chiave di firma: imposta GHL_SSO_SIGNING_KEY o SECRET_KEY")
    return secret


def _normalize_email(email: str | None) -> Optional[str]:
    if not email:
        return None
    normalized = email.strip().lower()
    return normalized or None


def resolve_sales_user_by_email(email: str | None) -> Optional[User]:
    """Risoluzione exact-match dell'utente sales tramite email normalizzata."""
    normalized = _normalize_email(email)
    if not normalized:
        return None
    return User.query.filter(
        func.lower(User.email) == normalized,
        User.is_active == True,  # noqa: E712
    ).first()


def build_sales_session_user(user: User) -> SalesSessionUser:
    return SalesSessionUser(
        sales_user_id=int(user.id),
        email=_normalize_email(user.email),
        name=user.full_name,
        role=getattr(user.role, "value", user.role),
    )


def create_sales_jwt(user: User) -> str:
    """Firma un JWT HS256 per un utente sales risolto via email."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "user_id": int(user.id),
        "sales_user_id": int(user.id),
        "email": _normalize_email(user.email),
        "name": user.full_name,
        "role": getattr(user.role, "value", user.role),
        "scope": SALES_SCOPE,
        "iss": JWT_ISSUER,
        "iat": now,
        "exp": now + timedelta(hours=JWT_LIFETIME_HOURS),
    }
    token = pyjwt.encode(payload, _get_signing_key(), algorithm="HS256")
    return token if isinstance(token, str) else token.decode("utf-8")


def _decode_sales_jwt(token: str) -> SalesSessionUser:
    payload = pyjwt.decode(
        token,
        _get_signing_key(),
        algorithms=["HS256"],
        issuer=JWT_ISSUER,
    )
    if (payload.get("scope") or "").strip().lower() != SALES_SCOPE:
        raise pyjwt.InvalidTokenError("scope non valido")

    sales_user_id = payload.get("sales_user_id") or payload.get("user_id")
    if not sales_user_id:
        raise pyjwt.InvalidTokenError("sales_user_id mancante")

    return SalesSessionUser(
        sales_user_id=int(sales_user_id),
        email=_normalize_email(payload.get("email")),
        name=(payload.get("name") or None),
        role=(payload.get("role") or None),
    )


def sales_assignments_auth_required(permission: str = "ghl:view_assignments"):
    """Autenticazione per la queue sales.

    Accetta:
    - Bearer JWT sales (GHL SSO)
    - Sessione Flask autenticata con permesso ACL legacy
    """

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            auth_header = (request.headers.get("Authorization") or "").strip()
            if auth_header.lower().startswith("bearer "):
                token = auth_header[7:].strip()
                if not token:
                    abort(401, description="Token sales vuoto")
                try:
                    session_user = _decode_sales_jwt(token)
                except pyjwt.ExpiredSignatureError:
                    abort(401, description="Token sales scaduto")
                except pyjwt.InvalidTokenError as exc:
                    logger.warning("[sales_ghl_assignments/sso] JWT invalido: %s", exc)
                    abort(401, description="Token sales non valido")

                sales_user = db.session.get(User, session_user.sales_user_id)
                if not sales_user or not sales_user.is_active:
                    abort(401, description="Utente sales non trovato o disattivato")

                g.sales_user = sales_user
                g.sales_auth_mode = "jwt"
                g.sales_session = session_user
                return fn(*args, **kwargs)

            if not current_user.is_authenticated:
                abort(401)

            if hasattr(current_app, "acl"):
                role = getattr(current_user.role, "value", current_user.role)
                acl = current_app.acl
                has_perm = False
                if hasattr(acl, "permitted"):
                    has_perm = acl.permitted(role, permission)
                elif hasattr(acl, "check"):
                    has_perm = acl.check(role, permission)
                elif hasattr(acl, "allow"):
                    has_perm = permission in getattr(acl, "rules", {}).get(role, set())
                if not has_perm:
                    abort(403, description=f"Permission denied: {permission}")

            g.sales_user = current_user
            g.sales_auth_mode = "session"
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def get_active_sales_user() -> Optional[User]:
    """Ritorna l'utente autenticato per la queue sales, se presente."""
    return getattr(g, "sales_user", None)
