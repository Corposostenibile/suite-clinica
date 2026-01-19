"""
Utilità per gestire il timezone di Roma nel sistema ticket.
"""

from datetime import datetime
import pytz

# Timezone di Roma
ROME_TZ = pytz.timezone('Europe/Rome')

def get_rome_time():
    """Restituisce l'ora corrente nel timezone di Roma."""
    return datetime.now(ROME_TZ)

def utc_to_rome(utc_dt):
    """Converte un datetime UTC in timezone di Roma."""
    if utc_dt is None:
        return None
    if utc_dt.tzinfo is None:
        # Se non ha timezone, assumiamo sia UTC
        utc_dt = pytz.utc.localize(utc_dt)
    return utc_dt.astimezone(ROME_TZ)

def rome_to_utc(rome_dt):
    """Converte un datetime di Roma in UTC."""
    if rome_dt is None:
        return None
    if rome_dt.tzinfo is None:
        # Se non ha timezone, assumiamo sia Roma
        rome_dt = ROME_TZ.localize(rome_dt)
    return rome_dt.astimezone(pytz.utc)

def format_rome_datetime(dt, format_string='%d/%m/%Y alle %H:%M'):
    """Formatta un datetime nel timezone di Roma."""
    if dt is None:
        return ''
    rome_dt = utc_to_rome(dt)
    return rome_dt.strftime(format_string)

def get_utc_now():
    """Restituisce l'ora corrente in UTC per confronti con database."""
    # Ottieni l'ora di Roma e convertila in UTC per i confronti
    rome_now = get_rome_time()
    return rome_now.astimezone(pytz.utc).replace(tzinfo=None)