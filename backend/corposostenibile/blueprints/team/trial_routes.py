"""
Routes per la gestione degli User in prova (Trial Users)
"""
from flask import (
    render_template, redirect, url_for, flash, request,
    abort, jsonify
)
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import and_, or_, text

from corposostenibile.extensions import db, csrf
from corposostenibile.models import User, Cliente, trial_user_clients
from . import team_bp
from .trial_forms import (
    TrialUserForm, TrialUserPromoteForm, AssignClientsForm
)


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


@team_bp.route('/trial-users')
@login_required
def trial_users_list():
    """Lista degli User in prova"""
    require_admin_or_supervisor()

    # Check se è head del dipartimento Nutrizione
    is_nutrition_head = (current_user.department and
                        current_user.department.head_id == current_user.id and
                        current_user.department_id == 2)

    # Admin e head Nutrizione vedono tutti i trial users
    if current_user.is_admin or is_nutrition_head:
        users = User.query.filter_by(
            is_trial=True
        ).order_by(User.trial_stage, User.first_name).all()
    else:
        # Altri supervisor vedono solo i loro supervisionati
        users = User.query.filter_by(
            trial_supervisor_id=current_user.id,
            is_trial=True
        ).order_by(User.trial_stage, User.first_name).all()

    return render_template(
        'team/trial/list.html',
        trial_users=users,
        title='User in Prova'
    )


@team_bp.route('/trial-users/new', methods=['GET', 'POST'])
@login_required
def trial_user_create():
    """Crea nuovo User in prova"""
    require_admin_or_supervisor()

    form = TrialUserForm()

    if form.validate_on_submit():
        user = User(
            email=form.email.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            job_title=form.job_title.data,
            department_id=form.department_id.data if form.department_id.data != 0 else None,
            is_trial=True,
            trial_stage=form.trial_stage.data,
            trial_started_at=datetime.utcnow(),
            trial_supervisor_id=form.trial_supervisor_id.data if form.trial_supervisor_id.data != 0 else current_user.id,
            is_active=True
        )

        # Set password
        if form.password.data:
            user.set_password(form.password.data)

        db.session.add(user)
        db.session.commit()

        flash(f"User in prova '{user.full_name}' creato con successo!", 'success')
        return redirect(url_for('team.trial_users_list'))

    return render_template(
        'team/trial/form.html',
        form=form,
        title='Nuovo User in Prova'
    )


@team_bp.route('/trial-users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def trial_user_edit(user_id):
    """Modifica User in prova"""
    require_admin_or_supervisor()

    user = User.query.get_or_404(user_id)

    # Check se è head del dipartimento Nutrizione
    is_nutrition_head = (current_user.department and
                        current_user.department.head_id == current_user.id and
                        current_user.department_id == 2)

    # Verifica permessi - admin e head nutrizione possono modificare tutti
    if not (current_user.is_admin or is_nutrition_head) and user.trial_supervisor_id != current_user.id:
        abort(403)

    form = TrialUserForm(obj=user)
    form.user_id = user_id  # Per validazione email

    if form.validate_on_submit():
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.email = form.email.data
        user.job_title = form.job_title.data
        user.department_id = form.department_id.data if form.department_id.data != 0 else None
        user.trial_stage = form.trial_stage.data
        user.trial_supervisor_id = form.trial_supervisor_id.data if form.trial_supervisor_id.data != 0 else None

        # Update password if provided
        if form.password.data:
            user.set_password(form.password.data)

        # Se stage 3, promuovi a user ufficiale
        if user.trial_stage == 3:
            user.is_trial = False
            user.trial_promoted_at = datetime.utcnow()

        db.session.commit()

        flash(f"User '{user.full_name}' aggiornato con successo!", 'success')
        return redirect(url_for('team.trial_users_list'))

    return render_template(
        'team/trial/form.html',
        form=form,
        user=user,
        title=f'Modifica User in Prova: {user.full_name}'
    )


@team_bp.route('/trial-users/<int:user_id>/promote', methods=['GET', 'POST'])
@login_required
def trial_user_promote(user_id):
    """Promuovi trial user allo stage successivo"""
    require_admin_or_supervisor()

    user = User.query.get_or_404(user_id)

    # Check se è head del dipartimento Nutrizione
    is_nutrition_head = (current_user.department and
                        current_user.department.head_id == current_user.id and
                        current_user.department_id == 2)

    # Verifica permessi - admin e head nutrizione possono promuovere tutti
    if not (current_user.is_admin or is_nutrition_head) and user.trial_supervisor_id != current_user.id:
        abort(403)

    if not user.is_trial:
        flash('Utente non è un trial user', 'warning')
        return redirect(url_for('team.trial_users_list'))

    form = TrialUserPromoteForm()
    form.user_id.data = user_id

    if form.validate_on_submit():
        old_stage = user.trial_stage
        if user.promote_to_next_stage():
            flash(
                f"User '{user.full_name}' promosso da Stage {old_stage} a {user.trial_stage_description}!",
                'success'
            )
        else:
            flash('Impossibile promuovere utente', 'warning')

        return redirect(url_for('team.trial_users_list'))

    return render_template(
        'team/trial/promote.html',
        form=form,
        user=user,
        now=datetime.utcnow(),
        title=f'Promuovi User: {user.full_name}'
    )


@team_bp.route('/trial-users/<int:user_id>/assign-clients', methods=['GET', 'POST'])
@login_required
def trial_user_assign_clients(user_id):
    """Assegna clienti a un trial user (Stage 2)"""
    require_admin_or_supervisor()

    user = User.query.get_or_404(user_id)

    # Check se è head del dipartimento Nutrizione
    is_nutrition_head = (current_user.department and
                        current_user.department.head_id == current_user.id and
                        current_user.department_id == 2)

    # Verifica permessi - admin e head nutrizione possono assegnare clienti a tutti
    if not (current_user.is_admin or is_nutrition_head) and user.trial_supervisor_id != current_user.id:
        abort(403)

    if not user.is_trial or user.trial_stage < 2:
        flash('User deve essere in Stage 2 o superiore per assegnare clienti', 'warning')
        return redirect(url_for('team.trial_users_list'))

    form = AssignClientsForm(user_id=user_id)

    if form.validate_on_submit():
        # Aggiungi clienti selezionati
        for cliente_id in form.cliente_ids.data:
            # Verifica che non sia già assegnato usando SQL raw
            existing = db.session.execute(
                text("""
                    SELECT 1 FROM trial_user_clients
                    WHERE user_id = :user_id AND cliente_id = :cliente_id
                """),
                {"user_id": user_id, "cliente_id": cliente_id}
            ).first()

            if not existing:
                # Inserisci nuovo record usando SQL raw
                db.session.execute(
                    text("""
                        INSERT INTO trial_user_clients
                        (user_id, cliente_id, assigned_at, assigned_by, notes)
                        VALUES (:user_id, :cliente_id, :assigned_at, :assigned_by, :notes)
                    """),
                    {
                        "user_id": user_id,
                        "cliente_id": cliente_id,
                        "assigned_at": datetime.utcnow(),
                        "assigned_by": current_user.id,
                        "notes": form.notes.data
                    }
                )

        db.session.commit()
        flash(f"Clienti assegnati a '{user.full_name}' con successo!", 'success')
        return redirect(url_for('team.trial_user_view', user_id=user_id))

    return render_template(
        'team/trial/assign_clients.html',
        form=form,
        user=user,
        title=f'Assegna Clienti a: {user.full_name}'
    )


@team_bp.route('/trial-users/<int:user_id>')
@login_required
def trial_user_view(user_id):
    """Visualizza dettagli trial user"""
    require_admin_or_supervisor()

    user = User.query.get_or_404(user_id)

    # Check se è head del dipartimento Nutrizione
    is_nutrition_head = (current_user.department and
                        current_user.department.head_id == current_user.id and
                        current_user.department_id == 2)

    # Verifica permessi - admin e head nutrizione possono vedere tutti
    if not (current_user.is_admin or is_nutrition_head) and user.trial_supervisor_id != current_user.id:
        abort(403)

    # Carica clienti assegnati con info aggiuntive
    from sqlalchemy import func

    assigned_clients = db.session.query(
        Cliente,
        trial_user_clients.c.assigned_at,
        trial_user_clients.c.notes,
        func.concat(User.first_name, ' ', User.last_name).label('assigned_by_name')
    ).join(
        trial_user_clients,
        Cliente.cliente_id == trial_user_clients.c.cliente_id
    ).outerjoin(
        User,
        User.id == trial_user_clients.c.assigned_by
    ).filter(
        trial_user_clients.c.user_id == user_id
    ).order_by(
        trial_user_clients.c.assigned_at.desc()
    ).all()

    return render_template(
        'team/trial/view.html',
        user=user,
        assigned_clients=assigned_clients,
        title=f'Dettagli Trial User: {user.full_name}'
    )


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