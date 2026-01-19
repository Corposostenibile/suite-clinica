"""
Form per la gestione dei progetti di sviluppo.
"""
from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, SelectField, DateField, IntegerField,
    BooleanField, FieldList, FormField, HiddenField, SelectMultipleField
)
from wtforms.validators import DataRequired, Optional, URL, NumberRange, ValidationError
from wtforms.widgets import ListWidget, CheckboxInput
from datetime import date


class MultiCheckboxField(SelectMultipleField):
    """Campo per checkbox multipli."""
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


class MilestoneSubForm(FlaskForm):
    """Sub-form per una singola milestone."""
    class Meta:
        csrf = False

    name = StringField('Nome Milestone', validators=[DataRequired()])
    description = TextAreaField('Descrizione')
    due_date = DateField('Scadenza', validators=[DataRequired()])
    assignee_id = SelectField('Assegnata a', coerce=int, validators=[Optional()])


class ProjectForm(FlaskForm):
    """Form per creare/modificare un progetto."""

    # Informazioni base
    name = StringField('Nome Progetto', validators=[DataRequired()])
    description = TextAreaField('Descrizione', validators=[DataRequired()])
    objective = TextAreaField('Obiettivo', validators=[DataRequired()])

    # Classificazione
    project_type = SelectField('Tipologia', choices=[
        ('feature', 'Nuova Funzionalità'),
        ('improvement', 'Miglioramento'),
        ('bugfix', 'Correzione Bug'),
        ('infrastructure', 'Infrastruttura'),
        ('integration', 'Integrazione'),
        ('optimization', 'Ottimizzazione'),
        ('migration', 'Migrazione')
    ], validators=[DataRequired()])

    priority = SelectField('Priorità', choices=[
        ('low', '🟢 Bassa'),
        ('medium', '🟡 Media'),
        ('high', '🟠 Alta'),
        ('critical', '🔴 Critica')
    ], default='medium', validators=[DataRequired()])

    status = SelectField('Stato', choices=[
        ('planning', 'Pianificazione'),
        ('in_progress', 'In Sviluppo'),
        ('testing', 'Testing'),
        ('review', 'Review'),
        ('completed', 'Completato'),
        ('on_hold', 'In Pausa'),
        ('cancelled', 'Cancellato')
    ], default='planning')

    # Assegnazioni
    # Project Manager fisso a Matteo Volpara (id=1)
    project_manager_id = HiddenField(default=1)

    # Membri del team (solo dipartimento IT)
    team_members = MultiCheckboxField('Membri del Team', coerce=int)

    # Dipartimento
    department_id = SelectField('Dipartimento', coerce=int, validators=[Optional()])
    is_company_wide = BooleanField('Progetto per tutta l\'azienda')

    # Repository
    repository_url = StringField('URL Repository', validators=[Optional(), URL()])

    # Milestone dinamiche (gestite via JavaScript)
    milestones_data = HiddenField('Milestones Data')


class MilestoneForm(FlaskForm):
    """Form per creare/modificare una milestone."""

    name = StringField('Nome Milestone', validators=[DataRequired()])
    description = TextAreaField('Descrizione')
    due_date = DateField('Scadenza', validators=[DataRequired()])

    status = SelectField('Stato', choices=[
        ('pending', 'In Attesa'),
        ('in_progress', 'In Corso'),
        ('completed', 'Completata'),
        ('delayed', 'In Ritardo'),
        ('cancelled', 'Cancellata')
    ], default='pending')

    assignee_id = SelectField('Assegnata a', coerce=int, validators=[Optional()])
    order_index = IntegerField('Ordine', default=0)
    progress_percentage = IntegerField(
        'Progresso (%)',
        default=0,
        validators=[NumberRange(min=0, max=100)]
    )

    # Deliverables e criteri (gestiti via JS)
    deliverables = HiddenField('Deliverables')
    success_criteria = HiddenField('Criteri di Successo')


class ProjectUpdateForm(FlaskForm):
    """Form per aggiungere aggiornamenti al progetto."""

    title = StringField('Titolo', validators=[DataRequired()])
    content = TextAreaField('Contenuto', validators=[DataRequired()])

    update_type = SelectField('Tipo', choices=[
        ('progress', 'Aggiornamento Progresso'),
        ('milestone', 'Milestone Completata'),
        ('blocker', 'Problema/Blocco'),
        ('completion', 'Completamento'),
        ('status_change', 'Cambio Stato')
    ], default='progress')

    is_public = BooleanField('Visibile a tutti')


class TeamMemberForm(FlaskForm):
    """Form per aggiungere membri al team."""

    user_id = SelectField('Membro', coerce=int, validators=[DataRequired()])
    role = StringField('Ruolo', default='Developer')
    allocation_percentage = IntegerField(
        'Allocazione (%)',
        default=100,
        validators=[NumberRange(min=10, max=100)]
    )


class ProjectFilterForm(FlaskForm):
    """Form per filtri nella dashboard."""

    status = SelectField('Stato', choices=[
        ('', 'Tutti gli stati'),
        ('planning', 'Pianificazione'),
        ('in_progress', 'In Sviluppo'),
        ('testing', 'Testing'),
        ('review', 'Review'),
        ('completed', 'Completato'),
        ('on_hold', 'In Pausa'),
        ('cancelled', 'Cancellato')
    ])

    priority = SelectField('Priorità', choices=[
        ('', 'Tutte le priorità'),
        ('critical', '🔴 Critica'),
        ('high', '🟠 Alta'),
        ('medium', '🟡 Media'),
        ('low', '🟢 Bassa')
    ])

    project_type = SelectField('Tipologia', choices=[
        ('', 'Tutte le tipologie'),
        ('feature', 'Nuova Funzionalità'),
        ('improvement', 'Miglioramento'),
        ('bugfix', 'Correzione Bug'),
        ('infrastructure', 'Infrastruttura'),
        ('integration', 'Integrazione'),
        ('optimization', 'Ottimizzazione'),
        ('migration', 'Migrazione')
    ])

    department_id = SelectField('Dipartimento', coerce=int)
    show_completed = BooleanField('Mostra completati')
    show_cancelled = BooleanField('Mostra cancellati')