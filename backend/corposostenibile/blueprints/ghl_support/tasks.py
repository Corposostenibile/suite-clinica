"""
Celery async tasks per l'integrazione ClickUp (GHL variant).

Pattern identico a it_support/tasks.py ma scopato sul nuovo Space GHL.
Niente priority (triage manuale su ClickUp), tag auto da build_tags.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from celery import current_app as celery_app
from celery.utils.log import get_task_logger

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import (
    GHLSupportTicket,
    GHLSupportTicketAttachment,
    GHLSupportTicketComment,
)

from .services import ClickUpClient, ClickUpError
from .services.field_mapping import (
    build_custom_fields_payload,
    build_description,
    build_tags,
    map_status_to_clickup,
)

logger = get_task_logger(__name__)


# ─── Push ticket → ClickUp task ────────────────────────────────────────────


@celery_app.task(
    bind=True,
    name="ghl_support.push_ticket_to_clickup",
    max_retries=5,
    default_retry_delay=60,
)
def push_ticket_to_clickup_ghl(self, ticket_id: int) -> Dict[str, Any]:
    """Crea il task ClickUp per il ticket GHL appena salvato in DB."""
    app = create_app()
    with app.app_context():
        ticket = GHLSupportTicket.query.get(ticket_id)
        if not ticket:
            logger.warning("[ghl_support] ticket %s non trovato, skip", ticket_id)
            return {"ok": False, "reason": "ticket_not_found"}

        if ticket.clickup_task_id:
            logger.info(
                "[ghl_support] ticket %s già sincronizzato (task %s), skip",
                ticket.ticket_number,
                ticket.clickup_task_id,
            )
            return {"ok": True, "skipped": True, "task_id": ticket.clickup_task_id}

        if not app.config.get("CLICKUP_GHL_INTEGRATION_ENABLED", False):
            logger.info("[ghl_support] integrazione ClickUp GHL disabilitata, skip")
            return {"ok": False, "reason": "disabled"}

        try:
            client = ClickUpClient.from_app_config(app)
            task_payload = {
                "name": ticket.title,
                "description": build_description(ticket),
                "custom_fields": build_custom_fields_payload(ticket),
                "tags": build_tags(ticket),
                "status": map_status_to_clickup(ticket.status),
            }
            response = client.create_task(**task_payload)
            ticket.clickup_task_id = str(response.get("id") or "")
            ticket.clickup_task_url = response.get("url") or None
            ticket.last_synced_at = datetime.utcnow()
            ticket.sync_error = None
            ticket.sync_attempts = (ticket.sync_attempts or 0) + 1
            db.session.commit()

            logger.info(
                "[ghl_support] ticket %s pushato su ClickUp (task %s)",
                ticket.ticket_number,
                ticket.clickup_task_id,
            )

            # dopo il create, pusha allegati pre-esistenti
            for att in ticket.attachments:
                if not att.synced_to_clickup:
                    push_attachment_to_clickup_ghl.delay(att.id)

            return {
                "ok": True,
                "task_id": ticket.clickup_task_id,
                "url": ticket.clickup_task_url,
            }
        except ClickUpError as exc:
            logger.error(
                "[ghl_support] errore push ticket %s: %s",
                ticket.ticket_number,
                exc,
            )
            ticket.sync_error = str(exc)[:500]
            ticket.sync_attempts = (ticket.sync_attempts or 0) + 1
            db.session.commit()
            raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))
        except Exception as exc:  # noqa: BLE001
            logger.exception("[ghl_support] exception push ticket %s", ticket.ticket_number)
            ticket.sync_error = f"exception: {exc!r}"[:500]
            ticket.sync_attempts = (ticket.sync_attempts or 0) + 1
            db.session.commit()
            raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


# ─── Push comment → ClickUp ────────────────────────────────────────────────


@celery_app.task(
    bind=True,
    name="ghl_support.push_comment_to_clickup",
    max_retries=5,
    default_retry_delay=30,
)
def push_comment_to_clickup_ghl(self, comment_id: int) -> Dict[str, Any]:
    app = create_app()
    with app.app_context():
        comment = GHLSupportTicketComment.query.get(comment_id)
        if not comment:
            logger.warning("[ghl_support] commento %s non trovato, skip", comment_id)
            return {"ok": False, "reason": "comment_not_found"}

        if comment.direction != "from_ghl":
            return {"ok": False, "reason": "wrong_direction"}

        if comment.clickup_comment_id:
            return {"ok": True, "skipped": True}

        ticket = comment.ticket
        if not ticket or not ticket.clickup_task_id:
            logger.info(
                "[ghl_support] ticket del commento %s non ancora sync, retry",
                comment.id,
            )
            raise self.retry(countdown=30)

        if not app.config.get("CLICKUP_GHL_INTEGRATION_ENABLED", False):
            return {"ok": False, "reason": "disabled"}

        author_name = comment.author_ghl_user_name or "Utente GHL"
        text = f"**{author_name}** (da GoHighLevel):\n\n{comment.content}"

        try:
            client = ClickUpClient.from_app_config(app)
            response = client.post_comment(
                task_id=ticket.clickup_task_id,
                comment_text=text,
                notify_all=True,
            )
            clickup_comment_id = str(
                response.get("id")
                or response.get("hist_id")
                or response.get("comment_id")
                or ""
            )
            if clickup_comment_id:
                comment.clickup_comment_id = clickup_comment_id
                db.session.commit()
            return {"ok": True, "clickup_comment_id": clickup_comment_id}
        except ClickUpError as exc:
            logger.error(
                "[ghl_support] errore push comment %s: %s",
                comment.id,
                exc,
            )
            raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))


# ─── Push attachment → ClickUp ────────────────────────────────────────────


@celery_app.task(
    bind=True,
    name="ghl_support.push_attachment_to_clickup",
    max_retries=5,
    default_retry_delay=30,
)
def push_attachment_to_clickup_ghl(self, attachment_id: int) -> Dict[str, Any]:
    app = create_app()
    with app.app_context():
        att = GHLSupportTicketAttachment.query.get(attachment_id)
        if not att:
            logger.warning("[ghl_support] allegato %s non trovato, skip", attachment_id)
            return {"ok": False, "reason": "attachment_not_found"}

        if att.synced_to_clickup:
            return {"ok": True, "skipped": True}

        ticket = att.ticket
        if not ticket or not ticket.clickup_task_id:
            logger.info(
                "[ghl_support] ticket dell'allegato %s non ancora sync, retry",
                att.id,
            )
            raise self.retry(countdown=30)

        if not app.config.get("CLICKUP_GHL_INTEGRATION_ENABLED", False):
            return {"ok": False, "reason": "disabled"}

        try:
            client = ClickUpClient.from_app_config(app)
            response = client.upload_attachment(
                task_id=ticket.clickup_task_id,
                file_path=att.file_path,
                filename=att.filename,
            )
            att.clickup_attachment_id = str(
                response.get("id") or response.get("attachment_id") or ""
            )
            att.synced_to_clickup = True
            db.session.commit()
            return {"ok": True, "clickup_attachment_id": att.clickup_attachment_id}
        except FileNotFoundError:
            logger.error("[ghl_support] file allegato %s non esiste", att.file_path)
            return {"ok": False, "reason": "file_missing"}
        except ClickUpError as exc:
            logger.error(
                "[ghl_support] errore upload allegato %s: %s",
                att.id,
                exc,
            )
            raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))
