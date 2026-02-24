"""
planner_webhook_routes.py
=========================
Webhook endpoint for Microsoft Graph subscription notifications (Planner).
Mounted on ``teams_bot_bp`` which is already CSRF-exempt.
"""

from __future__ import annotations

import logging

from flask import request, jsonify, current_app

from corposostenibile.blueprints.team_tickets import teams_bot_bp

logger = logging.getLogger(__name__)


@teams_bot_bp.route("/planner-webhook", methods=["POST"])
def planner_webhook():
    """
    POST /api/teams-bot/planner-webhook

    1. If ``?validationToken=...`` is present → return it as ``text/plain`` 200
       (Graph subscription validation handshake).
    2. Otherwise → verify ``clientState``, enqueue a Celery task for each
       notification, and return 202 Accepted.
    """
    # ── Validation handshake ──
    validation_token = request.args.get("validationToken")
    if validation_token:
        logger.info("Planner webhook validation handshake")
        return validation_token, 200, {"Content-Type": "text/plain"}

    # ── Process notifications ──
    expected_secret = current_app.config.get("PLANNER_WEBHOOK_SECRET", "planner-sync-secret")
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "invalid body"}), 400

    notifications = body.get("value", [])
    enqueued = 0

    for notification in notifications:
        client_state = notification.get("clientState", "")
        if client_state != expected_secret:
            logger.warning("Planner webhook: invalid clientState, skipping notification")
            continue

        resource = notification.get("resource", "")
        change_type = notification.get("changeType", "")

        if not resource or not change_type:
            continue

        try:
            from corposostenibile.blueprints.team_tickets.services.planner_tasks import (
                process_planner_notification_task,
            )
            process_planner_notification_task.delay(resource, change_type)
            enqueued += 1
        except Exception:
            logger.exception("Failed to enqueue Planner notification")

    logger.info("Planner webhook: enqueued %d/%d notifications", enqueued, len(notifications))
    return "", 202
