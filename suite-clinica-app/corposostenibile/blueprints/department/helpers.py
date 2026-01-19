"""
blueprints/department/helpers.py
================================

Funzioni helper e filtri template per il modulo Department.
"""

from __future__ import annotations

from datetime import date
from typing import Optional


def format_italian_date(date_obj: Optional[date]) -> Optional[str]:
    """
    Formatta una data in formato italiano.
    
    Args:
        date_obj: La data da formattare
        
    Returns:
        Stringa formattata in italiano (es. "15 marzo 2024") o None
    """
    if not date_obj:
        return None
    
    mesi = [
        'gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno',
        'luglio', 'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre'
    ]
    
    return f"{date_obj.day} {mesi[date_obj.month - 1]} {date_obj.year}"


def days_until_due(due_date: Optional[date]) -> Optional[str]:
    """
    Calcola i giorni mancanti alla scadenza in formato testuale.
    
    Args:
        due_date: La data di scadenza
        
    Returns:
        Stringa descrittiva (es. "Mancano 5 giorni", "Scade oggi") o None
    """
    if not due_date:
        return None
    
    today = date.today()
    delta = due_date - today
    days = delta.days
    
    if days < -1:
        return f"Scaduto da {abs(days)} giorni"
    elif days == -1:
        return "Scaduto ieri"
    elif days == 0:
        return "Scade oggi"
    elif days == 1:
        return "Scade domani"
    else:
        return f"Mancano {days} giorni"


def get_due_date_css_class(due_date: Optional[date]) -> str:
    """
    Restituisce la classe CSS appropriata in base alla scadenza.
    
    Args:
        due_date: La data di scadenza
        
    Returns:
        Nome della classe CSS Bootstrap
    """
    if not due_date:
        return "text-muted"
    
    today = date.today()
    delta = due_date - today
    days = delta.days
    
    if days < 0:
        return "text-danger"  # Scaduto
    elif days == 0:
        return "text-warning"  # Scade oggi
    elif days <= 3:
        return "text-warning"  # Scade presto
    else:
        return "text-success"  # Tempo sufficiente


def register_template_filters(app):
    """
    Registra i filtri personalizzati per i template Jinja2.
    
    Args:
        app: L'istanza Flask dell'applicazione
    """
    
    @app.template_filter('italian_date')
    def italian_date_filter(date_obj):
        """Filtro template per formattare date in italiano."""
        return format_italian_date(date_obj)
    
    @app.template_filter('days_until')
    def days_until_filter(due_date):
        """Filtro template per calcolare giorni alla scadenza."""
        return days_until_due(due_date)
    
    @app.template_filter('due_date_class')
    def due_date_class_filter(due_date):
        """Filtro template per classe CSS scadenza."""
        return get_due_date_css_class(due_date)