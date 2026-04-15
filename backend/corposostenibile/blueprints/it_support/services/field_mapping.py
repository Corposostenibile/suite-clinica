"""
Mapping fra enum interni (Suite) e struttura ClickUp.

Ogni dropdown ClickUp ha un field_id (UUID) e ciascuna opzione ha a sua
volta un UUID stabile. Questi UUID sono caricati dall'env (CLICKUP_FIELD_*
e CLICKUP_OPT_*) al boot dell'app.

Le priorità native ClickUp sono numeri interi 1..4 (Urgent..Low).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from flask import current_app

from corposostenibile.models import (
    ITSupportTicketCriticitaEnum,
    ITSupportTicketModuloEnum,
    ITSupportTicketStatusEnum,
    ITSupportTicketTipoEnum,
)


# ─── Priorità: Criticità → ClickUp priority (native) ───────────────────────
# Bloccante → Urgent(1), Non Bloccante → Normal(3)
_CRITICITA_TO_PRIORITY: Dict[ITSupportTicketCriticitaEnum, int] = {
    ITSupportTicketCriticitaEnum.bloccante: 1,
    ITSupportTicketCriticitaEnum.non_bloccante: 3,
}


def map_priority_from_criticita(criticita: Optional[ITSupportTicketCriticitaEnum]) -> Optional[int]:
    """Restituisce il valore ClickUp priority (1..4) dalla criticità."""
    if criticita is None:
        return None
    return _CRITICITA_TO_PRIORITY.get(criticita)


# ─── Status ClickUp ↔ Suite ──────────────────────────────────────────────
# Nota: ClickUp status sono nomi case-sensitive lowercase come configurati.

_SUITE_TO_CLICKUP_STATUS = {
    ITSupportTicketStatusEnum.nuovo: "nuovo",
    ITSupportTicketStatusEnum.in_triage: "in triage",
    ITSupportTicketStatusEnum.in_lavorazione: "in lavorazione",
    ITSupportTicketStatusEnum.in_attesa_utente: "in attesa utente",
    ITSupportTicketStatusEnum.da_testare: "da testare",
    ITSupportTicketStatusEnum.risolto: "risolto",
    ITSupportTicketStatusEnum.non_valido: "non valido",
}

_CLICKUP_TO_SUITE_STATUS = {v: k for k, v in _SUITE_TO_CLICKUP_STATUS.items()}


def map_status_to_clickup(status: ITSupportTicketStatusEnum) -> str:
    return _SUITE_TO_CLICKUP_STATUS[status]


def map_status_from_clickup(clickup_status_name: str) -> Optional[ITSupportTicketStatusEnum]:
    if not clickup_status_name:
        return None
    return _CLICKUP_TO_SUITE_STATUS.get(clickup_status_name.strip().lower())


# ─── Dropdown option mapping ────────────────────────────────────────────

def _opt(cfg_key: str) -> Optional[str]:
    """Leggi UUID opzione dropdown dall'app config."""
    value = current_app.config.get(cfg_key)
    return value if value else None


def _map_tipo(tipo: ITSupportTicketTipoEnum) -> Optional[str]:
    return _opt(f"CLICKUP_OPT_TIPO_{tipo.value.upper()}")


def _map_modulo(modulo: ITSupportTicketModuloEnum) -> Optional[str]:
    return _opt(f"CLICKUP_OPT_MODULO_{modulo.value.upper()}")


def _map_criticita(criticita: ITSupportTicketCriticitaEnum) -> Optional[str]:
    return _opt(f"CLICKUP_OPT_CRITICITA_{criticita.value.upper()}")


# ─── Custom fields payload builder ──────────────────────────────────────

def build_custom_fields_payload(ticket) -> List[Dict[str, Any]]:
    """
    Costruisce la lista `custom_fields` da passare a ClickUp al create/update.

    Formato accettato da ClickUp:
      [{"id": "<field_uuid>", "value": "<option_uuid_or_string>"}, ...]
    """
    cfg = current_app.config
    fields: List[Dict[str, Any]] = []

    def _add(field_cfg_key: str, value: Any):
        field_id = cfg.get(field_cfg_key)
        if field_id and value is not None and value != "":
            fields.append({"id": field_id, "value": value})

    # Dropdown (usano option UUID)
    _add("CLICKUP_FIELD_TIPO", _map_tipo(ticket.tipo))
    _add("CLICKUP_FIELD_MODULO", _map_modulo(ticket.modulo))
    _add("CLICKUP_FIELD_CRITICITA", _map_criticita(ticket.criticita))

    # Testo/email/URL (valore diretto)
    _add("CLICKUP_FIELD_TICKET_ID", ticket.ticket_number)
    _add("CLICKUP_FIELD_EMAIL_UTENTE", getattr(ticket.user, "email", None))

    user_full_name = None
    if ticket.user:
        first = (ticket.user.first_name or "").strip()
        last = (ticket.user.last_name or "").strip()
        user_full_name = f"{first} {last}".strip() or None
    _add("CLICKUP_FIELD_NOME_UTENTE", user_full_name)

    role_value = None
    if ticket.user and getattr(ticket.user, "role", None):
        role = ticket.user.role
        role_value = role.value if hasattr(role, "value") else str(role)
    _add("CLICKUP_FIELD_RUOLO", role_value)

    specialty_value = None
    if ticket.user and getattr(ticket.user, "specialty", None):
        sp = ticket.user.specialty
        specialty_value = sp.value if hasattr(sp, "value") else str(sp)
    _add("CLICKUP_FIELD_SPECIALITA", specialty_value)

    _add("CLICKUP_FIELD_CLIENTE_COINVOLTO", ticket.cliente_coinvolto)
    _add("CLICKUP_FIELD_BROWSER", ticket.browser)
    _add("CLICKUP_FIELD_OS", ticket.os)
    _add("CLICKUP_FIELD_VERSIONE_APP", ticket.versione_app)
    _add("CLICKUP_FIELD_COMMIT_SHA", ticket.commit_sha)
    _add("CLICKUP_FIELD_LINK_REGISTRAZIONE", ticket.link_registrazione)

    return fields


def build_description(ticket) -> str:
    """
    Costruisce il body della task ClickUp con un blocco 'Contesto tecnico'
    in coda, utile al team IT per debug.
    """
    base = (ticket.description or "").strip()

    tech_lines: List[str] = []
    if ticket.pagina_origine:
        tech_lines.append(f"- URL: {ticket.pagina_origine}")
    if ticket.browser or ticket.os:
        tech_lines.append(
            "- Browser/OS: "
            + " / ".join(filter(None, [ticket.browser, ticket.os]))
        )
    if ticket.versione_app:
        version_line = f"- Versione app: {ticket.versione_app}"
        if ticket.commit_sha:
            version_line += f" (commit `{ticket.commit_sha}`)"
        tech_lines.append(version_line)
    if ticket.user_agent_raw:
        tech_lines.append(f"- User-Agent: `{ticket.user_agent_raw[:400]}`")
    if ticket.cliente_coinvolto:
        tech_lines.append(f"- Cliente coinvolto: {ticket.cliente_coinvolto}")
    if ticket.user and ticket.user.email:
        tech_lines.append(f"- Aperto da: {ticket.user.full_name} ({ticket.user.email})")
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
    """Tag che verranno applicati al task ClickUp."""
    tags: List[str] = []
    if ticket.user and getattr(ticket.user, "role", None):
        role = ticket.user.role
        role_value = role.value if hasattr(role, "value") else str(role)
        tags.append(f"ruolo:{role_value}")
    if ticket.user and getattr(ticket.user, "specialty", None):
        sp = ticket.user.specialty
        sp_value = sp.value if hasattr(sp, "value") else str(sp)
        tags.append(f"spec:{sp_value}")
    if ticket.user and getattr(ticket.user, "is_trial", False):
        tags.append("trial")
    if ticket.modulo:
        tags.append(f"modulo:{ticket.modulo.value}")
    if ticket.tipo:
        tags.append(f"tipo:{ticket.tipo.value}")
    return tags
