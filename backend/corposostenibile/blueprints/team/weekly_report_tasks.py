"""
Task schedulati per i Report Settimanali
========================================

Gestisce l'invio automatico delle email di reminder.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List

from flask import current_app, url_for, render_template_string
from sqlalchemy import and_

from corposostenibile.extensions import db, celery, get_scheduler
from corposostenibile.models import User
from .models.weekly_report import WeeklyReport


def send_weekly_report_reminder(user: User) -> bool:
    """
    Invia email di reminder per il report a un singolo utente.
    Adatta il contenuto in base al tipo di dipartimento (Sales vs normale).
    
    Args:
        user: Utente a cui inviare il reminder
        
    Returns:
        True se l'email è stata inviata con successo
    """
    try:
        # Determina se è un utente Sales
        is_sales = user.department and WeeklyReport.is_sales_department(user.department.name)
        
        # URL per il report
        with current_app.test_request_context():
            report_url = url_for('weekly_report.new_report', _external=True)
        
        # Versione testo semplice differenziata
        if is_sales:
            subject = "📊 È tempo di compilare il tuo Report Mensile!"
            text_body = (
                f"Ciao {user.first_name or user.email},\n\n"
                "È l'ultimo sabato del mese! È il momento di compilare il tuo report mensile.\n"
                "Il tuo feedback è fondamentale per il nostro percorso di crescita e miglioramento continuo.\n\n"
                f"Compila il report: {report_url}\n\n"
                "Cosa includerai nel report:\n"
                "• Gli ostacoli principali che hai affrontato questo mese\n"
                "• Le tue idee per superare questi ostacoli\n"
                "• I punti del tuo lavoro che vorresti migliorare\n"
                "• Le tue idee per migliorare l'azienda\n\n"
                "Il form richiede solo 5-10 minuti del tuo tempo.\n\n"
                "Facciamo ogni giorno la differenza insieme.\n"
                "Grazie di far parte del team Corposostenibile"
            )
        else:
            subject = "📝 È tempo di compilare il tuo Report Settimanale!"
            text_body = (
                f"Ciao {user.first_name or user.email},\n\n"
                "È sabato! Ricordati di dedicare qualche minuto per compilare il tuo report settimanale.\n"
                "Il tuo feedback è fondamentale per il nostro percorso di crescita e miglioramento continuo.\n\n"
                f"Compila il report: {report_url}\n\n"
                "Cosa includerai nel report:\n"
                "• Le riflessioni sugli OKR del dipartimento e personali\n"
                "• Le tue idee per migliorare l'azienda\n\n"
                "Ricorda: Hai tempo fino a domenica sera per compilare il report.\n"
                "Il form richiede solo 5-10 minuti del tuo tempo.\n\n"
                "Facciamo ogni giorno la differenza insieme.\n"
                "Grazie di far parte del team Corposostenibile"
            )
        
        # Invia email SOLO TESTUALE
        from corposostenibile.blueprints.auth.email_utils import send_mail
        send_mail(
            subject,
            [user.email],
            text_body
        )
        
        current_app.logger.info(f"Weekly report reminder sent to {user.email}")
        return True
        
    except Exception as e:
        current_app.logger.error(f"Failed to send weekly report reminder to {user.email}: {e}")
        return False


@celery.task(name='team.send_weekly_report_reminders')
def send_weekly_report_reminders_task() -> dict:
    """
    Task Celery per inviare reminder a tutti gli utenti attivi.
    - Utenti normali: ogni sabato
    - Utenti Sales: solo ultimo sabato del mese
    
    Returns:
        Dict con statistiche di invio
    """
    with current_app.app_context():
        from datetime import date
        today = date.today()
        
        # Trova tutti gli utenti attivi che devono compilare il report
        users_to_notify = []
        
        for user in User.query.filter_by(is_active=True).all():
            # Verifica se l'utente può compilare il report oggi
            if not WeeklyReport.can_submit_report(user.id):
                continue
            
            # Verifica se ha già compilato il report per questo periodo
            if WeeklyReport.user_has_report_this_period(user.id):
                continue
            
            users_to_notify.append(user)
        
        # Invia reminder
        sent_count = 0
        failed_count = 0
        
        for user in users_to_notify:
            if send_weekly_report_reminder(user):
                sent_count += 1
            else:
                failed_count += 1
        
        current_app.logger.info(
            f"Weekly report reminders: {sent_count} sent, {failed_count} failed"
        )
        
        return {
            'sent': sent_count,
            'failed': failed_count,
            'total': len(users_to_notify)
        }


def schedule_weekly_report_reminders():
    """
    Configura lo scheduling automatico dei reminder.
    Da chiamare all'avvio dell'applicazione.
    """
    scheduler = get_scheduler()
    if not scheduler:
        current_app.logger.warning("APScheduler not available, weekly report reminders will not be scheduled")
        return
    
    from corposostenibile.extensions import schedule_task
    
    # Schedula ogni sabato alle 10:00
    job_id = schedule_task(
        send_weekly_report_reminders_task,
        trigger='cron',
        day_of_week='sat',
        hour=10,
        minute=0,
        id='weekly_report_reminder',
        name='Weekly Report Email Reminder',
        replace_existing=True
    )
    
    if job_id:
        current_app.logger.info(f"Weekly report reminder scheduled with job ID: {job_id}")
    else:
        current_app.logger.error("Failed to schedule weekly report reminder")


# Funzione alternativa per testing manuale
def send_test_reminder(user_email: str) -> bool:
    """
    Invia un reminder di test a un utente specifico.
    Utile per testing in development.
    
    Args:
        user_email: Email dell'utente
        
    Returns:
        True se inviato con successo
    """
    user = User.query.filter_by(email=user_email).first()
    if not user:
        return False
    
    return send_weekly_report_reminder(user)