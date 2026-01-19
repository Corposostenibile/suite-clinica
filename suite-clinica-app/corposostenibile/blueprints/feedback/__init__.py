"""
Feedback Blueprint
=================

Gestione feedback per azienda, nutrizionista, psicologa e coach.
"""

from flask import Blueprint

bp = Blueprint(
    'feedback',
    __name__,
    template_folder='templates',
    static_folder='static',
    url_prefix='/feedback'
)

from . import routes 