from __future__ import annotations

from datetime import datetime

from flask import abort, jsonify, request, current_app
from flask_login import current_user, login_required

from corposostenibile.blueprints.push_notifications import bp
from corposostenibile.blueprints.push_notifications.service import (
    create_notification_and_send_push,
    push_enabled,
)
from corposostenibile.extensions import db
from corposostenibile.models import AppNotification, PushSubscription, User, UserRoleEnum


def _is_admin_user() -> bool:
    role = getattr(current_user, "role", None)
    return bool(current_user.is_admin or role == UserRoleEnum.admin or str(role) == "admin")


def _require_admin() -> None:
    if not _is_admin_user():
        abort(403, "Accesso riservato agli amministratori")


@bp.route("/public-key", methods=["GET"])
@login_required
def get_public_key():
    public_key = current_app.config.get("VAPID_PUBLIC_KEY")
    return jsonify({"enabled": bool(public_key), "publicKey": public_key})


@bp.route("/subscriptions", methods=["POST"])
@login_required
def upsert_subscription():
    data = request.get_json(silent=True) or {}
    subscription = data.get("subscription", data)
    endpoint = subscription.get("endpoint")
    keys = subscription.get("keys") or {}
    p256dh = keys.get("p256dh")
    auth = keys.get("auth")
    expiration_time = subscription.get("expirationTime")

    if not endpoint or not p256dh or not auth:
        abort(400, "Subscription non valida")

    row = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if row is None:
        row = PushSubscription(
            user_id=current_user.id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
        )
        db.session.add(row)
    else:
        row.user_id = current_user.id
        row.p256dh = p256dh
        row.auth = auth

    row.expiration_time = expiration_time
    row.user_agent = request.headers.get("User-Agent", "")[:512]
    row.last_seen_at = datetime.utcnow()
    db.session.commit()

    return jsonify({"ok": True, "enabled": push_enabled()})


@bp.route("/subscriptions", methods=["DELETE"])
@login_required
def delete_subscription():
    data = request.get_json(silent=True) or {}
    endpoint = data.get("endpoint")

    query = PushSubscription.query.filter_by(user_id=current_user.id)
    if endpoint:
        query = query.filter_by(endpoint=endpoint)

    rows = query.all()
    for row in rows:
        db.session.delete(row)
    db.session.commit()

    return jsonify({"ok": True, "removed": len(rows)})


@bp.route("/notifications", methods=["GET"])
@login_required
def list_notifications():
    unread_only = str(request.args.get("unread_only", "1")).lower() in {"1", "true", "yes"}
    limit = min(max(int(request.args.get("limit", 20)), 1), 100)

    base_query = AppNotification.query.filter_by(user_id=current_user.id)
    unread_count = base_query.filter_by(is_read=False).count()

    items_query = base_query.order_by(AppNotification.created_at.desc())
    if unread_only:
        items_query = items_query.filter_by(is_read=False)
    items = items_query.limit(limit).all()

    return jsonify(
        {
            "items": [item.to_dict() for item in items],
            "unreadCount": unread_count,
        }
    )


@bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_notification_read(notification_id: int):
    notification = AppNotification.query.filter_by(id=notification_id, user_id=current_user.id).first()
    if not notification:
        abort(404, "Notifica non trovata")

    notification.mark_as_read()
    db.session.commit()
    unread_count = AppNotification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({"ok": True, "unreadCount": unread_count, "notification": notification.to_dict()})


@bp.route("/admin/professionisti", methods=["GET"])
@login_required
def list_professionisti():
    _require_admin()

    users = (
        User.query
        .filter(
            User.is_active.is_(True),
            User.is_admin.is_(False),
            User.role.in_([UserRoleEnum.professionista, UserRoleEnum.team_leader, UserRoleEnum.health_manager]),
        )
        .order_by(User.first_name.asc(), User.last_name.asc())
        .all()
    )

    data = [
        {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        }
        for user in users
    ]
    return jsonify({"items": data})


@bp.route("/admin/send", methods=["POST"])
@login_required
def send_manual_push():
    _require_admin()

    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    title = (data.get("title") or "").strip()
    body = (data.get("body") or "").strip()
    url = (data.get("url") or "").strip() or "/"

    if not user_id:
        abort(400, "user_id mancante")
    if not title:
        abort(400, "title mancante")
    if not body:
        abort(400, "body mancante")

    user = User.query.filter_by(id=user_id, is_active=True).first()
    if not user:
        abort(404, "Professionista non trovato")

    notification_id, sent = create_notification_and_send_push(
        user_id=user.id,
        kind="manual",
        title=title,
        body=body,
        url=url,
        payload={"source": "admin_manual", "sender_id": current_user.id},
        tag=f"manual-{user.id}-{int(datetime.utcnow().timestamp())}",
    )

    return jsonify({"ok": True, "sent": sent, "user_id": user.id, "notification_id": notification_id})
