"""
tab_routes.py
=============
Auth endpoint + write API for the Kanban Teams Tab.
All endpoints use JWT bearer token auth (no Flask-Login session).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

import jwt as pyjwt
from flask import jsonify, request, g, abort, current_app, send_file
from sqlalchemy import or_

from corposostenibile.extensions import db, socketio
from corposostenibile.models import (
    User, TeamTicket, TeamTicketMessage, team_ticket_assigned_users,
)
from corposostenibile.blueprints.team_tickets import team_tickets_bp
from corposostenibile.blueprints.team_tickets.services import ticket_service
from corposostenibile.blueprints.team_tickets.services.aad_token_validator import (
    validate_aad_token,
)

logger = logging.getLogger(__name__)

JWT_EXPIRY_HOURS = 8


# ═══════════════════════════════════════════════════════════════════════════ #
#                            AUTH DECORATOR                                   #
# ═══════════════════════════════════════════════════════════════════════════ #


def _issue_jwt(user: User) -> str:
    """Issue an internal JWT for the given user."""
    payload = {
        "user_id": user.id,
        "name": user.full_name,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
        "iss": "suite-clinica-tab",
    }
    return pyjwt.encode(payload, current_app.secret_key, algorithm="HS256")


def tab_auth_required(f):
    """Decorator: validates bearer JWT and sets g.current_user."""

    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Token mancante"}), 401

        token_str = auth_header[7:]
        try:
            payload = pyjwt.decode(
                token_str,
                current_app.secret_key,
                algorithms=["HS256"],
                issuer="suite-clinica-tab",
            )
        except pyjwt.ExpiredSignatureError:
            return jsonify({"error": "Token scaduto"}), 401
        except pyjwt.InvalidTokenError:
            return jsonify({"error": "Token non valido"}), 401

        user = db.session.get(User, payload["user_id"])
        if not user or not user.is_active:
            return jsonify({"error": "Utente non trovato o disattivato"}), 401

        g.current_user = user
        return f(*args, **kwargs)

    return decorated


# ═══════════════════════════════════════════════════════════════════════════ #
#                          AUTH ENDPOINTS                                      #
# ═══════════════════════════════════════════════════════════════════════════ #


@team_tickets_bp.route("/tab-auth", methods=["POST"])
def tab_auth():
    """Exchange AAD token from Teams SSO for internal JWT."""
    data = request.get_json(silent=True) or {}
    aad_token = data.get("aad_token", "").strip()
    if not aad_token:
        return jsonify({"error": "aad_token richiesto"}), 400

    try:
        claims = validate_aad_token(aad_token)
    except ValueError as e:
        logger.warning("[tab-auth] AAD validation failed: %s", e)
        return jsonify({"error": str(e)}), 401

    aad_oid = claims.get("oid")
    aad_name = claims.get("name", "")
    aad_email = claims.get("preferred_username", "")

    if not aad_oid:
        return jsonify({"error": "Token AAD manca il claim 'oid'"}), 401

    # Find or create user by AAD object ID
    user = User.query.filter_by(teams_aad_object_id=aad_oid).first()

    if not user and aad_email:
        # Try matching by email
        user = User.query.filter_by(email=aad_email).first()
        if user:
            user.teams_aad_object_id = aad_oid
            db.session.commit()

    if not user:
        # Auto-create (same pattern as teams_bot_service._resolve_teams_user_id)
        from werkzeug.security import generate_password_hash
        import hashlib

        user = User(
            email=aad_email or f"teams_{aad_oid[:8]}@teams.internal",
            password_hash=generate_password_hash(hashlib.sha256(aad_oid.encode()).hexdigest()),
            first_name=aad_name.split(" ")[0] if aad_name else "Teams",
            last_name=" ".join(aad_name.split(" ")[1:]) if aad_name and " " in aad_name else "User",
            teams_aad_object_id=aad_oid,
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
        logger.info("[tab-auth] Auto-created user %s for AAD oid %s", user.id, aad_oid)

    token = _issue_jwt(user)
    return jsonify({
        "token": token,
        "user_id": user.id,
        "name": user.full_name,
    })


@team_tickets_bp.route("/tab-auth/dev", methods=["POST"])
def tab_auth_dev():
    """Dev-only login: exchange username/password for JWT (no Teams SSO)."""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "Credenziali richieste"}), 400

    user = User.query.filter(
        or_(User.email == username, User.email == f"{username}@corposostenibile.com")
    ).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Credenziali non valide"}), 401

    if not user.is_active:
        return jsonify({"error": "Utente disattivato"}), 401

    token = _issue_jwt(user)
    return jsonify({
        "token": token,
        "user_id": user.id,
        "name": user.full_name,
    })


# ═══════════════════════════════════════════════════════════════════════════ #
#                        KANBAN TAB API ENDPOINTS                              #
# ═══════════════════════════════════════════════════════════════════════════ #


def _user_relationship(ticket: TeamTicket, user_id: int) -> str:
    """Determine user's relationship to a ticket."""
    if ticket.created_by_id == user_id:
        return "creator"
    if any(u.id == user_id for u in ticket.assigned_users):
        return "assignee"
    return "participant"


def _ticket_with_relationship(ticket: TeamTicket, user_id: int, **kwargs) -> dict:
    """Serialize ticket with relationship_to_user field."""
    d = ticket.to_dict(**kwargs)
    d["relationship_to_user"] = _user_relationship(ticket, user_id)
    return d


def _emit_ticket_event(event: str, ticket: TeamTicket) -> None:
    """Emit WebSocket event to the dashboard room."""
    try:
        socketio.emit(
            event,
            {"ticket": ticket.to_dict(), "timestamp": datetime.utcnow().isoformat()},
            namespace="/team-tickets",
            room="team_tickets_dashboard",
        )
    except Exception as e:
        logger.warning("[ws] Failed to emit %s: %s", event, e)


# ─────────────────── LIST (scope=mine) ───────────────────────────────────── #

@team_tickets_bp.route("/tab/tickets", methods=["GET"])
@tab_auth_required
def tab_list_tickets():
    """List tickets visible to the authenticated user (scope=mine)."""
    user = g.current_user
    per_page = request.args.get("per_page", 200, type=int)
    per_page = min(per_page, 500)

    # Get all tickets where user is creator, assignee, or has messages
    assigned_subq = (
        db.session.query(team_ticket_assigned_users.c.ticket_id)
        .filter(team_ticket_assigned_users.c.user_id == user.id)
    )
    messaged_subq = (
        db.session.query(TeamTicketMessage.ticket_id)
        .filter(TeamTicketMessage.sender_id == user.id)
        .distinct()
    )

    tickets = (
        TeamTicket.query
        .filter(
            or_(
                TeamTicket.created_by_id == user.id,
                TeamTicket.id.in_(assigned_subq),
                TeamTicket.id.in_(messaged_subq),
            )
        )
        .order_by(TeamTicket.updated_at.desc())
        .limit(per_page)
        .all()
    )

    return jsonify({
        "tickets": [_ticket_with_relationship(t, user.id) for t in tickets],
    })


# ─────────────────── DETAIL ──────────────────────────────────────────────── #

@team_tickets_bp.route("/tab/tickets/<int:ticket_id>", methods=["GET"])
@tab_auth_required
def tab_get_ticket(ticket_id):
    """Get ticket detail with messages and attachments."""
    ticket = ticket_service.get_ticket(ticket_id)
    if not ticket:
        abort(404)
    return jsonify(
        _ticket_with_relationship(
            ticket, g.current_user.id,
            include_messages=True, include_attachments=True,
        )
    )


# ─────────────────── STATUS CHANGE (drag-and-drop) ───────────────────────── #

@team_tickets_bp.route("/tab/tickets/<int:ticket_id>/status", methods=["PATCH"])
@tab_auth_required
def tab_update_status(ticket_id):
    """Change ticket status (drag-and-drop)."""
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if new_status not in ("aperto", "in_lavorazione", "risolto", "chiuso"):
        return jsonify({"error": "Stato non valido"}), 400

    ticket = ticket_service.update_ticket(
        ticket_id,
        changed_by_id=g.current_user.id,
        status=new_status,
        source="teams",
    )

    _emit_ticket_event("ticket_status_changed", ticket)
    _notify_assignees_async(
        ticket,
        event_type="status_changed",
        status_change=new_status,
        exclude_user_id=g.current_user.id,
    )

    return jsonify({
        "ticket": _ticket_with_relationship(ticket, g.current_user.id),
    })


# ─────────────────── CREATE ──────────────────────────────────────────────── #

@team_tickets_bp.route("/tab/tickets", methods=["POST"])
@tab_auth_required
def tab_create_ticket():
    """Create a new ticket from the Kanban board."""
    data = request.get_json(silent=True) or {}

    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    if not description:
        return jsonify({"error": "Descrizione obbligatoria"}), 400

    ticket = ticket_service.create_ticket(
        description=description,
        created_by_id=g.current_user.id,
        priority=data.get("priority", "media"),
        source="teams",
        assignee_ids=data.get("assignee_ids"),
        cliente_id=data.get("cliente_id"),
        title=title or None,
    )

    _emit_ticket_event("ticket_created", ticket)
    _notify_assignees_async(
        ticket,
        event_type="assigned",
        exclude_user_id=g.current_user.id,
    )

    return jsonify({
        "ticket": _ticket_with_relationship(ticket, g.current_user.id),
    }), 201


# ─────────────────── UPDATE ──────────────────────────────────────────────── #

@team_tickets_bp.route("/tab/tickets/<int:ticket_id>", methods=["PATCH"])
@tab_auth_required
def tab_update_ticket(ticket_id):
    """Update ticket fields (priority, assignees, description)."""
    data = request.get_json(silent=True) or {}

    kwargs = {"source": "teams"}
    if "priority" in data:
        kwargs["priority"] = data["priority"]
    if "assignee_ids" in data:
        kwargs["assignee_ids"] = data["assignee_ids"]
    if "description" in data:
        kwargs["description"] = data["description"]
    if "status" in data:
        kwargs["status"] = data["status"]

    ticket = ticket_service.update_ticket(
        ticket_id,
        changed_by_id=g.current_user.id,
        **kwargs,
    )

    _emit_ticket_event("ticket_updated", ticket)

    return jsonify({
        "ticket": _ticket_with_relationship(ticket, g.current_user.id),
    })


# ─────────────────── MESSAGES ────────────────────────────────────────────── #

@team_tickets_bp.route("/tab/tickets/<int:ticket_id>/messages", methods=["POST"])
@tab_auth_required
def tab_add_message(ticket_id):
    """Add a message to a ticket."""
    data = request.get_json(silent=True) or {}
    content = data.get("content", "").strip()
    if not content:
        return jsonify({"error": "Contenuto obbligatorio"}), 400

    msg = ticket_service.add_message(
        ticket_id=ticket_id,
        sender_id=g.current_user.id,
        content=content,
        source="teams",
    )

    # Update ticket timestamp
    ticket = ticket_service.get_ticket(ticket_id)
    if ticket:
        ticket.updated_at = datetime.utcnow()
        db.session.commit()
        _emit_ticket_event("ticket_updated", ticket)
        sender = g.current_user
        sender_name = f"{sender.first_name} {sender.last_name}".strip()
        _notify_assignees_async(
            ticket,
            event_type="message",
            message=content,
            sender_name=sender_name,
            exclude_user_id=sender.id,
        )

    return jsonify({"message": msg.to_dict()}), 201


# ─────────────────── ATTACHMENTS ─────────────────────────────────────────── #

@team_tickets_bp.route("/tab/tickets/<int:ticket_id>/attachments", methods=["POST"])
@tab_auth_required
def tab_upload_attachment(ticket_id):
    """Upload a file attachment to a ticket."""
    ticket = ticket_service.get_ticket(ticket_id)
    if not ticket:
        abort(404)

    if "file" not in request.files:
        return jsonify({"error": "File richiesto"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Filename vuoto"}), 400

    att = ticket_service._save_attachment(
        ticket=ticket,
        file=file,
        uploaded_by_id=g.current_user.id,
        source="teams",
    )
    db.session.commit()

    ticket.updated_at = datetime.utcnow()
    db.session.commit()

    _emit_ticket_event("ticket_updated", ticket)

    return jsonify({"attachment": att.to_dict()}), 201


# ─────────────────── USERS & PATIENTS (tab-authenticated) ────────────────── #

@team_tickets_bp.route("/tab/users", methods=["GET"])
@tab_auth_required
def tab_get_users():
    """Search assignable users by name/email. Only Teams users."""
    q = request.args.get("q", "").strip()
    query = User.query.filter(
        User.is_active.is_(True),
        User.teams_aad_object_id.isnot(None),
    )
    if q and len(q) >= 2:
        pattern = f"%{q}%"
        query = query.filter(
            or_(
                (User.first_name + " " + User.last_name).ilike(pattern),
                User.email.ilike(pattern),
            )
        )
    users = query.order_by(User.first_name).limit(20).all()
    return jsonify({"users": [
        {"id": u.id, "name": u.full_name, "email": u.email, "avatar": u.avatar_path}
        for u in users
    ]})


@team_tickets_bp.route("/tab/patients/search", methods=["GET"])
@tab_auth_required
def tab_search_patients():
    """Search patients (tab-authenticated wrapper)."""
    q = request.args.get("q", "").strip()
    results = ticket_service.search_patients(q)
    return jsonify({"patients": results})


# ─────────────────── ATTACHMENTS DOWNLOAD ────────────────────────────────── #

@team_tickets_bp.route("/tab/attachments/<int:att_id>", methods=["GET"])
@tab_auth_required
def tab_download_attachment(att_id):
    """Download attachment (tab-authenticated)."""
    att = ticket_service.get_attachment(att_id)
    if not att:
        abort(404)

    upload_base = current_app.config.get(
        "UPLOAD_FOLDER",
        str(Path(current_app.root_path).parent / "uploads"),
    )
    full_path = Path(upload_base).parent / att.file_path
    if not full_path.exists():
        abort(404)

    return send_file(str(full_path), download_name=att.filename, as_attachment=True)


# ─────────────────── NOTIFICATIONS (async helper) ────────────────────────── #

def _notify_assignees_async(
    ticket: TeamTicket,
    event_type: str = "update",
    message: str | None = None,
    sender_name: str | None = None,
    status_change: str | None = None,
    exclude_user_id: int | None = None,
) -> None:
    """Send bot notification to ticket assignees + creator (fire-and-forget).

    Notifies everyone involved except the user who triggered the action.
    """
    try:
        import asyncio
        from corposostenibile.blueprints.team_tickets.services.notification_service import (
            notify_teams_user,
        )
        from corposostenibile.blueprints.team_tickets.adaptive_cards.templates import (
            ticket_notification_card,
        )

        ticket_data = ticket.to_dict()
        card = ticket_notification_card(
            ticket=ticket_data,
            event_type=event_type,
            message=message,
            status_change=status_change,
            sender_name=sender_name,
        )

        # Collect all users to notify (assignees + creator), excluding triggerer
        users_to_notify: dict[int, User] = {}
        for u in ticket.assigned_users:
            if u.id != exclude_user_id:
                users_to_notify[u.id] = u
        if ticket.created_by and ticket.created_by_id != exclude_user_id:
            users_to_notify.setdefault(ticket.created_by_id, ticket.created_by)

        if not users_to_notify:
            return

        async def _send_all():
            for user in users_to_notify.values():
                await notify_teams_user(user, card)

        loop = asyncio.new_event_loop()
        loop.run_until_complete(_send_all())
        loop.close()
    except Exception as e:
        logger.warning("[notify] Failed to notify: %s", e)
