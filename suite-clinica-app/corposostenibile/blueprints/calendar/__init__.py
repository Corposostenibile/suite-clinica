"""
calendar blueprint
==================

Blueprint per l'integrazione Google Calendar.

Funzionalità:
- Connessione OAuth con Google Calendar
- Sincronizzazione eventi
- Gestione meeting associati ai clienti
- API per creare/modificare eventi
- Auto-refresh token OAuth
"""

from flask import Blueprint
import logging

logger = logging.getLogger(__name__)

calendar_bp = Blueprint(
    "calendar",
    __name__,
    template_folder="templates",
    static_folder="static",
    url_prefix="/calendar"
)

from . import routes

def init_app(app):
    """Inizializza il blueprint calendar nell'app Flask."""
    app.register_blueprint(calendar_bp)

    # Inizializza comandi CLI
    try:
        from .cli import init_cli
        init_cli(app)
        logger.debug("✅ Calendar CLI commands registrati")
    except Exception as e:
        logger.warning(f"⚠️ Impossibile registrare Calendar CLI: {e}")

    # Inizializza lo scheduler per auto-refresh token
    # Solo se non siamo in modalità debug o se esplicitamente abilitato
    if app.config.get('ENABLE_CALENDAR_SCHEDULER', True) and not app.debug:
        try:
            from .scheduler import init_scheduler
            init_scheduler(app)
            logger.info("✅ Calendar scheduler inizializzato")
        except Exception as e:
            logger.error(f"❌ Errore inizializzazione scheduler calendar: {e}")
    else:
        logger.info("⚠️ Calendar scheduler DISABILITATO (debug mode o config)")
