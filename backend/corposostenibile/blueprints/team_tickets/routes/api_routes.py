"""
api_routes.py
=============
REST API endpoints per la gestione Team Tickets dalla Suite Amministrativa.
Il pannello admin e' solo lettura — i ticket si gestiscono esclusivamente da Teams/SUMI.
"""

from __future__ import annotations

from pathlib import Path

from flask import jsonify, request, send_file, abort, current_app
from flask_login import login_required

from corposostenibile.blueprints.team_tickets import team_tickets_bp
from corposostenibile.blueprints.team_tickets.services import ticket_service


# ─────────────────────────── LIST ────────────────────────────────────── #

@team_tickets_bp.route("/", methods=["GET"])
@login_required
def list_tickets():
    """Lista ticket paginata con filtri."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    status = request.args.get("status")
    priority = request.args.get("priority")
    assignee_id = request.args.get("assignee_id", type=int)
    cliente_id = request.args.get("cliente_id", type=int)
    search = request.args.get("search")
    sort_by = request.args.get("sort_by", "created_at")
    sort_dir = request.args.get("sort_dir", "desc")

    pagination = ticket_service.list_tickets(
        page=page,
        per_page=per_page,
        status=status,
        priority=priority,
        assignee_id=assignee_id,
        cliente_id=cliente_id,
        search=search,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )

    return jsonify({
        "success": True,
        "tickets": [t.to_dict() for t in pagination.items],
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev,
        },
    })


# ─────────────────────────── DETAIL ──────────────────────────────────── #

@team_tickets_bp.route("/<int:ticket_id>", methods=["GET"])
@login_required
def get_ticket(ticket_id):
    """Dettaglio ticket con messaggi e allegati."""
    ticket = ticket_service.get_ticket(ticket_id)
    if not ticket:
        abort(404)
    return jsonify({
        "success": True,
        "ticket": ticket.to_dict(include_messages=True, include_attachments=True),
    })


# ─────────────────────────── MESSAGES (read-only) ────────────────────── #

@team_tickets_bp.route("/<int:ticket_id>/messages", methods=["GET"])
@login_required
def get_messages(ticket_id):
    """Messaggi del ticket (sola lettura)."""
    messages = ticket_service.get_messages(ticket_id)
    return jsonify({
        "success": True,
        "messages": [m.to_dict() for m in messages],
    })


# ─────────────────────────── ATTACHMENTS (download only) ─────────────── #

@team_tickets_bp.route("/attachments/<int:att_id>", methods=["GET"])
@login_required
def download_attachment(att_id):
    """Scarica un allegato."""
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


# ─────────────────────────── STATS ───────────────────────────────────── #

@team_tickets_bp.route("/stats", methods=["GET"])
@login_required
def get_stats():
    """Statistiche per la dashboard."""
    stats = ticket_service.get_stats()
    return jsonify({"success": True, **stats})


# ─────────────────────────── ANALYTICS ─────────────────────────────── #

@team_tickets_bp.route("/analytics", methods=["GET"])
@login_required
def get_analytics():
    """Dati analytics avanzati per la pagina analytics."""
    days = request.args.get("days", 30, type=int)
    days = max(7, min(days, 365))
    data = ticket_service.get_analytics(days=days)
    return jsonify({"success": True, **data})


# ─────────────────────────── USERS ───────────────────────────────────── #

@team_tickets_bp.route("/users", methods=["GET"])
@login_required
def get_assignable_users():
    """Utenti assegnabili ai ticket."""
    users = ticket_service.get_assignable_users()
    return jsonify({"success": True, "users": users})


# ─────────────────────────── PATIENT SEARCH ──────────────────────────── #

@team_tickets_bp.route("/patients/search", methods=["GET"])
@login_required
def search_patients():
    """Cerca pazienti per nome/email/telefono."""
    q = request.args.get("q", "").strip()
    results = ticket_service.search_patients(q)
    return jsonify({"success": True, "patients": results})
