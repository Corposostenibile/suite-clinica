"""
ClickUp API Client (GHL Support variant)
========================================
Wrapper thread-safe per le chiamate all'API ClickUp v2. Identico a quello di
``it_support`` ma parametrizzato per il nuovo Space/List GHL tramite le env
var ``CLICKUP_GHL_*``.

Docs: https://clickup.com/api
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import requests
from flask import current_app

logger = logging.getLogger(__name__)


class ClickUpError(RuntimeError):
    """Errore generico chiamata API ClickUp."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_text: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text

    def __str__(self) -> str:
        base = super().__str__()
        if self.status_code is not None:
            return f"[{self.status_code}] {base}"
        return base


class ClickUpClient:
    """Client sincrono per l'API ClickUp v2."""

    BASE_URL = "https://api.clickup.com/api/v2"

    def __init__(
        self,
        api_token: str,
        list_id: str,
        workspace_id: Optional[str] = None,
        timeout: float = 15.0,
        max_retries: int = 3,
    ) -> None:
        if not api_token:
            raise ValueError("CLICKUP_API_TOKEN mancante")
        if not list_id:
            raise ValueError("CLICKUP_GHL_LIST_ID mancante")
        self.api_token = api_token
        self.list_id = str(list_id)
        self.workspace_id = str(workspace_id) if workspace_id else None
        self.timeout = timeout
        self.max_retries = max_retries
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": self.api_token,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    @classmethod
    def from_app_config(cls, app=None) -> "ClickUpClient":
        """Factory che legge le CLICKUP_GHL_* (token + workspace condivisi)."""
        app = app or current_app
        return cls(
            api_token=app.config.get("CLICKUP_API_TOKEN", ""),
            list_id=app.config.get("CLICKUP_GHL_LIST_ID", ""),
            workspace_id=app.config.get("CLICKUP_WORKSPACE_ID"),
            timeout=float(app.config.get("CLICKUP_REQUEST_TIMEOUT", 15)),
            max_retries=int(app.config.get("CLICKUP_MAX_RETRIES", 3)),
        )

    # ─── HTTP dispatcher ────────────────────────────────────────────────────

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.BASE_URL}{path}"
        attempt = 0
        last_exc: Optional[Exception] = None

        while attempt <= self.max_retries:
            attempt += 1
            try:
                if files is not None:
                    headers = dict(self._session.headers)
                    headers.pop("Content-Type", None)
                    if extra_headers:
                        headers.update(extra_headers)
                    resp = requests.request(
                        method,
                        url,
                        data=json_body if json_body else None,
                        params=params,
                        files=files,
                        headers=headers,
                        timeout=self.timeout,
                    )
                else:
                    resp = self._session.request(
                        method,
                        url,
                        json=json_body,
                        params=params,
                        headers=extra_headers,
                        timeout=self.timeout,
                    )
            except requests.RequestException as exc:
                last_exc = exc
                logger.warning(
                    "[ClickUp-GHL] %s %s fallita (tentativo %d/%d): %s",
                    method, path, attempt, self.max_retries + 1, exc,
                )
                if attempt > self.max_retries:
                    raise ClickUpError(f"Network error: {exc}") from exc
                time.sleep(self._backoff(attempt))
                continue

            if resp.status_code == 429:
                retry_after = float(
                    resp.headers.get("Retry-After", self._backoff(attempt))
                )
                logger.warning("[ClickUp-GHL] rate limited, retry after %.1fs", retry_after)
                if attempt > self.max_retries:
                    raise ClickUpError(
                        "Rate limited", status_code=429, response_text=resp.text
                    )
                time.sleep(retry_after)
                continue

            if 500 <= resp.status_code < 600:
                logger.warning(
                    "[ClickUp-GHL] %s %s → %d (tentativo %d/%d)",
                    method, path, resp.status_code, attempt, self.max_retries + 1,
                )
                if attempt > self.max_retries:
                    raise ClickUpError(
                        f"Server error {resp.status_code}",
                        status_code=resp.status_code,
                        response_text=resp.text,
                    )
                time.sleep(self._backoff(attempt))
                continue

            if not resp.ok:
                raise ClickUpError(
                    f"HTTP {resp.status_code}: {resp.text[:400]}",
                    status_code=resp.status_code,
                    response_text=resp.text,
                )

            if not resp.content:
                return {}
            try:
                return resp.json()
            except ValueError:
                return {"raw": resp.text}

        if last_exc:
            raise ClickUpError(f"Network error dopo retry: {last_exc}") from last_exc
        raise ClickUpError("Request fallita dopo tutti i retry")

    @staticmethod
    def _backoff(attempt: int) -> float:
        return min(2 ** (attempt - 1), 30)

    # ─── Tasks ──────────────────────────────────────────────────────────────

    def create_task(
        self,
        name: str,
        description: str,
        priority: Optional[int] = None,
        custom_fields: Optional[List[Dict[str, Any]]] = None,
        tags: Optional[List[str]] = None,
        status: Optional[str] = None,
        due_date_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"name": name, "description": description}
        if priority is not None:
            payload["priority"] = priority
        if custom_fields:
            payload["custom_fields"] = custom_fields
        if tags:
            payload["tags"] = tags
        if status:
            payload["status"] = status
        if due_date_ms:
            payload["due_date"] = due_date_ms
        return self._request("POST", f"/list/{self.list_id}/task", json_body=payload)

    def update_task(self, task_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("PUT", f"/task/{task_id}", json_body=payload)

    def get_task(self, task_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/task/{task_id}")

    # ─── Comments ───────────────────────────────────────────────────────────

    def post_comment(
        self,
        task_id: str,
        comment_text: str,
        notify_all: bool = True,
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/task/{task_id}/comment",
            json_body={"comment_text": comment_text, "notify_all": notify_all},
        )

    # ─── Attachments ────────────────────────────────────────────────────────

    def upload_attachment(
        self,
        task_id: str,
        file_path: str,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        import os
        with open(file_path, "rb") as fp:
            files = {"attachment": (filename or os.path.basename(file_path), fp)}
            return self._request(
                "POST",
                f"/task/{task_id}/attachment",
                files=files,
            )

    # ─── Webhooks ───────────────────────────────────────────────────────────

    def list_webhooks(self, workspace_id: Optional[str] = None) -> Dict[str, Any]:
        wid = workspace_id or self.workspace_id
        if not wid:
            raise ValueError("workspace_id richiesto per list_webhooks")
        return self._request("GET", f"/team/{wid}/webhook")

    def create_webhook(
        self,
        endpoint_url: str,
        events: List[str],
        *,
        workspace_id: Optional[str] = None,
        space_id: Optional[str] = None,
        folder_id: Optional[str] = None,
        list_id: Optional[str] = None,
        task_id: Optional[str] = None,
        health_check_url: Optional[str] = None,
        secret: Optional[str] = None,
    ) -> Dict[str, Any]:
        wid = workspace_id or self.workspace_id
        if not wid:
            raise ValueError("workspace_id richiesto per create_webhook")
        payload: Dict[str, Any] = {"endpoint": endpoint_url, "events": events}
        if space_id:
            payload["space_id"] = space_id
        if folder_id:
            payload["folder_id"] = folder_id
        if list_id:
            payload["list_id"] = list_id
        if task_id:
            payload["task_id"] = task_id
        if health_check_url:
            payload["health_check_url"] = health_check_url
        if secret:
            payload["secret"] = secret
        return self._request("POST", f"/team/{wid}/webhook", json_body=payload)

    def delete_webhook(self, webhook_id: str) -> Dict[str, Any]:
        return self._request("DELETE", f"/webhook/{webhook_id}")
