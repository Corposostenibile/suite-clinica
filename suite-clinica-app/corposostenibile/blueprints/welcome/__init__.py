# corposostenibile/blueprints/welcome/__init__.py

"""
corposostenibile.blueprints.welcome
===================================
Blueprint "welcome" - pagina di benvenuto personalizzata.
"""

from __future__ import annotations

from flask import Flask
from .routes import welcome_bp

def init_app(app: Flask) -> None:  # noqa: D401
    """Registra il blueprint sull'app principale."""
    app.register_blueprint(welcome_bp, url_prefix="/welcome")
