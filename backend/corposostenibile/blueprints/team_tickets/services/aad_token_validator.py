"""
aad_token_validator.py
======================
Validates Azure AD tokens for Teams Tab SSO authentication.
Fetches JWKS from Azure AD, caches keys, validates JWT signature + claims.
"""

from __future__ import annotations

import time
import logging
from typing import Any

import jwt
import requests
from flask import current_app

logger = logging.getLogger(__name__)

# ── JWKS cache ───────────────────────────────────────────────────────────────

_jwks_cache: dict[str, Any] = {"keys": None, "fetched_at": 0}
_JWKS_TTL = 3600  # 1 hour


def _get_jwks(tenant_id: str) -> dict:
    """Fetch JWKS from Azure AD, with caching."""
    now = time.time()
    if _jwks_cache["keys"] and (now - _jwks_cache["fetched_at"]) < _JWKS_TTL:
        return _jwks_cache["keys"]

    url = (
        f"https://login.microsoftonline.com/{tenant_id}"
        "/discovery/v2.0/keys"
    )
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    keys = resp.json()

    _jwks_cache["keys"] = keys
    _jwks_cache["fetched_at"] = now
    logger.info("[AAD] JWKS refreshed (%d keys)", len(keys.get("keys", [])))
    return keys


def _find_key(jwks: dict, kid: str) -> dict | None:
    """Find the signing key by kid."""
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


# ── Public API ───────────────────────────────────────────────────────────────

def validate_aad_token(token_str: str) -> dict:
    """
    Validate an AAD access token from Teams Tab SSO.

    Returns decoded payload with claims on success.
    Raises ValueError on any validation failure.
    """
    tenant_id = current_app.config.get("TEAMS_BOT_TENANT_ID", "")
    app_id = current_app.config.get("TEAMS_BOT_APP_ID", "")

    if not tenant_id or not app_id:
        raise ValueError("Teams bot config missing (TEAMS_BOT_TENANT_ID / TEAMS_BOT_APP_ID)")

    # Decode header to find kid
    try:
        unverified = jwt.get_unverified_header(token_str)
    except jwt.DecodeError as e:
        raise ValueError(f"Token malformato: {e}")

    kid = unverified.get("kid")
    if not kid:
        raise ValueError("Token manca il claim 'kid' nell'header")

    # Fetch JWKS and find the matching key
    jwks = _get_jwks(tenant_id)
    key_data = _find_key(jwks, kid)

    if not key_data:
        # Keys may have rotated — force refresh
        _jwks_cache["fetched_at"] = 0
        jwks = _get_jwks(tenant_id)
        key_data = _find_key(jwks, kid)
        if not key_data:
            raise ValueError(f"Chiave pubblica non trovata per kid={kid}")

    # Build public key
    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key_data)

    # Validate — audience can be the app ID or the app ID URI
    valid_audiences = [
        app_id,
        f"api://clinica.corposostenibile.com/{app_id}",
    ]

    issuer = f"https://sts.windows.net/{tenant_id}/"

    try:
        payload = jwt.decode(
            token_str,
            key=public_key,
            algorithms=["RS256"],
            audience=valid_audiences,
            issuer=issuer,
            options={"require": ["exp", "iss", "aud", "oid"]},
        )
    except jwt.ExpiredSignatureError:
        raise ValueError("Token scaduto")
    except jwt.InvalidAudienceError:
        raise ValueError("Audience non valida")
    except jwt.InvalidIssuerError:
        raise ValueError("Issuer non valido")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Token non valido: {e}")

    return payload
