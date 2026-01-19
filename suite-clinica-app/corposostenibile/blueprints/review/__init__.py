"""
Blueprint Review
================

Sistema di recensioni/valutazioni per i membri del team.

Funzionalità:
- I responsabili possono scrivere review ai membri del loro dipartimento
- I membri possono vedere e confermare la lettura delle loro review
- Gli admin possono gestire tutte le review
"""

from flask import Blueprint

bp = Blueprint(
    'review',
    __name__,
    template_folder='templates',
    static_folder='static',
    url_prefix='/review'
)

from corposostenibile.blueprints.review import routes
from corposostenibile.blueprints.review.filters import register_filters

def init_app(app):
    """Inizializza il blueprint review."""
    app.register_blueprint(bp)
    register_filters(app)