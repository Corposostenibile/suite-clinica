"""
Filtri Jinja personalizzati per il blueprint customers
"""
from enum import Enum
from typing import Any

def format_enum_value(value: Any) -> str:
    """
    Formatta un valore Enum per la visualizzazione.
    Se è un Enum, restituisce il suo valore, altrimenti restituisce il valore così com'è.
    """
    if isinstance(value, Enum):
        return value.value
    return str(value) if value else ""

def format_giorno(value: Any) -> str:
    """
    Formatta un valore GiornoEnum in modo leggibile.
    Capitalizza la prima lettera per una migliore presentazione.
    """
    if value is None:
        return ""
    
    if isinstance(value, Enum):
        giorno = value.value
    else:
        giorno = str(value)
    
    # Mappa per i giorni abbreviati
    giorni_map = {
        'lun': 'Lunedì',
        'mar': 'Martedì', 
        'mer': 'Mercoledì',
        'gio': 'Giovedì',
        'ven': 'Venerdì',
        'sab': 'Sabato',
        'dom': 'Domenica',
        'lunedi': 'Lunedì',
        'martedi': 'Martedì',
        'mercoledi': 'Mercoledì',
        'giovedi': 'Giovedì',
        'venerdi': 'Venerdì',
        'sabato': 'Sabato',
        'domenica': 'Domenica'
    }
    
    return giorni_map.get(giorno.lower(), giorno.capitalize())

def image_url(path: Any) -> str:
    """
    Filtro smart per URL immagini.

    - Se l'URL inizia con http:// o https:// → ritorna così com'è (URL esterno)
    - Altrimenti → aggiunge / davanti (percorso locale)

    Args:
        path: Percorso immagine (locale o URL completo)

    Returns:
        URL corretto per l'attributo src
    """
    if not path:
        return ""

    path_str = str(path)

    # Se è già un URL completo, ritorna così com'è
    if path_str.startswith(('http://', 'https://')):
        return path_str

    # Altrimenti è un percorso locale, aggiungi / se non c'è già
    if path_str.startswith('/'):
        return path_str

    return f"/{path_str}"

def register_filters(app):
    """Registra i filtri Jinja personalizzati"""
    app.jinja_env.filters['enum_value'] = format_enum_value
    app.jinja_env.filters['format_giorno'] = format_giorno
    app.jinja_env.filters['image_url'] = image_url