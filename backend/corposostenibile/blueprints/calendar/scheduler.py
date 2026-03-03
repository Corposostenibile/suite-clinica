"""
calendar.scheduler
==================

Scheduler per task periodici del blueprint calendar.

Utilizza APScheduler per eseguire automaticamente:
- Refresh token Google OAuth ogni 5 minuti
- Cleanup token scaduti ogni giorno
- Monitoring salute token ogni ora
"""

import logging
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from .tasks import refresh_google_tokens_task, cleanup_expired_tokens_task, monitor_token_health

logger = logging.getLogger(__name__)

# Scheduler globale
scheduler = None


def init_scheduler(app: Flask):
    """
    Inizializza lo scheduler APScheduler per i task periodici.

    Args:
        app: Istanza Flask app
    """
    global scheduler

    if scheduler is not None:
        logger.warning("Scheduler già inizializzato, skip")
        return

    try:
        google_oauth_enabled = bool(app.config.get("GOOGLE_CLIENT_ID") and app.config.get("GOOGLE_CLIENT_SECRET"))

        # Crea scheduler in background
        scheduler = BackgroundScheduler(
            daemon=True,
            timezone='Europe/Rome'
        )

        # ─────────────────────────────────────────────────────────────
        # JOB 1: Refresh token ogni 5 minuti
        # ─────────────────────────────────────────────────────────────
        if google_oauth_enabled:
            scheduler.add_job(
                func=lambda: _run_in_app_context(app, refresh_google_tokens_task),
                trigger=IntervalTrigger(minutes=5),
                id='refresh_google_tokens',
                name='Refresh Google OAuth Tokens',
                replace_existing=True,
                max_instances=1,  # Evita esecuzioni concorrenti
                misfire_grace_time=120  # Tolleranza 2 minuti se il server è occupato
            )
            logger.info("✅ Job 'Refresh Google Tokens' schedulato ogni 5 minuti")
        else:
            logger.info("⏭️ Job 'Refresh Google Tokens' non schedulato: GOOGLE_CLIENT_ID/SECRET mancanti")

        # ─────────────────────────────────────────────────────────────
        # JOB 2: Cleanup token scaduti ogni giorno alle 3:00 AM
        # ─────────────────────────────────────────────────────────────
        scheduler.add_job(
            func=lambda: _run_in_app_context(app, cleanup_expired_tokens_task),
            trigger=CronTrigger(hour=3, minute=0, timezone='Europe/Rome'),
            id='cleanup_expired_tokens',
            name='Cleanup Expired Google Tokens',
            replace_existing=True,
            max_instances=1
        )
        logger.info("✅ Job 'Cleanup Expired Tokens' schedulato ogni giorno alle 3:00 AM")

        # ─────────────────────────────────────────────────────────────
        # JOB 3: Monitoring salute token ogni ora
        # ─────────────────────────────────────────────────────────────
        if google_oauth_enabled:
            scheduler.add_job(
                func=lambda: _run_in_app_context(app, monitor_token_health),
                trigger=IntervalTrigger(hours=1),
                id='monitor_token_health',
                name='Monitor Google Token Health',
                replace_existing=True,
                max_instances=1
            )
            logger.info("✅ Job 'Monitor Token Health' schedulato ogni ora")
        else:
            logger.info("⏭️ Job 'Monitor Token Health' non schedulato: GOOGLE_CLIENT_ID/SECRET mancanti")

        # Avvia scheduler
        scheduler.start()
        logger.info("🚀 Scheduler Calendar avviato con successo")

        # Registra shutdown handler
        import atexit
        atexit.register(lambda: shutdown_scheduler())

    except Exception as e:
        logger.error(f"❌ Errore inizializzazione scheduler: {e}", exc_info=True)


def _run_in_app_context(app: Flask, func):
    """
    Esegue una funzione all'interno del contesto Flask app.

    APScheduler esegue i job in thread separati, quindi dobbiamo
    assicurarci di avere l'app context attivo per accedere al database.

    Args:
        app: Istanza Flask app
        func: Funzione da eseguire
    """
    with app.app_context():
        try:
            return func()
        except Exception as e:
            logger.error(f"Errore nell'esecuzione task {func.__name__}: {e}", exc_info=True)


def shutdown_scheduler():
    """Ferma lo scheduler in modo pulito."""
    global scheduler

    if scheduler and scheduler.running:
        logger.info("🛑 Arresto scheduler...")
        scheduler.shutdown(wait=False)
        logger.info("✅ Scheduler arrestato")


def get_scheduler_status():
    """
    Restituisce lo stato dello scheduler e dei job.

    Returns:
        Dict con info su scheduler e job
    """
    global scheduler

    if not scheduler:
        return {'running': False, 'jobs': []}

    jobs_info = []
    for job in scheduler.get_jobs():
        jobs_info.append({
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
            'trigger': str(job.trigger)
        })

    return {
        'running': scheduler.running,
        'jobs': jobs_info,
        'num_jobs': len(jobs_info)
    }
