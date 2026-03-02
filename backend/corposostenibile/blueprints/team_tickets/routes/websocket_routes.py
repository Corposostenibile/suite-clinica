"""
websocket_routes.py
===================
WebSocket handlers per notifiche real-time ai client admin.
"""

from __future__ import annotations

from flask_login import current_user
from flask_socketio import emit, join_room, leave_room

from corposostenibile.extensions import socketio


@socketio.on("connect", namespace="/team-tickets")
def handle_connect():
    """Handle WebSocket connection for team tickets dashboard."""
    if not current_user.is_authenticated:
        return False
    join_room("team_tickets_dashboard")
    emit("connected", {"message": "Connected to team tickets"})


@socketio.on("disconnect", namespace="/team-tickets")
def handle_disconnect():
    """Handle WebSocket disconnection."""
    leave_room("team_tickets_dashboard")
