"""
task_notification_service.py
============================
Notifiche Teams proattive per i Task (task manuali, solleciti, reminder).

Punto di ingresso unico: ``notify_task_assigned(task, assigner_name)``.
Seleziona automaticamente la card corretta in base a ``task.category``
e delega l'invio a ``notification_service.notify_teams_user``.

Progettato per funzionare sia da request context Flask (assegnazione manuale)
sia da Celery (generazione automatica notifiche). In entrambi i casi la chiamata
è fire-and-forget: eventuali errori vengono loggati ma non propagati.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from corposostenibile.models import Task

logger = logging.getLogger(__name__)


def notify_task_assigned(task: "Task", assigner_name: str | None = None) -> None:
    """Invia notifica Teams proattiva all'assegnatario del task.

    Seleziona automaticamente la card appropriata:
    - ``category == sollecito``  → ``sollecito_card``
    - ``category == reminder``   → ``reminder_card``
    - tutti gli altri            → ``task_assigned_card``

    Args:
        task: istanza SQLAlchemy Task. Deve avere ``.assignee`` caricato.
        assigner_name: nome leggibile di chi ha creato/assegnato il task.
                       Usato solo per task_assigned_card (task manuali).
    """
    user = getattr(task, "assignee", None)
    if not user:
        logger.debug("[task_notify] Task %s senza assignee, skip.", task.id)
        return

    if not getattr(user, "teams_conversation_ref", None):
        logger.debug(
            "[task_notify] User %s non ha teams_conversation_ref, skip.", user.id
        )
        return

    try:
        card = _build_card(task, assigner_name)
    except Exception:
        logger.exception("[task_notify] Errore nella costruzione della card per task %s", task.id)
        return

    try:
        from corposostenibile.blueprints.team_tickets.services.notification_service import (
            notify_teams_user,
        )

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(notify_teams_user(user, card))
        finally:
            loop.close()

        logger.info(
            "[task_notify] Notifica Teams inviata: task=%s user=%s category=%s",
            task.id, user.id, _category_value(task),
        )
    except Exception:
        logger.exception(
            "[task_notify] Errore nell'invio notifica Teams per task %s", task.id
        )


# ─────────────────────── helpers ──────────────────────── #

def _category_value(task: "Task") -> str:
    cat = getattr(task, "category", None)
    return cat.value if hasattr(cat, "value") else str(cat)


def _build_card(task: "Task", assigner_name: str | None) -> dict:
    from corposostenibile.blueprints.team_tickets.adaptive_cards.templates import (
        task_assigned_card,
        sollecito_card,
        reminder_card,
    )

    # Serializzazione minimale per le card (evita importare _serialize_task da routes)
    client = getattr(task, "client", None)
    task_dict = {
        "id": task.id,
        "title": task.title or "",
        "description": task.description or "",
        "category": _category_value(task),
        "priority": getattr(task.priority, "value", str(task.priority)) if task.priority else "medium",
        "client_name": client.nome_cognome if client else None,
        "due_date": task.due_date.isoformat() if getattr(task, "due_date", None) else None,
        "payload": getattr(task, "payload", None) or {},
    }

    category = _category_value(task)
    if category == "sollecito":
        return sollecito_card(task_dict)
    elif category == "reminder":
        return reminder_card(task_dict)
    else:
        return task_assigned_card(task_dict, assigner_name=assigner_name)
