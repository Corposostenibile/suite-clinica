"""
Forms per la gestione degli User in prova (Trial Users)
"""
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, BooleanField, SelectField,
    IntegerField, SelectMultipleField, TextAreaField, HiddenField
)
from wtforms.validators import DataRequired, Email, Length, Optional, ValidationError
from wtforms.widgets import CheckboxInput, ListWidget
from corposostenibile.models import User, Cliente, Department


class MultiCheckboxField(SelectMultipleField):
    """Campo per checkbox multipli"""
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


class TrialUserForm(FlaskForm):
    """Form per creare/modificare un User in prova"""

    # Dati base
    first_name = StringField('Nome', validators=[DataRequired(), Length(max=80)])
    last_name = StringField('Cognome', validators=[DataRequired(), Length(max=80)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField('Password', validators=[Length(min=8, max=128)])

    # Dipartimento
    department_id = SelectField('Dipartimento', coerce=int, validators=[Optional()])
    job_title = StringField('Ruolo', validators=[Optional(), Length(max=120)])

    # Trial Settings
    is_trial = BooleanField('User in prova', default=True)
    trial_stage = SelectField('Stage',
                             choices=[
                                 (1, 'Stage 1: Dashboard + Training'),
                                 (2, 'Stage 2: Clienti Selezionati'),
                                 (3, 'Stage 3: User Ufficiale')
                             ],
                             coerce=int,
                             default=1,
                             validators=[DataRequired()])

    # Supervisor
    trial_supervisor_id = SelectField('Supervisor', coerce=int, validators=[Optional()])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Popola dipartimenti
        self.department_id.choices = [(0, '-- Seleziona --')] + [
            (d.id, d.name) for d in Department.query.order_by(Department.name).all()
        ]

        # Popola supervisors (solo admin e head di dipartimento)
        supervisors = User.query.filter(
            (User.is_admin == True) |
            User.departments_led.any()
        ).order_by(User.first_name, User.last_name).all()

        self.trial_supervisor_id.choices = [(0, '-- Seleziona --')] + [
            (u.id, f"{u.full_name} ({u.department.name if u.department else 'Admin'})")
            for u in supervisors
        ]

    def validate_email(self, field):
        """Verifica unicità email"""
        user = User.query.filter_by(email=field.data).first()
        if user and (not hasattr(self, 'user_id') or user.id != self.user_id):
            raise ValidationError('Email già registrata')


class TrialUserPromoteForm(FlaskForm):
    """Form per promuovere un trial user allo stage successivo"""
    user_id = HiddenField('User ID', validators=[DataRequired()])
    notes = TextAreaField('Note promozione', validators=[Optional()])

    def validate_user_id(self, field):
        """Verifica che l'user sia un trial user"""
        user = User.query.get(field.data)
        if not user:
            raise ValidationError('Utente non trovato')
        if not user.is_trial:
            raise ValidationError('Utente non è un trial user')
        if user.trial_stage >= 3:
            raise ValidationError('Utente già al massimo stage')


class AssignClientsForm(FlaskForm):
    """Form per assegnare clienti a un trial user (Stage 2)"""
    user_id = HiddenField('User ID', validators=[DataRequired()])
    cliente_ids = MultiCheckboxField('Clienti da assegnare', coerce=int)
    notes = TextAreaField('Note assegnazione', validators=[Optional()])

    def __init__(self, user_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if user_id:
            self.user_id.data = user_id
            user = User.query.get(user_id)

            # Mostra solo clienti non ancora assegnati a questo trial user
            assigned_ids = [c.cliente_id for c in user.trial_assigned_clients] if user else []

            # Query clienti attivi
            clienti = Cliente.query.filter(
                Cliente.stato_cliente == 'attivo'
            ).order_by(Cliente.nome_cognome).all()

            # Filtra clienti non assegnati
            available_clients = [c for c in clienti if c.cliente_id not in assigned_ids]

            self.cliente_ids.choices = [
                (c.cliente_id, f"{c.nome_cognome} ({c.programma_attuale or 'N/D'})")
                for c in available_clients
            ]

    def validate_user_id(self, field):
        """Verifica che l'user sia trial e in stage 2"""
        user = User.query.get(field.data)
        if not user:
            raise ValidationError('Utente non trovato')
        if not user.is_trial:
            raise ValidationError('Utente non è un trial user')
        if user.trial_stage < 2:
            raise ValidationError('Utente deve essere almeno in Stage 2')