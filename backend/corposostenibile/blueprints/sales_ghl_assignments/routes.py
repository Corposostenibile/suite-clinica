"""Routes per il blueprint sales_ghl_assignments.

Espone la vista lista delle SalesLead provenienti da GHL sotto
`/api/ghl-assignments`.
"""

from __future__ import annotations

from flask import abort, g, jsonify, request
from sqlalchemy import or_

from corposostenibile.models import SalesLead

from . import bp
from .services import serialize_sales_lead
from .sso import (
    build_sales_session_user,
    create_sales_jwt,
    get_active_sales_user,
    resolve_sales_user_by_email,
    sales_assignments_auth_required,
)


@bp.route("/sso/exchange", methods=["POST"])
def sso_exchange():
    """Scambia l'email del sales con un JWT firmato dal backend.

    Payload atteso:
    - user_email / email
    - user_name / name (opzionale)
    """
    payload = request.get_json(silent=True) or {}
    email = (
        payload.get("user_email")
        or payload.get("email")
        or payload.get("sales_user_email")
        or ""
    ).strip()

    if not email:
        abort(422, description="user_email richiesto")

    sales_user = resolve_sales_user_by_email(email)
    if not sales_user:
        abort(401, description="Utente sales non trovato")

    token = create_sales_jwt(sales_user)
    session_user = build_sales_session_user(sales_user)

    return jsonify(
        {
            "success": True,
            "scope": "sales",
            "token": token,
            "sales_user": session_user.to_dict(),
        }
    )


@bp.route("", methods=["GET"], strict_slashes=False)
@bp.route("/", methods=["GET"], strict_slashes=False)
@sales_assignments_auth_required()
def api_assignments():
    """Lista le SalesLead GHL.

    Query params supportati:
    - `status`: filtro stato (`all` per tutti)
    - `q`: ricerca su nome/email/telefono/unique_code
    - `limit`: massimo record restituiti (default 100, max 300)
    """
    status = (request.args.get("status") or "all").strip()
    search = (request.args.get("q") or request.args.get("search") or "").strip()
    limit = request.args.get("limit", type=int) or 100
    limit = max(1, min(limit, 300))

    query = SalesLead.query.filter(
        SalesLead.source_system == "ghl",
        SalesLead.archived_at.is_(None),
    )

    # Scoping: via JWT sales si vede solo la propria coda.
    if getattr(g, "sales_auth_mode", None) == "jwt" and get_active_sales_user():
        query = query.filter(SalesLead.sales_user_id == get_active_sales_user().id)

    if status.lower() != "all":
        query = query.filter(SalesLead.status == status.upper())

    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                SalesLead.first_name.ilike(like),
                SalesLead.last_name.ilike(like),
                SalesLead.email.ilike(like),
                SalesLead.phone.ilike(like),
                SalesLead.unique_code.ilike(like),
            )
        )

    leads = query.order_by(SalesLead.created_at.desc()).limit(limit).all()
    active_user = get_active_sales_user()

    return jsonify(
        {
            "assignments": [serialize_sales_lead(lead) for lead in leads],
            "total": len(leads),
            "status": status,
            "search": search,
            "limit": limit,
            "current_user_id": active_user.id if active_user else None,
            "auth_mode": getattr(g, "sales_auth_mode", None),
        }
    )
