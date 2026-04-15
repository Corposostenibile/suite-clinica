"""
Field mapping ClickUp per lo Space "Go High Level - Ticket".

Differenze rispetto al it_support:
- Nessun dropdown (tipo/modulo/criticità) — l'utente non sceglie
- Solo 6 custom field text/email configurati via env CLICKUP_GHL_FIELD_*:
    * ID Ticket
    * Utente Email
    * Utente Nome
    * User ID GHL
    * Browser Utente
    * OS Utente
- Nessuna priorità custom: il team IT la imposta manualmente su ClickUp
- Blocco "Contesto tecnico" nel body del task contiene: pagina origine,
  location GHL, ruolo, user-agent raw
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from flask import current_app

from corposostenibile.models import GHLSupportTicketStatusEnum


# ─── Status ClickUp ↔ Suite ──────────────────────────────────────────────

_SUITE_TO_CLICKUP_STATUS = {
    GHLSupportTicketStatusEnum.nuovo: "nuovo",
    GHLSupportTicketStatusEnum.in_analisi: "in analisi",
    GHLSupportTicketStatusEnum.in_lavorazione: "in lavorazione",
    GHLSupportTicketStatusEnum.in_attesa_highlevel: "in attesa highlevel",
    GHLSupportTicketStatusEnum.in_attesa_utente: "in attesa utente",
    GHLSupportTicketStatusEnum.risolto: "risolto",
    GHLSupportTicketStatusEnum.non_valido: "non valido",
}

_CLICKUP_TO_SUITE_STATUS = {v: k for k, v in _SUITE_TO_CLICKUP_STATUS.items()}


def map_status_to_clickup(status: GHLSupportTicketStatusEnum) -> str:
    return _SUITE_TO_CLICKUP_STATUS[status]


def map_status_from_clickup(clickup_status_name: str) -> Optional[GHLSupportTicketStatusEnum]:
    if not clickup_status_name:
        return None
    return _CLICKUP_TO_SUITE_STATUS.get(clickup_status_name.strip().lower())


# ─── Custom fields payload builder ──────────────────────────────────────

def build_custom_fields_payload(ticket) -> List[Dict[str, Any]]:
    """
    Costruisce la lista `custom_fields` da passare a ClickUp al create/update.
    Solo 6 field text (niente dropdown — l'utente GHL non sceglie nulla).
    """
    cfg = current_app.config
    fields: List[Dict[str, Any]] = []

    def _add(field_cfg_key: str, value: Any):
        field_id = cfg.get(field_cfg_key)
        if field_id and value is not None and value != "":
            fields.append({"id": field_id, "value": value})

    _add("CLICKUP_GHL_FIELD_TICKET_ID", ticket.ticket_number)
    _add("CLICKUP_GHL_FIELD_EMAIL_UTENTE", ticket.ghl_user_email)
    _add("CLICKUP_GHL_FIELD_NOME_UTENTE", ticket.ghl_user_name)
    _add("CLICKUP_GHL_FIELD_USER_ID_GHL", ticket.ghl_user_id)
    _add("CLICKUP_GHL_FIELD_BROWSER", ticket.browser)
    _add("CLICKUP_GHL_FIELD_OS", ticket.os)

    return fields


def build_description(ticket) -> str:
    """
    Costruisce il body della task ClickUp con un blocco 'Contesto tecnico'
    in coda, utile al team IT per debug.

    Nel contesto tecnico mettiamo TUTTO quello che NON ha un custom field
    dedicato: URL pagina origine, location GHL, ruolo GHL, user-agent raw.
    """
    base = (ticket.description or "").strip()

    tech_lines: List[str] = []
    if ticket.pagina_origine:
        tech_lines.append(f"- URL pagina GHL: {ticket.pagina_origine}")
    if ticket.ghl_location_name or ticket.ghl_location_id:
        loc = ticket.ghl_location_name or ""
        if ticket.ghl_location_id:
            loc = f"{loc} (ID {ticket.ghl_location_id})".strip()
        tech_lines.append(f"- Location GHL: {loc}")
    if ticket.ghl_user_role:
        tech_lines.append(f"- Ruolo GHL: {ticket.ghl_user_role}")
    if ticket.browser or ticket.os:
        tech_lines.append(
            "- Browser/OS: "
            + " / ".join(filter(None, [ticket.browser, ticket.os]))
        )
    if ticket.user_agent_raw:
        tech_lines.append(f"- User-Agent: `{ticket.user_agent_raw[:400]}`")
    if ticket.ghl_user_email:
        tech_lines.append(
            f"- Aperto da: {ticket.ghl_user_name or ''} ({ticket.ghl_user_email})".strip()
        )
    tech_lines.append(f"- Ticket Suite: **{ticket.ticket_number}**")
    if ticket.created_at:
        tech_lines.append(f"- Aperto il: {ticket.created_at.isoformat()}")

    if tech_lines:
        return (
            f"{base}\n\n"
            "---\n"
            "### 🔧 Contesto tecnico\n"
            + "\n".join(tech_lines)
        )
    return base


def build_tags(ticket) -> List[str]:
    """Tag applicati al task ClickUp per filtraggio lato team IT."""
    tags: List[str] = ["origine:ghl"]
    if ticket.ghl_user_role:
        tags.append(f"ruolo:{ticket.ghl_user_role}")
    if ticket.ghl_location_id:
        tags.append(f"loc:{ticket.ghl_location_id}")
    return tags
