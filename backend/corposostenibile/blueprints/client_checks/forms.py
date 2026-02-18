"""
Forms per il sistema Client Checks
==================================

Flask-WTF forms per la gestione dei form di controllo clienti.
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField, TextAreaField, SelectField, BooleanField,
    IntegerField, HiddenField, FieldList, FormField, DateField,
    SelectMultipleField, RadioField, FloatField
)
from wtforms.validators import DataRequired, Optional, Length, NumberRange, ValidationError
from datetime import date, timedelta

from corposostenibile.models import (
    User, Cliente,
    CheckFormStatusEnum, CheckFormFieldTypeEnum, AssignmentStatusEnum
)


class CheckFormFieldForm(FlaskForm):
    """Sub-form per i campi di un form di controllo."""
    
    field_name = StringField(
        'Nome Campo',
        validators=[
            DataRequired(message='Il nome del campo è obbligatorio'),
            Length(min=2, max=100, message='Il nome deve essere tra 2 e 100 caratteri')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': 'Es: Verifica documenti'
        }
    )
    
    field_type = SelectField(
        'Tipo Campo',
        choices=[
            (CheckFormFieldTypeEnum.text.value, 'Testo'),
            (CheckFormFieldTypeEnum.textarea.value, 'Testo lungo'),
            (CheckFormFieldTypeEnum.select.value, 'Selezione singola'),
            (CheckFormFieldTypeEnum.multiselect.value, 'Selezione multipla'),
            (CheckFormFieldTypeEnum.checkbox.value, 'Checkbox'),
            (CheckFormFieldTypeEnum.radio.value, 'Radio button'),
            (CheckFormFieldTypeEnum.number.value, 'Numero'),
            (CheckFormFieldTypeEnum.date.value, 'Data'),
            (CheckFormFieldTypeEnum.file.value, 'File upload'),
            (CheckFormFieldTypeEnum.rating.value, 'Valutazione (1-5)'),
            (CheckFormFieldTypeEnum.yesno.value, 'Sì/No')
        ],
        validators=[DataRequired()],
        render_kw={'class': 'form-select'}
    )
    
    field_options = TextAreaField(
        'Opzioni (una per riga)',
        validators=[Optional()],
        render_kw={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Opzione 1\nOpzione 2\nOpzione 3'
        }
    )
    
    is_required = BooleanField(
        'Campo obbligatorio',
        default=False,
        render_kw={'class': 'form-check-input'}
    )
    
    help_text = TextAreaField(
        'Testo di aiuto',
        validators=[Optional(), Length(max=500)],
        render_kw={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Testo di aiuto per compilare il campo'
        }
    )
    
    order_index = IntegerField(
        'Ordine',
        default=0,
        validators=[NumberRange(min=0)],
        render_kw={'class': 'form-control'}
    )


class CheckFormForm(FlaskForm):
    """Form per creare/modificare un form di controllo."""
    
    title = StringField(
        'Titolo Form',
        validators=[
            DataRequired(message='Il titolo è obbligatorio'),
            Length(min=3, max=200, message='Il titolo deve essere tra 3 e 200 caratteri')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': 'Es: Controllo Documentazione Cliente'
        }
    )
    
    description = TextAreaField(
        'Descrizione',
        validators=[Optional(), Length(max=1000)],
        render_kw={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Descrizione dettagliata del form di controllo'
        }
    )
    
    category = StringField(
        'Categoria',
        validators=[Optional(), Length(max=100)],
        render_kw={
            'class': 'form-control',
            'placeholder': 'Es: Documentazione, Compliance, Qualità'
        }
    )
    
    status = SelectField(
        'Stato',
        choices=[
            (CheckFormStatusEnum.draft.value, 'Bozza'),
            (CheckFormStatusEnum.active.value, 'Attivo'),
            (CheckFormStatusEnum.inactive.value, 'Inattivo'),
            (CheckFormStatusEnum.archived.value, 'Archiviato')
        ],
        default=CheckFormStatusEnum.draft.value,
        validators=[DataRequired()],
        render_kw={'class': 'form-select'}
    )
    
    is_public = BooleanField(
        'Form pubblico',
        default=False,
        render_kw={'class': 'form-check-input'}
    )
    
    allow_multiple_submissions = BooleanField(
        'Consenti invii multipli',
        default=False,
        render_kw={'class': 'form-check-input'}
    )
    
    # Campi del form (gestiti dinamicamente via JavaScript)
    fields = FieldList(FormField(CheckFormFieldForm), min_entries=1)


class ClientCheckAssignmentForm(FlaskForm):
    """Form per assegnare un controllo a uno o più clienti."""
    
    check_form_id = SelectField(
        'Form di Controllo',
        coerce=int,
        validators=[DataRequired(message='Seleziona un form di controllo')],
        choices=[],  # Popolato dinamicamente
        render_kw={'class': 'form-select'}
    )
    
    client_ids = SelectMultipleField(
        'Clienti',
        coerce=int,
        validators=[DataRequired(message='Seleziona almeno un cliente')],
        choices=[],  # Popolato dinamicamente
        render_kw={'class': 'form-select', 'multiple': True}
    )
    
    assigned_by_id = HiddenField('Assegnato da')
    
    due_date = DateField(
        'Scadenza',
        validators=[Optional()],
        render_kw={'class': 'form-control'}
    )
    
    priority = SelectField(
        'Priorità',
        choices=[
            ('low', '🟢 Bassa'),
            ('medium', '🟡 Media'),
            ('high', '🟠 Alta'),
            ('urgent', '🔴 Urgente')
        ],
        default='medium',
        validators=[DataRequired()],
        render_kw={'class': 'form-select'}
    )
    
    notes = TextAreaField(
        'Note per il cliente',
        validators=[Optional(), Length(max=1000)],
        render_kw={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Note aggiuntive per il cliente'
        }
    )
    
    send_notification = BooleanField(
        'Invia notifica email',
        default=True,
        render_kw={'class': 'form-check-input'}
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Popola le scelte per i form di controllo attivi
        from corposostenibile.models import CheckForm
        self.check_form_id.choices = [
            (form.id, form.name) 
            for form in CheckForm.query.filter_by(is_active=True).all()
        ]
        
        # Popola le scelte per i clienti
        self.client_ids.choices = [
            (client.cliente_id, f"{client.nome_cognome} ({client.mail or 'N/A'})")
            for client in Cliente.query.all()
        ]


class ClientCheckResponseForm(FlaskForm):
    """Form dinamico per la risposta del cliente."""
    
    assignment_id = HiddenField('Assignment ID', validators=[DataRequired()])
    
    def __init__(self, assignment, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Aggiungi dinamicamente i campi basati sul form di controllo
        for field in assignment.check_form.fields:
            field_name = f"field_{field.id}"
            
            if field.field_type == CheckFormFieldTypeEnum.text:
                setattr(self, field_name, StringField(
                    field.field_name,
                    validators=[DataRequired() if field.is_required else Optional()],
                    render_kw={'class': 'form-control', 'placeholder': field.help_text or ''}
                ))
                
            elif field.field_type == CheckFormFieldTypeEnum.textarea:
                setattr(self, field_name, TextAreaField(
                    field.field_name,
                    validators=[DataRequired() if field.is_required else Optional()],
                    render_kw={'class': 'form-control', 'rows': 4, 'placeholder': field.help_text or ''}
                ))
                
            elif field.field_type == CheckFormFieldTypeEnum.select:
                choices = [(opt.strip(), opt.strip()) for opt in field.field_options.split('\n') if opt.strip()]
                setattr(self, field_name, SelectField(
                    field.field_name,
                    choices=[('', 'Seleziona...')] + choices,
                    validators=[DataRequired() if field.is_required else Optional()],
                    render_kw={'class': 'form-select'}
                ))
                
            elif field.field_type == CheckFormFieldTypeEnum.multiselect:
                choices = [(opt.strip(), opt.strip()) for opt in field.field_options.split('\n') if opt.strip()]
                setattr(self, field_name, SelectMultipleField(
                    field.field_name,
                    choices=choices,
                    validators=[DataRequired() if field.is_required else Optional()],
                    render_kw={'class': 'form-select', 'multiple': True}
                ))
                
            elif field.field_type == CheckFormFieldTypeEnum.checkbox:
                setattr(self, field_name, BooleanField(
                    field.field_name,
                    render_kw={'class': 'form-check-input'}
                ))
                
            elif field.field_type == CheckFormFieldTypeEnum.radio:
                choices = [(opt.strip(), opt.strip()) for opt in field.field_options.split('\n') if opt.strip()]
                setattr(self, field_name, RadioField(
                    field.field_name,
                    choices=choices,
                    validators=[DataRequired() if field.is_required else Optional()]
                ))
                
            elif field.field_type == CheckFormFieldTypeEnum.number:
                setattr(self, field_name, IntegerField(
                    field.field_name,
                    validators=[DataRequired() if field.is_required else Optional()],
                    render_kw={'class': 'form-control'}
                ))
                
            elif field.field_type == CheckFormFieldTypeEnum.date:
                setattr(self, field_name, DateField(
                    field.field_name,
                    validators=[DataRequired() if field.is_required else Optional()],
                    render_kw={'class': 'form-control'}
                ))
                
            elif field.field_type == CheckFormFieldTypeEnum.rating:
                setattr(self, field_name, SelectField(
                    field.field_name,
                    choices=[('', 'Seleziona...')] + [(str(i), f"{i} stelle") for i in range(1, 6)],
                    validators=[DataRequired() if field.is_required else Optional()],
                    render_kw={'class': 'form-select'}
                ))
                
            elif field.field_type == CheckFormFieldTypeEnum.yesno:
                setattr(self, field_name, RadioField(
                    field.field_name,
                    choices=[('yes', 'Sì'), ('no', 'No')],
                    validators=[DataRequired() if field.is_required else Optional()]
                ))


class AssignmentFilterForm(FlaskForm):
    """Form per filtrare le assegnazioni."""
    
    status = SelectField(
        'Stato',
        choices=[('', 'Tutti')] + [
            (status.value, status.value.replace('_', ' ').title())
            for status in AssignmentStatusEnum
        ],
        default='',
        render_kw={'class': 'form-select'}
    )
    
    priority = SelectField(
        'Priorità',
        choices=[
            ('', 'Tutte'),
            ('low', '🟢 Bassa'),
            ('medium', '🟡 Media'),
            ('high', '🟠 Alta'),
            ('urgent', '🔴 Urgente')
        ],
        default='',
        render_kw={'class': 'form-select'}
    )
    
    client_id = SelectField(
        'Cliente',
        coerce=lambda x: int(x) if x and x != '' else None,
        choices=[],  # Popolato dinamicamente
        render_kw={'class': 'form-select'}
    )
    
    check_form_id = SelectField(
        'Form di Controllo',
        coerce=lambda x: int(x) if x and x != '' else None,
        choices=[],  # Popolato dinamicamente
        render_kw={'class': 'form-select'}
    )
    
    date_from = DateField(
        'Da Data',
        validators=[Optional()],
        render_kw={'class': 'form-control'}
    )
    
    date_to = DateField(
        'A Data',
        validators=[Optional()],
        render_kw={'class': 'form-control'}
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Popola le scelte per i clienti
        self.client_id.choices = [('', 'Tutti i clienti')] + [
            (client.cliente_id, f"{client.nome_cognome}")
            for client in Cliente.query.all()
        ]
        
        # Popola le scelte per i form di controllo
        from corposostenibile.models import CheckForm
        self.check_form_id.choices = [('', 'Tutti i form')] + [
            (form.id, form.title)
            for form in CheckForm.query.all()
        ]


class BulkAssignmentForm(FlaskForm):
    """Form per assegnazioni multiple."""
    
    check_form_id = SelectField(
        'Form di Controllo',
        coerce=int,
        validators=[DataRequired(message='Seleziona un form di controllo')],
        choices=[],  # Popolato dinamicamente
        render_kw={'class': 'form-select'}
    )
    
    client_filter = SelectField(
        'Filtro Clienti',
        choices=[
            ('all', 'Tutti i clienti attivi'),
            ('department', 'Per dipartimento'),
            ('category', 'Per categoria'),
            ('custom', 'Selezione personalizzata')
        ],
        default='all',
        validators=[DataRequired()],
        render_kw={'class': 'form-select'}
    )
    
    department_id = SelectField(
        'Dipartimento',
        coerce=lambda x: int(x) if x and x != '' else None,
        choices=[],  # Popolato dinamicamente
        render_kw={'class': 'form-select'}
    )
    
    category = StringField(
        'Categoria Cliente',
        validators=[Optional()],
        render_kw={'class': 'form-control'}
    )
    
    selected_clients = SelectMultipleField(
        'Clienti Selezionati',
        coerce=int,
        choices=[],  # Popolato dinamicamente
        render_kw={'class': 'form-select', 'multiple': True}
    )
    
    due_date = DateField(
        'Scadenza',
        validators=[Optional()],
        default=lambda: date.today() + timedelta(days=7),
        render_kw={'class': 'form-control'}
    )
    
    priority = SelectField(
        'Priorità',
        choices=[
            ('low', '🟢 Bassa'),
            ('medium', '🟡 Media'),
            ('high', '🟠 Alta'),
            ('urgent', '🔴 Urgente')
        ],
        default='medium',
        validators=[DataRequired()],
        render_kw={'class': 'form-select'}
    )
    
    notes = TextAreaField(
        'Note',
        validators=[Optional(), Length(max=1000)],
        render_kw={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Note per tutti i clienti selezionati'
        }
    )
    
    send_notification = BooleanField(
        'Invia notifiche email',
        default=True,
        render_kw={'class': 'form-check-input'}
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Popola le scelte per i form di controllo attivi
        from corposostenibile.models import CheckForm, Department
        
        self.check_form_id.choices = [
            (form.id, form.title) 
            for form in CheckForm.query.filter_by(status=CheckFormStatusEnum.active).all()
        ]
        
        # Popola le scelte per i dipartimenti
        self.department_id.choices = [('', 'Seleziona dipartimento')] + [
            (dept.id, dept.name)
            for dept in Department.query.filter_by(is_active=True).all()
        ]
        
        # Popola le scelte per i clienti
        self.selected_clients.choices = [
            (client.cliente_id, f"{client.nome_cognome} ({client.mail or 'N/A'})")
            for client in Cliente.query.all()
        ]


class DynamicCheckForm(FlaskForm):
    """
    Classe per generare dinamicamente form di controllo basati sui campi definiti nel CheckForm
    """
    
    @classmethod
    def create_form_class(cls, form_fields):
        """
        Crea dinamicamente una classe form basata sui campi forniti
        
        Args:
            form_fields: Lista di oggetti CheckFormField
            
        Returns:
            Classe FlaskForm generata dinamicamente
        """
        from wtforms import (
            StringField, TextAreaField, SelectField, BooleanField,
            IntegerField, RadioField, FileField, DateField
        )
        from wtforms.validators import DataRequired, Optional, NumberRange
        
        # Dizionario per mappare i tipi di campo
        field_type_mapping = {
            'text': StringField,
            'textarea': TextAreaField,
            'select': SelectField,
            'multiselect': SelectField,  # Con multiple=True nelle opzioni
            'checkbox': BooleanField,
            'radio': RadioField,
            'number': IntegerField,
            'date': DateField,
            'file': FileField,
            'rating': SelectField,
            'scale': SelectField,
            'yesno': RadioField
        }
        
        # Attributi della classe dinamica
        class_attrs = {}
        
        # Genera i campi dinamicamente
        for field in form_fields:
            field_name = f"field_{field.id}"
            field_type = field.field_type.value if hasattr(field.field_type, 'value') else field.field_type
            
            # Determina i validatori
            validators = []
            if field.is_required:
                validators.append(DataRequired(message=f'{field.label} è obbligatorio'))
            else:
                validators.append(Optional())
            
            # Opzioni di rendering
            render_kw = {'class': 'form-control'}
            
            # Crea il campo in base al tipo
            if field_type == 'text':
                class_attrs[field_name] = StringField(
                    field.label,
                    validators=validators,
                    render_kw=render_kw,
                    description=field.help_text
                )
                
            elif field_type == 'textarea':
                render_kw.update({'rows': 4})
                class_attrs[field_name] = TextAreaField(
                    field.label,
                    validators=validators,
                    render_kw=render_kw,
                    description=field.help_text
                )
                
            elif field_type in ['select', 'multiselect']:
                choices = []
                if field.options:
                    # field.options puo' essere dict JSONB, lista o stringa
                    if isinstance(field.options, dict):
                        raw_choices = field.options.get('choices', [])
                        choices = [(str(opt).strip(), str(opt).strip()) for opt in raw_choices if str(opt).strip()]
                    if isinstance(field.options, list):
                        choices = [(str(opt).strip(), str(opt).strip()) for opt in field.options if str(opt).strip()]
                    elif isinstance(field.options, str):
                        choices = [(opt.strip(), opt.strip()) for opt in field.options.split('\n') if opt.strip()]
                
                render_kw = {'class': 'form-select'}
                if field_type == 'multiselect':
                    render_kw['multiple'] = True
                    
                class_attrs[field_name] = SelectField(
                    field.label,
                    choices=choices,
                    validators=validators,
                    render_kw=render_kw,
                    description=field.help_text
                )
                
            elif field_type == 'checkbox':
                class_attrs[field_name] = BooleanField(
                    field.label,
                    render_kw={'class': 'form-check-input'},
                    description=field.help_text
                )
                
            elif field_type == 'radio':
                choices = []
                if field.options:
                    # field.options puo' essere dict JSONB, lista o stringa
                    if isinstance(field.options, dict):
                        raw_choices = field.options.get('choices', [])
                        choices = [(str(opt).strip(), str(opt).strip()) for opt in raw_choices if str(opt).strip()]
                    if isinstance(field.options, list):
                        choices = [(str(opt).strip(), str(opt).strip()) for opt in field.options if str(opt).strip()]
                    elif isinstance(field.options, str):
                        choices = [(opt.strip(), opt.strip()) for opt in field.options.split('\n') if opt.strip()]
                    
                class_attrs[field_name] = RadioField(
                    field.label,
                    choices=choices,
                    validators=validators,
                    render_kw={'class': 'form-check-input'},
                    description=field.help_text
                )
                
            elif field_type == 'number':
                validators.append(NumberRange(min=0))
                class_attrs[field_name] = IntegerField(
                    field.label,
                    validators=validators,
                    render_kw=render_kw,
                    description=field.help_text
                )
                
            elif field_type == 'date':
                render_kw = {'class': 'form-control', 'type': 'date'}
                class_attrs[field_name] = DateField(
                    field.label,
                    validators=validators,
                    render_kw=render_kw,
                    description=field.help_text
                )
                
            elif field_type == 'file':
                class_attrs[field_name] = FileField(
                    field.label,
                    validators=validators,
                    render_kw={'class': 'form-control'},
                    description=field.help_text
                )
                
            elif field_type == 'rating':
                choices = [(str(i), str(i)) for i in range(1, 6)]
                class_attrs[field_name] = SelectField(
                    field.label,
                    choices=choices,
                    validators=validators,
                    render_kw={'class': 'form-select'},
                    description=field.help_text
                )

            elif field_type == 'scale':
                min_value = 1
                max_value = 5
                if isinstance(field.options, dict):
                    min_value = int(field.options.get('min', min_value))
                    max_value = int(field.options.get('max', max_value))
                choices = [(str(i), str(i)) for i in range(min_value, max_value + 1)]
                class_attrs[field_name] = SelectField(
                    field.label,
                    choices=choices,
                    validators=validators,
                    render_kw={'class': 'form-select'},
                    description=field.help_text
                )
                
            elif field_type == 'yesno':
                choices = [('si', 'Sì'), ('no', 'No')]
                class_attrs[field_name] = RadioField(
                    field.label,
                    choices=choices,
                    validators=validators,
                    render_kw={'class': 'form-check-input'},
                    description=field.help_text
                )
        
        # Crea e restituisci la classe dinamica
        return type('DynamicCheckForm', (FlaskForm,), class_attrs)


class WeeklyCheckForm(FlaskForm):
    """
    Form per il Check Settimanale 2.0 - "Check Normale"

    Questo form sostituisce i vecchi TypeForm con un sistema integrato
    che include 29 campi: 3 foto, 13 campi testo, 7 rating 0-10,
    3 rating professionisti 1-10 con feedback, peso, progresso e referral.
    """

    class Meta:
        csrf = False  # Disabilita CSRF - form pubblico compilato da clienti non autenticati

    # ─── FOTO FISICO (3 campi) ──────────────────────────────────────────────
    photo_front = FileField(
        'Foto Fisico Frontale',
        validators=[
            Optional(),
            FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'heic'], 'Solo immagini (JPG, PNG, GIF, HEIC)!')
        ],
        render_kw={
            'class': 'form-control',
            'accept': 'image/*'
        }
    )

    photo_side = FileField(
        'Foto Fisico Laterale',
        validators=[
            Optional(),
            FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'heic'], 'Solo immagini (JPG, PNG, GIF, HEIC)!')
        ],
        render_kw={
            'class': 'form-control',
            'accept': 'image/*'
        }
    )

    photo_back = FileField(
        'Foto Fisico Posteriore',
        validators=[
            Optional(),
            FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'heic'], 'Solo immagini (JPG, PNG, GIF, HEIC)!')
        ],
        render_kw={
            'class': 'form-control',
            'accept': 'image/*'
        }
    )

    # ─── RIFLESSIONI SETTIMANALI (5 campi) ─────────────────────────────────
    what_worked = TextAreaField(
        'Cosa ha funzionato bene per te la settimana scorsa?',
        validators=[Optional(), Length(max=2000)],
        render_kw={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Descrivi cosa ha funzionato bene nel tuo percorso questa settimana...'
        }
    )

    what_didnt_work = TextAreaField(
        'Cosa NON ha funzionato bene per te la settimana scorsa?',
        validators=[Optional(), Length(max=2000)],
        render_kw={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Descrivi eventuali difficoltà o aspetti che non hanno funzionato...'
        }
    )

    what_learned = TextAreaField(
        'Cosa hai imparato questa settimana?',
        validators=[Optional(), Length(max=2000)],
        render_kw={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Condividi i tuoi apprendimenti e insight della settimana...'
        }
    )

    what_focus_next = TextAreaField(
        'Su cosa vogliamo focalizzarci la prossima settimana?',
        validators=[Optional(), Length(max=2000)],
        render_kw={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Obiettivi e focus per la settimana successiva...'
        }
    )

    injuries_notes = TextAreaField(
        'Hai avuto infortuni o ci sono note importanti da segnalare?',
        validators=[Optional(), Length(max=2000)],
        render_kw={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Eventuali infortuni, dolori o note importanti...'
        }
    )

    # ─── VALUTAZIONI BENESSERE (7 campi, scala 0-10) ───────────────────────
    digestion_rating = IntegerField(
        'Valuta la tua digestione questa settimana (0-10)',
        validators=[Optional(), NumberRange(min=0, max=10, message='Inserisci un valore tra 0 e 10')],
        render_kw={
            'class': 'form-control',
            'type': 'number',
            'min': '0',
            'max': '10',
            'placeholder': '0-10'
        }
    )

    energy_rating = IntegerField(
        'Valuta la tua energia questa settimana (0-10)',
        validators=[Optional(), NumberRange(min=0, max=10, message='Inserisci un valore tra 0 e 10')],
        render_kw={
            'class': 'form-control',
            'type': 'number',
            'min': '0',
            'max': '10',
            'placeholder': '0-10'
        }
    )

    strength_rating = IntegerField(
        'Valuta la tua forza questa settimana (0-10)',
        validators=[Optional(), NumberRange(min=0, max=10, message='Inserisci un valore tra 0 e 10')],
        render_kw={
            'class': 'form-control',
            'type': 'number',
            'min': '0',
            'max': '10',
            'placeholder': '0-10'
        }
    )

    hunger_rating = IntegerField(
        'Valuta il tuo senso di fame questa settimana (0-10)',
        validators=[Optional(), NumberRange(min=0, max=10, message='Inserisci un valore tra 0 e 10')],
        render_kw={
            'class': 'form-control',
            'type': 'number',
            'min': '0',
            'max': '10',
            'placeholder': '0-10'
        }
    )

    sleep_rating = IntegerField(
        'Valuta la qualità del tuo sonno questa settimana (0-10)',
        validators=[Optional(), NumberRange(min=0, max=10, message='Inserisci un valore tra 0 e 10')],
        render_kw={
            'class': 'form-control',
            'type': 'number',
            'min': '0',
            'max': '10',
            'placeholder': '0-10'
        }
    )

    mood_rating = IntegerField(
        'Valuta il tuo umore questa settimana (0-10)',
        validators=[Optional(), NumberRange(min=0, max=10, message='Inserisci un valore tra 0 e 10')],
        render_kw={
            'class': 'form-control',
            'type': 'number',
            'min': '0',
            'max': '10',
            'placeholder': '0-10'
        }
    )

    motivation_rating = IntegerField(
        'Valuta la tua motivazione questa settimana (0-10)',
        validators=[Optional(), NumberRange(min=0, max=10, message='Inserisci un valore tra 0 e 10')],
        render_kw={
            'class': 'form-control',
            'type': 'number',
            'min': '0',
            'max': '10',
            'placeholder': '0-10'
        }
    )

    # ─── PESO ────────────────────────────────────────────────────────────────
    weight = FloatField(
        'Peso (Kg)',
        validators=[Optional(), NumberRange(min=20, max=300, message='Inserisci un peso valido (20-300 Kg)')],
        render_kw={
            'class': 'form-control',
            'type': 'number',
            'step': '0.1',
            'min': '20',
            'max': '300',
            'placeholder': 'Es: 75.5'
        }
    )

    # ─── ADERENZA AI PROGRAMMI (7 campi) ───────────────────────────────────
    nutrition_program_adherence = TextAreaField(
        'Hai rispettato il programma alimentare che ti è stato assegnato?',
        validators=[Optional(), Length(max=2000)],
        render_kw={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Descrivi come hai seguito il programma alimentare...'
        }
    )

    training_program_adherence = TextAreaField(
        'Hai rispettato il programma sportivo che ti è stato assegnato?',
        validators=[Optional(), Length(max=2000)],
        render_kw={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Descrivi come hai seguito il programma sportivo...'
        }
    )

    exercise_modifications = TextAreaField(
        'Ci sono esercizi che non hai fatto o che hai aggiunto?',
        validators=[Optional(), Length(max=2000)],
        render_kw={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Eventuali modifiche agli esercizi...'
        }
    )

    daily_steps = TextAreaField(
        'Quanti passi hai fatto in media al giorno?',
        validators=[Optional(), Length(max=500)],
        render_kw={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Es: 8000-10000 passi al giorno'
        }
    )

    completed_training_weeks = TextAreaField(
        'Quante settimane di allenamento hai rispettato al 100%?',
        validators=[Optional(), Length(max=500)],
        render_kw={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Numero di settimane complete...'
        }
    )

    planned_training_days = TextAreaField(
        'Quanti giorni di allenamento avevi pianificato?',
        validators=[Optional(), Length(max=500)],
        render_kw={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Giorni pianificati per l\'allenamento...'
        }
    )

    live_session_topics = TextAreaField(
        'Di cosa vorresti parlare durante le prossime LIVE settimanali di gruppo?',
        validators=[Optional(), Length(max=2000)],
        render_kw={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Tematiche che vorresti approfondire nelle sessioni live...'
        }
    )

    # ─── VALUTAZIONI PROFESSIONISTI (3 set: rating 1-10 + feedback) ────────
    nutritionist_rating = IntegerField(
        'Come valuteresti il tuo nutrizionista? (1-10)',
        validators=[Optional(), NumberRange(min=1, max=10, message='Inserisci un valore tra 1 e 10')],
        render_kw={
            'class': 'form-control',
            'type': 'number',
            'min': '1',
            'max': '10',
            'placeholder': '1-10'
        }
    )

    nutritionist_feedback = TextAreaField(
        'Spiega la tua valutazione del nutrizionista',
        validators=[Optional(), Length(max=2000)],
        render_kw={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Cosa ti è piaciuto? Cosa potrebbe essere migliorato?'
        }
    )

    psychologist_rating = IntegerField(
        'Come valuteresti la tua psicologa? (1-10)',
        validators=[Optional(), NumberRange(min=1, max=10, message='Inserisci un valore tra 1 e 10')],
        render_kw={
            'class': 'form-control',
            'type': 'number',
            'min': '1',
            'max': '10',
            'placeholder': '1-10'
        }
    )

    psychologist_feedback = TextAreaField(
        'Spiega la tua valutazione della psicologa',
        validators=[Optional(), Length(max=2000)],
        render_kw={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Cosa ti è piaciuto? Cosa potrebbe essere migliorato?'
        }
    )

    coach_rating = IntegerField(
        'Come valuteresti il tuo coach? (1-10)',
        validators=[Optional(), NumberRange(min=1, max=10, message='Inserisci un valore tra 1 e 10')],
        render_kw={
            'class': 'form-control',
            'type': 'number',
            'min': '1',
            'max': '10',
            'placeholder': '1-10'
        }
    )

    coach_feedback = TextAreaField(
        'Spiega la tua valutazione del coach',
        validators=[Optional(), Length(max=2000)],
        render_kw={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Cosa ti è piaciuto? Cosa potrebbe essere migliorato?'
        }
    )

    # ─── PROGRESSO E REFERRAL ───────────────────────────────────────────────
    progress_rating = IntegerField(
        'Come valuteresti il tuo percorso complessivo? (1-10)',
        validators=[Optional(), NumberRange(min=1, max=10, message='Inserisci un valore tra 1 e 10')],
        render_kw={
            'class': 'form-control',
            'type': 'number',
            'min': '1',
            'max': '10',
            'placeholder': '1-10'
        }
    )

    referral = TextAreaField(
        'Conosci qualcuno che potrebbe essere interessato al nostro programma?',
        validators=[Optional(), Length(max=1000)],
        render_kw={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Nome, telefono ed email della persona da contattare...'
        }
    )

    # ─── COMMENTI EXTRA ──────────────────────────────────────────────────────
    extra_comments = TextAreaField(
        'Commenti o note aggiuntive',
        validators=[Optional(), Length(max=2000)],
        render_kw={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Eventuali commenti aggiuntivi che vuoi condividere...'
        }
    )


class DCACheckForm(FlaskForm):
    """
    Form per il Check DCA (Disturbi del Comportamento Alimentare)

    Check specializzato con 32 domande focalizzate su aspetti psicologici.
    NON include foto né valutazioni professionisti.
    Le scale sono 1-5 per aspetti psicologici e 1-10 per parametri fisici.
    """

    # ─── BENESSERE EMOTIVO (Scala 1-5) ─────────────────────────────────────
    mood_balance_rating = IntegerField(
        'Come valuto il mio stato d\'animo a livello di umore, energia e equilibrio generale?',
        validators=[Optional(), NumberRange(min=1, max=5)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '5'}
    )

    food_plan_serenity = IntegerField(
        'Quanto mi sono sentito/a sereno/a nel seguire il piano alimentare?',
        validators=[Optional(), NumberRange(min=1, max=5)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '5'}
    )

    food_weight_worry = IntegerField(
        'Quanta preoccupazione ho avuto in merito a cibo, peso e corpo?',
        validators=[Optional(), NumberRange(min=1, max=5)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '5'}
    )

    emotional_eating = IntegerField(
        'Quanto credo di aver mangiato in risposta ad emozioni (es. noia, ansia, stress) piuttosto che fame fisica?',
        validators=[Optional(), NumberRange(min=1, max=5)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '5'}
    )

    body_comfort = IntegerField(
        'Quanto mi sono sentito/a a mio agio nel mio corpo senza averci posto un\'attenzione eccessiva?',
        validators=[Optional(), NumberRange(min=1, max=5)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '5'}
    )

    body_respect = IntegerField(
        'Quanto sono riuscito/a a trattare il mio corpo con rispetto a prescindere dai risultati?',
        validators=[Optional(), NumberRange(min=1, max=5)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '5'}
    )

    # ─── ALLENAMENTO (Scala 1-5) ────────────────────────────────────────────
    exercise_wellness = IntegerField(
        'Quanto sono riuscito/a a gestire l\'allenamento come una fonte di benessere, ascoltando anche i segnali del mio corpo per adattarmi al meglio?',
        validators=[Optional(), NumberRange(min=1, max=5)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '5'}
    )

    exercise_guilt = IntegerField(
        'Quanto mi sono sentito/a in colpa qualora fosse capitato di saltare un allenamento?',
        validators=[Optional(), NumberRange(min=1, max=5)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '5'}
    )

    # ─── RIPOSO E RELAZIONI (Scala 1-5) ────────────────────────────────────
    sleep_satisfaction = IntegerField(
        'Quanto ho dormito in maniera soddisfacente svegliandomi ben riposato/a?',
        validators=[Optional(), NumberRange(min=1, max=5)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '5'}
    )

    relationship_time = IntegerField(
        'Come sono riuscita/o a dedicare tempo a relazioni significative?',
        validators=[Optional(), NumberRange(min=1, max=5)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '5'}
    )

    personal_time = IntegerField(
        'Quanto tempo ho avuto per me stesso in cui mi sono dedicato/a ad attività piacevoli?',
        validators=[Optional(), NumberRange(min=1, max=5)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '5'}
    )

    # ─── INTERFERENZE E GESTIONE (Scala 1-5) ───────────────────────────────
    life_interference = IntegerField(
        'Quanto il mio percorso ha interferito con il lavoro o la vita sociale?',
        validators=[Optional(), NumberRange(min=1, max=5)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '5'}
    )

    unexpected_management = IntegerField(
        'Quanto bene ho gestito eventuali imprevisti senza sentirmi in colpa?',
        validators=[Optional(), NumberRange(min=1, max=5)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '5'}
    )

    self_compassion = IntegerField(
        'Quanto sono riuscito ad essere comprensivo con me stesso/a nei momenti difficili?',
        validators=[Optional(), NumberRange(min=1, max=5)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '5'}
    )

    inner_dialogue = IntegerField(
        'Quanto penso che il mio dialogo interiore sia stato gentile e non giudicante?',
        validators=[Optional(), NumberRange(min=1, max=5)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '5'}
    )

    # ─── SOSTENIBILITÀ (Scala 1-5) ─────────────────────────────────────────
    long_term_sustainability = IntegerField(
        'Quanto ritengo che questo percorso sia sostenibile nel lungo termine?',
        validators=[Optional(), NumberRange(min=1, max=5)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '5'}
    )

    values_alignment = IntegerField(
        'Quanto sento che questo percorso sia in linea con i miei valori e i miei obiettivi?',
        validators=[Optional(), NumberRange(min=1, max=5)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '5'}
    )

    motivation_level = IntegerField(
        'Quanta motivazione sento nel proseguire, anche se con eventuali adattamenti?',
        validators=[Optional(), NumberRange(min=1, max=5)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '5'}
    )

    # ─── ORGANIZZAZIONE PASTI (Scala 1-5) ──────────────────────────────────
    meal_organization = IntegerField(
        'Quanto positiva credo sia stata la mia organizzazione dei pasti?',
        validators=[Optional(), NumberRange(min=1, max=5)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '5'}
    )

    meal_stress = IntegerField(
        'Quanto credo che la gestione dei pasti (es. cucinare, pianificare) sia stata fonte di stress?',
        validators=[Optional(), NumberRange(min=1, max=5)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '5'}
    )

    shopping_awareness = IntegerField(
        'Quanto credo di essere riuscito/a a fare la spesa in maniera consapevole, evitando acquisti impulsivi o restrittivi?',
        validators=[Optional(), NumberRange(min=1, max=5)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '5'}
    )

    shopping_impact = IntegerField(
        'La spesa alimentare ha influito sul mio tempo o budget in modo problematico?',
        validators=[Optional(), NumberRange(min=1, max=5)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '5'}
    )

    meal_clarity = IntegerField(
        'Quanto mi è stato chiaro cosa cucinare e come strutturare i pasti durante la giornata?',
        validators=[Optional(), NumberRange(min=1, max=5)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '5'}
    )

    # ─── PARAMETRI FISICI (Scala 1-10) ─────────────────────────────────────
    digestion_rating = IntegerField(
        'Valuta la tua digestione in questo periodo',
        validators=[Optional(), NumberRange(min=1, max=10)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '10'}
    )

    energy_rating = IntegerField(
        'Valuta i tuoi livelli di energia in questo periodo',
        validators=[Optional(), NumberRange(min=1, max=10)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '10'}
    )

    strength_rating = IntegerField(
        'Valuta il tuo livello di forza in questo periodo',
        validators=[Optional(), NumberRange(min=1, max=10)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '10'}
    )

    hunger_rating = IntegerField(
        'Valuta il tuo livello di fame in questo periodo',
        validators=[Optional(), NumberRange(min=1, max=10)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '10'}
    )

    sleep_rating = IntegerField(
        'Valuta la tua qualità del sonno',
        validators=[Optional(), NumberRange(min=1, max=10)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '10'}
    )

    mood_rating = IntegerField(
        'Valuta il tuo umore in questo periodo',
        validators=[Optional(), NumberRange(min=1, max=10)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '10'}
    )

    motivation_rating = IntegerField(
        'Valuta la tua motivazione in questo periodo',
        validators=[Optional(), NumberRange(min=1, max=10)],
        render_kw={'class': 'form-control', 'type': 'number', 'min': '1', 'max': '10'}
    )

    # ─── REFERRAL E COMMENTI ───────────────────────────────────────────────
    referral = TextAreaField(
        'Chi è la persona a cui vuoi bene e che sai che noi di CorpoSostenibile possiamo aiutare?',
        validators=[Optional(), Length(max=1000)],
        render_kw={'class': 'form-control', 'rows': 3}
    )

    extra_comments = TextAreaField(
        'Commenti extra',
        validators=[Optional(), Length(max=2000)],
        render_kw={'class': 'form-control', 'rows': 4}
    )
