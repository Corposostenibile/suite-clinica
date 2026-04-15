"""
Service layer di business logic per i ticket GHL.

Orchestrazione:
- creazione ticket (DB → enqueue Celery per push ClickUp)
- post commento utente GHL (DB → enqueue Celery per echo ClickUp)
- upload allegato (DB → enqueue Celery per upload ClickUp)
- aggiornamento da webhook ClickUp (status, commenti in ingresso)

L'identità utente NON viene dal DB (utente esterno GHL): viene passata come
parametri dai chiamanti che hanno già validato la sessione JWT GHL.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask import current_app

from corposostenibile.extensions import db
from corposostenibile.models import (
    GHLSupportTicket,
    GHLSupportTicketAttachment,
    GHLSupportTicketComment,
    GHLSupportTicketStatusEnum,
)

from .field_mapping import map_status_from_clickup

logger = logging.getLogger(__name__)


class GHLSupportTicketService:
    """Operazioni ad alto livello sui ticket GHL."""

    # ─── Create ─────────────────────────────────────────────────────────────

    @staticmethod
    def create_ticket(
        *,
        ghl_user_id: str,
        ghl_user_email: Optional[str],
        ghl_user_name: Optional[str],
        ghl_user_role: Optional[str],
        ghl_location_id: Optional[str],
        ghl_location_name: Optional[str],
        title: str,
        description: str,
        pagina_origine: Optional[str] = None,
        browser: Optional[str] = None,
        os: Optional[str] = None,
        user_agent_raw: Optional[str] = None,
    ) -> GHLSupportTicket:
        """Crea il ticket in DB e pianifica la push verso ClickUp."""
        ticket = GHLSupportTicket(
            ticket_number=GHLSupportTicket.generate_ticket_number(),
            ghl_user_id=ghl_user_id,
            ghl_user_email=(ghl_user_email or None),
            ghl_user_name=(ghl_user_name or None),
            ghl_user_role=(ghl_user_role or None),
            ghl_location_id=(ghl_location_id or None),
            ghl_location_name=(ghl_location_name or None),
            title=title.strip()[:255],
            description=description.strip(),
            pagina_origine=(pagina_origine or None),
            browser=(browser or None),
            os=(os or None),
            user_agent_raw=(user_agent_raw or None),
            status=GHLSupportTicketStatusEnum.nuovo,
        )
        db.session.add(ticket)
        db.session.commit()

        if current_app.config.get("CLICKUP_GHL_INTEGRATION_ENABLED", False):
            from ..tasks import push_ticket_to_clickup_ghl
            push_ticket_to_clickup_ghl.delay(ticket.id)
        else:
            logger.info(
                "[ghl_support] ClickUp integration DISABLED, ticket %s creato solo in DB",
                ticket.ticket_number,
            )

        return ticket

    # ─── Comments ───────────────────────────────────────────────────────────

    @staticmethod
    def add_comment_from_ghl_user(
        ticket: GHLSupportTicket,
        *,
        ghl_user_id: str,
        ghl_user_name: Optional[str],
        content: str,
    ) -> GHLSupportTicketComment:
        """Aggiunge un commento dall'utente GHL. Verrà replicato su ClickUp."""
        comment = GHLSupportTicketComment(
            ticket_id=ticket.id,
            author_ghl_user_id=ghl_user_id,
            author_ghl_user_name=ghl_user_name,
            content=content.strip(),
            direction="from_ghl",
        )
        db.session.add(comment)
        db.session.commit()

        if (
            current_app.config.get("CLICKUP_GHL_INTEGRATION_ENABLED", False)
            and ticket.clickup_task_id
        ):
            from ..tasks import push_comment_to_clickup_ghl
            push_comment_to_clickup_ghl.delay(comment.id)

        return comment

    @staticmethod
    def ingest_comment_from_clickup(
        ticket: GHLSupportTicket,
        *,
        clickup_comment_id: str,
        content: str,
        author_name: Optional[str],
    ) -> Optional[GHLSupportTicketComment]:
        """
        Crea un commento locale ricevuto via webhook ClickUp.
        Idempotente sul `clickup_comment_id`.
        """
        if not clickup_comment_id:
            logger.warning("[ghl_support] commento ClickUp senza id, skip")
            return None

        existing = GHLSupportTicketComment.query.filter_by(
            clickup_comment_id=clickup_comment_id
        ).first()
        if existing:
            return existing

        comment = GHLSupportTicketComment(
            ticket_id=ticket.id,
            author_ghl_user_id=None,
            author_ghl_user_name=None,
            author_name_external=author_name or "Team IT",
            content=(content or "").strip(),
            clickup_comment_id=clickup_comment_id,
            direction="from_clickup",
        )
        db.session.add(comment)
        db.session.commit()
        return comment

    # ─── Status from webhook ────────────────────────────────────────────────

    @staticmethod
    def update_status_from_clickup(
        ticket: GHLSupportTicket,
        clickup_status_name: str,
    ) -> bool:
        """Aggiorna lo status locale dal webhook. Restituisce True se cambiato."""
        new_status = map_status_from_clickup(clickup_status_name)
        if not new_status:
            logger.warning(
                "[ghl_support] status ClickUp ignoto '%s' per ticket %s",
                clickup_status_name,
                ticket.ticket_number,
            )
            return False

        if ticket.status == new_status:
            return False

        ticket.status = new_status
        ticket.last_synced_at = datetime.utcnow()
        if new_status in (
            GHLSupportTicketStatusEnum.risolto,
            GHLSupportTicketStatusEnum.non_valido,
        ):
            ticket.closed_at = ticket.closed_at or datetime.utcnow()
        elif new_status != GHLSupportTicketStatusEnum.risolto:
            ticket.closed_at = None

        db.session.commit()
        return True

    # ─── Queries ────────────────────────────────────────────────────────────

    @staticmethod
    def get_user_tickets(
        ghl_user_id: str,
        *,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[GHLSupportTicket]:
        query = GHLSupportTicket.query.filter_by(ghl_user_id=ghl_user_id)
        if status:
            query = query.filter(GHLSupportTicket.status == status)
        return (
            query.order_by(GHLSupportTicket.created_at.desc()).limit(limit).all()
        )

    @staticmethod
    def get_by_id_for_ghl_user(
        ticket_id: int, ghl_user_id: str
    ) -> Optional[GHLSupportTicket]:
        """Restituisce il ticket se l'utente GHL può vederlo (solo owner)."""
        ticket = GHLSupportTicket.query.get(ticket_id)
        if not ticket:
            return None
        if ticket.ghl_user_id == ghl_user_id:
            return ticket
        return None
