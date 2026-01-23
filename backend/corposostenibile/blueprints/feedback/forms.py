"""
Feedback forms for date range calculations and filtering.
"""

from datetime import datetime, timedelta, date
from typing import Tuple
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import Optional

def get_date_range_for_period(period: str, offset: int = 0, start_date_str: str = None, end_date_str: str = None) -> Tuple[datetime, datetime]:
    """Get start and end dates for a given period and offset.

    Args:
        period: Type of period ('week', 'month', 'trimester', 'year', 'custom')
        offset: Offset for predefined periods (ignored for custom)
        start_date_str: Start date string for custom period (format: YYYY-MM-DD)
        end_date_str: End date string for custom period (format: YYYY-MM-DD)

    Returns:
        Tuple of (start_datetime, end_datetime)
    """
    now = datetime.now()

    if period == "custom":
        # Custom period with user-specified dates
        if start_date_str and end_date_str:
            try:
                start = datetime.strptime(start_date_str, '%Y-%m-%d')
                start = start.replace(hour=0, minute=0, second=0, microsecond=0)
                end = datetime.strptime(end_date_str, '%Y-%m-%d')
                end = end.replace(hour=23, minute=59, second=59, microsecond=999999)
            except ValueError:
                # Se le date non sono valide, fallback al mese corrente
                start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                end = (start.replace(month=start.month + 1) if start.month < 12 else start.replace(year=start.year + 1, month=1)) - timedelta(seconds=1)
        else:
            # Se non ci sono date custom, fallback al mese corrente
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = (start.replace(month=start.month + 1) if start.month < 12 else start.replace(year=start.year + 1, month=1)) - timedelta(seconds=1)

    elif period == "week":
        # Start of current week (Monday)
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        # Add offset weeks
        start = start + timedelta(weeks=offset)
        end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)

    elif period == "month":
        # Start of current month
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Add offset months (with proper year rollover)
        total_months = start.month + offset
        year_offset = (total_months - 1) // 12
        new_month = ((total_months - 1) % 12) + 1
        start = start.replace(year=start.year + year_offset, month=new_month)
        # End of month
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1) - timedelta(seconds=1)
        else:
            end = start.replace(month=start.month + 1) - timedelta(seconds=1)

    elif period == "trimester":
        # Start of current quarter
        quarter_start_month = ((now.month - 1) // 3) * 3 + 1
        start = now.replace(month=quarter_start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        # Add offset quarters (with proper year rollover)
        total_months = start.month + (offset * 3)
        year_offset = (total_months - 1) // 12
        new_month = ((total_months - 1) % 12) + 1
        start = start.replace(year=start.year + year_offset, month=new_month)
        # End of quarter (3 months later)
        end_month = start.month + 2
        if end_month > 12:
            end = start.replace(year=start.year + 1, month=end_month - 12, day=1) - timedelta(seconds=1)
        else:
            end = start.replace(month=end_month, day=1)
            # Go to next month and subtract 1 second
            if end.month == 12:
                end = end.replace(year=end.year + 1, month=1) - timedelta(seconds=1)
            else:
                end = end.replace(month=end.month + 1) - timedelta(seconds=1)

    elif period == "year":
        # Start of current year
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        # Add offset years
        start = start.replace(year=start.year + offset)
        # End of year
        end = start.replace(year=start.year + 1) - timedelta(seconds=1)

    else:
        # Default to current month
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = (start.replace(month=start.month + 1) if start.month < 12 else start.replace(year=start.year + 1, month=1)) - timedelta(seconds=1)

    return start, end

def format_period_display(start_date: date, end_date: date, period: str) -> str:
    """
    Formatta la visualizzazione del periodo per l'interfaccia utente.

    Args:
        start_date: Data di inizio
        end_date: Data di fine
        period: Tipo di periodo ('week', 'month', 'trimester', 'year', 'custom')

    Returns:
        Stringa formattata per la visualizzazione (solo intervallo date)
    """
    if period == "custom":
        return f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}"
    elif period == "week":
        return f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}"
    elif period == "month":
        return f"{start_date.strftime('%B %Y')}"
    elif period == "trimester":
        quarter_num = (start_date.month - 1) // 3 + 1
        return f"Trimestre {quarter_num} {start_date.year}"
    elif period == "year":
        return f"{start_date.year}"
    else:
        return f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}" 

class ResponseFilterForm(FlaskForm):
    """Filtri ricerca lista risposte."""
    
    # Ricerca per nome
    q = StringField("Nome", validators=[Optional()])
    
    # Filtro per stato (associato/non associato)
    status = SelectField(
        "Stato",
        choices=[
            ("", "— Tutti —"),
            ("matched", "Associati"),
            ("unmatched", "Non associati")
        ],
        validators=[Optional()]
    )
    
    submit = SubmitField("Filtra") 