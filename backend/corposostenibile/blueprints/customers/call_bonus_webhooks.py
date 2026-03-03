"""
Webhook dispatch per call bonus "interessato" verso GHL (notifica HM).

Chiamata diretta dalla route (non event listener) quando il professionista
assegnato conferma l'interesse del paziente.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import requests
from flask import current_app

from corposostenibile.extensions import db


def _build_call_bonus_payload(call_bonus) -> dict[str, Any]:
    """Costruisce il payload webhook per una call bonus con interesse confermato."""
    cliente = call_bonus.cliente
    return {
        "event_type": "call_bonus.interessato",
        "occurred_at": datetime.utcnow().isoformat(),
        "cliente": {
            "id": cliente.cliente_id,
            "nome_cognome": cliente.nome_cognome,
            "email": cliente.mail,
            "telefono": cliente.numero_telefono,
        },
        "professionista_richiedente": {
            "id": call_bonus.created_by_id,
            "nome": call_bonus.created_by.full_name if call_bonus.created_by else None,
        },
        "professionista_assegnato": {
            "id": call_bonus.professionista_id,
            "nome": call_bonus.professionista.full_name if call_bonus.professionista else None,
        },
    }


def dispatch_call_bonus_webhook(call_bonus) -> bool:
    """
    Invia (o logga in mock mode) il webhook GHL per call bonus interessato.

    Ritorna True se il webhook è stato inviato con successo (o mock), False altrimenti.
    Aggiorna i campi webhook_sent / webhook_sent_at sulla call_bonus.
    """
    mode = (current_app.config.get("GHL_CALL_BONUS_WEBHOOK_MODE") or "mock").strip().lower()
    webhook_url = (current_app.config.get("GHL_CALL_BONUS_WEBHOOK_URL") or "").strip()

    payload = _build_call_bonus_payload(call_bonus)

    if mode == "mock" or not webhook_url:
        current_app.logger.info(
            "[GHL_MOCK_WEBHOOK] Call bonus interesse event: %s", payload
        )
        call_bonus.webhook_sent = True
        call_bonus.webhook_sent_at = datetime.utcnow()
        return True

    try:
        response = requests.post(webhook_url, json=payload, timeout=8)
        response.raise_for_status()
        current_app.logger.info(
            "[GHL_WEBHOOK] Call bonus interesse sent: call_bonus_id=%s http=%s",
            call_bonus.id,
            response.status_code,
        )
        call_bonus.webhook_sent = True
        call_bonus.webhook_sent_at = datetime.utcnow()
        return True
    except Exception as exc:
        current_app.logger.error(
            "[GHL_WEBHOOK] Call bonus webhook failed: %s", exc, exc_info=True
        )
        return False
