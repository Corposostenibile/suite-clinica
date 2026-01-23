"""
Sistema di Health Check e Recovery per Webhook Respond.io
Previene disconnessioni e gestisce recovery automatico
"""

import json
import time
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from flask import current_app
from sqlalchemy import and_, func
from corposostenibile.extensions import db, redis_client
from corposostenibile.models import (
    RespondIOWebhookLog,
    RespondIOWebhookHealth,
    RespondIOWebhookQueue
)

logger = logging.getLogger(__name__)


class WebhookHealthManager:
    """
    Gestisce la salute dei webhook e previene disconnessioni.
    
    Strategie implementate:
    1. Risposta sempre 200 OK (anche in caso di errore)
    2. Processamento asincrono tramite coda
    3. Retry automatico con exponential backoff
    4. Health check periodico
    5. Auto-recovery su failure
    """
    
    # Configurazione
    MAX_PROCESSING_TIME_MS = 4500  # Respond.io timeout a 5 secondi
    HEALTH_CHECK_INTERVAL = 300  # 5 minuti
    MAX_RETRIES = 3
    RETRY_DELAYS = [5, 30, 120]  # secondi
    
    # Webhook types
    WEBHOOK_TYPES = [
        'new-contact',
        'lifecycle-update',
        'incoming-message',
        'outgoing-message',
        'tag-updated'
    ]
    
    def __init__(self):
        """Inizializza il manager"""
        self.redis_key_prefix = "webhook:health:"
        self.queue_key = "webhook:queue:"
        
    def process_webhook_safe(self, webhook_type: str, data: dict) -> Tuple[bool, dict]:
        """
        Processa un webhook in modo sicuro con timeout e error handling.
        
        SEMPRE ritorna 200 OK per evitare disconnessioni!
        Il processing reale avviene in background.
        
        Args:
            webhook_type: Tipo di webhook
            data: Payload del webhook
            
        Returns:
            (success, response) - SEMPRE (True, 200 OK)
        """
        start_time = time.time()
        webhook_id = self._generate_webhook_id(webhook_type, data)
        
        try:
            # 1. Log immediato ricezione
            self._log_webhook_received(webhook_type, webhook_id, data)
            
            # 2. Verifica se già processato (deduplicazione)
            if self._is_duplicate(webhook_id):
                logger.info(f"Duplicate webhook {webhook_id} - skipping")
                return True, {'status': 'ok', 'message': 'duplicate', 'id': webhook_id}
            
            # 3. Aggiungi a coda per processamento asincrono
            self._enqueue_webhook(webhook_type, webhook_id, data)
            
            # 4. Risposta immediata (< 100ms)
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"Webhook {webhook_type} queued in {elapsed:.2f}ms")
            
            # SEMPRE RITORNA 200 OK!
            return True, {
                'status': 'ok',
                'queued': True,
                'id': webhook_id,
                'processing_time_ms': elapsed
            }
            
        except Exception as e:
            # Anche in caso di errore, ritorna 200 OK
            logger.error(f"Error processing webhook {webhook_type}: {e}", exc_info=True)
            
            # Salva per retry manuale
            self._save_failed_webhook(webhook_type, data, str(e))
            
            # COMUNQUE RITORNA 200 OK!
            return True, {
                'status': 'ok',
                'error_logged': True,
                'id': webhook_id,
                'message': 'Will retry in background'
            }
    
    def _generate_webhook_id(self, webhook_type: str, data: dict) -> str:
        """Genera ID univoco per webhook"""
        import hashlib
        
        # Usa campi univoci per tipo
        unique_fields = {
            'new-contact': ['contact.id'],
            'lifecycle-update': ['contact.id', 'lifecycle', 'oldLifecycle'],
            'incoming-message': ['message.id'],
            'outgoing-message': ['message.id'],
            'tag-updated': ['contact.id', 'tag', 'action', 'timestamp']
        }
        
        fields = unique_fields.get(webhook_type, ['timestamp'])
        
        # Estrai valori
        values = []
        for field in fields:
            value = data
            for key in field.split('.'):
                value = value.get(key, '') if isinstance(value, dict) else ''
            values.append(str(value))
        
        # Aggiungi timestamp se non presente
        if 'timestamp' not in str(values):
            values.append(str(int(time.time() * 1000)))
        
        # Genera hash
        content = f"{webhook_type}:{':'.join(values)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _is_duplicate(self, webhook_id: str) -> bool:
        """Verifica se il webhook è già stato processato"""
        if redis_client:
            key = f"{self.redis_key_prefix}processed:{webhook_id}"
            if redis_client.exists(key):
                return True
            # Marca come processato (TTL 24 ore)
            redis_client.setex(key, 86400, "1")
        return False
    
    def _enqueue_webhook(self, webhook_type: str, webhook_id: str, data: dict):
        """Aggiunge webhook a coda per processamento asincrono"""
        queue_item = {
            'id': webhook_id,
            'type': webhook_type,
            'data': data,
            'timestamp': datetime.utcnow().isoformat(),
            'attempts': 0
        }
        
        # Salva in Redis se disponibile
        if redis_client:
            queue_key = f"{self.queue_key}{webhook_type}"
            redis_client.lpush(queue_key, json.dumps(queue_item))
            logger.debug(f"Webhook {webhook_id} added to Redis queue")
        
        # Salva anche in DB per backup
        db_queue = RespondIOWebhookQueue(
            webhook_id=webhook_id,
            webhook_type=webhook_type,
            payload=data,
            status='queued',
            attempts=0
        )
        db.session.add(db_queue)
        db.session.commit()
    
    def _log_webhook_received(self, webhook_type: str, webhook_id: str, data: dict):
        """Log ricezione webhook"""
        log = RespondIOWebhookLog(
            webhook_id=webhook_id,
            webhook_type=webhook_type,
            payload=data,
            received_at=datetime.utcnow(),
            status='received'
        )
        db.session.add(log)
        db.session.commit()
    
    def _save_failed_webhook(self, webhook_type: str, data: dict, error: str):
        """Salva webhook fallito per retry manuale"""
        failed = RespondIOWebhookQueue(
            webhook_id=self._generate_webhook_id(webhook_type, data),
            webhook_type=webhook_type,
            payload=data,
            status='failed',
            error_message=error,
            attempts=1
        )
        db.session.add(failed)
        db.session.commit()
    
    def process_queue(self, webhook_type: str = None):
        """
        Processa la coda dei webhook in background.
        Chiamato da Celery task ogni minuto.
        """
        types_to_process = [webhook_type] if webhook_type else self.WEBHOOK_TYPES
        
        for wh_type in types_to_process:
            self._process_queue_for_type(wh_type)
    
    def _process_queue_for_type(self, webhook_type: str):
        """Processa coda per un tipo specifico"""
        # Prima prova Redis
        if redis_client:
            queue_key = f"{self.queue_key}{webhook_type}"
            
            while True:
                # Prendi item dalla coda
                item_json = redis_client.rpop(queue_key)
                if not item_json:
                    break
                
                try:
                    item = json.loads(item_json)
                    self._process_webhook_item(item)
                except Exception as e:
                    logger.error(f"Error processing queued webhook: {e}")
                    # Re-queue con delay
                    if item.get('attempts', 0) < self.MAX_RETRIES:
                        item['attempts'] = item.get('attempts', 0) + 1
                        redis_client.lpush(queue_key, json.dumps(item))
        
        # Processa anche da DB (backup)
        self._process_db_queue(webhook_type)
    
    def _process_db_queue(self, webhook_type: str):
        """Processa webhook dalla coda database"""
        queued = RespondIOWebhookQueue.query.filter(
            RespondIOWebhookQueue.webhook_type == webhook_type,
            RespondIOWebhookQueue.status.in_(['queued', 'retry']),
            RespondIOWebhookQueue.attempts < self.MAX_RETRIES
        ).order_by(RespondIOWebhookQueue.created_at).limit(10).all()
        
        for item in queued:
            try:
                # Processa il webhook reale
                self._process_webhook_real(item.webhook_type, item.payload)
                
                # Marca come completato
                item.status = 'processed'
                item.processed_at = datetime.utcnow()
                
            except Exception as e:
                logger.error(f"Error processing webhook {item.webhook_id}: {e}")
                item.attempts += 1
                item.last_error = str(e)
                
                if item.attempts >= self.MAX_RETRIES:
                    item.status = 'failed'
                else:
                    item.status = 'retry'
                    # Schedule retry con backoff
                    delay = self.RETRY_DELAYS[min(item.attempts - 1, len(self.RETRY_DELAYS) - 1)]
                    item.retry_after = datetime.utcnow() + timedelta(seconds=delay)
        
        db.session.commit()
    
    def _process_webhook_real(self, webhook_type: str, data: dict):
        """
        Processa realmente il webhook (chiamando il handler originale).
        Questo avviene in background, quindi può prendersi il tempo necessario.
        """
        from . import webhooks
        
        handlers = {
            'new-contact': webhooks.process_new_contact,
            'lifecycle-update': webhooks.process_lifecycle_update,
            'incoming-message': webhooks.process_incoming_message,
            'outgoing-message': webhooks.process_outgoing_message,
            'tag-updated': webhooks.process_tag_updated
        }
        
        handler = handlers.get(webhook_type)
        if handler:
            handler(data)
        else:
            logger.warning(f"No handler for webhook type {webhook_type}")
    
    def health_check(self) -> Dict:
        """
        Esegue health check completo dei webhook.
        
        Returns:
            Dict con stato di salute
        """
        health = {
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'healthy',
            'webhooks': {},
            'issues': []
        }
        
        # Check per ogni tipo di webhook
        for webhook_type in self.WEBHOOK_TYPES:
            wh_health = self._check_webhook_health(webhook_type)
            health['webhooks'][webhook_type] = wh_health
            
            if wh_health['status'] != 'healthy':
                health['status'] = 'degraded'
                health['issues'].append(f"{webhook_type}: {wh_health['issue']}")
        
        # Check coda
        queue_health = self._check_queue_health()
        health['queue'] = queue_health
        
        if queue_health['status'] != 'healthy':
            health['status'] = 'degraded'
            health['issues'].extend(queue_health['issues'])
        
        # Salva stato
        self._save_health_status(health)
        
        return health
    
    def _check_webhook_health(self, webhook_type: str) -> Dict:
        """Check salute per un tipo specifico di webhook"""
        # Ottieni ultime statistiche
        last_hour = datetime.utcnow() - timedelta(hours=1)
        
        stats = db.session.query(
            func.count(RespondIOWebhookLog.id).label('total'),
            func.sum(case((RespondIOWebhookLog.status == 'processed', 1), else_=0)).label('processed'),
            func.sum(case((RespondIOWebhookLog.status == 'failed', 1), else_=0)).label('failed'),
            func.max(RespondIOWebhookLog.received_at).label('last_received')
        ).filter(
            RespondIOWebhookLog.webhook_type == webhook_type,
            RespondIOWebhookLog.received_at >= last_hour
        ).first()
        
        health = {
            'total_last_hour': stats.total or 0,
            'processed': stats.processed or 0,
            'failed': stats.failed or 0,
            'last_received': stats.last_received.isoformat() if stats.last_received else None,
            'status': 'healthy'
        }
        
        # Determina stato
        if stats.failed and stats.total:
            failure_rate = (stats.failed / stats.total) * 100
            if failure_rate > 10:
                health['status'] = 'unhealthy'
                health['issue'] = f"High failure rate: {failure_rate:.1f}%"
            elif failure_rate > 5:
                health['status'] = 'degraded'
                health['issue'] = f"Elevated failure rate: {failure_rate:.1f}%"
        
        # Check se non riceve da troppo tempo (solo per webhook attivi)
        if webhook_type in ['incoming-message', 'outgoing-message']:
            if not stats.last_received or (datetime.utcnow() - stats.last_received) > timedelta(hours=2):
                health['status'] = 'warning'
                health['issue'] = "No recent webhooks received"
        
        return health
    
    def _check_queue_health(self) -> Dict:
        """Check salute della coda"""
        health = {
            'status': 'healthy',
            'queued': 0,
            'failed': 0,
            'retry': 0,
            'issues': []
        }
        
        # Conta items in coda
        counts = db.session.query(
            RespondIOWebhookQueue.status,
            func.count(RespondIOWebhookQueue.id)
        ).group_by(RespondIOWebhookQueue.status).all()
        
        for status, count in counts:
            if status == 'queued':
                health['queued'] = count
            elif status == 'failed':
                health['failed'] = count
            elif status == 'retry':
                health['retry'] = count
        
        # Determina stato
        if health['failed'] > 100:
            health['status'] = 'unhealthy'
            health['issues'].append(f"Too many failed webhooks: {health['failed']}")
        elif health['queued'] > 500:
            health['status'] = 'degraded'
            health['issues'].append(f"Large queue backlog: {health['queued']}")
        
        return health
    
    def _save_health_status(self, health: Dict):
        """Salva stato di salute"""
        health_record = RespondIOWebhookHealth(
            status=health['status'],
            details=health,
            checked_at=datetime.utcnow()
        )
        db.session.add(health_record)
        db.session.commit()
    
    def auto_recovery(self):
        """
        Tenta recovery automatico per webhook non funzionanti.
        Chiamato ogni 15 minuti da Celery.
        """
        logger.info("Starting webhook auto-recovery check")
        
        # 1. Riprocessa webhook falliti
        self._retry_failed_webhooks()
        
        # 2. Pulisce webhook duplicati/vecchi
        self._cleanup_old_webhooks()
        
        # 3. Verifica e ripara configurazione Respond.io
        self._verify_respond_config()
    
    def _retry_failed_webhooks(self):
        """Riprova webhook falliti"""
        retry_window = datetime.utcnow() - timedelta(minutes=30)
        
        failed = RespondIOWebhookQueue.query.filter(
            RespondIOWebhookQueue.status == 'retry',
            RespondIOWebhookQueue.retry_after <= datetime.utcnow(),
            RespondIOWebhookQueue.created_at >= retry_window
        ).limit(50).all()
        
        for webhook in failed:
            try:
                self._process_webhook_real(webhook.webhook_type, webhook.payload)
                webhook.status = 'processed'
                webhook.processed_at = datetime.utcnow()
                logger.info(f"Successfully retried webhook {webhook.webhook_id}")
            except Exception as e:
                webhook.attempts += 1
                webhook.last_error = str(e)
                if webhook.attempts >= self.MAX_RETRIES:
                    webhook.status = 'failed'
        
        db.session.commit()
    
    def _cleanup_old_webhooks(self):
        """Pulisce webhook vecchi"""
        cutoff = datetime.utcnow() - timedelta(days=7)
        
        # Elimina log vecchi processati
        deleted = RespondIOWebhookLog.query.filter(
            RespondIOWebhookLog.received_at < cutoff,
            RespondIOWebhookLog.status == 'processed'
        ).delete()
        
        # Elimina queue items vecchi
        deleted += RespondIOWebhookQueue.query.filter(
            RespondIOWebhookQueue.created_at < cutoff,
            RespondIOWebhookQueue.status.in_(['processed', 'failed'])
        ).delete()
        
        db.session.commit()
        
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old webhook records")
    
    def _verify_respond_config(self):
        """Verifica configurazione webhook in Respond.io"""
        # Questo potrebbe chiamare l'API di Respond.io per verificare
        # che i webhook siano ancora configurati correttamente
        pass


# Singleton instance
webhook_health_manager = WebhookHealthManager()