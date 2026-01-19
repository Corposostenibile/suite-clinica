"""
team.forms
==========

WTForms per la gestione degli utenti interni (CRUD Team).

- credenziali                               • flag ACL / stato
- profilo personale  (+ upload avatar)      • caricamento certificazioni (multi‑file)
- dati HR  (tipo + pdf contratto)           • nuovi campi estesi

Questo file ora **non** effettua più alcun controllo MIME lato WTForms sui
contratti e sulle certificazioni: la verifica viene delegata unicamente alle
funzioni `_validate_file`, `_save_contract` e `_save_cert_file` del blueprint.
Così il flusso di upload è identico a quello già funzionante nelle view
`add‑contract` e `add‑cert`.
"""

from __future__ import annotations

from typing import List, Tuple

from flask_babel import lazy_gettext as _l
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, MultipleFileField
from wtforms import (
    BooleanField,
    DateField,
    EmailField,
    PasswordField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
    TimeField,
    FormField,
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional
from wtforms.widgets import ListWidget, CheckboxInput

# ───────────────────────── helper scelte dinamiche ──────────────────────────

def _choices_from_query(
    query,
    label_attr: str = "name",
    value_attr: str = "id",
) -> List[Tuple]:
    """Converte una query SQLAlchemy in [(value, label), …]."""
    return [(getattr(o, value_attr), getattr(o, label_attr)) for o in query.all()]

# ─────────────────────────── mime‑types consentiti ───────────────────────────
# NB: questi set rimangono a disposizione di altre parti dell'applicazione, ma
# non vengono più usati nei validator del form (vedi sotto).
ALLOWED_AVATAR_MIMETYPES: set[str]   = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_CERT_MIMETYPES: set[str]     = {
    "application/pdf", "application/x-pdf", "application/acrobat",
    "applications/vnd.pdf", "text/pdf", "text/x-pdf", "application/octet-stream",
    "image/jpeg", "image/png", "image/jpg", "image/pjpeg", "image/x-png",
}
ALLOWED_CONTRACT_MIMETYPES: set[str] = {
    "application/pdf", "application/x-pdf", "application/acrobat",
    "applications/vnd.pdf", "text/pdf", "text/x-pdf", "application/octet-stream",
}

# ─────────────────────────── sub‑forms ───────────────────────────────────

class WorkScheduleForm(FlaskForm):
    """Sub‑form per orario di lavoro (nessun CSRF: gestita nel form padre)."""

    class Meta:
        csrf = False  # Disabilita CSRF per sub‑form

    schedule_type = SelectField(
        _l("Tipo orario"),
        choices=[
            ("full-time", "Full‑time"),
            ("part-time", "Part‑time"),
            ("shift", "Turni"),
            ("flexible", "Flessibile"),
        ],
        default="full-time",
    )

    hours_from = TimeField(
        _l("Dalle"),
        format="%H:%M",
        validators=[Optional()],
        render_kw={"placeholder": "09:00"},
    )

    hours_to = TimeField(
        _l("Alle"),
        format="%H:%M",
        validators=[Optional()],
        render_kw={"placeholder": "18:00"},
    )

    work_days = SelectMultipleField(
        _l("Giorni lavorativi"),
        choices=[
            ("mon", "Lunedì"),
            ("tue", "Martedì"),
            ("wed", "Mercoledì"),
            ("thu", "Giovedì"),
            ("fri", "Venerdì"),
            ("sat", "Sabato"),
            ("sun", "Domenica"),
        ],
        default=["mon", "tue", "wed", "thu", "fri"],
        widget=ListWidget(prefix_label=False),
        option_widget=CheckboxInput(),
    )


class DevelopmentPlanForm(FlaskForm):
    """Sub‑form per piano di sviluppo personale."""

    class Meta:
        csrf = False

    goals = TextAreaField(
        _l("Obiettivi di sviluppo"),
        validators=[Optional()],
        render_kw={"rows": 3, "placeholder": "Obiettivi di crescita professionale..."},
    )

    skills_to_develop = TextAreaField(
        _l("Competenze da sviluppare"),
        validators=[Optional()],
        render_kw={"rows": 3, "placeholder": "Skills tecniche/soft da migliorare..."},
    )

    timeline = StringField(
        _l("Timeline"),
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "es: Q1 2025, 6 mesi, etc."},
    )


# ─────────────────────────────── main form ──────────────────────────────────

class UserForm(FlaskForm):
    # ───── credenziali ─────
    email = EmailField(
        _l("Email"),
        validators=[DataRequired(), Email(), Length(max=255)],
        render_kw={"autocomplete": "username"},
    )

    password = PasswordField(
        _l("Password"),
        validators=[Optional(), Length(min=6)],
        render_kw={"autocomplete": "new-password"},
    )

    confirm = PasswordField(
        _l("Conferma password"),
        validators=[Optional(), EqualTo("password", message=_l("Le password non coincidono"))],
        render_kw={"autocomplete": "new-password"},
    )

    # ───── profilo personale ─────
    first_name = StringField(_l("Nome"), validators=[DataRequired(), Length(max=80)])
    last_name = StringField(_l("Cognome"), validators=[DataRequired(), Length(max=80)])
    job_title = StringField(_l("Ruolo / job title"), validators=[Optional(), Length(max=120)])
    mobile = StringField(_l("Mobile"), validators=[Optional(), Length(max=30)])

    # ───── INDIRIZZO ─────
    citta = StringField(
        _l("Città"),
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "es. Roma", "class": "form-control"},
    )
    indirizzo = StringField(
        _l("Indirizzo"),
        validators=[Optional(), Length(max=255)],
        render_kw={"placeholder": "es. Via Roma 123, 00100", "class": "form-control"},
    )

    # MODIFICA: Rimuoviamo FileAllowed per l'avatar
    avatar_file = FileField(
        _l("Avatar (JPG/PNG/WebP)"),
        validators=[Optional()],  # Solo Optional, nessun FileAllowed
        description=_l("L'immagine verrà ridimensionata a 256×256 px."),
    )

    # sentinel 0 = "nessun reparto"
    department_id = SelectField(
        _l("Dipartimento"),
        coerce=int,
        validators=[Optional()],
        choices=[(0, "---")],  # popolato dinamicamente in __init__
    )

    # ───── dati HR ─────
    contract_type = SelectField(
        _l("Tipo contratto"),
        choices=[
            ("", "---"),
            ("full-time", "Full-time"),
            ("part-time", "Part-time"),
            ("stage", "Stage"),
            ("p.iva", "P. IVA"),
        ],
        validators=[Optional()],
    )

    hired_at = DateField(
        _l("Data assunzione"),
        format="%Y-%m-%d",
        validators=[Optional()],
        render_kw={"placeholder": "YYYY-MM-DD"},
    )

    # *** NESSUN FileAllowed: la validazione reale avverrà in _validate_file ***
    contract_file = FileField(
        _l("Contratto (PDF)"),
        validators=[Optional()],
        description=_l("Carica il PDF firmato del contratto di lavoro."),
    )

    # ───── NUOVI CAMPI PERSONALI ─────
    birth_date = DateField(
        _l("Data di nascita"),
        format="%Y-%m-%d",
        validators=[Optional()],
        render_kw={"placeholder": "YYYY-MM-DD"},
        description=_l("Per calcolo età e auguri automatici"),
    )
    
    # ───── DATI FISCALI ─────
    codice_fiscale = StringField(
        _l("Codice Fiscale"),
        validators=[Optional(), Length(max=16)],
        render_kw={"placeholder": "RSSMRA85M01H501Z", "class": "form-control text-uppercase"},
        description=_l("Codice fiscale (16 caratteri)"),
    )
    
    partita_iva = StringField(
        _l("Partita IVA"),
        validators=[Optional(), Length(max=11)],
        render_kw={"placeholder": "12345678901", "class": "form-control"},
        description=_l("Solo numeri (11 cifre)"),
    )
    
    documento_tipo = SelectField(
        _l("Tipo documento"),
        choices=[
            ("", "-- Seleziona --"),
            ("carta_identita", "Carta d'identità"),
            ("patente", "Patente di guida"),
            ("passaporto", "Passaporto"),
        ],
        validators=[Optional()],
        render_kw={"class": "form-control"},
    )
    
    documento_numero = StringField(
        _l("Numero documento"),
        validators=[Optional(), Length(max=50)],
        render_kw={"placeholder": "AX1234567", "class": "form-control text-uppercase"},
    )
    
    documento_scadenza = DateField(
        _l("Scadenza documento"),
        format="%Y-%m-%d",
        validators=[Optional()],
        render_kw={"placeholder": "YYYY-MM-DD", "class": "form-control"},
    )
    
    ral_annua = StringField(
        _l("RAL Annua (€)"),
        validators=[Optional()],
        render_kw={"placeholder": "30000.00", "class": "form-control"},
        description=_l("Retribuzione Annua Lorda"),
    )
    
    stipendio_mensile_lordo = StringField(
        _l("Stipendio Mensile Lordo (€)"),
        validators=[Optional()],
        render_kw={"placeholder": "2500.00", "class": "form-control"},
    )

    languages = SelectMultipleField(
        _l("Lingue parlate"),
        choices=[
            ("it", "Italiano"),
            ("en", "Inglese"),
            ("fr", "Francese"),
            ("de", "Tedesco"),
            ("es", "Spagnolo"),
            ("zh", "Cinese"),
            ("ar", "Arabo"),
            ("pt", "Portoghese"),
            ("ru", "Russo"),
            ("ja", "Giapponese"),
        ],
        validators=[Optional()],
        widget=ListWidget(prefix_label=False),
        option_widget=CheckboxInput(),
        description=_l("Seleziona tutte le lingue parlate"),
    )

    # ───── ORARIO DI LAVORO ─────
    work_schedule = FormField(
        WorkScheduleForm,
        label=_l("Orario di lavoro"),
        description=_l("Definisci l'orario e i giorni lavorativi"),
    )

    # ───── PIANO DI SVILUPPO ─────
    development_plan = FormField(
        DevelopmentPlanForm,
        label=_l("Piano di sviluppo personale"),
        description=_l("Obiettivi e competenze da sviluppare"),
    )

    # ───── ACCESSI / ACCOUNT ─────
    accounts_google = StringField(
        _l("Account Google Workspace"),
        validators=[Optional(), Email(), Length(max=255)],
        render_kw={"placeholder": "nome.cognome@corposostenibile.it"},
    )

    accounts_slack = StringField(
        _l("Username Slack"),
        validators=[Optional(), Length(max=50)],
        render_kw={"placeholder": "@username"},
    )

    accounts_github = StringField(
        _l("Username GitHub"),
        validators=[Optional(), Length(max=50)],
        render_kw={"placeholder": "username"},
    )

    accounts_other = TextAreaField(
        _l("Altri account"),
        validators=[Optional()],
        render_kw={
            "rows": 2,
            "placeholder": "Altri account aziendali (uno per riga, formato: servizio: username/email)",
        },
        description=_l("es: Jira: nome.cognome@azienda.com"),
    )

    # ───── NOTE HR (solo admin) ─────
    hr_notes = TextAreaField(
        _l("Note HR (riservate)"),
        validators=[Optional()],
        render_kw={
            "rows": 4,
            "placeholder": "Note visibili solo agli amministratori...",
            "class": "form-control bg-light",
        },
        description=_l("⚠️ Informazioni riservate HR - Solo amministratori"),
    )

    # ───── NOTE PER ASSEGNAZIONE AI (solo admin) ─────
    assignment_ai_notes = TextAreaField(
        _l("Note per Assegnazione AI"),
        validators=[Optional(), Length(max=2000)],
        render_kw={
            "rows": 6,
            "placeholder": "Descrivi competenze, specialità e expertise del professionista per l'assegnazione automatica AI (max 2000 caratteri)...",
            "class": "form-control bg-light",
            "maxlength": "2000",
        },
        description=_l("🤖 Utilizzato dall'AI per assegnazioni automatiche - Solo amministratori"),
    )

    # ───── flag ACL / stato ─────
    is_admin = BooleanField(_l("Admin"))
    is_active = BooleanField(_l("Attivo"), default=True)

    # ───── certificazioni (multi‑file) ─────
    new_cert_files = MultipleFileField(
        _l("Carica certificazioni"),
        validators=[Optional()],
        description=_l("Allega uno o più file da associare al profilo."),
    )

    # ───── submit ─────
    submit = SubmitField(_l("Salva"))

    # ─────────────────── init dinamico ───────────────────

    def __init__(self, *args, db_session=None, **kwargs):
        """Popola il select dei reparti evitando import circolari."""
        super().__init__(*args, **kwargs)

        if db_session is None:
            from corposostenibile.extensions import db as _db
            db_session = _db.session

        from corposostenibile.models import Department

        self.department_id.choices = [(0, "---")] + _choices_from_query(
            db_session.query(Department).order_by(Department.name)
        )


# ════════════════════════════════════════════════════════════════════════════ #
#  Form per sistema ferie/permessi
# ════════════════════════════════════════════════════════════════════════════ #

class LeavePolicyForm(FlaskForm):
    """Form per configurazione policy ferie/permessi annuale."""
    
    year = SelectField(
        _l("Anno"),
        coerce=int,
        validators=[DataRequired()],
        render_kw={"class": "form-select"}
    )
    
    annual_leave_days = StringField(
        _l("Giorni ferie annuali"),
        validators=[DataRequired()],
        render_kw={"type": "number", "min": "0", "max": "365"},
        description=_l("Numero di giorni ferie spettanti per anno (uguale per tutti)")
    )
    
    annual_permission_hours = StringField(
        _l("Ore permessi annuali (ROL)"),
        validators=[DataRequired()],
        render_kw={"type": "number", "min": "0", "max": "500"},
        description=_l("Numero di ore di permesso retribuito annuali")
    )
    
    min_consecutive_days = StringField(
        _l("Giorni minimi consecutivi"),
        validators=[DataRequired()],
        render_kw={"type": "number", "min": "1", "max": "30"},
        description=_l("Numero minimo di giorni consecutivi per richiesta ferie")
    )
    
    max_consecutive_days = StringField(
        _l("Giorni massimi consecutivi"),
        validators=[DataRequired()],
        render_kw={"type": "number", "min": "1", "max": "60"},
        description=_l("Numero massimo di giorni consecutivi per richiesta ferie")
    )
    
    notes = TextAreaField(
        _l("Note/Regole aggiuntive"),
        validators=[Optional()],
        render_kw={"rows": 4, "placeholder": "Eventuali regole o note sulla policy..."}
    )
    
    submit = SubmitField(_l("Salva Policy"))
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Popola anni disponibili (anno corrente + prossimi 2)
        from datetime import datetime
        current_year = datetime.now().year
        self.year.choices = [(y, str(y)) for y in range(current_year, current_year + 3)]


class LeaveRequestForm(FlaskForm):
    """Form per richiesta ferie/permessi."""
    
    leave_type = SelectField(
        _l("Tipo assenza"),
        validators=[DataRequired()],
        render_kw={"class": "form-select"}
    )
    
    start_date = DateField(
        _l("Data inizio"),
        validators=[DataRequired()],
        render_kw={"class": "form-control datepicker"}
    )
    
    end_date = DateField(
        _l("Data fine"),
        validators=[DataRequired()],
        render_kw={"class": "form-control datepicker"}
    )
    
    # Solo per permessi
    hours = StringField(
        _l("Ore (solo per permessi)"),
        validators=[Optional()],
        render_kw={
            "type": "number", 
            "min": "0.5", 
            "max": "8", 
            "step": "0.5",
            "placeholder": "Es: 4.5"
        }
    )
    
    notes = TextAreaField(
        _l("Note/Motivazioni"),
        validators=[Optional()],
        render_kw={
            "rows": 3,
            "placeholder": "Eventuali note o motivazioni..."
        }
    )
    
    submit = SubmitField(_l("Invia Richiesta"))
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from corposostenibile.models import LeaveTypeEnum
        self.leave_type.choices = [
            (LeaveTypeEnum.ferie.value, "Ferie"),
            (LeaveTypeEnum.permesso.value, "Permesso (ore)"),
            (LeaveTypeEnum.malattia.value, "Malattia")
        ]


class HolidayForm(FlaskForm):
    """Form per gestione festività/ponti aziendali."""
    
    date = DateField(
        _l("Data"),
        validators=[DataRequired()],
        render_kw={"class": "form-control datepicker"}
    )
    
    name = StringField(
        _l("Nome festività"),
        validators=[DataRequired(), Length(max=100)],
        render_kw={"placeholder": "Es: Ponte Immacolata"}
    )
    
    is_company_bridge = BooleanField(
        _l("Ponte aziendale"),
        description=_l("Seleziona se è un ponte aggiunto dall'azienda")
    )
    
    submit = SubmitField(_l("Aggiungi Festività"))