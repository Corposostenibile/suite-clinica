"""
auth.routes
===========

Flusso completo:

1. **Login**               – GET/POST  → /auth/login
2. **Logout**              – POST      → /auth/logout
3. **Forgot-password**     – GET/POST  → /auth/forgot-password
4. **Reset-password**      – GET/POST  → /auth/reset-password/<token>

Dopo un login riuscito l’utente viene reindirizzato al modulo **team** (lista utenti).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)
from itsdangerous import BadSignature, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from corposostenibile.extensions import db
from corposostenibile.models import User, ImpersonationLog
from .forms import ForgotPasswordForm, LoginForm, ResetPasswordForm
from .email_utils import send_mail
from flask import session

# --------------------------------------------------------------------------- #
#  Blueprint setup                                                            #
# --------------------------------------------------------------------------- #

auth_bp = Blueprint(
    "auth",
    __name__,
    template_folder="templates",
    static_folder="static",
)

# --------------------------------------------------------------------------- #
#  Helper functions                                                           #
# --------------------------------------------------------------------------- #

def _send_password_changed_email(user: User, ip_address: str) -> None:
    """Invia email di conferma dopo cambio password."""
    from datetime import datetime
    from flask import render_template_string, current_app
    
    # Prepara il contesto per il template
    template_path = Path(__file__).parent / "templates" / "auth" / "email" / "password_changed.html"
    with open(template_path, 'r', encoding='utf-8') as f:
        html_template = f.read()
    
    # Formatta data e ora in italiano
    now = datetime.now()
    change_date = now.strftime("%d/%m/%Y alle ore %H:%M")
    
    # Renderizza il template con i dati
    html_body = render_template_string(
        html_template,
        user_name=user.first_name or user.email,
        change_date=change_date,
        ip_address=ip_address or "Non disponibile",
        login_url=url_for("auth.login", _external=True)
    )
    
    # Versione testo semplice
    text_body = (
        f"Ciao {user.first_name or user.email},\n\n"
        "La tua password è stata correttamente resettata.\n\n"
        f"Dettagli della modifica:\n"
        f"- Data e ora: {change_date}\n"
        f"- IP di provenienza: {ip_address or 'Non disponibile'}\n\n"
        "IMPORTANTE: Se non hai richiesto tu questa modifica, contatta immediatamente il team IT!\n\n"
        "Facciamo ogni giorno la differenza insieme.\n"
        "Grazie di far parte del team Corposostenibile"
    )
    
    # Prepara il path del logo
    logo_path = Path(current_app.root_path) / "static" / "assets" / "immagini" / "Suite.png"
    
    # Invia email con entrambe le versioni e logo embeddato
    from .email_utils import send_mail_html
    send_mail_html(
        "Password Modificata - Corposostenibile Suite",
        [user.email],
        text_body,
        html_body,
        attachments={"logo": str(logo_path)}
    )


def _get_serializer() -> URLSafeTimedSerializer:
    """Restituisce un serializer firmato con secret-key + salt."""
    from flask import current_app

    secret = current_app.config["SECRET_KEY"]
    salt = current_app.config.get("SECURITY_PASSWORD_SALT", "pw-reset")
    return URLSafeTimedSerializer(secret, salt=salt)


def _generate_reset_token(user: User) -> str:
    return _get_serializer().dumps({"uid": user.id})


def _verify_reset_token(token: str, max_age: int = 3600) -> User | None:
    s = _get_serializer()
    try:
        data = s.loads(token, max_age=max_age)
    except BadSignature:
        return None
    return User.query.get(data.get("uid"))  # type: ignore[arg-type]


def _send_reset_email(user: User) -> None:
    token = _generate_reset_token(user)
    reset_url = url_for("auth.reset_password", token=token, _external=True)
    
    # Prepara il contesto per il template
    from flask import render_template_string
    
    # Legge il template HTML
    template_path = Path(__file__).parent / "templates" / "auth" / "email" / "reset_password.html"
    with open(template_path, 'r', encoding='utf-8') as f:
        html_template = f.read()
    
    # Renderizza il template con i dati
    html_body = render_template_string(
        html_template,
        user_name=user.first_name or user.email,
        reset_url=reset_url
    )
    
    # Versione testo semplice per client che non supportano HTML
    text_body = (
        f"Ciao {user.first_name or user.email},\n\n"
        "Abbiamo ricevuto una richiesta di reset della password per il tuo account.\n"
        "Per reimpostare la tua password clicca sul link seguente:\n\n"
        f"{reset_url}\n\n"
        "Questo link scadrà tra 1 ora.\n\n"
        "IMPORTANTE: Se non hai richiesto tu il reset, contatta immediatamente il team IT!\n\n"
        "Facciamo ogni giorno la differenza insieme.\n"
        "Grazie di far parte del team Corposostenibile"
    )
    
    # Prepara il path del logo
    from flask import current_app
    logo_path = Path(current_app.root_path) / "static" / "assets" / "immagini" / "Suite.png"
    
    # Invia email con entrambe le versioni e logo embeddato
    from .email_utils import send_mail_html
    send_mail_html(
        "Reset Password - Corposostenibile Suite",
        [user.email],
        text_body,
        html_body,
        attachments={"logo": str(logo_path)}
    )

# --------------------------------------------------------------------------- #
#  Routes                                                                     #
# --------------------------------------------------------------------------- #


@auth_bp.route("/login", methods=["GET", "POST"])
def login():  # noqa: D401
    """Form di login con redirect alla Welcome page se autenticato."""
    if current_user.is_authenticated:
        return redirect(url_for("welcome.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user: User | None = User.query.filter_by(
            email=form.email.data.lower()
        ).first()
        if not user:
            flash("Email non trovata. Verifica l'indirizzo inserito.", "danger")
        elif not check_password_hash(user.password_hash, form.password.data):
            flash("Password errata, riprova.", "danger")
        else:
            login_user(user, remember=form.remember_me.data)
            flash("Benvenuto!", "success")
            # priorità al parametro next, altrimenti Welcome
            next_url = request.args.get("next") or url_for("welcome.index")
            return redirect(next_url)

    return render_template("auth/login.html", form=form)

@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """Chiude la sessione utente."""
    logout_user()
    flash("Sei uscito dall’account.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Richiesta link di reset password."""
    if current_user.is_authenticated:
        return redirect(url_for("team.user_list"))

    if request.is_json:
        form = ForgotPasswordForm(data=request.get_json())
    else:
        form = ForgotPasswordForm()

    if form.validate_on_submit():
        user: User | None = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            _send_reset_email(user)
            if request.is_json:
                return {'success': True, 'message': 'Email inviata! Controlla la tua casella di posta.'}, 200
            flash("Email inviata! Controlla la tua casella di posta.", "success")
            return redirect(url_for("auth.login"))
        else:
            if request.is_json:
                return {'success': False, 'error': 'Questa email non esiste nel sistema.'}, 400
            flash("Questa email non esiste nel sistema.", "danger")
    elif request.is_json and (form.errors or not request.get_json()):
        return {'success': False, 'error': form.errors if form.errors else 'Missing email'}, 400

    return render_template("auth/forgot_password.html", form=form)


@auth_bp.route("/verify-reset-token/<token>", methods=["GET"])
def verify_reset_token(token: str):
    """Verifica validità token."""
    user = _verify_reset_token(token)
    if user:
        return {'valid': True}, 200
    return {'valid': False, 'error': 'Token non valido o scaduto'}, 400


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token: str):
    """Imposta una nuova password usando il token ricevuto via e-mail."""
    if current_user.is_authenticated:
        return redirect(url_for("team.user_list"))

    user = _verify_reset_token(token)
    if not user:
        flash("Link non valido o scaduto.", "danger")
        return redirect(url_for("auth.forgot_password"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.password_hash = generate_password_hash(form.password.data)
        user.last_password_change_at = datetime.utcnow()
        
        # Ottieni IP dell'utente
        user_ip = request.remote_addr or request.environ.get('HTTP_X_FORWARDED_FOR', 'Non disponibile')
        
        db.session.commit()
        
        # Invia email di conferma
        try:
            _send_password_changed_email(user, user_ip)
        except Exception as e:
            current_app.logger.error(f"Errore invio email conferma reset: {e}")
        
        flash("Password aggiornata, ora puoi accedere.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", form=form)


# --------------------------------------------------------------------------- #
#  Impersonation Routes (Admin Only)                                          #
# --------------------------------------------------------------------------- #

@auth_bp.route("/impersonate")
@login_required
def impersonate_list():
    """Pagina admin con lista utenti per impersonation."""
    if not current_user.is_admin:
        flash("Accesso non autorizzato.", "danger")
        return redirect(url_for("welcome.index"))

    # Non permettere impersonation se già in modalità impersonation
    if session.get('impersonating'):
        flash("Sei già in modalità impersonazione. Torna al tuo account prima.", "warning")
        return redirect(url_for("welcome.index"))

    users = User.query.filter(
        User.is_active == True,
        User.id != current_user.id
    ).order_by(User.first_name, User.last_name).all()

    # Log recenti delle impersonazioni
    recent_logs = ImpersonationLog.query.filter_by(
        admin_id=current_user.id
    ).order_by(ImpersonationLog.started_at.desc()).limit(10).all()

    return render_template(
        "auth/impersonate_list.html",
        users=users,
        recent_logs=recent_logs
    )


@auth_bp.route("/impersonate/<int:user_id>", methods=["POST"])
@login_required
def impersonate_user(user_id: int):
    """Accede come un altro utente."""
    if not current_user.is_admin:
        if request.is_json:
            return {'success': False, 'error': 'Accesso non autorizzato.'}, 403
        flash("Accesso non autorizzato.", "danger")
        return redirect(url_for("welcome.index"))

    # Non permettere impersonation se già in modalità impersonazione
    if session.get('impersonating'):
        if request.is_json:
            return {'success': False, 'error': 'Sei già in modalità impersonazione.'}, 400
        flash("Sei già in modalità impersonazione. Torna al tuo account prima.", "warning")
        return redirect(url_for("welcome.index"))

    target_user = User.query.get(user_id)
    if not target_user:
        if request.is_json:
            return {'success': False, 'error': 'Utente non trovato.'}, 404
        return "Not Found", 404

    # Non permettere di impersonare se stessi
    if target_user.id == current_user.id:
        if request.is_json:
            return {'success': False, 'error': 'Non puoi impersonare te stesso.'}, 400
        flash("Non puoi impersonare te stesso.", "warning")
        return redirect(url_for("auth.impersonate_list"))

    # Salva l'ID dell'admin originale nella sessione
    session['impersonating'] = True
    session['original_admin_id'] = current_user.id
    session['original_admin_name'] = current_user.full_name

    # Crea log dell'impersonazione
    log = ImpersonationLog(
        admin_id=current_user.id,
        impersonated_user_id=target_user.id,
        ip_address=request.remote_addr or request.environ.get('HTTP_X_FORWARDED_FOR'),
        user_agent=request.user_agent.string[:500] if request.user_agent else None,
        reason=request.form.get('reason', '')
    )
    db.session.add(log)
    db.session.commit()

    # Salva l'ID del log per aggiornarlo quando si esce
    session['impersonation_log_id'] = log.id

    # Effettua il login come l'utente target
    logout_user()
    login_user(target_user)

    if request.is_json:
        return {'success': True, 'message': f'Stai ora navigando come {target_user.full_name}'}, 200

    flash(f"Stai ora navigando come {target_user.full_name}", "info")
    return redirect(url_for("welcome.index"))


@auth_bp.route("/stop-impersonation", methods=["POST"])
@login_required
def stop_impersonation():
    """Torna all'account admin originale."""
    if not session.get('impersonating'):
        if request.is_json:
            return {'success': False, 'error': 'Non sei in modalità impersonazione.'}, 400
        flash("Non sei in modalità impersonazione.", "warning")
        return redirect(url_for("welcome.index"))

    original_admin_id = session.get('original_admin_id')
    impersonation_log_id = session.get('impersonation_log_id')

    if not original_admin_id:
        if request.is_json:
            return {'success': False, 'error': 'Errore: impossibile recuperare l\'account originale.'}, 400
        flash("Errore: impossibile recuperare l'account originale.", "danger")
        # Pulisci comunque la sessione
        session.pop('impersonating', None)
        session.pop('original_admin_id', None)
        session.pop('original_admin_name', None)
        session.pop('impersonation_log_id', None)
        return redirect(url_for("auth.logout"))

    # Aggiorna il log con timestamp di fine
    if impersonation_log_id:
        log = ImpersonationLog.query.get(impersonation_log_id)
        if log:
            log.ended_at = datetime.utcnow()
            db.session.commit()

    # Recupera l'admin originale
    admin = User.query.get(original_admin_id)
    if not admin:
        if request.is_json:
            return {'success': False, 'error': 'Errore: account admin non trovato.'}, 400
        flash("Errore: account admin non trovato.", "danger")
        session.pop('impersonating', None)
        session.pop('original_admin_id', None)
        session.pop('original_admin_name', None)
        session.pop('impersonation_log_id', None)
        return redirect(url_for("auth.login"))

    # Pulisci la sessione di impersonation
    session.pop('impersonating', None)
    session.pop('original_admin_id', None)
    session.pop('original_admin_name', None)
    session.pop('impersonation_log_id', None)

    # Effettua il login come admin
    logout_user()
    login_user(admin)

    if request.is_json:
        return {'success': True, 'message': f'Sei tornato al tuo account ({admin.full_name})'}, 200

    flash(f"Sei tornato al tuo account ({admin.full_name})", "success")
    return redirect(url_for("welcome.index"))

