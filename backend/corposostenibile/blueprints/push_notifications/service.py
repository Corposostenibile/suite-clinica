from __future__ import annotations

import json
from sqlalchemy.orm import Session as SASession
from flask import current_app
from pywebpush import WebPushException, webpush

from corposostenibile.extensions import db
from corposostenibile.models import PushSubscription


def _vapid_config() -> tuple[str | None, str | None, str]:
    public_key = current_app.config.get("VAPID_PUBLIC_KEY")
    private_key = current_app.config.get("VAPID_PRIVATE_KEY")
    subject = current_app.config.get("VAPID_CLAIMS_SUB", "mailto:it@corposostenibile.com")
    return public_key, private_key, subject


def push_enabled() -> bool:
    public_key, private_key, _ = _vapid_config()
    return bool(public_key and private_key)


def send_push_to_user(user_id: int, payload: dict) -> int:
    public_key, private_key, subject = _vapid_config()
    if not (public_key and private_key):
        return 0

    # Called from SQLAlchemy session hooks (after_commit), so we must not use
    # the same scoped session that just committed.
    with SASession(bind=db.engine) as session:
        subscriptions = (
            session.query(PushSubscription)
            .filter(PushSubscription.user_id == user_id)
            .all()
        )

    if not subscriptions:
        return 0

    sent = 0
    vapid_claims = {"sub": subject}
    payload_json = json.dumps(payload)

    for sub in subscriptions:
        try:
            webpush(
                subscription_info=sub.to_webpush_info(),
                data=payload_json,
                vapid_private_key=private_key,
                vapid_claims=vapid_claims,
                ttl=60,
            )
            sent += 1
        except WebPushException as exc:
            current_app.logger.warning(
                "[push_notifications] Failed push for user=%s sub=%s: %s",
                user_id,
                sub.id,
                exc,
            )
        except Exception as exc:  # pragma: no cover
            current_app.logger.warning(
                "[push_notifications] Unexpected push error user=%s sub=%s: %s",
                user_id,
                sub.id,
                exc,
            )

    return sent


def send_task_assigned_push(task_id: int, assignee_id: int, task_title: str) -> int:
    if not assignee_id:
        return 0

    payload = {
        "title": "Nuovo task assegnato",
        "body": task_title,
        "icon": "/suitemind.png",
        "badge": "/suitemind.png",
        "url": "/task",
        "tag": f"task-{task_id}",
    }
    return send_push_to_user(assignee_id, payload)
