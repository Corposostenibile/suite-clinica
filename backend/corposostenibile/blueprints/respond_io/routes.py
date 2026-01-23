"""
Route per dashboard Respond.io - versione semplificata solo metriche
"""

from datetime import datetime, date, timedelta
from collections import defaultdict
from flask import render_template, request, jsonify, flash, redirect, url_for, current_app, session
from flask_login import login_required
from sqlalchemy import func, and_, or_
from corposostenibile.extensions import db
from corposostenibile.models import (
    RESPOND_IO_CHANNELS,
    RespondIOFollowupQueue,
    RespondIOFollowupConfig,
    RespondIOLifecycleChange,
    FOLLOWUP_ENABLED_LIFECYCLES
)
from . import bp
from .services import FunnelAnalyticsService


@bp.route('/test-api')
@login_required
def test_api():
    """Route di test per verificare la connessione API"""
    try:
        from .client import RespondIOClient
        import requests
        
        # Test manuale diretto con requests
        api_token = current_app.config.get('RESPOND_IO_API_TOKEN')
        
        # Facciamo una chiamata diretta per debug
        url = "https://api.respond.io/v2/contact/list?limit=1"
        headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        body = {
            "search": "",
            "filter": {
                "$and": []
            },
            "timezone": "Europe/Rome"  # RICHIESTO!
        }
        
        response = requests.post(url, json=body, headers=headers)
        
        return jsonify({
            'success': response.status_code == 200,
            'status_code': response.status_code,
            'response_text': response.text,
            'response_headers': dict(response.headers),
            'request_body': body,
            'request_url': url
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard principale con aggregazione contatti per lifecycle e canale"""
    
    # Parametri dalla query string
    max_contacts = request.args.get('max_contacts', type=int)  # Limite per testing
    
    try:
        # Verifica configurazione API
        if not current_app.config.get('RESPOND_IO_API_TOKEN'):
            raise ValueError("RESPOND_IO_API_TOKEN non configurato. Verifica il file .env")
        
        # Inizializza client
        from .client import RespondIOClient
        client = RespondIOClient(current_app.config)
        
        current_app.logger.info(f"Starting to fetch ALL contacts (max: {max_contacts or 'unlimited'})")
        
        # Recupera TUTTI i contatti
        all_contacts = []
        cursor_id = None
        
        while True:
            response = client.list_contacts(limit=100, cursor_id=cursor_id)
            contacts = response.get('items', [])
            
            if not contacts:
                break
                
            all_contacts.extend(contacts)
            current_app.logger.info(f"Fetched batch: {len(contacts)} contacts (total so far: {len(all_contacts)})")
            
            # Check for max limit
            if max_contacts and len(all_contacts) >= max_contacts:
                all_contacts = all_contacts[:max_contacts]
                break
            
            # Get next cursor
            pagination = response.get('pagination', {})
            next_url = pagination.get('next')
            if not next_url:
                break
                
            # Extract cursorId from URL
            import re
            cursor_match = re.search(r'cursorId=(\d+)', next_url)
            if cursor_match:
                cursor_id = cursor_match.group(1)
            else:
                break
        
        current_app.logger.info(f"Successfully fetched {len(all_contacts)} contacts from Respond.io")
        
        # Recupera i nomi dei canali dalla cache locale (RespondIOContactChannel)
        from corposostenibile.models import RespondIOContactChannel
        
        # Statistiche per debug
        channels_found = 0
        channels_not_found = 0
        
        # Dizionario per mappare i canali più comuni (fallback)
        # Questi sono i canali WhatsApp tipici che avete
        channel_fallback = {
            '+393357623716': 'Sciaudone Matteo',
            '+393889991117': 'Cristiano Fallai',
            '+393517815816': 'Celestino Breccione Mattucci',
            # Aggiungi altri mapping se necessari
        }
        
        # NON assegnare canali qui - lo faremo dopo solo per i contatti filtrati
        # Manteniamo il codice per backward compatibility ma non assegniamo default
        for contact in all_contacts:
            contact_id = str(contact.get('id'))
            channel_name, channel_source = RespondIOContactChannel.get_channel(contact_id)
            
            if channel_name:
                # Usa il nome dalla cache
                contact['primary_channel'] = channel_name
                contact['channel_source'] = channel_source or channel_name
                channels_found += 1
            else:
                # Non assegnare un default qui - lo faremo dopo per i contatti filtrati
                channels_not_found += 1
        
        current_app.logger.info(f"Channels found in cache: {channels_found}, not found: {channels_not_found}")
        
        # Aggregazione dati
        stats = {
            'total_contacts': len(all_contacts),
            'by_lifecycle': defaultdict(int),
            'by_channel': defaultdict(int),
            'by_status': defaultdict(int),
            'by_lifecycle_and_channel': defaultdict(lambda: defaultdict(int)),
            'contacts_with_tags': 0,
            'contacts_assigned': 0,
            'open_assigned': 0,  # Assegnati tra le conversazioni aperte
            'open_in_target_lifecycles': 0,  # Conversazioni aperte nei 4 lifecycle target
            'open_assigned_in_target': 0  # Aperte e assegnate nei 4 lifecycle target
        }
        
        # I 4 lifecycle che ci interessano
        target_lifecycles_set = {'Contrassegnato', 'In Target', 'Link Da Inviare', 'Link Inviato'}
        
        # Lista dei contatti che mostreremo (con tag di attesa)
        contacts_to_show = []
        
        # Processa ogni contatto
        for contact in all_contacts:
            # Lifecycle
            lifecycle = contact.get('lifecycle') or 'Nessun Lifecycle'
            stats['by_lifecycle'][lifecycle] += 1
            
            # Canale
            channel = contact.get('primary_channel', 'Unknown')
            stats['by_channel'][channel] += 1
            
            # Status conversazione
            status = contact.get('status', 'unknown')
            stats['by_status'][status] += 1
            
            # Lifecycle + Canale (matrice)
            stats['by_lifecycle_and_channel'][lifecycle][channel] += 1
            
            # Tags
            if contact.get('tags'):
                stats['contacts_with_tags'] += 1
            
            # Assegnazioni
            if contact.get('assignee'):
                stats['contacts_assigned'] += 1
                # Se è assegnato E aperto
                if status == 'open':
                    stats['open_assigned'] += 1
                    # Se è anche in uno dei 4 lifecycle target
                    if lifecycle in target_lifecycles_set:
                        stats['open_assigned_in_target'] += 1
            
            # Conta conversazioni aperte nei 4 lifecycle target
            if status == 'open' and lifecycle in target_lifecycles_set:
                stats['open_in_target_lifecycles'] += 1
        
        # Converti defaultdict in dict normale per template
        stats['by_lifecycle'] = dict(stats['by_lifecycle'])
        stats['by_channel'] = dict(stats['by_channel'])
        stats['by_status'] = dict(stats['by_status'])
        stats['by_lifecycle_and_channel'] = {
            k: dict(v) for k, v in stats['by_lifecycle_and_channel'].items()
        }
        
        # SOLO i 4 lifecycle che ci interessano, nell'ordine esatto
        target_lifecycles = [
            'Contrassegnato',
            'In Target',
            'Link Da Inviare',
            'Link Inviato'
        ]
        
        # Crea nuove statistiche solo per conversazioni OPEN nei 4 lifecycle target CON TAG "da_rispondere"
        open_by_lifecycle = {}
        open_by_lifecycle_and_channel = defaultdict(lambda: defaultdict(int))
        total_open_in_target = 0
        total_waiting_in_target = 0  # Nuovo contatore per quelle con tag da_rispondere
        
        # Conta solo le conversazioni OPEN per ogni lifecycle target
        for contact in all_contacts:
            if contact.get('status') == 'open':
                lifecycle = contact.get('lifecycle') or 'Nessun Lifecycle'
                if lifecycle in target_lifecycles:
                    # NUOVO FILTRO: controlla se ha il tag "in_attesa" O "da_rispondere"
                    tags = contact.get('tags', [])
                    has_waiting_tag = 'in_attesa' in tags or 'da_rispondere' in tags
                    
                    if has_waiting_tag:  # SOLO se ha uno dei tag di attesa
                        # Aggiungi a contacts_to_show per recuperare i canali dopo
                        contacts_to_show.append(contact)
                        channel = contact.get('primary_channel', 'Unknown')
                        # Incrementa contatori
                        if lifecycle not in open_by_lifecycle:
                            open_by_lifecycle[lifecycle] = 0
                        open_by_lifecycle[lifecycle] += 1
                        open_by_lifecycle_and_channel[lifecycle][channel] += 1
                        total_waiting_in_target += 1
                    
                    total_open_in_target += 1  # Conta tutti per riferimento
        
        # Recupera i canali reali solo per i contatti che mostreremo
        current_app.logger.info(f"Recupero canali per {len(contacts_to_show)} contatti filtrati...")
        
        # Reset delle statistiche per canale per ricalcolarle con i nomi corretti
        open_by_lifecycle_and_channel = defaultdict(lambda: defaultdict(int))
        
        # Limita le chiamate API per evitare timeout
        max_channel_lookups = 100  # Limita a 100 contatti per evitare timeout
        
        for idx, contact in enumerate(contacts_to_show):
            contact_id = str(contact.get('id'))
            lifecycle = contact.get('lifecycle')
            
            # Se abbiamo già recuperato troppi canali, usa il fallback
            if idx < max_channel_lookups:
                try:
                    # Recupera i canali del contatto dall'API
                    channels_response = client.get_contact_channels(contact_id, limit=10)
                    channels = channels_response.get('items', [])
                    
                    if channels:
                        # Usa il primo canale disponibile (di solito c'è solo uno)
                        channel_name = channels[0].get('name', 'Senza Nome')
                        contact['primary_channel'] = channel_name
                        contact['channel_source'] = channels[0].get('source', 'unknown')
                        current_app.logger.debug(f"Contatto {contact_id}: canale '{channel_name}'")
                    else:
                        # Nessun canale trovato
                        contact['primary_channel'] = 'Nessun Canale'
                        contact['channel_source'] = 'none'
                        
                except Exception as e:
                    current_app.logger.warning(f"Errore recupero canali per contatto {contact_id}: {e}")
                    # Fallback se l'API fallisce
                    phone = contact.get('phone')
                    if phone and phone in channel_fallback:
                        contact['primary_channel'] = channel_fallback[phone]
                        contact['channel_source'] = phone
                    else:
                        contact['primary_channel'] = 'Nessun Canale'
                        contact['channel_source'] = 'none'
            else:
                # Usa fallback per i contatti oltre il limite
                phone = contact.get('phone')
                if phone and phone in channel_fallback:
                    contact['primary_channel'] = channel_fallback[phone]
                    contact['channel_source'] = phone
                else:
                    contact['primary_channel'] = 'Canale Non Verificato'
                    contact['channel_source'] = 'not_checked'
            
            # Aggiorna le statistiche con il nome corretto del canale
            channel = contact.get('primary_channel', 'Unknown')
            open_by_lifecycle_and_channel[lifecycle][channel] += 1
        
        current_app.logger.info(f"Canali recuperati. Statistiche per lifecycle e canale: {dict(open_by_lifecycle_and_channel)}")
        
        # Assicura che tutti i lifecycle target siano presenti (anche con 0)
        for lc in target_lifecycles:
            if lc not in open_by_lifecycle:
                open_by_lifecycle[lc] = 0
        
        # Sostituisci le statistiche con quelle filtrate per OPEN + da_rispondere
        stats['by_lifecycle'] = open_by_lifecycle
        stats['by_lifecycle_and_channel'] = dict(open_by_lifecycle_and_channel)
        stats['total_in_target_lifecycles'] = total_waiting_in_target  # USA IL NUOVO TOTALE
        stats['total_open_in_target'] = total_open_in_target  # Mantieni anche il totale generale per riferimento
        stats['waiting_percentage'] = round((total_waiting_in_target / total_open_in_target * 100), 1) if total_open_in_target > 0 else 0
        
        # Calcola percentuali
        total = stats['total_contacts']
        if total > 0:
            # Percentuali dei lifecycle basate SOLO sulle conversazioni con tag da_rispondere
            if total_waiting_in_target > 0:
                stats['percentages'] = {
                    'by_lifecycle': {k: round(v/total_waiting_in_target*100, 1) for k, v in stats['by_lifecycle'].items()},
                    'by_channel': {k: round(v/total*100, 1) for k, v in stats['by_channel'].items()},
                    'by_status': {k: round(v/total*100, 1) for k, v in stats['by_status'].items()}
                }
            else:
                stats['percentages'] = {
                    'by_lifecycle': {k: 0 for k in stats['by_lifecycle'].keys()},
                    'by_channel': {k: round(v/total*100, 1) for k, v in stats['by_channel'].items()},
                    'by_status': {k: round(v/total*100, 1) for k, v in stats['by_status'].items()}
                }
        else:
            stats['percentages'] = {'by_lifecycle': {}, 'by_channel': {}, 'by_status': {}}
        
        # Top channels - Usa i canali dai contatti filtrati con i tag di attesa
        channel_counts = defaultdict(int)
        for lifecycle_channels in stats['by_lifecycle_and_channel'].values():
            for channel, count in lifecycle_channels.items():
                channel_counts[channel] += count
        
        stats['top_channels'] = sorted(
            channel_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]
        
        return render_template('respond_io/dashboard.html', 
                             stats=stats,
                             last_update=datetime.now())
        
    except Exception as e:
        current_app.logger.error(f"Error loading dashboard: {e}")
        flash(f"Errore nel caricamento della dashboard: {str(e)}", 'error')
        return render_template('respond_io/dashboard.html', 
                             stats=None,
                             error=str(e))


@bp.route('/dashboard-cambi')
@login_required
def dashboard_cambi():
    """Dashboard per visualizzare i cambi di stato/lifecycle"""
    
    # Parametri filtro - date range diretto
    start_date_str = request.args.get('start_date', date.today().isoformat())
    end_date_str = request.args.get('end_date', date.today().isoformat())
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except:
        start_date = date.today()
        end_date = date.today()
    
    # Assicura che start_date <= end_date
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    
    # Lifecycle principali e secondari
    main_lifecycles = [
        'Nuova Lead',
        'Contrassegnato', 
        'In Target',
        'Link Da Inviare',
        'Link Inviato',
        'Prenotato'
    ]
    
    secondary_lifecycles = [
        'Non In Target',
        'Non in Target',  # Variante con 'in' minuscolo
        'Under',
        'Prenotato Non In Target'
    ]
    
    # Query per ottenere i cambi di stato nel periodo
    changes_query = RespondIOLifecycleChange.query.filter(
        and_(
            func.date(RespondIOLifecycleChange.changed_at) >= start_date,
            func.date(RespondIOLifecycleChange.changed_at) <= end_date
        )
    )
    
    all_changes = changes_query.all()
    
    # Statistiche aggregate
    stats = {
        'total_changes': len(all_changes),
        'by_lifecycle': defaultdict(int),
        'transitions': defaultdict(int),
        'by_channel': defaultdict(int),
        'main_lifecycles': {},
        'secondary_lifecycles': {},
        'daily_breakdown': defaultdict(lambda: defaultdict(int)),
        'bookings_by_channel': defaultdict(int)  # Nuova struttura per prenotazioni per canale
    }
    
    # Aggiungi struttura per lifecycle per canale
    stats['lifecycle_by_channel'] = defaultdict(lambda: defaultdict(int))
    
    # Processa ogni cambio
    for change in all_changes:
        # Conta arrivi per lifecycle
        to_lc = change.to_lifecycle
        stats['by_lifecycle'][to_lc] += 1
        
        # Conta transizioni specifiche
        transition = f"{change.from_lifecycle or 'Nuovo'} → {to_lc}"
        stats['transitions'][transition] += 1
        
        # Per canale
        channel = change.channel_name or 'Canale Sconosciuto'
        stats['by_channel'][channel] += 1
        
        # Lifecycle per canale (per il nuovo grafico)
        stats['lifecycle_by_channel'][channel][to_lc] += 1
        
        # Conta prenotazioni per canale (SOLO "Prenotato", non "Prenotato Non In Target")
        if to_lc == 'Prenotato':
            stats['bookings_by_channel'][channel] += 1
        
        # Breakdown giornaliero
        change_date = change.changed_at.date()
        stats['daily_breakdown'][change_date.isoformat()][to_lc] += 1
        
        # Separa main e secondary
        if to_lc in main_lifecycles:
            if to_lc not in stats['main_lifecycles']:
                stats['main_lifecycles'][to_lc] = {'total': 0, 'transitions': defaultdict(int)}
            stats['main_lifecycles'][to_lc]['total'] += 1
            stats['main_lifecycles'][to_lc]['transitions'][change.from_lifecycle or 'Nuovo'] += 1
        elif to_lc in secondary_lifecycles:
            if to_lc not in stats['secondary_lifecycles']:
                stats['secondary_lifecycles'][to_lc] = {'total': 0, 'transitions': defaultdict(int)}
            stats['secondary_lifecycles'][to_lc]['total'] += 1
            stats['secondary_lifecycles'][to_lc]['transitions'][change.from_lifecycle or 'Nuovo'] += 1
    
    # Ordina lifecycle principali secondo l'ordine definito
    ordered_main = {}
    for lc in main_lifecycles:
        if lc in stats['main_lifecycles']:
            ordered_main[lc] = stats['main_lifecycles'][lc]
        else:
            ordered_main[lc] = {'total': 0, 'transitions': {}}
    stats['main_lifecycles'] = ordered_main
    
    # Ordina lifecycle secondari e unifica le varianti di "Non In/in Target"
    ordered_secondary = {}
    
    # Unifica le varianti di "Non In Target"
    non_in_target_total = {'total': 0, 'transitions': defaultdict(int)}
    for variant in ['Non In Target', 'Non in Target']:
        if variant in stats['secondary_lifecycles']:
            non_in_target_total['total'] += stats['secondary_lifecycles'][variant]['total']
            for from_lc, count in stats['secondary_lifecycles'][variant]['transitions'].items():
                non_in_target_total['transitions'][from_lc] += count
    
    # Aggiungi al dizionario ordinato con nome unificato
    if non_in_target_total['total'] > 0:
        ordered_secondary['Non In Target'] = {
            'total': non_in_target_total['total'],
            'transitions': dict(non_in_target_total['transitions'])
        }
    else:
        ordered_secondary['Non In Target'] = {'total': 0, 'transitions': {}}
    
    # Aggiungi gli altri lifecycle secondari
    for lc in ['Under', 'Prenotato Non In Target']:
        if lc in stats['secondary_lifecycles']:
            ordered_secondary[lc] = stats['secondary_lifecycles'][lc]
        else:
            ordered_secondary[lc] = {'total': 0, 'transitions': {}}
    stats['secondary_lifecycles'] = ordered_secondary
    
    # Converti defaultdict in dict normale
    stats['by_lifecycle'] = dict(stats['by_lifecycle'])
    stats['transitions'] = dict(stats['transitions'])
    stats['by_channel'] = dict(stats['by_channel'])
    stats['daily_breakdown'] = {k: dict(v) for k, v in stats['daily_breakdown'].items()}
    stats['lifecycle_by_channel'] = {k: dict(v) for k, v in stats['lifecycle_by_channel'].items()}
    stats['bookings_by_channel'] = dict(stats['bookings_by_channel'])
    
    # Top transizioni
    stats['top_transitions'] = sorted(
        stats['transitions'].items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    # Top canali
    stats['top_channels'] = sorted(
        stats['by_channel'].items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]
    
    # Calcola numero di giorni nel periodo
    days_in_period = (end_date - start_date).days + 1
    
    # Calcola media nuove lead per giorno della settimana (su TUTTI i dati storici)
    from sqlalchemy import extract
    weekday_stats = defaultdict(lambda: {'count': 0, 'days': set()})
    
    # Query per ottenere TUTTE le nuove lead storiche
    all_new_leads = RespondIOLifecycleChange.query.filter(
        RespondIOLifecycleChange.to_lifecycle == 'Nuova Lead'
    ).all()
    
    # Conta per giorno della settimana
    for lead in all_new_leads:
        weekday = lead.changed_at.weekday()  # 0=Lunedì, 6=Domenica
        date_only = lead.changed_at.date()
        weekday_stats[weekday]['count'] += 1
        weekday_stats[weekday]['days'].add(date_only)
    
    # Calcola medie
    weekday_averages = {}
    weekday_names = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
    
    for day_num in range(7):
        if day_num in weekday_stats:
            unique_days = len(weekday_stats[day_num]['days'])
            if unique_days > 0:
                weekday_averages[weekday_names[day_num]] = round(weekday_stats[day_num]['count'] / unique_days, 1)
            else:
                weekday_averages[weekday_names[day_num]] = 0
        else:
            weekday_averages[weekday_names[day_num]] = 0
    
    stats['weekday_averages'] = weekday_averages
    
    return render_template('respond_io/dashboard_cambi.html',
                         stats=stats,
                         start_date=start_date,
                         end_date=end_date,
                         days_in_period=days_in_period,
                         main_lifecycles=main_lifecycles,
                         secondary_lifecycles=secondary_lifecycles,
                         date=date,  # Pass date class for template
                         timedelta=timedelta)  # Pass timedelta class for template


# API routes temporaneamente disabilitate - saranno ricostruite
# Le route per follow-up rimangono intatte sotto


# ========================= FOLLOW-UP SYSTEM ROUTES =========================

@bp.route('/followup/dashboard')
@login_required
def followup_dashboard():
    """Dashboard per monitoraggio follow-up"""
    
    # Statistiche generali
    from sqlalchemy import func
    import pytz
    
    stats = {
        'pending': RespondIOFollowupQueue.query.filter_by(status='pending').count(),
        'sent_today': RespondIOFollowupQueue.query.filter(
            RespondIOFollowupQueue.status == 'sent',
            func.date(RespondIOFollowupQueue.sent_at) == date.today()
        ).count(),
        'cancelled_today': RespondIOFollowupQueue.query.filter(
            RespondIOFollowupQueue.status == 'cancelled',
            func.date(RespondIOFollowupQueue.cancelled_at) == date.today()
        ).count(),
        'failed_today': RespondIOFollowupQueue.query.filter(
            RespondIOFollowupQueue.status == 'failed',
            func.date(RespondIOFollowupQueue.updated_at) == date.today()
        ).count()
    }
    
    # Queue pending
    pending_followups = RespondIOFollowupQueue.query.filter_by(
        status='pending'
    ).order_by(RespondIOFollowupQueue.scheduled_at).limit(20).all()
    
    # Converti orari UTC in ora italiana per visualizzazione
    rome_tz = pytz.timezone('Europe/Rome')
    for followup in pending_followups:
        # Il database salva in UTC, convertiamo per la visualizzazione
        followup.scheduled_at_rome = pytz.utc.localize(followup.scheduled_at).astimezone(rome_tz)
        # Se c'è un orario originale (posticipato per quiet hours), convertilo anche
        if followup.original_scheduled_at:
            followup.original_scheduled_at_rome = pytz.utc.localize(followup.original_scheduled_at).astimezone(rome_tz)
        
        # Ottieni il lifecycle ATTUALE del contatto
        last_change = RespondIOLifecycleChange.query.filter_by(
            contact_id=str(followup.contact_id)
        ).order_by(RespondIOLifecycleChange.changed_at.desc()).first()
        
        if last_change:
            followup.current_lifecycle = last_change.to_lifecycle
        else:
            # Se non troviamo cambiamenti, usa quello salvato
            followup.current_lifecycle = followup.lifecycle
    
    # Configurazioni
    configs = RespondIOFollowupConfig.query.all()
    
    # Statistiche per lifecycle
    lifecycle_stats = db.session.query(
        RespondIOFollowupQueue.lifecycle,
        RespondIOFollowupQueue.status,
        func.count(RespondIOFollowupQueue.id).label('count')
    ).group_by(
        RespondIOFollowupQueue.lifecycle,
        RespondIOFollowupQueue.status
    ).all()
    
    # Organizza stats per lifecycle
    stats_by_lifecycle = {}
    for lifecycle, status, count in lifecycle_stats:
        if lifecycle not in stats_by_lifecycle:
            stats_by_lifecycle[lifecycle] = {}
        stats_by_lifecycle[lifecycle][status] = count
    
    return render_template('respond_io/followup_dashboard.html',
                         stats=stats,
                         pending_followups=pending_followups,
                         configs=configs,
                         stats_by_lifecycle=stats_by_lifecycle,
                         lifecycles=FOLLOWUP_ENABLED_LIFECYCLES)


@bp.route('/api/followup/config', methods=['GET', 'POST'])
@login_required
def api_followup_config():
    """API per gestire configurazioni follow-up"""
    
    if request.method == 'GET':
        configs = RespondIOFollowupConfig.query.all()
        return jsonify([{
            'id': c.id,
            'lifecycle': c.lifecycle,
            'enabled': c.enabled,
            'delay_hours': c.delay_hours,
            'message_text': c.message_text,
            'template_name': c.template_name,
            'tag_waiting': c.tag_waiting,
            'tag_sent': c.tag_sent,
            'total_scheduled': c.total_scheduled,
            'total_sent': c.total_sent,
            'total_cancelled': c.total_cancelled
        } for c in configs])
    
    elif request.method == 'POST':
        data = request.get_json()
        lifecycle = data.get('lifecycle')
        
        if lifecycle not in FOLLOWUP_ENABLED_LIFECYCLES:
            return jsonify({'error': 'Invalid lifecycle'}), 400
        
        config = RespondIOFollowupConfig.query.filter_by(lifecycle=lifecycle).first()
        if not config:
            config = RespondIOFollowupConfig(lifecycle=lifecycle)
            db.session.add(config)
        
        # Aggiorna configurazione
        config.enabled = data.get('enabled', config.enabled)
        config.delay_hours = data.get('delay_hours', config.delay_hours)
        config.message_text = data.get('message_text', config.message_text)
        config.template_name = data.get('template_name', config.template_name)
        config.tag_waiting = data.get('tag_waiting', config.tag_waiting)
        config.tag_sent = data.get('tag_sent', config.tag_sent)
        
        db.session.commit()
        
        return jsonify({'status': 'success', 'id': config.id})


@bp.route('/api/followup/queue/<int:queue_id>', methods=['DELETE'])
@login_required
def api_cancel_followup(queue_id):
    """Cancella un follow-up pending"""
    
    followup = RespondIOFollowupQueue.query.get_or_404(queue_id)
    
    if followup.status != 'pending':
        return jsonify({'error': 'Can only cancel pending follow-ups'}), 400
    
    followup.status = 'cancelled'
    followup.cancelled_at = datetime.utcnow()
    followup.error_message = 'Manually cancelled from dashboard'
    
    db.session.commit()
    
    flash(f'Follow-up per contatto {followup.contact_id} cancellato', 'success')
    return jsonify({'status': 'success'})


@bp.route('/api/followup/stats')
@login_required
def api_followup_stats():
    """Statistiche follow-up per grafici"""
    
    days = request.args.get('days', 7, type=int)
    start_date = date.today() - timedelta(days=days)
    
    # Query statistiche giornaliere
    from sqlalchemy import func
    
    daily_stats = db.session.query(
        func.date(RespondIOFollowupQueue.created_at).label('date'),
        RespondIOFollowupQueue.status,
        func.count(RespondIOFollowupQueue.id).label('count')
    ).filter(
        RespondIOFollowupQueue.created_at >= start_date
    ).group_by(
        'date',
        RespondIOFollowupQueue.status
    ).all()
    
    # Organizza per data
    stats_by_date = {}
    current = start_date
    while current <= date.today():
        stats_by_date[current.isoformat()] = {
            'pending': 0,
            'sent': 0,
            'cancelled': 0,
            'failed': 0
        }
        current += timedelta(days=1)
    
    for date_val, status, count in daily_stats:
        if date_val:
            date_str = date_val.isoformat()
            if date_str in stats_by_date:
                stats_by_date[date_str][status] = count
    
    return jsonify({
        'dates': list(stats_by_date.keys()),
        'data': stats_by_date
    })


@bp.route('/api/followup/duplicates')
@login_required
def api_followup_duplicates():
    """API per rilevare duplicati nel sistema follow-up"""
    
    from sqlalchemy import func
    
    # Duplicati già inviati (stesso contact, stesso giorno, multiple volte)
    sent_duplicates = db.session.query(
        RespondIOFollowupQueue.contact_id,
        func.date(RespondIOFollowupQueue.sent_at).label('date'),
        func.count(RespondIOFollowupQueue.id).label('count')
    ).filter(
        RespondIOFollowupQueue.status == 'sent',
        RespondIOFollowupQueue.sent_at.isnot(None)
    ).group_by(
        RespondIOFollowupQueue.contact_id,
        func.date(RespondIOFollowupQueue.sent_at)
    ).having(
        func.count(RespondIOFollowupQueue.id) > 1
    ).all()
    
    # Duplicati pending/processing (potenziali futuri duplicati)
    pending_duplicates = db.session.query(
        RespondIOFollowupQueue.contact_id,
        RespondIOFollowupQueue.lifecycle,
        func.count(RespondIOFollowupQueue.id).label('count')
    ).filter(
        RespondIOFollowupQueue.status.in_(['pending', 'processing'])
    ).group_by(
        RespondIOFollowupQueue.contact_id,
        RespondIOFollowupQueue.lifecycle
    ).having(
        func.count(RespondIOFollowupQueue.id) > 1
    ).all()
    
    # Dettagli per duplicati inviati
    sent_details = []
    for contact_id, date, count in sent_duplicates:
        details = RespondIOFollowupQueue.query.filter(
            RespondIOFollowupQueue.contact_id == contact_id,
            func.date(RespondIOFollowupQueue.sent_at) == date,
            RespondIOFollowupQueue.status == 'sent'
        ).order_by(RespondIOFollowupQueue.sent_at).all()
        
        sent_details.append({
            'contact_id': contact_id,
            'date': date.isoformat() if date else None,
            'count': count,
            'messages': [{
                'id': d.id,
                'sent_at': d.sent_at.isoformat() if d.sent_at else None,
                'message_type': d.message_type
            } for d in details]
        })
    
    # Dettagli per duplicati pending
    pending_details = []
    for contact_id, lifecycle, count in pending_duplicates:
        details = RespondIOFollowupQueue.query.filter(
            RespondIOFollowupQueue.contact_id == contact_id,
            RespondIOFollowupQueue.lifecycle == lifecycle,
            RespondIOFollowupQueue.status.in_(['pending', 'processing'])
        ).order_by(RespondIOFollowupQueue.scheduled_at).all()
        
        pending_details.append({
            'contact_id': contact_id,
            'lifecycle': lifecycle,
            'count': count,
            'followups': [{
                'id': d.id,
                'scheduled_at': d.scheduled_at.isoformat() if d.scheduled_at else None,
                'status': d.status
            } for d in details]
        })
    
    return jsonify({
        'sent_duplicates': sent_details,
        'pending_duplicates': pending_details,
        'has_duplicates': len(sent_details) > 0 or len(pending_details) > 0,
        'total_sent_duplicates': len(sent_details),
        'total_pending_duplicates': len(pending_details)
    })


@bp.route('/api/followup/cleanup-duplicates', methods=['POST'])
@login_required
def api_cleanup_duplicates():
    """Rimuove follow-up duplicati mantenendo solo il primo per contatto"""
    
    from sqlalchemy import func
    
    removed_count = 0
    
    try:
        # IMPORTANTE: Un contatto dovrebbe avere SOLO UN follow-up attivo alla volta
        # indipendentemente dal lifecycle (perché può cambiare rapidamente)
        
        # Trova tutti i contatti con più di un follow-up pending/processing
        contacts_with_duplicates = db.session.query(
            RespondIOFollowupQueue.contact_id,
            func.count(RespondIOFollowupQueue.id).label('count')
        ).filter(
            RespondIOFollowupQueue.status.in_(['pending', 'processing'])
        ).group_by(
            RespondIOFollowupQueue.contact_id
        ).having(
            func.count(RespondIOFollowupQueue.id) > 1
        ).all()
        
        # Per ogni contatto con duplicati
        for contact_id, count in contacts_with_duplicates:
            # Prendi TUTTI i follow-up per questo contatto (indipendentemente dal lifecycle)
            followups = RespondIOFollowupQueue.query.filter(
                RespondIOFollowupQueue.contact_id == contact_id,
                RespondIOFollowupQueue.status.in_(['pending', 'processing'])
            ).order_by(
                RespondIOFollowupQueue.scheduled_at  # Mantieni quello schedulato prima
            ).all()
            
            # Log per debug
            current_app.logger.info(f"Contact {contact_id} has {len(followups)} pending follow-ups")
            
            # Mantieni solo il PRIMO (quello schedulato prima)
            # Cancella TUTTI gli altri
            for followup in followups[1:]:
                # Revoca il task Celery se esiste
                if followup.celery_task_id:
                    try:
                        from corposostenibile.celery_app import celery
                        celery.control.revoke(followup.celery_task_id, terminate=True)
                        current_app.logger.info(f"Revoked Celery task {followup.celery_task_id}")
                    except Exception as e:
                        current_app.logger.error(f"Error revoking task: {e}")
                
                # Marca come cancellato
                followup.status = 'cancelled'
                followup.cancelled_at = datetime.utcnow()
                followup.error_message = f'Duplicate removed - keeping only first followup for contact'
                removed_count += 1
                
                current_app.logger.info(f"Cancelled follow-up {followup.id} for contact {contact_id} (lifecycle: {followup.lifecycle})")
        
        db.session.commit()
        
        flash(f'Rimossi {removed_count} follow-up duplicati', 'success')
        current_app.logger.info(f"Cleanup completed: removed {removed_count} duplicate follow-ups")
        
        return jsonify({'status': 'success', 'removed': removed_count})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'error': str(e)}), 500


@bp.route('/api/followup/test', methods=['POST'])
@login_required
def api_test_followup():
    """Test invio follow-up manuale (solo per testing)"""
    
    data = request.get_json()
    contact_id = data.get('contact_id')
    lifecycle = data.get('lifecycle', 'Link Inviato')
    use_template = data.get('use_template', False)
    
    if not contact_id:
        return jsonify({'error': 'contact_id required'}), 400
    
    try:
        from .client import RespondIOClient
        from flask import current_app
        
        client = RespondIOClient(current_app.config)
        
        # Ottieni canale
        from corposostenibile.models import RespondIOContactChannel
        channel_name, channel_source = RespondIOContactChannel.get_channel(contact_id)
        
        if not channel_name:
            return jsonify({'error': 'Channel not found for contact'}), 404
        
        # Invia messaggio di test
        if use_template:
            result = client.send_template_message(
                contact_id,
                'followup_generico1',
                language='it'
            )
            message_type = 'template'
        else:
            result = client.send_message(
                contact_id,
                "Ciao 💪 Stai bene?"
            )
            message_type = 'text'
        
        return jsonify({
            'status': 'success',
            'message_type': message_type,
            'result': result
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500