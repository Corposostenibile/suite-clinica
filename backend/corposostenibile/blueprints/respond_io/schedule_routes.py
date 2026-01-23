"""
Routes per gestione orari di lavoro e assegnazioni automatiche
Utilizza gli utenti del workspace Respond.io
"""

from datetime import datetime, time
from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import or_ as db_or
from corposostenibile.extensions import db
from corposostenibile.models import (
    User,
    RespondIOUser,
    RespondIOUserWorkSchedule,
    RespondIOAssignmentLog,
    Department
)
from . import bp
from .assignment_service import ContactAssignmentService
from .schedule_forms import (
    UserWorkScheduleForm,
    BulkScheduleForm,
    AutoAssignmentForm,
    ScheduleFilterForm
)


@bp.route('/schedules')
@login_required
def schedules_index():
    """Reindirizza direttamente al calendario interattivo"""
    return redirect(url_for('respond_io.calendar_view'))


@bp.route('/schedules/sync', methods=['POST'])
@login_required
def sync_respond_io_users():
    """Sincronizza utenti dal workspace Respond.io"""
    
    if not current_user.is_admin:
        return jsonify({'error': 'Solo gli admin possono sincronizzare'}), 403
    
    service = ContactAssignmentService()
    result = service.sync_workspace_users()
    
    if result['errors']:
        flash(f"Sincronizzazione parziale: {result['errors'][0]}", 'warning')
    else:
        flash(f"Sincronizzati {result['created']} nuovi utenti, {result['updated']} aggiornati", 'success')
    
    return redirect(url_for('respond_io.calendar_view'))


@bp.route('/schedules/user/<int:user_id>')
@login_required
def schedule_edit(user_id):
    """Modifica orari di un utente Respond.io"""
    
    user = RespondIOUser.query.get_or_404(user_id)
    
    # Solo admin possono modificare orari
    if not current_user.is_admin:
        flash('Solo gli amministratori possono modificare gli orari', 'error')
        return redirect(url_for('respond_io.calendar_view'))
    
    form = UserWorkScheduleForm()
    
    # Carica orari esistenti
    schedules = RespondIOUserWorkSchedule.query.filter_by(user_id=user_id).all()
    schedule_dict = {s.day_of_week: s for s in schedules}
    
    if request.method == 'GET':
        # Popola il form con i dati esistenti
        form.user_id.data = user_id
        
        # Ottieni timezone dall'ultimo schedule o default
        if schedules:
            form.timezone.data = schedules[0].timezone
        
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for i, day_name in enumerate(days):
            day_field = getattr(form, day_name)
            
            if i in schedule_dict:
                schedule = schedule_dict[i]
                day_field.is_active.data = schedule.is_active
                day_field.start_time.data = schedule.start_time
                day_field.end_time.data = schedule.end_time
                day_field.notes.data = schedule.notes
    
    return render_template('respond_io/schedule_edit.html',
                         form=form,
                         user=user)


@bp.route('/schedules/user/<int:user_id>', methods=['POST'])
@login_required
def schedule_save(user_id):
    """Salva orari di un utente Respond.io"""
    
    user = RespondIOUser.query.get_or_404(user_id)
    
    # Verifica permessi
    if not current_user.is_admin:
        return jsonify({'error': 'Permessi insufficienti'}), 403
    
    form = UserWorkScheduleForm()
    
    if form.validate_on_submit():
        try:
            # Elimina orari esistenti
            RespondIOUserWorkSchedule.query.filter_by(user_id=user_id).delete()
            
            # Salva nuovi orari
            days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            
            for i, day_name in enumerate(days):
                day_field = getattr(form, day_name)
                
                # Crea schedule solo se attivo o ha orari definiti
                if day_field.is_active.data or day_field.start_time.data:
                    schedule = RespondIOUserWorkSchedule(
                        user_id=user_id,
                        day_of_week=i,
                        is_active=day_field.is_active.data,
                        start_time=day_field.start_time.data or time(9, 0),
                        end_time=day_field.end_time.data or time(18, 0),
                        notes=day_field.notes.data,
                        timezone=form.timezone.data
                    )
                    db.session.add(schedule)
            
            db.session.commit()
            flash(f'Orari di {user.full_name} aggiornati con successo', 'success')
            
            return redirect(url_for('respond_io.calendar_view'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Errore nel salvataggio: {str(e)}', 'error')
    
    return render_template('respond_io/schedule_edit.html',
                         form=form,
                         user=user)


@bp.route('/schedules/bulk')
@login_required
def schedule_bulk():
    """Vista per configurazione orari multipli utenti Respond.io"""
    
    if not current_user.is_admin:
        flash('Solo gli amministratori possono configurare orari multipli', 'error')
        return redirect(url_for('respond_io.calendar_view'))
    
    form = BulkScheduleForm()
    
    # Popola utenti Respond.io disponibili
    users = RespondIOUser.query.filter_by(is_active=True).order_by(RespondIOUser.first_name).all()
    form.selected_users.choices = [(str(u.id), u.full_name) for u in users]
    
    return render_template('respond_io/schedule_bulk.html',
                         form=form,
                         users=users)


@bp.route('/schedules/bulk', methods=['POST'])
@login_required
def schedule_bulk_save():
    """Salva configurazione orari multipli per utenti Respond.io"""
    
    if not current_user.is_admin:
        return jsonify({'error': 'Permessi insufficienti'}), 403
    
    form = BulkScheduleForm()
    
    # Ripopola choices
    users = RespondIOUser.query.filter_by(is_active=True).all()
    form.selected_users.choices = [(str(u.id), u.full_name) for u in users]
    
    if form.validate_on_submit():
        try:
            # Determina utenti target
            if form.apply_to_all.data:
                target_users = users
            else:
                user_ids = [int(uid) for uid in form.selected_users.data]
                target_users = RespondIOUser.query.filter(RespondIOUser.id.in_(user_ids)).all()
            
            if not target_users:
                flash('Nessun utente selezionato', 'warning')
                return redirect(url_for('respond_io.schedule_bulk'))
            
            # Applica template a ogni utente
            for user in target_users:
                # Elimina orari esistenti
                RespondIOUserWorkSchedule.query.filter_by(user_id=user.id).delete()
                
                # Lunedì-Venerdì
                for day in range(5):
                    schedule = RespondIOUserWorkSchedule(
                        user_id=user.id,
                        day_of_week=day,
                        is_active=True,
                        start_time=form.template_weekdays_start.data,
                        end_time=form.template_weekdays_end.data,
                        timezone=form.timezone.data
                    )
                    db.session.add(schedule)
                
                # Sabato
                if form.enable_saturday.data:
                    schedule = RespondIOUserWorkSchedule(
                        user_id=user.id,
                        day_of_week=5,
                        is_active=True,
                        start_time=form.template_saturday_start.data,
                        end_time=form.template_saturday_end.data,
                        timezone=form.timezone.data
                    )
                    db.session.add(schedule)
                
                # Domenica
                if form.enable_sunday.data:
                    schedule = RespondIOUserWorkSchedule(
                        user_id=user.id,
                        day_of_week=6,
                        is_active=True,
                        start_time=form.template_sunday_start.data,
                        end_time=form.template_sunday_end.data,
                        timezone=form.timezone.data
                    )
                    db.session.add(schedule)
            
            db.session.commit()
            flash(f'Orari configurati per {len(target_users)} utenti Respond.io', 'success')
            
            return redirect(url_for('respond_io.calendar_view'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Errore nel salvataggio: {str(e)}', 'error')
    
    return render_template('respond_io/schedule_bulk.html',
                         form=form,
                         users=users)


@bp.route('/assignment-old')
@login_required
def assignment_dashboard_old():
    """Dashboard per assegnazioni automatiche con utenti Respond.io"""
    
    form = AutoAssignmentForm()
    service = ContactAssignmentService()
    
    # Ottieni filter_mode dal form o usa default
    filter_mode = request.args.get('filter_mode', 'waiting')
    form.filter_mode.data = filter_mode
    
    # Check se è richiesto il caricamento preview (solo quando esplicitamente richiesto)
    load_preview = request.args.get('load_preview', 'false') == 'true'
    
    if load_preview:
        # Carica preview solo se esplicitamente richiesto
        preview = service.get_assignment_preview(filter_mode)
    else:
        # Preview veloce: mostra solo utenti in turno senza contare i contatti
        users_on_duty = service.get_users_on_duty()
        preview = {
            'users_on_duty': [
                {
                    'id': u['id'],
                    'name': u['full_name'],
                    'email': u['email']
                }
                for u in users_on_duty
            ],
            'contacts_to_assign': 0,
            'already_assigned': 0,
            'distribution': {},
            'can_proceed': False,
            'filter_mode': filter_mode,
            'message': 'Clicca su "Carica Preview" per vedere i contatti da assegnare',
            'preview_loaded': False
        }
    
    # Ottieni log recenti
    recent_logs = service.get_recent_logs(limit=10)
    
    # Statistiche
    stats = {
        'users_on_duty': len(preview['users_on_duty']),
        'contacts_to_assign': preview.get('contacts_to_assign', 0),
        'last_assignment': None
    }
    
    if recent_logs:
        last_log = recent_logs[0]
        stats['last_assignment'] = {
            'date': last_log.started_at,
            'assigned': last_log.contacts_assigned,
            'total': last_log.total_contacts,
            'status': last_log.status
        }
    
    return render_template('respond_io/assignment_dashboard.html',
                         form=form,
                         preview=preview,
                         recent_logs=recent_logs,
                         stats=stats)


@bp.route('/assignment/preview', methods=['POST'])
@login_required
def assignment_preview():
    """API endpoint per preview assegnazioni"""
    
    # Ottieni filter_mode dal request
    data = request.get_json() or {}
    filter_mode = data.get('filter_mode', 'waiting')
    
    service = ContactAssignmentService()
    preview = service.get_assignment_preview(filter_mode)
    
    return jsonify(preview)


@bp.route('/assignment/execute', methods=['POST'])
@login_required
def assignment_execute():
    """Esegue assegnazione automatica a utenti Respond.io"""
    
    form = AutoAssignmentForm()
    
    if form.validate_on_submit():
        if not form.confirm_assignment.data:
            return jsonify({'error': 'Devi confermare l\'assegnazione'}), 400
        
        service = ContactAssignmentService()
        
        # Ottieni filter_mode dal form
        filter_mode = form.filter_mode.data or 'waiting'
        
        # Esegui assegnazione con il filter_mode specificato
        result = service.auto_assign_all_contacts(
            executed_by=current_user,
            filter_mode=filter_mode
        )
        
        if result['success']:
            flash(result['message'], 'success')
            
            # Log dettagli
            if 'stats' in result:
                stats = result['stats']
                flash(f"Assegnati {stats['assigned']} contatti a {stats['users_involved']} utenti Respond.io", 'info')
        else:
            flash(result['message'], 'error')
        
        return redirect(url_for('respond_io.assignment_dashboard_old'))
    
    # Form non valido
    errors = []
    for field, field_errors in form.errors.items():
        for error in field_errors:
            errors.append(f"{field}: {error}")
    
    return jsonify({'error': 'Form non valido', 'details': errors}), 400


@bp.route('/assignment/logs')
@login_required
def assignment_logs():
    """Visualizza storico assegnazioni"""
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    logs = RespondIOAssignmentLog.query.order_by(
        RespondIOAssignmentLog.started_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('respond_io/assignment_logs.html',
                         logs=logs)


@bp.route('/assignment/log/<int:log_id>')
@login_required
def assignment_log_detail(log_id):
    """Dettaglio singolo log assegnazione"""
    
    log = RespondIOAssignmentLog.query.get_or_404(log_id)
    
    return render_template('respond_io/assignment_log_detail.html',
                         log=log)


@bp.route('/api/schedules/current-users')
@login_required
def api_current_users_on_duty():
    """API endpoint per ottenere utenti Respond.io attualmente in turno"""
    
    service = ContactAssignmentService()
    users = service.get_users_on_duty()
    
    return jsonify({
        'count': len(users),
        'users': [
            {
                'id': u['id'],
                'respond_io_id': u['respond_io_id'],
                'name': u['full_name'],
                'email': u['email']
            }
            for u in users
        ]
    })


@bp.route('/api/schedules/sync-users', methods=['POST'])
@login_required
def api_sync_workspace_users():
    """API per sincronizzare utenti workspace Respond.io"""
    
    if not current_user.is_admin:
        return jsonify({'error': 'Permessi insufficienti'}), 403
    
    service = ContactAssignmentService()
    result = service.sync_workspace_users()
    
    if result['errors']:
        return jsonify({
            'success': False,
            'message': f"Sincronizzazione parziale: {result['errors'][0]}",
            'errors': result['errors'],
            'created': result['created'],
            'updated': result['updated']
        }), 207  # Partial success
    
    return jsonify({
        'success': True,
        'message': f"Sincronizzati {result['created']} nuovi utenti, {result['updated']} aggiornati",
        'users': result['users']
    })