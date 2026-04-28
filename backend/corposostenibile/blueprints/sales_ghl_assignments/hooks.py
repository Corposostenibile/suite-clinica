"""Webhook inbound GHL per il flusso SalesLead.

Endpoint:
- POST /webhooks/ghl-leads/new

Riceve lead GHL firmati HMAC, li normalizza e li salva come SalesLead
nel database locale.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from flask import current_app, jsonify, request

from corposostenibile.blueprints.ghl_integration.security import rate_limiter, require_webhook_signature

from . import sales_ghl_hooks_bp
from .services import save_sales_lead_from_ghl_payload

logger = logging.getLogger(__name__)


def _save_test_payload(entry: dict) -> Path:
    """Salva il payload test su file locale in formato NDJSON."""
    configured_target = current_app.config.get("GHL_LEADS_TEST_PAYLOADS_FILE")
    target = Path(configured_target) if configured_target else Path("/tmp/ghl_leads_new_test_payloads.ndjson")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return target


@sales_ghl_hooks_bp.route("/ghl-leads/new/test", methods=["POST"])
def ghl_leads_new_test_webhook():
    """Endpoint pubblico di test: accetta payload non strict e lo salva su file locale."""
    raw_body = request.get_data(cache=True) or b""
    raw_text = request.get_data(as_text=True) or ""
    parsed_json = request.get_json(silent=True)
    form_payload = request.form.to_dict(flat=False) if request.form else {}

    payload = (
        parsed_json
        if parsed_json is not None
        else (form_payload if form_payload else raw_text)
    )

    entry = {
        "received_at": datetime.now(timezone.utc).isoformat(),
        "path": request.path,
        "method": request.method,
        "ip": request.remote_addr,
        "content_type": request.content_type,
        "query": request.args.to_dict(flat=False),
        "headers": {
            "User-Agent": request.headers.get("User-Agent", ""),
            "Content-Type": request.headers.get("Content-Type", ""),
            "X-Forwarded-For": request.headers.get("X-Forwarded-For", ""),
            "X-Real-IP": request.headers.get("X-Real-IP", ""),
        },
        "payload": payload,
        "raw_body_bytes": len(raw_body),
    }

    target = _save_test_payload(entry)

    return jsonify(
        {
            "ok": True,
            "success": True,
            "message": "Payload test ricevuto e salvato",
            "saved_to": str(target),
            "bytes": len(raw_body),
        }
    ), 200


@sales_ghl_hooks_bp.route("/ghl-leads/new", methods=["POST"])
@require_webhook_signature
def ghl_leads_new_webhook():
    """Riceve nuovi lead GHL firmati e li salva come SalesLead."""
    raw_body = request.get_data() or b""
    raw_preview = (request.get_data(as_text=True) or "")[:300]
    logger.info(
        "[sales_ghl_assignments/webhook] received POST /webhooks/ghl-leads/new (len=%d) body[:300]=%s",
        len(raw_body),
        raw_preview,
    )

    client_ip = request.remote_addr or "unknown"
    if not rate_limiter.is_allowed(f"ghl_leads_webhook_{client_ip}"):
        logger.warning("[sales_ghl_assignments/webhook] rate limit exceeded IP=%s", client_ip)
        return jsonify({"ok": False, "error": "rate_limited"}), 429

    try:
        payload = request.get_json(silent=True) or {}
        if not payload:
            payload = request.form.to_dict() or request.values.to_dict() or {}
        if not payload:
            return jsonify({"ok": False, "error": "No payload provided"}), 400

        lead, created = save_sales_lead_from_ghl_payload(payload, client_ip)

        return jsonify(
            {
                "ok": True,
                "success": True,
                "message": "Lead GHL ricevuto e salvato come SalesLead",
                "id": lead.id,
                "created": created,
                "unique_code": lead.unique_code,
            }
        )
    except ValueError as exc:
        logger.warning("[sales_ghl_assignments/webhook] validation error: %s", exc)
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        logger.exception("[sales_ghl_assignments/webhook] errore processando ghl-leads/new: %s", exc)
        return jsonify({"ok": False, "error": "internal"}), 500
