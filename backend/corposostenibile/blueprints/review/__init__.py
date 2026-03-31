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
    url_prefix='/review'
)

from corposostenibile.blueprints.review import routes

def init_app(app):
    """Inizializza il blueprint review."""
    app.register_blueprint(bp)
