"""Routes per il blueprint alias sales_ghl_assignments.

Questo blueprint espone un alias stabile per la lista assegnazioni GHL
sotto `/api/ghl-assignments`, riusando la stessa logica di `ghl_integration`.
"""

from __future__ import annotations

from typing import Any, Dict

from flask import jsonify, request
from flask_login import current_user, login_required

from corposostenibile.models import ServiceClienteAssignment
from corposostenibile.blueprints.ghl_integration.routes import (
    _assignment_in_team_leader_scope,
    _get_team_leader_member_ids,
    _is_team_leader_user,
)
from corposostenibile.blueprints.ghl_integration.security import require_permission

from . import bp


def _serialize_assignment(ass: ServiceClienteAssignment) -> Dict[str, Any]:
    cliente = ass.cliente
    return {
        "id": ass.id,
        "cliente_id": ass.cliente_id,
        "cliente_nome": cliente.nome_cognome if cliente else None,
        "cliente_email": getattr(cliente, "mail", None) if cliente else None,
        "cliente_cellulare": (
            getattr(cliente, "cellulare", None) or getattr(cliente, "numero_telefono", None)
            if cliente
            else None
        ),
        "status": ass.status,
        "finance_approved": ass.finance_approved,
        "checkup_iniziale_fatto": ass.checkup_iniziale_fatto,
        "nutrizionista_assigned": ass.nutrizionista_assigned_id is not None,
        "coach_assigned": ass.coach_assigned_id is not None,
        "psicologa_assigned": ass.psicologa_assigned_id is not None,
        "ai_analysis": ass.ai_analysis,
        "ai_analysis_snapshot": ass.ai_analysis_snapshot,
        "created_at": ass.created_at.isoformat() if ass.created_at else None,
    }


@bp.route("", methods=["GET"], strict_slashes=False)
@bp.route("/", methods=["GET"], strict_slashes=False)
@login_required
@require_permission("ghl:view_assignments")
def api_assignments():
    """Alias della lista assegnazioni GHL esposta come `/api/ghl-assignments`."""
    status = request.args.get("status", "pending_finance")

    query = ServiceClienteAssignment.query
    if status != "all":
        query = query.filter_by(status=status)

    assignments = query.order_by(
        ServiceClienteAssignment.created_at.desc()
    ).limit(300).all()

    if _is_team_leader_user(current_user) and not current_user.is_admin:
        allowed_ids = _get_team_leader_member_ids(current_user.id) | {current_user.id}
        assignments = [a for a in assignments if _assignment_in_team_leader_scope(a, allowed_ids)]

    assignments = assignments[:100]

    return jsonify({
        "assignments": [_serialize_assignment(ass) for ass in assignments],
        "total": len(assignments),
    })
