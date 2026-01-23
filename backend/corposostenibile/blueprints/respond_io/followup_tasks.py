"""
Task Celery per sistema follow-up automatico Respond.io
"""

from datetime import datetime, timedelta
from celery import shared_task
from flask import current_app
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def schedule_followup(self, followup_id, test_mode=False):
    """
    Task principale per inviare follow-up.
    Verifica condizioni e invia messaggio/template appropriato.
    
    Args:
        followup_id: ID del follow-up da processare
        test_mode: Se True, simula l'invio senza chiamare l'API
    """
    try:
        # Crea app context per tutto il task
        from flask import Flask
        from corposostenibile.config import Config
        from corposostenibile.extensions import db
        
        app = Flask(__name__)
        app.config.from_object(Config.get('production'))
        db.init_app(app)
        
        with app.app_context():
            # Import modelli dentro il context
            from corposostenibile.models import (
                RespondIOFollowupQueue,
                RespondIOFollowupConfig,
                RespondIOMessageHistory,
                RespondIOContactChannel
            )
            
            # Recupera il follow-up dalla queue CON LOCK PESSIMISTICO
            # Questo previene che due worker processino lo stesso follow-up
            followup = RespondIOFollowupQueue.query.with_for_update(skip_locked=True).filter_by(
                id=followup_id,
                status='pending'  # Solo se è ancora pending
            ).first()
            
            if not followup:
                # Il follow-up non esiste, è già processato o è locked da un altro worker
                logger.info(f"Follow-up {followup_id} not found or already being processed")
                return
            
            # IMPORTANTE: Marchiamo subito come 'processing' per evitare duplicati
            followup.status = 'processing'
            db.session.commit()
            
            logger.info(f"Processing follow-up {followup_id} for contact {followup.contact_id}")
            
            # Inizializza client API
            from corposostenibile.blueprints.respond_io.client import RespondIOClient
            client = RespondIOClient(app.config)
            
            # In modalità test, salta tutte le verifiche API
            if test_mode:
                logger.info(f"TEST MODE: Skipping API verifications for follow-up {followup_id}")
            else:
                # Verifica se il contatto ha ancora il tag "in_attesa_followup_1"
                contact = client.get_contact(followup.contact_id)
                if not contact:
                    followup.status = 'failed'
                    followup.error_message = 'Contact not found'
                    db.session.commit()
                    return
                
                tags = contact.get('tags', [])
                if followup.tag_waiting not in tags:
                    # Il tag è stato rimosso, non inviare follow-up
                    followup.status = 'cancelled'
                    followup.cancelled_at = datetime.utcnow()
                    followup.error_message = 'Tag was removed - follow-up cancelled'
                    db.session.commit()
                    
                    logger.info(f"Follow-up {followup_id} cancelled - tag not present")
                    return
                
            # Determina se usare messaggio normale o template
            if test_mode:
                # In test mode, simula casualmente
                import random
                is_within_24h = random.choice([True, False])
                logger.info(f"TEST MODE: Simulating 24h window = {is_within_24h}")
            else:
                # IMPORTANTE: Se non abbiamo dati certi sulla finestra 24h, usiamo template per sicurezza
                is_within_24h = RespondIOMessageHistory.is_within_24h_window(followup.contact_id)
                
                # Se non abbiamo dati nella history locale, proviamo con l'API
                if not is_within_24h:
                    # Verifica anche tramite API Respond.io
                    is_within_24h = client.check_24h_window(followup.contact_id)
                
            # Log per debug
            logger.info(f"Contact {followup.contact_id} - 24h window check: {is_within_24h}")
            
            # Ottieni configurazione follow-up
            config = RespondIOFollowupConfig.query.filter_by(lifecycle=followup.lifecycle).first()
            if not config:
                config = RespondIOFollowupConfig(
                    lifecycle=followup.lifecycle,
                    enabled=True,
                    delay_hours=12,
                    message_text="Ciao 💪 Stai bene?",
                    template_name="followup_generico1",
                    tag_waiting="in_attesa_followup_1",
                    tag_sent="followup_1_inviato"
                )
                db.session.add(config)
            
            # Invia messaggio
            # POLICY: Se non siamo sicuri della finestra 24h, usiamo SEMPRE il template
            # per evitare errori di invio. Meglio essere conservativi.
            try:
                if test_mode:
                    # MODALITÀ TEST: Simula l'invio senza chiamare l'API
                    logger.warning(f"TEST MODE: Simulazione invio follow-up a {followup.contact_id}")
                    
                    if is_within_24h:
                        followup.message_type = 'text'
                        followup.message_sent = f"[TEST] {config.message_text}"
                        logger.info(f"TEST: Simulato invio messaggio normale a {followup.contact_id}")
                    else:
                        followup.message_type = 'template'
                        followup.message_sent = f"[TEST] Template: {config.template_name}"
                        logger.info(f"TEST: Simulato invio template a {followup.contact_id}")
                    
                    result = {"status": "test_success"}
                    
                elif is_within_24h:
                    # Invia messaggio normale SOLO se siamo certi di essere dentro le 24h
                    result = client.send_message(
                        followup.contact_id,
                        config.message_text,
                        channel_id=followup.channel_id
                    )
                    followup.message_type = 'text'
                    followup.message_sent = config.message_text
                    logger.info(f"Sent normal message to {followup.contact_id}")
                else:
                    # Invia template WhatsApp
                    result = client.send_template_message(
                        followup.contact_id,
                        config.template_name,
                        channel_id=followup.channel_id,
                        language='it'
                    )
                    followup.message_type = 'template'
                    followup.message_sent = f"Template: {config.template_name}"
                    logger.info(f"Sent template message to {followup.contact_id}")
                
                # Aggiorna stato follow-up
                followup.status = 'sent'
                followup.sent_at = datetime.utcnow()
                
                # Rimuovi tag di attesa e aggiungi tag di invio (solo se non in test mode)
                if not test_mode:
                    # Usa i tag dalla config o quelli di default
                    tag_waiting = config.tag_waiting if config else "in_attesa_followup_1"
                    tag_sent = config.tag_sent if config else "followup_1_inviato"
                    
                    try:
                        client.remove_tags(followup.contact_id, [tag_waiting])
                        logger.info(f"Removed tag '{tag_waiting}' from contact {followup.contact_id}")
                        
                        with open('/home/devops/corposostenibile-suite/logs/tag_operations.log', 'a') as f:
                            f.write(f"{datetime.utcnow().isoformat()} - FOLLOWUP TAG REMOVED: Removed '{tag_waiting}' from contact {followup.contact_id} after sending follow-up\n")
                    except Exception as e:
                        logger.error(f"Error removing tag: {e}")
                        
                        with open('/home/devops/corposostenibile-suite/logs/tag_operations.log', 'a') as f:
                            f.write(f"{datetime.utcnow().isoformat()} - FOLLOWUP TAG ERROR: Failed to remove '{tag_waiting}' from contact {followup.contact_id}: {e}\n")
                    
                    try:
                        client.add_tags(followup.contact_id, [tag_sent])
                        logger.info(f"Added tag '{tag_sent}' to contact {followup.contact_id}")
                        
                        with open('/home/devops/corposostenibile-suite/logs/tag_operations.log', 'a') as f:
                            f.write(f"{datetime.utcnow().isoformat()} - FOLLOWUP TAG ADDED: Added '{tag_sent}' to contact {followup.contact_id} after sending follow-up\n")
                    except Exception as e:
                        logger.error(f"Error adding tag: {e}")
                        
                        with open('/home/devops/corposostenibile-suite/logs/tag_operations.log', 'a') as f:
                            f.write(f"{datetime.utcnow().isoformat()} - FOLLOWUP TAG ERROR: Failed to add '{tag_sent}' to contact {followup.contact_id}: {e}\n")
                else:
                    logger.info(f"TEST: Simulata rimozione tag '{config.tag_waiting if config else 'in_attesa_followup_1'}' e aggiunta tag '{config.tag_sent if config else 'followup_1_inviato'}'")
                
                # Aggiorna statistiche
                config.total_sent = (config.total_sent or 0) + 1
                
                db.session.commit()
                
                logger.info(f"Follow-up {followup_id} sent successfully")
                return {'status': 'sent', 'message_type': followup.message_type}
                
            except Exception as e:
                logger.error(f"Error sending follow-up {followup_id}: {str(e)}")
                
                # Retry se possibile
                if self.request.retries < self.max_retries:
                    # Rimetti lo stato a 'pending' per il retry
                    followup.status = 'pending'
                    db.session.commit()
                    raise self.retry(exc=e, countdown=300)  # Retry dopo 5 minuti
                
                # Altrimenti marca come fallito
                followup.status = 'failed'
                followup.error_message = str(e)
                db.session.commit()
                return {'status': 'failed', 'error': str(e)}
                    
    except Exception as e:
        logger.error(f"Critical error in follow-up task {followup_id}: {str(e)}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def cleanup_old_followups():
    """
    Pulizia periodica dei follow-up vecchi.
    Rimuove record completati/cancellati più vecchi di 7 giorni.
    """
    try:
        from flask import Flask
        from corposostenibile.config import Config
        from corposostenibile.extensions import db
        
        app = Flask(__name__)
        app.config.from_object(Config.get('production'))
        db.init_app(app)
        
        with app.app_context():
            from corposostenibile.models import RespondIOFollowupQueue
            
            cutoff = datetime.utcnow() - timedelta(days=7)
            
            deleted = RespondIOFollowupQueue.query.filter(
                RespondIOFollowupQueue.status.in_(['sent', 'cancelled', 'failed']),
                RespondIOFollowupQueue.created_at < cutoff
            ).delete()
            
            db.session.commit()
            
            logger.info(f"Cleaned up {deleted} old follow-up records")
            return {'deleted': deleted}
        
    except Exception as e:
        logger.error(f"Error cleaning up follow-ups: {str(e)}")
        return {'error': str(e)}


@shared_task
def check_pending_followups():
    """
    Verifica follow-up pending che potrebbero essere rimasti bloccati.
    Eseguito ogni ora per sicurezza.
    """
    try:
        from flask import Flask
        from corposostenibile.config import Config
        from corposostenibile.extensions import db
        
        app = Flask(__name__)
        app.config.from_object(Config.get('production'))
        db.init_app(app)
        
        with app.app_context():
            from corposostenibile.models import RespondIOFollowupQueue
            
            # Trova follow-up che dovevano essere inviati ma sono ancora pending
            overdue = RespondIOFollowupQueue.query.filter(
                RespondIOFollowupQueue.status == 'pending',
                RespondIOFollowupQueue.scheduled_at < datetime.utcnow() - timedelta(minutes=30)
            ).all()
            
            processed = 0
            for followup in overdue:
                # Prova a processare
                schedule_followup.apply_async(args=[followup.id])
                processed += 1
            
            if processed > 0:
                logger.warning(f"Found and reprocessed {processed} overdue follow-ups")
            
            return {'processed': processed}
        
    except Exception as e:
        logger.error(f"Error checking pending follow-ups: {str(e)}")
        return {'error': str(e)}


@shared_task
def generate_followup_report():
    """
    Genera report giornaliero sui follow-up.
    """
    try:
        from flask import Flask
        from corposostenibile.config import Config
        from corposostenibile.extensions import db
        from datetime import date
        from sqlalchemy import func
        
        app = Flask(__name__)
        app.config.from_object(Config.get('production'))
        db.init_app(app)
        
        with app.app_context():
            from corposostenibile.models import RespondIOFollowupQueue
            
            today = date.today()
            yesterday = today - timedelta(days=1)
            
            # Statistiche del giorno
            stats = db.session.query(
                RespondIOFollowupQueue.lifecycle,
                RespondIOFollowupQueue.status,
                func.count(RespondIOFollowupQueue.id).label('count')
            ).filter(
                func.date(RespondIOFollowupQueue.created_at) == yesterday
            ).group_by(
                RespondIOFollowupQueue.lifecycle,
                RespondIOFollowupQueue.status
            ).all()
            
            report = {
                'date': yesterday.isoformat(),
                'stats': {}
            }
            
            for lifecycle, status, count in stats:
                if lifecycle not in report['stats']:
                    report['stats'][lifecycle] = {}
                report['stats'][lifecycle][status] = count
            
            # Calcola totali
            report['totals'] = {
                'scheduled': sum(s.get('pending', 0) for s in report['stats'].values()),
                'sent': sum(s.get('sent', 0) for s in report['stats'].values()),
                'cancelled': sum(s.get('cancelled', 0) for s in report['stats'].values()),
                'failed': sum(s.get('failed', 0) for s in report['stats'].values())
            }
            
            logger.info(f"Follow-up report for {yesterday}: {report}")
            return report
        
    except Exception as e:
        logger.error(f"Error generating follow-up report: {str(e)}")
        return {'error': str(e)}