"""
corposostenibile.filters
========================

Filtri personalizzati per i template Jinja2.
"""

from __future__ import annotations

import math
from datetime import datetime, date, timezone
from typing import Any

from dateutil import parser
from flask_babel import format_datetime
from markupsafe import Markup, escape
import pytz

__all__ = [
    "datetime_filter",
    "date_filter",
    "nl2br",
    "file_size",
    "timeago",  # Aggiungi questo
    "rome_datetime",  # Filtro per fuso orario Roma
    "linkify",  # Filtro per link cliccabili
    "image_url",  # Filtro per URL immagini smart
    "register_filters",
]


# --------------------------------------------------------------------------- #
# Helper per parsing date/ora
# --------------------------------------------------------------------------- #

def _to_datetime(value: Any) -> datetime | None:
    """Converte *value* in :class:`datetime.datetime` (naive, UTC) oppure
    restituisce **None**.

    - ``datetime`` → invariato
    - ``date``     → mezzanotte dello stesso giorno
    - Unix epoch   → ``datetime.utcfromtimestamp``
    - ISO string   → parsing via :pyfunc:`dateutil.parser.isoparse`
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())

    if isinstance(value, (int, float)):
        try:
            return datetime.utcfromtimestamp(value)
        except (OverflowError, OSError, ValueError):
            return None

    if isinstance(value, str):
        try:
            return parser.isoparse(value)
        except (ValueError, TypeError):
            return None

    return None


# --------------------------------------------------------------------------- #
# Jinja filters
# --------------------------------------------------------------------------- #

def datetime_filter(value: Any, fmt: str = "medium") -> str:
    """Filtro Jinja ``{{ value|datetime }}``.

    Parameters
    ----------
    value
        ``datetime``, ``date``, Unix epoch (``int``/``float``) o stringa ISO‑8601.
    fmt
        Qualsiasi formato accettato da :pyfunc:`flask_babel.format_datetime`
        ("short", "medium", "long", "full" **oppure** stringa ``strftime``).

    Returns
    -------
    str
        Data/ora formattata secondo la locale corrente oppure *value* convertito
        in stringa se non parsabile.
    """
    dt = _to_datetime(value)
    if dt is None:
        return str(value or "")

    try:
        # Se il formato contiene "%" assumiamo che sia uno strftime custom
        if "%" in fmt:
            return dt.strftime(fmt)
        # Altrimenti deleghiamo a Babel (onora la locale corrente)
        return format_datetime(dt, format=fmt)
    except Exception:
        # Fallback prudenziale
        return dt.isoformat(sep=" ")


def date_filter(value: Any, fmt: str = "%d/%m/%Y") -> str:
    """Filtro Jinja ``{{ value|date }}`` (solo parte data).

    Accetta gli stessi tipi di :pyfunc:`datetime_filter`.
    Se *fmt* contiene «%» viene passato a ``strftime``; altrimenti usiamo
    ``flask_babel.format_date`` con quel formato.
    """
    from flask_babel import format_date  # import lazy per evitare dipendenze hard

    dt = _to_datetime(value)
    if dt is None:
        return str(value or "")

    try:
        if "%" in fmt:
            return dt.strftime(fmt)
        return format_date(dt, format=fmt)
    except Exception:
        return dt.date().isoformat()


def timeago(value: Any) -> str:
    """Converte un datetime in formato 'tempo fa' (es. '2 ore fa', '3 giorni fa').
    
    Parameters
    ----------
    value
        ``datetime``, ``date``, Unix epoch o stringa ISO-8601.
        
    Returns
    -------
    str
        Tempo relativo in italiano (ora, X minuti fa, X ore fa, etc.)
    """
    dt = _to_datetime(value)
    if dt is None:
        return ""
    
    # Se dt è naive, assumiamo sia UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    now = datetime.now(timezone.utc)
    diff = now - dt
    seconds = diff.total_seconds()
    
    # Gestisce date future
    if seconds < 0:
        return "nel futuro"
    
    if seconds < 60:
        return "ora"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minut{'o' if minutes == 1 else 'i'} fa"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} or{'a' if hours == 1 else 'e'} fa"
    elif seconds < 604800:  # 7 giorni
        days = int(seconds / 86400)
        return f"{days} giorn{'o' if days == 1 else 'i'} fa"
    elif seconds < 2592000:  # 30 giorni
        weeks = int(seconds / 604800)
        return f"{weeks} settiman{'a' if weeks == 1 else 'e'} fa"
    elif seconds < 31536000:  # 365 giorni
        months = int(seconds / 2592000)
        return f"{months} mes{'e' if months == 1 else 'i'} fa"
    else:
        years = int(seconds / 31536000)
        return f"{years} ann{'o' if years == 1 else 'i'} fa"


def nl2br(value: str | None) -> Markup:
    """Converte le *newline* in ``<br>`` preservando la sicurezza HTML."""
    if not value:
        return Markup("")

    # Prima eseguiamo l'escape, poi sostituiamo i ``\n`` con ``<br>``
    return Markup(escape(value).replace("\n", Markup("<br>")))


def file_size(num_bytes: int | float | None) -> str:
    """Rende *num_bytes* human‑friendly («1.4 MB», «932 B»…).

    Se il valore non è valido ritorna stringa vuota.
    """
    if not isinstance(num_bytes, (int, float)) or num_bytes < 0:
        return ""

    if num_bytes < 1024:
        return f"{num_bytes:.0f} B"

    # Decidiamo l'unità
    units = ("KB", "MB", "GB", "TB", "PB", "EB")
    size = float(num_bytes)
    for unit in units:
        size /= 1024
        if size < 1024:
            return f"{size:.1f} {unit}"

    # Estremo: zettabyte e oltre
    return f"{size:.1f} ZB"


def rome_datetime(value, format_string='%d/%m/%Y alle %H:%M'):
    """Converte un datetime UTC in fuso orario di Roma e lo formatta.
    
    Args:
        value: datetime object (presumibilmente in UTC)
        format_string: formato di output (default: '%d/%m/%Y alle %H:%M')
    
    Returns:
        String formattata con data/ora nel fuso orario di Roma
    """
    if value is None:
        return ''
    
    # Timezone di Roma
    rome_tz = pytz.timezone('Europe/Rome')
    
    # Se il datetime non ha timezone, assumiamo sia UTC
    if value.tzinfo is None:
        value = pytz.utc.localize(value)
    
    # Converti in fuso orario di Roma
    rome_dt = value.astimezone(rome_tz)
    
    # Formatta secondo il formato richiesto
    return rome_dt.strftime(format_string)


def linkify(text):
    """Converte automaticamente URL in link cliccabili e poi applica nl2br.
    
    Args:
        text: testo che può contenere URL
    
    Returns:
        HTML con link cliccabili e a capo preservati
    """
    if not text:
        return ''
    
    import re
    
    # Prima escape del testo per sicurezza
    text = escape(text)
    
    # Pattern per rilevare URL (supporta http, https, ftp e www)
    url_pattern = re.compile(
        r'(?i)\b((?:https?://|ftp://|www\.)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?«»""'']))',
        re.IGNORECASE
    )
    
    def replace_url(match):
        url = match.group(0)
        # Se inizia con www ma non ha protocollo, aggiungi http://
        if url.lower().startswith('www.'):
            href = 'http://' + url
        else:
            href = url
        # Tronca il testo del link se è troppo lungo
        display_text = url if len(url) <= 50 else url[:47] + '...'
        return f'<a href="{href}" target="_blank" rel="noopener noreferrer" style="color: #25B36A; text-decoration: underline;">{display_text}</a>'
    
    # Sostituisci tutti gli URL trovati
    text_with_links = url_pattern.sub(replace_url, str(text))
    
    # Converti newline in <br>
    text_with_links = text_with_links.replace('\n', '<br>\n')
    
    return Markup(text_with_links)


def image_url(path: str | None) -> str:
    """
    Filtro smart per URL immagini.

    - Se l'URL inizia con http:// o https:// → ritorna così com'è (URL esterno)
    - Altrimenti → aggiunge / davanti (percorso locale)

    Esempio:
        {{ response.photo_front|image_url }}

    Args:
        path: Percorso immagine (locale o URL completo)

    Returns:
        URL corretto per l'attributo src
    """
    if not path:
        return ""

    # Se è già un URL completo, ritorna così com'è
    if path.startswith(('http://', 'https://')):
        return path

    # Altrimenti è un percorso locale, aggiungi / se non c'è già
    if path.startswith('/'):
        return path

    return f"/{path}"


# --------------------------------------------------------------------------- #
# Flask helper
# --------------------------------------------------------------------------- #

def register_filters(app):
    """Registra in una app Flask tutti i filtri definiti in questo modulo."""
    app.add_template_filter(datetime_filter, "datetime")
    app.add_template_filter(date_filter, "date")
    app.add_template_filter(nl2br, "nl2br")
    # Alias compatibile con Django / Jinja built‑in
    app.add_template_filter(file_size, "filesizeformat")
    app.add_template_filter(file_size, "file_size")
    # Aggiungi il filtro timeago
    app.add_template_filter(timeago, "timeago")
    # Aggiungi il filtro per il fuso orario di Roma
    app.add_template_filter(rome_datetime, "rome_datetime")
    # Aggiungi il filtro per i link cliccabili
    app.add_template_filter(linkify, "linkify")
    # Aggiungi il filtro per URL immagini smart
    app.add_template_filter(image_url, "image_url")

    # Per comodità esponiamo anche il modulo come variabile globale
    app.jinja_env.globals.setdefault("filters", globals())