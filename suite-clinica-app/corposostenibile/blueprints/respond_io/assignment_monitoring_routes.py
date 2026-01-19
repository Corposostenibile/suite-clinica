"""
Routes per monitoraggio assegnazioni automatiche basate su timbrature
"""

from datetime import datetime, date, timedelta
from collections import defaultdict
from flask import render_template, request, jsonify, current_app
from flask_login import login_required
from sqlalchemy import func, and_
from corposostenibile.extensions import db, csrf
from corposostenibile.models import (
    User,
    RespondIOUser,
    RespondIOAssignmentLog,
    RespondIOWorkTimestamp,
    RespondIOContactChannel
)
from . import bp


@bp.route('/assignment')
@login_required
def assignment_monitoring():
    """Dashboard monitoraggio assegnazioni e distribuzione contatti"""
    
    # Parametri filtro
    filter_date = request.args.get('date', date.today().isoformat())
    try:
        filter_date = datetime.strptime(filter_date, '%Y-%m-%d').date()
    except:
        filter_date = date.today()
    
    # 1. UTENTI ATTIVI (senza conteggi reali al caricamento per velocità)
    active_users = _get_active_users_basic()  # Solo info base senza API calls
    
    # 2. CONTATTI IN ATTESA NON ASSEGNATI (placeholder)
    unassigned_waiting = {'total': 0, 'lifecycle_breakdown': {}}
    
    # 3. LOG ASSEGNAZIONI DEL GIORNO
    assignment_logs = _get_assignment_logs(filter_date)
    
    # 4. STATISTICHE DISTRIBUZIONE PER LIFECYCLE
    lifecycle_distribution = _get_lifecycle_distribution_real(active_users)
    
    # 5. TIMELINE EVENTI GIORNATA
    timeline_events = _get_timeline_events(filter_date)
    
    return render_template('respond_io/assignment_monitoring.html',
                         active_users=active_users,
                         unassigned_waiting=unassigned_waiting,
                         assignment_logs=assignment_logs,
                         lifecycle_distribution=lifecycle_distribution,
                         timeline_events=timeline_events,
                         filter_date=filter_date,
                         today=date.today())


def _get_active_users_basic():
    """
    Ottiene gli utenti attualmente attivi SENZA conteggi reali.
    Versione veloce per il caricamento iniziale della pagina.
    """
    from flask import current_app
    
    # Query per ottenere l'ultimo stato di ogni utente
    subquery = db.session.query(
        RespondIOWorkTimestamp.user_id,
        func.max(RespondIOWorkTimestamp.timestamp).label('last_timestamp')
    ).group_by(RespondIOWorkTimestamp.user_id).subquery()
    
    # Ottieni gli stati correnti (solo working)
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
    ).all()
    
    active_users = []
    
    for state in current_states:
        user = User.query.get(state.user_id)
        if user and user.respond_io_profile:
            user_data = {
                'id': user.id,
                'respond_io_id': user.respond_io_profile.respond_io_id,
                'email': user.email,
                'full_name': user.full_name,
                'total_contacts': 0,  # Placeholder - sarà calcolato con API
                'lifecycle_breakdown': {},  # Placeholder
                'status_since': state.timestamp.isoformat()
            }
            active_users.append(user_data)
    
    return active_users


@bp.route('/api/assignment/test-calculation', methods=['GET'])
@login_required
def test_calculation():
    """Test endpoint per verificare il calcolo"""
    try:
        active_users = _get_active_users_basic()
        
        # Test semplice: prova a recuperare contatti per il primo utente
        if active_users:
            first_user = active_users[0]
            test_result = {
                'active_users': len(active_users),
                'first_user': first_user['email'],
                'respond_io_id': first_user.get('respond_io_id'),
                'test_query': None,
                'error': None
            }
            
            # Prova a fare una query di test
            try:
                filter_query = {
                    '$and': [
                        {'lifecycles': {'$in': ['Nuova Lead']}},
                        {'tags': {'$in': ['in_attesa']}},
                        {'assignedUserId': first_user['respond_io_id']}
                    ]
                }
                
                response = current_app.respond_io_client.list_contacts(
                    limit=10,
                    filters={'filter': filter_query}
                )
                test_result['test_query'] = {
                    'success': True,
                    'count': len(response.get('items', [])),
                    'response_keys': list(response.keys()) if response else []
                }
            except Exception as e:
                test_result['error'] = str(e)
                
            return jsonify(test_result)
        else:
            return jsonify({'error': 'No active users found'})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/assignment/calculate-real-counts', methods=['POST'])
@csrf.exempt
@login_required
def calculate_real_assignment_counts():
    """
    API endpoint per calcolare i conteggi reali dei contatti assegnati.
    Chiamato dal pulsante "Calcola distribuzione reale".
    """
    import time
    from flask import current_app
    
    # Log the request for debugging
    current_app.logger.info("calculate_real_assignment_counts called")
    
    try:
        # Target lifecycles
        target_lifecycles = [
            'Nuova Lead',
            'Contrassegnato',
            'In Target',
            'Link Da Inviare',
            'Link Inviato',
            'Prenotato'
        ]
        
        # Ottieni utenti attivi
        active_users = _get_active_users_basic()
        
        # Log per debug
        current_app.logger.info(f"Active users found: {len(active_users)}")
        
        # Check if we have the client
        if not hasattr(current_app, 'respond_io_client'):
            current_app.logger.error("respond_io_client not found in app")
            return jsonify({
                'success': False,
                'error': 'Respond.io client not initialized'
            }), 500
        
        result = {
            'user_breakdown': {},  # Changed structure to match template expectations
            'unassigned_breakdown': {},
            'total_assigned': 0,
            'total_unassigned': 0,
            'active_users_count': len(active_users),
            'success': True
        }
        
        # Se non ci sono utenti attivi, ritorna subito
        if not active_users:
            current_app.logger.warning("No active users found to calculate counts for")
            return jsonify(result)
        
        # Per ogni utente attivo, recupera TUTTI i contatti assegnati in una singola query
        for user in active_users:
            user_email = user['email']
            user_contacts = {
                'total': 0,
                'by_lifecycle': {}
            }
            
            current_app.logger.info(f"Processing user {user_email} with respond_io_id: {user.get('respond_io_id')}")
            
            try:
                # Rate limiting
                time.sleep(0.1)
                
                # Query singola per TUTTI i lifecycle
                filter_query = {
                    '$and': [
                        {'lifecycles': {'$in': target_lifecycles}},  # Tutti i lifecycle in una query
                        {'tags': {'$in': ['in_attesa']}},
                        {'assignedUserId': user['respond_io_id']}
                    ]
                }
                
                current_app.logger.debug(f"Querying ALL contacts for {user_email}")
                response = current_app.respond_io_client.list_contacts(
                    limit=500,
                    filters={'filter': filter_query}
                )
                
                # Processa i risultati e conta per lifecycle
                items = response.get('items', [])
                for item in items:
                    # Ottieni il lifecycle del contatto
                    contact_lifecycle = item.get('lifecycle')
                    if contact_lifecycle and contact_lifecycle in target_lifecycles:
                        if contact_lifecycle not in user_contacts['by_lifecycle']:
                            user_contacts['by_lifecycle'][contact_lifecycle] = 0
                        user_contacts['by_lifecycle'][contact_lifecycle] += 1
                        user_contacts['total'] += 1
                        result['total_assigned'] += 1
                
                current_app.logger.info(f"Found {user_contacts['total']} total contacts for {user_email}")
                    
            except Exception as e:
                current_app.logger.error(f"Error fetching contacts for {user_email}: {str(e)}")
                current_app.logger.exception("Full traceback:")
            
            result['user_breakdown'][user_email] = user_contacts
        
        # Recupera TUTTI i contatti non assegnati in una singola query
        current_app.logger.info("Fetching unassigned contacts...")
        try:
            time.sleep(0.1)
            
            # Query singola per TUTTI i lifecycle non assegnati
            filter_query = {
                '$and': [
                    {'lifecycles': {'$in': target_lifecycles}},  # Tutti i lifecycle
                    {'tags': {'$in': ['in_attesa']}},
                    {'assignedUserId': {'$eq': None}}  # Non assegnati
                ]
            }
            
            current_app.logger.debug(f"Querying ALL unassigned contacts")
            response = current_app.respond_io_client.list_contacts(
                limit=500,
                filters={'filter': filter_query}
            )
            
            # Processa i risultati e conta per lifecycle
            items = response.get('items', [])
            for item in items:
                contact_lifecycle = item.get('lifecycle')
                if contact_lifecycle and contact_lifecycle in target_lifecycles:
                    if contact_lifecycle not in result['unassigned_breakdown']:
                        result['unassigned_breakdown'][contact_lifecycle] = 0
                    result['unassigned_breakdown'][contact_lifecycle] += 1
                    result['total_unassigned'] += 1
            
            current_app.logger.info(f"Found {result['total_unassigned']} total unassigned contacts")
                
        except Exception as e:
            current_app.logger.error(f"Error fetching unassigned contacts: {str(e)}")
            current_app.logger.exception("Full traceback:")
        
        # Log final result summary
        current_app.logger.info(f"Calculation complete: {result['total_assigned']} assigned, {result['total_unassigned']} unassigned")
        current_app.logger.info(f"Result structure: {list(result.keys())}")
        
        # Return result with the structure expected by the template
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Error calculating real counts: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _get_active_users_with_real_counts():
    """
    Ottiene gli utenti attualmente attivi con i conteggi REALI dei contatti assegnati.
    Carica i dati direttamente dall'API rispettando i rate limits.
    """
    import time
    from flask import current_app
    
    # Query per ottenere l'ultimo stato di ogni utente
    subquery = db.session.query(
        RespondIOWorkTimestamp.user_id,
        func.max(RespondIOWorkTimestamp.timestamp).label('last_timestamp')
    ).group_by(RespondIOWorkTimestamp.user_id).subquery()
    
    # Ottieni gli stati correnti (solo working)
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
    ).all()
    
    active_users = []
    
    # Target lifecycles
    target_lifecycles = [
        'Nuova Lead',
        'Contrassegnato',
        'In Target', 
        'Link Da Inviare',
        'Link Inviato',
        'Prenotato'
    ]
    
    for state in current_states:
        user = User.query.get(state.user_id)
        if user and user.respond_io_profile:
            user_data = {
                'id': user.id,
                'respond_io_id': user.respond_io_profile.respond_io_id,
                'email': user.email,
                'full_name': user.full_name,
                'total_contacts': 0,
                'lifecycle_breakdown': {},
                'status_since': state.timestamp.isoformat()
            }
            
            # Carica i contatti assegnati a questo utente
            try:
                for lifecycle in target_lifecycles:
                    time.sleep(0.2)  # Rate limit: 5 req/sec
                    
                    filters = {
                        'lifecycles': [lifecycle],
                        'tags': ['in_attesa'],
                        'assignedUserId': user.respond_io_profile.respond_io_id,
                        'limit': 100
                    }
                    
                    result = current_app.respond_io_client.list_contacts(filters)
                    count = len(result.get('items', []))
                    
                    if count > 0:
                        user_data['lifecycle_breakdown'][lifecycle] = count
                        user_data['total_contacts'] += count
                        
            except Exception as e:
                current_app.logger.warning(f"Error loading contacts for {user.email}: {e}")
            
            active_users.append(user_data)
    
    return active_users


def _get_active_users_with_counts():
    """
    Ottiene gli utenti attualmente attivi con i conteggi dei contatti assegnati.
    VERSIONE LEGGERA - Non chiama API per evitare timeout
    """
    # Query per ottenere l'ultimo stato di ogni utente
    subquery = db.session.query(
        RespondIOWorkTimestamp.user_id,
        func.max(RespondIOWorkTimestamp.timestamp).label('last_timestamp')
    ).group_by(RespondIOWorkTimestamp.user_id).subquery()
    
    # Ottieni gli stati correnti (solo working)
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
    ).all()
    
    active_users = []
    
    for state in current_states:
        user = User.query.get(state.user_id)
        if user and user.respond_io_profile:
            # NON chiamiamo API qui per evitare timeout
            # Usiamo placeholder per ora
            active_users.append({
                'id': user.id,
                'respond_io_id': user.respond_io_profile.respond_io_id if user.respond_io_profile else None,
                'email': user.email,
                'full_name': user.full_name,
                'total_contacts': 0,  # Sarà popolato via AJAX
                'lifecycle_breakdown': {},  # Sarà popolato via AJAX
                'status_since': state.timestamp.isoformat()
            })
    
    return active_users


def _get_unassigned_waiting_contacts_real():
    """
    Ottiene il numero di contatti con tag "in_attesa" ma non assegnati.
    VERSIONE CON DATI REALI dall'API.
    """
    import time
    from flask import current_app
    
    target_lifecycles = [
        'Nuova Lead',
        'Contrassegnato',
        'In Target',
        'Link Da Inviare', 
        'Link Inviato',
        'Prenotato'
    ]
    
    total_unassigned = 0
    by_lifecycle = {}
    
    try:
        for lifecycle in target_lifecycles:
            time.sleep(0.2)  # Rate limit: 5 req/sec
            
            # Cerca contatti non assegnati con tag in_attesa
            filters = {
                'lifecycles': [lifecycle],
                'tags': ['in_attesa'],
                'assignedUserId': None,  # Non assegnati
                'limit': 100
            }
            
            result = current_app.respond_io_client.list_contacts(filters)
            count = len(result.get('items', []))
            
            if count > 0:
                by_lifecycle[lifecycle] = count
                total_unassigned += count
                
    except Exception as e:
        current_app.logger.warning(f"Error loading unassigned contacts: {e}")
    
    return {
        'total': total_unassigned,
        'by_lifecycle': by_lifecycle,
        'loading': False
    }


def _get_unassigned_waiting_contacts():
    """
    Ottiene il numero di contatti con tag "in_attesa" ma non assegnati.
    VERSIONE SEMPLIFICATA - Ritorna placeholder per evitare timeout
    """
    # Per ora ritorniamo dati placeholder
    # I dati reali verranno caricati via AJAX
    return {
        'total': 0,
        'by_lifecycle': {},
        'loading': True  # Indica che deve essere caricato via AJAX
    }


def _get_assignment_logs(filter_date):
    """
    Ottiene i log delle assegnazioni per una data specifica.
    """
    # Query logs del giorno
    logs = RespondIOAssignmentLog.query.filter(
        func.date(RespondIOAssignmentLog.started_at) == filter_date
    ).order_by(
        RespondIOAssignmentLog.started_at.desc()
    ).limit(100).all()
    
    log_entries = []
    for log in logs:
        # Determina il tipo di evento dal assignment_type
        event_type = 'unknown'
        trigger_user = None
        
        if log.assignment_type.startswith('timestamp_'):
            event_type = log.assignment_type.replace('timestamp_', '')
            if log.details and 'triggered_by' in log.details:
                trigger_user = log.details['triggered_by']
        
        log_entries.append({
            'id': log.id,
            'time': log.started_at.strftime('%H:%M:%S'),
            'type': log.assignment_type,
            'event_type': event_type,
            'trigger_user': trigger_user,
            'total_contacts': log.total_contacts,
            'assigned': log.contacts_assigned,
            'failed': log.contacts_failed,
            'status': log.status,
            'duration': log.duration_seconds,
            'distribution': log.assigned_to_users or [],
            'error': log.error_message
        })
    
    return log_entries


def _get_lifecycle_distribution_real(active_users):
    """
    Calcola la distribuzione dei contatti per lifecycle tra gli utenti attivi.
    Usa i dati già caricati dagli utenti attivi.
    """
    # Target lifecycles
    target_lifecycles = [
        'Nuova Lead',
        'Contrassegnato',
        'In Target',
        'Link Da Inviare',
        'Link Inviato',
        'Prenotato'
    ]
    
    distribution = {}
    
    for lifecycle in target_lifecycles:
        distribution[lifecycle] = {
            'total': 0,
            'users': {}
        }
        
        for user in active_users:
            count = user['lifecycle_breakdown'].get(lifecycle, 0)
            if count > 0:
                distribution[lifecycle]['total'] += count
                distribution[lifecycle]['users'][user['email']] = count
    
    return distribution


def _get_lifecycle_distribution(active_users):
    """
    Calcola la distribuzione dei contatti per lifecycle tra gli utenti attivi.
    """
    # Target lifecycles
    target_lifecycles = [
        'Nuova Lead',
        'Contrassegnato',
        'In Target',
        'Link Da Inviare',
        'Link Inviato',
        'Prenotato'
    ]
    
    distribution = {}
    
    for lifecycle in target_lifecycles:
        distribution[lifecycle] = {
            'total': 0,
            'users': {}
        }
        
        for user in active_users:
            count = user['lifecycle_breakdown'].get(lifecycle, 0)
            if count > 0:
                distribution[lifecycle]['total'] += count
                distribution[lifecycle]['users'][user['email']] = count
    
    return distribution


def _get_timeline_events(filter_date):
    """
    Costruisce una timeline degli eventi di timbratura e assegnazione del giorno.
    """
    events = []
    
    # 1. Eventi di timbratura
    timestamps = RespondIOWorkTimestamp.query.filter(
        func.date(RespondIOWorkTimestamp.timestamp) == filter_date
    ).order_by(RespondIOWorkTimestamp.timestamp).all()
    
    for ts in timestamps:
        user = User.query.get(ts.user_id)
        if user:
            event_desc = {
                'start': f"{user.full_name} ha iniziato il turno",
                'pause_start': f"{user.full_name} è andato in pausa",
                'pause_end': f"{user.full_name} è tornato dalla pausa",
                'end': f"{user.full_name} ha terminato il turno"
            }.get(ts.timestamp_type, f"{user.full_name} - {ts.timestamp_type}")
            
            events.append({
                'time': ts.timestamp.strftime('%H:%M:%S'),
                'type': 'timestamp',
                'subtype': ts.timestamp_type,
                'description': event_desc,
                'user': user.full_name
            })
    
    # 2. Eventi di assegnazione
    assignments = RespondIOAssignmentLog.query.filter(
        func.date(RespondIOAssignmentLog.started_at) == filter_date
    ).order_by(RespondIOAssignmentLog.started_at).all()
    
    for log in assignments:
        trigger = "Sistema"
        if log.details and 'triggered_by' in log.details:
            trigger_user = User.query.filter_by(email=log.details['triggered_by']).first()
            if trigger_user:
                trigger = trigger_user.full_name
        
        events.append({
            'time': log.started_at.strftime('%H:%M:%S'),
            'type': 'assignment',
            'subtype': log.assignment_type,
            'description': f"Assegnati {log.contacts_assigned}/{log.total_contacts} contatti",
            'user': trigger,
            'status': log.status
        })
    
    # Ordina per tempo
    events.sort(key=lambda x: x['time'])
    
    return events


@bp.route('/assignment/api/current-distribution')
@login_required
def api_current_distribution():
    """API per ottenere la distribuzione corrente in real-time - VERSIONE LEGGERA"""
    
    # Versione semplificata che non chiama API pesanti
    active_users = _get_active_users_with_counts()
    
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'active_users': active_users,
        'summary': {
            'active_agents': len(active_users),
            'status': 'simplified'  # Indica che è la versione semplificata
        }
    })


@bp.route('/assignment/api/contact-counts')
@login_required  
def api_contact_counts():
    """API separata per caricare i conteggi contatti (chiamata pesante)"""
    
    try:
        from flask import current_app
        import time
        
        # Ottieni gli utenti attivi
        active_users = _get_active_users_with_counts()
        
        if not active_users:
            return jsonify({
                'success': True,
                'data': {
                    'total_assigned': 0,
                    'total_unassigned': 0,
                    'by_user': {},
                    'by_lifecycle': {}
                }
            })
        
        # Prepara i dati per il conteggio
        total_assigned = 0
        total_unassigned = 0
        by_user = {}
        by_lifecycle = {}
        
        # Target lifecycles
        target_lifecycles = [
            'Nuova Lead',
            'Contrassegnato', 
            'In Target',
            'Link Da Inviare',
            'Link Inviato',
            'Prenotato'
        ]
        
        # Ottieni contatti con tag "in_attesa" per lifecycle target
        # Rate limit: 5 req/sec per list contacts
        for lifecycle in target_lifecycles:
            try:
                # Delay di 200ms tra richieste per rispettare rate limit (5/sec)
                time.sleep(0.2)
                
                # Ottieni contatti per questo lifecycle con tag in_attesa
                filters = {
                    'lifecycles': [lifecycle],
                    'tags': ['in_attesa'],
                    'limit': 100  # Limitiamo per velocità
                }
                
                result = current_app.respond_io_client.list_contacts(filters)
                contacts = result.get('items', [])
                
                # Conta assegnati e non assegnati
                lifecycle_assigned = 0
                lifecycle_unassigned = 0
                
                for contact in contacts:
                    assignee = contact.get('assignedUserId')
                    if assignee:
                        lifecycle_assigned += 1
                        # Trova l'utente assegnato tra gli attivi
                        for user in active_users:
                            if user.get('respond_io_id') == assignee:
                                email = user['email']
                                if email not in by_user:
                                    by_user[email] = 0
                                by_user[email] += 1
                                break
                    else:
                        lifecycle_unassigned += 1
                
                by_lifecycle[lifecycle] = {
                    'assigned': lifecycle_assigned,
                    'unassigned': lifecycle_unassigned,
                    'total': len(contacts)
                }
                
                total_assigned += lifecycle_assigned
                total_unassigned += lifecycle_unassigned
                
            except Exception as e:
                current_app.logger.warning(f"Error getting contacts for {lifecycle}: {e}")
                by_lifecycle[lifecycle] = {
                    'assigned': 0,
                    'unassigned': 0,
                    'total': 0,
                    'error': str(e)
                }
        
        return jsonify({
            'success': True,
            'data': {
                'total_assigned': total_assigned,
                'total_unassigned': total_unassigned,
                'by_user': by_user,
                'by_lifecycle': by_lifecycle,
                'active_users': len(active_users)
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting contact counts: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/assignment/api/logs/<string:date>')
@login_required
def api_assignment_logs(date):
    """API per ottenere i log di una data specifica"""
    
    try:
        filter_date = datetime.strptime(date, '%Y-%m-%d').date()
    except:
        return jsonify({'error': 'Invalid date format'}), 400
    
    logs = _get_assignment_logs(filter_date)
    
    return jsonify({
        'date': date,
        'logs': logs,
        'total': len(logs)
    })


@bp.route('/assignment/api/trigger-redistribution', methods=['POST'])
@login_required
def api_trigger_redistribution():
    """
    API per triggerare manualmente una redistribuzione (solo per admin).
    """
    # Verifica permessi admin
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        from flask import current_app
        service = current_app.timestamp_assignment_service
        
        # Simula un evento di redistribuzione totale
        active_users = _get_active_users_with_counts()
        
        if not active_users:
            return jsonify({
                'success': False,
                'message': 'Nessun utente attivo trovato'
            })
        
        # Triggera redistribuzione come se fosse un nuovo utente che entra
        first_active = User.query.get(active_users[0]['id'])
        service.handle_timestamp_event(first_active, 'start')
        
        return jsonify({
            'success': True,
            'message': f'Redistribuzione triggerata per {len(active_users)} utenti attivi'
        })
        
    except Exception as e:
        current_app.logger.error(f"Manual redistribution failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500