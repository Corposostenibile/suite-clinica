"""
Filtri template per il blueprint Review
"""

import re
from markupsafe import Markup


def nl2br(value):
    """
    Converte i newline in tag <br> HTML.
    """
    if not value:
        return ''
    
    # Escape HTML per sicurezza
    value = str(value)
    value = value.replace('&', '&amp;')
    value = value.replace('<', '&lt;')
    value = value.replace('>', '&gt;')
    value = value.replace('"', '&quot;')
    value = value.replace("'", '&#39;')
    
    # Converti newline in <br>
    value = value.replace('\r\n', '<br>')
    value = value.replace('\n', '<br>')
    value = value.replace('\r', '<br>')
    
    return Markup(value)


def register_filters(app):
    """
    Registra i filtri template nell'app Flask.
    """
    app.jinja_env.filters['nl2br'] = nl2br