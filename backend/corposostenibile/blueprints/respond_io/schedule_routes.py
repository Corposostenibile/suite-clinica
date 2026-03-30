"""
Routes per gestione orari di lavoro e assegnazioni automatiche
Utilizza gli utenti del workspace Respond.io
"""

from datetime import datetime, time
from flask import request, jsonify, flash, redirect, url_for
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
    """API endpoint for schedule edit"""
    # HTML form deleted - use API instead
    return jsonify({'error': 'Use API instead'}), 404


@bp.route('/schedules/user/<int:user_id>', methods=['POST'])
@login_required
def schedule_save(user_id):
    """API endpoint for schedule save"""
    # HTML form deleted - use API instead
    return jsonify({'error': 'Use API instead'}), 404


@bp.route('/schedules/bulk')
@login_required
def schedule_bulk():
    """API endpoint for bulk schedule view"""
    # HTML form deleted - use API instead
    return jsonify({'error': 'Use API instead'}), 404


@bp.route('/schedules/bulk', methods=['POST'])
@login_required
def schedule_bulk_save():
    """API endpoint for bulk schedule save"""
    # HTML form deleted - use API instead
    return jsonify({'error': 'Use API instead'}), 404


@bp.route('/assignment-old')
@login_required
def assignment_dashboard_old():
    """API endpoint for assignment dashboard"""
    # HTML dashboard deleted - use API instead
    return jsonify({'error': 'Use API instead'}), 404


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
    """API endpoint for assignment logs"""
    # HTML page deleted - use API instead
    return jsonify({'error': 'Use API instead'}), 404


@bp.route('/assignment/log/<int:log_id>')
@login_required
def assignment_log_detail(log_id):
    """API endpoint for assignment log detail"""
    # HTML page deleted - use API instead
    return jsonify({'error': 'Use API instead'}), 404


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