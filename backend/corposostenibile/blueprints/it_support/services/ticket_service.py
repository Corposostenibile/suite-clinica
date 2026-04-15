"""
Service layer di business logic per i ticket IT.

Orchestrazione:
- creazione ticket (DB → enqueue Celery per push ClickUp)
- post commento (DB → enqueue Celery per echo ClickUp)
- upload allegato (DB → enqueue Celery per upload ClickUp)
- aggiornamento da webhook ClickUp (status, commenti in ingresso)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask import current_app

from corposostenibile.extensions import db
from corposostenibile.models import (
    ITSupportTicket,
    ITSupportTicketAttachment,
    ITSupportTicketComment,
    ITSupportTicketCriticitaEnum,
    ITSupportTicketModuloEnum,
    ITSupportTicketStatusEnum,
    ITSupportTicketTipoEnum,
    User,
)

from .field_mapping import map_status_from_clickup

logger = logging.getLogger(__name__)


class ITSupportTicketService:
    """Operazioni ad alto livello sui ticket IT."""

    # ─── Create ─────────────────────────────────────────────────────────────

    @staticmethod
    def create_ticket(
        *,
        user: User,
        title: str,
        description: str,
        tipo: ITSupportTicketTipoEnum,
        modulo: ITSupportTicketModuloEnum,
        criticita: ITSupportTicketCriticitaEnum,
        cliente_coinvolto: Optional[str] = None,
        link_registrazione: Optional[str] = None,
        pagina_origine: Optional[str] = None,
        browser: Optional[str] = None,
        os: Optional[str] = None,
        versione_app: Optional[str] = None,
        commit_sha: Optional[str] = None,
        user_agent_raw: Optional[str] = None,
    ) -> ITSupportTicket:
        """Crea il ticket in DB e pianifica la push verso ClickUp."""
        ticket = ITSupportTicket(
            ticket_number=ITSupportTicket.generate_ticket_number(),
            user_id=user.id,
            title=title.strip()[:255],
            description=description.strip(),
            tipo=tipo,
            modulo=modulo,
            criticita=criticita,
            cliente_coinvolto=(cliente_coinvolto or None),
            link_registrazione=(link_registrazione or None),
            pagina_origine=(pagina_origine or None),
            browser=(browser or None),
            os=(os or None),
            versione_app=(versione_app or None),
            commit_sha=(commit_sha or None),
            user_agent_raw=(user_agent_raw or None),
            status=ITSupportTicketStatusEnum.nuovo,
        )
        db.session.add(ticket)
        db.session.commit()

        # Enqueue push verso ClickUp (import qui per evitare circular import)
        if current_app.config.get("CLICKUP_INTEGRATION_ENABLED", False):
            from ..tasks import push_ticket_to_clickup
            push_ticket_to_clickup.delay(ticket.id)
        else:
            logger.info(
                "[it_support] ClickUp integration DISABLED, ticket %s creato solo in DB",
                ticket.ticket_number,
            )

        return ticket

    # ─── Comments ───────────────────────────────────────────────────────────

    @staticmethod
    def add_comment_from_user(
        ticket: ITSupportTicket,
        author: User,
        content: str,
    ) -> ITSupportTicketComment:
        """Aggiunge un commento dall'utente Suite. Verrà replicato su ClickUp."""
        comment = ITSupportTicketComment(
            ticket_id=ticket.id,
            author_user_id=author.id,
            content=content.strip(),
            direction="from_suite",
        )
        db.session.add(comment)
        db.session.commit()

        if (
            current_app.config.get("CLICKUP_INTEGRATION_ENABLED", False)
            and ticket.clickup_task_id
        ):
            from ..tasks import push_comment_to_clickup
            push_comment_to_clickup.delay(comment.id)

        return comment

    @staticmethod
    def ingest_comment_from_clickup(
        ticket: ITSupportTicket,
        *,
        clickup_comment_id: str,
        content: str,
        author_name: Optional[str],
    ) -> Optional[ITSupportTicketComment]:
        """
        Crea un commento locale ricevuto via webhook ClickUp.
        Idempotente sul `clickup_comment_id`.
        """
        if not clickup_comment_id:
            logger.warning("[it_support] commento ClickUp senza id, skip")
            return None

        existing = ITSupportTicketComment.query.filter_by(
            clickup_comment_id=clickup_comment_id
        ).first()
        if existing:
            return existing

        comment = ITSupportTicketComment(
            ticket_id=ticket.id,
            author_user_id=None,
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
        ticket: ITSupportTicket,
        clickup_status_name: str,
    ) -> bool:
        """Aggiorna lo status locale dal webhook. Restituisce True se cambiato."""
        new_status = map_status_from_clickup(clickup_status_name)
        if not new_status:
            logger.warning(
                "[it_support] status ClickUp ignoto '%s' per ticket %s",
                clickup_status_name,
                ticket.ticket_number,
            )
            return False

        if ticket.status == new_status:
            return False

        ticket.status = new_status
        ticket.last_synced_at = datetime.utcnow()
        if new_status in (
            ITSupportTicketStatusEnum.risolto,
            ITSupportTicketStatusEnum.non_valido,
        ):
            ticket.closed_at = ticket.closed_at or datetime.utcnow()
        elif new_status != ITSupportTicketStatusEnum.risolto:
            ticket.closed_at = None

        db.session.commit()
        return True

    # ─── Queries ────────────────────────────────────────────────────────────

    @staticmethod
    def get_user_tickets(
        user_id: int,
        *,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[ITSupportTicket]:
        query = ITSupportTicket.query.filter_by(user_id=user_id)
        if status:
            query = query.filter(ITSupportTicket.status == status)
        return (
            query.order_by(ITSupportTicket.created_at.desc()).limit(limit).all()
        )

    @staticmethod
    def get_by_id_for_user(ticket_id: int, user_id: int, *, is_admin: bool = False) -> Optional[ITSupportTicket]:
        """Restituisce il ticket se l'utente può vederlo (owner o admin)."""
        ticket = ITSupportTicket.query.get(ticket_id)
        if not ticket:
            return None
        if is_admin or ticket.user_id == user_id:
            return ticket
        return None


def _safe_commit() -> None:
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("[it_support] commit fallito")
        raise
