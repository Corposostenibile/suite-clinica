"""
Routes per gestione turni utenti (non admin)
"""

from datetime import datetime, date, timedelta
from flask import render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from sqlalchemy import and_, func
from corposostenibile.extensions import db
from corposostenibile.models import (
    User,
    RespondIOUser,
    RespondIOCalendarEvent,
    RespondIOUserWorkSchedule,
    RespondIOWorkTimestamp,
    RespondIOCalendarBreak
)
from . import bp
import pytz


@bp.route('/my-shifts')
@login_required
def my_shifts():
    """Vista turni personali per utenti con profilo Respond.io"""
    
    # Verifica se l'utente ha un profilo Respond.io associato
    if not current_user.respond_io_profile:
        flash('Non hai un profilo Respond.io associato. Contatta l\'amministratore.', 'warning')
        return redirect(url_for('base.index'))
    
    # Ottieni settimana corrente
    tz = pytz.timezone('Europe/Rome')
    now = datetime.now(tz)
    today = now.date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    # Ottieni turni della settimana
    respond_io_user = current_user.respond_io_profile
    
    # Converti date in datetime per il confronto con eventi
    week_start_datetime = datetime.combine(week_start, datetime.min.time()).replace(tzinfo=tz)
    week_end_datetime = datetime.combine(week_end, datetime.max.time()).replace(tzinfo=tz)
    
    # Eventi calendario - CORRETTO: usa respond_io_user.id
    calendar_events = RespondIOCalendarEvent.query.filter(
        and_(
            RespondIOCalendarEvent.user_id == respond_io_user.id,  # ID corretto del RespondIOUser
            RespondIOCalendarEvent.start_datetime >= week_start_datetime,
            RespondIOCalendarEvent.start_datetime <= week_end_datetime,
            RespondIOCalendarEvent.event_type == 'work',
            RespondIOCalendarEvent.status != 'cancelled'
        )
    ).order_by(RespondIOCalendarEvent.start_datetime).all()
    
    # Turni settimanali ricorrenti - CORRETTO: usa respond_io_user.id
    weekly_schedules = RespondIOUserWorkSchedule.query.filter_by(
        user_id=respond_io_user.id,  # ID corretto del RespondIOUser
        is_active=True
    ).all()
    
    
    # Stato attuale del turno
    current_status = RespondIOWorkTimestamp.get_current_status(current_user.id)
    
    # Turno di oggi (se esiste)
    today_shift = None
    today_dow = today.weekday()
    
    # Prima cerca negli eventi
    for event in calendar_events:
        if event.start_datetime.date() == today:
            today_shift = {
                'id': event.id,
                'type': 'event',
                'start': event.start_datetime.strftime('%H:%M'),
                'end': event.end_datetime.strftime('%H:%M'),
                'title': event.title
            }
            break
    
    # Se non c'è evento, cerca nei turni settimanali
    if not today_shift:
        for schedule in weekly_schedules:
            if schedule.day_of_week == today_dow:
                today_shift = {
                    'id': schedule.id,
                    'type': 'schedule',
                    'start': schedule.start_time.strftime('%H:%M') if schedule.start_time else '09:00',
                    'end': schedule.end_time.strftime('%H:%M') if schedule.end_time else '18:00',
                    'title': 'Turno programmato'
                }
                break
    
    # Timbrature di oggi
    today_timestamps = RespondIOWorkTimestamp.query.filter(
        and_(
            RespondIOWorkTimestamp.user_id == current_user.id,
            func.date(RespondIOWorkTimestamp.timestamp) == today
        )
    ).order_by(RespondIOWorkTimestamp.timestamp).all()
    
    # Crea un dizionario con gli eventi per ogni giorno della settimana
    events_by_day = {}
    for i in range(7):
        day = week_start + timedelta(days=i)
        events_by_day[day.strftime('%Y-%m-%d')] = None
        
        # Cerca evento per questo giorno
        for event in calendar_events:
            if event.start_datetime.date() == day:
                events_by_day[day.strftime('%Y-%m-%d')] = {
                    'start': event.start_datetime.strftime('%H:%M'),
                    'end': event.end_datetime.strftime('%H:%M'),
                    'title': event.title,
                    'type': event.event_type
                }
                break
    
    return render_template('respond_io/my_shifts.html',
                         calendar_events=calendar_events,
                         weekly_schedules=weekly_schedules,
                         events_by_day=events_by_day,  # Passa il dizionario eventi per giorno
                         current_status=current_status,
                         today_shift=today_shift,
                         today_timestamps=today_timestamps,
                         today=today,
                         week_start=week_start,
                         week_end=week_end,
                         timedelta=timedelta)  # Passa timedelta al template


@bp.route('/timestamp-form', methods=['POST'])
@login_required
def create_timestamp_form():
    """Crea una nuova timbratura tramite form HTML"""
    
    # Ottieni dati dal form invece che da JSON
    timestamp_type = request.form.get('timestamp_type')
    notes = request.form.get('notes', '')
    
    # Validazione tipo
    valid_types = ['start', 'pause_start', 'pause_end', 'end']
    if timestamp_type not in valid_types:
        flash('Tipo timbratura non valido', 'danger')
        return redirect(url_for('respond_io.my_shifts'))
    
    # Verifica profilo Respond.io
    if not current_user.respond_io_profile:
        flash('Profilo Respond.io non associato. Contatta l\'amministratore.', 'danger')
        return redirect(url_for('respond_io.my_shifts'))
    
    try:
        # Ottieni stato attuale
        current_status = RespondIOWorkTimestamp.get_current_status(current_user.id)
        
        # Validazioni logiche
        if timestamp_type == 'start' and current_status != 'not_started':
            flash('Turno già iniziato', 'warning')
            return redirect(url_for('respond_io.my_shifts'))
        
        if timestamp_type == 'pause_start' and current_status != 'working':
            flash('Non puoi iniziare una pausa se non stai lavorando', 'warning')
            return redirect(url_for('respond_io.my_shifts'))
        
        if timestamp_type == 'pause_end' and current_status != 'paused':
            flash('Non sei in pausa', 'warning')
            return redirect(url_for('respond_io.my_shifts'))
        
        if timestamp_type == 'end' and current_status not in ['working', 'paused']:
            flash('Non puoi terminare un turno non iniziato', 'warning')
            return redirect(url_for('respond_io.my_shifts'))
        
        # Determina nuovo stato
        new_status = {
            'start': 'working',
            'pause_start': 'paused',
            'pause_end': 'working',
            'end': 'ended'
        }[timestamp_type]
        
        # Trova evento calendario correlato (se esiste)
        tz = pytz.timezone('Europe/Rome')
        now = datetime.now(tz)
        calendar_event = RespondIOCalendarEvent.query.filter(
            and_(
                RespondIOCalendarEvent.user_id == current_user.respond_io_profile.id,
                RespondIOCalendarEvent.start_datetime <= now,
                RespondIOCalendarEvent.end_datetime >= now,
                RespondIOCalendarEvent.event_type == 'work',
                RespondIOCalendarEvent.status != 'cancelled'
            )
        ).first()
        
        # Crea timbratura
        timestamp = RespondIOWorkTimestamp(
            user_id=current_user.id,
            timestamp_type=timestamp_type,
            timestamp=now,
            current_status=new_status,
            calendar_event_id=calendar_event.id if calendar_event else None,
            notes=notes
        )
        
        db.session.add(timestamp)
        
        # Se è una pausa, gestisci anche RespondIOCalendarBreak
        if timestamp_type == 'pause_end' and calendar_event:
            # Trova l'inizio della pausa
            pause_start = RespondIOWorkTimestamp.query.filter(
                and_(
                    RespondIOWorkTimestamp.user_id == current_user.id,
                    RespondIOWorkTimestamp.timestamp_type == 'pause_start',
                    func.date(RespondIOWorkTimestamp.timestamp) == date.today()
                )
            ).order_by(RespondIOWorkTimestamp.timestamp.desc()).first()
            
            if pause_start:
                # Crea record pausa nel calendario
                calendar_break = RespondIOCalendarBreak(
                    event_id=calendar_event.id,
                    start_time=pause_start.timestamp,
                    end_time=now,
                    notes='Pausa registrata da timbratura',
                    created_by_id=current_user.id
                )
                db.session.add(calendar_break)
        
        db.session.commit()
        
        # NUOVO: Triggera assegnazione automatica basata su timbratura
        try:
            from flask import current_app
            current_app.logger.info(f"[TIMESTAMP] About to trigger assignment for {timestamp_type} by {current_user.email}")
            
            # Verifica se il servizio esiste
            if not hasattr(current_app, 'timestamp_assignment_service'):
                current_app.logger.error("[TIMESTAMP] ERROR: timestamp_assignment_service not found in app!")
                # Prova a inizializzarlo al volo
                from .timestamp_assignment_service import TimestampAssignmentService
                current_app.timestamp_assignment_service = TimestampAssignmentService(current_app.respond_io_client)
                current_app.logger.info("[TIMESTAMP] Service initialized on-the-fly")
            
            current_app.timestamp_assignment_service.handle_timestamp_event(
                current_user, 
                timestamp_type
            )
            current_app.logger.info(f"[TIMESTAMP] Successfully triggered assignment for {timestamp_type} by {current_user.email}")
        except Exception as assign_error:
            current_app.logger.error(f"[TIMESTAMP] Failed to trigger assignment: {assign_error}", exc_info=True)
            # Non bloccare la timbratura se l'assegnazione fallisce
        
        # Messaggi di successo
        messages = {
            'start': 'Turno iniziato con successo! Assegnazione contatti in corso...',
            'pause_start': 'Pausa iniziata. Redistribuzione contatti in corso...',
            'pause_end': 'Turno ripreso. Ribilanciamento contatti in corso...',
            'end': 'Turno terminato. Redistribuzione contatti in corso...'
        }
        
        flash(messages[timestamp_type], 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore timbratura: {str(e)}")
        flash(f'Errore durante la timbratura: {str(e)}', 'danger')
    
    return redirect(url_for('respond_io.my_shifts'))


@bp.route('/timestamp', methods=['POST'])
@login_required
def create_timestamp():
    """Crea una nuova timbratura"""
    
    data = request.get_json()
    timestamp_type = data.get('type')
    
    # Validazione tipo
    valid_types = ['start', 'pause_start', 'pause_end', 'end']
    if timestamp_type not in valid_types:
        return jsonify({'success': False, 'error': 'Tipo timbratura non valido'}), 400
    
    # Verifica profilo Respond.io
    if not current_user.respond_io_profile:
        return jsonify({'success': False, 'error': 'Profilo Respond.io non associato'}), 403
    
    try:
        # Ottieni stato attuale
        current_status = RespondIOWorkTimestamp.get_current_status(current_user.id)
        
        # Validazioni logiche
        if timestamp_type == 'start' and current_status != 'not_started':
            return jsonify({'success': False, 'error': 'Turno già iniziato'}), 400
        
        if timestamp_type == 'pause_start' and current_status != 'working':
            return jsonify({'success': False, 'error': 'Non puoi iniziare una pausa se non stai lavorando'}), 400
        
        if timestamp_type == 'pause_end' and current_status != 'paused':
            return jsonify({'success': False, 'error': 'Non sei in pausa'}), 400
        
        if timestamp_type == 'end' and current_status not in ['working', 'paused']:
            return jsonify({'success': False, 'error': 'Non puoi terminare un turno non iniziato'}), 400
        
        # Determina nuovo stato
        new_status = {
            'start': 'working',
            'pause_start': 'paused',
            'pause_end': 'working',
            'end': 'ended'
        }[timestamp_type]
        
        # Trova evento calendario correlato (se esiste)
        tz = pytz.timezone('Europe/Rome')
        now = datetime.now(tz)
        calendar_event = RespondIOCalendarEvent.query.filter(
            and_(
                RespondIOCalendarEvent.user_id == current_user.respond_io_profile.id,
                RespondIOCalendarEvent.start_datetime <= now,
                RespondIOCalendarEvent.end_datetime >= now,
                RespondIOCalendarEvent.event_type == 'work',
                RespondIOCalendarEvent.status != 'cancelled'
            )
        ).first()
        
        # Crea timbratura
        timestamp = RespondIOWorkTimestamp(
            user_id=current_user.id,
            timestamp_type=timestamp_type,
            timestamp=now,
            current_status=new_status,
            calendar_event_id=calendar_event.id if calendar_event else None,
            notes=data.get('notes', '')
        )
        
        db.session.add(timestamp)
        
        # Se è una pausa, crea anche record in RespondIOCalendarBreak
        if timestamp_type == 'pause_start' and calendar_event:
            # Salveremo l'end_time quando farà pause_end
            pass
        elif timestamp_type == 'pause_end' and calendar_event:
            # Trova l'inizio della pausa
            pause_start = RespondIOWorkTimestamp.query.filter(
                and_(
                    RespondIOWorkTimestamp.user_id == current_user.id,
                    RespondIOWorkTimestamp.timestamp_type == 'pause_start',
                    func.date(RespondIOWorkTimestamp.timestamp) == date.today()
                )
            ).order_by(RespondIOWorkTimestamp.timestamp.desc()).first()
            
            if pause_start:
                # Crea record pausa nel calendario
                calendar_break = RespondIOCalendarBreak(
                    event_id=calendar_event.id,
                    start_time=pause_start.timestamp,
                    end_time=now,
                    notes='Pausa registrata da timbratura',
                    created_by_id=current_user.id
                )
                db.session.add(calendar_break)
        
        db.session.commit()
        
        # NUOVO: Triggera assegnazione automatica basata su timbratura
        try:
            from flask import current_app
            current_app.logger.info(f"[TIMESTAMP] About to trigger assignment for {timestamp_type} by {current_user.email}")
            
            # Verifica se il servizio esiste
            if not hasattr(current_app, 'timestamp_assignment_service'):
                current_app.logger.error("[TIMESTAMP] ERROR: timestamp_assignment_service not found in app!")
                # Prova a inizializzarlo al volo
                from .timestamp_assignment_service import TimestampAssignmentService
                current_app.timestamp_assignment_service = TimestampAssignmentService(current_app.respond_io_client)
                current_app.logger.info("[TIMESTAMP] Service initialized on-the-fly")
            
            current_app.timestamp_assignment_service.handle_timestamp_event(
                current_user, 
                timestamp_type
            )
            current_app.logger.info(f"[TIMESTAMP] Successfully triggered assignment for {timestamp_type} by {current_user.email}")
        except Exception as assign_error:
            current_app.logger.error(f"[TIMESTAMP] Failed to trigger assignment: {assign_error}", exc_info=True)
            # Non bloccare la timbratura se l'assegnazione fallisce
        
        return jsonify({
            'success': True,
            'new_status': new_status,
            'timestamp': timestamp.timestamp.isoformat(),
            'assignment_triggered': True
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore timbratura: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/my-shifts/week/<string:direction>')
@login_required
def navigate_week(direction):
    """Naviga tra le settimane"""
    
    # Implementazione navigazione settimane
    # TODO: Implementare navigazione
    pass


@bp.route('/my-shifts/stats')
@login_required
def my_shift_stats():
    """Statistiche personali turni"""
    
    if not current_user.respond_io_profile:
        return jsonify({'error': 'No Respond.io profile'}), 403
    
    # Calcola statistiche del mese
    tz = pytz.timezone('Europe/Rome')
    now = datetime.now(tz)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Timbrature del mese
    timestamps = RespondIOWorkTimestamp.query.filter(
        and_(
            RespondIOWorkTimestamp.user_id == current_user.id,
            RespondIOWorkTimestamp.timestamp >= month_start
        )
    ).all()
    
    # Calcola ore totali, pause, etc.
    total_hours = 0
    total_breaks = 0
    days_worked = set()
    
    for ts in timestamps:
        days_worked.add(ts.timestamp.date())
        # TODO: Calcolare ore effettive
    
    return jsonify({
        'month': now.strftime('%B %Y'),
        'days_worked': len(days_worked),
        'total_hours': round(total_hours, 1),
        'total_breaks': round(total_breaks, 1),
        'avg_hours_per_day': round(total_hours / len(days_worked), 1) if days_worked else 0
    })