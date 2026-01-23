"""
Blueprint per la gestione delle comunicazioni aziendali.
"""

from flask import Blueprint

communications_bp = Blueprint(
    'communications',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/static/communications'
)

from . import routes, api_routes
from .init_app import init_app

__all__ = ['communications_bp', 'init_app']