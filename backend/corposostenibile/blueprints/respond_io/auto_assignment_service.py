"""
Servizio avanzato per assegnazione automatica intelligente con monitoraggio real-time
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Tuple
from collections import defaultdict
import pytz
from flask import current_app
from sqlalchemy import and_, or_, func
from corposostenibile.extensions import db
from corposostenibile.models import (
    User,
    RespondIOUser,
    RespondIOCalendarEvent,
    RespondIOAssignmentLog,
    RespondIOCalendarBreak
)


class AutoAssignmentService:
    """
    Servizio intelligente per assegnazione automatica con:
    - Check ogni 10 minuti per variazioni
    - Distribuzione equa per utente E per lifecycle
    - Assegnazione istantanea nuovi contatti
    - Gestione cambio turni
    - Rimozione assegnazioni quando nessuno in turno
    """
    
    # Configurazione
    CHECK_INTERVAL_MINUTES = 10
    TAG_FILTERS = ['in_attesa']  # Solo tag in_attesa
    TARGET_LIFECYCLES = ['Contrassegnato', 'In Target', 'Link Da Inviare', 'Link Inviato']
    
    # Cache per rilevare variazioni
    _last_state_hash = None
    _last_users_on_duty = set()
    _last_contacts_state = {}
    _contacts_per_user = defaultdict(int)
    
    def __init__(self, client=None):
        """Inizializza il servizio"""
        self.client = client
        if not self.client and current_app:
            self.client = current_app.respond_io_client
        self.tz = pytz.timezone('Europe/Rome')
    
    def get_current_state_hash(self) -> str:
        """
        Calcola un hash dello stato attuale per rilevare variazioni.
        Include: utenti in turno, contatti aperti con tag, assegnazioni attuali
        """
        state_parts = []
        
        # 1. Utenti in turno
        users_on_duty = self.get_users_on_duty_detailed()
        users_ids = sorted([str(u['id']) for u in users_on_duty])
        state_parts.append(f"users:{','.join(users_ids)}")
        
        # 2. Contatti aperti con tag in_attesa
        contacts = self.fetch_contacts_with_tag()
        contact_ids = sorted([str(c['id']) for c in contacts])
        state_parts.append(f"contacts:{','.join(contact_ids)}")
        
        # 3. Assegnazioni attuali
        assignments = {}
        for contact in contacts:
            if contact.get('assignee'):
                assignments[contact['id']] = contact['assignee'].get('email', '')
        
        assignment_str = json.dumps(assignments, sort_keys=True)
        state_parts.append(f"assignments:{assignment_str}")
        
        # Calcola hash
        state_string = '|'.join(state_parts)
        return hashlib.md5(state_string.encode()).hexdigest()
    
    def get_users_on_duty_detailed(self) -> List[Dict]:
        """
        Ottiene utenti in turno con dettagli completi, escludendo chi è in pausa.
        """
        now = datetime.now(self.tz)
        users_on_duty = []
        user_ids_added = set()
        
        # Check eventi calendario
        calendar_events = RespondIOCalendarEvent.query.filter(
            and_(
                RespondIOCalendarEvent.start_datetime <= now,
                RespondIOCalendarEvent.end_datetime >= now,
                RespondIOCalendarEvent.event_type == 'work',
                RespondIOCalendarEvent.status != 'cancelled'
            )
        ).all()
        
        for event in calendar_events:
            user = event.user
            if user and user.id not in user_ids_added and user.is_active:
                # Check se in pausa
                is_on_break = False
                for break_item in event.breaks:
                    if break_item.start_time <= now <= break_item.end_time:
                        is_on_break = True
                        break
                
                if not is_on_break:
                    users_on_duty.append({
                        'id': user.id,
                        'respond_io_id': user.respond_io_id,
                        'email': user.email,
                        'full_name': user.full_name,
                        'current_load': self._contacts_per_user.get(user.email, 0)
                    })
                    user_ids_added.add(user.id)
        
        return users_on_duty
    
    def fetch_contacts_with_tag(self) -> List[Dict]:
        """Recupera tutti i contatti aperti con tag 'in_attesa' o 'da_rispondere' nei lifecycle target"""
        try:
            current_app.logger.info(f"Fetching contacts with tags: {self.TAG_FILTERS} in lifecycles: {self.TARGET_LIFECYCLES}")
            
            # Recupera tutti i contatti aperti (dobbiamo filtrarli manualmente per lifecycle)
            all_open_contacts = self.client.list_contacts_filtered(
                status='open',
                limit=2000  # Aumentiamo il limite
            )
            
            # Filtra per: tag (in_attesa O da_rispondere) E lifecycle target
            filtered_contacts = []
            for contact in all_open_contacts:
                # Check lifecycle
                lifecycle = contact.get('lifecycle')
                if lifecycle not in self.TARGET_LIFECYCLES:
                    continue
                
                # Check tags (deve avere almeno uno dei tag)
                tags = contact.get('tags', [])
                has_required_tag = any(tag in tags for tag in self.TAG_FILTERS)
                if not has_required_tag:
                    continue
                
                # Passa entrambi i filtri
                filtered_contacts.append(contact)
            
            current_app.logger.info(f"Found {len(filtered_contacts)} contacts with tags {self.TAG_FILTERS} in target lifecycles")
            current_app.logger.info(f"  Total open contacts: {len(all_open_contacts)}")
            current_app.logger.info(f"  Filtered to: {len(filtered_contacts)}")
            
            # Log distribution for debug
            assigned_count = len([c for c in filtered_contacts if c.get('assignee')])
            unassigned_count = len([c for c in filtered_contacts if not c.get('assignee')])
            current_app.logger.info(f"  - Already assigned: {assigned_count}")
            current_app.logger.info(f"  - Unassigned: {unassigned_count}")
            
            # Log by lifecycle
            by_lifecycle = defaultdict(int)
            for c in filtered_contacts:
                by_lifecycle[c.get('lifecycle', 'Unknown')] += 1
            current_app.logger.info(f"  - By lifecycle: {dict(by_lifecycle)}")
            
            return filtered_contacts
        except Exception as e:
            current_app.logger.error(f"Errore recupero contatti: {str(e)}")
            return []
    
    def distribute_contacts_by_lifecycle(self, 
                                       contacts: List[Dict], 
                                       users: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Distribuisce i contatti equamente per utente E per lifecycle.
        
        Returns:
            Dict mapping user_email -> lista contatti assegnati
        """
        if not users:
            return {}
        
        # Raggruppa contatti per lifecycle
        contacts_by_lifecycle = defaultdict(list)
        for contact in contacts:
            # Il lifecycle è direttamente nel contact, non nested
            lifecycle = contact.get('lifecycle', 'Unknown')
            contacts_by_lifecycle[lifecycle].append(contact)
        
        # Inizializza assegnazioni
        assignments = defaultdict(list)
        user_emails = [u['email'] for u in users]
        user_index = 0
        
        # Distribuisci ogni lifecycle equamente tra gli utenti
        for lifecycle, lifecycle_contacts in contacts_by_lifecycle.items():
            # Ordina per data creazione (FIFO)
            lifecycle_contacts.sort(key=lambda x: x.get('createdAt', ''))
            
            # Assegna round-robin
            for contact in lifecycle_contacts:
                assignments[user_emails[user_index]].append(contact)
                user_index = (user_index + 1) % len(users)
        
        # Bilancia il carico finale
        assignments = self.balance_final_load(dict(assignments), users)
        
        return assignments
    
    def balance_final_load(self, 
                          assignments: Dict[str, List[Dict]], 
                          users: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Bilancia il carico finale per evitare squilibri eccessivi.
        """
        if len(users) <= 1:
            return assignments
        
        # Calcola carico medio
        total_contacts = sum(len(contacts) for contacts in assignments.values())
        avg_load = total_contacts / len(users)
        tolerance = max(1, int(avg_load * 0.1))  # 10% di tolleranza
        
        # Identifica utenti sovraccarichi e sottocarichi
        overloaded = []
        underloaded = []
        
        for user in users:
            email = user['email']
            current_load = len(assignments.get(email, []))
            
            if current_load > avg_load + tolerance:
                overloaded.append((email, current_load))
            elif current_load < avg_load - tolerance:
                underloaded.append((email, current_load))
        
        # Riequilibra
        for over_email, over_load in overloaded:
            for under_email, under_load in underloaded:
                transfer_count = min(
                    int((over_load - avg_load) / 2),
                    int((avg_load - under_load) / 2)
                )
                
                if transfer_count > 0:
                    # Trasferisci contatti
                    transfers = assignments[over_email][-transfer_count:]
                    assignments[over_email] = assignments[over_email][:-transfer_count]
                    assignments[under_email].extend(transfers)
                    
                    current_app.logger.info(
                        f"Bilanciamento: trasferiti {transfer_count} contatti "
                        f"da {over_email} a {under_email}"
                    )
        
        return assignments
    
    def detect_changes(self) -> Dict:
        """
        Rileva variazioni nello stato del sistema.
        
        Returns:
            Dict con tipo di variazione e dettagli
        """
        changes = {
            'has_changes': False,
            'type': None,
            'details': {}
        }
        
        # Stato attuale
        current_hash = self.get_current_state_hash()
        current_users = set(u['email'] for u in self.get_users_on_duty_detailed())
        current_contacts = self.fetch_contacts_with_tag()
        
        # Prima esecuzione
        if self._last_state_hash is None:
            changes['has_changes'] = True
            changes['type'] = 'initial'
            changes['details'] = {
                'message': 'Prima esecuzione del sistema',
                'users_count': len(current_users),
                'contacts_count': len(current_contacts)
            }
        
        # Check variazione hash
        elif current_hash != self._last_state_hash:
            changes['has_changes'] = True
            
            # Analizza tipo di variazione
            if current_users != self._last_users_on_duty:
                if len(current_users) == 0:
                    changes['type'] = 'no_users'
                    changes['details'] = {
                        'message': 'Nessun utente in turno - rimozione assegnazioni',
                        'previous_users': list(self._last_users_on_duty)
                    }
                elif len(self._last_users_on_duty) == 0:
                    changes['type'] = 'users_started'
                    changes['details'] = {
                        'message': 'Utenti entrati in turno',
                        'new_users': list(current_users)
                    }
                else:
                    added = current_users - self._last_users_on_duty
                    removed = self._last_users_on_duty - current_users
                    changes['type'] = 'users_changed'
                    changes['details'] = {
                        'message': 'Cambio turni utenti',
                        'added': list(added),
                        'removed': list(removed)
                    }
            
            # Check nuovi contatti
            else:
                new_contacts = []
                changed_assignments = []
                
                current_contact_ids = {c['id']: c for c in current_contacts}
                
                for contact in current_contacts:
                    if contact['id'] not in self._last_contacts_state:
                        new_contacts.append(contact['id'])
                    elif self._last_contacts_state[contact['id']].get('assignee') != contact.get('assignee'):
                        changed_assignments.append(contact['id'])
                
                if new_contacts:
                    changes['type'] = 'new_contacts'
                    changes['details'] = {
                        'message': f'Nuovi contatti con tag {self.TAG_FILTER}',
                        'new_contact_ids': new_contacts,
                        'count': len(new_contacts)
                    }
                elif changed_assignments:
                    changes['type'] = 'assignments_changed'
                    changes['details'] = {
                        'message': 'Assegnazioni modificate manualmente',
                        'changed_ids': changed_assignments
                    }
        
        # Aggiorna cache
        self._last_state_hash = current_hash
        self._last_users_on_duty = current_users
        self._last_contacts_state = {c['id']: c for c in current_contacts}
        
        return changes
    
    def execute_auto_assignment(self, reason: str = "Check periodico") -> Dict:
        """
        Esegue l'assegnazione automatica intelligente.
        
        Returns:
            Dict con risultati dell'operazione
        """
        result = {
            'success': False,
            'timestamp': datetime.now(self.tz).isoformat(),
            'reason': reason,
            'stats': {}
        }
        
        try:
            # Rileva variazioni
            changes = self.detect_changes()
            
            if not changes['has_changes']:
                result['success'] = True
                result['message'] = 'Nessuna variazione rilevata'
                return result
            
            # Log variazione
            current_app.logger.info(f"Variazione rilevata: {changes['type']} - {changes['details']}")
            result['change_type'] = changes['type']
            result['change_details'] = changes['details']
            
            # Ottieni stato attuale
            users_on_duty = self.get_users_on_duty_detailed()
            contacts = self.fetch_contacts_with_tag()
            
            # Caso speciale: nessun utente in turno
            if len(users_on_duty) == 0:
                result.update(self.remove_all_assignments(contacts))
                return result
            
            # Filtra solo contatti non assegnati o da riassegnare
            contacts_to_assign = []
            for contact in contacts:
                if not contact.get('assignee'):
                    contacts_to_assign.append(contact)
                elif changes['type'] in ['users_changed', 'users_started']:
                    # Riassegna se ci sono cambi turno
                    contacts_to_assign.append(contact)
            
            if not contacts_to_assign:
                result['success'] = True
                result['message'] = 'Nessun contatto da assegnare'
                return result
            
            # Distribuisci intelligentemente
            assignments = self.distribute_contacts_by_lifecycle(contacts_to_assign, users_on_duty)
            
            # Esegui assegnazioni
            log = self.execute_bulk_assignments(assignments, reason)
            
            # Aggiorna contatori
            for email, assigned_contacts in assignments.items():
                self._contacts_per_user[email] = len(assigned_contacts)
            
            # Prepara risultato
            result['success'] = log.status in ['completed', 'partial']
            result['message'] = f"Assegnati {log.contacts_assigned} contatti su {log.total_contacts}"
            result['stats'] = {
                'total_contacts': log.total_contacts,
                'assigned': log.contacts_assigned,
                'failed': log.contacts_failed,
                'users_involved': len(users_on_duty),
                'assignments_per_user': log.assigned_to_users,
                'log_id': log.id
            }
            
            # Statistiche per lifecycle
            lifecycle_stats = defaultdict(lambda: defaultdict(int))
            for email, contacts_list in assignments.items():
                for contact in contacts_list:
                    lifecycle = contact.get('lifecycle', {}).get('name', 'Unknown')
                    lifecycle_stats[email][lifecycle] += 1
            
            result['lifecycle_distribution'] = dict(lifecycle_stats)
            
        except Exception as e:
            result['success'] = False
            result['message'] = f"Errore: {str(e)}"
            current_app.logger.error(f"Errore auto-assignment: {str(e)}", exc_info=True)
        
        return result
    
    def remove_all_assignments(self, contacts: List[Dict]) -> Dict:
        """
        Rimuove tutte le assegnazioni quando non ci sono utenti in turno.
        """
        result = {
            'success': False,
            'message': 'Rimozione assegnazioni per mancanza utenti in turno'
        }
        
        try:
            # Prepara lista di de-assegnazioni
            unassignments = []
            for contact in contacts:
                if contact.get('assignee'):
                    unassignments.append((
                        str(contact['id']),
                        None  # Assegna a nessuno
                    ))
            
            if unassignments:
                # Esegui de-assegnazioni
                results = self.client.bulk_assign_conversations(
                    unassignments,
                    batch_size=10
                )
                
                result['success'] = True
                result['stats'] = {
                    'removed': len(results['successful']),
                    'failed': len(results['failed']),
                    'total': len(unassignments)
                }
                
                current_app.logger.info(
                    f"Rimosse {len(results['successful'])} assegnazioni "
                    f"(nessun utente in turno)"
                )
            else:
                result['success'] = True
                result['message'] = 'Nessuna assegnazione da rimuovere'
            
        except Exception as e:
            result['message'] = f"Errore rimozione: {str(e)}"
            current_app.logger.error(f"Errore rimozione assegnazioni: {str(e)}")
        
        return result
    
    def execute_bulk_assignments(self, 
                                assignments: Dict[str, List[Dict]], 
                                reason: str) -> RespondIOAssignmentLog:
        """
        Esegue le assegnazioni in bulk con logging.
        """
        # Crea log
        log = RespondIOAssignmentLog(
            assignment_type='automatic',
            started_at=datetime.utcnow(),
            status='in_progress',
            notes=reason,
            details={
                'reason': reason,
                'tag_filter': self.TAG_FILTER,
                'timestamp': datetime.now(self.tz).isoformat()
            }
        )
        db.session.add(log)
        db.session.commit()
        
        # Prepara assegnazioni
        all_assignments = []
        user_counts = []
        
        for user_email, contacts in assignments.items():
            user_counts.append({
                'email': user_email,
                'count': len(contacts)
            })
            
            for contact in contacts:
                all_assignments.append((
                    str(contact['id']),
                    user_email
                ))
        
        log.total_contacts = len(all_assignments)
        log.assigned_to_users = user_counts
        
        # Esegui
        try:
            results = self.client.bulk_assign_conversations(
                all_assignments,
                batch_size=10
            )
            
            log.contacts_assigned = len(results['successful'])
            log.contacts_failed = len(results['failed'])
            log.status = 'completed' if results['success_rate'] == 100 else 'partial'
            log.completed_at = datetime.utcnow()
            
            if results['failed']:
                log.error_message = f"Failed: {len(results['failed'])} contacts"
                log.details['failed_assignments'] = results['failed'][:10]
            
        except Exception as e:
            log.status = 'failed'
            log.error_message = str(e)
            log.completed_at = datetime.utcnow()
            raise
        
        finally:
            db.session.commit()
        
        return log
    
    def assign_single_new_contact(self, contact: Dict) -> Dict:
        """
        Assegna istantaneamente un nuovo contatto all'utente con meno carico.
        """
        result = {
            'success': False,
            'contact_id': contact['id']
        }
        
        try:
            users = self.get_users_on_duty_detailed()
            
            if not users:
                result['message'] = 'Nessun utente in turno'
                return result
            
            # Trova utente con meno carico
            users.sort(key=lambda u: u.get('current_load', 0))
            selected_user = users[0]
            
            # Assegna
            self.client.assign_conversation(
                contact['id'],
                selected_user['email']
            )
            
            # Aggiorna contatore
            self._contacts_per_user[selected_user['email']] += 1
            
            result['success'] = True
            result['assigned_to'] = selected_user['email']
            result['message'] = f"Assegnato a {selected_user['full_name']}"
            
            current_app.logger.info(
                f"Nuovo contatto {contact['id']} assegnato istantaneamente a {selected_user['email']}"
            )
            
        except Exception as e:
            result['message'] = f"Errore: {str(e)}"
            current_app.logger.error(f"Errore assegnazione singola: {str(e)}")
        
        return result
    
    def get_current_statistics(self) -> Dict:
        """
        Ottiene statistiche real-time per la dashboard.
        """
        stats = {
            'timestamp': datetime.now(self.tz).isoformat(),
            'users_on_duty': [],
            'total_contacts': 0,
            'distribution': {},
            'lifecycle_breakdown': defaultdict(lambda: defaultdict(int))
        }
        
        try:
            # Utenti in turno
            users = self.get_users_on_duty_detailed()
            stats['users_on_duty'] = users
            
            # Contatti con tag
            contacts = self.fetch_contacts_with_tag()
            stats['total_contacts'] = len(contacts)
            
            # Distribuzione attuale
            for contact in contacts:
                assignee = contact.get('assignee', {})
                if assignee:
                    email = assignee.get('email', 'unassigned')
                    lifecycle = contact.get('lifecycle', {}).get('name', 'Unknown')
                    
                    if email not in stats['distribution']:
                        stats['distribution'][email] = {
                            'name': assignee.get('firstName', '') + ' ' + assignee.get('lastName', ''),
                            'count': 0,
                            'lifecycles': defaultdict(int)
                        }
                    
                    stats['distribution'][email]['count'] += 1
                    stats['distribution'][email]['lifecycles'][lifecycle] += 1
                    stats['lifecycle_breakdown'][lifecycle][email] += 1
            
            # Converti defaultdict in dict normale
            for email in stats['distribution']:
                stats['distribution'][email]['lifecycles'] = dict(
                    stats['distribution'][email]['lifecycles']
                )
            stats['lifecycle_breakdown'] = {
                k: dict(v) for k, v in stats['lifecycle_breakdown'].items()
            }
            
        except Exception as e:
            current_app.logger.error(f"Errore statistiche: {str(e)}")
        
        return stats
    
    def get_today_logs(self) -> List[Dict]:
        """
        Ottiene i log di oggi per la dashboard.
        """
        today_start = datetime.now(self.tz).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        
        logs = RespondIOAssignmentLog.query.filter(
            RespondIOAssignmentLog.started_at >= today_start
        ).order_by(
            RespondIOAssignmentLog.started_at.desc()
        ).all()
        
        log_list = []
        for log in logs:
            log_list.append({
                'id': log.id,
                'timestamp': log.started_at.isoformat(),
                'type': log.assignment_type,
                'status': log.status,
                'reason': log.notes or 'Assegnazione automatica',
                'total_contacts': log.total_contacts,
                'assigned': log.contacts_assigned,
                'failed': log.contacts_failed,
                'duration': log.duration_seconds,
                'users': log.assigned_to_users
            })
        
        return log_list
    
    def log_assignment(self, action, reason, details=None, user_id=None, contact_id=None):
        """Log assignment action to database"""
        from corposostenibile.extensions import db
        from corposostenibile.models import RespondIOAssignmentLog
        
        log = RespondIOAssignmentLog(
            action=action,
            reason=reason,
            details=details,
            user_id=user_id,
            contact_id=contact_id
        )
        db.session.add(log)
        db.session.commit()
        
        return log
    
    @property
    def last_check_time(self):
        """Get last check time from latest log"""
        last_log = RespondIOAssignmentLog.query.filter_by(
            assignment_type='automatic'
        ).order_by(RespondIOAssignmentLog.started_at.desc()).first()
        
        if last_log:
            return last_log.started_at
        return None
    
    def get_assignment_statistics(self):
        """Get current assignment statistics for dashboard"""
        stats = {
            'total_contacts': 0,
            'unassigned_contacts': 0,
            'by_user': {},
            'by_lifecycle': {},
            'tag_filters': self.TAG_FILTERS,  # Show which tags we're filtering
            'target_lifecycles': self.TARGET_LIFECYCLES  # Show which lifecycles
        }
        
        try:
            # Get ONLY contacts with tag "in_attesa"
            contacts = self.fetch_contacts_with_tag()
            stats['total_contacts'] = len(contacts)
            
            # Count unassigned
            unassigned = [c for c in contacts if not c.get('assignee')]
            stats['unassigned_contacts'] = len(unassigned)
            
            # Count by user and lifecycle
            for contact in contacts:
                if contact.get('assignee'):
                    # Try multiple fields for user name
                    assignee = contact.get('assignee', {})
                    user_name = assignee.get('firstName', '')
                    if assignee.get('lastName'):
                        user_name += f" {assignee.get('lastName')}"
                    if not user_name.strip():
                        user_name = assignee.get('email', 'Unknown')
                    
                    stats['by_user'][user_name] = stats['by_user'].get(user_name, 0) + 1
                
                # Try multiple places for lifecycle
                lifecycle = None
                # Try direct lifecycle field
                if 'lifecycle' in contact:
                    lifecycle = contact['lifecycle']
                # Try in customFields
                elif 'customFields' in contact and contact['customFields']:
                    lifecycle = contact['customFields'].get('Lifecycle')
                # Try tags as fallback
                elif 'tags' in contact:
                    # Check for lifecycle-like tags
                    for tag in contact.get('tags', []):
                        if tag in ['Nuova Lead', 'Contrassegnato', 'In Target', 'Link Da Inviare', 'Link Inviato']:
                            lifecycle = tag
                            break
                
                if not lifecycle:
                    lifecycle = 'Non Classificato'
                    
                stats['by_lifecycle'][lifecycle] = stats['by_lifecycle'].get(lifecycle, 0) + 1
        
        except Exception as e:
            current_app.logger.error(f"Error getting statistics: {str(e)}")
            # Return mock data for testing
            stats = {
                'total_contacts': 0,
                'unassigned_contacts': 0,
                'by_user': {},
                'by_lifecycle': {}
            }
        
        return stats
    
    def run_assignment_check(self):
        """
        Main method to run the automatic assignment check.
        Detects changes and performs assignments as needed.
        """
        result = {
            'success': False,
            'message': '',
            'stats': {}
        }
        
        try:
            # Check for changes
            current_hash = self.get_current_state_hash()
            
            if self._last_state_hash and current_hash == self._last_state_hash:
                result['message'] = 'No changes detected'
                result['success'] = True
                return result
            
            # Get users on duty
            users_on_duty = self.get_users_on_duty_detailed()
            
            if not users_on_duty:
                # No users on duty - remove all assignments
                contacts = self.fetch_contacts_with_tag()
                removal_result = self.handle_no_users_on_duty(contacts)
                result.update(removal_result)
                self._last_state_hash = current_hash
                return result
            
            # Get ALL contacts with tag (assigned or not - we reassign all)
            contacts = self.fetch_contacts_with_tag()
            
            if not contacts:
                result['message'] = 'No contacts with tag to assign'
                result['success'] = True
                self._last_state_hash = current_hash
                return result
            
            current_app.logger.info(f"Reassigning ALL {len(contacts)} contacts with tags {self.TAG_FILTERS} in lifecycles {self.TARGET_LIFECYCLES}")
            
            # Distribute ALL contacts (reassign everyone)
            assignments = self.distribute_contacts_by_lifecycle(contacts, users_on_duty)
            
            # Execute assignments
            log = self.execute_bulk_assignments(
                assignments, 
                f'Automatic reassignment - {len(contacts)} contacts to {len(users_on_duty)} users'
            )
            
            result['success'] = True
            result['message'] = f'Assigned {log.contacts_assigned} contacts'
            result['stats'] = {
                'assigned': log.contacts_assigned,
                'failed': log.contacts_failed,
                'total': log.total_contacts
            }
            
            # Update state hash
            self._last_state_hash = current_hash
            
        except Exception as e:
            result['message'] = f'Error: {str(e)}'
            current_app.logger.error(f"Assignment check error: {str(e)}")
        
        return result