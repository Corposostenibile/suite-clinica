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
    render_template,
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
from .okr_forms import (
    DepartmentObjectiveForm,
    DepartmentWeeklyUpdateForm,
    DepartmentQuickProgressForm,
    LinkPersonalOKRForm,
)


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

@dept_bp.route("/<int:dept_id>/okr")
@login_required
def okr_dashboard(dept_id: int) -> str:
    """Dashboard OKR per un dipartimento specifico."""
    dept = Department.query.get_or_404(dept_id)
    _require_dept_okr_permission(dept)
    
    # Parametri filtro
    year = request.args.get("year", date.today().year, type=int)
    status = request.args.get("status", "active")
    
    # Query obiettivi - FIX: use db.session.query instead of relationship
    query = db.session.query(DepartmentObjective).filter_by(department_id=dept_id)
    
    if status != "all":
        query = query.filter(DepartmentObjective.status == status)
    
    objectives = query.order_by(
        DepartmentObjective.order_index, 
        DepartmentObjective.created_at.desc()
    ).all()
    
    # Calcola statistiche
    stats = {
        "total": len(objectives),
        "active": sum(1 for o in objectives if o.status == OKRStatusEnum.active),
        "completed": sum(1 for o in objectives if o.status == OKRStatusEnum.completed),
        "total_kr": sum(len(o.key_results) for o in objectives),
    }
    
    # Anni disponibili per il filtro (semplificato senza campo year)
    available_years = [date.today().year]
    
    # Ultimi aggiornamenti
    recent_updates = DepartmentOKRUpdate.query.join(
        DepartmentObjective
    ).filter(
        DepartmentObjective.department_id == dept_id
    ).order_by(
        DepartmentOKRUpdate.created_at.desc()
    ).limit(5).all()
    
    # Nessun tracking di assegnazioni (rimosso assignee_id)
    members_with_kr = []
    
    return render_template(
        "department/okr/dashboard.html",
        dept=dept,
        objectives=objectives,
        stats=stats,
        current_year=year,
        current_status=status,
        available_years=available_years,
        recent_updates=recent_updates,
        members_with_kr=members_with_kr,
        can_edit=_can_edit_dept_okr(dept),
    )


# ════════════════════════════════════════════════════════════════════════
#  CRUD Obiettivi
# ════════════════════════════════════════════════════════════════════════

@dept_bp.route("/<int:dept_id>/okr/new", methods=["GET", "POST"])
@login_required
def okr_create(dept_id: int) -> str | Any:
    """Crea nuovo obiettivo OKR dipartimentale."""
    dept = Department.query.get_or_404(dept_id)
    _require_dept_okr_permission(dept, edit=True)
    
    # Verifica limite obiettivi attivi (max 5 per dipartimento) - FIX: use query
    active_count = db.session.query(DepartmentObjective).filter_by(
        department_id=dept_id,
        status=OKRStatusEnum.active
    ).count()
    
    if active_count >= 5:
        flash("Il dipartimento può avere massimo 5 obiettivi attivi contemporaneamente.", "warning")
        return redirect(url_for("department.okr_dashboard", dept_id=dept_id))
    
    form = DepartmentObjectiveForm(department=dept)
    
    if form.validate_on_submit():
        # Crea obiettivo
        objective = DepartmentObjective(
            department_id=dept_id,
            created_by_id=current_user.id,
            title=form.title.data.strip(),
            period=",".join(form.periods.data) if form.periods.data else "yearly",  # Salva trimestri multipli
            okr_type=form.okr_type.data,
            status=OKRStatusEnum.active,  # Default attivo
            order_index=db.session.query(DepartmentObjective).filter_by(department_id=dept_id).count(),
        )
        
        # Aggiungi key results
        for idx, kr_data in enumerate(form.key_results.data):
            if not kr_data.get('title'):
                continue
            
            kr = DepartmentKeyResult(
                title=kr_data['title'].strip(),
                order_index=idx,
            )
            
            objective.key_results.append(kr)
        
        # Non c'è più il concetto di progress automatico
        
        db.session.add(objective)
        db.session.commit()
        
        flash("Obiettivo dipartimentale creato con successo!", "success")
        return redirect(url_for("department.okr_dashboard", dept_id=dept_id))
    
    # Get active members for the template
    active_members = db.session.query(User).filter(
        User.department_id == dept_id,
        User.is_active.is_(True)
    ).order_by(User.first_name).all()
    
    # Count active members and objectives
    active_members_count = len(active_members)
    active_objectives_count = db.session.query(DepartmentObjective).filter_by(
        department_id=dept_id,
        status=OKRStatusEnum.active
    ).count()
    
    return render_template(
        "department/okr/form.html",
        form=form,
        dept=dept,
        mode="create",
        active_members=active_members,
        active_members_count=active_members_count,
        active_objectives_count=active_objectives_count,
    )


@dept_bp.route("/okr/<int:objective_id>/edit", methods=["GET", "POST"])
@login_required
def okr_edit(objective_id: int) -> str | Any:
    """Modifica obiettivo OKR dipartimentale esistente."""
    objective = DepartmentObjective.query.get_or_404(objective_id)
    dept = objective.department
    _require_dept_okr_permission(dept, edit=True)
    
    form = DepartmentObjectiveForm(obj=objective, department=dept)
    
    if form.validate_on_submit():
        # Aggiorna dati base
        objective.title = form.title.data.strip()
        objective.period = ",".join(form.periods.data) if form.periods.data else "yearly"  # Salva trimestri multipli
        objective.okr_type = form.okr_type.data
        objective.status = OKRStatusEnum.active  # Mantieni sempre attivo per ora
        
        # Gestione key results
        existing_kr_ids = {kr.id for kr in objective.key_results}
        form_kr_ids = set()
        
        for idx, kr_data in enumerate(form.key_results.data):
            if not kr_data.get('title'):
                continue
            
            kr_id = kr_data.get('id')
            if kr_id and str(kr_id).isdigit():
                # Update esistente
                kr_id = int(kr_id)
                kr = DepartmentKeyResult.query.get(kr_id)
                if kr and kr.objective_id == objective_id:
                    kr.title = kr_data['title'].strip()
                    kr.order_index = idx
                    form_kr_ids.add(kr_id)
            else:
                # Nuovo key result
                kr = DepartmentKeyResult(
                    objective_id=objective_id,
                    title=kr_data['title'].strip(),
                    order_index=idx,
                )
                db.session.add(kr)
        
        # Rimuovi key results eliminati
        for kr_id in existing_kr_ids - form_kr_ids:
            kr = DepartmentKeyResult.query.get(kr_id)
            if kr:
                db.session.delete(kr)
        
        # Non c'è più il concetto di progress automatico
        
        db.session.commit()
        flash("Obiettivo aggiornato con successo!", "success")
        return redirect(url_for("department.okr_dashboard", dept_id=dept.id))
    
    # Prepara form per GET
    if request.method == 'GET':
        # Prepopola i trimestri selezionati
        if objective.period and objective.period != "yearly":
            form.periods.data = objective.period.split(',')  # Selezione multipla
        
        # Rimuovi entries vuote
        while len(form.key_results) > 0:
            form.key_results.pop_entry()
        
        # Aggiungi key results esistenti
        for kr in objective.key_results:
            form.key_results.append_entry({
                'id': str(kr.id),
                'title': kr.title,
                'order_index': kr.order_index,
            })
    
    # Get active members for the template
    active_members = db.session.query(User).filter(
        User.department_id == dept.id,
        User.is_active.is_(True)
    ).order_by(User.first_name).all()
    
    # Count active members and objectives
    active_members_count = len(active_members)
    active_objectives_count = db.session.query(DepartmentObjective).filter_by(
        department_id=dept.id,
        status=OKRStatusEnum.active
    ).count()
    
    return render_template(
        "department/okr/form.html",
        form=form,
        dept=dept,
        objective=objective,
        mode="edit",
        active_members=active_members,
        active_members_count=active_members_count,
        active_objectives_count=active_objectives_count,
    )

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
#  Update settimanali
# ════════════════════════════════════════════════════════════════════════

@dept_bp.route("/okr/<int:objective_id>/weekly-update", methods=["GET", "POST"])
@login_required
def okr_weekly_update(objective_id: int) -> str | Any:
    """Form per aggiornamento settimanale del dipartimento."""
    objective = DepartmentObjective.query.get_or_404(objective_id)
    dept = objective.department
    _require_dept_okr_permission(dept)  # Membri possono fare update
    
    if objective.status != OKRStatusEnum.active:
        flash("Puoi aggiornare solo obiettivi attivi.", "warning")
        return redirect(url_for("department.okr_dashboard", dept_id=dept.id))
    
    form = DepartmentWeeklyUpdateForm()
    
    if form.validate_on_submit():
        # Calcola settimana corrente
        today = date.today()
        week_number = today.isocalendar()[1]
        year = today.year
        
        # Crea snapshot key results
        kr_snapshot = {}
        for kr in objective.key_results:
            kr_snapshot[str(kr.id)] = {
                'title': kr.title,
            }
        
        # Prepara metriche team
        team_metrics = {}
        if form.tickets_completed.data is not None:
            team_metrics['tickets_completed'] = form.tickets_completed.data
        if form.team_hours_saved.data is not None:
            team_metrics['team_hours_saved'] = float(form.team_hours_saved.data)
        if form.customer_satisfaction.data is not None:
            team_metrics['customer_satisfaction'] = float(form.customer_satisfaction.data)
        
        # Crea update
        update = DepartmentOKRUpdate(
            objective_id=objective_id,
            user_id=current_user.id,
            week_number=week_number,
            year=year,
            notes=form.notes.data.strip() if form.notes.data else None,
            achievements=form.achievements.data.strip() if form.achievements.data else None,
            blockers=form.blockers.data.strip() if form.blockers.data else None,
            next_steps=form.next_steps.data.strip() if form.next_steps.data else None,
            team_morale=form.team_morale.data,
            confidence_level=form.confidence_level.data,
            objective_progress=0,  # Non c'è più tracking automatico del progress
            key_results_snapshot=kr_snapshot,
            team_metrics=team_metrics if team_metrics else None,
        )
        
        db.session.add(update)
        db.session.commit()
        
        flash("Aggiornamento settimanale del team salvato!", "success")
        return redirect(url_for("department.okr_dashboard", dept_id=dept.id))
    
    # Verifica se esiste già un update per questa settimana
    today = date.today()
    week_number = today.isocalendar()[1]
    year = today.year
    
    existing_update = DepartmentOKRUpdate.query.filter_by(
        objective_id=objective_id,
        week_number=week_number,
        year=year,
    ).first()
    
    # Statistiche per il form (semplificato)
    assigned_krs = []  # Non più necessario senza assignee_id
    
    return render_template(
        "department/okr/weekly_update.html",
        form=form,
        objective=objective,
        dept=dept,
        existing_update=existing_update,
        assigned_krs=assigned_krs,
        date=date,
    )


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
#  Collegamento con OKR personali (opzionale)
# ════════════════════════════════════════════════════════════════════════

@dept_bp.route("/okr/<int:objective_id>/link-personal", methods=["GET", "POST"])
@login_required
def okr_link_personal(objective_id: int) -> str | Any:
    """Collega OKR personali dei membri agli obiettivi del dipartimento."""
    objective = DepartmentObjective.query.get_or_404(objective_id)
    dept = objective.department
    _require_dept_okr_permission(dept, edit=True)
    
    form = LinkPersonalOKRForm(department=dept)
    
    if form.validate_on_submit():
        # Rimuovi collegamenti esistenti
        objective.linked_personal_objectives.clear()
        
        # Aggiungi nuovi collegamenti
        from corposostenibile.models import Objective
        
        for obj_id in form.personal_objective_ids.data:
            personal_obj = Objective.query.get(obj_id)
            if personal_obj and personal_obj.user.department_id == dept.id:
                objective.linked_personal_objectives.append(personal_obj)
        
        db.session.commit()
        flash("Collegamenti aggiornati con successo!", "success")
        return redirect(url_for("department.okr_dashboard", dept_id=dept.id))
    
    # Pre-seleziona obiettivi già collegati
    if request.method == 'GET':
        form.personal_objective_ids.data = [
            obj.id for obj in objective.linked_personal_objectives
        ]
    
    return render_template(
        "department/okr/link_personal.html",
        form=form,
        objective=objective,
        dept=dept,
    )


# ════════════════════════════════════════════════════════════════════════
#  Vista aggregata membri del team - RIMOSSA
# ════════════════════════════════════════════════════════════════════════
# Non più necessaria senza assignee_id