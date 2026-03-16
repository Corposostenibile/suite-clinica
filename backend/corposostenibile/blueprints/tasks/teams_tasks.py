"""
teams_tasks.py
==============
Celery task dedicata per l'invio di notifiche Teams sui Task.

Separata da tasks.py per evitare circular imports e per garantire
che le notifiche vengano inviate in un contesto Flask valido,
anche quando il task Celery generatore (generate_solicitations_task,
generate_reminders_task) ha già concluso la sua transazione.

Utilizzo:
    send_task_notification_task.delay(task_id)
    send_task_notification_task.delay(task_id, assigner_name="Mario Rossi")
"""

from __future__ import annotations

import logging

from corposostenibile.extensions import celery, db
from corposostenibile.models import Task

logger = logging.getLogger(__name__)


@celery.task(bind=True, max_retries=2, default_retry_delay=30)
def send_task_notification_task(self, task_id: int, assigner_name: str | None = None) -> str:
    """Invia notifica Teams per il task con id ``task_id``.

    Viene accodata subito dopo il commit che ha creato il task,
    sia da route (task manuali) sia da task Celery (solleciti/reminder).

    Args:
        task_id: PK del Task da notificare.
        assigner_name: nome leggibile di chi ha assegnato il task (opzionale).

    Returns:
        Stringa descrittiva del risultato (per i log Celery).
    """
    try:
        task = db.session.get(Task, task_id)
        if not task:
            logger.warning("[teams_tasks] Task %s non trovato, skip notifica.", task_id)
            return f"task {task_id} not found"

        if not task.assignee:
            logger.debug("[teams_tasks] Task %s senza assignee, skip notifica.", task_id)
            return f"task {task_id} no assignee"

        from corposostenibile.blueprints.team_tickets.services.task_notification_service import (
            notify_task_assigned,
        )

        notify_task_assigned(task, assigner_name=assigner_name)
        return f"notifica inviata per task {task_id}"

    except Exception as exc:
        logger.exception("[teams_tasks] Errore nella notifica per task %s", task_id)
        raise self.retry(exc=exc)
