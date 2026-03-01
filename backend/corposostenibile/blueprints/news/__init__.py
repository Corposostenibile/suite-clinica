"""
Blueprint per la gestione delle Novità/Aggiornamenti di Corposostenibile Suite.
"""

from flask import Blueprint

news_bp = Blueprint(
    'news',
    __name__,
    template_folder='templates',
    url_prefix='/news'
)

from . import routes
from .api_routes import news_api_bp

__all__ = ['news_bp', 'news_api_bp']
