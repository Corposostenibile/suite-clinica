"""
auth.api
========

REST API endpoints for React frontend authentication.
All endpoints return JSON responses.
"""
from __future__ import annotations

from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from corposostenibile.extensions import db, csrf
from corposostenibile.models import User
from .routes import _generate_reset_token, _verify_reset_token, _send_reset_email, _send_password_changed_email

# --------------------------------------------------------------------------- #
#  Blueprint setup                                                            #
# --------------------------------------------------------------------------- #

auth_api_bp = Blueprint(
    "auth_api",
    __name__,
    url_prefix="/api/auth",
)

# Exempt API blueprint from CSRF protection (JSON API with session cookies)
csrf.exempt(auth_api_bp)


# --------------------------------------------------------------------------- #
#  API Routes                                                                  #
# --------------------------------------------------------------------------- #

@auth_api_bp.route("/login", methods=["POST"])
def api_login():
    """
    Login with email and password.

    Request JSON:
        {
            "email": "user@example.com",
            "password": "password123",
            "remember_me": false
        }

    Response JSON:
        Success: {"success": true, "user": {...}}
        Error: {"success": false, "error": "message"}
    """
    try:
        # Ripristina la sessione DB se una richiesta precedente ha lasciato la transazione in errore
        db.session.rollback()
        if current_user.is_authenticated:
            return jsonify({
                "success": True,
                "user": _user_to_dict(current_user),
                "redirect": "/welcome"
            })

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Dati non validi"}), 400

        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        remember_me = bool(data.get("remember_me", False))

        if not email or not password:
            return jsonify({"success": False, "error": "Email e password sono richiesti"}), 400

        # Rollback prima della query login: il caricamento di current_user può aver lasciato la transazione in errore
        db.session.rollback()
        user = User.query.filter_by(email=email).first()

        if not user:
            return jsonify({"success": False, "error": "Email non trovata. Verifica l'indirizzo inserito."}), 401

        if not user.is_active:
            return jsonify({"success": False, "error": "Account disattivato. Contatta il team IT."}), 401

        if not user.password_hash or not check_password_hash(user.password_hash, password):
            return jsonify({"success": False, "error": "Password errata, riprova."}), 401

        login_user(user, remember=remember_me)

        return jsonify({
            "success": True,
            "user": _user_to_dict(user),
            "redirect": "/welcome"
        })
    except Exception as e:
        from flask import current_app
        current_app.logger.exception("Login API error: %s", e)
        return jsonify({"success": False, "error": "Errore durante il login. Riprova più tardi."}), 500


@auth_api_bp.route("/logout", methods=["POST"])
@login_required
def api_logout():
    """
    Logout current user.

    Response JSON:
        {"success": true, "message": "Logout effettuato"}
    """
    logout_user()
    return jsonify({
        "success": True,
        "message": "Sei uscito dall'account."
    })


@auth_api_bp.route("/me", methods=["GET"])
def api_me():
    """
    Get current user info.

    Response JSON:
        Authenticated: {"authenticated": true, "user": {...}}
        Not authenticated: {"authenticated": false}
    """
    if current_user.is_authenticated:
        return jsonify({
            "authenticated": True,
            "user": _user_to_dict(current_user)
        })
    return jsonify({"authenticated": False})


@auth_api_bp.route("/forgot-password", methods=["POST"])
def api_forgot_password():
    """
    Request password reset email.

    Request JSON:
        {"email": "user@example.com"}

    Response JSON:
        Always returns success for privacy (don't reveal if email exists)
        {"success": true, "message": "..."}
    """
    if current_user.is_authenticated:
        return jsonify({"success": False, "error": "Già autenticato"}), 400

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Dati non validi"}), 400

    email = data.get("email", "").lower().strip()
    if not email:
        return jsonify({"success": False, "error": "Email richiesta"}), 400

    user = User.query.filter_by(email=email).first()
    if user:
        try:
            _send_reset_email(user)
        except Exception as e:
            # Log error but don't reveal to user
            from flask import current_app
            current_app.logger.error(f"Errore invio email reset: {e}")

    # Always return success for privacy
    return jsonify({
        "success": True,
        "message": "Se l'email è associata a un account, riceverai le istruzioni per il reset."
    })


@auth_api_bp.route("/verify-reset-token/<token>", methods=["GET"])
def api_verify_reset_token(token: str):
    """
    Verify if a reset token is valid.

    Response JSON:
        Valid: {"valid": true}
        Invalid: {"valid": false, "error": "..."}
    """
    user = _verify_reset_token(token)
    if not user:
        return jsonify({
            "valid": False,
            "error": "Link non valido o scaduto."
        }), 400

    return jsonify({"valid": True})


@auth_api_bp.route("/reset-password/<token>", methods=["POST"])
def api_reset_password(token: str):
    """
    Reset password using token.

    Request JSON:
        {
            "password": "newpassword123",
            "password2": "newpassword123"
        }

    Response JSON:
        Success: {"success": true, "message": "..."}
        Error: {"success": false, "error": "..."}
    """
    if current_user.is_authenticated:
        return jsonify({"success": False, "error": "Già autenticato"}), 400

    user = _verify_reset_token(token)
    if not user:
        return jsonify({
            "success": False,
            "error": "Link non valido o scaduto."
        }), 400

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Dati non validi"}), 400

    password = data.get("password", "")
    password2 = data.get("password2", "")

    # Validate password
    validation_error = _validate_password(password, password2)
    if validation_error:
        return jsonify({"success": False, "error": validation_error}), 400

    # Update password
    user.password_hash = generate_password_hash(password)
    user.last_password_change_at = datetime.utcnow()

    # Get user IP
    user_ip = request.remote_addr or request.environ.get('HTTP_X_FORWARDED_FOR', 'Non disponibile')

    db.session.commit()

    # Send confirmation email
    try:
        _send_password_changed_email(user, user_ip)
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Errore invio email conferma reset: {e}")

    return jsonify({
        "success": True,
        "message": "Password aggiornata con successo!"
    })


# --------------------------------------------------------------------------- #
#  Helper functions                                                           #
# --------------------------------------------------------------------------- #

def _user_to_dict(user: User) -> dict:
    """Convert User model to JSON-safe dict."""
    role_val = getattr(user, "role", None)
    role_value = role_val.value if (role_val is not None and hasattr(role_val, "value")) else (str(role_val) if role_val is not None else None)
    spec = getattr(user, "specialty", None)
    specialty_value = spec.value if (spec is not None and hasattr(spec, "value")) else (str(spec) if spec is not None else None)
    full_name = getattr(user, "full_name", None) or f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip()
    is_hm_team_leader = False
    if role_value == "team_leader":
        teams_led = getattr(user, "teams_led", []) or []
        is_hm_team_leader = any(
            (getattr(getattr(team, "team_type", None), "value", getattr(team, "team_type", None)) == "health_manager")
            for team in teams_led
        )
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": full_name,
        "is_admin": getattr(user, "is_admin", False),
        "role": role_value,
        "specialty": specialty_value,
        "avatar_path": getattr(user, "avatar_path", None),
        "is_trial": getattr(user, "is_trial", False),
        "trial_stage": getattr(user, "trial_stage", None),
        "trial_supervisor_id": getattr(user, "trial_supervisor_id", None),
        "is_health_manager_team_leader": is_hm_team_leader,
    }


def _validate_password(password: str, password2: str) -> str | None:
    """
    Validate password meets requirements.
    Returns error message or None if valid.
    """
    if not password or not password2:
        return "Password richiesta"

    if password != password2:
        return "Le password non coincidono"

    if len(password) < 8:
        return "La password deve essere di almeno 8 caratteri"

    import re
    if not re.search(r"[A-Z]", password):
        return "La password deve contenere almeno una lettera maiuscola"

    if not re.search(r"[a-z]", password):
        return "La password deve contenere almeno una lettera minuscola"

    if not re.search(r"[0-9]", password):
        return "La password deve contenere almeno un numero"

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return "La password deve contenere almeno un carattere speciale (!@#$%^&*)"

    return None
