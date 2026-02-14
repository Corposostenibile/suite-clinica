"""
corposostenibile/__init__.py
============================
Application-factory principale.
- Inizializza estensioni (db, migrate, celery, …)
- Registra gli ENUM Postgres (una sola volta, solo se non esistono)
- Monta tutti i blueprint core (auth, customers, team, department, hr,
  nutrition, ticket, …)
- Integrazione Google OAuth2 (blueprint Flask-Dance) – registrata prima di Calendar
- Imposta ACL minimale in-memory
- Registra CLI custom, filtri Jinja "date", "datetime", "time_ago" …
- Opzionale: lint di tutti i template in DEBUG per intercettare errori Jinja

================================================================================
INDICE DI NAVIGAZIONE RAPIDA - __INIT__.PY
================================================================================

🏗️ FUNZIONE PRINCIPALE
    L220 - create_app()                  # Application factory Flask

📦 CLASSI E UTILITIES
    L47  - SimpleACL                     # Sistema ACL (Access Control List) minimale
        L53  - allow()                   # Aggiunge permesso a ruolo
        L56  - permitted()               # Verifica permesso per ruolo
        L60  - rules                     # Proprietà read-only delle regole

🔧 FUNZIONI HELPER
    L65  - _lint_templates()             # Verifica sintassi template Jinja in debug
    L91  - _register_jinja_filters()     # Registra tutti i filtri Jinja personalizzati

📋 FILTRI JINJA REGISTRATI
    L95  - date                          # Formatta date (|date)
    L104 - datetime                      # Formatta datetime (|datetime)
    L105 - nl2br                         # Newline to <br> (|nl2br)
    L106 - file_size                     # Formatta dimensioni file (|file_size)
    L110 - format_calories               # Formatta calorie nutrizione (|format_calories)
    L114 - format_macros                 # Formatta macro nutrienti (|format_macros)
    L119 - whatsapp_phone                # Formatta numero WhatsApp (|whatsapp_phone)
    L130 - time_ago/timeago              # Tempo relativo "x fa" (|time_ago)
    L178 - truncate_message              # Tronca messaggi lunghi (|truncate_message)
    L185 - ticket_status_label           # Label stato ticket (|ticket_status_label)
    L194 - ticket_urgency_icon           # Icona urgenza ticket (|ticket_urgency_icon)
    L206 - update_query_params           # Aggiorna parametri query (|update_query_params)

🔌 BLUEPRINT REGISTRATI
    L250-262 - Import blueprint          # Import di tutti i blueprint
    L267 - welcome                       # Homepage/Welcome
    L268 - customers                     # Gestione clienti
    L269 - auth                          # Autenticazione
    L270 - team                          # Gestione team
    L271 - department                    # Gestione dipartimenti
    L273 - hr                            # Human Resources
    L274 - nutrition                     # Modulo nutrizione
    L276 - ticket                        # Sistema ticket
    L277 - help                          # Help/Documentazione
    L282 - pwa                           # Progressive Web App

🎯 ROUTE PRINCIPALI
    L292 - /                             # Redirect a login
    L297 - Error handler generico        # Gestione errori JSON
    L309 - WebSocket error handler       # Gestione errori WebSocket

⚙️ CONFIGURAZIONI
    L224 - Caricamento config            # Config da classe + instance
    L230 - Inizializzazione estensioni   # Init di tutte le estensioni
    L236 - Google OAuth                  # Registrazione blueprint OAuth
    L239 - ENUM Postgres                 # Registrazione tipi ENUM
    L244 - ACL system                    # Sistema permessi in-memory
    L285 - Celery tasks                  # Registrazione task Celery
    L289 - CLI commands                  # Registrazione comandi CLI
    L326 - Jinja globals                 # Variabili globali template
    L334 - Context processor             # Funzioni utility template

================================================================================
"""
from __future__ import annotations

import os
from datetime import date, datetime, timezone
from http import HTTPStatus
from pathlib import Path
from types import MappingProxyType
from typing import Dict, List, Set, Union

from dateutil import parser
from flask import Flask, jsonify, redirect, url_for, request


from jinja2 import TemplateSyntaxError
from werkzeug.exceptions import HTTPException

# ══════════════════════════════════════════════════════════════════════════════ #
#                       IMPORT ESTENSIONI E HELPER                               #
# ══════════════════════════════════════════════════════════════════════════════ #
from .cli import register_cli_commands
from .config import Config
from .extensions import (
    celery,
    google_bp,
    init_app as init_exts,
    login_manager,
    get_scheduler,
    schedule_task,
    is_scheduler_available
)
from . import models as _models  # noqa: F401 – import a side-effect
from .models import register_enums

BASE_DIR = Path(__file__).resolve().parent


# ───────────────────────────── ACL minimale ────────────────────────────
class SimpleACL:
    """Mappatura `ruolo → {permessi}` con helper *allow* / *permitted*."""
    
    def __init__(self, initial: Dict[str, Set[str]] | None = None) -> None:
        self._rules: Dict[str, Set[str]] = {k: set(v) for k, v in (initial or {}).items()}
    
    def allow(self, role: str, perm: str) -> None:
        self._rules.setdefault(role, set()).add(perm)
    
    def permitted(self, role: str, perm: str) -> bool:
        return perm in self._rules.get(role, set())
    
    @property
    def rules(self) -> MappingProxyType:  # sola lettura
        return MappingProxyType(self._rules)


# ───────────────────── Lint dei template in debug ───────────────────────
def _lint_templates(app: Flask) -> None:
    if not app.debug and not app.config.get("LINT_TEMPLATES", False):
        return
    
    problems: List[str] = []
    with app.app_context():
        for tpl_name in app.jinja_env.list_templates():
            try:
                app.jinja_env.get_template(tpl_name)
            except TemplateSyntaxError as exc:
                rel = Path(exc.filename or tpl_name).as_posix()
                problems.append(f"{rel}:{exc.lineno} – {exc.message}")
                app.logger.error("[TEMPLATE-ERROR] %s", problems[-1])
    
    if problems:
        print("\n──── Template syntax errors ───────────────────────────────")
        for line in problems:
            print(line)
        print("────────────────────────────────────────────────────────────")
        raise RuntimeError(
            f"{len(problems)} template Jinja contengono errori di sintassi:\n"
            + "\n".join(problems)
        )


# ───────────────────── Filtri Jinja globali ────────────────────────────
def _register_jinja_filters(app: Flask) -> None:
    """Registra filtri |date, |datetime, |nl2br, |file_size, nutrition e ticket."""
    
    # ——— base |date
    @app.template_filter("date")
    def _fmt_date(value: Union[date, datetime, str, None], fmt: str = "%d/%m/%Y") -> str:
        if value in (None, ""):
            return ""
        if isinstance(value, (date, datetime)):
            return value.strftime(fmt)
        return str(value)
    
    # filtri comuni definiti altrove
    from .filters import datetime_filter, nl2br, file_size, rome_datetime, linkify
    app.jinja_env.filters["datetime"] = datetime_filter
    app.jinja_env.filters["nl2br"] = nl2br
    app.jinja_env.filters["file_size"] = file_size
    app.jinja_env.filters["rome_datetime"] = rome_datetime
    app.jinja_env.filters["linkify"] = linkify
    
    # ——— nutrition specific
    @app.template_filter("format_calories")
    def format_calories(value):
        return "0 kcal" if value is None else f"{int(value)} kcal"
    
    @app.template_filter("format_macros")
    def format_macros(value):
        return "0.0" if value is None else f"{value:.1f}"
    
    # ——— whatsapp phone prettify
    @app.template_filter("whatsapp_phone")
    def whatsapp_phone(value):
        if not value:
            return ""
        clean = "".join(filter(str.isdigit, str(value)))
        if len(clean) > 10:
            return f"+{clean[:2]} {clean[2:5]} {clean[5:8]} {clean[8:]}"
        return value
    
    # ——— time_ago (FIX offset-naive vs aware)
    @app.template_filter("time_ago")
    @app.template_filter("timeago")  # Alias per compatibilità con i template
    def time_ago(value):
        """
        Converte una data/ora in stringa "x minuti/ore/giorni fa" o DD/MM/YYYY
        se più vecchia di 7 giorni.
        • Accetta datetime naive o timezone-aware.
        • Accetta stringhe ISO 8601 (o formati compatibili con dateutil).
        • Non solleva eccezioni; input non gestibile → restituito com'è.
        """
        if not value:
            return ""
        
        # stringa → datetime
        if isinstance(value, str):
            try:
                value = parser.isoparse(value)
            except Exception:
                try:
                    value = parser.parse(value)
                except Exception:
                    return str(value)
        
        if not isinstance(value, datetime):
            return str(value)
        
        if value.tzinfo is not None:  # aware → UTC naive
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        
        now = datetime.utcnow()
        try:
            diff = now - value
        except TypeError:
            value = value.replace(tzinfo=None)
            diff = now - value
        
        seconds = int(diff.total_seconds())
        
        if diff.days > 7:
            return value.strftime("%d/%m/%Y")
        if diff.days >= 1:
            return f"{diff.days} giorni fa"
        if seconds >= 3600:
            return f"{seconds // 3600} ore fa"
        if seconds >= 60:
            return f"{seconds // 60} minuti fa"
        return "ora"
    
    # ——— truncate_message
    @app.template_filter("truncate_message")
    def truncate_message(value, length: int = 50):
        if not value:
            return ""
        return value if len(value) <= length else value[:length] + "..."
    
    # ——— ticket specific filters
    @app.template_filter("ticket_status_label")
    def ticket_status_label(status):
        """Converte enum status in label leggibile."""
        if not status:
            return ""
        if hasattr(status, 'value'):
            return status.value.replace('_', ' ').title()
        return str(status).replace('_', ' ').title()
    
    @app.template_filter("ticket_urgency_icon")
    def ticket_urgency_icon(urgency):
        """Ritorna icona per urgenza."""
        icons = {
            '1': '🔴',  # alta
            '2': '🟡',  # media
            '3': '🟢',  # bassa
        }
        if hasattr(urgency, 'value'):
            return icons.get(urgency.value, '')
        return icons.get(str(urgency), '')
    
    @app.template_filter("update_query_params")
    def update_query_params(args_dict, **kwargs):
        """Helper per aggiornare parametri query string."""
        updated = args_dict.copy() if isinstance(args_dict, dict) else {}
        for key, value in kwargs.items():
            if value is not None:
                updated[key] = value
            elif key in updated:
                del updated[key]
        return updated



# ───────────────────────────── Factory ─────────────────────────────────
def create_app(config_name: str | None = None) -> Flask:
    """Restituisce un'istanza Flask completamente configurata."""
    app = Flask(__name__, instance_relative_config=True)
    
    # Config da classe + instance config
    cfg_name = config_name or os.getenv("FLASK_ENV", "development")
    app.config.from_object(Config.get(cfg_name))
    app.config.from_pyfile("config.py", silent=True)
    
    # Estensioni (db, redis, login, celery, …)
    init_exts(app)
    if login_manager.refresh_view is None:
        login_manager.refresh_view = "auth.login"

    # Tracking automatico per tutti i blueprint
    from corposostenibile.middleware.tracking import setup_tracking_middleware
    setup_tracking_middleware(app)
    
    # Google OAuth blueprint
    if google_bp is not None and google_bp.name not in app.blueprints:
        app.register_blueprint(google_bp, url_prefix="/oauth/google")  # type: ignore[arg-type]
    
    # ENUM Postgres (solo se non in migrazione)
    if not os.getenv("ALEMBIC_RUNNING"):
        with app.app_context():
            register_enums()
    
    # ACL "semplice" in-memory
    app.acl = SimpleACL()  # type: ignore[attr-defined]
    
    # Filtri Jinja2
    _register_jinja_filters(app)
    
    # Route per servire i file caricati (avatars, etc.)
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        from flask import send_from_directory, abort
        # Use configured UPLOAD_FOLDER - ensure absolute path
        upload_folder = app.config.get('UPLOAD_FOLDER')
        if not upload_folder:
            upload_folder = str(Path(app.root_path).parent / 'uploads')

        # Ensure it's an absolute path
        upload_path = Path(upload_folder)
        if not upload_path.is_absolute():
            upload_path = Path(app.root_path).parent / upload_folder

        # Check if file exists
        full_path = upload_path / filename
        if not full_path.exists():
            app.logger.error(f"File not found: {full_path}")
            abort(404)

        return send_from_directory(str(upload_path), filename)

    # Route per servire node_modules (Loom SDK e altre librerie JS)
    @app.route('/node_modules/<path:filename>')
    def node_modules_file(filename):
        from flask import send_from_directory
        import os
        node_modules_folder = os.path.join(app.root_path, '..', 'node_modules')
        return send_from_directory(node_modules_folder, filename)

    # Blueprint core
    from .blueprints import (
        auth,
        customers,
        team,
        department,
        welcome,
        nutrition,
        ticket,  # AGGIUNTO: Import del blueprint ticket
        communications,  # AGGIUNTO: Import del blueprint communications
        respond_io,  # AGGIUNTO: Import del blueprint respond_io
        feedback,  # AGGIUNTO: Import del blueprint feedback
        review,  # AGGIUNTO: Import del blueprint review
        projects,  # AGGIUNTO: Import del blueprint projects
        knowledge_base,  # AGGIUNTO: Import del blueprint knowledge_base
        finance,  # AGGIUNTO: Import del blueprint finance
        recruiting,  # AGGIUNTO: Import del blueprint recruiting
        ghl_integration,  # AGGIUNTO: Import del blueprint GHL integration
        calendar,  # AGGIUNTO: Import del blueprint calendar
        client_checks,  # AGGIUNTO: Import del blueprint client_checks
        sales_form,  # AGGIUNTO: Import del blueprint sales_form
        suitemind,  # AGGIUNTO: Import del blueprint SuiteMind AI
        feedback_global,  # AGGIUNTO: Sistema feedback democratico globale
        manual,  # AGGIUNTO: Import del blueprint manual (documentazione suite)
        kpi,  # AGGIUNTO: Sistema KPI e ARR

        appointment_setting,  # Appointment Setting - messaggi Respond.io
        tasks,  # AGGIUNTO: Import del blueprint tasks
        documentation,  # AGGIUNTO: Import del blueprint documentation
        search,  # AGGIUNTO: Import del blueprint search
    )


    from .blueprints.blueprint_registry import bp as blueprint_registry_bp  # Blueprint Registry
    from .blueprints.database_registry import bp as database_registry_bp  # Database Models Registry
    from .blueprints.dev_tracker import bp as dev_tracker_bp  # Dev Tracker - Development Team Management
    from .blueprints.it_projects import bp as it_projects_bp  # IT Projects - Gestione Progetti IT
    from .blueprints.news import news_bp  # AGGIUNTO: Import del blueprint news

    from .blueprints.pwa import pwa_bp
    
    welcome.init_app(app)
    customers.init_app(app)
    auth.init_app(app)
    team.init_app(app)
    department.init_app(app)
    nutrition.init_app(app)
    ticket.init_app(app)  # AGGIUNTO: Inizializzazione del blueprint ticket
    communications.init_app(app)  # AGGIUNTO: Inizializzazione del blueprint communications
    respond_io.init_app(app)  # AGGIUNTO: Inizializzazione del blueprint respond_io
    review.init_app(app)  # AGGIUNTO: Inizializzazione del blueprint review
    projects.init_app(app)  # AGGIUNTO: Inizializzazione del blueprint projects
    knowledge_base.init_app(app)  # AGGIUNTO: Inizializzazione del blueprint knowledge_base
    finance.init_app(app)  # AGGIUNTO: Inizializzazione del blueprint finance
    recruiting.init_app(app)  # AGGIUNTO: Inizializzazione del blueprint recruiting
    ghl_integration.init_app(app)  # AGGIUNTO: Inizializzazione del blueprint GHL integration
    calendar.init_app(app)  # AGGIUNTO: Inizializzazione del blueprint calendar
    client_checks.init_app(app)  # AGGIUNTO: Inizializzazione del blueprint client_checks
    suitemind.init_app(app)  # AGGIUNTO: Inizializzazione del blueprint SuiteMind AI
    feedback_global.init_app(app)  # AGGIUNTO: Sistema feedback democratico globale (FASE 1+2)
    manual.init_app(app)  # AGGIUNTO: Inizializzazione del blueprint manual (documentazione suite)
    kpi.init_app(app)  # AGGIUNTO: Inizializzazione del blueprint KPI e ARR

    appointment_setting.init_app(app)  # Appointment Setting
    tasks.init_app(app)  # AGGIUNTO: Inizializzazione del blueprint tasks


    # Sales Form Blueprint
    from .blueprints.sales_form import sales_form_bp
    app.register_blueprint(sales_form_bp)

    # Route diretta per welcome-form (senza /sales-form prefix)
    from .blueprints.sales_form.public import public_form as welcome_form_view
    app.add_url_rule('/welcome-form/<string:unique_code>',
                     'welcome_form',
                     welcome_form_view,
                     methods=['GET', 'POST'])
    # Blueprint Feedback
    app.register_blueprint(feedback.bp)

    # News Blueprint
    app.register_blueprint(news_bp)  # AGGIUNTO: Registrazione del blueprint news

    # Blueprint Registry
    app.register_blueprint(blueprint_registry_bp)  # AGGIUNTO: Registrazione Blueprint Registry
    app.register_blueprint(database_registry_bp)  # AGGIUNTO: Registrazione Database Models Registry
    app.register_blueprint(dev_tracker_bp)  # AGGIUNTO: Registrazione Dev Tracker
    app.register_blueprint(it_projects_bp)  # AGGIUNTO: Registrazione IT Projects
    
    # Documentation Blueprint
    app.register_blueprint(documentation.documentation_bp, url_prefix='/documentation')

    # Quality Score
    from corposostenibile.blueprints.quality import bp as quality_bp
    app.register_blueprint(quality_bp)

    # Post-it / Promemoria
    from corposostenibile.blueprints.postit import bp as postit_bp
    app.register_blueprint(postit_bp)

    app.register_blueprint(pwa_bp)
    
    # Health check endpoint
    from .health import health_bp
    app.register_blueprint(health_bp)

    # Search Blueprint
    app.register_blueprint(search.bp, url_prefix='/api/search')
    
    # Celery tasks specifici
    from corposostenibile.blueprints.customers import init_celery as customers_celery
    customers_celery(celery)
    
    # CLI custom
    register_cli_commands(app)
    
    # ---- Serve React Frontend Assets ---- #
    # React app is served via Vite dev server in development (port 3000)
    # In production, these routes serve the built React assets
    # Check standard structure (backend/frontend)
    react_dist = Path(__file__).parent.parent / "frontend" / "dist"
    
    # Check Suite Clinica structure (suite-clinica/corposostenibile-clinica) if standard not found
    if not react_dist.exists():
        react_dist = Path(__file__).parent.parent.parent / "corposostenibile-clinica" / "dist"

    if react_dist.exists():
        from flask import send_from_directory, request as flask_request, make_response, abort

        # Override login_manager to redirect to React SPA login (not Jinja)
        app.login_manager.login_view = None

        @app.login_manager.unauthorized_handler
        def unauthorized():
            """Redirect to React login for pages, 401 for API calls."""
            if flask_request.path.startswith('/api/'):
                return jsonify({"authenticated": False, "error": "Login richiesto"}), 401
            return redirect('/login')

        @app.get("/static/clinica/<path:filename>")
        def serve_react_static_assets(filename):
            """
            Serve bundled React assets from dist under a dedicated static prefix.
            This avoids collisions with other services exposing /assets.
            """
            target = react_dist / filename
            if not target.exists() or not target.is_file():
                abort(404)
            return send_from_directory(str(react_dist), filename)

        # Paths that should NOT be intercepted (handled by Flask)
        _flask_prefixes = (
            '/api/',
            '/customers/',
            '/uploads/',
            '/oauth/',
            '/static/',
            '/quality/api/',
            '/documentation/',
            '/ghl/',
            '/review/api/',
            '/health',
            '/auth/',
        )

        @app.before_request
        def serve_spa_for_pages():
            """Intercept page requests and serve React SPA instead of Jinja templates."""
            path = flask_request.path

            # SPA fallback must never intercept API/form submissions.
            if flask_request.method not in ("GET", "HEAD"):
                return None

            # Only serve SPA for real browser page navigations.
            accepts = flask_request.accept_mimetypes
            wants_html = accepts.accept_html and accepts["text/html"] >= accepts["application/json"]
            if not wants_html:
                return None

            # Let Flask handle API, uploads, OAuth, and static routes
            if any(path.startswith(p) for p in _flask_prefixes):
                return None

            # Serve React static assets
            if path.startswith('/assets/'):
                filename = path[len('/assets/'):]
                return send_from_directory(react_dist / "assets", filename)

            # Serve static files from React dist (favicon, etc.)
            rel_path = path.lstrip('/')
            if rel_path:
                full_path = react_dist / rel_path
                if full_path.exists() and full_path.is_file():
                    return send_from_directory(str(react_dist), rel_path)

            # All other page routes: serve React SPA index.html
            return send_from_directory(str(react_dist), "index.html")

        # Fallback catch-all route for SPA (handles 404s on unknown routes)
        @app.route("/<path:path>")
        def catch_all(path):
            if any(path.startswith(p) for p in _flask_prefixes):
                abort(404)
            return send_from_directory(str(react_dist), "index.html")
    else:
        # Development: redirect to login (Vite handles React separately)
        @app.get("/")
        def index():
            return redirect(url_for("auth.login"))

    # Ensure CSRF cookie is set for SPA
    @app.after_request
    def set_csrf_cookie(response):
        if not request.path.startswith('/static') and not request.path.startswith('/assets'):
            from flask_wtf.csrf import generate_csrf
            try:
                csrf_token = generate_csrf()
                # Set cookie accessible by JS (httpOnly=False) so Axios can read it if needed, 
                # OR api.js reads it. api.js code: getCookie('csrf_token') 
                # So we must NOT use httpOnly=True.
                # secure=True matches SESSION_COOKIE_SECURE usually.
                response.set_cookie(
                    'csrf_token', 
                    csrf_token, 
                    secure=app.config.get('SESSION_COOKIE_SECURE', False),
                    samesite='Lax'
                )
            except Exception:
                pass
        return response
    
    # Error-handling JSON-first
    @app.errorhandler(Exception)
    def handle_exception(exc):
        if isinstance(exc, HTTPException):
            resp = exc.get_response()
            resp.data = jsonify({"error": exc.name, "description": exc.description}).data
            resp.content_type = "application/json"
            return resp
        return (
            jsonify({"error": "Internal Server Error", "description": str(exc)}),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )
    
    @app.errorhandler(ConnectionError)
    def handle_websocket_error(exc):
        app.logger.error("WebSocket error: %s", exc)
        return (
            jsonify(
                {
                    "error": "WebSocket Connection Error",
                    "description": "Connection to real-time service failed. Please refresh the page.",
                }
            ),
            HTTPStatus.SERVICE_UNAVAILABLE,
        )
    
    # Lint template (solo debug)
    _lint_templates(app)
    
    # Variabili globali per template
    app.jinja_env.globals.update(
        {
            # AGGIUNTO: Configurazioni ticket
            "TICKET_EMAIL_ENABLED": app.config.get("TICKET_EMAIL_ENABLED", False),
        }
    )
    
    # AGGIUNTO: Registra funzioni helper nei template Jinja
    @app.context_processor
    def utility_processor():
        """Aggiunge funzioni utility ai template."""
        from datetime import timedelta
        from corposostenibile.blueprints.ticket.permissions import can_edit_ticket, can_view_ticket
        from corposostenibile.blueprints.ticket.helpers import get_open_tickets_count
        from corposostenibile.blueprints.communications.permissions import can_create_communication, get_unread_communications_count
        from corposostenibile.blueprints.feedback.helpers import can_access_nutrition_feedback, can_access_psychology_feedback, can_access_coach_feedback
        from corposostenibile.blueprints.client_checks.helpers import get_unread_checks_count
        from corposostenibile.blueprints.review.helpers import (
            get_unread_reviews_count,
            get_unread_messages_count,
            get_total_unread_count,
            has_unread_notifications,
            get_pending_requests_count,
            get_my_pending_requests_count,
            get_total_review_notifications
        )

        def has_completed_survey(user_id, survey_id=1):
            """Check if user has completed anonymous survey."""
            from corposostenibile.models import AnonymousSurveyResponse
            if not user_id:
                return False
            return AnonymousSurveyResponse.query.filter_by(
                user_id=user_id,
                survey_id=survey_id
            ).first() is not None

        return dict(
            can_edit_ticket=can_edit_ticket,
            can_view_ticket=can_view_ticket,
            get_open_tickets_count=get_open_tickets_count,
            can_create_communication=can_create_communication,
            get_unread_communications_count=get_unread_communications_count,
            can_access_nutrition_feedback=can_access_nutrition_feedback,
            can_access_psychology_feedback=can_access_psychology_feedback,
            can_access_coach_feedback=can_access_coach_feedback,
            get_unread_checks_count=get_unread_checks_count,
            get_unread_reviews_count=get_unread_reviews_count,
            get_unread_messages_count=get_unread_messages_count,
            get_total_unread_count=get_total_unread_count,
            has_unread_notifications=has_unread_notifications,
            get_pending_requests_count=get_pending_requests_count,
            get_my_pending_requests_count=get_my_pending_requests_count,
            get_total_review_notifications=get_total_review_notifications,
            has_completed_survey=has_completed_survey,
            timedelta=timedelta
        )
    
    return app
