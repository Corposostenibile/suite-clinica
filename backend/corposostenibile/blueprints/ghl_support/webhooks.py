"""Webhook ClickUp → Suite.

Endpoint:
- POST /webhooks/clickup-ghl
- GET /webhooks/clickup-ghl/health

Gestisce:
- taskStatusUpdated  → aggiorna status locale del ticket
- taskCommentPosted  → salva commento in DB (se non già inviato da noi)
- taskUpdated        → log debug
- taskDeleted        → logga e marca sync_error

Sicurezza:
- ClickUp: HMAC-SHA256 del body con CLICKUP_GHL_WEBHOOK_SECRET

Idempotenza: i commenti usano clickup_comment_id UNIQUE, eventi duplicati
sono assorbiti silenziosamente.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
from typing import Any, Dict, Optional

from flask import abort, current_app, jsonify, request

from corposostenibile.models import GHLSupportTicket

from . import ghl_support_hooks_bp
from .services import GHLSupportTicketService

logger = logging.getLogger(__name__)


# ─── HMAC verification ─────────────────────────────────────────────────────


def _verify_clickup_signature() -> bool:
    secret = current_app.config.get("CLICKUP_GHL_WEBHOOK_SECRET") or ""
    if not secret:
        is_dev = (
            current_app.config.get("FLASK_ENV") == "development"
            or current_app.debug
        )
        if is_dev:
            logger.warning(
                "[ghl_support/webhook] CLICKUP_GHL_WEBHOOK_SECRET non configurato, verifica saltata in DEV"
            )
            return True
        logger.error("[ghl_support/webhook] CLICKUP_GHL_WEBHOOK_SECRET non configurato")
        return False

    signature_header = (
        request.headers.get("X-Signature")
        or request.headers.get("X-Clickup-Signature")
        or ""
    ).strip()
    if not signature_header:
        logger.warning("[ghl_support/webhook] header X-Signature mancante")
        return False

    raw_body = request.get_data() or b""
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
    computed_hex = digest.hex()
    computed_b64 = base64.b64encode(digest).decode("ascii")

    matched = (
        hmac.compare_digest(computed_hex, signature_header)
        or hmac.compare_digest(computed_b64, signature_header)
    )

    if not matched:
        logger.warning(
            "[ghl_support/webhook] signature mismatch. recv=%s... hex=%s... b64=%s...",
            signature_header[:16],
            computed_hex[:16],
            computed_b64[:16],
        )

    return matched


# ─── Event dispatchers ─────────────────────────────────────────────────────


def _handle_status_updated(ticket: GHLSupportTicket, payload: Dict[str, Any]) -> None:
    history = payload.get("history_items") or []
    new_status = None
    for item in history:
        if not isinstance(item, dict):
            continue
        after = item.get("after")
        if isinstance(after, dict) and after.get("status"):
            new_status = after.get("status")
            break
        if isinstance(after, str) and after:
            new_status = after
            break
        if item.get("field") == "status":
            data = item.get("data") or {}
            status_ids = data.get("status_type") or data.get("status")
            if status_ids:
                new_status = status_ids if isinstance(status_ids, str) else None

    if not new_status:
        new_status = payload.get("status")
    if not new_status:
        task = payload.get("task") or {}
        if isinstance(task, dict):
            st = task.get("status")
            if isinstance(st, dict):
                new_status = st.get("status")
            elif isinstance(st, str):
                new_status = st

    logger.info(
        "[ghl_support/webhook] statusUpdated extracted='%s' for ticket=%s (current=%s)",
        new_status,
        ticket.ticket_number,
        ticket.status.value if ticket.status else None,
    )

    if not new_status:
        logger.warning(
            "[ghl_support/webhook] statusUpdated senza status per ticket %s",
            ticket.ticket_number,
        )
        return

    changed = GHLSupportTicketService.update_status_from_clickup(ticket, new_status)
    if changed:
        logger.info(
            "[ghl_support/webhook] ticket %s → status '%s'",
            ticket.ticket_number,
            new_status,
        )


def _handle_comment_posted(ticket: GHLSupportTicket, payload: Dict[str, Any]) -> None:
    history = payload.get("history_items") or []
    comment_data: Optional[Dict[str, Any]] = None
    for item in history:
        if isinstance(item, dict) and item.get("comment"):
            comment_data = item.get("comment")
            break

    if not comment_data and payload.get("comment"):
        comment_data = payload.get("comment")

    if not isinstance(comment_data, dict):
        logger.warning(
            "[ghl_support/webhook] commentPosted senza body (ticket %s)",
            ticket.ticket_number,
        )
        return

    clickup_comment_id = str(
        comment_data.get("id") or comment_data.get("hist_id") or ""
    )
    content = (
        comment_data.get("comment_text")
        or comment_data.get("text_content")
        or comment_data.get("text")
        or ""
    )
    user_obj = comment_data.get("user") or {}
    author_name = (
        user_obj.get("username")
        or user_obj.get("email")
        or f"ClickUp user {user_obj.get('id', '?')}"
    )

    if not clickup_comment_id:
        logger.warning(
            "[ghl_support/webhook] commento senza id ClickUp (ticket %s)",
            ticket.ticket_number,
        )
        return

    GHLSupportTicketService.ingest_comment_from_clickup(
        ticket,
        clickup_comment_id=clickup_comment_id,
        content=content,
        author_name=author_name,
    )


# ─── Endpoint ──────────────────────────────────────────────────────────────


@ghl_support_hooks_bp.route("/clickup-ghl", methods=["POST"])
def clickup_webhook():
    raw_preview = (request.get_data(as_text=True) or "")[:300]
    logger.info(
        "[ghl_support/webhook] received POST /webhooks/clickup-ghl (len=%d) body[:300]=%s",
        len(request.get_data() or b""),
        raw_preview,
    )

    if not _verify_clickup_signature():
        logger.warning(
            "[ghl_support/webhook] firma invalida IP=%s",
            request.remote_addr,
        )
        abort(401)

    payload = request.get_json(silent=True) or {}
    event = payload.get("event") or ""
    task_id = payload.get("task_id") or ""
    logger.info(
        "[ghl_support/webhook] event=%s task_id=%s",
        event,
        task_id,
    )

    if not task_id:
        return jsonify({"ok": True, "ignored": True})

    ticket = GHLSupportTicket.query.filter_by(clickup_task_id=str(task_id)).first()
    if not ticket:
        logger.info(
            "[ghl_support/webhook] task %s non è un ticket GHL, ignoro",
            task_id,
        )
        return jsonify({"ok": True, "ignored": True})

    try:
        if event == "taskStatusUpdated":
            _handle_status_updated(ticket, payload)
        elif event == "taskCommentPosted":
            _handle_comment_posted(ticket, payload)
        elif event == "taskDeleted":
            logger.warning(
                "[ghl_support/webhook] task ClickUp %s eliminato per ticket %s",
                task_id,
                ticket.ticket_number,
            )
            ticket.sync_error = "Task eliminato su ClickUp"
            from corposostenibile.extensions import db
            db.session.commit()
        elif event == "taskUpdated":
            logger.debug(
                "[ghl_support/webhook] taskUpdated ricevuto per %s",
                ticket.ticket_number,
            )
        else:
            logger.debug("[ghl_support/webhook] evento non gestito: %s", event)
    except Exception:  # noqa: BLE001
        logger.exception(
            "[ghl_support/webhook] errore processando evento %s per ticket %s",
            event,
            ticket.ticket_number,
        )
        return jsonify({"ok": False, "error": "internal"})

    return jsonify({"ok": True, "event": event, "ticket": ticket.ticket_number})


@ghl_support_hooks_bp.route("/clickup-ghl/health", methods=["GET"])
def clickup_webhook_health():
    return jsonify({"ok": True, "service": "ghl_support.clickup_webhook"})
