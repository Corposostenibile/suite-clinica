"""
Task Celery per pre-assegnazione contatti prima del primo turno.
Assegna i contatti 30 minuti prima che gli operatori del primo turno arrivino.
"""

from datetime import datetime, timedelta, time
from celery import shared_task
from flask import current_app
from sqlalchemy import and_, or_, func
import pytz
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def pre_assign_first_shift_contacts(self):
    """
    Task schedulato per assegnare i contatti 30 minuti prima del primo turno.
    Eseguito ogni giorno alle ore prestabilite (es: 7:30 se il primo turno è alle 8:00).
    """
    try:
        from flask import Flask
        from corposostenibile.config import Config
        from corposostenibile.extensions import db
        
        app = Flask(__name__)
        app.config.from_object(Config.get('production'))
        db.init_app(app)
        
        with app.app_context():
            from corposostenibile.models import (
                User,
                RespondIOUser,
                RespondIOCalendarEvent,
                RespondIOUserWorkSchedule
            )
            from corposostenibile.blueprints.respond_io.timestamp_assignment_service import TimestampAssignmentService
            
            # Inizializza il servizio
            from corposostenibile.blueprints.respond_io.client import RespondIOClient
            client = RespondIOClient(app.config)
            service = TimestampAssignmentService(client)
            
            tz = pytz.timezone('Europe/Rome')
            now = datetime.now(tz)
            
            # Trova il prossimo inizio turno (entro i prossimi 45 minuti)
            check_start = now
            check_end = now + timedelta(minutes=45)
            
            logger.info(f"Checking for first shift between {check_start} and {check_end}")
            
            # Cerca utenti che inizieranno il turno nel range temporale
            upcoming_users = []
            
            # 1. Check eventi calendario
            calendar_events = RespondIOCalendarEvent.query.filter(
                and_(
                    RespondIOCalendarEvent.start_datetime >= check_start,
                    RespondIOCalendarEvent.start_datetime <= check_end,
                    RespondIOCalendarEvent.event_type == 'work',
                    RespondIOCalendarEvent.status != 'cancelled'
                )
            ).all()
            
            for event in calendar_events:
                user = event.user
                if user and user.is_active:
                    upcoming_users.append({
                        'user': user,
                        'start_time': event.start_datetime,
                        'source': 'calendar'
                    })
            
            # 2. Check schedule settimanale ricorrente
            current_day = now.weekday()
            current_time = now.time()
            check_time = (now + timedelta(minutes=30)).time()
            check_time_end = (now + timedelta(minutes=45)).time()
            
            weekly_schedules = RespondIOUserWorkSchedule.query.filter(
                and_(
                    RespondIOUserWorkSchedule.day_of_week == current_day,
                    RespondIOUserWorkSchedule.is_active == True,
                    RespondIOUserWorkSchedule.start_time >= check_time,
                    RespondIOUserWorkSchedule.start_time <= check_time_end
                )
            ).all()
            
            for schedule in weekly_schedules:
                user = schedule.user
                if user and user.is_active:
                    # Verifica che non sia già negli eventi calendario (evita duplicati)
                    if not any(u['user'].id == user.id for u in upcoming_users):
                        upcoming_users.append({
                            'user': user,
                            'start_time': datetime.combine(now.date(), schedule.start_time, tzinfo=tz),
                            'source': 'weekly_schedule'
                        })
            
            if not upcoming_users:
                logger.info("No users starting shift in the next 30-45 minutes")
                return {'status': 'no_users', 'message': 'No upcoming shifts'}
            
            # Verifica se è il PRIMO turno della giornata
            # (nessuno attualmente working)
            from corposostenibile.models import RespondIOWorkTimestamp
            
            # Check ultimo stato di ogni utente
            subquery = db.session.query(
                RespondIOWorkTimestamp.user_id,
                func.max(RespondIOWorkTimestamp.timestamp).label('last_timestamp')
            ).group_by(RespondIOWorkTimestamp.user_id).subquery()
            
            current_working = db.session.query(
                RespondIOWorkTimestamp
            ).join(
                subquery,
                and_(
                    RespondIOWorkTimestamp.user_id == subquery.c.user_id,
                    RespondIOWorkTimestamp.timestamp == subquery.c.last_timestamp
                )
            ).filter(
                RespondIOWorkTimestamp.current_status == 'working'
            ).count()
            
            if current_working > 0:
                logger.info(f"Not first shift - {current_working} users already working")
                return {'status': 'not_first_shift', 'working_users': current_working}
            
            logger.info(f"First shift detected! Pre-assigning contacts to {len(upcoming_users)} users")
            
            # Ottieni tutti i contatti con tag "in_attesa"
            contacts = service._fetch_contacts_with_waiting_tag()
            
            if not contacts:
                logger.info("No contacts to pre-assign")
                return {'status': 'no_contacts', 'users_count': len(upcoming_users)}
            
            # Prepara lista utenti per distribuzione
            users_for_distribution = []
            for u in upcoming_users:
                user = u['user']
                # RespondIOUser ha i campi direttamente, non tramite profile
                if hasattr(user, 'respond_io_id'):
                    users_for_distribution.append({
                        'id': user.id,
                        'email': user.email,
                        'full_name': user.full_name if hasattr(user, 'full_name') else f"{user.first_name} {user.last_name}",
                        'respond_io_id': user.respond_io_id
                    })
            
            if not users_for_distribution:
                logger.error("No users with Respond.io profiles for pre-assignment")
                return {'status': 'error', 'message': 'No valid users'}
            
            # Distribuisci i contatti
            assignments = service._distribute_contacts_equally(contacts, users_for_distribution)
            
            # Esegui le assegnazioni
            # Crea un utente di sistema per il log
            system_user = User.query.filter_by(email='system@corposostenibile.com').first()
            if not system_user:
                # Usa il primo admin come fallback
                system_user = User.query.filter_by(is_admin=True).first()
            
            service._execute_bulk_assignments(
                assignments,
                assignment_type='pre_shift_assignment',
                triggered_by=system_user or upcoming_users[0]['user']
            )
            
            logger.info(f"Pre-assigned {len(contacts)} contacts to {len(users_for_distribution)} users")
            
            # Registra che abbiamo fatto la pre-assegnazione per oggi
            # per evitare di rifarla se il task viene rieseguito
            _mark_pre_assignment_done(now.date())
            
            return {
                'status': 'success',
                'contacts_assigned': len(contacts),
                'users_count': len(users_for_distribution),
                'timestamp': now.isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error in pre-assignment task: {str(e)}", exc_info=True)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=300)  # Retry dopo 5 minuti
        return {'status': 'error', 'error': str(e)}


@shared_task
def schedule_daily_pre_assignments():
    """
    Task che gira ogni giorno a mezzanotte per schedulare le pre-assegnazioni.
    Analizza gli orari del giorno e schedula i task 30 minuti prima del primo turno.
    """
    try:
        from flask import Flask
        from corposostenibile.config import Config
        from corposostenibile.extensions import db
        
        app = Flask(__name__)
        app.config.from_object(Config.get('production'))
        db.init_app(app)
        
        with app.app_context():
            from corposostenibile.models import (
                RespondIOCalendarEvent,
                RespondIOUserWorkSchedule
            )
            
            tz = pytz.timezone('Europe/Rome')
            today = datetime.now(tz).date()
            tomorrow = today + timedelta(days=1)
            current_day = today.weekday()
            
            # Trova il primo orario di inizio turno per oggi
            earliest_start = None
            
            # Check eventi calendario
            first_event = RespondIOCalendarEvent.query.filter(
                and_(
                    func.date(RespondIOCalendarEvent.start_datetime) == today,
                    RespondIOCalendarEvent.event_type == 'work',
                    RespondIOCalendarEvent.status != 'cancelled'
                )
            ).order_by(RespondIOCalendarEvent.start_datetime).first()
            
            if first_event:
                earliest_start = first_event.start_datetime
            
            # Check schedule settimanale
            first_schedule = RespondIOUserWorkSchedule.query.filter(
                and_(
                    RespondIOUserWorkSchedule.day_of_week == current_day,
                    RespondIOUserWorkSchedule.is_active == True
                )
            ).order_by(RespondIOUserWorkSchedule.start_time).first()
            
            if first_schedule:
                schedule_start = datetime.combine(today, first_schedule.start_time, tzinfo=tz)
                if not earliest_start or schedule_start < earliest_start:
                    earliest_start = schedule_start
            
            if not earliest_start:
                logger.info(f"No shifts scheduled for {today}")
                return {'status': 'no_shifts', 'date': today.isoformat()}
            
            # Schedula pre-assegnazione 30 minuti prima
            pre_assign_time = earliest_start - timedelta(minutes=30)
            
            # Se è già passato, non schedulare
            if pre_assign_time <= datetime.now(tz):
                logger.info(f"Pre-assignment time already passed for {today}")
                return {'status': 'already_passed', 'date': today.isoformat()}
            
            # Schedula il task
            pre_assign_first_shift_contacts.apply_async(eta=pre_assign_time)
            
            logger.info(f"Scheduled pre-assignment for {pre_assign_time.isoformat()}")
            
            return {
                'status': 'scheduled',
                'first_shift': earliest_start.isoformat(),
                'pre_assign_time': pre_assign_time.isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error scheduling daily pre-assignments: {str(e)}")
        return {'status': 'error', 'error': str(e)}


def _mark_pre_assignment_done(date):
    """
    Marca che la pre-assegnazione è stata fatta per una data specifica.
    Usa una semplice cache in memoria o database per tracking.
    """
    # Per ora usiamo un file di log semplice
    # In produzione, meglio usare Redis o una tabella dedicata
    import os
    
    log_dir = '/home/devops/corposostenibile-suite/logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, 'pre_assignments.log')
    
    with open(log_file, 'a') as f:
        f.write(f"{date.isoformat()},{datetime.now().isoformat()}\n")


def _check_pre_assignment_done(date):
    """
    Verifica se la pre-assegnazione è già stata fatta per una data.
    """
    import os
    
    log_file = '/home/devops/corposostenibile-suite/logs/pre_assignments.log'
    
    if not os.path.exists(log_file):
        return False
    
    with open(log_file, 'r') as f:
        for line in f:
            if line.startswith(f"{date.isoformat()},"):
                return True
    
    return False