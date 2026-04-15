"""
Webhook ClickUp → Suite Clinica.

Endpoint:
- POST /webhooks/clickup

Gestisce:
- taskStatusUpdated  → aggiorna status locale del ticket
- taskCommentPosted  → salva commento in DB (se non già inviato da noi)
- taskUpdated        → refresh campi (best-effort)
- taskDeleted        → logga e marca sync_error

Sicurezza:
- Verifica HMAC-SHA256 del body con CLICKUP_WEBHOOK_SECRET
- In dev (FLASK_ENV=development) la verifica può essere bypassata con log warn

Idempotenza:
- I commenti usano clickup_comment_id come UNIQUE
- Gli eventi duplicati sono assorbiti silenziosamente
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any, Dict, Optional

from flask import abort, current_app, jsonify, request

from corposostenibile.models import ITSupportTicket

from . import it_support_hooks_bp
from .services import ITSupportTicketService

logger = logging.getLogger(__name__)


# ─── HMAC verification ─────────────────────────────────────────────────────


def _verify_clickup_signature() -> bool:
    """
    ClickUp invia header 'X-Signature' con HMAC-SHA256 del body firmato col
    secret ricevuto alla creazione del webhook. L'encoding può essere hex
    o base64 a seconda del provider — accettiamo entrambi.
    """
    import base64

    secret = current_app.config.get("CLICKUP_WEBHOOK_SECRET") or ""
    if not secret:
        is_dev = (
            current_app.config.get("FLASK_ENV") == "development"
            or current_app.debug
        )
        if is_dev:
            logger.warning(
                "[it_support/webhook] nessun CLICKUP_WEBHOOK_SECRET configurato "
                "- verifica saltata in DEV"
            )
            return True
        logger.error("[it_support/webhook] CLICKUP_WEBHOOK_SECRET non configurato")
        return False

    signature_header = (
        request.headers.get("X-Signature")
        or request.headers.get("X-Clickup-Signature")
        or ""
    ).strip()
    if not signature_header:
        logger.warning(
            "[it_support/webhook] header X-Signature mancante (headers: %s)",
            dict(request.headers),
        )
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
            "[it_support/webhook] signature mismatch. received=%s... computed_hex=%s... computed_b64=%s...",
            signature_header[:16],
            computed_hex[:16],
            computed_b64[:16],
        )

    return matched


# ─── Event dispatchers ─────────────────────────────────────────────────────


def _handle_status_updated(ticket: ITSupportTicket, payload: Dict[str, Any]) -> None:
    history = payload.get("history_items") or []
    new_status = None
    for item in history:
        if not isinstance(item, dict):
            continue
        after = item.get("after")
        # 1) after è un dict con chiave status
        if isinstance(after, dict) and after.get("status"):
            new_status = after.get("status")
            break
        # 2) after è direttamente una stringa (alcuni payload ClickUp)
        if isinstance(after, str) and after:
            new_status = after
            break
        # 3) field=status con valore dentro data
        if item.get("field") == "status":
            data = item.get("data") or {}
            status_ids = data.get("status_type") or data.get("status")
            if status_ids:
                new_status = status_ids if isinstance(status_ids, str) else None

    # fallback top-level
    if not new_status:
        new_status = payload.get("status")
    if not new_status:
        # fallback: nested task_url may have status
        task = payload.get("task") or {}
        if isinstance(task, dict):
            st = task.get("status")
            if isinstance(st, dict):
                new_status = st.get("status")
            elif isinstance(st, str):
                new_status = st

    logger.info(
        "[it_support/webhook] statusUpdated extracted='%s' for ticket=%s (current=%s)",
        new_status,
        ticket.ticket_number,
        ticket.status.value if ticket.status else None,
    )

    if not new_status:
        logger.warning(
            "[it_support/webhook] statusUpdated senza status nel payload per ticket %s",
            ticket.ticket_number,
        )
        return

    changed = ITSupportTicketService.update_status_from_clickup(ticket, new_status)
    if changed:
        logger.info(
            "[it_support/webhook] ticket %s → status '%s'",
            ticket.ticket_number,
            new_status,
        )
    else:
        logger.info(
            "[it_support/webhook] ticket %s status invariato (mapping/no-change)",
            ticket.ticket_number,
        )


def _handle_comment_posted(ticket: ITSupportTicket, payload: Dict[str, Any]) -> None:
    history = payload.get("history_items") or []
    comment_data: Optional[Dict[str, Any]] = None
    for item in history:
        if isinstance(item, dict) and item.get("comment"):
            comment_data = item.get("comment")
            break

    # fallback: struttura alternativa
    if not comment_data and payload.get("comment"):
        comment_data = payload.get("comment")

    if not isinstance(comment_data, dict):
        logger.warning(
            "[it_support/webhook] commentPosted senza body commento (ticket %s)",
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
            "[it_support/webhook] commento senza id ClickUp (ticket %s)",
            ticket.ticket_number,
        )
        return

    ITSupportTicketService.ingest_comment_from_clickup(
        ticket,
        clickup_comment_id=clickup_comment_id,
        content=content,
        author_name=author_name,
    )


# ─── Endpoint ──────────────────────────────────────────────────────────────


@it_support_hooks_bp.route("/clickup", methods=["POST"])
def clickup_webhook():
    raw_preview = (request.get_data(as_text=True) or "")[:300]
    logger.info(
        "[it_support/webhook] received POST /webhooks/clickup (len=%d) body[:300]=%s",
        len(request.get_data() or b""),
        raw_preview,
    )

    if not _verify_clickup_signature():
        logger.warning(
            "[it_support/webhook] firma invalida IP=%s",
            request.remote_addr,
        )
        abort(401)

    payload = request.get_json(silent=True) or {}
    event = payload.get("event") or ""
    task_id = payload.get("task_id") or ""
    logger.info(
        "[it_support/webhook] event=%s task_id=%s",
        event,
        task_id,
    )

    if not task_id:
        logger.info("[it_support/webhook] evento '%s' senza task_id, ignoro", event)
        return jsonify({"ok": True, "ignored": True})

    ticket = ITSupportTicket.query.filter_by(clickup_task_id=str(task_id)).first()
    if not ticket:
        logger.info(
            "[it_support/webhook] task %s non è un nostro ticket, ignoro",
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
                "[it_support/webhook] task ClickUp %s eliminato per ticket %s",
                task_id,
                ticket.ticket_number,
            )
            ticket.sync_error = "Task eliminato su ClickUp"
            from corposostenibile.extensions import db
            db.session.commit()
        elif event == "taskUpdated":
            # refresh leggero: log e basta; lo status viene da taskStatusUpdated
            logger.debug(
                "[it_support/webhook] taskUpdated ricevuto per %s",
                ticket.ticket_number,
            )
        else:
            logger.debug("[it_support/webhook] evento non gestito: %s", event)
    except Exception:  # noqa: BLE001
        logger.exception(
            "[it_support/webhook] errore processando evento %s per ticket %s",
            event,
            ticket.ticket_number,
        )
        # rispondiamo 200 per evitare retry-storm; l'errore è loggato
        return jsonify({"ok": False, "error": "internal"})

    return jsonify({"ok": True, "event": event, "ticket": ticket.ticket_number})


@it_support_hooks_bp.route("/clickup/health", methods=["GET"])
def clickup_webhook_health():
    """Endpoint di health per verifica webhook registrato."""
    return jsonify({"ok": True, "service": "it_support.clickup_webhook"})
