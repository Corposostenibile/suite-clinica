"""
department/okr_routes.py
========================

Routes per la gestione OKR (Objectives and Key Results) dipartimentali.
Dashboard, CRUD obiettivi, update settimanali e tracking progressi.
"""

from __future__ import annotations

from datetime import datetime, date, timedelta
from http import HTTPStatus
from typing import Any, Dict

from flask import (
    abort,
    flash,
    jsonify,
    redirect,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import and_, or_, func

from corposostenibile.extensions import db
from corposostenibile.models import (
    Department,
    DepartmentObjective,
    DepartmentKeyResult,
    DepartmentOKRUpdate,
    User,
    OKRStatusEnum,
)
from . import dept_bp


# ════════════════════════════════════════════════════════════════════════
#  Helper permissions
# ════════════════════════════════════════════════════════════════════════

def _can_view_dept_okr(dept: Department) -> bool:
    """
    Verifica se l'utente corrente può vedere gli OKR del dipartimento.
    TUTTI gli utenti autenticati possono vedere gli OKR di TUTTI i dipartimenti.
    """
    return current_user.is_authenticated


def _can_edit_dept_okr(dept: Department) -> bool:
    """
    Verifica se l'utente corrente può modificare gli OKR del dipartimento.
    Solo admin e head del dipartimento possono modificare gli OKR.
    """
    if not current_user.is_authenticated:
        return False
    
    # Admin può modificare tutto
    if current_user.is_admin:
        return True
    
    # Solo head del dipartimento può modificare
    if dept.head_id == current_user.id:
        return True
    
    return False


def _require_dept_okr_permission(dept: Department, edit: bool = False) -> None:
    """Richiede permessi per visualizzare/modificare OKR del dipartimento."""
    if edit and not _can_edit_dept_okr(dept):
        abort(HTTPStatus.FORBIDDEN)
    elif not _can_view_dept_okr(dept):
        abort(HTTPStatus.FORBIDDEN)


# ════════════════════════════════════════════════════════════════════════
#  Dashboard OKR Dipartimento
# ════════════════════════════════════════════════════════════════════════


# ════════════════════════════════════════════════════════════════════════
#  CRUD Obiettivi
# ════════════════════════════════════════════════════════════════════════

@dept_bp.route("/okr/<int:objective_id>/delete", methods=["POST"])
@login_required
def okr_delete(objective_id: int):
    """Elimina obiettivo OKR dipartimentale."""
    objective = DepartmentObjective.query.get_or_404(objective_id)
    dept = objective.department
    _require_dept_okr_permission(dept, edit=True)
    
    dept_id = objective.department_id
    db.session.delete(objective)
    db.session.commit()
    
    flash("Obiettivo eliminato.", "info")
    return redirect(url_for("department.okr_dashboard", dept_id=dept_id))


# ════════════════════════════════════════════════════════════════════════
#  Update rapido progress (AJAX) - RIMOSSO
# ════════════════════════════════════════════════════════════════════════
# Non più necessario senza tracking del progress


# ════════════════════════════════════════════════════════════════════════
#  Reorder obiettivi (drag & drop)
# ════════════════════════════════════════════════════════════════════════

@dept_bp.route("/okr/reorder", methods=["POST"])
@login_required
def okr_reorder():
    """Riordina obiettivi dipartimentali via drag & drop."""
    try:
        data = request.get_json()
        dept_id = data.get('dept_id')
        order = data.get('order', [])  # array di objective_id in ordine
        
        dept = Department.query.get_or_404(dept_id)
        _require_dept_okr_permission(dept, edit=True)
        
        # Aggiorna order_index
        for idx, obj_id in enumerate(order):
            DepartmentObjective.query.filter_by(
                id=obj_id,
                department_id=dept_id
            ).update({'order_index': idx})
        
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ════════════════════════════════════════════════════════════════════════
#  Vista aggregata membri del team - RIMOSSA
# ════════════════════════════════════════════════════════════════════════
# Non più necessaria senza assignee_id