"""
Inizializzazione del blueprint communications.
"""

from flask import Flask
from . import communications_bp


def init_app(app: Flask) -> None:
    """
    Registra il blueprint communications nell'applicazione Flask.
    
    Args:
        app: L'istanza Flask dell'applicazione
    """
    app.register_blueprint(communications_bp, url_prefix='/communications')