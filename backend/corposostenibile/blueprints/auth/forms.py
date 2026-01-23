"""
auth.forms
==========

Form Flask‑WTF per il blueprint di autenticazione.
"""
from __future__ import annotations

from flask_babel import lazy_gettext as _l
from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField, ValidationError
from wtforms.validators import DataRequired, Email, EqualTo, Length
import re


class LoginForm(FlaskForm):
    """Form di login con opzione *Ricordami*."""

    email = StringField(
        _l("E‑mail"),
        validators=[DataRequired(), Email(), Length(max=255)],
    )
    password = PasswordField(
        _l("Password"),
        validators=[DataRequired()],
    )
    remember_me = BooleanField(_l("Ricordami"), default=False)
    submit = SubmitField(_l("Entra"))


class ForgotPasswordForm(FlaskForm):
    """Form di richiesta reset password."""

    email = StringField(
        _l("E‑mail"),
        validators=[DataRequired(), Email(), Length(max=255)],
    )
    submit = SubmitField(_l("Invia link"))


class ResetPasswordForm(FlaskForm):
    """Form di impostazione nuova password (dopo link e‑mail)."""

    password = PasswordField(
        _l("Nuova password"),
        validators=[DataRequired(), Length(min=8, message=_l("Minimo 8 caratteri"))],
    )
    password2 = PasswordField(
        _l("Conferma password"),
        validators=[
            DataRequired(),
            EqualTo("password", message=_l("Le password non coincidono")),
        ],
    )
    submit = SubmitField(_l("Aggiorna password"))
    
    def validate_password(self, field):
        """Validazione password con requisiti di sicurezza."""
        password = field.data
        
        # Check minimo 8 caratteri (già fatto da Length validator)
        
        # Check almeno una maiuscola
        if not re.search(r'[A-Z]', password):
            raise ValidationError(_l("La password deve contenere almeno una lettera maiuscola"))
        
        # Check almeno una minuscola
        if not re.search(r'[a-z]', password):
            raise ValidationError(_l("La password deve contenere almeno una lettera minuscola"))
        
        # Check almeno un numero
        if not re.search(r'\d', password):
            raise ValidationError(_l("La password deve contenere almeno un numero"))
        
        # Check almeno un carattere speciale
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError(_l("La password deve contenere almeno un carattere speciale"))
