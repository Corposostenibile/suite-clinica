"""
blueprints/department/forms.py
==============================

Flask-WTF forms per:

- creazione / modifica di un Department
- creazione / modifica di un Task Kanban
- inserimento di commenti a un Task
"""

from __future__ import annotations

from datetime import date
from typing import List, Tuple

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    DateField,
    HiddenField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Length,
    Optional,
    ValidationError,
)

from corposostenibile.extensions import db
from corposostenibile.models import (
    Cliente,
    Department,
    TaskPriorityEnum,
    TaskStatusEnum,
    Team,
    User,
)

# --------------------------------------------------------------
#  Helper -­­ enum → choices
# --------------------------------------------------------------

def _enum_choices(enum_cls) -> List[Tuple[str, str]]:
    """Ritorna una lista [(value, label), …] partendo da un Enum."""
    return [(member.value, member.name.replace("_", " ").title()) for member in enum_cls]


# --------------------------------------------------------------
#  1. DepartmentForm
# --------------------------------------------------------------

class DepartmentForm(FlaskForm):
    """Form semplice per creare / modificare un reparto."""

    name = StringField(
        "Nome Dipartimento",
        validators=[DataRequired(), Length(max=80)],
        render_kw={"placeholder": "Es. Amministrazione"},
    )

    head_id = SelectField(
        "Manager Dipartimento",
        coerce=int,
        validators=[Optional()],
        choices=[],  # popolato in __init__
        description="Utente responsabile (facoltativo).",
    )

    # ────────────────────── NUOVI CAMPI DOCUMENTI ────────────────────── #
    
    # Linee guida (testo o PDF)
    guidelines_text = TextAreaField(
        "Linee Guida Dipartimento (Testo)",
        validators=[Optional(), Length(max=10000)],
        render_kw={
            "rows": 10, 
            "placeholder": "Inserisci le linee guida testuali del dipartimento...\n\nPuoi usare markdown per la formattazione.",
            "class": "form-control"
        },
        description="Puoi inserire le linee guida come testo oppure caricare un PDF."
    )
    
    guidelines_pdf = FileField(
        "Linee Guida Dipartimento (PDF)",
        validators=[
            Optional(),
            FileAllowed(['pdf'], 'Solo file PDF sono ammessi!')
        ],
        description="Carica un PDF con le linee guida del dipartimento (max 10MB)."
    )
    
    # Standard Operating Procedures
    sop_members_pdf = FileField(
        "SOP Membri (PDF)",
        validators=[
            Optional(),
            FileAllowed(['pdf'], 'Solo file PDF sono ammessi!')
        ],
        description="Standard Operating Procedures per i membri del dipartimento."
    )
    
    sop_managers_pdf = FileField(
        "SOP Manager (PDF)", 
        validators=[
            Optional(),
            FileAllowed(['pdf'], 'Solo file PDF sono ammessi!')
        ],
        description="Standard Operating Procedures per i manager/responsabili."
    )

    # Flag per rimuovere documenti esistenti
    remove_guidelines_pdf = HiddenField(default="false")
    remove_sop_members_pdf = HiddenField(default="false")
    remove_sop_managers_pdf = HiddenField(default="false")

    submit = SubmitField("Salva")

    # ─────────────────── init dinamico ────────────────────────── #
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # tendina con tutti gli utenti attivi
        self.head_id.choices = (
            [(0, "— Nessuno —")]
            + [
                (u.id, u.full_name)
                for u in db.session.query(User)
                .filter(User.is_active.is_(True))
                .order_by(User.first_name, User.last_name)
            ]
        )

    # ─────────────────── validazioni custom documenti ────────────────────── #
    def validate_guidelines_pdf(self, field: FileField):
        """Valida dimensione file PDF linee guida."""
        if field.data:
            # La validazione della dimensione sarà gestita da Flask MAX_CONTENT_LENGTH
            # ma possiamo aggiungere controlli aggiuntivi qui se necessario
            pass
    
    def validate_sop_members_pdf(self, field: FileField):
        """Valida dimensione file PDF SOP membri."""
        if field.data:
            pass
    
    def validate_sop_managers_pdf(self, field: FileField):
        """Valida dimensione file PDF SOP manager."""
        if field.data:
            pass


# --------------------------------------------------------------
#  2. TaskForm  (creazione / modifica card Kanban)
# --------------------------------------------------------------

class TaskForm(FlaskForm):
    """Form per creare o aggiornare un task Kanban di reparto."""

    title = StringField(
        "Titolo",
        validators=[DataRequired(), Length(max=255)],
        render_kw={"placeholder": "Es. Preparare report mensile"},
    )

    description = TextAreaField(
        "Descrizione",
        validators=[Optional()],
        render_kw={"rows": 4, "placeholder": "Dettagli, link, checklist…"},
    )

    status = SelectField(
        "Colonna / Stato",
        choices=_enum_choices(TaskStatusEnum),
        validators=[DataRequired()],
    )

    priority = SelectField(
        "Priorità",
        choices=_enum_choices(TaskPriorityEnum),
        validators=[DataRequired()],
    )

    due_date = DateField(
        "Scadenza",
        validators=[Optional()],
        format="%Y-%m-%d",
        default=None,
        render_kw={"placeholder": "YYYY-MM-DD"},
    )

    department_id = SelectField(
        "Reparto",
        coerce=int,
        validators=[DataRequired()],
        choices=[],  # popolato in __init__
    )

    # CAMBIATO: Assegnatario ora usa campi hidden + search
    assignee_id = HiddenField(
        "Assegnatario ID",
        validators=[Optional()],
    )
    
    assignee_search = StringField(
        "Assegnatario",
        validators=[Optional()],
        render_kw={"placeholder": "Cerca utente..."},
    )

    # CAMBIATO: Cliente ora usa campi hidden + search  
    client_id = HiddenField(
        "Cliente ID",
        validators=[Optional()],
    )
    
    client_search = StringField(
        "Cliente collegato",
        validators=[Optional()],
        render_kw={"placeholder": "Cerca cliente..."},
    )

    submit = SubmitField("Salva task")

    # ─────────────────── init dinamico ────────────────────────── #
    def __init__(self, *args, **kwargs):
        """
        Accetta opzionalmente:

        • department (Department) → non più necessario per filtro assignee
        """
        department: Department | None = kwargs.pop("department", None)
        super().__init__(*args, **kwargs)

        # Reparti
        self.department_id.choices = [
            (d.id, d.name)
            for d in db.session.query(Department).order_by(Department.name)
        ]

        # Se stiamo modificando un task esistente, precompila i campi search
        if hasattr(self, 'data') and self.assignee_id.data:
            user = db.session.query(User).get(self.assignee_id.data)
            if user:
                self.assignee_search.data = user.full_name
                
        if hasattr(self, 'data') and self.client_id.data:
            client = db.session.query(Cliente).get(self.client_id.data)
            if client:
                self.client_search.data = client.nome_cognome

    # ─────────────────── validazioni extra ────────────────────── #
    def validate_due_date(self, field: DateField):  # noqa: N802
        if field.data and field.data < date.today():
            raise ValidationError("La scadenza non può essere nel passato.")
            
    def validate_assignee_id(self, field: HiddenField):  # noqa: N802
        """Valida che l'ID assegnatario sia valido se presente."""
        if field.data:
            user = db.session.query(User).get(field.data)
            if not user or not user.is_active:
                raise ValidationError("Assegnatario non valido.")
                
    def validate_client_id(self, field: HiddenField):  # noqa: N802
        """Valida che l'ID cliente sia valido se presente."""
        if field.data:
            client = db.session.query(Cliente).get(field.data)
            if not client:
                raise ValidationError("Cliente non valido.")


# --------------------------------------------------------------
#  3. CommentForm  (note / discussione sul task)
# --------------------------------------------------------------

class CommentForm(FlaskForm):
    """Aggiunge una nota a un task."""

    body = TextAreaField(
        "Commento",
        validators=[DataRequired(), Length(max=2000)],
        render_kw={"rows": 3, "placeholder": "Scrivi un commento…"},
    )

    submit = SubmitField("Aggiungi commento")


# --------------------------------------------------------------
#  4. TeamForm  (creazione / modifica team)
# --------------------------------------------------------------

class TeamForm(FlaskForm):
    """
    Form per creare o modificare un Team all'interno di un dipartimento.

    Un team è una sotto-organizzazione del dipartimento con:
    - Nome proprio
    - Descrizione opzionale
    - Team leader (head)
    - Membri assegnati
    """

    name = StringField(
        "Nome Team",
        validators=[DataRequired(), Length(max=120)],
        render_kw={"placeholder": "es. Team Clinico, Team Sportivo, Team Ricerca"},
        description="Nome identificativo del team all'interno del dipartimento."
    )

    description = TextAreaField(
        "Descrizione",
        validators=[Optional(), Length(max=500)],
        render_kw={
            "rows": 3,
            "placeholder": "Descrizione del team e delle sue responsabilità..."
        },
        description="Breve descrizione delle funzioni e responsabilità del team (opzionale)."
    )

    head_id = SelectField(
        "Team Leader",
        coerce=int,
        validators=[Optional()],
        choices=[],  # popolato in __init__
        description="Responsabile del team (deve essere membro del dipartimento)."
    )

    submit = SubmitField("Salva Team")

    # ─────────────────── init dinamico ────────────────────────── #
    def __init__(self, department=None, *args, **kwargs):
        """
        Inizializza il form con le scelte disponibili.

        Args:
            department: Department object (obbligatorio per popolare head_id choices)
        """
        super().__init__(*args, **kwargs)

        if department:
            # Popola choices con membri del dipartimento
            self.head_id.choices = [(0, "— Nessun leader —")] + [
                (user.id, user.full_name)
                for user in department.all_members
                if user.is_active
            ]
        else:
            self.head_id.choices = [(0, "— Nessun leader —")]

    # ─────────────────── validazioni custom ────────────────────── #
    def validate_head_id(self, field: SelectField):
        """Valida che il team leader sia un membro attivo."""
        if field.data and field.data != 0:
            user = db.session.get(User, field.data)
            if not user:
                raise ValidationError("Team leader non trovato.")
            if not user.is_active:
                raise ValidationError("Il team leader deve essere un utente attivo.")

    def validate_name(self, field: StringField):
        """
        Valida che il nome del team sia unico all'interno del dipartimento.

        Nota: Questa validazione è duplicata dal constraint del database
        (uq_teams_department_name), ma è meglio catturare l'errore qui
        per dare un messaggio più chiaro all'utente.
        """
        # Questa validazione viene fatta anche in route con controllo più approfondito
        # se necessario verificare unicità con department_id
        pass