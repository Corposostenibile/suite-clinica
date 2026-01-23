"""
Task Celery per respond.io
"""

from datetime import date, datetime, timedelta
from celery import shared_task
from corposostenibile.extensions import db
from .services import FunnelAnalyticsService
from corposostenibile.models import (
    RESPOND_IO_CHANNELS, 
    RespondIOContactChannel,
    RespondIOMessageHistory
)
import logging

logger = logging.getLogger(__name__)


@shared_task
def recalculate_daily_metrics(target_date=None, channel_source=None):
    """
    Ricalcola le metriche giornaliere.
    Chiamato dai webhook o schedulato.
    """
    if target_date is None:
        target_date = date.today()
    elif isinstance(target_date, str):
        target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        
    FunnelAnalyticsService.recalculate_daily_metrics(target_date, channel_source)
    return f"Metriche ricalcolate per {target_date}"


@shared_task
def recalculate_historical_metrics(days_back=7):
    """
    Ricalcola metriche storiche per gli ultimi N giorni.
    Utile per correggere dati o dopo un downtime.
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days_back)
    
    current_date = start_date
    while current_date <= end_date:
        for channel in RESPOND_IO_CHANNELS.keys():
            FunnelAnalyticsService.recalculate_daily_metrics(current_date, channel)
        current_date += timedelta(days=1)
    
    return f"Ricalcolate metriche per {days_back} giorni"




@shared_task
def cleanup_old_contact_channels():
    """
    Task automatico per pulire i contact channels vecchi.
    Esegue ogni notte alle 3:00 AM.
    Rimuove record più vecchi di 48 ore.
    """
    try:
        from corposostenibile import create_app
        app = create_app('production')
        
        with app.app_context():
            # Pulisce record più vecchi di 48 ore
            deleted_count = RespondIOContactChannel.cleanup_old_records(days=2)
            
            logger.info(
                f"[RESPOND.IO CLEANUP] Rimossi {deleted_count} contact channels "
                f"obsoleti alle {datetime.utcnow()}"
            )
            
            return {
                'status': 'success',
                'deleted': deleted_count,
                'timestamp': datetime.utcnow().isoformat()
            }
        
    except Exception as e:
        logger.error(f"[RESPOND.IO CLEANUP] Errore durante pulizia: {str(e)}")
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


@shared_task
def cleanup_message_history():
    """
    Task automatico per pulire i message history vecchi.
    Esegue ogni notte alle 2:00 AM.
    Rimuove record più vecchi di 48 ore.
    """
    try:
        from corposostenibile import create_app
        app = create_app('production')
        
        with app.app_context():
            deleted_count = RespondIOMessageHistory.cleanup_old_records(days=2)
            
            logger.info(
                f"[RESPOND.IO MESSAGE HISTORY CLEANUP] Rimossi {deleted_count} record "
                f"obsoleti alle {datetime.utcnow()}"
            )
            
            return {
                'status': 'success',
                'deleted': deleted_count,
                'timestamp': datetime.utcnow().isoformat()
            }
        
    except Exception as e:
        logger.error(f"[RESPOND.IO MESSAGE HISTORY CLEANUP] Errore durante pulizia: {str(e)}")
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


def register_tasks():
    """Registra task periodici con Celery Beat"""
    # Ricalcola metriche ogni ora
    recalculate_daily_metrics.apply_async(args=[], countdown=60)
    
    # Per schedulare task periodici, configurare in celery beat schedule