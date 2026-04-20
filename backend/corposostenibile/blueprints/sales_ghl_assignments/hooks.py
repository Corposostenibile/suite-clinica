"""Webhook inbound GHL per il flusso SalesLead.

Endpoint:
- POST /webhooks/ghl-leads/new

Riceve lead GHL firmati HMAC, li normalizza e li salva come SalesLead
nel database locale.
"""

from __future__ import annotations

import logging

from flask import jsonify, request

from corposostenibile.blueprints.ghl_integration.security import rate_limiter, require_webhook_signature

from . import sales_ghl_hooks_bp
from .services import save_sales_lead_from_ghl_payload

logger = logging.getLogger(__name__)


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
