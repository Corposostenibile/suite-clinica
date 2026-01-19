"""
corposostenibile.blueprints.auth
================================

Blueprint “auth” – login / logout e flusso *password-reset*.

* Rotte pubbliche:
  • **/auth/login**                – form login  
  • **/auth/logout**               – logout immediato  
  • **/auth/forgot-password**      – richiesta reset (e-mail con token)  
  • **/auth/reset-password/<tok>** – scelta nuova password

* Dipendenze:
  • `flask-login`  – gestione sessione
  • `itsdangerous` – token firmati per reset password
  • (opz.) `flask-mail`  – invio e-mail, altrimenti semplice log
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from flask import Flask
from flask_login import LoginManager
from werkzeug.security import check_password_hash

from corposostenibile.models import User
from .routes import auth_bp  # noqa: E402 – blueprint definito in routes.py
from .api import auth_api_bp  # API endpoints for React frontend

# --------------------------------------------------------------------------- #
#  LoginManager setup                                                         #
# --------------------------------------------------------------------------- #
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.session_protection = "strong"


@login_manager.user_loader
def _load_user(user_id: str) -> User | None:  # pragma: no cover
    """Callback flask-login – ritorna User (o None) dato l’ID in sessione."""
    try:
        return User.query.get(int(user_id))
    except Exception:
        return None


def _request_loader(req) -> User | None:  # pragma: no cover
    """
    Login “token” via header `Authorization: Basic (email:token)` – facoltativo.
    Utile per API se in futuro vorrai generare token statici.
    """
    auth = req.authorization
    if not auth:
        return None
    user = User.query.filter_by(email=auth.username).first()
    if user and check_password_hash(user.password_hash, auth.password):  # reuse hash check
        return user
    return None


# --------------------------------------------------------------------------- #
#  Factory helper                                                             #
# --------------------------------------------------------------------------- #
def init_app(app: Flask) -> None:  # noqa: D401
    """
    Registra blueprint e inizializza *login_manager* sull’app principale.
    Da invocare nella *application-factory* **dopo** l’init delle estensioni.
    """
    # ---- LoginManager ---- #
    login_manager.init_app(app)
    login_manager.request_loader(_request_loader)

    # remember-me cookie valido 30 giorni (override via app.config se serve)
    app.config.setdefault("REMEMBER_COOKIE_DURATION", timedelta(days=30))

    # ---- Blueprint ---- #
    app.register_blueprint(auth_bp, url_prefix="/auth")

    # ---- API Blueprint for React ---- #
    app.register_blueprint(auth_api_bp)

    # ---- Jinja helper ---- #
    @app.context_processor
    def _inject_user() -> dict[str, Any]:  # pragma: no cover
        """Rende `current_user` disponibile come `g_user` nei template."""
        from flask_login import current_user  # late import
        return {"g_user": current_user}
