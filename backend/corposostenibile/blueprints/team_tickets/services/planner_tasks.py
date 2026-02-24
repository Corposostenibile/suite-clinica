"""
planner_tasks.py
================
Celery tasks for Microsoft Planner sync.
"""

from __future__ import annotations

import logging

from celery import current_app as celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="corposostenibile.blueprints.team_tickets.services.planner_tasks.renew_planner_subscription_task",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
)
def renew_planner_subscription_task(self):
    """Renew the Planner Graph subscription (runs every ~2 days via Celery Beat)."""
    from flask import current_app as flask_app

    # Need Flask app context for config and DB
    from corposostenibile import create_app
    app = create_app()

    with app.app_context():
        if not flask_app.config.get("PLANNER_SYNC_ENABLED"):
            logger.info("Planner sync disabled, skipping subscription renewal")
            return

        subscription_id = None

        # Try Redis first
        try:
            from corposostenibile.extensions import redis_client
            if redis_client:
                subscription_id = redis_client.get("planner:subscription_id")
        except Exception:
            pass

        # Fallback to DB
        if not subscription_id:
            from corposostenibile.models import PlannerSyncState
            state = PlannerSyncState.query.first()
            if state and state.subscription_id:
                subscription_id = state.subscription_id

        if subscription_id:
            from corposostenibile.blueprints.team_tickets.services.planner_sync_service import (
                renew_planner_subscription,
            )
            if renew_planner_subscription(subscription_id):
                logger.info("Planner subscription renewed successfully")
                return

        # Renewal failed or no subscription found → recreate
        logger.info("Creating new Planner subscription")
        from corposostenibile.blueprints.team_tickets.services.planner_sync_service import (
            create_planner_subscription,
        )
        new_id = create_planner_subscription()
        if new_id:
            logger.info("New Planner subscription created: %s", new_id)
        else:
            logger.warning("Failed to create Planner subscription")


@celery_app.task(
    name="corposostenibile.blueprints.team_tickets.services.planner_tasks.planner_initial_setup_task",
    bind=True,
)
def planner_initial_setup_task(self):
    """One-time setup: ensure buckets exist and create first subscription."""
    from corposostenibile import create_app
    app = create_app()

    with app.app_context():
        from corposostenibile.blueprints.team_tickets.services.planner_sync_service import (
            _ensure_buckets,
            create_planner_subscription,
        )

        buckets = _ensure_buckets()
        logger.info("Planner buckets: %s", buckets)

        sub_id = create_planner_subscription()
        logger.info("Initial Planner subscription: %s", sub_id)


@celery_app.task(
    name="corposostenibile.blueprints.team_tickets.services.planner_tasks.process_planner_notification_task",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def process_planner_notification_task(self, resource: str, change_type: str):
    """Process a single Planner webhook notification asynchronously."""
    from corposostenibile import create_app
    app = create_app()

    with app.app_context():
        from corposostenibile.blueprints.team_tickets.services.planner_sync_service import (
            handle_planner_change,
        )
        try:
            handle_planner_change(resource, change_type)
        except Exception as exc:
            logger.exception("Error processing Planner notification: resource=%s, type=%s", resource, change_type)
            raise self.retry(exc=exc)
