from __future__ import annotations

from datetime import datetime

from flask import abort, jsonify, request, current_app
from flask_login import current_user, login_required

from corposostenibile.blueprints.push_notifications import bp
from corposostenibile.blueprints.push_notifications.service import push_enabled
from corposostenibile.extensions import db
from corposostenibile.models import PushSubscription


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
