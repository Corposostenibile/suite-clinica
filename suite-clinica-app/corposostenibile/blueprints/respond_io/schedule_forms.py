"""
Forms per configurazione orari di lavoro e assegnazioni
"""

from flask_wtf import FlaskForm
from wtforms import (
    SelectField, SelectMultipleField, TimeField, BooleanField, 
    StringField, SubmitField, HiddenField,
    FieldList, FormField, TextAreaField
)
from wtforms.validators import DataRequired, Optional, Length
from datetime import time


class WorkScheduleEntryForm(FlaskForm):
    """Form per singolo orario di lavoro"""
    class Meta:
        csrf = False  # Disabilita CSRF per sub-form
    
    day_of_week = HiddenField('Giorno', validators=[DataRequired()])
    is_active = BooleanField('Attivo', default=True)
    start_time = TimeField('Inizio', format='%H:%M', validators=[Optional()])
    end_time = TimeField('Fine', format='%H:%M', validators=[Optional()])
    notes = StringField('Note', validators=[Optional(), Length(max=200)])


class UserWorkScheduleForm(FlaskForm):
    """Form per configurare gli orari settimanali di un utente"""
    
    user_id = HiddenField('User ID', validators=[DataRequired()])
    timezone = SelectField('Fuso Orario', 
                          choices=[
                              ('Europe/Rome', 'Italia (Roma)'),
                              ('Europe/London', 'UK (Londra)'),
                              ('Europe/Paris', 'Francia (Parigi)'),
                              ('Europe/Berlin', 'Germania (Berlino)'),
                              ('Europe/Madrid', 'Spagna (Madrid)'),
                              ('UTC', 'UTC')
                          ],
                          default='Europe/Rome',
                          validators=[DataRequired()])
    
    # Orari per ogni giorno della settimana
    monday = FormField(WorkScheduleEntryForm)
    tuesday = FormField(WorkScheduleEntryForm)
    wednesday = FormField(WorkScheduleEntryForm)
    thursday = FormField(WorkScheduleEntryForm)
    friday = FormField(WorkScheduleEntryForm)
    saturday = FormField(WorkScheduleEntryForm)
    sunday = FormField(WorkScheduleEntryForm)
    
    submit = SubmitField('Salva Orari')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Inizializza i giorni con i valori corretti
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for i, day_name in enumerate(days):
            day_field = getattr(self, day_name)
            day_field.day_of_week.data = str(i)
            
            # Imposta orari default per giorni lavorativi
            if i < 5:  # Lunedì-Venerdì
                if not day_field.start_time.data:
                    day_field.start_time.data = time(9, 0)
                if not day_field.end_time.data:
                    day_field.end_time.data = time(18, 0)
                day_field.is_active.data = True
            else:  # Weekend
                day_field.is_active.data = False


class BulkScheduleForm(FlaskForm):
    """Form per configurare orari di multipli utenti contemporaneamente"""
    
    apply_to_all = BooleanField('Applica a tutti gli utenti attivi')
    selected_users = SelectMultipleField('Oppure seleziona utenti specifici',
                                         choices=[],
                                         validators=[Optional()])
    
    # Template orario da applicare
    template_weekdays_start = TimeField('Orario Inizio (Lun-Ven)', 
                                       format='%H:%M',
                                       default=time(9, 0))
    template_weekdays_end = TimeField('Orario Fine (Lun-Ven)', 
                                     format='%H:%M',
                                     default=time(18, 0))
    
    enable_saturday = BooleanField('Abilita Sabato')
    template_saturday_start = TimeField('Orario Inizio (Sabato)', 
                                       format='%H:%M',
                                       default=time(9, 0))
    template_saturday_end = TimeField('Orario Fine (Sabato)', 
                                     format='%H:%M',
                                     default=time(13, 0))
    
    enable_sunday = BooleanField('Abilita Domenica')
    template_sunday_start = TimeField('Orario Inizio (Domenica)', 
                                     format='%H:%M',
                                     default=time(9, 0))
    template_sunday_end = TimeField('Orario Fine (Domenica)', 
                                   format='%H:%M',
                                   default=time(13, 0))
    
    timezone = SelectField('Fuso Orario',
                          choices=[
                              ('Europe/Rome', 'Italia (Roma)'),
                              ('Europe/London', 'UK (Londra)'),
                              ('Europe/Paris', 'Francia (Parigi)'),
                              ('Europe/Berlin', 'Germania (Berlino)'),
                              ('Europe/Madrid', 'Spagna (Madrid)'),
                              ('UTC', 'UTC')
                          ],
                          default='Europe/Rome')
    
    submit = SubmitField('Applica Template')


class AutoAssignmentForm(FlaskForm):
    """Form per eseguire assegnazione automatica"""
    
    # Modalità di filtro principale
    filter_mode = SelectField('Cosa assegnare',
                             choices=[
                                 ('waiting', 'Solo contatti in attesa di risposta (con tag "in_attesa")'),
                                 ('unassigned_waiting', 'Solo contatti non assegnati in attesa di risposta'),
                                 ('all', 'Tutti i contatti aperti nei lifecycle target')
                             ],
                             default='waiting',
                             validators=[DataRequired()])
    
    # Filtri opzionali per lifecycle (solo se serve personalizzare)
    include_lifecycles = SelectField('Lifecycle da includere',
                                    choices=[
                                        ('all', 'Tutti i lifecycle target'),
                                        ('custom', 'Personalizza')
                                    ],
                                    default='all')
    
    selected_lifecycles = SelectMultipleField('Seleziona Lifecycle',
                                              choices=[
                                                  ('Nuova Lead', 'Nuova Lead'),
                                                  ('Contrassegnato', 'Contrassegnato'),
                                                  ('In Target', 'In Target'),
                                                  ('Link Da Inviare', 'Link Da Inviare'),
                                                  ('Link Inviato', 'Link Inviato')
                                              ],
                                              validators=[Optional()])
    
    # Conferma
    confirm_assignment = BooleanField('Confermo di voler procedere con l\'assegnazione automatica',
                                     validators=[DataRequired()])
    
    notes = TextAreaField('Note (opzionale)', 
                         validators=[Optional(), Length(max=500)])
    
    preview = SubmitField('Anteprima')
    execute = SubmitField('Esegui Assegnazione')


class ScheduleFilterForm(FlaskForm):
    """Form per filtrare la visualizzazione degli orari"""
    
    show_active_only = BooleanField('Mostra solo utenti attivi')
    department = SelectField('Filtra per dipartimento',
                            choices=[('all', 'Tutti i dipartimenti')],
                            default='all')
    search = StringField('Cerca utente', validators=[Optional()])
    
    submit = SubmitField('Applica Filtri')