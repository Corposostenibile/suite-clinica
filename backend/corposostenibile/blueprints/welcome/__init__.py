# corposostenibile/blueprints/welcome/__init__.py

"""
corposostenibile.blueprints.welcome
===================================
Blueprint "welcome" - pagina di benvenuto personalizzata.
"""

from __future__ import annotations

from flask import Blueprint, Flask

welcome_bp = Blueprint("welcome", __name__, url_prefix="/welcome")


def init_app(app: Flask) -> None:
    """Register welcome blueprint."""
    app.register_blueprint(welcome_bp)
