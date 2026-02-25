"""
Webhook dispatch per cambi stato globale cliente verso pausa/ghost.

Listener SQLAlchemy centralizzato:
- intercetta qualunque update a Cliente.stato_cliente
- accoda l'evento in transazione
- invia (o logga in mock mode) solo dopo commit riuscito
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import requests
from flask import Flask, current_app, has_app_context
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from corposostenibile.models import Cliente

_LISTENERS_REGISTERED = False
_PENDING_KEY = "_global_status_webhook_events"
_APP_KEY = "_global_status_webhook_app"


def _state_value(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _build_payload(cliente: Cliente, old_status: str | None, new_status: str) -> dict[str, Any]:
    return {
        "event_type": "cliente.global_status.changed",
        "trigger": "global_status_to_pause_or_ghost",
        "occurred_at": datetime.utcnow().isoformat(),
        "cliente": {
            "id": cliente.cliente_id,
            "nome_cognome": cliente.nome_cognome,
            "email": cliente.mail,
            "telefono": cliente.numero_telefono,
        },
        "status": {
            "old": old_status,
            "new": new_status,
        },
    }


def _dispatch_webhook(payload: dict[str, Any]) -> None:
    mode = (current_app.config.get("GHL_GLOBAL_STATUS_WEBHOOK_MODE") or "mock").strip().lower()
    webhook_url = (current_app.config.get("GHL_GLOBAL_STATUS_WEBHOOK_URL") or "").strip()

    if mode == "mock" or not webhook_url:
        current_app.logger.info("[GHL_MOCK_WEBHOOK] Global status event triggered: %s", payload)
        return

    try:
        response = requests.post(webhook_url, json=payload, timeout=8)
        response.raise_for_status()
        current_app.logger.info(
            "[GHL_WEBHOOK] Global status event sent: cliente_id=%s status=%s http=%s",
            payload.get("cliente", {}).get("id"),
            payload.get("status", {}).get("new"),
            response.status_code,
        )
    except Exception as exc:
        current_app.logger.error("[GHL_WEBHOOK] Global status webhook failed: %s", exc, exc_info=True)


def _before_flush(session: Session, flush_context, instances) -> None:  # noqa: ANN001
    pending = session.info.setdefault(_PENDING_KEY, {})

    app_obj: Flask | None = None
    if has_app_context():
        app_obj = current_app._get_current_object()
    if app_obj is not None:
        session.info[_APP_KEY] = app_obj

    for obj in session.dirty:
        if not isinstance(obj, Cliente):
            continue

        state = inspect(obj)
        history = state.attrs.stato_cliente.history
        if not history.has_changes():
            continue

        old_status = _state_value(history.deleted[0]) if history.deleted else None
        new_status = _state_value(history.added[0]) if history.added else _state_value(obj.stato_cliente)

        if not new_status or new_status not in {"pausa", "ghost"}:
            continue
        if old_status == new_status:
            continue

        pending[obj.cliente_id] = _build_payload(obj, old_status, new_status)


def _after_commit(session: Session) -> None:
    pending = session.info.pop(_PENDING_KEY, None) or {}
    app_obj: Flask | None = session.info.pop(_APP_KEY, None)
    if not pending:
        return

    if app_obj is not None:
        with app_obj.app_context():
            for payload in pending.values():
                _dispatch_webhook(payload)
        return

    if has_app_context():
        for payload in pending.values():
            _dispatch_webhook(payload)


def _after_rollback(session: Session) -> None:
    session.info.pop(_PENDING_KEY, None)
    session.info.pop(_APP_KEY, None)


def register_global_status_webhook_listeners(app: Flask) -> None:
    global _LISTENERS_REGISTERED
    if _LISTENERS_REGISTERED:
        return

    event.listen(Session, "before_flush", _before_flush)
    event.listen(Session, "after_commit", _after_commit)
    event.listen(Session, "after_rollback", _after_rollback)
    _LISTENERS_REGISTERED = True
    app.logger.info("[customers] Global status webhook listeners registered")
