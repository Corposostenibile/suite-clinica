"""Servizi per il flusso SalesLead proveniente da GHL.

Questo modulo normalizza i payload webhook GHL e li salva nel modello
canonico `SalesLead`, mantenendo il flusso allineato al resto del backend
Sales.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from flask import current_app
from sqlalchemy import func

from corposostenibile.extensions import db
from corposostenibile.models import LeadStatusEnum, SalesLead, User

logger = logging.getLogger(__name__)


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
            continue
        return value
    return None


def _normalize_custom_data(raw_custom_data: Any) -> Dict[str, Any]:
    """Normalizza customData GHL in un dict key->value."""
    if isinstance(raw_custom_data, str):
        try:
            raw_custom_data = json.loads(raw_custom_data)
        except (ValueError, TypeError):
            return {}

    if isinstance(raw_custom_data, dict):
        return raw_custom_data

    if isinstance(raw_custom_data, list):
        normalized: Dict[str, Any] = {}
        for item in raw_custom_data:
            if not isinstance(item, dict):
                continue
            key = (
                item.get("key")
                or item.get("field")
                or item.get("fieldName")
                or item.get("name")
                or item.get("id")
            )
            if not key:
                continue
            value = (
                item.get("value")
                if "value" in item
                else item.get("field_value")
                if "field_value" in item
                else item.get("val")
            )
            normalized[str(key)] = value
        return normalized

    return {}


def _coerce_incoming_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Deserializza eventuali wrapper JSON string nei payload webhook GHL."""
    if not isinstance(payload, dict):
        return {}

    normalized = dict(payload)
    for wrapper_key in ("payload", "data", "body", "raw_payload"):
        wrapper_value = normalized.get(wrapper_key)
        if not isinstance(wrapper_value, str):
            continue
        try:
            decoded = json.loads(wrapper_value)
        except (ValueError, TypeError):
            continue
        if isinstance(decoded, dict):
            normalized.update(decoded)

    return normalized


def _split_full_name(full_name: str | None) -> tuple[str, str]:
    name = (full_name or "").strip()
    if not name:
        return "N/D", "N/D"

    parts = [part for part in name.split() if part]
    if len(parts) == 1:
        return parts[0], parts[0]
    return parts[0], " ".join(parts[1:])


def _extract_sales_user_email(*, custom_data: Dict[str, Any], payload: Dict[str, Any], opportunity: Dict[str, Any]) -> Optional[str]:
    sales_user = custom_data.get("sales_user") or payload.get("sales_user") or opportunity.get("sales_user")
    if isinstance(sales_user, dict):
        candidate = _first_non_empty(
            sales_user.get("email"),
            sales_user.get("mail"),
        )
        if candidate:
            return str(candidate).strip().lower()

    candidate = _first_non_empty(
        custom_data.get("sales_user_email"),
        custom_data.get("sales_owner_email"),
        custom_data.get("sales_person_email"),
        custom_data.get("sales_consultant_email"),
        custom_data.get("owner_email"),
        custom_data.get("consultant_email"),
        payload.get("sales_user_email"),
        payload.get("sales_owner_email"),
        payload.get("sales_person_email"),
        payload.get("sales_consultant_email"),
        payload.get("owner_email"),
        payload.get("consultant_email"),
        opportunity.get("sales_user_email"),
        opportunity.get("sales_owner_email"),
        opportunity.get("sales_person_email"),
        opportunity.get("sales_consultant_email"),
    )
    return str(candidate).strip().lower() if candidate else None


def _extract_text_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _first_non_empty(
            value.get("name"),
            value.get("full_name"),
            value.get("fullName"),
            value.get("label"),
            value.get("value"),
            value.get("email"),
        )
    return value


def _extract_ghl_lead_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Estrae i campi normalizzati dal payload webhook GHL."""
    payload = _coerce_incoming_payload(payload)
    opportunity = payload.get("opportunity", {}) if isinstance(payload.get("opportunity"), dict) else {}
    contact = payload.get("contact", {}) if isinstance(payload.get("contact"), dict) else {}

    custom_data: Dict[str, Any] = {}
    for raw_custom_data in (
        opportunity.get("custom_fields", {}),
        opportunity.get("customData", {}),
        payload.get("custom_fields", {}),
        payload.get("customData", {}),
    ):
        custom_data.update(_normalize_custom_data(raw_custom_data))

    first_name = _first_non_empty(
        custom_data.get("first_name"),
        custom_data.get("nome"),
        payload.get("first_name"),
        payload.get("nome"),
        opportunity.get("first_name"),
        opportunity.get("nome"),
        contact.get("first_name"),
        contact.get("name"),
        payload.get("name"),
        opportunity.get("name"),
    )
    last_name = _first_non_empty(
        custom_data.get("last_name"),
        custom_data.get("cognome"),
        payload.get("last_name"),
        payload.get("cognome"),
        opportunity.get("last_name"),
        opportunity.get("cognome"),
        contact.get("last_name"),
    )

    full_name = _first_non_empty(
        custom_data.get("nome_completo"),
        custom_data.get("full_name"),
        payload.get("nome_completo"),
        payload.get("full_name"),
        opportunity.get("nome_completo"),
        opportunity.get("full_name"),
        contact.get("name"),
        payload.get("name"),
        opportunity.get("name"),
    )

    if not first_name or not last_name:
        split_first, split_last = _split_full_name(full_name)
        first_name = first_name or split_first
        last_name = last_name or split_last

    email = _first_non_empty(
        custom_data.get("email"),
        payload.get("email"),
        opportunity.get("email"),
        contact.get("email"),
    )

    phone = _first_non_empty(
        custom_data.get("telefono"),
        custom_data.get("phone"),
        custom_data.get("cellulare"),
        custom_data.get("mobile"),
        custom_data.get("phone_number"),
        payload.get("telefono"),
        payload.get("phone"),
        payload.get("cellulare"),
        payload.get("mobile"),
        payload.get("phone_number"),
        opportunity.get("phone"),
        opportunity.get("mobile"),
        contact.get("phone"),
        contact.get("mobile"),
    )

    health_manager_email = _first_non_empty(
        custom_data.get("health_manager_email"),
        custom_data.get("healthmanager_email"),
        custom_data.get("email_health_manager"),
        custom_data.get("hm_email"),
        payload.get("health_manager_email"),
        payload.get("healthmanager_email"),
        payload.get("email_health_manager"),
        payload.get("hm_email"),
        opportunity.get("health_manager_email"),
    )
    if isinstance(health_manager_email, str):
        health_manager_email = health_manager_email.strip().lower() or None

    sales_user_email = _extract_sales_user_email(
        custom_data=custom_data,
        payload=payload,
        opportunity=opportunity,
    )

    sales_user_name = _first_non_empty(
        _extract_text_value(custom_data.get("sales_consultant")),
        _extract_text_value(custom_data.get("sales_person")),
        _extract_text_value(custom_data.get("sales_user")),
        _extract_text_value(custom_data.get("sales_owner")),
        _extract_text_value(custom_data.get("sales_rep")),
        _extract_text_value(custom_data.get("consultant")),
        _extract_text_value(custom_data.get("owner")),
        _extract_text_value(custom_data.get("consulente")),
        _extract_text_value(payload.get("sales_consultant")),
        _extract_text_value(payload.get("sales_person")),
        _extract_text_value(payload.get("sales_user")),
        _extract_text_value(payload.get("sales_owner")),
        _extract_text_value(payload.get("sales_rep")),
        _extract_text_value(payload.get("consultant")),
        _extract_text_value(payload.get("owner")),
        _extract_text_value(payload.get("consulente")),
        _extract_text_value(opportunity.get("sales_consultant")),
        _extract_text_value(opportunity.get("sales_person")),
        _extract_text_value(opportunity.get("sales_user")),
        _extract_text_value(opportunity.get("sales_owner")),
    )

    story = _first_non_empty(
        custom_data.get("storia"),
        custom_data.get("story"),
        custom_data.get("note"),
        custom_data.get("notes"),
        payload.get("storia"),
        payload.get("story"),
        payload.get("note"),
        payload.get("notes"),
        opportunity.get("storia"),
        opportunity.get("story"),
        opportunity.get("note"),
        contact.get("notes"),
    )

    package_name = _first_non_empty(
        custom_data.get("pacchetto"),
        custom_data.get("package"),
        custom_data.get("plan"),
        payload.get("pacchetto"),
        payload.get("package"),
        payload.get("plan"),
        opportunity.get("pacchetto"),
        opportunity.get("package"),
        opportunity.get("plan"),
    )

    origin = _first_non_empty(
        custom_data.get("origin"),
        custom_data.get("origine"),
        custom_data.get("origine_contatto"),
        custom_data.get("source"),
        payload.get("origin"),
        payload.get("origine"),
        payload.get("source"),
        opportunity.get("origin"),
        opportunity.get("source"),
        contact.get("source"),
        "GHL",
    )

    source_campaign = _first_non_empty(
        custom_data.get("source_campaign"),
        custom_data.get("utm_campaign"),
        payload.get("source_campaign"),
        opportunity.get("source_campaign"),
        payload.get("utm_campaign"),
        opportunity.get("utm_campaign"),
    )
    source_medium = _first_non_empty(
        custom_data.get("source_medium"),
        custom_data.get("utm_medium"),
        payload.get("source_medium"),
        opportunity.get("source_medium"),
        payload.get("utm_medium"),
        opportunity.get("utm_medium"),
    )
    source_url = _first_non_empty(
        custom_data.get("source_url"),
        custom_data.get("page_url"),
        custom_data.get("url"),
        payload.get("source_url"),
        opportunity.get("source_url"),
        payload.get("page_url"),
        payload.get("url"),
    )
    referrer_url = _first_non_empty(
        custom_data.get("referrer_url"),
        payload.get("referrer_url"),
        opportunity.get("referrer_url"),
    )
    landing_page = _first_non_empty(
        custom_data.get("landing_page"),
        payload.get("landing_page"),
        opportunity.get("landing_page"),
        payload.get("page_url"),
    )
    utm_source = _first_non_empty(custom_data.get("utm_source"), payload.get("utm_source"), opportunity.get("utm_source"))
    utm_medium = _first_non_empty(custom_data.get("utm_medium"), payload.get("utm_medium"), opportunity.get("utm_medium"))
    utm_campaign = _first_non_empty(custom_data.get("utm_campaign"), payload.get("utm_campaign"), opportunity.get("utm_campaign"))
    utm_term = _first_non_empty(custom_data.get("utm_term"), payload.get("utm_term"), opportunity.get("utm_term"))
    utm_content = _first_non_empty(custom_data.get("utm_content"), payload.get("utm_content"), opportunity.get("utm_content"))

    return {
        "custom_data": custom_data,
        "event_type": payload.get("event_type"),
        "timestamp": payload.get("timestamp") or datetime.utcnow().isoformat(),
        "ghl_opportunity_id": opportunity.get("id"),
        "ghl_contact_id": contact.get("id"),
        "first_name": str(first_name or "N/D").strip(),
        "last_name": str(last_name or "N/D").strip(),
        "email": str(email or "").strip().lower(),
        "phone": str(phone).strip() if phone else None,
        "health_manager_email": health_manager_email,
        "sales_user_email": sales_user_email,
        "sales_user_name": sales_user_name,
        "story": str(story).strip() if story else None,
        "package_name": str(package_name).strip() if package_name else None,
        "origin": str(origin).strip() if origin else None,
        "source_campaign": str(source_campaign).strip() if source_campaign else None,
        "source_medium": str(source_medium).strip() if source_medium else None,
        "source_url": str(source_url).strip() if source_url else None,
        "referrer_url": str(referrer_url).strip() if referrer_url else None,
        "landing_page": str(landing_page).strip() if landing_page else None,
        "utm_source": str(utm_source).strip() if utm_source else None,
        "utm_medium": str(utm_medium).strip() if utm_medium else None,
        "utm_campaign": str(utm_campaign).strip() if utm_campaign else None,
        "utm_term": str(utm_term).strip() if utm_term else None,
        "utm_content": str(utm_content).strip() if utm_content else None,
        "raw_payload": payload,
    }


def _resolve_user_by_email(email: str | None) -> Optional[User]:
    if not email:
        return None
    normalized = email.strip().lower()
    if not normalized:
        return None
    return User.query.filter(
        func.lower(User.email) == normalized,
        User.is_active == True,  # noqa: E712
    ).first()


def _generate_unique_code() -> str:
    return f"GHL-LEAD-{datetime.utcnow().year}-{uuid.uuid4().hex[:8].upper()}"


def save_sales_lead_from_ghl_payload(payload: Dict[str, Any], client_ip: str) -> Tuple[SalesLead, bool]:
    """Salva/aggiorna un SalesLead partendo da un payload GHL.

    Returns:
        (lead, created)
    """
    normalized = _extract_ghl_lead_fields(payload)
    if not normalized["email"]:
        raise ValueError("Campo email mancante nel payload GHL")

    sales_user = _resolve_user_by_email(normalized.get("sales_user_email"))
    health_manager = _resolve_user_by_email(normalized.get("health_manager_email"))

    lead = SalesLead.query.filter(
        func.lower(SalesLead.email) == normalized["email"],
        SalesLead.source_system == "ghl",
    ).first()
    created = lead is None

    if not lead:
        lead = SalesLead(
            source_system="ghl",
            unique_code=_generate_unique_code(),
            first_name=normalized["first_name"],
            last_name=normalized["last_name"],
            email=normalized["email"],
            status=LeadStatusEnum.NEW,
        )
        db.session.add(lead)

    previous_sales_user_id = lead.sales_user_id
    previous_health_manager_id = lead.health_manager_id

    lead.first_name = normalized["first_name"] or lead.first_name
    lead.last_name = normalized["last_name"] or lead.last_name
    lead.email = normalized["email"] or lead.email
    lead.phone = normalized.get("phone") or lead.phone
    lead.source_system = "ghl"
    lead.origin = normalized.get("origin") or lead.origin or "GHL"
    lead.client_story = normalized.get("story") or lead.client_story
    lead.custom_package_name = normalized.get("package_name") or lead.custom_package_name
    lead.source_campaign = normalized.get("source_campaign") or lead.source_campaign
    lead.source_medium = normalized.get("source_medium") or lead.source_medium
    lead.source_url = normalized.get("source_url") or lead.source_url
    lead.referrer_url = normalized.get("referrer_url") or lead.referrer_url
    lead.landing_page = normalized.get("landing_page") or lead.landing_page
    lead.utm_source = normalized.get("utm_source") or lead.utm_source
    lead.utm_medium = normalized.get("utm_medium") or lead.utm_medium
    lead.utm_campaign = normalized.get("utm_campaign") or lead.utm_campaign
    lead.utm_term = normalized.get("utm_term") or lead.utm_term
    lead.utm_content = normalized.get("utm_content") or lead.utm_content
    lead.ip_address = client_ip or lead.ip_address
    lead.form_responses = {
        "source_system": "ghl",
        "event_type": normalized.get("event_type"),
        "timestamp": normalized.get("timestamp"),
        "ghl_opportunity_id": normalized.get("ghl_opportunity_id"),
        "ghl_contact_id": normalized.get("ghl_contact_id"),
        "sales_user_email": normalized.get("sales_user_email"),
        "sales_user_name": normalized.get("sales_user_name"),
        "health_manager_email": normalized.get("health_manager_email"),
        "custom_fields": normalized.get("custom_data") or {},
        "raw_payload": normalized.get("raw_payload") or {},
    }

    if sales_user:
        lead.sales_user_id = sales_user.id
    if health_manager:
        lead.health_manager_id = health_manager.id

    db.session.flush()

    lead.add_activity_log(
        "created" if created else "updated",
        "Lead GHL importata da webhook firmato",
        user_id=sales_user.id if sales_user else None,
        metadata={
            "source_system": "ghl",
            "sales_user_email": normalized.get("sales_user_email"),
            "health_manager_email": normalized.get("health_manager_email"),
        },
    )

    if previous_sales_user_id != lead.sales_user_id and lead.sales_user_id:
        lead.add_activity_log(
            "assigned",
            "Sales user risolto da email GHL",
            user_id=lead.sales_user_id,
            metadata={"sales_user_id": lead.sales_user_id},
        )

    if previous_health_manager_id != lead.health_manager_id and lead.health_manager_id:
        lead.add_activity_log(
            "assigned",
            "Health manager risolto da email GHL",
            user_id=lead.health_manager_id,
            metadata={"health_manager_id": lead.health_manager_id},
        )

    db.session.commit()

    try:
        from corposostenibile.blueprints.sales_form.services import LinkService

        LinkService.create_all_links_for_lead(lead.id, lead.sales_user_id)
    except Exception as exc:  # noqa: BLE001
        current_app.logger.warning(
            "[sales_ghl_assignments] impossibile generare i link check per lead %s: %s",
            lead.id,
            exc,
        )

    current_app.logger.info(
        "[sales_ghl_assignments] Lead GHL salvata: id=%s email=%s sales_user_id=%s created=%s",
        lead.id,
        lead.email,
        lead.sales_user_id,
        created,
    )

    return lead, created


def serialize_sales_lead(lead: SalesLead) -> Dict[str, Any]:
    """Serializza una SalesLead GHL per API e debug."""
    sales_user = lead.sales_user
    return {
        "id": lead.id,
        "unique_code": lead.unique_code,
        "source_system": lead.source_system,
        "first_name": lead.first_name,
        "last_name": lead.last_name,
        "full_name": getattr(lead, "full_name", f"{lead.first_name} {lead.last_name}".strip()),
        "email": lead.email,
        "phone": lead.phone,
        "status": lead.status.value if hasattr(lead.status, "value") else str(lead.status),
        "sales_user_id": lead.sales_user_id,
        "sales_user": (
            {
                "id": sales_user.id,
                "full_name": sales_user.full_name,
                "email": sales_user.email,
                "role": sales_user.role.value if hasattr(sales_user.role, "value") else str(sales_user.role or ""),
            }
            if sales_user
            else None
        ),
        "health_manager_id": lead.health_manager_id,
        "origin": lead.origin,
        "client_story": lead.client_story,
        "custom_package_name": lead.custom_package_name,
        "form_link_id": lead.form_link_id,
        "converted_to_client_id": lead.converted_to_client_id,
        "assigned_nutritionist_id": lead.assigned_nutritionist_id,
        "assigned_coach_id": lead.assigned_coach_id,
        "assigned_psychologist_id": lead.assigned_psychologist_id,
        "assigned_by": lead.assigned_by,
        "assigned_at": lead.assigned_at.isoformat() if lead.assigned_at else None,
        "assignment_notes": lead.assignment_notes,
        "ai_analysis": lead.ai_analysis,
        "ai_analysis_snapshot": lead.ai_analysis_snapshot,
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
        "updated_at": lead.updated_at.isoformat() if lead.updated_at else None,
    }
