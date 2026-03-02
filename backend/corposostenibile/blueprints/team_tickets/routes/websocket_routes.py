"""
websocket_routes.py
===================
WebSocket handlers per notifiche real-time ai client admin e tab Kanban.
Supporta sia session auth (admin) che JWT bearer (tab).
"""

from __future__ import annotations

import logging

import jwt as pyjwt
from flask import request, current_app
from flask_login import current_user
from flask_socketio import emit, join_room, leave_room

from corposostenibile.extensions import socketio, db
from corposostenibile.models import User

logger = logging.getLogger(__name__)


def _authenticate_tab_token() -> bool:
    """Try to authenticate via JWT bearer token from socket auth."""
    token = request.args.get("token") or (request.args.get("auth") or "")

    # Also check the auth dict sent by socket.io-client
    if not token and hasattr(request, "event"):
        auth = request.event.get("args", [{}])[0] if request.event.get("args") else {}
        if isinstance(auth, dict):
            token = auth.get("token", "")

    if not token:
        return False

    try:
        payload = pyjwt.decode(
            token,
            current_app.secret_key,
            algorithms=["HS256"],
            issuer="suite-clinica-tab",
        )
        user = db.session.get(User, payload["user_id"])
        return user is not None and user.is_active
    except (pyjwt.InvalidTokenError, KeyError):
        return False


@socketio.on("connect", namespace="/team-tickets")
def handle_connect(auth=None):
    """Handle WebSocket connection for team tickets dashboard.
    Accepts session auth (admin) or JWT bearer (tab).
    """
    # Session-based auth
    if current_user.is_authenticated:
        join_room("team_tickets_dashboard")
        emit("connected", {"message": "Connected to team tickets"})
        return

    # JWT bearer auth (tab)
    token = None
    if isinstance(auth, dict):
        token = auth.get("token")

    if token:
        try:
            payload = pyjwt.decode(
                token,
                current_app.secret_key,
                algorithms=["HS256"],
                issuer="suite-clinica-tab",
            )
            user = db.session.get(User, payload["user_id"])
            if user and user.is_active:
                join_room("team_tickets_dashboard")
                emit("connected", {"message": "Connected to team tickets (tab)"})
                return
        except (pyjwt.InvalidTokenError, KeyError) as e:
            logger.warning("[ws] JWT auth failed: %s", e)

    # No valid auth
    return False


@socketio.on("disconnect", namespace="/team-tickets")
def handle_disconnect():
    """Handle WebSocket disconnection."""
    leave_room("team_tickets_dashboard")
