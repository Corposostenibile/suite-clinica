"""
Routes per la gestione degli User in prova (Trial Users)
"""
from flask import (
    redirect, url_for, flash, request,
    abort, jsonify
)
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import and_, or_, text

from corposostenibile.extensions import db, csrf
from corposostenibile.models import User, Cliente, trial_user_clients
from . import team_bp


def require_admin_or_supervisor():
    """Verifica che l'utente sia admin o supervisor di trial users o head del dipartimento Nutrizione"""
    if not current_user.is_authenticated:
        abort(401)

    # Admin sempre ok
    if current_user.is_admin:
        return True

    # Check se è head del dipartimento Nutrizione (id=2)
    if (current_user.department and
        current_user.department.head_id == current_user.id and
        current_user.department_id == 2):
        return True

    # Check se è supervisor di qualche trial user
    supervised = User.query.filter_by(
        trial_supervisor_id=current_user.id,
        is_trial=True
    ).count()

    if supervised > 0:
        return True

    abort(403)




















@team_bp.route('/trial-users/<int:user_id>/remove-client/<int:cliente_id>', methods=['POST'])
@login_required
def trial_user_remove_client(user_id, cliente_id):
    """Rimuovi cliente assegnato a trial user"""
    require_admin_or_supervisor()

    user = User.query.get_or_404(user_id)

    # Check se è head del dipartimento Nutrizione
    is_nutrition_head = (current_user.department and
                        current_user.department.head_id == current_user.id and
                        current_user.department_id == 2)

    # Verifica permessi - admin e head nutrizione possono rimuovere clienti da tutti
    if not (current_user.is_admin or is_nutrition_head) and user.trial_supervisor_id != current_user.id:
        abort(403)

    # Rimuovi associazione usando SQL raw
    db.session.execute(
        text("""
            DELETE FROM trial_user_clients
            WHERE user_id = :user_id AND cliente_id = :cliente_id
        """),
        {"user_id": user_id, "cliente_id": cliente_id}
    )
    db.session.commit()

    flash('Cliente rimosso con successo', 'success')
    return redirect(url_for('team.trial_user_view', user_id=user_id))


@team_bp.route('/trial-users/<int:user_id>/delete', methods=['POST'])
@login_required
@csrf.exempt
def trial_user_delete(user_id):
    """Elimina un trial user"""
    import logging
    logging.info(f"DELETE TRIAL USER chiamato per user_id: {user_id}")

    require_admin_or_supervisor()

    user = User.query.get_or_404(user_id)
    logging.info(f"User trovato: {user.email}, is_trial: {user.is_trial}")

    # Verifica che sia effettivamente un trial user
    if not user.is_trial:
        flash('Questo utente non è un trial user', 'warning')
        return redirect(url_for('team.trial_users_list'))

    # Check se è head del dipartimento Nutrizione
    is_nutrition_head = (current_user.department and
                        current_user.department.head_id == current_user.id and
                        current_user.department_id == 2)

    # Verifica permessi - admin e head nutrizione possono eliminare tutti
    if not (current_user.is_admin or is_nutrition_head) and user.trial_supervisor_id != current_user.id:
        abort(403)

    try:
        # Prima rimuovi tutti i clienti assegnati
        db.session.execute(
            text("""
                DELETE FROM trial_user_clients
                WHERE user_id = :user_id
            """),
            {"user_id": user_id}
        )
        logging.info(f"Clienti assegnati rimossi per user_id: {user_id}")

        # Poi elimina l'utente
        db.session.delete(user)
        db.session.commit()
        logging.info(f"User {user_id} eliminato con successo")

        flash(f"Trial user '{user.full_name}' eliminato con successo", 'success')
    except Exception as e:
        logging.error(f"Errore eliminazione user {user_id}: {str(e)}")
        db.session.rollback()
        flash(f"Errore durante l'eliminazione: {str(e)}", 'danger')

    return redirect(url_for('team.trial_users_list'))