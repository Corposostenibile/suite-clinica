"""
Configurazione Celery Beat per task schedulati del blueprint respond_io
"""

from celery.schedules import crontab

# Aggiungi questi task alla configurazione CELERYBEAT_SCHEDULE nel tuo config.py principale

RESPOND_IO_BEAT_SCHEDULE = {
    # Schedula il task di analisi turni ogni giorno alle 00:30
    # per preparare le pre-assegnazioni del giorno
    'schedule-daily-pre-assignments': {
        'task': 'corposostenibile.blueprints.respond_io.pre_assignment_tasks.schedule_daily_pre_assignments',
        'schedule': crontab(hour=0, minute=30),
        'options': {
            'queue': 'respond_io',
            'priority': 9  # Alta priorità
        }
    },
    
    # Backup: Controlla ogni ora se ci sono turni non gestiti
    # (utile se il sistema è stato offline)
    'check-upcoming-shifts': {
        'task': 'corposostenibile.blueprints.respond_io.pre_assignment_tasks.pre_assign_first_shift_contacts',
        'schedule': crontab(minute=0),  # Ogni ora
        'options': {
            'queue': 'respond_io',
            'priority': 7
        }
    },
    
    # Pulizia log pre-assegnazioni vecchi (ogni domenica alle 3:00)
    'cleanup-pre-assignment-logs': {
        'task': 'corposostenibile.blueprints.respond_io.pre_assignment_tasks.cleanup_old_logs',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),
        'options': {
            'queue': 'respond_io',
            'priority': 3
        }
    }
}

# Esempio di come integrare nella config principale:
"""
# Nel tuo config.py principale, aggiungi:

from corposostenibile.blueprints.respond_io.celery_config import RESPOND_IO_BEAT_SCHEDULE

CELERYBEAT_SCHEDULE = {
    # ... altri task schedulati ...
}

# Aggiungi i task di respond_io
CELERYBEAT_SCHEDULE.update(RESPOND_IO_BEAT_SCHEDULE)
"""