from __future__ import annotations
from flask import Flask


def init_app(app: Flask) -> None:
    from .api import appointment_setting_api_bp
    app.register_blueprint(appointment_setting_api_bp)
