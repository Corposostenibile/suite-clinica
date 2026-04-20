"""Routes per il blueprint sales_ghl_assignments.

Espone la vista lista delle SalesLead provenienti da GHL sotto
`/api/ghl-assignments`.
"""

from __future__ import annotations

from typing import Any, Dict

from flask import jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import or_

from corposostenibile.blueprints.ghl_integration.security import require_permission
from corposostenibile.models import SalesLead

from . import bp
from .services import serialize_sales_lead


@bp.route("", methods=["GET"], strict_slashes=False)
@bp.route("/", methods=["GET"], strict_slashes=False)
@login_required
@require_permission("ghl:view_assignments")
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

    return jsonify({
        "assignments": [serialize_sales_lead(lead) for lead in leads],
        "total": len(leads),
        "status": status,
        "search": search,
        "limit": limit,
        "current_user_id": current_user.id if getattr(current_user, "is_authenticated", False) else None,
    })
