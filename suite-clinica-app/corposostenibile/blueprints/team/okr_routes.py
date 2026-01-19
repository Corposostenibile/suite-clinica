"""
team.okr_routes
===============

Routes per la gestione OKR (Objectives and Key Results).
Dashboard, CRUD obiettivi, update settimanali e tracking progressi.
"""

from __future__ import annotations

from datetime import datetime, date
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
    Objective,
    KeyResult,
    User,
    OKRStatusEnum,
)
from . import team_bp
from .okr_forms import ObjectiveForm


# ════════════════════════════════════════════════════════════════════════
#  Helper permissions
# ════════════════════════════════════════════════════════════════════════

def _can_view_okr(user: User) -> bool:
    """Verifica se l'utente corrente può vedere gli OKR di un altro utente."""
    # Tutti gli utenti autenticati possono vedere gli OKR di tutti
    return current_user.is_authenticated


def _can_edit_okr(user: User) -> bool:
    """Verifica se l'utente corrente può modificare gli OKR di un altro utente."""
    return (
        current_user.is_authenticated and 
        (current_user.id == user.id or current_user.is_admin)
    )


def _require_okr_permission(user: User, edit: bool = False) -> None:
    """Richiede permessi per visualizzare/modificare OKR."""
    if edit and not _can_edit_okr(user):
        abort(HTTPStatus.FORBIDDEN)
    elif not _can_view_okr(user):
        abort(HTTPStatus.FORBIDDEN)


# ════════════════════════════════════════════════════════════════════════
#  Dashboard OKR
# ════════════════════════════════════════════════════════════════════════

@team_bp.route("/<int:user_id>/okr")
@login_required
def okr_dashboard(user_id: int) -> str:
    """Dashboard OKR per un utente specifico."""
    user = User.query.get_or_404(user_id)
    _require_okr_permission(user)
    
    # Parametri filtro
    year = request.args.get("year", date.today().year, type=int)
    
    # Query obiettivi - mostra tutti gli obiettivi dell'utente
    objectives = db.session.query(Objective).filter_by(
        user_id=user_id
    ).order_by(
        Objective.order_index, 
        Objective.created_at.desc()
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
    
    return render_template(
        "team/okr/dashboard.html",
        user=user,
        objectives=objectives,
        stats=stats,
        current_year=year,
        available_years=available_years,
        can_edit=_can_edit_okr(user),
    )

# ════════════════════════════════════════════════════════════════════════
#  CRUD Obiettivi
# ════════════════════════════════════════════════════════════════════════

@team_bp.route("/<int:user_id>/okr/new", methods=["GET", "POST"])
@login_required
def okr_create(user_id: int) -> str | Any:
    """Crea nuovo obiettivo OKR."""
    try:
        user = User.query.get_or_404(user_id)
        _require_okr_permission(user, edit=True)
        
        # Verifica limite obiettivi attivi (max 5) - Allineato con department
        active_count = Objective.query.filter_by(
            user_id=user_id, 
            status=OKRStatusEnum.active
        ).count()
        
        if active_count >= 5:
            flash("Puoi avere massimo 5 obiettivi attivi contemporaneamente.", "warning")
            return redirect(url_for("team.okr_dashboard", user_id=user_id))
        
        form = ObjectiveForm(user=user)
        
        if form.validate_on_submit():
            # Crea obiettivo
            objective = Objective(
                user_id=user_id,
                title=form.title.data.strip(),
                period=",".join(form.periods.data) if form.periods.data else "yearly",  # Salva trimestri multipli
                okr_type=form.okr_type.data,
                status=OKRStatusEnum.active,  # Default attivo
                order_index=db.session.query(Objective).filter_by(user_id=user_id).count(),
            )
            
            # Aggiungi key results
            for idx, kr_data in enumerate(form.key_results.data):
                if not kr_data.get('title'):
                    continue
                
                kr = KeyResult(
                    title=kr_data['title'].strip(),
                    order_index=idx,
                )
                
                objective.key_results.append(kr)
            
            # Non c'è più il concetto di progress automatico
            
            db.session.add(objective)
            db.session.commit()
            
            flash("Obiettivo creato con successo!", "success")
            return redirect(url_for("team.okr_dashboard", user_id=user_id))
        
        return render_template(
            "team/okr/form.html",
            form=form,
            user=user,
            mode="create",
            key_results=None  # Per create, non ci sono KR esistenti
        )
    except Exception as e:
        print(f"ERROR in okr_create: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


@team_bp.route("/okr/<int:objective_id>/edit", methods=["GET", "POST"])
@login_required
def okr_edit(objective_id: int) -> str | Any:
    """Modifica obiettivo OKR esistente."""
    objective = Objective.query.get_or_404(objective_id)
    _require_okr_permission(objective.user, edit=True)
    
    form = ObjectiveForm(obj=objective)
    
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
                kr = KeyResult.query.get(kr_id)
                if kr and kr.objective_id == objective_id:
                    kr.title = kr_data['title'].strip()
                    kr.order_index = idx
                    form_kr_ids.add(kr_id)
            else:
                # Nuovo key result
                kr = KeyResult(
                    objective_id=objective_id,
                    title=kr_data['title'].strip(),
                    order_index=idx,
                )
                db.session.add(kr)
        
        # Rimuovi key results eliminati
        for kr_id in existing_kr_ids - form_kr_ids:
            kr = KeyResult.query.get(kr_id)
            if kr:
                db.session.delete(kr)
        
        # Non c'è più il concetto di progress automatico
        
        db.session.commit()
        flash("Obiettivo aggiornato con successo!", "success")
        return redirect(url_for("team.okr_dashboard", user_id=objective.user_id))
    
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
    
    return render_template(
        "team/okr/form.html",
        form=form,
        user=objective.user,
        objective=objective,
        mode="edit",
    )


@team_bp.route("/okr/<int:objective_id>/delete", methods=["POST"])
@login_required
def okr_delete(objective_id: int):
    """Elimina obiettivo OKR."""
    objective = Objective.query.get_or_404(objective_id)
    _require_okr_permission(objective.user, edit=True)
    
    user_id = objective.user_id
    db.session.delete(objective)
    db.session.commit()
    
    flash("Obiettivo eliminato.", "info")
    return redirect(url_for("team.okr_dashboard", user_id=user_id))


# ════════════════════════════════════════════════════════════════════════
#  Update settimanali - RIMOSSO (non richiesto per OKR personali)
# ════════════════════════════════════════════════════════════════════════
# Gli OKR personali non richiedono update settimanali


# ════════════════════════════════════════════════════════════════════════
#  Reorder obiettivi (drag & drop)
# ════════════════════════════════════════════════════════════════════════

@team_bp.route("/okr/reorder", methods=["POST"])
@login_required
def okr_reorder():
    """Riordina obiettivi via drag & drop."""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        order = data.get('order', [])  # array di objective_id in ordine
        
        user = User.query.get_or_404(user_id)
        _require_okr_permission(user, edit=True)
        
        # Aggiorna order_index
        for idx, obj_id in enumerate(order):
            Objective.query.filter_by(
                id=obj_id,
                user_id=user_id
            ).update({'order_index': idx})
        
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500