"""
calendar.forms
==============

Form per la gestione dei meeting e eventi Google Calendar.
"""

from datetime import datetime, date
from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, DateTimeField, SelectField, 
    SubmitField, URLField, HiddenField
)
from wtforms.validators import DataRequired, Optional, Length, URL
from wtforms.widgets import TextArea


class MeetingForm(FlaskForm):
    """Form per creare/modificare un meeting."""
    
    title = StringField(
        'Titolo Meeting',
        validators=[DataRequired(), Length(max=255)],
        render_kw={'placeholder': 'Es: Call con cliente - Follow-up'}
    )
    
    description = TextAreaField(
        'Descrizione',
        validators=[Optional(), Length(max=1000)],
        render_kw={'rows': 3, 'placeholder': 'Descrizione del meeting...'}
    )
    
    start_time = DateTimeField(
        'Data e Ora Inizio',
        validators=[DataRequired()],
        format='%Y-%m-%dT%H:%M',
        render_kw={'type': 'datetime-local'}
    )
    
    end_time = DateTimeField(
        'Data e Ora Fine',
        validators=[DataRequired()],
        format='%Y-%m-%dT%H:%M',
        render_kw={'type': 'datetime-local'}
    )
    
    meeting_type = SelectField(
        'Tipo Meeting',
        choices=[
            ('call', 'Telefonata'),
            ('video_call', 'Video Call'),
            ('in_person', 'In Persona'),
            ('other', 'Altro')
        ],
        default='video_call'
    )
    
    cliente_id = HiddenField('Cliente ID')
    
    submit = SubmitField('Salva Meeting')


class MeetingDetailsForm(FlaskForm):
    """Form per aggiornare i dettagli di un meeting (esito, note, Loom)."""
    
    meeting_outcome = TextAreaField(
        'Esito della Call',
        validators=[Optional(), Length(max=2000)],
        render_kw={
            'rows': 4, 
            'placeholder': 'Descrivi l\'esito della call, i prossimi passi, decisioni prese...'
        }
    )
    
    meeting_notes = TextAreaField(
        'Note del Meeting',
        validators=[Optional(), Length(max=2000)],
        render_kw={
            'rows': 4,
            'placeholder': 'Note aggiuntive, osservazioni, follow-up...'
        }
    )
    
    loom_link = URLField(
        'Link Loom',
        validators=[Optional(), URL()],
        render_kw={'placeholder': 'https://loom.com/share/...'}
    )
    
    status = SelectField(
        'Stato Meeting',
        choices=[
            ('scheduled', 'Programmato'),
            ('completed', 'Completato'),
            ('cancelled', 'Cancellato'),
            ('no_show', 'Non Presente')
        ],
        default='scheduled'
    )
    
    submit = SubmitField('Aggiorna Dettagli')


class GoogleCalendarConnectForm(FlaskForm):
    """Form per la connessione a Google Calendar."""
    
    submit = SubmitField('Connetti Google Calendar', render_kw={'class': 'btn btn-primary'})