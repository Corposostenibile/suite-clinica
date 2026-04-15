"""
corposostenibile.config
=======================

Configurazione gerarchica (*Base* → env-specifica) per **Corposostenibile**.

Key points
----------
* legge la stringa di connessione da ``DATABASE_URL`` (fallback SQLite *dev.db*)
* abilita di default il **versioning** di SQLAlchemy-Continuum
* esporta impostazioni pronte per **Celery**, **Flask-Mail**, **CSRF**
* integra le chiavi e gli scope Google
* gestisce upload file con limiti e percorsi configurabili
* configurazioni specifiche per il modulo Nutrition
* consente override segreti in ``instance/config.py`` (NON versionato)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Type

# ====== IMPORTANTE: Carica le variabili d'ambiente dal file .env ======
from dotenv import load_dotenv

# Carica il file .env PRIMA di leggere qualsiasi variabile d'ambiente
load_dotenv()

# root del progetto
BASE_DIR = Path(__file__).resolve().parent.parent


class BaseConfig:
    # ---------------------------------------------------------------- Flask
    DEBUG: bool = False
    TESTING: bool = False
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-prod-pls")

    # Server configuration per URL generation
    SERVER_NAME: str | None = os.getenv("SERVER_NAME", None)
    PREFERRED_URL_SCHEME: str = os.getenv("PREFERRED_URL_SCHEME", "https")

    # ---------------------------------------------------------------- Session cookies
    # Letti dalle env var impostate in k8s/deployment.yaml
    SESSION_COOKIE_SECURE: bool = str(os.getenv("SESSION_COOKIE_SECURE", "0")).lower() in ("1", "true", "yes")
    SESSION_COOKIE_HTTPONLY: bool = str(os.getenv("SESSION_COOKIE_HTTPONLY", "1")).lower() in ("1", "true", "yes")
    SESSION_COOKIE_SAMESITE: str | None = os.getenv("SESSION_COOKIE_SAMESITE", "Lax") or None

    # ---------------------------------------------------------------- DB
    # IMPORTANTE: Ora leggerà correttamente dal .env file
    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'dev.db'}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # Debug: stampa l'URI del database (rimuovi in produzione)
    @classmethod
    def init_app(cls, app):
        """Hook di inizializzazione per verificare la configurazione."""
        print(f"[CONFIG] Using database: {cls.SQLALCHEMY_DATABASE_URI}")

    # ------------------ SQLAlchemy-Continuum -----------------------
    SQLALCHEMY_CONTINUUM_VERSIONING: bool = True
    CONTINUUM_NATIVE_VERSIONING: bool = False      # compat Postgres < 9.6

    # --------------------------- Celery ----------------------------
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    CELERY_TASK_ALWAYS_EAGER: bool = False          # True → esecuzione inline (dev)
    
    # Celery Beat Schedule - Import dalla configurazione centralizzata
    from corposostenibile.celery_config import CELERYBEAT_SCHEDULE, CELERY_TIMEZONE, CELERY_ENABLE_UTC
    beat_schedule = CELERYBEAT_SCHEDULE
    timezone = CELERY_TIMEZONE
    enable_utc = CELERY_ENABLE_UTC
    
    # Celery Beat Schedule per follow-up
    USE_CELERY: bool = bool(int(os.getenv("USE_CELERY", "1")))
    USE_APSCHEDULER: bool = bool(int(os.getenv("USE_APSCHEDULER", "0")))

    # -------------------------- Mail -------------------------------
    MAIL_SERVER: str          = os.getenv("MAIL_SERVER", "localhost")
    MAIL_PORT: int            = int(os.getenv("MAIL_PORT", "25"))
    MAIL_USE_TLS: bool        = bool(int(os.getenv("MAIL_USE_TLS", "0")))
    MAIL_USERNAME: str | None = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD: str | None = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER: str  = os.getenv("MAIL_DEFAULT_SENDER", "noreply@corposostenibile.local")
    
    # -------------------------- Ticket Email -----------------------
    TICKET_EMAIL_ENABLED: bool = bool(int(os.getenv("TICKET_EMAIL_ENABLED", "0")))

    # ---------------------- Microsoft Teams Bot --------------------
    TEAMS_BOT_APP_ID: str = os.getenv("TEAMS_BOT_APP_ID", "")
    TEAMS_BOT_APP_PASSWORD: str = os.getenv("TEAMS_BOT_APP_PASSWORD", "")
    TEAMS_BOT_TENANT_ID: str = os.getenv("TEAMS_BOT_TENANT_ID", "")

    # --------------------------- CSRF ------------------------------
    WTF_CSRF_ENABLED: bool = True                   # disattivare solo nei test
    WTF_CSRF_EXEMPT_LIST: list = [
        # COMMENTATO: Webhook di respond_io disabilitati
        # 'respond_io.webhook_new_contact',
        # 'respond_io.webhook_lifecycle_update',
        # 'respond_io.webhook_incoming_message',
        # 'respond_io.webhook_outgoing_message',
        # 'respond_io.webhook_tag_updated',
        'customers.update_multiple_fields',  # API endpoint per update cliente
        'customers_api_v1.api_update',  # REST API PATCH endpoint
        'customers.history_restore_view',  # Endpoint per ripristino versioni
        # SuiteMind API endpoints
        'suitemind.chat_api',  # API endpoint per chat
        # Knowledge Base API endpoints - usando i nomi esatti delle funzioni
        'kb.api_create_category',
        'kb.api_update_category', 
        'kb.api_delete_category',
        'kb.api_reorder_categories',
        'kb.api_toggle_category',
        'kb.api_upload_file',
        'kb.api_delete_attachment',
        'kb.api_autosave',
        'kb.api_preview',
        'kb.api_track_reading',
        'kb.api_search_suggestions',
        'kb.api_article_feedback',
        'kb.api_analytics_chart',
        'kb.api_get_stats',
        'kb.api_download_attachment',
        'kb.api_attachment_thumbnail',
        'kb.toggle_bookmark',
        'kb.api_test',
        # Client Checks - Public form endpoints (no authentication required)
        'client_checks.public_form',      # Form compilation endpoint
        'client_checks.public_success',   # Success page after submission
        # Sales Form - API endpoints (JSON)
        'sales_form.update_health_manager_inline',  # Change HM from panel (AJAX)
        'sales_form.update_onboarding_time',  # Update onboarding time from panel (AJAX)
    ]

    # ------------------ Google OAuth 2.0 API -----------------------
    GOOGLE_CLIENT_ID: str | None     = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str | None = os.getenv("GOOGLE_CLIENT_SECRET")

    # Scopes di default identici a `google_utils._SCOPES`
    _default_scopes = (
        "https://www.googleapis.com/auth/calendar "
        "https://www.googleapis.com/auth/calendar.events"
    )
    GOOGLE_SCOPES: tuple[str, ...] = tuple(
        os.getenv("GOOGLE_SCOPES", _default_scopes).split()
    )

    # Redirect URI registrato sul progetto Google Cloud
    GOOGLE_REDIRECT_URL: str | None = os.getenv("GOOGLE_REDIRECT_URL")

    # ------------------ Web Push / PWA Notifications -----------------------
    VAPID_PUBLIC_KEY: str | None = os.getenv("VAPID_PUBLIC_KEY")
    VAPID_PRIVATE_KEY: str | None = os.getenv("VAPID_PRIVATE_KEY")
    VAPID_CLAIMS_SUB: str = os.getenv("VAPID_CLAIMS_SUB", "mailto:it@corposostenibile.com")


    # ------------------ File Upload Configuration -----------------
    # Cartella base per tutti gli upload
    UPLOAD_FOLDER: str = os.getenv(
        "UPLOAD_FOLDER",
        str(BASE_DIR / "uploads")
    )
    
    # Dimensione massima file upload (in bytes)
    # 100MB default per documenti PDF, contratti, certificazioni, foto
    MAX_CONTENT_LENGTH: int = int(os.getenv("MAX_UPLOAD_SIZE", str(100 * 1024 * 1024)))  # 100MB default
    
    # Estensioni permesse per tipo di upload
    ALLOWED_EXTENSIONS: dict[str, set[str]] = {
        'documents': {'pdf'},                                    # Documenti dipartimento
        'images': {'jpg', 'jpeg', 'png', 'gif', 'webp'},       # Avatar e immagini
        'certifications': {'pdf', 'jpg', 'jpeg', 'png'},        # Certificazioni HR
        'contracts': {'pdf'},                                    # Solo PDF per contratti
        'nutrition': {'pdf', 'csv', 'xlsx'},                    # Export piani alimentari
    }
    
    # Path relativi dentro UPLOAD_FOLDER
    UPLOAD_PATHS: dict[str, str] = {
        'departments': 'departments',      # /uploads/departments/{dept_id}/
        'avatars': 'avatars',             # /uploads/avatars/
        'certifications': 'certifications', # /uploads/certifications/
        'contracts': 'contracts',          # /uploads/contracts/
        'attachments': 'attachments',      # /uploads/attachments/
        'nutrition': 'nutrition',          # /uploads/nutrition/
    }
    
    # Sicurezza upload
    UPLOAD_SECURE_FILENAMES: bool = True  # Usa sempre secure_filename()
    UPLOAD_REQUIRE_AUTH: bool = True      # Richiedi autenticazione per upload
    
    # Limiti specifici per tipo (in bytes)
    UPLOAD_SIZE_LIMITS: dict[str, int] = {
        'avatar': 5 * 1024 * 1024,         # 5MB per avatar
        'document': 10 * 1024 * 1024,      # 10MB per documenti PDF
        'certification': 10 * 1024 * 1024,  # 10MB per certificazioni
        'contract': 10 * 1024 * 1024,      # 10MB per contratti
        'attachment': 20 * 1024 * 1024,    # 20MB per allegati generici
        'nutrition_pdf': 5 * 1024 * 1024,  # 5MB per PDF piani alimentari
    }

    # ------------------ Nutrition Module Configuration -------------
    # Configurazioni specifiche per il modulo Nutrition
    
    # Database alimenti esterno (es. Open Food Facts API)
    FOOD_API_URL: str | None = os.getenv("FOOD_API_URL")
    FOOD_API_KEY: str | None = os.getenv("FOOD_API_KEY")
    
    # Cache per ricerche alimenti (in secondi)
    FOOD_SEARCH_CACHE_TTL: int = int(os.getenv("FOOD_SEARCH_CACHE_TTL", "3600"))  # 1 ora
    
    # Limiti per piani alimentari
    MAX_MEAL_PLAN_DAYS: int = int(os.getenv("MAX_MEAL_PLAN_DAYS", "90"))  # Max 90 giorni
    MAX_FOODS_PER_MEAL: int = int(os.getenv("MAX_FOODS_PER_MEAL", "20"))  # Max 20 alimenti per pasto
    
    # Path per export PDF piani alimentari (relativo a UPLOAD_FOLDER)
    NUTRITION_PDF_PATH: str = "nutrition/meal_plans"
    NUTRITION_SHOPPING_LIST_PATH: str = "nutrition/shopping_lists"
    
    # Valori nutrizionali di default per calcoli
    DEFAULT_ACTIVITY_MULTIPLIER: dict[str, float] = {
        'sedentario': 1.2,
        'leggermente_attivo': 1.375,
        'moderatamente_attivo': 1.55,
        'molto_attivo': 1.725,
        'estremamente_attivo': 1.9
    }
    
    # Macro distribuzione di default per obiettivi
    DEFAULT_MACRO_DISTRIBUTION: dict[str, dict[str, float]] = {
        'dimagrimento': {'proteins': 0.30, 'carbs': 0.35, 'fats': 0.35},
        'mantenimento': {'proteins': 0.25, 'carbs': 0.45, 'fats': 0.30},
        'aumento_massa': {'proteins': 0.25, 'carbs': 0.50, 'fats': 0.25},
        'ricomposizione': {'proteins': 0.35, 'carbs': 0.35, 'fats': 0.30},
        'salute_generale': {'proteins': 0.20, 'carbs': 0.50, 'fats': 0.30},
    }
    
    # Permessi nutrizionisti
    NUTRITIONIST_CAN_CREATE_FOODS: bool = True  # I nutrizionisti possono creare nuovi alimenti
    NUTRITIONIST_CAN_EDIT_ALL_RECIPES: bool = False  # Solo le proprie ricette

    # WebSocket configuration
    WEBSOCKET_MESSAGE_QUEUE: str = os.getenv("WEBSOCKET_QUEUE", "redis://localhost:6379/3")
    WEBSOCKET_PING_INTERVAL: int = int(os.getenv("WEBSOCKET_PING_INTERVAL", "25"))  # secondi
    WEBSOCKET_PING_TIMEOUT: int = int(os.getenv("WEBSOCKET_PING_TIMEOUT", "10"))  # secondi
    
    # Scheduler configuration per follow-up
    SCHEDULER_USE_REDIS: bool = bool(int(os.getenv("SCHEDULER_USE_REDIS", "1")))
    SCHEDULER_REDIS_DB: int = int(os.getenv("SCHEDULER_REDIS_DB", "4"))
    SCHEDULER_THREAD_POOL_SIZE: int = int(os.getenv("SCHEDULER_THREAD_POOL_SIZE", "10"))
    SCHEDULER_PROCESS_POOL_SIZE: int = int(os.getenv("SCHEDULER_PROCESS_POOL_SIZE", "2"))
    SCHEDULER_MISFIRE_GRACE_TIME: int = int(os.getenv("SCHEDULER_MISFIRE_GRACE_TIME", "300"))  # 5 minuti
    SCHEDULER_TIMEZONE: str = os.getenv("SCHEDULER_TIMEZONE", "UTC")
    
    # Base URL del backend (per webhook GHL, link email, ecc.)
    # Necessario per sviluppatori: GHL deve raggiungere il backend dall'esterno
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:5001")
    # Base URL pubblico dedicato ai link dei check cliente (puo' coincidere con BASE_URL)
    PUBLIC_CHECKS_BASE_URL: str = os.getenv("PUBLIC_CHECKS_BASE_URL", BASE_URL)

    # ------------------ GHL (GoHighLevel) Integration ----------------
    GHL_WEBHOOK_SECRET: str | None = os.getenv("GHL_WEBHOOK_SECRET")
    GHL_API_KEY: str | None = os.getenv("GHL_API_KEY")
    GHL_LOCATION_ID: str | None = os.getenv("GHL_LOCATION_ID")
    GHL_API_BASE_URL: str = os.getenv("GHL_API_BASE_URL", "https://rest.gohighlevel.com/v1")
    GHL_GLOBAL_STATUS_WEBHOOK_MODE: str = os.getenv("GHL_GLOBAL_STATUS_WEBHOOK_MODE", "mock")
    GHL_GLOBAL_STATUS_WEBHOOK_URL: str | None = os.getenv("GHL_GLOBAL_STATUS_WEBHOOK_URL")
    GHL_GLOBAL_STATUS_WEBHOOK_URL_GHOST: str | None = os.getenv("GHL_GLOBAL_STATUS_WEBHOOK_URL_GHOST")
    GHL_GLOBAL_STATUS_WEBHOOK_URL_PAUSA: str | None = os.getenv("GHL_GLOBAL_STATUS_WEBHOOK_URL_PAUSA")
    GHL_CALL_BONUS_WEBHOOK_MODE: str = os.getenv("GHL_CALL_BONUS_WEBHOOK_MODE", "mock")
    GHL_CALL_BONUS_WEBHOOK_URL: str | None = os.getenv("GHL_CALL_BONUS_WEBHOOK_URL")

    # ------------------ Respond.io Integration -----------------------
    RESPOND_IO_API_TOKEN: str | None = os.getenv("RESPOND_IO_API_TOKEN")
    RESPOND_IO_API_BASE_URL: str = os.getenv("RESPOND_IO_API_BASE_URL", "https://api.respond.io/v2")
    # Opzionale: canale specifico per invio messaggi API (se assente usa ultimo canale del contatto)
    RESPOND_IO_DEFAULT_CHANNEL_ID: int | None = (
        int(os.getenv("RESPOND_IO_DEFAULT_CHANNEL_ID"))
        if os.getenv("RESPOND_IO_DEFAULT_CHANNEL_ID")
        else None
    )
    
    # Webhook Signing Keys
    RESPOND_IO_WEBHOOK_KEY_NEW_CONTACT: str | None = os.getenv("RESPOND_IO_WEBHOOK_KEY_NEW_CONTACT")
    RESPOND_IO_WEBHOOK_KEY_LIFECYCLE: str | None = os.getenv("RESPOND_IO_WEBHOOK_KEY_LIFECYCLE")
    RESPOND_IO_WEBHOOK_KEY_INCOMING_MESSAGE: str | None = os.getenv("RESPOND_IO_WEBHOOK_KEY_INCOMING_MESSAGE")
    RESPOND_IO_WEBHOOK_KEY_OUTGOING_MESSAGE: str | None = os.getenv("RESPOND_IO_WEBHOOK_KEY_OUTGOING_MESSAGE")
    RESPOND_IO_WEBHOOK_KEY_TAG_UPDATED: str | None = os.getenv("RESPOND_IO_WEBHOOK_KEY_TAG_UPDATED", 
                                                                "Hc0M8HSW1yt5CMOJugVVyMDitWhVjkIPRYFPlZYYmXw=")
    
    # Rate Limiting per API calls
    RESPOND_IO_RATE_LIMIT_CONTACTS: int = int(os.getenv("RESPOND_IO_RATE_LIMIT_CONTACTS", "5"))
    RESPOND_IO_RATE_LIMIT_MESSAGES: int = int(os.getenv("RESPOND_IO_RATE_LIMIT_MESSAGES", "10"))

    # ================================================================
    # ClickUp Integration (IT Support Tickets - blueprint it_support)
    # ================================================================
    CLICKUP_INTEGRATION_ENABLED: bool = str(
        os.getenv("CLICKUP_INTEGRATION_ENABLED", "0")
    ).lower() in ("1", "true", "yes")

    CLICKUP_API_TOKEN: str = os.getenv("CLICKUP_API_TOKEN", "")
    CLICKUP_WEBHOOK_SECRET: str = os.getenv("CLICKUP_WEBHOOK_SECRET", "")

    CLICKUP_WORKSPACE_ID: str = os.getenv("CLICKUP_WORKSPACE_ID", "")
    CLICKUP_SPACE_ID: str = os.getenv("CLICKUP_SPACE_ID", "")
    CLICKUP_LIST_ID: str = os.getenv("CLICKUP_LIST_ID", "")
    CLICKUP_WEBHOOK_URL: str = os.getenv("CLICKUP_WEBHOOK_URL", "")

    CLICKUP_REQUEST_TIMEOUT: int = int(os.getenv("CLICKUP_REQUEST_TIMEOUT", "15"))
    CLICKUP_MAX_RETRIES: int = int(os.getenv("CLICKUP_MAX_RETRIES", "3"))

    # Custom Field UUIDs
    CLICKUP_FIELD_TIPO: str = os.getenv("CLICKUP_FIELD_TIPO", "")
    CLICKUP_FIELD_MODULO: str = os.getenv("CLICKUP_FIELD_MODULO", "")
    CLICKUP_FIELD_CRITICITA: str = os.getenv("CLICKUP_FIELD_CRITICITA", "")
    CLICKUP_FIELD_TICKET_ID: str = os.getenv("CLICKUP_FIELD_TICKET_ID", "")
    CLICKUP_FIELD_EMAIL_UTENTE: str = os.getenv("CLICKUP_FIELD_EMAIL_UTENTE", "")
    CLICKUP_FIELD_NOME_UTENTE: str = os.getenv("CLICKUP_FIELD_NOME_UTENTE", "")
    CLICKUP_FIELD_RUOLO: str = os.getenv("CLICKUP_FIELD_RUOLO", "")
    CLICKUP_FIELD_SPECIALITA: str = os.getenv("CLICKUP_FIELD_SPECIALITA", "")
    CLICKUP_FIELD_CLIENTE_COINVOLTO: str = os.getenv("CLICKUP_FIELD_CLIENTE_COINVOLTO", "")
    CLICKUP_FIELD_BROWSER: str = os.getenv("CLICKUP_FIELD_BROWSER", "")
    CLICKUP_FIELD_OS: str = os.getenv("CLICKUP_FIELD_OS", "")
    CLICKUP_FIELD_VERSIONE_APP: str = os.getenv("CLICKUP_FIELD_VERSIONE_APP", "")
    CLICKUP_FIELD_COMMIT_SHA: str = os.getenv("CLICKUP_FIELD_COMMIT_SHA", "")
    CLICKUP_FIELD_LINK_REGISTRAZIONE: str = os.getenv("CLICKUP_FIELD_LINK_REGISTRAZIONE", "")
    CLICKUP_FIELD_ALLEGATO: str = os.getenv("CLICKUP_FIELD_ALLEGATO", "")

    # Dropdown option UUIDs (Tipo)
    CLICKUP_OPT_TIPO_BUG: str = os.getenv("CLICKUP_OPT_TIPO_BUG", "")
    CLICKUP_OPT_TIPO_DATO_ERRATO: str = os.getenv("CLICKUP_OPT_TIPO_DATO_ERRATO", "")
    CLICKUP_OPT_TIPO_ACCESSO: str = os.getenv("CLICKUP_OPT_TIPO_ACCESSO", "")
    CLICKUP_OPT_TIPO_LENTEZZA: str = os.getenv("CLICKUP_OPT_TIPO_LENTEZZA", "")

    # Dropdown option UUIDs (Modulo)
    CLICKUP_OPT_MODULO_ASSEGNAZIONI: str = os.getenv("CLICKUP_OPT_MODULO_ASSEGNAZIONI", "")
    CLICKUP_OPT_MODULO_CALENDARIO: str = os.getenv("CLICKUP_OPT_MODULO_CALENDARIO", "")
    CLICKUP_OPT_MODULO_CHECK: str = os.getenv("CLICKUP_OPT_MODULO_CHECK", "")
    CLICKUP_OPT_MODULO_CLIENTI: str = os.getenv("CLICKUP_OPT_MODULO_CLIENTI", "")
    CLICKUP_OPT_MODULO_DASHBOARD: str = os.getenv("CLICKUP_OPT_MODULO_DASHBOARD", "")
    CLICKUP_OPT_MODULO_FORMAZIONE: str = os.getenv("CLICKUP_OPT_MODULO_FORMAZIONE", "")
    CLICKUP_OPT_MODULO_GENERICO: str = os.getenv("CLICKUP_OPT_MODULO_GENERICO", "")
    CLICKUP_OPT_MODULO_PROFILO: str = os.getenv("CLICKUP_OPT_MODULO_PROFILO", "")
    CLICKUP_OPT_MODULO_QUALITY: str = os.getenv("CLICKUP_OPT_MODULO_QUALITY", "")
    CLICKUP_OPT_MODULO_SUPPORTO: str = os.getenv("CLICKUP_OPT_MODULO_SUPPORTO", "")
    CLICKUP_OPT_MODULO_TASK: str = os.getenv("CLICKUP_OPT_MODULO_TASK", "")
    CLICKUP_OPT_MODULO_TEAM: str = os.getenv("CLICKUP_OPT_MODULO_TEAM", "")

    # Dropdown option UUIDs (Criticità)
    CLICKUP_OPT_CRITICITA_BLOCCANTE: str = os.getenv("CLICKUP_OPT_CRITICITA_BLOCCANTE", "")
    CLICKUP_OPT_CRITICITA_NON_BLOCCANTE: str = os.getenv("CLICKUP_OPT_CRITICITA_NON_BLOCCANTE", "")

    # Status IDs (Space-level)
    CLICKUP_STATUS_NUOVO: str = os.getenv("CLICKUP_STATUS_NUOVO", "")
    CLICKUP_STATUS_IN_TRIAGE: str = os.getenv("CLICKUP_STATUS_IN_TRIAGE", "")
    CLICKUP_STATUS_IN_LAVORAZIONE: str = os.getenv("CLICKUP_STATUS_IN_LAVORAZIONE", "")
    CLICKUP_STATUS_IN_ATTESA_UTENTE: str = os.getenv("CLICKUP_STATUS_IN_ATTESA_UTENTE", "")
    CLICKUP_STATUS_DA_TESTARE: str = os.getenv("CLICKUP_STATUS_DA_TESTARE", "")
    CLICKUP_STATUS_RISOLTO: str = os.getenv("CLICKUP_STATUS_RISOLTO", "")
    CLICKUP_STATUS_NON_VALIDO: str = os.getenv("CLICKUP_STATUS_NON_VALIDO", "")

    # ================================================================
    # ClickUp Integration (GHL Support Tickets - blueprint ghl_support)
    # ================================================================
    # Space dedicato: "Go High Level - Ticket" (ID 90127111740).
    # Usa lo stesso CLICKUP_API_TOKEN e CLICKUP_WORKSPACE_ID del IT Support.
    # ================================================================
    CLICKUP_GHL_INTEGRATION_ENABLED: bool = str(
        os.getenv("CLICKUP_GHL_INTEGRATION_ENABLED", "0")
    ).lower() in ("1", "true", "yes")

    CLICKUP_GHL_SPACE_ID: str = os.getenv("CLICKUP_GHL_SPACE_ID", "")
    CLICKUP_GHL_LIST_ID: str = os.getenv("CLICKUP_GHL_LIST_ID", "")
    CLICKUP_GHL_WEBHOOK_URL: str = os.getenv("CLICKUP_GHL_WEBHOOK_URL", "")
    CLICKUP_GHL_WEBHOOK_SECRET: str = os.getenv("CLICKUP_GHL_WEBHOOK_SECRET", "")

    # Custom Field UUIDs (6 field, solo metadati)
    CLICKUP_GHL_FIELD_TICKET_ID: str = os.getenv("CLICKUP_GHL_FIELD_TICKET_ID", "")
    CLICKUP_GHL_FIELD_EMAIL_UTENTE: str = os.getenv("CLICKUP_GHL_FIELD_EMAIL_UTENTE", "")
    CLICKUP_GHL_FIELD_NOME_UTENTE: str = os.getenv("CLICKUP_GHL_FIELD_NOME_UTENTE", "")
    CLICKUP_GHL_FIELD_USER_ID_GHL: str = os.getenv("CLICKUP_GHL_FIELD_USER_ID_GHL", "")
    CLICKUP_GHL_FIELD_BROWSER: str = os.getenv("CLICKUP_GHL_FIELD_BROWSER", "")
    CLICKUP_GHL_FIELD_OS: str = os.getenv("CLICKUP_GHL_FIELD_OS", "")

    # Status IDs (space-level)
    CLICKUP_GHL_STATUS_NUOVO: str = os.getenv("CLICKUP_GHL_STATUS_NUOVO", "")
    CLICKUP_GHL_STATUS_IN_ANALISI: str = os.getenv("CLICKUP_GHL_STATUS_IN_ANALISI", "")
    CLICKUP_GHL_STATUS_IN_LAVORAZIONE: str = os.getenv("CLICKUP_GHL_STATUS_IN_LAVORAZIONE", "")
    CLICKUP_GHL_STATUS_IN_ATTESA_HIGHLEVEL: str = os.getenv("CLICKUP_GHL_STATUS_IN_ATTESA_HIGHLEVEL", "")
    CLICKUP_GHL_STATUS_IN_ATTESA_UTENTE: str = os.getenv("CLICKUP_GHL_STATUS_IN_ATTESA_UTENTE", "")
    CLICKUP_GHL_STATUS_RISOLTO: str = os.getenv("CLICKUP_GHL_STATUS_RISOLTO", "")
    CLICKUP_GHL_STATUS_NON_VALIDO: str = os.getenv("CLICKUP_GHL_STATUS_NON_VALIDO", "")

    # ================================================================
    # GHL Support SSO (Opzione A — Custom Menu Link)
    # ================================================================
    # Chiave HS256 per firmare i JWT di sessione GHL. Se non impostata usa
    # SECRET_KEY come fallback.
    GHL_SSO_SIGNING_KEY: str = os.getenv("GHL_SSO_SIGNING_KEY", "")

# ---------------------------------------------------------------- Env-specifiche
class DevelopmentConfig(BaseConfig):
    DEBUG: bool = True
    CELERY_TASK_ALWAYS_EAGER: bool = True           # run tasks inline in dev
    
    # In dev, usa dati mock per test
    USE_MOCK_FOOD_DATA: bool = True
    
    
    # In dev, crea automaticamente le cartelle upload se non esistono
    @classmethod
    def init_app(cls, app):
        """Inizializza configurazioni specifiche per development."""
        # Prima chiama il metodo della classe base per il debug
        super().init_app(app)
        
        upload_folder = Path(app.config['UPLOAD_FOLDER'])
        
        # Crea struttura cartelle upload
        for subpath in app.config['UPLOAD_PATHS'].values():
            folder = upload_folder / subpath
            folder.mkdir(parents=True, exist_ok=True)
            
        # Crea sottocartelle specifiche per nutrition
        nutrition_folder = upload_folder / 'nutrition'
        for subdir in ['meal_plans', 'shopping_lists', 'exports']:
            (nutrition_folder / subdir).mkdir(parents=True, exist_ok=True)
            
        # Crea anche .gitkeep in ogni cartella (per git)
        for subpath in app.config['UPLOAD_PATHS'].values():
            gitkeep = upload_folder / subpath / '.gitkeep'
            gitkeep.touch(exist_ok=True)
            
        # Log per debug
        app.logger.info(f"Upload folder configurato: {upload_folder}")
        app.logger.info(f"MAX_CONTENT_LENGTH: {app.config['MAX_CONTENT_LENGTH']} bytes")


class TestingConfig(BaseConfig):
    TESTING: bool = True
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///:memory:"
    CELERY_TASK_ALWAYS_EAGER: bool = True
    WTF_CSRF_ENABLED: bool = False                  # semplifica i test
    
    # Per i test, usa una cartella temporanea
    UPLOAD_FOLDER: str = os.getenv("TEST_UPLOAD_FOLDER", "/tmp/corposostenibile_test_uploads")
    
    # Limiti più bassi per velocizzare i test
    MAX_CONTENT_LENGTH: int = 1 * 1024 * 1024  # 1MB nei test
    
    # Nutrition test config
    MAX_MEAL_PLAN_DAYS: int = 7  # Solo 7 giorni nei test
    USE_MOCK_FOOD_DATA: bool = True  # Sempre mock nei test
    


class ProductionConfig(BaseConfig):
    """Override production-specific (se serve)."""
    
    # In produzione, assicurati che UPLOAD_FOLDER punti a storage persistente
    # es. volume montato, S3, ecc.
    UPLOAD_FOLDER: str = os.getenv(
        "UPLOAD_FOLDER",
        "/var/corposostenibile/uploads"  # Path production standard
    )
    
    # Aumenta i limiti in produzione se necessario
    MAX_CONTENT_LENGTH: int = int(os.getenv("MAX_UPLOAD_SIZE", str(100 * 1024 * 1024)))  # 100MB
    
    # Sicurezza extra in produzione
    UPLOAD_SECURE_FILENAMES: bool = True
    UPLOAD_REQUIRE_AUTH: bool = True
    
    # Se usi un CDN o storage esterno
    CDN_URL: str | None = os.getenv("CDN_URL")  # es. https://cdn.corposostenibile.com
    USE_S3: bool = bool(int(os.getenv("USE_S3", "0")))
    
    # AWS S3 config (se USE_S3 = True)
    AWS_ACCESS_KEY_ID: str | None = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str | None = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_S3_BUCKET: str | None = os.getenv("AWS_S3_BUCKET")
    AWS_S3_REGION: str = os.getenv("AWS_S3_REGION", "eu-west-1")
    
    # Nutrition production config
    USE_MOCK_FOOD_DATA: bool = False  # Mai mock in produzione
    NUTRITIONIST_CAN_CREATE_FOODS: bool = False  # Solo admin in produzione
    
    # Cache Redis per nutrition (se disponibile)
    NUTRITION_CACHE_BACKEND: str = os.getenv("NUTRITION_CACHE_BACKEND", "redis://localhost:6379/2")
    
    # Rate limiting più stringente in produzione
    PERISKOPE_RATE_LIMIT: int = int(os.getenv("PERISKOPE_RATE_LIMIT", "50"))  # Più conservativo

    # ── Trustpilot Integration ──
    TRUSTPILOT_ENABLED: bool = str(os.getenv("TRUSTPILOT_ENABLED", "0")).lower() in ("1", "true", "yes")
    TRUSTPILOT_API_KEY: str = os.getenv("TRUSTPILOT_API_KEY", "")
    TRUSTPILOT_API_SECRET: str = os.getenv("TRUSTPILOT_API_SECRET", "")
    TRUSTPILOT_BUSINESS_UNIT_ID: str = os.getenv("TRUSTPILOT_BUSINESS_UNIT_ID", "")
    TRUSTPILOT_BUSINESS_USER_ID: str = os.getenv("TRUSTPILOT_BUSINESS_USER_ID", "")
    TRUSTPILOT_REDIRECT_URI: str = os.getenv("TRUSTPILOT_REDIRECT_URI", "")
    TRUSTPILOT_WEBHOOK_USERNAME: str = os.getenv("TRUSTPILOT_WEBHOOK_USERNAME", "")
    TRUSTPILOT_WEBHOOK_PASSWORD: str = os.getenv("TRUSTPILOT_WEBHOOK_PASSWORD", "")
    TRUSTPILOT_EMAIL_TEMPLATE_ID: str = os.getenv("TRUSTPILOT_EMAIL_TEMPLATE_ID", "")
    TRUSTPILOT_SENDER_NAME: str = os.getenv("TRUSTPILOT_SENDER_NAME", "")
    TRUSTPILOT_SENDER_EMAIL: str = os.getenv("TRUSTPILOT_SENDER_EMAIL", "")
    TRUSTPILOT_REPLY_TO: str = os.getenv("TRUSTPILOT_REPLY_TO", "")
    TRUSTPILOT_LOCALE_DEFAULT: str = os.getenv("TRUSTPILOT_LOCALE_DEFAULT", "it-IT")
    TRUSTPILOT_TIMEOUT_SECONDS: int = int(os.getenv("TRUSTPILOT_TIMEOUT_SECONDS", "20"))


# ---------------------------------------------------------------- Dispatcher
class Config:
    """
    Restituisce la sottoclasse di *BaseConfig* adatta all'ambiente
    (``development`` / ``testing`` / ``production``).
    """
    _mapping: dict[str, Type[BaseConfig]] = {
        "development": DevelopmentConfig,
        "testing": TestingConfig,
        "production": ProductionConfig,
    }

    @classmethod
    def get(cls, env_name: str | None) -> Type[BaseConfig]:
        env_name = (env_name or "").lower()
        return cls._mapping.get(env_name, DevelopmentConfig)
