"""
Webhook handlers per Respond.io - versione semplificata
Solo tracking metriche, non salviamo dati personali
"""

import json
import hmac
import hashlib
import base64
import time
from datetime import datetime, date
from flask import request, jsonify, current_app
from corposostenibile.extensions import db, csrf
from corposostenibile.models import (
    RespondIOLifecycleChange,
    RespondIODailyMetrics,
    RespondIOContactChannel,
    RespondIOFollowupConfig,
    RespondIOFollowupQueue,
    RespondIOMessageHistory,
    RESPOND_IO_CHANNELS,
    FOLLOWUP_ENABLED_LIFECYCLES
)
from . import bp


def verify_webhook_signature(signing_key):
    """Verifica la firma del webhook usando HMAC-SHA256"""
    signature = request.headers.get('X-Webhook-Signature')
    if not signature:
        return False
    
    # Calcola la firma attesa
    payload = request.get_data()
    expected_signature = base64.b64encode(
        hmac.new(
            signing_key.encode('utf-8'),
            payload,
            hashlib.sha256
        ).digest()
    ).decode('utf-8')
    
    return hmac.compare_digest(signature, expected_signature)


def extract_channel_from_contact(contact_data):
    """
    Estrae il canale origine dalla cache dei messaggi.
    Se non trovato, ritorna 'Unknown Channel'.
    """
    contact_id = contact_data.get('id')
    if not contact_id:
        current_app.logger.warning("No contact ID provided")
        return 'unknown', 'Unknown Channel'
    
    # Controlla la cache nel database
    channel_name, channel_source = get_channel_from_cache(contact_id)
    if channel_name:
        current_app.logger.info(f"Found channel in cache for contact {contact_id}: {channel_name}")
        return channel_source or channel_name, channel_name
    
    # Nessun canale trovato - il contatto non ha ancora messaggi
    current_app.logger.info(f"No channel mapping found for contact {contact_id}")
    return 'unknown', 'Unknown Channel'


@bp.route('/webhook/new-contact', methods=['POST'])
@csrf.exempt
def webhook_new_contact():
    """Handler per nuovo contatto creato - SEMPRE ritorna 200 OK"""
    
    # Verifica firma
    signing_key = current_app.config.get('RESPOND_IO_WEBHOOK_KEY_NEW_CONTACT')
    if not verify_webhook_signature(signing_key):
        current_app.logger.warning('Invalid webhook signature for new contact')
        # IMPORTANTE: Ritorna 200 OK anche con firma invalida per non disconnettere
        return jsonify({'status': 'ok', 'error': 'signature_invalid'}), 200
    
    try:
        data = request.get_json()
        
        # Usa il nuovo sistema di health management
        from .webhook_health import webhook_health_manager
        success, response = webhook_health_manager.process_webhook_safe('new-contact', data)
        
        # SEMPRE ritorna 200 OK
        return jsonify(response), 200
        
    except Exception as e:
        current_app.logger.error(f'Critical error in webhook: {str(e)}')
        # ANCHE IN CASO DI ERRORE CRITICO, ritorna 200 OK
        return jsonify({'status': 'ok', 'error': 'logged_for_retry'}), 200


def process_new_contact(data):
    """Processa realmente il nuovo contatto (chiamato async dalla coda)"""
    try:
        contact_data = data.get('contact', {})
        
        # Estrai dati essenziali
        contact_id = str(contact_data.get('id'))
        lifecycle = contact_data.get('lifecycle', 'Nuova Lead')
        
        # WORKAROUND: Per nuovi contatti, aspetta che arrivi il messaggio
        # che ci darà il canale corretto
        import time
        max_retries = 10  # Aumentato da 5 a 10 tentativi
        retry_delay = 0.5  # Aumentato da 300ms a 500ms tra tentativi (totale max 5 secondi)
        
        channel_source = 'unknown'
        channel_name = 'Unknown Channel'
        
        for retry in range(max_retries):
            # Prova a ottenere il canale dalla cache
            channel_name_tmp, channel_source_tmp = get_channel_from_cache(contact_id)
            if channel_name_tmp:
                channel_name = channel_name_tmp
                channel_source = channel_source_tmp
                current_app.logger.info(f"Found channel for new contact {contact_id} after {retry} retries: {channel_name}")
                break
            
            if retry < max_retries - 1:
                time.sleep(retry_delay)
        
        if channel_source == 'unknown':
            current_app.logger.warning(f"No channel found for new contact {contact_id} after {max_retries} retries")
        
        # Timestamp
        created_timestamp = contact_data.get('created_at')
        if created_timestamp:
            created_at = datetime.fromtimestamp(created_timestamp)
        else:
            created_at = datetime.utcnow()
        
        # Registra il cambio lifecycle (da None a Nuova Lead)
        lifecycle_change = RespondIOLifecycleChange(
            contact_id=contact_id,
            from_lifecycle=None,
            to_lifecycle=lifecycle,
            channel_source=channel_source,
            channel_name=channel_name,
            changed_at=created_at
        )
        db.session.add(lifecycle_change)
        
        # Aggiorna metriche giornaliere
        update_daily_metrics(created_at.date(), channel_source, channel_name, 'new_contact', lifecycle)
        
        db.session.commit()
        
        current_app.logger.info(f'New contact tracked: {contact_id} from {channel_name}')
        
        return jsonify({'status': 'success', 'contact_id': contact_id}), 200
        
    except Exception as e:
        current_app.logger.error(f'Error processing new contact webhook: {str(e)}')
        db.session.rollback()
        # IMPORTANTE: Sempre 200 OK per evitare disconnessioni
        return jsonify({'status': 'ok', 'error': 'logged'}), 200


@bp.route('/webhook/lifecycle-update', methods=['POST'])
@csrf.exempt
def webhook_lifecycle_update():
    """Handler per aggiornamento lifecycle - registra solo la transizione"""
    
    # Verifica firma
    signing_key = current_app.config.get('RESPOND_IO_WEBHOOK_KEY_LIFECYCLE')
    if not verify_webhook_signature(signing_key):
        current_app.logger.warning('Invalid webhook signature for lifecycle update')
        # IMPORTANTE: Sempre 200 OK per evitare disconnessioni
        return jsonify({'status': 'ok', 'error': 'invalid_signature'}), 200
    
    try:
        data = request.get_json()
        contact_data = data.get('contact', {})
        
        # Estrai dati
        contact_id = str(contact_data.get('id'))
        new_lifecycle = data.get('lifecycle')
        old_lifecycle = data.get('oldLifecycle')
        
        # Determina il canale
        channel_source, channel_name = extract_channel_from_contact(contact_data)
        
        # Registra il cambio
        lifecycle_change = RespondIOLifecycleChange(
            contact_id=contact_id,
            from_lifecycle=old_lifecycle,
            to_lifecycle=new_lifecycle,
            channel_source=channel_source,
            channel_name=channel_name,
            changed_at=datetime.utcnow()
        )
        db.session.add(lifecycle_change)
        
        # Aggiorna metriche giornaliere
        update_daily_metrics(
            date.today(),
            channel_source,
            channel_name,
            'lifecycle_change',
            new_lifecycle,
            old_lifecycle
        )
        
        # IMPORTANTE: Se il nuovo lifecycle NON è tra quelli abilitati per follow-up
        # ma quello vecchio lo era, dobbiamo cancellare eventuali follow-up pending
        if (old_lifecycle in FOLLOWUP_ENABLED_LIFECYCLES and 
            new_lifecycle not in FOLLOWUP_ENABLED_LIFECYCLES):
            
            # Cancella follow-up pending per questo contatto
            cancelled = RespondIOFollowupQueue.query.filter(
                RespondIOFollowupQueue.contact_id == contact_id,
                RespondIOFollowupQueue.status.in_(['pending', 'processing'])
            ).all()
            
            cancelled_count = 0
            for followup in cancelled:
                # Revoca task Celery se presente
                if followup.celery_task_id:
                    try:
                        from corposostenibile.celery_app import celery
                        celery.control.revoke(followup.celery_task_id, terminate=True)
                    except Exception as e:
                        current_app.logger.error(f"Error revoking Celery task: {e}")
                
                # Marca come cancellato
                followup.status = 'cancelled'
                followup.cancelled_at = datetime.utcnow()
                followup.error_message = f'Lifecycle changed from {old_lifecycle} to {new_lifecycle} (not eligible for follow-up)'
                cancelled_count += 1
            
            if cancelled_count > 0:
                current_app.logger.info(
                    f"Cancelled {cancelled_count} follow-ups for contact {contact_id} "
                    f"due to lifecycle change to {new_lifecycle}"
                )
                
                # Rimuovi tag "in_attesa_followup_1" dal contatto in Respond.io
                try:
                    from .client import RespondIOClient
                    client = RespondIOClient(current_app.config)
                    client.remove_tags(contact_id, ['in_attesa_followup_1'])
                    current_app.logger.info(f"Removed tag 'in_attesa_followup_1' from contact {contact_id}")
                    
                    with open('/home/devops/corposostenibile-suite/logs/tag_operations.log', 'a') as f:
                        f.write(f"{datetime.utcnow().isoformat()} - FOLLOWUP CANCELLED: Removed 'in_attesa_followup_1' tag from contact {contact_id} (lifecycle changed from {old_lifecycle} to {new_lifecycle})\n")
                except Exception as e:
                    current_app.logger.error(f"Error removing tag from contact {contact_id}: {e}")
                    
                    with open('/home/devops/corposostenibile-suite/logs/tag_operations.log', 'a') as f:
                        f.write(f"{datetime.utcnow().isoformat()} - FOLLOWUP ERROR: Failed to remove 'in_attesa_followup_1' tag from contact {contact_id}: {e}\n")
        
        db.session.commit()
        
        current_app.logger.info(
            f'Lifecycle updated for {contact_id}: {old_lifecycle} → {new_lifecycle} '
            f'(Channel: {channel_name})'
        )
        
        # Trigger calcolo metriche async se Celery è attivo
        if current_app.config.get('USE_CELERY'):
            from .tasks import recalculate_daily_metrics
            recalculate_daily_metrics.delay(date.today(), channel_source)
        
        return jsonify({
            'status': 'success',
            'contact_id': contact_id,
            'transition': f'{old_lifecycle} → {new_lifecycle}'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Error processing lifecycle webhook: {str(e)}')
        db.session.rollback()
        # IMPORTANTE: Sempre 200 OK per evitare disconnessioni
        return jsonify({'status': 'ok', 'error': 'logged'}), 200


def update_daily_metrics(target_date, channel_source, channel_name, event_type, 
                        new_lifecycle=None, old_lifecycle=None):
    """
    Aggiorna le metriche giornaliere in tempo reale.
    IMPORTANTE: Contiamo OGNI VOLTA che un contatto viene messo in un lifecycle,
    NON le transizioni da uno stato all'altro.
    """
    # Trova o crea record per oggi e questo canale
    # IMPORTANTE: Usa channel_name come identificatore univoco, non channel_source!
    metrics = RespondIODailyMetrics.query.filter_by(
        date=target_date,
        channel_name=channel_name  # Cambiato da channel_source a channel_name
    ).first()
    
    if not metrics:
        metrics = RespondIODailyMetrics(
            date=target_date,
            channel_source=channel_source,
            channel_name=channel_name
        )
        db.session.add(metrics)
    else:
        # Aggiorna channel_source se necessario
        if metrics.channel_source != channel_source:
            metrics.channel_source = channel_source
    
    # Aggiorna contatori basati sull'evento
    if event_type == 'new_contact':
        metrics.new_contacts = (metrics.new_contacts or 0) + 1
        if new_lifecycle == 'Nuova Lead':
            metrics.new_leads = (metrics.new_leads or 0) + 1
    
    elif event_type == 'lifecycle_change':
        # NUOVO APPROCCIO: Contiamo OGNI VOLTA che un contatto entra in uno stato
        # indipendentemente da dove proveniva
        
        # Mappa dei lifecycle ai campi delle metriche
        lifecycle_field_map = {
            'Nuova Lead': 'new_leads',
            'Contrassegnato': 'total_contrassegnato',
            'In Target': 'total_in_target',
            'Link Da Inviare': 'total_link_da_inviare',
            'Link Inviato': 'total_link_inviato',
            'Prenotato': 'total_prenotato',
            'Under': 'to_under',
            'Non in Target': 'to_non_target',
            'Prenotato Non In Target': 'to_prenotato_non_target'
        }
        
        # Incrementa il contatore per il nuovo lifecycle
        if new_lifecycle in lifecycle_field_map:
            field_name = lifecycle_field_map[new_lifecycle]
            current_value = getattr(metrics, field_name, 0) or 0
            setattr(metrics, field_name, current_value + 1)
        
        # MANTENIAMO ANCHE le transizioni per retrocompatibilità e analisi del flusso
        # Ma queste sono informazioni supplementari, non le metriche principali
        transition_map = {
            ('Nuova Lead', 'Contrassegnato'): 'lead_to_contrassegnato',
            ('Contrassegnato', 'In Target'): 'contrassegnato_to_target',
            ('In Target', 'Link Da Inviare'): 'target_to_link_da_inviare',
            ('Link Da Inviare', 'Link Inviato'): 'link_da_inviare_to_link_inviato',
            ('In Target', 'Link Inviato'): 'target_to_link',  # Compatibilità: transizione diretta
            ('Link Inviato', 'Prenotato'): 'link_to_prenotato',
        }
        
        transition_key = (old_lifecycle, new_lifecycle)
        if transition_key in transition_map:
            field_name = transition_map[transition_key]
            current_value = getattr(metrics, field_name, 0) or 0
            setattr(metrics, field_name, current_value + 1)
    
    metrics.updated_at = datetime.utcnow()
    
    # Non facciamo commit qui, lo fa il chiamante


@bp.route('/webhook/incoming-message', methods=['POST'])
@csrf.exempt
def webhook_incoming_message():
    """Handler per nuovo messaggio in arrivo - salva il mapping contact-channel e gestisce follow-up"""
    
    # Log inizio processamento
    start_time = time.time()
    current_app.logger.info(f"[WEBHOOK] incoming-message started at {datetime.utcnow()}")
    
    # Verifica firma
    signing_key = current_app.config.get('RESPOND_IO_WEBHOOK_KEY_INCOMING_MESSAGE')
    if not verify_webhook_signature(signing_key):
        current_app.logger.warning('Invalid webhook signature for incoming message')
        # IMPORTANTE: Sempre 200 OK per evitare disconnessioni
        return jsonify({'status': 'ok', 'error': 'invalid_signature'}), 200
    
    try:
        data = request.get_json()
        
        # LOG DEBUG
        with open('/tmp/webhook_debug.log', 'a') as f:
            f.write(f"\n[{datetime.utcnow()}] WEBHOOK INCOMING RECEIVED\n")
            f.write(f"  📦 Data: {json.dumps(data)[:200]}\n")
        
        # Estrai dati del contatto e del canale
        contact_data = data.get('contact', {})
        contact_id = str(contact_data.get('id'))
        lifecycle = contact_data.get('lifecycle')
        
        # Se il lifecycle non è nel webhook, recuperalo dal database
        if not lifecycle and contact_id:
            recent_lifecycle = RespondIOLifecycleChange.query.filter_by(
                contact_id=contact_id
            ).order_by(
                RespondIOLifecycleChange.changed_at.desc()
            ).first()
            if recent_lifecycle:
                lifecycle = recent_lifecycle.to_lifecycle
                current_app.logger.info(f"Lifecycle retrieved from DB for {contact_id}: {lifecycle}")
                with open('/tmp/webhook_debug.log', 'a') as f:
                    f.write(f"  📊 Lifecycle from DB: {lifecycle}\n")
        
        # Il canale è direttamente nel payload!
        channel_data = data.get('channel', {})
        channel_id = channel_data.get('id')  # Questo è un integer dall'API!
        channel_name = channel_data.get('name', '')
        channel_source = channel_data.get('source', '')
        
        # LOG DEBUG del channel completo
        with open('/tmp/webhook_debug.log', 'a') as f:
            f.write(f"  📡 Channel ID: {channel_id} (type: {type(channel_id).__name__}), Name: {channel_name}, Source: {channel_source}\n")
        
        # Message data
        message_data = data.get('message', {})
        message_id = message_data.get('id')
        
        with open('/tmp/webhook_debug.log', 'a') as f:
            f.write(f"  🔍 Check cancel follow-up: contact={contact_id}, lifecycle={lifecycle}\n")
            f.write(f"  📋 Enabled lifecycles: {FOLLOWUP_ENABLED_LIFECYCLES}\n")
        
        if contact_id and channel_name:
            # Salva il mapping contact-channel nel database
            save_contact_channel_mapping(contact_id, channel_name, channel_source, channel_id)
            
            # IMPORTANTE: Aggiorna anche eventuali lifecycle changes con Unknown Channel
            update_unknown_channel_lifecycles(contact_id, channel_name, channel_source)
            
            # Salva nella history per tracking finestra 24h
            history = RespondIOMessageHistory(
                contact_id=contact_id,
                channel_id=channel_id,
                message_type='incoming',
                message_id=message_id,
                message_timestamp=datetime.utcnow()
            )
            db.session.add(history)
            
            # IMPORTANTE: Aggiungi tag "in_attesa" quando il cliente scrive
            # Questo indica che il contatto è in attesa di risposta dall'agente
            max_retries = 3
            retry_count = 0
            tag_added = False
            
            while retry_count < max_retries and not tag_added:
                try:
                    from .client import RespondIOClient
                    client = RespondIOClient(current_app.config)
                    result = client.add_tags(contact_id, ["in_attesa"])
                    current_app.logger.info(f"Added 'in_attesa' tag to contact {contact_id} - customer sent message")
                    tag_added = True
                    
                    # Log success
                    with open('/home/devops/corposostenibile-suite/logs/tag_operations.log', 'a') as f:
                        f.write(f"{datetime.utcnow().isoformat()} - SUCCESS: Added 'in_attesa' tag to contact {contact_id}\n")
                except Exception as e:
                    retry_count += 1
                    current_app.logger.error(f"Error adding 'in_attesa' tag to {contact_id} (attempt {retry_count}/{max_retries}): {e}")
                    
                    with open('/home/devops/corposostenibile-suite/logs/tag_operations.log', 'a') as f:
                        f.write(f"{datetime.utcnow().isoformat()} - ERROR: Failed to add 'in_attesa' tag to {contact_id} (attempt {retry_count}): {e}\n")
                    
                    if retry_count < max_retries:
                        time.sleep(2 ** retry_count)  # Exponential backoff: 2, 4, 8 seconds
                    else:
                        # Final failure - log critically
                        current_app.logger.critical(f"FAILED to add 'in_attesa' tag to {contact_id} after {max_retries} attempts")
            
            # FOLLOW-UP: Rimuove tag "in_attesa_followup_1" se presente
            # perché il contatto ha risposto
            if lifecycle in FOLLOWUP_ENABLED_LIFECYCLES:
                with open('/tmp/webhook_debug.log', 'a') as f:
                    f.write(f"  ✅ SHOULD CANCEL FOLLOW-UP!\n")
                
                # Cancella eventuali follow-up pending
                cancelled = RespondIOFollowupQueue.cancel_pending(contact_id, lifecycle)
                with open('/tmp/webhook_debug.log', 'a') as f:
                    f.write(f"  📊 Follow-ups cancelled: {cancelled}\n")
                
                # Log follow-up cancellation
                with open('/home/devops/corposostenibile-suite/logs/tag_operations.log', 'a') as f:
                    f.write(f"{datetime.utcnow().isoformat()} - FOLLOWUP CANCELLED: Customer responded - cancelled {cancelled} pending follow-ups for contact {contact_id} in lifecycle {lifecycle}\n")
                    
                if cancelled > 0:
                    current_app.logger.info(
                        f"Cancelled {cancelled} pending follow-ups for contact {contact_id} - customer responded"
                    )
                    with open('/tmp/webhook_debug.log', 'a') as f:
                        f.write(f"  ✅ Cancelled {cancelled} follow-ups in DB\n")
                else:
                    with open('/tmp/webhook_debug.log', 'a') as f:
                        f.write(f"  ⚠️ No pending follow-ups found to cancel\n")
                
                # Rimuovi tag di attesa tramite API sempre (anche se non ci sono follow-up)
                from .client import RespondIOClient
                client = RespondIOClient(current_app.config)
                try:
                    result = client.remove_tags(contact_id, ["in_attesa_followup_1"])
                    current_app.logger.info(f"Tag removed successfully from {contact_id}: {result}")
                    with open('/tmp/webhook_debug.log', 'a') as f:
                        f.write(f"  ✅ Tag 'in_attesa_followup_1' removed via API\n")
                except Exception as e:
                    current_app.logger.error(f"Error removing follow-up tag: {e}")
                    with open('/tmp/webhook_debug.log', 'a') as f:
                        f.write(f"  ❌ Error removing tag: {e}\n")
            
            db.session.commit()
            
            current_app.logger.info(
                f"Incoming message - Contact {contact_id} mapped to channel: {channel_name}"
            )
        
        # Log tempo di processamento
        elapsed = time.time() - start_time
        current_app.logger.info(f"[WEBHOOK] incoming-message completed in {elapsed:.3f}s")
        
        if elapsed > 5:
            current_app.logger.warning(f"[WEBHOOK] SLOW RESPONSE: {elapsed:.3f}s - might cause disconnection")
            
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        elapsed = time.time() - start_time
        current_app.logger.error(f'[WEBHOOK] incoming-message error after {elapsed:.3f}s: {str(e)}')
        db.session.rollback()
        # IMPORTANTE: Sempre 200 OK per evitare disconnessioni
        return jsonify({'status': 'ok', 'error': 'logged'}), 200


@bp.route('/webhook/outgoing-message', methods=['POST'])
@csrf.exempt
def webhook_outgoing_message():
    """Handler per messaggio in uscita - salva il mapping contact-channel e schedula follow-up"""
    
    # LOG DEBUG
    with open('/tmp/webhook_debug.log', 'a') as f:
        f.write(f"\n[{datetime.utcnow()}] WEBHOOK OUTGOING RECEIVED\n")
    
    # Verifica firma
    signing_key = current_app.config.get('RESPOND_IO_WEBHOOK_KEY_OUTGOING_MESSAGE')
    if not verify_webhook_signature(signing_key):
        current_app.logger.warning('Invalid webhook signature for outgoing message')
        with open('/tmp/webhook_debug.log', 'a') as f:
            f.write(f"  ❌ Invalid signature\n")
        # IMPORTANTE: Sempre 200 OK per evitare disconnessioni
        return jsonify({'status': 'ok', 'error': 'invalid_signature'}), 200
    
    try:
        data = request.get_json()
        
        # LOG DEBUG - Log completo del webhook per debug
        with open('/tmp/webhook_debug.log', 'a') as f:
            f.write(f"  📦 Data: {json.dumps(data)[:200]}\n")
            # Log anche il channel data completo
            channel_data = data.get('channel', {})
            f.write(f"  📡 Channel Data: {json.dumps(channel_data)}\n")
        
        # Estrai dati del contatto e del canale
        contact_data = data.get('contact', {})
        contact_id = str(contact_data.get('id'))
        lifecycle = contact_data.get('lifecycle')
        
        # Se il lifecycle non è nel webhook, recuperalo dal database
        if not lifecycle and contact_id:
            recent_lifecycle = RespondIOLifecycleChange.query.filter_by(
                contact_id=contact_id
            ).order_by(
                RespondIOLifecycleChange.changed_at.desc()
            ).first()
            if recent_lifecycle:
                lifecycle = recent_lifecycle.to_lifecycle
                current_app.logger.info(f"Lifecycle retrieved from DB for {contact_id}: {lifecycle}")
                with open('/tmp/webhook_debug.log', 'a') as f:
                    f.write(f"  📊 Lifecycle from DB: {lifecycle}\n")
        
        # Il canale è direttamente nel payload!
        channel_data = data.get('channel', {})
        channel_id = channel_data.get('id')  # Questo è un integer dall'API!
        channel_name = channel_data.get('name', '')
        channel_source = channel_data.get('source', '')
        
        # LOG DEBUG del channel completo
        with open('/tmp/webhook_debug.log', 'a') as f:
            f.write(f"  📡 Channel ID: {channel_id} (type: {type(channel_id).__name__}), Name: {channel_name}, Source: {channel_source}\n")
        
        # Message data
        message_data = data.get('message', {})
        message_id = message_data.get('id')
        message_type = message_data.get('type', 'text')
        
        # Non schedulare follow-up se è un messaggio di follow-up stesso
        is_followup_message = message_data.get('text', '').startswith('Ciao 💪')
        
        # IMPORTANTE: Non schedulare nuovo follow-up se ne abbiamo già inviato uno
        # e il cliente non ha ancora risposto
        has_sent_followup_waiting = False
        if not is_followup_message:
            # Verifica se c'è un follow-up già inviato in attesa di risposta
            last_followup = RespondIOFollowupQueue.query.filter_by(
                contact_id=contact_id,
                lifecycle=lifecycle,
                status='sent'
            ).order_by(
                RespondIOFollowupQueue.sent_at.desc()
            ).first()
            
            if last_followup:
                # Verifica se il cliente ha risposto dopo l'invio del follow-up
                last_client_message = RespondIOMessageHistory.query.filter(
                    RespondIOMessageHistory.contact_id == contact_id,
                    RespondIOMessageHistory.message_type == 'incoming',
                    RespondIOMessageHistory.message_timestamp > last_followup.sent_at
                ).first()
                
                if not last_client_message:
                    # Cliente non ha risposto dopo il follow-up
                    has_sent_followup_waiting = True
                    current_app.logger.info(
                        f"Not scheduling new follow-up - waiting for client response to follow-up sent at {last_followup.sent_at}"
                    )
                    with open('/tmp/webhook_debug.log', 'a') as f:
                        f.write(f"  ⏸️ SKIP: Already sent follow-up at {last_followup.sent_at}, waiting for client response\n")
                else:
                    # Cliente ha risposto, possiamo schedulare nuovo follow-up
                    with open('/tmp/webhook_debug.log', 'a') as f:
                        f.write(f"  ✅ Client responded at {last_client_message.message_timestamp}, can schedule new follow-up\n")
        
        if contact_id and channel_name:
            # Salva il mapping contact-channel nel database
            save_contact_channel_mapping(contact_id, channel_name, channel_source, channel_id)
            
            # IMPORTANTE: Aggiorna anche eventuali lifecycle changes con Unknown Channel
            update_unknown_channel_lifecycles(contact_id, channel_name, channel_source)
            
            # Salva nella history per tracking
            history = RespondIOMessageHistory(
                contact_id=contact_id,
                channel_id=channel_id,
                message_type='outgoing',
                message_id=message_id,
                message_timestamp=datetime.utcnow()
            )
            db.session.add(history)
            
            # IMPORTANTE: Rimuovi tag "in_attesa" quando l'agente risponde
            # Il contatto non è più in attesa di risposta
            max_retries = 3
            retry_count = 0
            tag_removed = False
            
            while retry_count < max_retries and not tag_removed:
                try:
                    from .client import RespondIOClient
                    client = RespondIOClient(current_app.config)
                    result = client.remove_tags(contact_id, ["in_attesa"])
                    current_app.logger.info(f"Removed 'in_attesa' tag from contact {contact_id} - agent replied")
                    tag_removed = True
                    
                    # Log success
                    with open('/home/devops/corposostenibile-suite/logs/tag_operations.log', 'a') as f:
                        f.write(f"{datetime.utcnow().isoformat()} - SUCCESS: Removed 'in_attesa' tag from contact {contact_id}\n")
                except Exception as e:
                    retry_count += 1
                    current_app.logger.error(f"Error removing 'in_attesa' tag from {contact_id} (attempt {retry_count}/{max_retries}): {e}")
                    
                    with open('/home/devops/corposostenibile-suite/logs/tag_operations.log', 'a') as f:
                        f.write(f"{datetime.utcnow().isoformat()} - ERROR: Failed to remove 'in_attesa' tag from {contact_id} (attempt {retry_count}): {e}\n")
                    
                    if retry_count < max_retries:
                        time.sleep(2 ** retry_count)  # Exponential backoff: 2, 4, 8 seconds
                    else:
                        # Final failure - log critically
                        current_app.logger.critical(f"FAILED to remove 'in_attesa' tag from {contact_id} after {max_retries} attempts")
            
            # FOLLOW-UP: Schedula follow-up se lifecycle è abilitato e non è già un follow-up
            current_app.logger.info(f"Checking follow-up for {contact_id}: lifecycle={lifecycle}, is_followup={is_followup_message}")
            
            # LOG DEBUG
            with open('/tmp/webhook_debug.log', 'a') as f:
                f.write(f"  🔍 Check follow-up: contact={contact_id}, lifecycle={lifecycle}, is_followup={is_followup_message}\n")
                f.write(f"  📋 Enabled lifecycles: {FOLLOWUP_ENABLED_LIFECYCLES}\n")
            
            if lifecycle in FOLLOWUP_ENABLED_LIFECYCLES and not is_followup_message and not has_sent_followup_waiting:
                # IMPORTANTE: Usa lock pessimistico per evitare race conditions
                # Verifica se esiste già un follow-up pending o processing per evitare duplicati
                existing_pending = RespondIOFollowupQueue.query.with_for_update().filter(
                    RespondIOFollowupQueue.contact_id == contact_id,
                    RespondIOFollowupQueue.lifecycle == lifecycle,
                    RespondIOFollowupQueue.status.in_(['pending', 'processing'])
                ).first()
                
                if existing_pending:
                    current_app.logger.info(
                        f"Follow-up already {existing_pending.status} for {contact_id} in {lifecycle}, skipping duplicate"
                    )
                    with open('/tmp/webhook_debug.log', 'a') as f:
                        f.write(f"  ⏭️ SKIP: Follow-up already {existing_pending.status} (ID: {existing_pending.id})\n")
                    # Non creare un nuovo follow-up, usa quello esistente
                    continue_processing = False
                else:
                    current_app.logger.info(f"Scheduling follow-up for {contact_id} in {lifecycle}")
                    
                    # LOG DEBUG
                    with open('/tmp/webhook_debug.log', 'a') as f:
                        f.write(f"  ✅ SHOULD SCHEDULE FOLLOW-UP!\n")
                    
                    # Applica tag "in_attesa_followup_1"
                    from .client import RespondIOClient
                    client = RespondIOClient(current_app.config)
                    continue_processing = True
                    
                    # Log follow-up operation start
                    with open('/home/devops/corposostenibile-suite/logs/tag_operations.log', 'a') as f:
                        f.write(f"{datetime.utcnow().isoformat()} - FOLLOWUP START: Scheduling follow-up for contact {contact_id} in lifecycle {lifecycle}\n")
                    
                    try:
                        result = client.add_tags(contact_id, ["in_attesa_followup_1"])
                        current_app.logger.info(f"Tag applied successfully to {contact_id}: {result}")
                        
                        with open('/home/devops/corposostenibile-suite/logs/tag_operations.log', 'a') as f:
                            f.write(f"{datetime.utcnow().isoformat()} - FOLLOWUP SUCCESS: Added 'in_attesa_followup_1' tag to contact {contact_id}\n")
                    except Exception as e:
                        current_app.logger.error(f"Error applying tag: {e}")
                        continue_processing = False
                        
                        with open('/home/devops/corposostenibile-suite/logs/tag_operations.log', 'a') as f:
                            f.write(f"{datetime.utcnow().isoformat()} - FOLLOWUP ERROR: Failed to add 'in_attesa_followup_1' tag to contact {contact_id}: {e}\n")
                    
                    if continue_processing:
                        try:
                            # Schedula follow-up dopo 12 ore
                            from .followup_tasks import schedule_followup
                            from datetime import timedelta
                            import pytz
                            
                            # Usa timezone italiano per scheduling
                            rome_tz = pytz.timezone('Europe/Rome')
                            rome_now = datetime.now(rome_tz)
                            # Schedula tra 12 ore in timezone italiano
                            scheduled_rome = rome_now + timedelta(hours=12)
                            original_scheduled = scheduled_rome  # Salva orario originale per tracking
                            
                            # QUIET PERIOD: Se il follow-up cade tra mezzanotte e le 6:59, posticipa alle 7:00
                            quiet_start_hour = 0  # Mezzanotte
                            quiet_end_hour = 7    # 7:00 del mattino
                            
                            if scheduled_rome.hour >= quiet_start_hour and scheduled_rome.hour < quiet_end_hour:
                                # Conta quanti follow-up sono già schedulati per dopo le 7:00
                                from sqlalchemy import and_, func
                                import random
                                
                                # Trova l'orario base (7:00 dello stesso giorno)
                                base_time = scheduled_rome.replace(hour=quiet_end_hour, minute=0, second=0, microsecond=0)
                                
                                # Conta follow-up già schedulati tra le 7:00 e le 8:00
                                start_window = base_time.astimezone(pytz.UTC).replace(tzinfo=None)
                                end_window = (base_time + timedelta(hours=1)).astimezone(pytz.UTC).replace(tzinfo=None)
                                
                                existing_count = RespondIOFollowupQueue.query.filter(
                                    and_(
                                        RespondIOFollowupQueue.status == 'pending',
                                        RespondIOFollowupQueue.scheduled_at >= start_window,
                                        RespondIOFollowupQueue.scheduled_at < end_window
                                    )
                                ).count()
                                
                                # Distribuisci i follow-up: 1 ogni 30 secondi per rispettare rate limits
                                # Max 120 follow-up per ora (2 al minuto)
                                delay_seconds = existing_count * 30
                                scheduled_rome = base_time + timedelta(seconds=delay_seconds)
                                
                                # Aggiungi un po' di randomizzazione (0-10 secondi) per sembrare più naturale
                                random_offset = random.randint(0, 10)
                                scheduled_rome = scheduled_rome + timedelta(seconds=random_offset)
                                
                                current_app.logger.info(
                                    f"Follow-up postponed from {original_scheduled.strftime('%H:%M')} to {scheduled_rome.strftime('%H:%M:%S')} "
                                    f"(quiet hours, position {existing_count + 1} in queue)"
                                )
                            
                            # Salva come UTC nel database (senza timezone info per SQLAlchemy)
                            scheduled_at_utc = scheduled_rome.astimezone(pytz.UTC).replace(tzinfo=None)
                            # Per Celery, usa il datetime con timezone
                            scheduled_at_for_celery = scheduled_rome.astimezone(pytz.UTC)
                            
                            # Crea record in queue
                            followup = RespondIOFollowupQueue(
                                contact_id=contact_id,
                                lifecycle=lifecycle,
                                channel_name=channel_name,
                                channel_id=channel_id,
                                scheduled_at=scheduled_at_utc,  # Usa UTC per database
                                original_scheduled_at=original_scheduled.astimezone(pytz.UTC).replace(tzinfo=None) if original_scheduled != scheduled_rome else None,
                                status='pending',
                                tag_waiting='in_attesa_followup_1',
                                tag_sent='followup_1_inviato'
                            )
                            db.session.add(followup)
                            db.session.flush()  # Per ottenere l'ID
                            
                            # Log follow-up queue addition
                            with open('/home/devops/corposostenibile-suite/logs/tag_operations.log', 'a') as f:
                                f.write(f"{datetime.utcnow().isoformat()} - FOLLOWUP QUEUED: Added to queue - ID: {followup.id}, Contact: {contact_id}, Scheduled for: {scheduled_rome.isoformat()}\n")
                            
                            # Schedula task Celery con datetime timezone-aware
                            task = schedule_followup.apply_async(
                                args=[followup.id],
                                eta=scheduled_at_for_celery  # Usa datetime con timezone per Celery
                            )
                            followup.celery_task_id = task.id
                            
                            current_app.logger.info(
                                f"Scheduled follow-up for contact {contact_id} in lifecycle {lifecycle} at {scheduled_rome.isoformat()} (Rome time)"
                            )
                            
                            with open('/home/devops/corposostenibile-suite/logs/tag_operations.log', 'a') as f:
                                f.write(f"{datetime.utcnow().isoformat()} - FOLLOWUP CELERY: Task scheduled with ID: {task.id}\n")
                            
                        except Exception as e:
                            current_app.logger.error(f"Error scheduling follow-up: {e}")
            
            db.session.commit()
            
            current_app.logger.info(
                f"Outgoing message - Contact {contact_id} mapped to channel: {channel_name}"
            )
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        current_app.logger.error(f'Error processing outgoing message webhook: {str(e)}')
        db.session.rollback()
        # IMPORTANTE: Sempre 200 OK per evitare disconnessioni
        return jsonify({'status': 'ok', 'error': 'logged'}), 200


def save_contact_channel_mapping(contact_id, channel_name, channel_source, channel_id=None):
    """
    Salva o aggiorna il mapping contact-channel nel database.
    """
    try:
        RespondIOContactChannel.update_mapping(
            contact_id=contact_id,
            channel_name=channel_name,
            channel_source=channel_source,
            channel_id=channel_id
        )
        db.session.commit()
        
        current_app.logger.info(
            f"Channel mapping saved to DB: contact={contact_id}, "
            f"channel={channel_name}, source={channel_source}"
        )
    except Exception as e:
        current_app.logger.error(f"Error saving channel mapping: {e}")
        db.session.rollback()


def get_channel_from_cache(contact_id):
    """
    Recupera il canale dal database per un contact_id.
    """
    return RespondIOContactChannel.get_channel(contact_id)


def update_unknown_channel_lifecycles(contact_id, channel_name, channel_source):
    """
    Aggiorna i lifecycle changes che hanno 'Unknown Channel' per questo contact_id.
    Chiamato quando arriva un messaggio che ci dice il canale corretto.
    """
    try:
        # Trova tutti i lifecycle changes con Unknown Channel per questo contatto
        # negli ultimi 30 minuti (aumentato per maggiore sicurezza)
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=30)
        
        updated = RespondIOLifecycleChange.query.filter(
            RespondIOLifecycleChange.contact_id == str(contact_id),
            RespondIOLifecycleChange.channel_source == 'unknown',
            RespondIOLifecycleChange.changed_at >= cutoff_time
        ).update({
            'channel_name': channel_name,
            'channel_source': channel_source or channel_name
        })
        
        if updated > 0:
            db.session.commit()
            current_app.logger.info(
                f"Updated {updated} Unknown Channel records for contact {contact_id} to {channel_name}"
            )
            
            # Aggiorna anche le metriche giornaliere se necessario
            from datetime import date
            update_daily_metrics(
                date.today(), 
                channel_source or channel_name, 
                channel_name,
                'channel_correction',
                None
            )
    except Exception as e:
        current_app.logger.error(f"Error updating unknown channels: {e}")
        db.session.rollback()


@bp.route('/webhook/tag-updated', methods=['POST'])
@csrf.exempt
def webhook_tag_updated():
    """Handler per aggiornamento tag - gestisce rimozione manuale tag follow-up"""
    
    # Verifica firma
    signing_key = current_app.config.get('RESPOND_IO_WEBHOOK_KEY_TAG_UPDATED', 
                                         'Hc0M8HSW1yt5CMOJugVVyMDitWhVjkIPRYFPlZYYmXw=')
    if not verify_webhook_signature(signing_key):
        current_app.logger.warning('Invalid webhook signature for tag updated')
        # IMPORTANTE: Sempre 200 OK per evitare disconnessioni
        return jsonify({'status': 'ok', 'error': 'invalid_signature'}), 200
    
    try:
        data = request.get_json()
        
        # LOG DEBUG completo del payload
        with open('/tmp/webhook_debug.log', 'a') as f:
            f.write(f"\n[{datetime.utcnow()}] WEBHOOK TAG-UPDATED RAW DATA:\n")
            f.write(f"  Full payload: {json.dumps(data)}\n")  # Log completo, non troncato
        
        # Estrai dati
        contact_data = data.get('contact', {})
        contact_id = str(contact_data.get('id'))
        lifecycle = contact_data.get('lifecycle')
        
        # Respond.io invia solo la lista attuale dei tag, non i cambiamenti
        # Dobbiamo dedurre se "in_attesa_followup_1" è stato rimosso
        current_tags = contact_data.get('tags', [])
        
        # NUOVO: Gestione tag "in_attesa" per assegnazioni automatiche
        # Il webhook fornisce direttamente quale tag è cambiato e l'azione
        tag_changed = data.get('tag')  # Il tag che è stato modificato
        tag_action = data.get('action')  # "add" o "remove"
        
        # Se il tag modificato è "in_attesa", triggera assegnazione/dissociazione
        if tag_changed == 'in_attesa':
            current_app.logger.info(f"Tag 'in_attesa' {tag_action} for contact {contact_id}")
            
            if tag_action == 'add':
                # Tag AGGIUNTO - schedula assegnazione dopo 2 minuti
                try:
                    current_app.timestamp_assignment_service.handle_tag_change(
                        contact_id=contact_id,
                        tag='in_attesa',
                        action='added'
                    )
                    current_app.logger.info(f"Scheduled assignment for contact {contact_id} in 2 minutes")
                except Exception as e:
                    current_app.logger.error(f"Failed to schedule assignment: {e}")
                    
            elif tag_action == 'remove':
                # Tag RIMOSSO - schedula dissociazione dopo 2 minuti
                try:
                    current_app.timestamp_assignment_service.handle_tag_change(
                        contact_id=contact_id,
                        tag='in_attesa',
                        action='removed'
                    )
                    current_app.logger.info(f"Scheduled dissociation for contact {contact_id} in 2 minutes")
                except Exception as e:
                    current_app.logger.error(f"Failed to schedule dissociation: {e}")
        
        # Log per debug dettagliato
        with open('/tmp/webhook_debug.log', 'a') as f:
            f.write(f"  Contact ID: {contact_id}\n")
            f.write(f"  Current tags: {current_tags}\n")
            f.write(f"  Tag changed: {tag_changed}\n")
            f.write(f"  Action: {tag_action}\n")
            f.write(f"  Tag 'in_attesa_followup_1' present: {'in_attesa_followup_1' in current_tags}\n")
        
        # Verifica se c'è un follow-up pending per questo contatto
        pending_followup = RespondIOFollowupQueue.query.filter_by(
            contact_id=contact_id,
            status='pending'
        ).first()
        
        has_pending_followup = pending_followup is not None
        
        with open('/tmp/webhook_debug.log', 'a') as f:
            f.write(f"  Has pending follow-up: {has_pending_followup}\n")
            if pending_followup:
                f.write(f"  Pending follow-up ID: {pending_followup.id}, scheduled_at: {pending_followup.scheduled_at}\n")
        
        # Se il tag "in_attesa_followup_1" NON è nella lista attuale
        # ma c'è un follow-up pending, significa che è stato rimosso
        tag_was_removed = 'in_attesa_followup_1' not in current_tags
        
        # Per retrocompatibilità, manteniamo le variabili originali
        tags_added = []
        tags_removed = []
        
        # Se il tag non c'è più ma c'è un follow-up pending, il tag è stato rimosso
        if tag_was_removed and has_pending_followup:
            tags_removed = ['in_attesa_followup_1']
            with open('/tmp/webhook_debug.log', 'a') as f:
                f.write(f"  ✅ Detected tag removal: in_attesa_followup_1 (was removed manually)\n")
        
        current_app.logger.info(
            f"Tag update for contact {contact_id}: added={tags_added}, removed={tags_removed}"
        )
        
        # LOG DEBUG per tag webhook
        with open('/tmp/webhook_debug.log', 'a') as f:
            f.write(f"\n[{datetime.utcnow()}] WEBHOOK TAG-UPDATED\n")
            f.write(f"  Contact: {contact_id}, Lifecycle: {lifecycle}\n")
            f.write(f"  Tags added: {tags_added}\n")
            f.write(f"  Tags removed: {tags_removed}\n")
        
        # Se è stato rimosso il tag "in_attesa_followup_1", cancella il follow-up
        if 'in_attesa_followup_1' in tags_removed:
            # Se non abbiamo il lifecycle nel webhook, recuperalo dal database
            if not lifecycle:
                recent_lifecycle = RespondIOLifecycleChange.query.filter_by(
                    contact_id=contact_id
                ).order_by(
                    RespondIOLifecycleChange.changed_at.desc()
                ).first()
                if recent_lifecycle:
                    lifecycle = recent_lifecycle.to_lifecycle
                    current_app.logger.info(f"Lifecycle retrieved from DB for cancellation: {lifecycle}")
            
            # Cancella tutti i follow-up pending per questo contatto (indipendentemente dal lifecycle)
            # perché il tag è stato rimosso manualmente
            cancelled = RespondIOFollowupQueue.cancel_pending(contact_id)  # Non passare il lifecycle
            
            with open('/tmp/webhook_debug.log', 'a') as f:
                f.write(f"  ✅ Cancelled {cancelled} follow-ups for contact {contact_id}\n")
            
            if cancelled > 0:
                current_app.logger.info(
                    f"Cancelled {cancelled} pending follow-ups for contact {contact_id} - tag manually removed"
                )
                
                # Aggiorna statistiche
                if lifecycle:
                    config = RespondIOFollowupConfig.query.filter_by(lifecycle=lifecycle).first()
                    if config:
                        config.total_cancelled = (config.total_cancelled or 0) + cancelled
            else:
                current_app.logger.warning(f"No pending follow-ups found to cancel for contact {contact_id}")
        
        # Se è stato aggiunto il tag "in_attesa_followup_1" manualmente (raro ma possibile)
        if 'in_attesa_followup_1' in tags_added and lifecycle in FOLLOWUP_ENABLED_LIFECYCLES:
            # Verifica se non c'è già un follow-up pending
            existing = RespondIOFollowupQueue.query.filter_by(
                contact_id=contact_id,
                lifecycle=lifecycle,
                status='pending'
            ).first()
            
            if not existing:
                # Schedula un nuovo follow-up
                from .followup_tasks import schedule_followup
                from datetime import timedelta
                
                # Ottieni info canale
                channel_name, channel_source = RespondIOContactChannel.get_channel(contact_id)
                if channel_name:
                    import pytz
                    import random
                    from sqlalchemy import and_
                    
                    rome_tz = pytz.timezone('Europe/Rome')
                    rome_now = datetime.now(rome_tz)
                    # Schedula tra 12 ore in timezone italiano
                    scheduled_rome = rome_now + timedelta(hours=12)
                    original_scheduled = scheduled_rome  # Salva orario originale
                    
                    # QUIET PERIOD: Se il follow-up cade tra mezzanotte e le 6:59, posticipa alle 7:00
                    quiet_start_hour = 0
                    quiet_end_hour = 7
                    
                    if scheduled_rome.hour >= quiet_start_hour and scheduled_rome.hour < quiet_end_hour:
                        # Trova l'orario base (7:00 dello stesso giorno)
                        base_time = scheduled_rome.replace(hour=quiet_end_hour, minute=0, second=0, microsecond=0)
                        
                        # Conta follow-up già schedulati
                        start_window = base_time.astimezone(pytz.UTC).replace(tzinfo=None)
                        end_window = (base_time + timedelta(hours=1)).astimezone(pytz.UTC).replace(tzinfo=None)
                        
                        existing_count = RespondIOFollowupQueue.query.filter(
                            and_(
                                RespondIOFollowupQueue.status == 'pending',
                                RespondIOFollowupQueue.scheduled_at >= start_window,
                                RespondIOFollowupQueue.scheduled_at < end_window
                            )
                        ).count()
                        
                        # Distribuisci i follow-up
                        delay_seconds = existing_count * 30
                        scheduled_rome = base_time + timedelta(seconds=delay_seconds)
                        
                        # Randomizzazione
                        random_offset = random.randint(0, 10)
                        scheduled_rome = scheduled_rome + timedelta(seconds=random_offset)
                        
                        current_app.logger.info(
                            f"Manual tag follow-up postponed to {scheduled_rome.strftime('%H:%M:%S')} (quiet hours)"
                        )
                    
                    # Salva come UTC nel database (senza timezone info per SQLAlchemy)
                    scheduled_at_utc = scheduled_rome.astimezone(pytz.UTC).replace(tzinfo=None)
                    # Per Celery, usa il datetime con timezone
                    scheduled_at_for_celery = scheduled_rome.astimezone(pytz.UTC)
                    
                    followup = RespondIOFollowupQueue(
                        contact_id=contact_id,
                        lifecycle=lifecycle,
                        channel_name=channel_name,
                        scheduled_at=scheduled_at_utc,  # Usa UTC per database
                        original_scheduled_at=original_scheduled.astimezone(pytz.UTC).replace(tzinfo=None) if original_scheduled != scheduled_rome else None,
                        status='pending',
                        tag_waiting='in_attesa_followup_1',
                        tag_sent='followup_1_inviato'
                    )
                    db.session.add(followup)
                    db.session.flush()
                    
                    task = schedule_followup.apply_async(
                        args=[followup.id],
                        eta=scheduled_at_for_celery  # Usa datetime con timezone per Celery
                    )
                    followup.celery_task_id = task.id
                    
                    current_app.logger.info(
                        f"Scheduled follow-up for contact {contact_id} - tag manually added"
                    )
        
        db.session.commit()
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        current_app.logger.error(f'Error processing tag updated webhook: {str(e)}')
        db.session.rollback()
        # IMPORTANTE: Sempre 200 OK per evitare disconnessioni
        return jsonify({'status': 'ok', 'error': 'logged'}), 200


def register_webhook_handlers(app):
    """Registra configurazioni webhook nell'app"""
    # Le route sono già registrate sopra con @bp.route
    pass