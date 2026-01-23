"""
Servizio di assegnazione automatica basato su eventi di timbratura.
Gestisce la distribuzione dei contatti in base agli stati di lavoro degli utenti.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import threading
import time
from flask import current_app
from sqlalchemy import and_, or_, func
from corposostenibile.extensions import db
from corposostenibile.models import (
    User,
    RespondIOUser,
    RespondIOWorkTimestamp,
    RespondIOAssignmentLog,
    RespondIOContactChannel
)


class TimestampAssignmentService:
    """
    Servizio per gestire l'assegnazione automatica dei contatti
    basata sugli eventi di timbratura degli utenti.
    """
    
    # Lifecycle target aggiornati
    TARGET_LIFECYCLES = [
        'Nuova Lead',
        'Contrassegnato',
        'In Target',
        'Link Da Inviare',
        'Link Inviato',
        'Prenotato'
    ]
    
    # Lock per gestione concorrenza
    _assignment_lock = threading.Lock()
    _current_assignment_thread = None
    
    def __init__(self, client=None):
        """
        Inizializza il servizio.
        
        Args:
            client: RespondIOClient instance
        """
        self.client = client
        if not self.client and current_app:
            self.client = current_app.respond_io_client
    
    def handle_timestamp_event(self, user: User, timestamp_type: str):
        """
        Gestisce un evento di timbratura e triggera le assegnazioni necessarie.
        
        Args:
            user: Utente che ha timbrato
            timestamp_type: Tipo di timbratura (start, pause_start, pause_end, end)
        """
        from flask import current_app
        current_app.logger.info(f"Handling timestamp event: {timestamp_type} for user {user.email}")
        
        # NUOVO: Se è un START, verifica se è il primo turno della giornata
        if timestamp_type == 'start':
            if self._is_first_shift_user(user):
                current_app.logger.info(f"User {user.email} is part of first shift - contacts already pre-assigned, skipping")
                return  # Non fare nulla, i contatti sono già stati assegnati
        
        # Interrompi eventuale assegnazione in corso
        if self._current_assignment_thread and self._current_assignment_thread.is_alive():
            current_app.logger.warning("Interrupting current assignment cycle for new timestamp event")
            # Il lock impedirà l'avvio finché non termina
        
        # Avvia nuovo thread per gestire l'assegnazione
        # Passa l'app context e l'ID utente (non l'oggetto che perde contesto)
        app = current_app._get_current_object()
        user_id = user.id  # Cattura solo l'ID
        user_email = user.email  # Per logging
        self._current_assignment_thread = threading.Thread(
            target=self._process_assignment_with_context,
            args=(app, user_id, user_email, timestamp_type)
        )
        self._current_assignment_thread.start()
    
    def _process_assignment_with_context(self, app, user_id: int, user_email: str, timestamp_type: str):
        """Wrapper per gestire il contesto Flask nel thread."""
        with app.app_context():
            # Recupera l'utente nel contesto del thread
            from corposostenibile.models import User
            user = User.query.get(user_id)
            if not user:
                app.logger.error(f"User {user_id} ({user_email}) not found in thread context!")
                return
            self._process_assignment(user, timestamp_type)
    
    def _process_assignment(self, user: User, timestamp_type: str):
        """
        Processa l'assegnazione in base al tipo di timbratura.
        Thread-safe con lock. Il contesto Flask viene già gestito dal wrapper.
        """
        with self._assignment_lock:
            try:
                current_app.logger.info(f"Processing assignment for {timestamp_type} event from user {user.email}")
                
                if timestamp_type == 'start':
                    self._handle_start_shift(user)
                elif timestamp_type == 'pause_start':
                    self._handle_pause_start(user)
                elif timestamp_type == 'pause_end':
                    self._handle_pause_end(user)
                elif timestamp_type == 'end':
                    self._handle_end_shift(user)
                    
                current_app.logger.info(f"Assignment processing completed for {timestamp_type}")
                
            except Exception as e:
                current_app.logger.error(f"Error in assignment processing: {e}", exc_info=True)
                # Retry logic
                time.sleep(5)
                try:
                    current_app.logger.info("Retrying assignment after error...")
                    if timestamp_type == 'start':
                        self._handle_start_shift(user)
                    elif timestamp_type == 'pause_start':
                        self._handle_pause_start(user)
                    elif timestamp_type == 'pause_end':
                        self._handle_pause_end(user)
                    elif timestamp_type == 'end':
                        self._handle_end_shift(user)
                except Exception as retry_error:
                    current_app.logger.error(f"Retry failed: {retry_error}", exc_info=True)
    
    def _handle_start_shift(self, user: User):
        """
        NUOVA LOGICA: Quando un utente NON del primo turno inizia:
        ridistribuisci TUTTI i contatti tra TUTTI gli utenti attivi per bilanciare.
        
        Args:
            user: Utente che ha iniziato il turno (NON primo turno)
        """
        current_app.logger.info(f"User {user.email} started shift (not first shift) - redistributing for balance")
        
        # Ottieni tutti gli utenti attivi (working, non in pausa) INCLUSO il nuovo
        active_users = self._get_active_users()
        
        if not active_users:
            current_app.logger.error("No active users found after shift start")
            return
        
        if len(active_users) == 1:
            # Se è l'unico utente, assegna tutti a lui
            current_app.logger.info(f"User {user.email} is the only active user - assigning all contacts")
        else:
            # Più utenti: redistribuisci per bilanciare
            current_app.logger.info(f"Redistributing contacts among {len(active_users)} active users for balance")
        
        # Ottieni TUTTI i contatti con tag "in_attesa"
        contacts = self._fetch_contacts_with_waiting_tag()
        
        if not contacts:
            current_app.logger.info("No contacts with 'in_attesa' tag to assign")
            return
        
        # Distribuisci equamente tra tutti gli attivi (incluso il nuovo)
        assignments = self._distribute_contacts_equally(contacts, active_users)
        
        # Esegui le assegnazioni
        self._execute_bulk_assignments(
            assignments,
            assignment_type='shift_start_rebalance',  # Cambiato per chiarezza
            triggered_by=user
        )
    
    def _handle_pause_start(self, user: User):
        """
        Quando un utente va in pausa: prendi i suoi contatti e
        ridistribuiscili agli altri utenti attivi.
        Se non ci sono altri utenti attivi, dissocia tutti i contatti.
        """
        current_app.logger.info(f"User {user.email} started pause - redistributing their contacts")
        
        # Ottieni i contatti assegnati all'utente in pausa
        user_contacts = self._get_user_assigned_contacts(user)
        
        if not user_contacts:
            current_app.logger.info(f"User {user.email} has no contacts to redistribute")
            return
        
        current_app.logger.info(f"User {user.email} has {len(user_contacts)} contacts to redistribute")
        
        # Ottieni utenti attivi (escluso chi va in pausa)
        active_users = self._get_active_users(exclude_user_id=user.id)
        
        if not active_users:
            # NESSUN ALTRO UTENTE ATTIVO: Dissocia tutti i contatti
            current_app.logger.warning("No other active users - dissociating all contacts")
            
            # Crea assegnazioni vuote per dissociare
            dissociations = []
            for contact in user_contacts:
                dissociations.append((str(contact['id']), None))  # None = dissocia
            
            # Esegui dissociazioni
            self._execute_bulk_dissociations(
                dissociations,
                assignment_type='pause_start_no_users',
                triggered_by=user
            )
            return
        
        # Ci sono altri utenti: distribuisci i contatti
        assignments = self._distribute_contacts_equally(user_contacts, active_users)
        
        # Esegui le riassegnazioni
        self._execute_bulk_assignments(
            assignments,
            assignment_type='pause_start',
            triggered_by=user
        )
    
    def _handle_pause_end(self, user: User):
        """
        Quando un utente torna dalla pausa: 
        - Se è l'unico utente: assegna tutti i contatti non assegnati a lui
        - Se ci sono altri utenti: ridistribuisci equamente
        """
        current_app.logger.info(f"User {user.email} ended pause - rebalancing contacts")
        
        # Ottieni tutti gli utenti attivi (incluso chi torna)
        all_active_users = self._get_active_users()
        
        # Ottieni TUTTI i contatti con tag "in_attesa" 
        all_contacts = self._fetch_contacts_with_waiting_tag()
        
        if not all_contacts:
            current_app.logger.info("No contacts to rebalance")
            return
        
        current_app.logger.info(f"Found {len(all_contacts)} contacts with 'in_attesa' tag to distribute")
        
        if len(all_active_users) == 1:
            # Solo un utente (quello che torna): assegna tutti i contatti a lui
            current_app.logger.info(f"Only one active user - assigning all {len(all_contacts)} contacts to {user.email}")
            assignments = {user.email: all_contacts}
        else:
            # Più utenti: ridistribuisci equamente
            current_app.logger.info(f"Multiple active users ({len(all_active_users)}) - redistributing contacts equally")
            assignments = self._distribute_contacts_equally(all_contacts, all_active_users)
        
        # Esegui le assegnazioni
        self._execute_bulk_assignments(
            assignments,
            assignment_type='pause_end',
            triggered_by=user
        )
    
    def _handle_end_shift(self, user: User):
        """
        MODIFICATO: Quando un utente finisce il turno:
        - Se rimangono altri utenti: ridistribuisci i suoi contatti
        - Se è l'ultimo utente: dissocia TUTTI i contatti da tutti
        """
        current_app.logger.info(f"User {user.email} ended shift - checking remaining users")
        
        # Ottieni utenti attivi rimanenti (escluso chi sta uscendo)
        remaining_users = self._get_active_users(exclude_user_id=user.id)
        
        if not remaining_users:
            # È l'ultimo utente - DISSOCIA TUTTI I CONTATTI
            current_app.logger.info("LAST USER ending shift - dissociating ALL contacts from ALL users")
            self._dissociate_all_contacts(user)
            
            # Log importante per tracking
            with open('/home/devops/corposostenibile-suite/logs/shift_operations.log', 'a') as f:
                f.write(f"{datetime.utcnow().isoformat()} - END OF DAY: Last user {user.email} ended shift, all contacts dissociated\n")
            return
        
        # Ci sono ancora utenti attivi - redistribuisci solo i contatti di chi esce
        current_app.logger.info(f"{len(remaining_users)} users still active - redistributing contacts from {user.email}")
        
        # Ottieni i contatti dell'utente che esce
        user_contacts = self._get_user_assigned_contacts(user)
        
        if not user_contacts:
            current_app.logger.info(f"User {user.email} has no contacts to redistribute")
            return
        
        current_app.logger.info(f"Redistributing {len(user_contacts)} contacts from {user.email} to {len(remaining_users)} remaining users")
        
        # Distribuisci agli utenti rimanenti
        assignments = self._distribute_contacts_equally(user_contacts, remaining_users)
        
        # Esegui le riassegnazioni
        self._execute_bulk_assignments(
            assignments,
            assignment_type='shift_end_redistribution',
            triggered_by=user
        )
    
    def _get_active_users(self, exclude_user_id: Optional[int] = None) -> List[Dict]:
        """
        Ottiene gli utenti attualmente attivi (working, non in pausa).
        
        Args:
            exclude_user_id: ID utente da escludere (opzionale)
            
        Returns:
            Lista di dizionari con info utenti attivi
        """
        # Query per ottenere l'ultimo stato di ogni utente
        subquery = db.session.query(
            RespondIOWorkTimestamp.user_id,
            func.max(RespondIOWorkTimestamp.timestamp).label('last_timestamp')
        ).group_by(RespondIOWorkTimestamp.user_id).subquery()
        
        # Ottieni gli stati correnti
        current_states = db.session.query(
            RespondIOWorkTimestamp
        ).join(
            subquery,
            and_(
                RespondIOWorkTimestamp.user_id == subquery.c.user_id,
                RespondIOWorkTimestamp.timestamp == subquery.c.last_timestamp
            )
        ).filter(
            RespondIOWorkTimestamp.current_status == 'working'
        )
        
        if exclude_user_id:
            current_states = current_states.filter(
                RespondIOWorkTimestamp.user_id != exclude_user_id
            )
        
        active_users = []
        for state in current_states.all():
            user = User.query.get(state.user_id)
            if user and user.respond_io_profile:
                active_users.append({
                    'id': user.id,
                    'email': user.email,
                    'full_name': user.full_name,
                    'respond_io_id': user.respond_io_profile.respond_io_id
                })
        
        current_app.logger.info(f"Found {len(active_users)} active users")
        return active_users
    
    def _fetch_contacts_with_waiting_tag(self) -> List[Dict]:
        """
        Recupera tutti i contatti con tag "in_attesa" nei lifecycle target.
        
        Returns:
            Lista di contatti
        """
        current_app.logger.info("Fetching contacts with 'in_attesa' tag")
        
        params = {
            'lifecycles': self.TARGET_LIFECYCLES,
            'status': 'open',
            'tags': ['in_attesa']
        }
        
        contacts = self.client.list_contacts_filtered(**params)
        
        # Aggiungi informazioni sulla storia per priorità
        for contact in contacts:
            contact['previous_assignee'] = self._get_previous_assignee(contact['id'])
        
        current_app.logger.info(f"Found {len(contacts)} contacts with 'in_attesa' tag")
        return contacts
    
    def _get_user_assigned_contacts(self, user: User) -> List[Dict]:
        """
        Ottiene i contatti attualmente assegnati a un utente.
        
        Args:
            user: Utente di cui ottenere i contatti
            
        Returns:
            Lista di contatti assegnati all'utente
        """
        if not user.respond_io_profile:
            return []
        
        # IMPORTANTE: Usa l'ID di Respond.io, non l'email!
        params = {
            'lifecycles': self.TARGET_LIFECYCLES,
            'status': 'open',
            'tags': ['in_attesa'],
            'assignee': user.respond_io_profile.respond_io_id  # Usa ID numerico di Respond.io
        }
        
        contacts = self.client.list_contacts_filtered(**params)
        
        # Aggiungi info storia
        for contact in contacts:
            contact['previous_assignee'] = user.email
        
        current_app.logger.info(f"User {user.email} has {len(contacts)} assigned contacts")
        return contacts
    
    def _distribute_contacts_equally(self, 
                                    contacts: List[Dict], 
                                    users: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Distribuisce i contatti equamente tra gli utenti.
        Considera:
        1. Priorità a chi ha già lavorato con il contatto
        2. Distribuzione equa per numero totale
        3. Distribuzione equa per lifecycle
        
        Args:
            contacts: Lista contatti da distribuire
            users: Lista utenti disponibili
            
        Returns:
            Dict mapping user_email -> lista contatti
        """
        if not users:
            raise ValueError("No users available for assignment")
        
        assignments = defaultdict(list)
        user_emails = [u['email'] for u in users]
        
        # Separa contatti per lifecycle
        contacts_by_lifecycle = defaultdict(list)
        for contact in contacts:
            lifecycle = contact.get('lifecycle', 'Unknown')
            contacts_by_lifecycle[lifecycle].append(contact)
        
        # Per ogni lifecycle, distribuisci equamente
        for lifecycle, lifecycle_contacts in contacts_by_lifecycle.items():
            current_app.logger.debug(f"Distributing {len(lifecycle_contacts)} contacts in lifecycle '{lifecycle}'")
            
            # Prima assegna a chi ha già lavorato con il contatto (priorità)
            remaining_contacts = []
            for contact in lifecycle_contacts:
                previous_assignee = contact.get('previous_assignee')
                if previous_assignee and previous_assignee in user_emails:
                    assignments[previous_assignee].append(contact)
                    current_app.logger.debug(f"Reassigning contact {contact['id']} to previous assignee {previous_assignee}")
                else:
                    remaining_contacts.append(contact)
            
            # Distribuisci i rimanenti equamente
            if remaining_contacts:
                # Ordina utenti per numero di contatti già assegnati (ascending)
                sorted_users = sorted(
                    user_emails,
                    key=lambda email: len(assignments[email])
                )
                
                # Assegna round-robin
                for i, contact in enumerate(remaining_contacts):
                    user_email = sorted_users[i % len(sorted_users)]
                    assignments[user_email].append(contact)
        
        # Log distribuzione finale
        for user_email, user_contacts in assignments.items():
            lifecycle_counts = defaultdict(int)
            for contact in user_contacts:
                lifecycle_counts[contact.get('lifecycle', 'Unknown')] += 1
            
            current_app.logger.info(
                f"User {user_email} will receive {len(user_contacts)} contacts: {dict(lifecycle_counts)}"
            )
        
        return dict(assignments)
    
    def _execute_bulk_assignments(self,
                                 assignments: Dict[str, List[Dict]],
                                 assignment_type: str,
                                 triggered_by: User):
        """
        Esegue le assegnazioni in bulk con retry logic.
        
        Args:
            assignments: Mapping user_email -> lista contatti
            assignment_type: Tipo di trigger (shift_start, pause_start, etc.)
            triggered_by: Utente che ha triggerato l'evento
        """
        from flask import current_app
        from corposostenibile.models import User
        
        # Crea log entry
        log = RespondIOAssignmentLog(
            executed_by_id=triggered_by.id,
            assignment_type=f'timestamp_{assignment_type}',
            started_at=datetime.utcnow(),
            status='in_progress',
            lifecycles_processed=self.TARGET_LIFECYCLES,
            details={
                'trigger': assignment_type,
                'triggered_by': triggered_by.email
            }
        )
        db.session.add(log)
        db.session.commit()
        
        # Prepara lista assegnazioni
        all_assignments = []
        user_counts = []
        
        for user_email, contacts in assignments.items():
            # Trova l'ID Respond.io dell'utente
            user = User.query.filter_by(email=user_email).first()
            respond_io_id = None
            if user and user.respond_io_profile:
                respond_io_id = user.respond_io_profile.respond_io_id  # Mantieni come INTEGER!
            else:
                current_app.logger.error(f"No Respond.io profile found for {user_email}")
                continue
            
            user_counts.append({
                'email': user_email,
                'count': len(contacts)
            })
            
            for contact in contacts:
                all_assignments.append((
                    str(contact['id']),
                    respond_io_id  # Usa ID Respond.io invece dell'email!
                ))
        
        log.total_contacts = len(all_assignments)
        log.assigned_to_users = user_counts
        
        # Esegui assegnazioni con retry
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                current_app.logger.info(
                    f"Executing bulk assignment of {len(all_assignments)} contacts (attempt {retry_count + 1})"
                )
                
                results = self.client.bulk_assign_conversations(
                    all_assignments,
                    batch_size=10
                )
                
                # Aggiorna log con risultati
                log.contacts_assigned = len(results['successful'])
                log.contacts_failed = len(results['failed'])
                log.contacts_skipped = 0
                log.status = 'completed' if results['success_rate'] == 100 else 'partial'
                log.completed_at = datetime.utcnow()
                
                if results['failed']:
                    log.error_message = f"Failed to assign {len(results['failed'])} contacts"
                    log.details['failed_assignments'] = results['failed'][:10]
                
                current_app.logger.info(
                    f"Assignment completed: {log.contacts_assigned}/{log.total_contacts} successful"
                )
                
                db.session.commit()
                break  # Success, exit retry loop
                
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    log.status = 'failed'
                    log.error_message = f"Failed after {max_retries} attempts: {str(e)}"
                    log.completed_at = datetime.utcnow()
                    db.session.commit()
                    current_app.logger.error(f"Assignment failed after {max_retries} retries: {e}")
                    raise
                else:
                    current_app.logger.warning(f"Assignment attempt {retry_count} failed, retrying: {e}")
                    time.sleep(5 * retry_count)  # Exponential backoff
    
    def _execute_bulk_dissociations(self,
                                   dissociations: List[Tuple[str, None]],
                                   assignment_type: str,
                                   triggered_by: User):
        """
        Esegue dissociazioni in bulk per contatti.
        
        Args:
            dissociations: Lista di tuple (contact_id, None) per dissociare
            assignment_type: Tipo di trigger
            triggered_by: Utente che ha triggerato l'evento
        """
        from flask import current_app
        
        # Crea log entry
        log = RespondIOAssignmentLog(
            executed_by_id=triggered_by.id,
            assignment_type=f'timestamp_{assignment_type}',
            started_at=datetime.utcnow(),
            status='in_progress',
            lifecycles_processed=self.TARGET_LIFECYCLES,
            details={
                'trigger': assignment_type,
                'triggered_by': triggered_by.email,
                'action': 'dissociation'
            }
        )
        db.session.add(log)
        db.session.commit()
        
        log.total_contacts = len(dissociations)
        
        current_app.logger.info(f"Dissociating {len(dissociations)} contacts")
        
        # Esegui dissociazioni usando bulk_assign con None
        try:
            results = self.client.bulk_assign_conversations(
                dissociations,
                batch_size=10
            )
            
            # Aggiorna log con risultati
            log.contacts_assigned = len(results['successful'])  # In questo caso sono dissociazioni
            log.contacts_failed = len(results['failed'])
            log.status = 'completed' if results['success_rate'] == 100 else 'partial'
            log.completed_at = datetime.utcnow()
            
            if results['failed']:
                log.error_message = f"Failed to dissociate {len(results['failed'])} contacts"
                log.details['failed_dissociations'] = results['failed'][:10]
            
            current_app.logger.info(
                f"Dissociation completed: {log.contacts_assigned}/{log.total_contacts} successful"
            )
            
            db.session.commit()
            
        except Exception as e:
            log.status = 'failed'
            log.error_message = f"Dissociation failed: {str(e)}"
            log.completed_at = datetime.utcnow()
            db.session.commit()
            current_app.logger.error(f"Bulk dissociation failed: {e}")
            raise
    
    def _dissociate_all_contacts(self, last_user: User):
        """
        Dissocia tutti i contatti quando l'ultimo utente esce.
        
        Args:
            last_user: L'ultimo utente che sta uscendo
        """
        current_app.logger.info("Dissociating all contacts - no users remaining")
        
        # Ottieni TUTTI i contatti con tag "in_attesa"
        contacts = self._fetch_contacts_with_waiting_tag()
        
        if not contacts:
            current_app.logger.info("No contacts to dissociate")
            return
        
        # Crea log
        log = RespondIOAssignmentLog(
            executed_by_id=last_user.id,
            assignment_type='timestamp_dissociate_all',
            started_at=datetime.utcnow(),
            status='in_progress',
            lifecycles_processed=self.TARGET_LIFECYCLES,
            details={
                'trigger': 'last_user_exit',
                'triggered_by': last_user.email
            }
        )
        db.session.add(log)
        db.session.commit()
        
        # Prepara dissociazioni (assegna a None/null)
        dissociations = [(str(contact['id']), None) for contact in contacts]
        
        log.total_contacts = len(dissociations)
        
        try:
            # Esegui dissociazioni
            results = self.client.bulk_assign_conversations(
                dissociations,
                batch_size=10
            )
            
            log.contacts_assigned = len(results['successful'])
            log.contacts_failed = len(results['failed'])
            log.status = 'completed' if results['success_rate'] == 100 else 'partial'
            log.completed_at = datetime.utcnow()
            
            current_app.logger.info(f"Dissociated {log.contacts_assigned} contacts successfully")
            
        except Exception as e:
            log.status = 'failed'
            log.error_message = str(e)
            log.completed_at = datetime.utcnow()
            current_app.logger.error(f"Dissociation failed: {e}")
            raise
        
        finally:
            db.session.commit()
    
    def _is_first_shift_user(self, user: User) -> bool:
        """
        Verifica se l'utente fa parte del primo turno della giornata.
        Un utente è del primo turno se:
        1. Non ci sono altri utenti già working
        2. Il suo orario di inizio è entro 1 ora dal primo turno schedulato
        
        Args:
            user: Utente che ha timbrato
            
        Returns:
            True se l'utente fa parte del primo turno
        """
        from datetime import datetime, timedelta
        import pytz
        
        # Check se ci sono già utenti working (escluso questo)
        other_working = self._get_active_users(exclude_user_id=user.id)
        
        if len(other_working) > 0:
            # Ci sono già altri utenti working, non è il primo turno
            current_app.logger.debug(f"User {user.email} is not first shift - {len(other_working)} users already working")
            return False
        
        # Non ci sono altri utenti working - verifica se è nel range del primo turno
        tz = pytz.timezone('Europe/Rome')
        now = datetime.now(tz)
        
        # Cerca il primo turno schedulato per oggi
        from corposostenibile.models import RespondIOCalendarEvent, RespondIOUserWorkSchedule
        
        # Check eventi calendario
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59)
        
        first_event = RespondIOCalendarEvent.query.filter(
            and_(
                RespondIOCalendarEvent.start_datetime >= today_start,
                RespondIOCalendarEvent.start_datetime <= today_end,
                RespondIOCalendarEvent.event_type == 'work',
                RespondIOCalendarEvent.status != 'cancelled'
            )
        ).order_by(RespondIOCalendarEvent.start_datetime).first()
        
        first_shift_time = None
        if first_event:
            first_shift_time = first_event.start_datetime
        
        # Check schedule settimanale
        current_day = now.weekday()
        first_schedule = RespondIOUserWorkSchedule.query.filter(
            and_(
                RespondIOUserWorkSchedule.day_of_week == current_day,
                RespondIOUserWorkSchedule.is_active == True
            )
        ).order_by(RespondIOUserWorkSchedule.start_time).first()
        
        if first_schedule:
            schedule_time = datetime.combine(now.date(), first_schedule.start_time, tzinfo=tz)
            if not first_shift_time or schedule_time < first_shift_time:
                first_shift_time = schedule_time
        
        if not first_shift_time:
            # Nessun turno schedulato, considera come primo turno
            current_app.logger.info(f"No shifts scheduled - treating {user.email} as first shift")
            return True
        
        # Verifica se l'utente sta timbrando entro 1 ora dal primo turno
        time_difference = abs((now - first_shift_time).total_seconds() / 60)  # in minuti
        
        if time_difference <= 60:  # Entro 60 minuti dal primo turno
            current_app.logger.info(
                f"User {user.email} is part of first shift "
                f"(timing within {time_difference:.0f} min of first shift at {first_shift_time.strftime('%H:%M')})"
            )
            return True
        else:
            current_app.logger.info(
                f"User {user.email} is NOT first shift "
                f"(timing {time_difference:.0f} min from first shift at {first_shift_time.strftime('%H:%M')})"
            )
            return False
    
    def _get_previous_assignee(self, contact_id: str) -> Optional[str]:
        """
        Ottiene l'assignee precedente di un contatto dalla storia.
        
        Args:
            contact_id: ID del contatto
            
        Returns:
            Email dell'assignee precedente o None
        """
        # Per ora ritorniamo None, evitando la query problematica sul JSON
        # TODO: Implementare ricerca corretta quando necessario
        return None
    
    def handle_tag_change(self, contact_id: str, tag: str, action: str):
        """
        Gestisce i cambiamenti di tag.
        - REMOVED: dissocia immediatamente
        - ADDED: assegna IMMEDIATAMENTE
        
        Args:
            contact_id: ID del contatto
            tag: Nome del tag
            action: 'added' o 'removed'
        """
        if tag != 'in_attesa':
            return
        
        from flask import current_app
        
        if action == 'removed':
            # RIMOZIONE: Dissocia SUBITO
            current_app.logger.info(f"Tag 'in_attesa' removed for contact {contact_id} - dissociating immediately")
            try:
                self.client.assign_conversation(contact_id, None)
                current_app.logger.info(f"Successfully dissociated contact {contact_id}")
            except Exception as e:
                current_app.logger.error(f"Failed to dissociate contact {contact_id}: {e}")
        else:
            # AGGIUNTA: Assegna IMMEDIATAMENTE
            current_app.logger.info(f"Tag 'in_attesa' added for contact {contact_id} - assigning immediately")
            
            # Processa SUBITO l'assegnazione
            self._process_tag_change(contact_id, 'added')
    
    def _process_tag_change_with_context(self, app, contact_id: str, action: str):
        """Wrapper per gestire il contesto Flask nel thread del timer."""
        with app.app_context():
            self._process_tag_change(contact_id, action)
    
    def _process_tag_change(self, contact_id: str, action: str):
        """
        Processa il cambio di tag IMMEDIATAMENTE.
        
        Args:
            contact_id: ID del contatto
            action: 'added' o 'removed'
        """
        from flask import current_app
        from corposostenibile.models import User, RespondIOAssignmentLog
        from corposostenibile.extensions import db
        
        try:
            if action == 'removed':
                # Dissocia il contatto
                current_app.logger.info(f"Dissociating contact {contact_id} after tag removal")
                self.client.assign_conversation(contact_id, None)
                
            elif action == 'added':
                # Assegna all'utente con MENO CONTATTI (bilanciamento del carico)
                active_users = self._get_active_users()
                if not active_users:
                    current_app.logger.warning("No active users to assign contact to")
                    return
                
                current_app.logger.info(f"Found {len(active_users)} active users for assignment")
                
                # Conta i contatti per ogni utente per trovare chi ha meno carico
                user_loads = {}
                user_id_map = {}  # Mappa user.id -> respond_io_id
                
                for user_data in active_users:
                    user = User.query.get(user_data['id'])
                    if user and user.respond_io_profile:
                        # Conta velocemente i contatti assegnati
                        user_contacts = self._get_user_assigned_contacts(user)
                        load = len(user_contacts) if user_contacts else 0
                        user_loads[user.id] = load
                        user_id_map[user.id] = {
                            'respond_io_id': user.respond_io_profile.respond_io_id,
                            'email': user.email,
                            'load': load
                        }
                
                if not user_loads:
                    current_app.logger.error("No users with respond.io profiles found")
                    return
                
                # Trova l'utente con MENO contatti assegnati
                min_user_id = min(user_loads, key=user_loads.get)
                min_user_data = user_id_map[min_user_id]
                respond_io_id = min_user_data['respond_io_id']
                
                current_app.logger.info(
                    f"Assigning contact {contact_id} to user {min_user_data['email']} "
                    f"(ID: {respond_io_id}, current load: {min_user_data['load']} contacts)"
                )
                
                try:
                    # Assegna al user con meno carico
                    self.client.assign_conversation(contact_id, respond_io_id)
                    current_app.logger.info(f"Successfully assigned contact {contact_id}")
                    
                    # Log assegnazione nel database
                    assignment_log = RespondIOAssignmentLog(
                        contact_id=contact_id,
                        assigned_to_id=min_user_id,
                        event_type='tag_added',
                        triggered_by_id=min_user_id,
                        status='completed',
                        total_contacts=1,
                        assigned_count=1
                    )
                    db.session.add(assignment_log)
                    db.session.commit()
                    
                except Exception as assign_error:
                    current_app.logger.error(f"Failed to assign to {min_user_data['email']}: {assign_error}")
                
        except Exception as e:
            current_app.logger.error(f"Error processing tag change: {e}", exc_info=True)