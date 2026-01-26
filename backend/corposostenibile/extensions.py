"""
corposostenibile.extensions
===========================

Bootstrap di **tutte** le estensioni condivise:

* SQLAlchemy (+ Continuum)      → ``db``
* Flask-Migrate                 → ``migrate``
* Marshmallow                   → ``ma``
* Celery                        → ``celery``
* SQLAlchemy-Searchable         → FTS PostgreSQL
* Flask-Login                   → ``login_manager``
* Flask-WTF CSRF                → ``csrf``
* Flask-Babel                   → ``babel``   ← i18n / lazy_gettext
* Flask-Sock                    → ``sock``    (WebSocket layer)
* **Flask-Dance Google OAuth2** → ``google_bp``
* Redis                         → ``redis_client`` (per cache e WebSocket)
* Flask-Limiter                 → ``limiter`` (per rate limiting)
* APScheduler                   → ``scheduler`` (per task periodici)
* Flask-Mail                    → ``mail`` (per invio email)

‼️  *make_versioned()* va chiamato **prima** di importare i modelli
    così Continuum genera correttamente le *version-tables*; analogamente
    *make_searchable()* va chiamato prima di creare le tabelle per aggiungere
    i trigger FTS.
"""
from __future__ import annotations

from typing import Optional, Dict, Any, Callable
import redis
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime, timedelta
import logging

# ────────────────────────────────────────────────────────────────────────────
#  ORM + VERSIONING (SQLAlchemy-Continuum)
# ────────────────────────────────────────────────────────────────────────────
from sqlalchemy_continuum import make_versioned, versioning_manager

# Configure versioning (user tracking disabled until database migration)
make_versioned(user_cls=None)  # abilita il versioning senza tracciamento utente per ora

# ────────────────────────────────────────────────────────────────────────────
#  ORM core + FTS + SERIALISATION
# ────────────────────────────────────────────────────────────────────────────
from flask_sqlalchemy import SQLAlchemy             # noqa: E402 – dopo make_versioned
from sqlalchemy_searchable import make_searchable   # noqa: E402
from flask_marshmallow import Marshmallow           # noqa: E402
from flask_migrate import Migrate                   # noqa: E402
from celery import Celery                           # noqa: E402
from flask_sock import Sock                         # noqa: E402
from flask_login import LoginManager                # noqa: E402
from flask_wtf import CSRFProtect                   # noqa: E402
from flask_babel import Babel                       # noqa: E402
from flask import Blueprint                         # noqa: E402
from flask_dance.contrib.google import make_google_blueprint  # noqa: E402
from flask_mail import Mail                         # noqa: E402  # NUOVO IMPORT
from flask_socketio import SocketIO                 # noqa: E402

# APScheduler per task periodici (opzionale se non usi Celery)
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.jobstores.redis import RedisJobStore
    from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False
    BackgroundScheduler = None  # type: ignore

# ────────────────────────── ISTANZE GLOBALI ────────────────────────────────
db: SQLAlchemy = SQLAlchemy()
ma: Marshmallow = Marshmallow()
migrate: Migrate = Migrate()
csrf: CSRFProtect = CSRFProtect()
babel: Babel = Babel()
celery: Celery = Celery("corposostenibile")
sock: Sock = Sock()
login_manager: LoginManager = LoginManager()
mail: Mail = Mail()  # NUOVA ISTANZA GLOBALE
socketio: SocketIO = SocketIO()  # WebSocket support

# Rate limiter per API
limiter: Limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri="redis://localhost:6379/5"  # DB Redis dedicato per rate limiting
)

# blueprint Google OAuth2 (inizializzato dentro init_app)
google_bp: Optional["Blueprint"] = None

# Redis client globale (inizializzato in init_app)
redis_client: Optional[redis.Redis] = None

# APScheduler globale (inizializzato in init_app)
scheduler: Optional[BackgroundScheduler] = None

# Logger per scheduler
scheduler_logger = logging.getLogger('apscheduler')

# FTS su *tutte* le tabelle che verranno dichiarate successivamente
make_searchable(db.metadata)

# ────────────────────────────────────────────────────────────────────────────
#  Continuum – compatibilità 1.3 / 1.4
# ────────────────────────────────────────────────────────────────────────────
try:  # Continuum ≤ 1.3.x
    _modifier = versioning_manager.transaction_cls.modifier  # type: ignore[attr-defined]
except AttributeError:  # Continuum ≥ 1.4
    _modifier = None

if _modifier:

    @_modifier  # type: ignore[arg-type]
    def _current_user_id() -> int | None:  # noqa: D401
        """ID utente loggato (o *None*), usato da Continuum."""
        try:
            from flask_login import current_user
        except Exception:  # pragma: no cover
            return None
        return getattr(current_user, "id", None)

else:
    # Continuum ≥ 1.4 – usa il plugin dedicato
    from sqlalchemy_continuum.plugins import FlaskPlugin  # type: ignore

    if not any(isinstance(p, FlaskPlugin) for p in versioning_manager.plugins):
        versioning_manager.plugins.append(FlaskPlugin())

# helper opzionale (solo Continuum ≤ 1.3.x)
try:
    from sqlalchemy_continuum import make_version_tables  # type: ignore
except ImportError:  # Continuum ≥ 1.4
    make_version_tables = None  # pyright: ignore[reportGeneralTypeIssues]

# ────────────────────────────────────────────────────────────────────────────
#  BOOTSTRAP FUNCTION
# ────────────────────────────────────────────────────────────────────────────
def init_app(app):  # noqa: D401
    """
    Collega tutte le estensioni all'istanza **Flask** *app*.
    Da chiamare nella *application-factory* **prima** di importare i modelli.
    """
    global google_bp, redis_client, scheduler  # pylint: disable=global-statement

    # ── SQLAlchemy / Marshmallow / Migrate ────────────────────────────────
    db.init_app(app)
    ma.init_app(app)
    migrate.init_app(app, db)
    
    # ── SQLAlchemy-Continuum Plugin ────────────────────────────────────
    # Plugin disabled until database migration for user_id column
    # try:
    #     from corposostenibile.versioning_plugin import FlaskLoginPlugin
    #     versioning_manager.plugins.append(FlaskLoginPlugin())
    #     app.logger.debug("[extensions] FlaskLoginPlugin registered for versioning")
    # except ImportError:
    #     app.logger.warning("[extensions] Could not import FlaskLoginPlugin")

    # ── Flask-Mail ────────────────────────────────────────────────  # NUOVA SEZIONE
    mail.init_app(app)
    app.logger.info("[extensions] Flask-Mail initialized")
    
    # ── Flask-SocketIO ──────────────────────────────────────────────
    socketio.init_app(app, cors_allowed_origins="*", async_mode='threading')
    app.logger.info("[extensions] Flask-SocketIO initialized")

    # ── CSRF (Flask-WTF) ────────────────────────────────────────────────
    csrf.init_app(app)

    # ── Babel (i18n) ────────────────────────────────────────────────────
    babel.init_app(app, default_locale="it")

    # ── Rate Limiter ────────────────────────────────────────────────────
    limiter.init_app(app)
    # Configura storage Redis per rate limiting se specificato
    if app.config.get("PERISKOPE_RATE_LIMIT"):
        limiter._storage_uri = "redis://localhost:6379/5"

    # ── Redis Client ────────────────────────────────────────────────────
    # Inizializza Redis client per WebSocket messaging
    redis_url = app.config.get("WEBSOCKET_MESSAGE_QUEUE", "redis://localhost:6379/3")
    try:
        redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30
        )
        # Test connessione
        redis_client.ping()
        app.logger.info(f"[extensions] Redis connected: {redis_url}")
    except (redis.ConnectionError, redis.TimeoutError, OSError) as e:
        app.logger.warning(f"[extensions] Redis connection failed: {e}")
        # In development, possiamo procedere senza Redis
        redis_client = None

    # ── Celery ──────────────────────────────────────────────────────────
    celery.conf.update(app.config)              # type: ignore[arg-type]
    celery.app = app                            # type: ignore[attr-defined]
    celery.flask_app = app

    class _ContextTask(celery.Task):  # type: ignore[misc]  # pragma: no cover
        """Esegue ogni task dentro un app-context automatico."""

        def __call__(self, *args, **kwargs):  # noqa: ANN001
            from flask import current_app as _flask_app

            with _flask_app.app_context():
                return super().__call__(*args, **kwargs)

    celery.Task = _ContextTask  # type: ignore[assignment]

    # ── APScheduler (Alternativa a Celery) ─────────────────────────────
    if HAS_APSCHEDULER and app.config.get("USE_APSCHEDULER", False):
        scheduler = _init_scheduler(app)
    else:
        scheduler = None
        if app.config.get("USE_APSCHEDULER", False):
            app.logger.warning("[extensions] APScheduler requested but not installed")

    # ── Flask-Login ─────────────────────────────────────────────────────
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    if not login_manager.refresh_view:
        # vista da raggiungere se il session-cookie è scaduto
        login_manager.refresh_view = login_manager.login_view

    if "REMEMBER_COOKIE_DURATION" in app.config:
        login_manager.remember_cookie_duration = app.config["REMEMBER_COOKIE_DURATION"]

    # ── WebSocket (Sock) ────────────────────────────────────────────────
    sock.init_app(app)
    # Configura ping/pong per mantenere connessioni vive
    if hasattr(sock, 'websocket_ping_interval'):
        sock.websocket_ping_interval = app.config.get('WEBSOCKET_PING_INTERVAL', 25)
        sock.websocket_ping_timeout = app.config.get('WEBSOCKET_PING_TIMEOUT', 10)

    # ── Google OAuth2 (Flask-Dance) ────────────────────────────────────
    if app.config.get("GOOGLE_CLIENT_ID") and app.config.get("GOOGLE_CLIENT_SECRET"):
        # normalizza GOOGLE_SCOPES: accetta str, tuple, list o set
        scopes_cfg = app.config.get(
            "GOOGLE_SCOPES",
            (
                "https://www.googleapis.com/auth/calendar",
                "https://www.googleapis.com/auth/calendar.events",
            ),
        )
        if isinstance(scopes_cfg, str):
            scopes = scopes_cfg.split()
        else:  # list / tuple / set
            scopes = list(scopes_cfg)

        if not google_bp:
            google_bp = make_google_blueprint(
                client_id=app.config["GOOGLE_CLIENT_ID"],
                client_secret=app.config["GOOGLE_CLIENT_SECRET"],
                scope=scopes,
                redirect_to="calendar.calendar_connect",  # endpoint che completa l'OAuth
                offline=True,          # ✅ chiede refresh_token
                reprompt_consent=True,  # forza nuova schermata di consenso se già concesso
            )

        # registra sempre (evita doppio registro in test multipli)
        if google_bp.name not in app.blueprints:
            app.register_blueprint(google_bp, url_prefix="/oauth/google")
            app.logger.debug("[extensions] Google OAuth blueprint registered")

    # ── Continuum: crea version-tables (solo helper ≤ 1.3.x) ───────────
    if make_version_tables:  # pragma: no cover
        with app.app_context():
            make_version_tables(
                db.metadata,
                engine=db.engine,
                session=db.session,
            )

# ────────────────────────────────────────────────────────────────────────────
#  SCHEDULER INITIALIZATION
# ────────────────────────────────────────────────────────────────────────────

def _init_scheduler(app) -> Optional[BackgroundScheduler]:
    """
    Inizializza APScheduler con configurazione appropriata.
    
    Args:
        app: Flask application instance
        
    Returns:
        BackgroundScheduler configurato o None se non disponibile
    """
    if not HAS_APSCHEDULER:
        return None
    
    # Configurazione jobstores
    jobstores = {}
    
    # Se Redis è disponibile, usa RedisJobStore per persistenza
    if redis_client and app.config.get("SCHEDULER_USE_REDIS", True):
        try:
            jobstores['default'] = RedisJobStore(
                db=app.config.get("SCHEDULER_REDIS_DB", 4),
                host=app.config.get("REDIS_HOST", "localhost"),
                port=app.config.get("REDIS_PORT", 6379),
                password=app.config.get("REDIS_PASSWORD")
            )
            app.logger.info("[extensions] APScheduler using Redis jobstore")
        except Exception as e:
            app.logger.warning(f"[extensions] Failed to setup Redis jobstore: {e}")
    
    # Configurazione executors
    executors = {
        'default': ThreadPoolExecutor(app.config.get("SCHEDULER_THREAD_POOL_SIZE", 10)),
        'processpool': ProcessPoolExecutor(app.config.get("SCHEDULER_PROCESS_POOL_SIZE", 2))
    }
    
    # Configurazione job defaults
    job_defaults = {
        'coalesce': True,  # Se multiple esecuzioni mancate, esegui solo una volta
        'max_instances': 1,  # Max istanze concorrenti per job
        'misfire_grace_time': app.config.get("SCHEDULER_MISFIRE_GRACE_TIME", 300)  # 5 minuti
    }
    
    # Crea scheduler
    global scheduler
    scheduler = BackgroundScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone=app.config.get("SCHEDULER_TIMEZONE", "UTC"),
        daemon=True
    )
    
    # Configura logging
    if app.debug:
        scheduler_logger.setLevel(logging.DEBUG)
    else:
        scheduler_logger.setLevel(logging.INFO)
    
    # Registra shutdown handler
    import atexit
    atexit.register(lambda: scheduler.shutdown(wait=False))
    
    # Start scheduler
    scheduler.start()
    app.logger.info("[extensions] APScheduler started successfully")
    
    return scheduler

# ────────────────────────────────────────────────────────────────────────────
#  HELPER FUNCTIONS
# ────────────────────────────────────────────────────────────────────────────

def get_redis_client() -> Optional[redis.Redis]:
    """
    Ritorna il client Redis globale.
    Utile per accedere a Redis da blueprint e servizi.
    """
    return redis_client


def is_redis_available() -> bool:
    """
    Verifica se Redis è disponibile e funzionante.
    """
    if not redis_client:
        return False
    try:
        redis_client.ping()
        return True
    except (redis.ConnectionError, AttributeError):
        return False


def get_cache_key(prefix: str, *args) -> str:
    """
    Genera una chiave cache standardizzata.
    
    Args:
        prefix: Prefisso per la chiave (es. "chatter:chats")
        *args: Parti aggiuntive della chiave
        
    Returns:
        Chiave formattata (es. "chatter:chats:123456789:active")
    """
    parts = [prefix] + [str(arg) for arg in args if arg is not None]
    return ":".join(parts)


def invalidate_cache_pattern(pattern: str) -> int:
    """
    Invalida tutte le chiavi cache che matchano un pattern.
    
    Args:
        pattern: Pattern Redis (es. "chatter:chats:*")
        
    Returns:
        Numero di chiavi eliminate
    """
    if not redis_client:
        return 0
    
    try:
        keys = redis_client.keys(pattern)
        if keys:
            return redis_client.delete(*keys)
        return 0
    except redis.ConnectionError:
        return 0



# ────────────────────────────────────────────────────────────────────────────
#  SCHEDULER HELPER FUNCTIONS
# ────────────────────────────────────────────────────────────────────────────

def get_scheduler() -> Optional[BackgroundScheduler]:
    """
    Ritorna l'istanza globale di APScheduler.
    
    Returns:
        BackgroundScheduler instance o None se non configurato
    """
    return scheduler


def is_scheduler_available() -> bool:
    """
    Verifica se lo scheduler è disponibile e running.
    
    Returns:
        True se scheduler è attivo
    """
    return scheduler is not None and scheduler.running


def schedule_task(
    func: Callable,
    trigger: str = "interval",
    **kwargs
) -> Optional[str]:
    """
    Helper per schedulare un task con APScheduler.
    
    Args:
        func: Funzione da eseguire
        trigger: Tipo di trigger ('interval', 'cron', 'date')
        **kwargs: Parametri per il trigger
        
    Returns:
        Job ID o None se scheduler non disponibile
        
    Examples:
        # Ogni 5 minuti
        schedule_task(my_func, trigger='interval', minutes=5)
        
        # Ogni giorno alle 10:30
        schedule_task(my_func, trigger='cron', hour=10, minute=30)
        
        # Una volta sola a una data specifica
        schedule_task(my_func, trigger='date', run_date=datetime(2024, 12, 25))
    """
    if not scheduler or not scheduler.running:
        return None
    
    try:
        # Separa i parametri del job da quelli del trigger
        job_params = {}
        trigger_params = {}
        
        # Parametri specifici del job
        job_specific = ['id', 'name', 'replace_existing', 'max_instances', 'coalesce']
        for key in job_specific:
            if key in kwargs:
                job_params[key] = kwargs.pop(key)
        
        # I rimanenti kwargs sono per il trigger
        trigger_params = kwargs
        
        # Crea il trigger appropriato
        if trigger == 'interval':
            trigger_obj = IntervalTrigger(**trigger_params)
        elif trigger == 'cron':
            trigger_obj = CronTrigger(**trigger_params)
        elif trigger == 'date':
            from apscheduler.triggers.date import DateTrigger
            trigger_obj = DateTrigger(**trigger_params)
        else:
            raise ValueError(f"Unknown trigger type: {trigger}")
        
        # Aggiungi il job con i parametri corretti
        job = scheduler.add_job(
            func,
            trigger=trigger_obj,
            id=job_params.get('id'),
            name=job_params.get('name'),
            replace_existing=job_params.get('replace_existing', True),
            max_instances=job_params.get('max_instances', 1),
            coalesce=job_params.get('coalesce', True)
        )
        
        return job.id
        
    except Exception as e:
        logging.error(f"Failed to schedule task: {e}")
        return None


def unschedule_task(job_id: str) -> bool:
    """
    Rimuove un task schedulato.
    
    Args:
        job_id: ID del job da rimuovere
        
    Returns:
        True se rimosso con successo
    """
    if not scheduler:
        return False
    
    try:
        scheduler.remove_job(job_id)
        return True
    except Exception:
        return False


def get_scheduled_jobs() -> Dict[str, Any]:
    """
    Ritorna informazioni sui job schedulati.
    
    Returns:
        Dict con info sui job attivi
    """
    if not scheduler:
        return {}
    
    jobs = {}
    for job in scheduler.get_jobs():
        jobs[job.id] = {
            'name': job.name,
            'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
            'trigger': str(job.trigger),
            'pending': job.pending,
            'func': job.func.__name__ if hasattr(job.func, '__name__') else str(job.func)
        }
    
    return jobs


def pause_scheduler() -> bool:
    """
    Mette in pausa lo scheduler.
    
    Returns:
        True se messo in pausa con successo
    """
    if not scheduler or not scheduler.running:
        return False
    
    try:
        scheduler.pause()
        return True
    except Exception:
        return False


def resume_scheduler() -> bool:
    """
    Riprende lo scheduler dalla pausa.
    
    Returns:
        True se ripreso con successo
    """
    if not scheduler:
        return False
    
    try:
        scheduler.resume()
        return True
    except Exception:
        return False


def reschedule_task(
    job_id: str,
    trigger: str = "interval",
    **kwargs
) -> bool:
    """
    Modifica lo scheduling di un task esistente.
    
    Args:
        job_id: ID del job da rischedulare
        trigger: Nuovo tipo di trigger
        **kwargs: Nuovi parametri per il trigger
        
    Returns:
        True se rischedulato con successo
    """
    if not scheduler:
        return False
    
    try:
        # Crea nuovo trigger
        if trigger == 'interval':
            trigger_obj = IntervalTrigger(**kwargs)
        elif trigger == 'cron':
            trigger_obj = CronTrigger(**kwargs)
        else:
            raise ValueError(f"Unknown trigger type: {trigger}")
        
        # Modifica il job
        scheduler.reschedule_job(job_id, trigger=trigger_obj)
        return True
        
    except Exception as e:
        logging.error(f"Failed to reschedule task: {e}")
        return False