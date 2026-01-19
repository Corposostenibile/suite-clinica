"""
Configurazione Celery Beat per task schedulati
"""

from celery.schedules import crontab

# Configurazione dei task periodici
CELERYBEAT_SCHEDULE = {
    # Pulizia contact channels ogni notte alle 3:00 AM
    'cleanup-respond-io-channels': {
        'task': 'corposostenibile.blueprints.respond_io.tasks.cleanup_old_contact_channels',
        'schedule': crontab(hour=3, minute=0),  # Ogni giorno alle 3:00 AM
        'options': {
            'expires': 3600,  # Scade dopo 1 ora se non eseguito
        }
    },
    
    # Ricalcolo metriche giornaliere ogni ora
    'recalculate-respond-io-metrics': {
        'task': 'corposostenibile.blueprints.respond_io.tasks.recalculate_daily_metrics',
        'schedule': crontab(minute=0),  # Ogni ora al minuto 0
        'options': {
            'expires': 1800,  # Scade dopo 30 minuti se non eseguito
        }
    },
    
    # Controllo follow-up pending ogni ora
    'check-pending-followups': {
        'task': 'corposostenibile.blueprints.respond_io.followup_tasks.check_pending_followups',
        'schedule': crontab(minute=30),  # Ogni ora al minuto 30
        'options': {
            'expires': 1800,
        }
    },
    
    # Pulizia follow-up vecchi ogni notte alle 4:00 AM
    'cleanup-old-followups': {
        'task': 'corposostenibile.blueprints.respond_io.followup_tasks.cleanup_old_followups',
        'schedule': crontab(hour=4, minute=0),
        'options': {
            'expires': 3600,
        }
    },
    
    # Report giornaliero follow-up alle 8:00 AM
    'generate-followup-report': {
        'task': 'corposostenibile.blueprints.respond_io.followup_tasks.generate_followup_report',
        'schedule': crontab(hour=8, minute=0),
        'options': {
            'expires': 3600,
        }
    },
    
    # Pulizia message history ogni notte alle 2:00 AM
    'cleanup-message-history': {
        'task': 'corposostenibile.blueprints.respond_io.tasks.cleanup_message_history',
        'schedule': crontab(hour=2, minute=0),
        'options': {
            'expires': 3600,
        }
    },
    
    # NUOVO: Schedula pre-assegnazioni per il primo turno
    'schedule-daily-pre-assignments': {
        'task': 'corposostenibile.blueprints.respond_io.pre_assignment_tasks.schedule_daily_pre_assignments',
        'schedule': crontab(hour=0, minute=30),  # Ogni giorno alle 00:30
        'options': {
            'expires': 3600,
            'priority': 9,  # Alta priorità
        }
    },
    
    # NUOVO: Backup check per pre-assegnazioni (ogni ora)
    'check-upcoming-first-shifts': {
        'task': 'corposostenibile.blueprints.respond_io.pre_assignment_tasks.pre_assign_first_shift_contacts',
        'schedule': crontab(minute=15),  # Ogni ora al minuto 15
        'options': {
            'expires': 1800,
            'priority': 7,
        }
    },
    
    # WEBHOOK HEALTH MANAGEMENT
    'process-webhook-queue': {
        'task': 'corposostenibile.blueprints.respond_io.webhook_tasks.process_webhook_queue',
        'schedule': crontab(minute='*'),  # Ogni minuto
        'options': {
            'expires': 55,  # Scade dopo 55 secondi
            'priority': 10,  # Massima priorità
        }
    },
    
    'webhook-health-check': {
        'task': 'corposostenibile.blueprints.respond_io.webhook_tasks.webhook_health_check',
        'schedule': crontab(minute='*/5'),  # Ogni 5 minuti
        'options': {
            'expires': 240,
            'priority': 8,
        }
    },
    
    'webhook-auto-recovery': {
        'task': 'corposostenibile.blueprints.respond_io.webhook_tasks.webhook_auto_recovery',
        'schedule': crontab(minute='*/15'),  # Ogni 15 minuti
        'options': {
            'expires': 600,
            'priority': 7,
        }
    },
    
    'webhook-daily-statistics': {
        'task': 'corposostenibile.blueprints.respond_io.webhook_tasks.webhook_statistics_report',
        'schedule': crontab(hour=6, minute=0),  # Ogni giorno alle 06:00
        'options': {
            'expires': 3600,
            'priority': 5,
        }
    },

}

# Timezone per Celery Beat (importante per crontab)
CELERY_TIMEZONE = 'Europe/Rome'

# Abilita UTC
CELERY_ENABLE_UTC = True