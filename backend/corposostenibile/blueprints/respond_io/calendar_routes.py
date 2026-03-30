"""
Routes per calendario interattivo stile Google Calendar
"""

from datetime import datetime, date, timedelta, time
from flask import request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from sqlalchemy import and_, or_ as db_or, func
from corposostenibile.extensions import db
from corposostenibile.models import (
    User,
    RespondIOUser,
    RespondIOCalendarEvent,
    RespondIOScheduleTemplate,
    RespondIOWorkHistory,
    RespondIOTimeOff,
    RespondIOUserWorkSchedule,
    RespondIOCalendarBreak,
    RespondIOWorkTimestamp
)
from . import bp
import pytz


def generate_time_off_events(start_date, end_date, user_ids=None):
    """
    Genera eventi per ferie e assenze approvate.
    """
    events = []
    
    # Query per time off approvati
    query = RespondIOTimeOff.query.filter(
        and_(
            RespondIOTimeOff.status == 'approved',
            RespondIOTimeOff.start_date <= end_date.date() if hasattr(end_date, 'date') else end_date,
            RespondIOTimeOff.end_date >= start_date.date() if hasattr(start_date, 'date') else start_date
        )
    )
    
    if user_ids:
        query = query.filter(RespondIOTimeOff.user_id.in_(user_ids))
    
    time_offs = query.all()
    
    for time_off in time_offs:
        # Crea evento per ogni giorno di ferie
        current_date = max(time_off.start_date, start_date.date() if hasattr(start_date, 'date') else start_date)
        end_date_limit = min(time_off.end_date, end_date.date() if hasattr(end_date, 'date') else end_date)
        
        while current_date <= end_date_limit:
            event = {
                'id': f'timeoff_{time_off.id}_{current_date}',
                'title': f'Ferie: {time_off.user.full_name if time_off.user else "N/A"}',
                'start': current_date.isoformat(),
                'end': current_date.isoformat(),
                'allDay': True,
                'color': '#dc3545',  # Rosso per ferie
                'extendedProps': {
                    'event_type': 'holiday',
                    'status': 'approved',
                    'notes': time_off.reason or 'Ferie/Assenza',
                    'location': '',
                    'user_id': time_off.user_id,
                    'user_name': time_off.user.full_name if time_off.user else None,
                    'is_recurring': False,
                    'from_time_off': True
                }
            }
            events.append(event)
            current_date += timedelta(days=1)
    
    return events


def generate_events_from_weekly_schedules(start_date, end_date, user_ids=None):
    """
    Genera eventi del calendario basati sugli orari settimanali configurati.
    Questo permette di visualizzare i turni ricorrenti senza doverli salvare come eventi.
    """
    events = []
    
    # Prima controlla se ci sono eventi salvati nel calendario per questo periodo
    # Se ci sono, non generare eventi automatici per evitare duplicati
    saved_events = RespondIOCalendarEvent.query.filter(
        and_(
            RespondIOCalendarEvent.start_datetime >= start_date,
            RespondIOCalendarEvent.start_datetime <= end_date,
            RespondIOCalendarEvent.event_type == 'work',
            RespondIOCalendarEvent.status != 'cancelled'
        )
    ).all()
    
    # Se ci sono già eventi salvati, ritorna solo quelli
    if saved_events:
        return []  # Non generare eventi automatici se ci sono già eventi salvati
    
    # Query per ottenere gli schedules
    query = RespondIOUserWorkSchedule.query.filter_by(is_active=True)
    
    # Filtra per utenti se specificati
    if user_ids:
        user_ids = [int(uid) for uid in user_ids if uid]
        query = query.filter(RespondIOUserWorkSchedule.user_id.in_(user_ids))
    
    schedules = query.all()
    
    # Genera eventi per ogni giorno nel range
    current_date = start_date.date() if hasattr(start_date, 'date') else start_date
    end_date_only = end_date.date() if hasattr(end_date, 'date') else end_date
    
    while current_date <= end_date_only:
        day_of_week = current_date.weekday()
        
        # Trova schedules per questo giorno della settimana
        for schedule in schedules:
            if schedule.day_of_week == day_of_week and schedule.is_active:
                # Crea evento virtuale per questo turno
                tz = pytz.timezone(schedule.timezone or 'Europe/Rome')
                
                # Combina data con orari
                start_datetime = tz.localize(datetime.combine(
                    current_date, 
                    schedule.start_time or time(9, 0)
                ))
                end_datetime = tz.localize(datetime.combine(
                    current_date, 
                    schedule.end_time or time(18, 0)
                ))
                
                # Crea dizionario evento in formato FullCalendar
                event = {
                    'id': f'schedule_{schedule.id}_{current_date}',
                    'title': f'{schedule.user.full_name} - Turno',
                    'start': start_datetime.isoformat(),
                    'end': end_datetime.isoformat(),
                    'allDay': False,
                    'color': '#28a745',  # Verde per turni di lavoro
                    'extendedProps': {
                        'event_type': 'work',
                        'status': 'scheduled',
                        'notes': schedule.notes or 'Turno programmato da orario settimanale',
                        'location': '',
                        'user_id': schedule.user_id,
                        'user_name': schedule.user.full_name if schedule.user else None,
                        'is_recurring': True,
                        'from_weekly_schedule': True  # Flag per distinguere da eventi salvati
                    }
                }
                events.append(event)
        
        # Passa al giorno successivo
        current_date += timedelta(days=1)
    
    return events


@bp.route('/calendar/events')
@login_required
def get_calendar_events():
    """API endpoint per recuperare eventi del calendario"""
    
    # Parametri dalla richiesta
    start = request.args.get('start')
    end = request.args.get('end')
    user_ids = request.args.getlist('user_ids[]')
    event_types = request.args.getlist('event_types[]')
    
    # Converti date
    try:
        start_date = datetime.fromisoformat(start.replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(end.replace('Z', '+00:00'))
    except:
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now() + timedelta(days=30)
    
    # Query base per eventi salvati
    query = RespondIOCalendarEvent.query.filter(
        RespondIOCalendarEvent.start_datetime <= end_date,
        RespondIOCalendarEvent.end_datetime >= start_date
    )
    
    # Filtri opzionali
    if user_ids:
        user_ids = [int(uid) for uid in user_ids if uid]
        query = query.filter(RespondIOCalendarEvent.user_id.in_(user_ids))
    
    if event_types:
        query = query.filter(RespondIOCalendarEvent.event_type.in_(event_types))
    
    # Escludi eventi cancellati
    query = query.filter(RespondIOCalendarEvent.status != 'cancelled')
    
    # Ottieni eventi salvati
    events = query.all()
    
    # Converti in formato FullCalendar
    calendar_events = [event.to_fullcalendar_dict() for event in events]
    
    # Aggiungi eventi ricorrenti generati
    for event in events:
        if event.is_recurring:
            recurring_events = event.generate_recurring_events(start_date, end_date)
            calendar_events.extend(recurring_events)
    
    # IMPORTANTE: Genera eventi dai turni settimanali se non ci sono eventi salvati
    # o se è richiesto il tipo "work"
    if not event_types or 'work' in event_types:
        weekly_events = generate_events_from_weekly_schedules(
            start_date, end_date, user_ids
        )
        calendar_events.extend(weekly_events)
    
    # Aggiungi eventi per ferie/assenze approvate
    if not event_types or 'holiday' in event_types:
        time_off_events = generate_time_off_events(start_date, end_date, user_ids)
        calendar_events.extend(time_off_events)
    
    return jsonify(calendar_events)


@bp.route('/calendar/event', methods=['POST'])
@login_required
def create_calendar_event():
    """Crea un nuovo evento nel calendario"""
    
    data = request.get_json()
    
    # Validazione base
    required_fields = ['user_id', 'title', 'start', 'end']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Campo mancante: {field}'}), 400
    
    try:
        # Crea nuovo evento
        event = RespondIOCalendarEvent(
            user_id=data['user_id'],
            title=data['title'],
            start_datetime=datetime.fromisoformat(data['start'].replace('Z', '+00:00')),
            end_datetime=datetime.fromisoformat(data['end'].replace('Z', '+00:00')),
            all_day=data.get('allDay', False),
            event_type=data.get('event_type', 'work'),
            color=data.get('color', '#3788d8'),
            notes=data.get('notes', ''),
            location=data.get('location', ''),
            is_recurring=data.get('is_recurring', False),
            recurrence_rule=data.get('recurrence_rule'),
            created_by_id=current_user.id
        )
        
        db.session.add(event)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'event': event.to_fullcalendar_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore creazione evento: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/calendar/event/<int:event_id>', methods=['PUT'])
@login_required
def update_calendar_event(event_id):
    """Aggiorna un evento esistente"""
    
    event = RespondIOCalendarEvent.query.get_or_404(event_id)
    data = request.get_json()
    
    try:
        # Aggiorna campi
        if 'title' in data:
            event.title = data['title']
        if 'start' in data:
            event.start_datetime = datetime.fromisoformat(data['start'].replace('Z', '+00:00'))
        if 'end' in data:
            event.end_datetime = datetime.fromisoformat(data['end'].replace('Z', '+00:00'))
        if 'user_id' in data:
            event.user_id = data['user_id']
        if 'event_type' in data:
            event.event_type = data['event_type']
        if 'color' in data:
            event.color = data['color']
        if 'notes' in data:
            event.notes = data['notes']
        if 'location' in data:
            event.location = data['location']
        if 'allDay' in data:
            event.all_day = data['allDay']
        
        event.updated_by_id = current_user.id
        db.session.commit()
        
        return jsonify({
            'success': True,
            'event': event.to_fullcalendar_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore aggiornamento evento: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/calendar/event/<int:event_id>', methods=['DELETE'])
@login_required
def delete_calendar_event(event_id):
    """Elimina un evento dal calendario"""
    
    event = RespondIOCalendarEvent.query.get_or_404(event_id)
    
    try:
        # Se è un evento ricorrente, chiedi conferma
        if event.is_recurring:
            delete_all = request.args.get('delete_all', 'false') == 'true'
            if delete_all and event.parent_event_id is None:
                # Elimina anche tutte le istanze ricorrenti
                RespondIOCalendarEvent.query.filter_by(parent_event_id=event.id).delete()
        
        db.session.delete(event)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore eliminazione evento: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/calendar/event/<int:event_id>/drag', methods=['POST'])
@login_required
def drag_calendar_event(event_id):
    """Gestisce il drag & drop di un evento"""
    
    event = RespondIOCalendarEvent.query.get_or_404(event_id)
    data = request.get_json()
    
    try:
        # Calcola il delta
        if 'delta' in data:
            delta_ms = data['delta']
            delta = timedelta(milliseconds=delta_ms)
            event.start_datetime += delta
            event.end_datetime += delta
        else:
            # Nuovo orario assoluto
            if 'start' in data:
                event.start_datetime = datetime.fromisoformat(data['start'].replace('Z', '+00:00'))
            if 'end' in data:
                event.end_datetime = datetime.fromisoformat(data['end'].replace('Z', '+00:00'))
        
        event.updated_by_id = current_user.id
        db.session.commit()
        
        return jsonify({
            'success': True,
            'event': event.to_fullcalendar_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore drag evento: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/calendar/event/<int:event_id>/resize', methods=['POST'])
@login_required
def resize_calendar_event(event_id):
    """Gestisce il ridimensionamento di un evento"""
    
    event = RespondIOCalendarEvent.query.get_or_404(event_id)
    data = request.get_json()
    
    try:
        # Nuovo orario di fine
        if 'end' in data:
            event.end_datetime = datetime.fromisoformat(data['end'].replace('Z', '+00:00'))
        elif 'delta' in data:
            delta_ms = data['delta']
            delta = timedelta(milliseconds=delta_ms)
            event.end_datetime += delta
        
        event.updated_by_id = current_user.id
        db.session.commit()
        
        return jsonify({
            'success': True,
            'event': event.to_fullcalendar_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore resize evento: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/calendar/template/<int:template_id>/apply', methods=['POST'])
@login_required
def apply_schedule_template(template_id):
    """Applica un template di orari a uno o più utenti"""
    
    template = RespondIOScheduleTemplate.query.get_or_404(template_id)
    data = request.get_json()
    
    user_ids = data.get('user_ids', [])
    start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
    end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00'))
    
    created_events = []
    
    try:
        for user_id in user_ids:
            # Genera eventi dal template
            events = template.apply_to_user(user_id, start_date, end_date)
            
            for event_data in events:
                event = RespondIOCalendarEvent(
                    user_id=user_id,
                    title=event_data['title'],
                    start_datetime=event_data['start'],
                    end_datetime=event_data['end'],
                    event_type='work',
                    color=template.color,
                    created_by_id=current_user.id
                )
                db.session.add(event)
                created_events.append(event)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'events_created': len(created_events)
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore applicazione template: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/calendar/work-history')
@login_required
def get_work_history():
    """Recupera lo storico del lavoro per analisi"""
    
    user_id = request.args.get('user_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Query base
    query = RespondIOWorkHistory.query
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    if start_date:
        start = datetime.fromisoformat(start_date)
        query = query.filter(RespondIOWorkHistory.actual_start >= start)
    
    if end_date:
        end = datetime.fromisoformat(end_date)
        query = query.filter(RespondIOWorkHistory.actual_start <= end)
    
    history = query.order_by(RespondIOWorkHistory.actual_start.desc()).limit(100).all()
    
    # Prepara dati per JSON
    history_data = []
    for record in history:
        history_data.append({
            'id': record.id,
            'user_id': record.user_id,
            'user_name': record.user.full_name if record.user else 'N/A',
            'actual_start': record.actual_start.isoformat(),
            'actual_end': record.actual_end.isoformat() if record.actual_end else None,
            'duration_minutes': record.actual_duration_minutes,
            'conversations_handled': record.conversations_handled,
            'messages_sent': record.messages_sent,
            'efficiency_score': record.efficiency_score,
            'performance_rating': record.performance_rating
        })
    
    return jsonify(history_data)


@bp.route('/calendar/time-off', methods=['GET', 'POST'])
@login_required
def manage_time_off():
    """Gestisce richieste di ferie/assenze"""
    
    if request.method == 'POST':
        data = request.get_json()
        
        try:
            time_off = RespondIOTimeOff(
                user_id=data['user_id'],
                start_date=datetime.fromisoformat(data['start_date']).date(),
                end_date=datetime.fromisoformat(data['end_date']).date(),
                type=data['type'],
                reason=data.get('reason', ''),
                notes=data.get('notes', '')
            )
            
            db.session.add(time_off)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'time_off_id': time_off.id
            })
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Errore creazione time off: {e}")
            return jsonify({'error': str(e)}), 500
    
    else:
        # GET - Recupera richieste di ferie
        query = RespondIOTimeOff.query
        
        user_id = request.args.get('user_id', type=int)
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        status = request.args.get('status')
        if status:
            query = query.filter_by(status=status)
        
        time_offs = query.order_by(RespondIOTimeOff.start_date.desc()).limit(50).all()
        
        time_off_data = []
        for to in time_offs:
            time_off_data.append({
                'id': to.id,
                'user_id': to.user_id,
                'user_name': to.user.full_name if to.user else 'N/A',
                'start_date': to.start_date.isoformat(),
                'end_date': to.end_date.isoformat(),
                'type': to.type,
                'status': to.status,
                'total_days': to.total_days,
                'reason': to.reason
            })
        
        return jsonify(time_off_data)


@bp.route('/calendar/breaks', methods=['POST'])
@login_required
def add_calendar_break():
    """Aggiungi una pausa a un turno di lavoro"""
    
    data = request.get_json()
    
    # Validazione dati
    event_id = data.get('event_id')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    notes = data.get('notes', '')
    
    if not all([event_id, start_time, end_time]):
        return jsonify({'success': False, 'error': 'Dati mancanti'}), 400
    
    try:
        # Verifica che l'evento esista
        event = RespondIOCalendarEvent.query.get(event_id)
        if not event:
            return jsonify({'success': False, 'error': 'Evento non trovato'}), 404
        
        # Verifica permessi (solo admin o proprietario dell'evento)
        if not current_user.is_admin and event.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Non autorizzato'}), 403
        
        # Converti stringhe in datetime
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        
        # Verifica che la pausa sia all'interno del turno
        if start_dt < event.start_datetime or end_dt > event.end_datetime:
            return jsonify({'success': False, 'error': 'La pausa deve essere all\'interno del turno'}), 400
        
        # Verifica che non si sovrapponga con altre pause
        existing_breaks = RespondIOCalendarBreak.query.filter_by(event_id=event_id).all()
        for existing_break in existing_breaks:
            if not (end_dt <= existing_break.start_time or start_dt >= existing_break.end_time):
                return jsonify({'success': False, 'error': 'La pausa si sovrappone con un\'altra pausa esistente'}), 400
        
        # Crea la nuova pausa
        new_break = RespondIOCalendarBreak(
            event_id=event_id,
            start_time=start_dt,
            end_time=end_dt,
            notes=notes,
            created_by_id=current_user.id
        )
        
        db.session.add(new_break)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'break': new_break.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore aggiunta pausa: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/calendar/breaks/<int:break_id>', methods=['DELETE'])
@login_required
def delete_calendar_break(break_id):
    """Elimina una pausa"""
    
    try:
        # Trova la pausa
        break_item = RespondIOCalendarBreak.query.get(break_id)
        if not break_item:
            return jsonify({'success': False, 'error': 'Pausa non trovata'}), 404
        
        # Verifica permessi
        event = break_item.event
        if not current_user.is_admin and event.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Non autorizzato'}), 403
        
        # Elimina la pausa
        db.session.delete(break_item)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore eliminazione pausa: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/calendar/associate-user', methods=['POST'])
@login_required
def associate_user():
    """API per associare un utente Respond.io a un utente del sistema"""
    
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Non autorizzato'}), 403
    
    data = request.get_json()
    respond_io_user_id = data.get('respond_io_user_id')
    system_user_id = data.get('system_user_id')
    
    try:
        respond_io_user = RespondIOUser.query.get_or_404(respond_io_user_id)
        
        if system_user_id:
            # Verifica che l'utente sistema esista
            system_user = User.query.get_or_404(system_user_id)
            
            # Verifica che non sia già associato a un altro utente Respond.io
            existing = RespondIOUser.query.filter(
                and_(
                    RespondIOUser.user_id == system_user_id,
                    RespondIOUser.id != respond_io_user_id
                )
            ).first()
            
            if existing:
                return jsonify({
                    'success': False,
                    'error': f'L\'utente {system_user.full_name} è già associato a {existing.full_name}'
                }), 400
            
            respond_io_user.user_id = system_user_id
            message = f'Associato {respond_io_user.full_name} a {system_user.full_name}'
        else:
            # Rimuovi associazione
            respond_io_user.user_id = None
            message = f'Rimossa associazione per {respond_io_user.full_name}'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore associazione utente: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/calendar/stats')
@login_required
def get_calendar_stats():
    """API per ottenere statistiche del calendario in tempo reale"""
    
    # Ottieni utenti in turno ora con stato timbrature
    from .assignment_service import ContactAssignmentService
    from corposostenibile.models import RespondIOWorkTimestamp
    
    service = ContactAssignmentService()
    users_on_duty = service.get_users_on_duty()
    
    # Aggiungi stato timbratura per ogni utente
    for user in users_on_duty:
        # Trova l'utente del sistema associato
        respond_io_user = RespondIOUser.query.get(user['id'])
        if respond_io_user and respond_io_user.user_id:
            user['timestamp_status'] = RespondIOWorkTimestamp.get_current_status(respond_io_user.user_id)
            
            # Ottieni ultima timbratura
            last_timestamp = RespondIOWorkTimestamp.query.filter(
                and_(
                    RespondIOWorkTimestamp.user_id == respond_io_user.user_id,
                    func.date(RespondIOWorkTimestamp.timestamp) == date.today()
                )
            ).order_by(RespondIOWorkTimestamp.timestamp.desc()).first()
            
            if last_timestamp:
                user['last_timestamp_time'] = last_timestamp.timestamp.strftime('%H:%M')
                user['last_timestamp_type'] = last_timestamp.timestamp_type
            else:
                user['last_timestamp_time'] = None
                user['last_timestamp_type'] = None
        else:
            user['timestamp_status'] = 'no_profile'
            user['last_timestamp_time'] = None
            user['last_timestamp_type'] = None
    
    # Filtra utenti che sono attualmente in pausa
    now = datetime.now(pytz.timezone('Europe/Rome'))
    active_users = []
    
    for user in users_on_duty:
        # Controlla se l'utente ha un evento attivo ora
        active_event = RespondIOCalendarEvent.query.filter(
            and_(
                RespondIOCalendarEvent.user_id == user['id'],
                RespondIOCalendarEvent.start_datetime <= now,
                RespondIOCalendarEvent.end_datetime >= now,
                RespondIOCalendarEvent.event_type == 'work',
                RespondIOCalendarEvent.status != 'cancelled'
            )
        ).first()
        
        if active_event:
            # Controlla se è in pausa ora
            is_on_break = False
            for break_item in active_event.breaks:
                if break_item.start_time <= now <= break_item.end_time:
                    is_on_break = True
                    break
            
            if not is_on_break:
                active_users.append(user)
        else:
            # Se non ha evento ma è in turno secondo lo schedule, lo includiamo
            active_users.append(user)
    
    # Calcola ore totali settimana corrente
    today = datetime.now(pytz.timezone('Europe/Rome'))
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    # Query per eventi della settimana
    week_events = RespondIOCalendarEvent.query.filter(
        and_(
            RespondIOCalendarEvent.start_datetime >= week_start,
            RespondIOCalendarEvent.start_datetime <= week_end,
            RespondIOCalendarEvent.event_type == 'work',
            RespondIOCalendarEvent.status != 'cancelled'
        )
    ).all()
    
    # Calcola ore totali (sottraendo le pause)
    total_hours = 0
    for event in week_events:
        duration = (event.end_datetime - event.start_datetime).total_seconds() / 3600
        
        # Sottrai durata delle pause
        total_break_hours = 0
        for break_item in event.breaks:
            break_duration = (break_item.end_time - break_item.start_time).total_seconds() / 3600
            total_break_hours += break_duration
        
        duration -= total_break_hours
        total_hours += duration
    
    # Aggiungi ore dai turni settimanali
    weekly_schedules = RespondIOUserWorkSchedule.query.filter_by(is_active=True).all()
    for schedule in weekly_schedules:
        if schedule.start_time and schedule.end_time:
            # Calcola ore per questo turno
            start_minutes = schedule.start_time.hour * 60 + schedule.start_time.minute
            end_minutes = schedule.end_time.hour * 60 + schedule.end_time.minute
            duration_hours = (end_minutes - start_minutes) / 60
            total_hours += duration_hours
    
    # Trova prossimi turni (TUTTI quelli che iniziano alla stessa ora)
    next_shifts = []
    
    # Prima trova il prossimo orario di inizio
    next_event = RespondIOCalendarEvent.query.filter(
        and_(
            RespondIOCalendarEvent.start_datetime > today,
            RespondIOCalendarEvent.event_type == 'work',
            RespondIOCalendarEvent.status != 'cancelled'
        )
    ).order_by(RespondIOCalendarEvent.start_datetime).first()
    
    if next_event:
        # Ora trova TUTTI gli eventi che iniziano a quell'ora
        next_start_time = next_event.start_datetime
        all_upcoming_events = RespondIOCalendarEvent.query.filter(
            and_(
                RespondIOCalendarEvent.start_datetime == next_start_time,
                RespondIOCalendarEvent.event_type == 'work',
                RespondIOCalendarEvent.status != 'cancelled'
            )
        ).all()
        
        for event in all_upcoming_events:
            next_shifts.append({
                'user': event.user.full_name if event.user else 'N/A',
                'time': event.start_datetime.strftime('%H:%M')
            })
    else:
        # Cerca nei turni settimanali
        tomorrow = today + timedelta(days=1)
        tomorrow_dow = tomorrow.weekday()
        
        # Prima trova il prossimo orario dai turni settimanali
        next_schedule = RespondIOUserWorkSchedule.query.filter(
            and_(
                RespondIOUserWorkSchedule.day_of_week >= tomorrow_dow,
                RespondIOUserWorkSchedule.is_active == True
            )
        ).order_by(
            RespondIOUserWorkSchedule.day_of_week,
            RespondIOUserWorkSchedule.start_time
        ).first()
        
        if next_schedule:
            # Trova TUTTI i turni che iniziano alla stessa ora nello stesso giorno
            same_time_schedules = RespondIOUserWorkSchedule.query.filter(
                and_(
                    RespondIOUserWorkSchedule.day_of_week == next_schedule.day_of_week,
                    RespondIOUserWorkSchedule.start_time == next_schedule.start_time,
                    RespondIOUserWorkSchedule.is_active == True
                )
            ).all()
            
            for schedule in same_time_schedules:
                next_shifts.append({
                    'user': schedule.user.full_name if schedule.user else 'N/A',
                    'time': schedule.start_time.strftime('%H:%M') if schedule.start_time else '09:00'
                })
    
    # Formatta i prossimi turni
    if next_shifts:
        # Se c'è solo un turno, mostra come prima
        if len(next_shifts) == 1:
            next_shift_text = f"{next_shifts[0]['user']} - {next_shifts[0]['time']}"
        else:
            # Se ci sono più turni alla stessa ora, mostrali tutti
            time = next_shifts[0]['time']  # Tutti hanno la stessa ora
            users = [shift['user'] for shift in next_shifts]
            next_shift_text = f"{', '.join(users)} - {time}"
    else:
        next_shift_text = 'Nessuno programmato'
    
    return jsonify({
        'totalHoursWeek': round(total_hours, 1),
        'activeShifts': len(active_users),  # Usa active_users che esclude chi è in pausa
        'usersOnDuty': [
            {
                'id': u['id'],
                'name': u['full_name'],
                'email': u['email']
            }
            for u in active_users  # Usa active_users che esclude chi è in pausa
        ],
        'nextShift': next_shift_text,
        'nextShifts': next_shifts  # Aggiungi anche array completo per futuri usi
    })
