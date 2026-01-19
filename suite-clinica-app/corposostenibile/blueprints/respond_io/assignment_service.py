"""
Servizio per gestione assegnazioni automatiche contatti Respond.io
"""

from datetime import datetime, time
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import pytz
from flask import current_app
from sqlalchemy import and_, or_
from corposostenibile.extensions import db
from corposostenibile.models import (
    User,
    RespondIOUser,
    RespondIOUserWorkSchedule,
    RespondIOAssignmentLog
)


class ContactAssignmentService:
    """
    Servizio per gestire l'assegnazione automatica dei contatti
    basata sugli orari di lavoro degli utenti.
    """
    
    # Lifecycle target per assegnazione automatica (AGGIORNATI)
    TARGET_LIFECYCLES = [
        'Nuova Lead',
        'Contrassegnato', 
        'In Target',
        'Link Da Inviare',
        'Link Inviato',
        'Prenotato'
    ]
    
    def __init__(self, client=None):
        """
        Inizializza il servizio.
        
        Args:
            client: RespondIOClient instance (verrà preso da app se None)
        """
        self.client = client
        if not self.client and current_app:
            self.client = current_app.respond_io_client
    
    def get_users_on_duty(self, check_time: Optional[datetime] = None) -> List[Dict]:
        """
        Ottiene la lista degli utenti Respond.io attualmente in turno.
        Controlla sia gli orari settimanali che gli eventi del calendario.
        
        Args:
            check_time: Datetime da verificare (default: now)
            
        Returns:
            List[Dict]: Lista utenti con i loro dettagli
        """
        if check_time is None:
            # Usa timezone italiano di default
            tz = pytz.timezone('Europe/Rome')
            check_time = datetime.now(tz)
        
        current_day = check_time.weekday()
        current_time = check_time.time()
        
        users_on_duty = []
        user_ids_added = set()  # Per evitare duplicati
        
        # 1. Controlla RespondIOCalendarEvent (eventi salvati nel calendario)
        from corposostenibile.models import RespondIOCalendarEvent
        calendar_events = RespondIOCalendarEvent.query.filter(
            and_(
                RespondIOCalendarEvent.start_datetime <= check_time,
                RespondIOCalendarEvent.end_datetime >= check_time,
                RespondIOCalendarEvent.event_type == 'work',
                RespondIOCalendarEvent.status != 'cancelled'
            )
        ).all()
        
        for event in calendar_events:
            user = event.user
            if user and user.id not in user_ids_added and user.is_active:
                # Verifica che non sia in pausa
                is_on_break = False
                for break_item in event.breaks:
                    if break_item.start_time <= check_time <= break_item.end_time:
                        is_on_break = True
                        break
                
                if not is_on_break:
                    users_on_duty.append({
                        'id': user.id,
                        'email': user.email,
                        'full_name': user.full_name,
                        'source': 'calendar_event'
                    })
                    user_ids_added.add(user.id)
        
        # 2. Controlla RespondIOUserWorkSchedule (orari settimanali ricorrenti)
        schedules = RespondIOUserWorkSchedule.query.filter(
            and_(
                RespondIOUserWorkSchedule.day_of_week == current_day,
                RespondIOUserWorkSchedule.is_active == True,
                RespondIOUserWorkSchedule.start_time <= current_time,
                RespondIOUserWorkSchedule.end_time >= current_time
            )
        ).all()
        
        for schedule in schedules:
            user = schedule.user
            
            # Verifica che l'utente sia attivo e non già aggiunto
            if user and user.id not in user_ids_added and user.is_active:
                users_on_duty.append({
                    'id': user.id,
                    'respond_io_id': user.respond_io_id,
                    'email': user.email,
                    'full_name': user.full_name,
                    'source': 'weekly_schedule'
                })
                user_ids_added.add(user.id)
        
        current_app.logger.info(f"Found {len(users_on_duty)} Respond.io users on duty at {check_time}")
        return users_on_duty
    
    def fetch_contacts_to_assign(self, filter_mode: str = 'all') -> List[Dict]:
        """
        Recupera i contatti da assegnare in base alla modalità di filtro.
        
        Args:
            filter_mode: Modalità di filtro
                - 'all': Tutti i contatti aperti nei lifecycle target
                - 'waiting': Solo contatti con tag "in_attesa" 
                - 'unassigned_waiting': Solo non assegnati con tag "in_attesa"
        
        Returns:
            List[Dict]: Lista contatti da assegnare
        """
        current_app.logger.info(f"Fetching contacts with mode: {filter_mode}, lifecycles: {self.TARGET_LIFECYCLES}")
        
        # Prepara parametri base
        params = {
            'lifecycles': self.TARGET_LIFECYCLES,
            'status': 'open'  # SEMPRE solo contatti aperti
        }
        
        # Applica filtri in base alla modalità
        if filter_mode in ['waiting', 'unassigned_waiting']:
            # Filtra solo contatti con tag "in_attesa"
            params['tags'] = ['in_attesa']
            current_app.logger.info("Filtering for contacts with 'in_attesa' tag")
        
        if filter_mode == 'unassigned_waiting':
            # Filtra anche per non assegnati
            params['assignee'] = None
            current_app.logger.info("Filtering for unassigned contacts only")
        
        # Recupera contatti con i filtri applicati
        contacts = self.client.list_contacts_filtered(**params)
        
        current_app.logger.info(
            f"Found {len(contacts)} contacts to assign with filter_mode='{filter_mode}'"
        )
        return contacts
    
    def divide_contacts_equally(self, 
                               contacts: List[Dict], 
                               users: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Divide i contatti equamente tra gli utenti.
        
        Args:
            contacts: Lista contatti da assegnare
            users: Lista utenti disponibili
            
        Returns:
            Dict: Mapping user_email -> lista contatti
        """
        if not users:
            raise ValueError("Nessun utente disponibile per l'assegnazione")
        
        assignments = defaultdict(list)
        
        # Calcola quanti contatti per utente
        contacts_per_user = len(contacts) // len(users)
        remainder = len(contacts) % len(users)
        
        current_index = 0
        for i, user in enumerate(users):
            # Alcuni utenti ricevono un contatto in più per gestire il resto
            user_count = contacts_per_user + (1 if i < remainder else 0)
            
            # Assegna i contatti a questo utente
            user_contacts = contacts[current_index:current_index + user_count]
            assignments[user['email']] = user_contacts
            
            current_index += user_count
            
            current_app.logger.info(
                f"User {user['email']} will receive {len(user_contacts)} contacts"
            )
        
        return dict(assignments)
    
    def execute_assignments(self, 
                          assignments: Dict[str, List[Dict]],
                          executed_by: Optional[User] = None) -> RespondIOAssignmentLog:
        """
        Esegue le assegnazioni effettive tramite API.
        
        Args:
            assignments: Mapping user_email -> lista contatti
            executed_by: Utente che ha eseguito l'operazione
            
        Returns:
            RespondIOAssignmentLog: Log dell'operazione
        """
        # Crea log entry
        log = RespondIOAssignmentLog(
            executed_by_id=executed_by.id if executed_by else None,
            assignment_type='manual',
            started_at=datetime.utcnow(),
            status='in_progress',
            lifecycles_processed=self.TARGET_LIFECYCLES,
            details={
                'filter_status': 'open',
                'filter_lifecycles': self.TARGET_LIFECYCLES
            }
        )
        db.session.add(log)
        db.session.commit()
        
        # Prepara lista di assegnazioni
        all_assignments = []
        user_counts = []
        
        for user_email, contacts in assignments.items():
            user_counts.append({
                'email': user_email,
                'count': len(contacts)
            })
            
            for contact in contacts:
                all_assignments.append((
                    str(contact['id']),  # contact_id
                    user_email            # assignee
                ))
        
        log.total_contacts = len(all_assignments)
        log.assigned_to_users = user_counts
        
        # Esegui assegnazioni in batch
        try:
            current_app.logger.info(f"Starting bulk assignment of {len(all_assignments)} contacts")
            
            results = self.client.bulk_assign_conversations(
                all_assignments,
                batch_size=10  # Processa 10 alla volta
            )
            
            # Aggiorna log con risultati
            log.contacts_assigned = len(results['successful'])
            log.contacts_failed = len(results['failed'])
            log.contacts_skipped = 0
            log.status = 'completed' if results['success_rate'] == 100 else 'partial'
            log.completed_at = datetime.utcnow()
            
            # Salva dettagli errori se presenti
            if results['failed']:
                log.error_message = f"Failed to assign {len(results['failed'])} contacts"
                log.details['failed_assignments'] = results['failed'][:10]  # Primi 10 errori
            
            current_app.logger.info(
                f"Assignment completed: {log.contacts_assigned}/{log.total_contacts} successful"
            )
            
        except Exception as e:
            log.status = 'failed'
            log.error_message = str(e)
            log.completed_at = datetime.utcnow()
            current_app.logger.error(f"Assignment failed: {str(e)}")
            raise
        
        finally:
            db.session.commit()
        
        return log
    
    def auto_assign_all_contacts(self, 
                                executed_by: Optional[User] = None,
                                filter_mode: str = 'all') -> Dict:
        """
        Processo completo di assegnazione automatica.
        
        Args:
            executed_by: Utente che ha eseguito l'operazione
            filter_mode: Modalità di filtro ('all', 'waiting', 'unassigned_waiting')
            
        Returns:
            Dict: Risultato dell'operazione con statistiche
        """
        result = {
            'success': False,
            'message': '',
            'stats': {}
        }
        
        try:
            # 1. Ottieni utenti in turno
            users_on_duty = self.get_users_on_duty()
            
            if not users_on_duty:
                result['message'] = 'Nessun utente in turno al momento'
                current_app.logger.warning(result['message'])
                return result
            
            # 2. Ottieni i contatti da riassegnare in base al filter_mode
            contacts = self.fetch_contacts_to_assign(filter_mode)
            
            if not contacts:
                result['message'] = 'Nessun contatto da assegnare nei lifecycle target'
                result['success'] = True
                current_app.logger.info(result['message'])
                return result
            
            # 3. Dividi equamente
            assignments = self.divide_contacts_equally(contacts, users_on_duty)
            
            # 4. Esegui assegnazioni
            log = self.execute_assignments(assignments, executed_by)
            
            # 5. Prepara risultato
            result['success'] = log.status in ['completed', 'partial']
            result['message'] = f"Assegnati {log.contacts_assigned} contatti su {log.total_contacts}"
            result['stats'] = {
                'total_contacts': log.total_contacts,
                'assigned': log.contacts_assigned,
                'failed': log.contacts_failed,
                'users_involved': len(users_on_duty),
                'duration_seconds': log.duration_seconds,
                'log_id': log.id
            }
            
            # Dettaglio assegnazioni per utente
            result['assignments_per_user'] = log.assigned_to_users
            
        except Exception as e:
            result['message'] = f"Errore durante l'assegnazione: {str(e)}"
            current_app.logger.error(result['message'], exc_info=True)
        
        return result
    
    def get_assignment_preview(self, filter_mode: str = 'all') -> Dict:
        """
        Ottiene un'anteprima dell'assegnazione senza eseguirla.
        
        Args:
            filter_mode: Modalità di filtro ('all', 'waiting', 'unassigned_waiting')
        
        Returns:
            Dict: Preview con statistiche e distribuzione
        """
        preview = {
            'users_on_duty': [],
            'contacts_to_assign': 0,
            'already_assigned': 0,
            'distribution': {},
            'can_proceed': False
        }
        
        try:
            # Ottieni utenti in turno
            users_on_duty = self.get_users_on_duty()
            preview['users_on_duty'] = [
                {
                    'id': u['id'],
                    'name': u['full_name'],
                    'email': u['email']
                }
                for u in users_on_duty
            ]
            
            if not users_on_duty:
                preview['message'] = 'Nessun utente in turno'
                return preview
            
            # Conta i contatti da riassegnare in base al filter_mode
            contacts = self.fetch_contacts_to_assign(filter_mode)
            preview['contacts_to_assign'] = len(contacts)
            preview['filter_mode'] = filter_mode  # Aggiungi info sul filtro applicato
            
            # Conta quanti già hanno un assignee (per info)
            preview['already_assigned'] = sum(1 for c in contacts if c.get('assignee'))
            
            if preview['contacts_to_assign'] == 0:
                preview['message'] = 'Nessun contatto da assegnare'
                preview['can_proceed'] = False
                return preview
            
            # Calcola distribuzione
            contacts_per_user = preview['contacts_to_assign'] // len(users_on_duty)
            remainder = preview['contacts_to_assign'] % len(users_on_duty)
            
            for i, user in enumerate(users_on_duty):
                user_count = contacts_per_user + (1 if i < remainder else 0)
                preview['distribution'][user['email']] = {
                    'name': user['full_name'],
                    'count': user_count
                }
            
            preview['can_proceed'] = True
            preview['message'] = f"Pronti per assegnare {preview['contacts_to_assign']} contatti a {len(users_on_duty)} utenti"
            
        except Exception as e:
            preview['message'] = f"Errore nel calcolo preview: {str(e)}"
            current_app.logger.error(preview['message'], exc_info=True)
        
        return preview
    
    def get_recent_logs(self, limit: int = 10) -> List[RespondIOAssignmentLog]:
        """
        Ottiene i log recenti delle assegnazioni.
        
        Args:
            limit: Numero massimo di log da ritornare
            
        Returns:
            List[RespondIOAssignmentLog]: Lista dei log recenti
        """
        return RespondIOAssignmentLog.query.order_by(
            RespondIOAssignmentLog.started_at.desc()
        ).limit(limit).all()
    
    def sync_workspace_users(self) -> Dict:
        """
        Sincronizza gli utenti del workspace Respond.io con il database.
        
        Returns:
            Dict: Risultato della sincronizzazione
        """
        result = {
            'created': 0,
            'updated': 0,
            'errors': [],
            'users': []
        }
        
        try:
            # Ottieni utenti dal workspace Respond.io
            workspace_users = self.client.fetch_workspace_users()
            
            for ws_user in workspace_users:
                # Cerca utente Respond.io esistente
                respond_io_user = RespondIOUser.query.filter_by(
                    respond_io_id=ws_user['id']
                ).first()
                
                if respond_io_user:
                    # Aggiorna dati esistenti
                    respond_io_user.email = ws_user['email']
                    respond_io_user.first_name = ws_user['firstName']
                    respond_io_user.last_name = ws_user['lastName']
                    respond_io_user.role = ws_user.get('role', 'agent')
                    respond_io_user.team_id = ws_user.get('team', {}).get('id') if ws_user.get('team') else None
                    respond_io_user.team_name = ws_user.get('team', {}).get('name') if ws_user.get('team') else None
                    respond_io_user.restrictions = ws_user.get('restrictions', [])
                    respond_io_user.last_synced = datetime.utcnow()
                    result['updated'] += 1
                else:
                    # Crea nuovo utente Respond.io
                    respond_io_user = RespondIOUser(
                        respond_io_id=ws_user['id'],
                        email=ws_user['email'],
                        first_name=ws_user['firstName'],
                        last_name=ws_user['lastName'],
                        role=ws_user.get('role', 'agent'),
                        team_id=ws_user.get('team', {}).get('id') if ws_user.get('team') else None,
                        team_name=ws_user.get('team', {}).get('name') if ws_user.get('team') else None,
                        restrictions=ws_user.get('restrictions', []),
                        is_active=True
                    )
                    db.session.add(respond_io_user)
                    result['created'] += 1
                
                result['users'].append({
                    'id': ws_user['id'],
                    'email': ws_user['email'],
                    'name': f"{ws_user['firstName']} {ws_user['lastName']}",
                    'role': ws_user.get('role', 'agent')
                })
            
            db.session.commit()
            current_app.logger.info(f"Synced {len(workspace_users)} users from Respond.io")
            
        except Exception as e:
            db.session.rollback()
            result['errors'].append(f"Errore sincronizzazione: {str(e)}")
            current_app.logger.error(f"Error syncing workspace users: {str(e)}", exc_info=True)
        
        return result