"""
Invio dati dalla Suite verso GHL (webhook outbound).

Quando un paziente passa in stato ghost (manualmente o automaticamente),
viene inviato un POST al webhook configurato (GHL_WEBHOOK_GHOST_URL) con
tutti i dati necessari del paziente per aggiornare GHL.
"""

from datetime import datetime
from typing import Any, Dict, Optional

import requests
from flask import current_app

from corposostenibile.models import Cliente


def _stato_value(stato) -> Optional[str]:
    """Restituisce il valore stringa dello stato (Enum o stringa)."""
    if stato is None:
        return None
    if hasattr(stato, "value"):
        return stato.value
    return str(stato)


def _dt_iso(dt: Optional[datetime]) -> Optional[str]:
    """Formatta datetime in ISO per il payload JSON."""
    if dt is None:
        return None
    return dt.isoformat() if hasattr(dt, "isoformat") else str(dt)


def build_ghost_payload(cliente: Cliente) -> Dict[str, Any]:
    """
    Costruisce il payload da inviare a GHL quando un paziente va in ghost.

    Include i dati necessari per identificare il contatto in GHL e gli stati
    dei servizi (nutrizione, coach, psicologia).
    """
    return {
        "event": "cliente_ghost",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "cliente": {
            "cliente_id": cliente.cliente_id,
            "nome_cognome": cliente.nome_cognome or "",
            "mail": getattr(cliente, "mail", None) or "",
            "numero_telefono": getattr(cliente, "numero_telefono", None) or "",
            "ghl_contact_id": getattr(cliente, "ghl_contact_id", None) or None,
            "stato_cliente": _stato_value(cliente.stato_cliente),
            "stato_cliente_data": _dt_iso(getattr(cliente, "stato_cliente_data", None)),
            "stato_nutrizione": _stato_value(getattr(cliente, "stato_nutrizione", None)),
            "stato_nutrizione_data": _dt_iso(getattr(cliente, "stato_nutrizione_data", None)),
            "stato_coach": _stato_value(getattr(cliente, "stato_coach", None)),
            "stato_coach_data": _dt_iso(getattr(cliente, "stato_coach_data", None)),
            "stato_psicologia": _stato_value(getattr(cliente, "stato_psicologia", None)),
            "stato_psicologia_data": _dt_iso(getattr(cliente, "stato_psicologia_data", None)),
            "programma_attuale": getattr(cliente, "programma_attuale", None) or None,
            "data_inizio_abbonamento": _dt_iso(getattr(cliente, "data_inizio_abbonamento", None)),
            "data_rinnovo": _dt_iso(getattr(cliente, "data_rinnovo", None)),
            "tipologia_cliente": _stato_value(getattr(cliente, "tipologia_cliente", None)),
        },
    }


def send_ghost_webhook_to_ghl(cliente: Cliente) -> bool:
    """
    Invia a GHL un webhook con i dati del paziente quando passa in ghost.

    Usa la variabile GHL_WEBHOOK_GHOST_URL. Se non configurata, non fa nulla.
    Esegue un POST JSON in best-effort (errori loggati, non sollevati).

    Returns:
        True se l'invio è andato a buon fine (2xx), False altrimenti o se URL non configurato.
    """
    url = current_app.config.get("GHL_WEBHOOK_GHOST_URL")
    if not url or not str(url).strip():
        current_app.logger.debug(
            "GHL_WEBHOOK_GHOST_URL non configurato; skip invio webhook ghost per cliente %s",
            cliente.cliente_id,
        )
        return False

    payload = build_ghost_payload(cliente)
    try:
        resp = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        if resp.ok:
            current_app.logger.info(
                "[GHL Outbound] Webhook ghost inviato per cliente %s (%s) -> %s",
                cliente.cliente_id,
                cliente.nome_cognome,
                url,
            )
            return True
        current_app.logger.warning(
            "[GHL Outbound] Webhook ghost risposta non 2xx per cliente %s: %s %s",
            cliente.cliente_id,
            resp.status_code,
            resp.text[:200],
        )
        return False
    except requests.RequestException as e:
        current_app.logger.exception(
            "[GHL Outbound] Errore invio webhook ghost per cliente %s: %s",
            cliente.cliente_id,
            e,
        )
        return False
