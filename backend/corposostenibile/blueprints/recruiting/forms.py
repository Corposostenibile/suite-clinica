"""
Form per il modulo Recruiting
"""

from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, SelectField, IntegerField, 
    BooleanField, FieldList, FormField, HiddenField, FloatField,
    SelectMultipleField, RadioField, DateField, FileField
)
from wtforms.validators import DataRequired, Optional, Length, NumberRange, Email, URL
from wtforms.widgets import TextArea
from corposostenibile.models import QuestionTypeEnum, Department


class JobQuestionForm(FlaskForm):
    """Form per singola domanda del questionario."""
    
    question_text = TextAreaField(
        "Testo domanda",
        validators=[DataRequired(), Length(min=5, max=500)],
        render_kw={"rows": 3}
    )
    
    question_type = SelectField(
        "Tipo domanda",
        choices=[
            (QuestionTypeEnum.short_text.value, "Testo breve"),
            (QuestionTypeEnum.long_text.value, "Testo lungo"),
            (QuestionTypeEnum.select.value, "Scelta singola"),
            (QuestionTypeEnum.multiselect.value, "Scelta multipla"),
            (QuestionTypeEnum.number.value, "Numero"),
            (QuestionTypeEnum.date.value, "Data"),
            (QuestionTypeEnum.file.value, "Upload file"),
            (QuestionTypeEnum.email.value, "Email"),
            (QuestionTypeEnum.phone.value, "Telefono"),
            (QuestionTypeEnum.url.value, "URL"),
            (QuestionTypeEnum.yesno.value, "Sì/No"),
        ],
        validators=[DataRequired()]
    )
    
    # Opzioni per select/multiselect/radio/checkbox
    options = TextAreaField(
        "Opzioni (una per riga)",
        validators=[Optional()],
        render_kw={"rows": 4, "placeholder": "Opzione 1\nOpzione 2\nOpzione 3"}
    )
    
    # Risposta attesa
    expected_answer = TextAreaField(
        "Risposta attesa",
        validators=[Optional()],
        render_kw={"rows": 2}
    )
    
    expected_min = FloatField(
        "Valore minimo atteso",
        validators=[Optional()]
    )
    
    expected_max = FloatField(
        "Valore massimo atteso",
        validators=[Optional()]
    )
    
    # Configurazione
    is_required = BooleanField("Obbligatoria", default=True)
    weight = FloatField(
        "Peso % (importanza)",
        validators=[NumberRange(min=0, max=100)],
        default=0
    )
    
    help_text = TextAreaField(
        "Testo di aiuto",
        validators=[Optional(), Length(max=500)],
        render_kw={"rows": 2}
    )
    
    placeholder = StringField(
        "Placeholder",
        validators=[Optional(), Length(max=255)]
    )
    
    # Validazione
    min_length = IntegerField(
        "Lunghezza minima",
        validators=[Optional()]
    )
    
    max_length = IntegerField(
        "Lunghezza massima",
        validators=[Optional()]
    )
    
    order = IntegerField(
        "Ordine",
        validators=[Optional()],
        default=0
    )


class JobOfferForm(FlaskForm):
    """Form per creazione/modifica offerta di lavoro."""
    
    # Informazioni base
    title = StringField(
        "Titolo posizione",
        validators=[DataRequired(), Length(min=5, max=255)]
    )
    
    description = TextAreaField(
        "Descrizione",
        validators=[DataRequired(), Length(min=50)],
        widget=TextArea(),
        render_kw={"rows": 8}
    )
    
    requirements = TextAreaField(
        "Requisiti",
        validators=[Optional()],
        render_kw={"rows": 6}
    )
    
    benefits = TextAreaField(
        "Benefit",
        validators=[Optional()],
        render_kw={"rows": 4}
    )
    
    salary_range = StringField(
        "Range salariale",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "es. 30k-45k EUR"}
    )
    
    location = StringField(
        "Luogo di lavoro",
        validators=[Optional(), Length(max=255)]
    )
    
    employment_type = SelectField(
        "Tipo contratto",
        choices=[
            ("full-time", "Full-time"),
            ("part-time", "Part-time"),
            ("contract", "Contratto"),
            ("internship", "Stage"),
            ("apprenticeship", "Apprendistato"),
            ("freelance", "Freelance"),
        ],
        validators=[Optional()]
    )
    
    # Dipartimento
    department_id = SelectField(
        "Dipartimento",
        coerce=int,
        validators=[DataRequired()]
    )
    
    # ATS Configuration
    what_we_search = TextAreaField(
        "Cosa cerchiamo nel CV (per analisi ATS)",
        validators=[DataRequired()],
        render_kw={
            "rows": 6,
            "placeholder": "Inserisci keywords, competenze, esperienze che l'ATS deve cercare nel CV..."
        }
    )
    
    form_weight = IntegerField(
        "Peso % del questionario",
        validators=[NumberRange(min=0, max=100)],
        default=50,
        render_kw={"placeholder": "50"}
    )
    
    cv_weight = IntegerField(
        "Peso % del CV",
        validators=[NumberRange(min=0, max=100)],
        default=50,
        render_kw={"placeholder": "50"}
    )
    
    # Kanban
    kanban_id = SelectField(
        "Pipeline Kanban",
        coerce=int,
        validators=[DataRequired(message="Seleziona una pipeline")]
    )
    
    # Costi separati per advertising
    costo_totale_speso_linkedin = FloatField(
        "Costo LinkedIn (€)",
        validators=[Optional(), NumberRange(min=0)],
        default=0.00,
        render_kw={"placeholder": "0.00", "step": "0.01"}
    )
    
    costo_totale_speso_facebook = FloatField(
        "Costo Facebook (€)",
        validators=[Optional(), NumberRange(min=0)],
        default=0.00,
        render_kw={"placeholder": "0.00", "step": "0.01"}
    )
    
    costo_totale_speso_instagram = FloatField(
        "Costo Instagram (€)",
        validators=[Optional(), NumberRange(min=0)],
        default=0.00,
        render_kw={"placeholder": "0.00", "step": "0.01"}
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Popola le scelte per department
        self.department_id.choices = [
            (0, "-- Seleziona dipartimento --")
        ] + [
            (d.id, d.name) 
            for d in Department.query.order_by(Department.name).all()
        ]
        
        # Popola le scelte per kanban
        from corposostenibile.models import RecruitingKanban
        self.kanban_id.choices = [
            (0, "-- Seleziona pipeline --")
        ] + [
            (k.id, k.name)
            for k in RecruitingKanban.query.filter_by(is_active=True).order_by(RecruitingKanban.name).all()
        ]
    
    def validate(self, extra_validators=None):
        """Validazione custom."""
        if not super().validate(extra_validators):
            return False
        
        # Verifica che form_weight + cv_weight = 100
        if self.form_weight.data + self.cv_weight.data != 100:
            self.form_weight.errors.append(
                "La somma dei pesi di form e CV deve essere 100%"
            )
            return False
        
        return True


class ApplicationForm(FlaskForm):
    """Form per candidatura pubblica."""
    
    # Dati personali
    first_name = StringField(
        "Nome",
        validators=[DataRequired(), Length(min=2, max=100)]
    )
    
    last_name = StringField(
        "Cognome",
        validators=[DataRequired(), Length(min=2, max=100)]
    )
    
    email = StringField(
        "Email",
        validators=[DataRequired(), Email()]
    )
    
    phone = StringField(
        "Telefono",
        validators=[Optional(), Length(max=30)]
    )
    
    linkedin_profile = StringField(
        "Profilo LinkedIn",
        validators=[Optional(), URL(), Length(max=255)]
    )
    
    portfolio_url = StringField(
        "Portfolio/Website",
        validators=[Optional(), URL(), Length(max=255)]
    )
    
    # Documenti
    cv_file = FileField(
        "Curriculum Vitae (PDF)",
        validators=[DataRequired()]
    )
    
    cover_letter = TextAreaField(
        "Lettera di presentazione",
        validators=[Optional()],
        render_kw={"rows": 6}
    )
    
    # Le domande dinamiche verranno aggiunte runtime


class KanbanForm(FlaskForm):
    """Form per configurazione Kanban."""
    
    name = StringField(
        "Nome pipeline",
        validators=[DataRequired(), Length(min=3, max=100)]
    )
    
    description = TextAreaField(
        "Descrizione",
        validators=[Optional()],
        render_kw={"rows": 3}
    )
    
    is_default = BooleanField("Pipeline di default")
    is_active = BooleanField("Attiva", default=True)
    
    auto_reject_days = IntegerField(
        "Auto-rifiuta dopo giorni",
        validators=[Optional(), NumberRange(min=1, max=365)],
        render_kw={"placeholder": "es. 30"}
    )


class KanbanStageForm(FlaskForm):
    """Form per fase del Kanban."""
    
    name = StringField(
        "Nome fase",
        validators=[DataRequired(), Length(min=2, max=100)]
    )
    
    stage_type = SelectField(
        "Tipo fase",
        validators=[DataRequired()]
    )
    
    description = TextAreaField(
        "Descrizione",
        validators=[Optional()],
        render_kw={"rows": 2}
    )
    
    color = StringField(
        "Colore (HEX)",
        validators=[Optional(), Length(max=7)],
        render_kw={"placeholder": "#3498db"}
    )
    
    icon = StringField(
        "Icona",
        validators=[Optional(), Length(max=50)]
    )
    
    order = IntegerField(
        "Ordine",
        validators=[NumberRange(min=0)],
        default=0
    )
    
    is_active = BooleanField("Attiva", default=True)
    is_final = BooleanField("Fase finale")
    
    auto_email_template = TextAreaField(
        "Template email automatica",
        validators=[Optional()],
        render_kw={"rows": 4}
    )


class OnboardingTemplateForm(FlaskForm):
    """Form per template onboarding."""
    
    name = StringField(
        "Nome template",
        validators=[DataRequired(), Length(min=3, max=100)]
    )
    
    department_id = SelectField(
        "Dipartimento",
        coerce=int,
        validators=[DataRequired()]
    )
    
    description = TextAreaField(
        "Descrizione",
        validators=[Optional()],
        render_kw={"rows": 3}
    )
    
    duration_days = IntegerField(
        "Durata (giorni)",
        validators=[NumberRange(min=1, max=365)],
        default=30
    )
    
    is_active = BooleanField("Attivo", default=True)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Popola le scelte per department
        self.department_id.choices = [
            (d.id, d.name) 
            for d in Department.query.order_by(Department.name).all()
        ]


class OnboardingTaskForm(FlaskForm):
    """Form per task onboarding."""
    
    name = StringField(
        "Nome task",
        validators=[DataRequired(), Length(min=3, max=200)]
    )
    
    description = TextAreaField(
        "Descrizione",
        validators=[Optional()],
        render_kw={"rows": 3}
    )
    
    task_type = SelectField(
        "Tipo task",
        choices=[
            ("document", "Documento"),
            ("training", "Formazione"),
            ("meeting", "Meeting"),
            ("system_access", "Accesso sistema"),
            ("equipment", "Attrezzatura"),
            ("introduction", "Presentazione"),
            ("compliance", "Compliance"),
            ("other", "Altro"),
        ],
        validators=[DataRequired()]
    )
    
    order = IntegerField(
        "Ordine",
        validators=[NumberRange(min=0)],
        default=0
    )
    
    due_after_days = IntegerField(
        "Scadenza dopo giorni",
        validators=[NumberRange(min=0, max=365)],
        default=0
    )
    
    is_required = BooleanField("Obbligatorio", default=True)
    
    assigned_role = StringField(
        "Ruolo assegnato",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "es. HR, IT, Manager"}
    )


class ScreeningForm(FlaskForm):
    """Form per avviare lo screening ATS."""
    
    job_offer_id = HiddenField(validators=[DataRequired()])
    
    screen_all = BooleanField(
        "Analizza tutte le candidature",
        default=True
    )
    
    only_new = BooleanField(
        "Solo candidature nuove"
    )
    
    min_score = IntegerField(
        "Punteggio minimo per passare",
        validators=[NumberRange(min=0, max=100)],
        default=60
    )
    
    auto_reject = BooleanField(
        "Rifiuta automaticamente candidati sotto la soglia",
        default=False
    )
    
    send_notifications = BooleanField(
        "Invia notifiche ai recruiter",
        default=True
    )