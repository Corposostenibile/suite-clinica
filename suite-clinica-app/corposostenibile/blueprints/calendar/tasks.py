"""
calendar.tasks
==============

Background tasks per il blueprint calendar.

Funzionalità:
- Refresh periodico token Google OAuth
- Monitoraggio scadenze
- Cleanup token scaduti
"""

import logging
from datetime import datetime, timedelta
from typing import Dict

from corposostenibile.extensions import db
from corposostenibile.models import GoogleAuth
from .services import GoogleTokenRefreshService

logger = logging.getLogger(__name__)


def refresh_google_tokens_task() -> Dict[str, int]:
    """
    Task periodico per refreshare i token Google OAuth in scadenza.

    Questo task dovrebbe essere eseguito ogni 5 minuti da un scheduler
    (APScheduler, Celery, cron job, etc.)

    Returns:
        Dict con statistiche del refresh: {'refreshed': N, 'failed': M}
    """
    logger.info("🔄 Avvio task refresh token Google OAuth")

    try:
        # Refresha tutti i token che scadono entro 10 minuti
        stats = GoogleTokenRefreshService.refresh_all_expiring_tokens(threshold_minutes=10)

        logger.info(f"✅ Task refresh completato: {stats}")
        return stats

    except Exception as e:
        logger.error(f"❌ Errore nel task refresh token: {e}", exc_info=True)
        return {'refreshed': 0, 'failed': 0, 'skipped': 0}


def cleanup_expired_tokens_task() -> int:
    """
    Task periodico per eliminare token completamente scaduti e irrecuperabili.

    Questo task dovrebbe essere eseguito una volta al giorno.

    Returns:
        Numero di token eliminati
    """
    logger.info("🧹 Avvio task cleanup token scaduti")

    try:
        # Elimina token scaduti da più di 7 giorni (ormai irrecuperabili)
        threshold = datetime.utcnow() - timedelta(days=7)

        expired_tokens = GoogleAuth.query.filter(
            GoogleAuth.expires_at < threshold
        ).all()

        count = len(expired_tokens)

        if count > 0:
            logger.warning(f"Trovati {count} token scaduti da più di 7 giorni, eliminazione in corso...")

            for google_auth in expired_tokens:
                try:
                    user_id = google_auth.user_id
                    db.session.delete(google_auth)
                    logger.info(f"Token eliminato per user {user_id}")
                except Exception as e:
                    logger.error(f"Errore eliminazione token: {e}")

            db.session.commit()
            logger.info(f"✅ Cleanup completato: {count} token eliminati")
        else:
            logger.info("✅ Nessun token da eliminare")

        return count

    except Exception as e:
        logger.error(f"❌ Errore nel task cleanup token: {e}", exc_info=True)
        return 0


def monitor_token_health() -> Dict:
    """
    Task di monitoraggio per controllare lo stato di salute dei token.

    Returns:
        Dict con metriche di salute
    """
    logger.info("📊 Avvio monitoring salute token")

    try:
        status_list = GoogleTokenRefreshService.get_token_expiry_status()

        total = len(status_list)
        expired = sum(1 for s in status_list if s['is_expired'])
        expiring_soon = sum(1 for s in status_list if s['needs_refresh'] and not s['is_expired'])
        healthy = total - expired - expiring_soon

        metrics = {
            'total_tokens': total,
            'healthy': healthy,
            'expiring_soon': expiring_soon,
            'expired': expired,
            'timestamp': datetime.utcnow().isoformat()
        }

        logger.info(f"📊 Metriche token: {metrics}")

        # Log warning se ci sono troppi token scaduti
        if expired > 0:
            logger.warning(f"⚠️ Attenzione: {expired} token scaduti richiedono riautenticazione")

        return metrics

    except Exception as e:
        logger.error(f"❌ Errore nel monitoring token: {e}", exc_info=True)
        return {}
