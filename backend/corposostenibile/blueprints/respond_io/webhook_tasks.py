"""
Task Celery per gestione webhook e health check
"""

from datetime import datetime
from celery import shared_task
from flask import current_app
import logging

logger = logging.getLogger(__name__)


@shared_task
def process_webhook_queue():
    """
    Processa la coda dei webhook in background.
    Eseguito ogni minuto per processare webhook in attesa.
    """
    try:
        from flask import Flask
        from corposostenibile.config import Config
        from corposostenibile.extensions import db
        
        app = Flask(__name__)
        app.config.from_object(Config.get('production'))
        db.init_app(app)
        
        with app.app_context():
            from .webhook_health import webhook_health_manager
            
            # Processa tutti i tipi di webhook in coda
            webhook_health_manager.process_queue()
            
            logger.info("Webhook queue processed successfully")
            return {'status': 'success', 'timestamp': datetime.utcnow().isoformat()}
            
    except Exception as e:
        logger.error(f"Error processing webhook queue: {str(e)}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def webhook_health_check():
    """
    Esegue health check completo dei webhook.
    Verifica stato, identifica problemi e genera alert.
    Eseguito ogni 5 minuti.
    """
    try:
        from flask import Flask
        from corposostenibile.config import Config
        from corposostenibile.extensions import db
        
        app = Flask(__name__)
        app.config.from_object(Config.get('production'))
        db.init_app(app)
        
        with app.app_context():
            from .webhook_health import webhook_health_manager
            
            # Esegui health check
            health = webhook_health_manager.health_check()
            
            # Se ci sono problemi, genera alert
            if health['status'] != 'healthy':
                logger.warning(f"Webhook health degraded: {health['issues']}")
                
                # Invia notifica (email/Slack/etc)
                _send_health_alert(health)
            
            logger.info(f"Webhook health check: {health['status']}")
            return health
            
    except Exception as e:
        logger.error(f"Error in webhook health check: {str(e)}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def webhook_auto_recovery():
    """
    Tenta recovery automatico per webhook non funzionanti.
    Riprocessa falliti, pulisce vecchi, verifica configurazione.
    Eseguito ogni 15 minuti.
    """
    try:
        from flask import Flask
        from corposostenibile.config import Config
        from corposostenibile.extensions import db
        
        app = Flask(__name__)
        app.config.from_object(Config.get('production'))
        db.init_app(app)
        
        with app.app_context():
            from .webhook_health import webhook_health_manager
            
            # Esegui auto-recovery
            webhook_health_manager.auto_recovery()
            
            logger.info("Webhook auto-recovery completed")
            return {'status': 'success', 'timestamp': datetime.utcnow().isoformat()}
            
    except Exception as e:
        logger.error(f"Error in webhook auto-recovery: {str(e)}")
        return {'status': 'error', 'error': str(e)}


@shared_task
def reprocess_failed_webhooks(limit=100):
    """
    Riprocessa manualmente webhook falliti.
    Può essere chiamato on-demand per recovery manuale.
    
    Args:
        limit: Numero massimo di webhook da riprocessare
    """
    try:
        from flask import Flask
        from corposostenibile.config import Config
        from corposostenibile.extensions import db
        from corposostenibile.models import RespondIOWebhookQueue
        
        app = Flask(__name__)
        app.config.from_object(Config.get('production'))
        db.init_app(app)
        
        with app.app_context():
            from .webhook_health import webhook_health_manager
            
            # Trova webhook falliti
            failed = RespondIOWebhookQueue.query.filter(
                RespondIOWebhookQueue.status.in_(['failed', 'retry'])
            ).order_by(RespondIOWebhookQueue.created_at.desc()).limit(limit).all()
            
            processed = 0
            errors = 0
            
            for webhook in failed:
                try:
                    webhook_health_manager._process_webhook_real(
                        webhook.webhook_type,
                        webhook.payload
                    )
                    webhook.status = 'processed'
                    webhook.processed_at = datetime.utcnow()
                    processed += 1
                    
                except Exception as e:
                    logger.error(f"Failed to reprocess webhook {webhook.webhook_id}: {e}")
                    webhook.last_error = str(e)
                    errors += 1
            
            db.session.commit()
            
            logger.info(f"Reprocessed {processed} webhooks, {errors} errors")
            return {
                'status': 'success',
                'processed': processed,
                'errors': errors,
                'timestamp': datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error reprocessing failed webhooks: {str(e)}")
        return {'status': 'error', 'error': str(e)}


def _send_health_alert(health):
    """
    Invia alert per problemi di salute webhook.
    
    Args:
        health: Dizionario con stato di salute
    """
    try:
        # Prepara messaggio
        message = f"""
        ⚠️ WEBHOOK HEALTH ALERT
        
        Status: {health['status']}
        Time: {health['timestamp']}
        
        Issues:
        {chr(10).join('- ' + issue for issue in health['issues'])}
        
        Webhook Status:
        """
        
        for webhook_type, wh_health in health['webhooks'].items():
            if wh_health['status'] != 'healthy':
                message += f"\n- {webhook_type}: {wh_health['status']}"
                if 'issue' in wh_health:
                    message += f" ({wh_health['issue']})"
        
        # Log critico
        logger.critical(message)
        
        # TODO: Implementare invio email/Slack
        # send_email_notification(message)
        # send_slack_notification(message)
        
    except Exception as e:
        logger.error(f"Failed to send health alert: {e}")


@shared_task
def webhook_statistics_report():
    """
    Genera report statistiche webhook.
    Eseguito giornalmente per monitoraggio.
    """
    try:
        from flask import Flask
        from corposostenibile.config import Config
        from corposostenibile.extensions import db
        from sqlalchemy import func
        from datetime import timedelta
        
        app = Flask(__name__)
        app.config.from_object(Config.get('production'))
        db.init_app(app)
        
        with app.app_context():
            from corposostenibile.models import RespondIOWebhookLog
            
            yesterday = datetime.utcnow() - timedelta(days=1)
            
            # Statistiche per tipo
            stats = db.session.query(
                RespondIOWebhookLog.webhook_type,
                func.count(RespondIOWebhookLog.id).label('total'),
                func.sum(func.case(
                    [(RespondIOWebhookLog.status == 'processed', 1)],
                    else_=0
                )).label('processed'),
                func.sum(func.case(
                    [(RespondIOWebhookLog.status == 'failed', 1)],
                    else_=0
                )).label('failed')
            ).filter(
                RespondIOWebhookLog.received_at >= yesterday
            ).group_by(
                RespondIOWebhookLog.webhook_type
            ).all()
            
            report = {
                'date': yesterday.date().isoformat(),
                'webhook_stats': {},
                'totals': {
                    'received': 0,
                    'processed': 0,
                    'failed': 0
                }
            }
            
            for webhook_type, total, processed, failed in stats:
                report['webhook_stats'][webhook_type] = {
                    'total': total,
                    'processed': processed or 0,
                    'failed': failed or 0,
                    'success_rate': ((processed or 0) / total * 100) if total > 0 else 0
                }
                
                report['totals']['received'] += total
                report['totals']['processed'] += processed or 0
                report['totals']['failed'] += failed or 0
            
            # Calcola success rate totale
            if report['totals']['received'] > 0:
                report['totals']['success_rate'] = (
                    report['totals']['processed'] / report['totals']['received'] * 100
                )
            else:
                report['totals']['success_rate'] = 0
            
            logger.info(f"Webhook statistics report: {report}")
            return report
            
    except Exception as e:
        logger.error(f"Error generating webhook statistics: {str(e)}")
        return {'status': 'error', 'error': str(e)}