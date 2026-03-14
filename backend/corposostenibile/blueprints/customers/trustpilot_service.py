from __future__ import annotations

import base64
import secrets
import time
from datetime import datetime
from typing import Any
from uuid import uuid4

import requests
from flask import current_app


class TrustpilotConfigError(RuntimeError):
    """Errore di configurazione Trustpilot."""


class TrustpilotAPIError(RuntimeError):
    """Errore restituito da Trustpilot."""


class TrustpilotService:
    TOKEN_CACHE_KEY = "trustpilot_access_token"
    TOKEN_URL = "https://authenticate.trustpilot.com/v1/oauth/oauth-business-users-for-applications/accesstoken"
    API_BASE_URL = "https://invitations-api.trustpilot.com/v1/private/business-units"

    @classmethod
    def is_enabled(cls) -> bool:
        return bool(current_app.config.get("TRUSTPILOT_ENABLED"))

    @classmethod
    def get_default_locale(cls) -> str:
        return current_app.config.get("TRUSTPILOT_LOCALE_DEFAULT", "it-IT")

    @classmethod
    def ensure_enabled(cls) -> None:
        if not cls.is_enabled():
            raise TrustpilotConfigError("Integrazione Trustpilot non abilitata.")

    @classmethod
    def _require_config(cls, key: str) -> str:
        value = (current_app.config.get(key) or "").strip()
        if not value:
            raise TrustpilotConfigError(f"Configurazione Trustpilot mancante: {key}")
        return value

    @classmethod
    def _get_business_unit_id(cls) -> str:
        return cls._require_config("TRUSTPILOT_BUSINESS_UNIT_ID")

    @classmethod
    def _get_client_id(cls) -> str:
        return cls._require_config("TRUSTPILOT_API_KEY")

    @classmethod
    def _get_client_secret(cls) -> str:
        return cls._require_config("TRUSTPILOT_API_SECRET")

    @classmethod
    def _get_business_user_id(cls) -> str | None:
        value = (current_app.config.get("TRUSTPILOT_BUSINESS_USER_ID") or "").strip()
        return value or None

    @classmethod
    def _get_redirect_uri(cls) -> str | None:
        value = (current_app.config.get("TRUSTPILOT_REDIRECT_URI") or "").strip()
        return value or None

    @classmethod
    def _get_timeout(cls) -> int:
        return int(current_app.config.get("TRUSTPILOT_TIMEOUT_SECONDS", 20))

    @classmethod
    def _token_cache(cls) -> dict[str, Any]:
        return current_app.extensions.setdefault("trustpilot_oauth", {})

    @classmethod
    def _build_basic_auth(cls) -> str:
        credentials = f"{cls._get_client_id()}:{cls._get_client_secret()}".encode("utf-8")
        return base64.b64encode(credentials).decode("ascii")

    @classmethod
    def get_access_token(cls) -> str:
        cls.ensure_enabled()
        cache = cls._token_cache()
        now = int(time.time())
        cached_token = cache.get(cls.TOKEN_CACHE_KEY)
        cached_expiry = int(cache.get("expires_at") or 0)
        if cached_token and cached_expiry > now + 30:
            return cached_token

        response = requests.post(
            cls.TOKEN_URL,
            headers={
                "Authorization": f"Basic {cls._build_basic_auth()}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials"},
            timeout=cls._get_timeout(),
        )
        if not response.ok:
            raise TrustpilotAPIError(
                f"Errore OAuth Trustpilot: HTTP {response.status_code} - {response.text[:300]}"
            )

        payload = response.json()
        token = payload.get("access_token")
        expires_in = int(payload.get("expires_in") or 0)
        if not token:
            raise TrustpilotAPIError("Trustpilot non ha restituito access_token.")

        cache[cls.TOKEN_CACHE_KEY] = token
        cache["expires_at"] = now + max(expires_in - 60, 60)
        return token

    @classmethod
    def _build_headers(cls, include_business_user: bool = False) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {cls.get_access_token()}",
            "Content-Type": "application/json",
        }
        if include_business_user and cls._get_business_user_id():
            headers["x-business-user-id"] = cls._get_business_user_id()  # type: ignore[assignment]
        return headers

    @classmethod
    def _post(cls, path: str, payload: dict[str, Any], *, include_business_user: bool = False) -> dict[str, Any]:
        business_unit_id = cls._get_business_unit_id()
        response = requests.post(
            f"{cls.API_BASE_URL}/{business_unit_id}{path}",
            json=payload,
            headers=cls._build_headers(include_business_user=include_business_user),
            timeout=cls._get_timeout(),
        )
        if not response.ok:
            raise TrustpilotAPIError(
                f"Errore Trustpilot: HTTP {response.status_code} - {response.text[:400]}"
            )
        return response.json()

    @classmethod
    def generate_reference_id(cls, cliente_id: int) -> str:
        return f"sc-{cliente_id}-{secrets.token_hex(4)}-{uuid4().hex[:8]}"

    @classmethod
    def create_invitation_link(
        cls,
        *,
        email: str,
        name: str,
        reference_id: str,
        locale: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "referenceId": reference_id,
            "email": email,
            "name": name,
            "locale": locale or cls.get_default_locale(),
        }
        redirect_uri = cls._get_redirect_uri()
        if redirect_uri:
            payload["redirectUri"] = redirect_uri
        return cls._post("/invitation-links", payload)

    @classmethod
    def create_email_invitation(
        cls,
        *,
        email: str,
        name: str,
        reference_id: str,
        locale: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        template_id = cls._require_config("TRUSTPILOT_EMAIL_TEMPLATE_ID")
        sender_name = cls._require_config("TRUSTPILOT_SENDER_NAME")
        sender_email = cls._require_config("TRUSTPILOT_SENDER_EMAIL")
        reply_to = cls._require_config("TRUSTPILOT_REPLY_TO")

        payload: dict[str, Any] = {
            "replyTo": reply_to,
            "locale": locale or cls.get_default_locale(),
            "senderName": sender_name,
            "senderEmail": sender_email,
            "referenceNumber": reference_id,
            "consumerName": name,
            "consumerEmail": email,
            "type": "email",
            "serviceReviewInvitation": {
                "templateId": template_id,
                "preferredSendTime": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            },
        }
        redirect_uri = cls._get_redirect_uri()
        if redirect_uri:
            payload["serviceReviewInvitation"]["redirectUri"] = redirect_uri
        if tags:
            payload["serviceReviewInvitation"]["tags"] = tags
        return cls._post("/email-invitations", payload, include_business_user=True)
