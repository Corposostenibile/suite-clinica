"""
blueprints/ticket/forms.py
==========================

Flask-WTF forms per il sistema di ticketing.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Tuple

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, MultipleFileField
from wtforms import (
    BooleanField,
    DateTimeField,
    HiddenField,
    RadioField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    Length,
    Optional,
    ValidationError,
)

from corposostenibile.extensions import db
from corposostenibile.models import (
    Department,
    Ticket,
    TicketCategoryEnum,
    TicketStatusEnum,
    TicketUrgencyEnum,
    User,
)


# ────────────────────────────────────────────────────────────────────
#  Helper functions
# ────────────────────────────────────────────────────────────────────

def _urgency_choices() -> List[Tuple[str, str]]:
    """Ritorna le scelte per il campo urgenza."""
    return [
        (TicketUrgencyEnum.alta.value, "🔴 Alta - Da risolvere entro oggi"),
        (TicketUrgencyEnum.media.value, "🟡 Media - Da risolvere entro 2 giorni"),
        (TicketUrgencyEnum.bassa.value, "🟢 Bassa - Da risolvere entro la settimana"),
    ]


def _status_choices() -> List[Tuple[str, str]]:
    """Ritorna le scelte per il campo status."""
    return [
        (TicketStatusEnum.nuovo.value, "Nuovo"),
        (TicketStatusEnum.in_lavorazione.value, "In Lavorazione"),
        (TicketStatusEnum.in_attesa.value, "In Attesa"),
        (TicketStatusEnum.chiuso.value, "Chiuso"),
    ]


def _category_choices() -> List[Tuple[str, str]]:
    """Ritorna le scelte per il campo categoria (solo dept 13)."""
    return [
        (TicketCategoryEnum.problema.value, "Problema"),
        (TicketCategoryEnum.upgrade.value, "Upgrade"),
        (TicketCategoryEnum.review.value, "Review"),
    ]


# ────────────────────────────────────────────────────────────────────
#  Form per utenti autenticati
# ────────────────────────────────────────────────────────────────────

class AuthenticatedTicketForm(FlaskForm):
    """
    Form per apertura ticket da utenti autenticati.
    Nome, cognome, email e dipartimento vengono presi dall'utente loggato.
    """
    
    # Dipartimento destinatario
    department_id = SelectField(
        "Dipartimento a cui inviare la richiesta *",
        coerce=int,
        validators=[
            DataRequired(message="Seleziona il dipartimento destinatario")
        ],
        choices=[],  # Popolato in __init__
        render_kw={
            "class": "form-select",
            "onchange": "loadDepartmentMembers(this.value)"
        }
    )
    
    # Membro del dipartimento (OBBLIGATORIO)
    assigned_to_id = SelectField(
        "Seleziona membro del dipartimento *",
        coerce=int,
        validators=[
            DataRequired(message="Devi selezionare un membro del dipartimento")
        ],
        choices=[],  # Popolato dinamicamente via JavaScript
        validate_choice=False,  # Disabilita la validazione automatica delle scelte
        render_kw={
            "class": "form-select",
            "disabled": "disabled"
        }
    )
    
    # Tipo di riferimento (Lead o Cliente esistente)
    reference_type = RadioField(
        "Tipo di riferimento",
        choices=[
            ('none', 'Nessun riferimento'),
            ('lead', 'Lead (non ancora cliente)'),
            ('cliente', 'Cliente esistente')
        ],
        default='none',
        validators=[Optional()],
        render_kw={"class": "form-check-input"}
    )
    
    # Campo per Lead (nome testuale)
    related_client_name = StringField(
        "Nome Lead",
        validators=[
            Optional(),
            Length(max=255)
        ],
        render_kw={
            "placeholder": "Nome del lead interessato",
            "class": "form-control"
        }
    )
    
    # Campo per Cliente esistente (sarà popolato via autocomplete)
    cliente_id = HiddenField(
        "ID Cliente",
        validators=[Optional()]
    )
    
    # Campo di ricerca per autocomplete cliente
    cliente_search = StringField(
        "Cerca Cliente",
        validators=[Optional()],
        render_kw={
            "placeholder": "Inizia a digitare il nome del cliente...",
            "class": "form-control",
            "autocomplete": "off"
        }
    )
    
    # Dettagli ticket
    title = StringField(
        "Oggetto della richiesta *",
        validators=[
            DataRequired(message="L'oggetto è obbligatorio")
        ],
        render_kw={
            "placeholder": "Breve descrizione del problema/richiesta",
            "class": "form-control"
        }
    )
    
    description = TextAreaField(
        "Descrizione dettagliata *",
        validators=[
            DataRequired(message="La descrizione è obbligatoria")
        ],
        render_kw={
            "rows": 6,
            "placeholder": "Descrivi in dettaglio la problematica o richiesta...",
            "class": "form-control"
        }
    )
    
    urgency = RadioField(
        "Grado di urgenza *",
        choices=_urgency_choices(),
        validators=[
            DataRequired(message="Seleziona il grado di urgenza")
        ],
        default=TicketUrgencyEnum.media.value,
        render_kw={"class": "form-check-input"}
    )

    # Categoria (solo per dipartimento ID=13)
    category = RadioField(
        "Categoria ticket *",
        choices=_category_choices(),
        validators=[Optional()],  # Validato dinamicamente se dept 13
        render_kw={
            "class": "form-check-input",
            "style": "display:none;"  # Nascosto di default, mostrato da JS
        }
    )

    # Allegati multipli (opzionale, max 5)
    attachments = MultipleFileField(
        "Allegati (max 5 file, 5MB ciascuno)",
        validators=[
            Optional(),
            FileAllowed(
                ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'webp'],
                'Sono accettati solo file PDF o immagini (JPG, PNG, GIF, WEBP)'
            )
        ],
        render_kw={
            "class": "form-control",
            "accept": ".pdf,.jpg,.jpeg,.png,.gif,.webp",
            "multiple": True,
            "data-max-files": "5",
            "data-max-size": "5242880"  # 5MB in bytes
        }
    )
    
    submit = SubmitField(
        "Invia Richiesta",
        render_kw={"class": "btn btn-primary"}
    )
    
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Popola dipartimenti
        self.department_id.choices = [(0, "-- Seleziona --")]
        
        # Mostra tutti i dipartimenti rilevanti (incluso il proprio per permettere ticket interni)
        # Escludi solo CEO, Co-Founder e Test che sono dipartimenti speciali
        departments = Department.query.filter(
            ~Department.name.in_(['CEO', 'Co-Founder', 'Test'])
        ).order_by(Department.name).all()
        
        # Unifica Consulenti Sales 1 e Consulenti Sales 2 in un'unica voce
        sales_team_added = False
        for d in departments:
            if d.name in ['Consulenti Sales 1', 'Consulenti Sales 2']:
                if not sales_team_added:
                    # Usa l'ID del primo Consulenti Sales trovato e rinomina in "Sales Team"
                    self.department_id.choices.append((d.id, 'Sales Team'))
                    sales_team_added = True
                # Salta il secondo Consulenti Sales
            else:
                self.department_id.choices.append((d.id, d.name))
        
        # Popola membri se un dipartimento è già selezionato (per validazione POST)
        if self.department_id.data and self.department_id.data != 0:
            members = User.query.filter_by(
                department_id=self.department_id.data,
                is_active=True
            ).order_by(User.first_name, User.last_name).all()
            
            self.assigned_to_id.choices = [(0, "-- Seleziona un membro --")]
            self.assigned_to_id.choices.extend([
                (m.id, m.full_name) for m in members
            ])
        else:
            # Se non c'è dipartimento selezionato, metti scelte vuote
            self.assigned_to_id.choices = [(0, "-- Seleziona prima un dipartimento --")]
        
        # Validazione custom per department_id
        def validate_department_id(form, field):
            if field.data == 0:
                raise ValidationError("Seleziona un dipartimento valido")
        
        self.department_id.validators.append(validate_department_id)
        
        # Validazione custom per assigned_to_id
        def validate_assigned_to_id(form, field):
            if not field.data or field.data == 0:
                raise ValidationError("Devi selezionare un membro del dipartimento")

        self.assigned_to_id.validators.append(validate_assigned_to_id)

        # Validazione custom per category (obbligatoria solo per dept 13)
        def validate_category(form, field):
            if form.department_id.data == 13:
                if not field.data:
                    raise ValidationError("La categoria è obbligatoria per questo dipartimento")

        self.category.validators.append(validate_category)


# ────────────────────────────────────────────────────────────────────
#  Form pubblico (DEPRECATO - mantenuto per compatibilità)
# ────────────────────────────────────────────────────────────────────

class PublicTicketForm(FlaskForm):
    """
    Form pubblico per apertura ticket.
    Non richiede autenticazione.
    """
    
    # Dati richiedente
    first_name = StringField(
        "Nome *",
        validators=[
            DataRequired(message="Il nome è obbligatorio"),
            Length(min=2, max=80, message="Il nome deve essere tra 2 e 80 caratteri")
        ],
        render_kw={"placeholder": "Mario", "class": "form-control"}
    )
    
    last_name = StringField(
        "Cognome *",
        validators=[
            DataRequired(message="Il cognome è obbligatorio"),
            Length(min=2, max=80, message="Il cognome deve essere tra 2 e 80 caratteri")
        ],
        render_kw={"placeholder": "Rossi", "class": "form-control"}
    )
    
    email = StringField(
        "Email *",
        validators=[
            DataRequired(message="L'email è obbligatoria"),
            Email(message="Inserisci un'email valida"),
            Length(max=255)
        ],
        render_kw={"placeholder": "mario.rossi@example.com", "class": "form-control"}
    )
    
    # Dipartimento destinatario
    department_id = SelectField(
        "Dipartimento a cui inviare la richiesta *",
        coerce=int,
        validators=[
            DataRequired(message="Seleziona il dipartimento destinatario")
        ],
        choices=[],  # Popolato in __init__
        render_kw={"class": "form-select"}
    )
    
    # Tipo di riferimento (Lead o Cliente esistente)
    reference_type = RadioField(
        "Tipo di riferimento",
        choices=[
            ('none', 'Nessun riferimento'),
            ('lead', 'Lead (non ancora cliente)'),
            ('cliente', 'Cliente esistente')
        ],
        default='none',
        validators=[Optional()],
        render_kw={"class": "form-check-input"}
    )
    
    # Campo per Lead (nome testuale)
    related_client_name = StringField(
        "Nome Lead",
        validators=[
            Optional(),
            Length(max=255)
        ],
        render_kw={
            "placeholder": "Nome del lead interessato",
            "class": "form-control"
        }
    )
    
    # Campo per Cliente esistente (sarà popolato via autocomplete)
    cliente_id = HiddenField(
        "ID Cliente",
        validators=[Optional()]
    )
    
    # Campo di ricerca per autocomplete cliente
    cliente_search = StringField(
        "Cerca Cliente",
        validators=[Optional()],
        render_kw={
            "placeholder": "Inizia a digitare il nome del cliente...",
            "class": "form-control",
            "autocomplete": "off"
        }
    )
    
    # Dettagli ticket
    title = StringField(
        "Oggetto della richiesta *",
        validators=[
            DataRequired(message="L'oggetto è obbligatorio")
        ],
        render_kw={
            "placeholder": "Breve descrizione del problema/richiesta",
            "class": "form-control"
        }
    )
    
    description = TextAreaField(
        "Descrizione dettagliata *",
        validators=[
            DataRequired(message="La descrizione è obbligatoria")
        ],
        render_kw={
            "rows": 6,
            "placeholder": "Descrivi in dettaglio la problematica o richiesta...",
            "class": "form-control"
        }
    )
    
    urgency = RadioField(
        "Grado di urgenza *",
        choices=_urgency_choices(),
        validators=[
            DataRequired(message="Seleziona il grado di urgenza")
        ],
        default=TicketUrgencyEnum.media.value,
        render_kw={"class": "form-check-input"}
    )
    
    # Submit
    submit = SubmitField(
        "Invia Richiesta",
        render_kw={"class": "btn btn-success btn-lg"}
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Lista dei dipartimenti ammessi
        allowed_departments = ['Coach', 'IT', 'Nutrizione', 'Psicologia', 'Sales']
        
        # Popola lista dipartimenti filtrata
        departments = db.session.query(Department).filter(
            Department.name.in_(allowed_departments)
        ).order_by(Department.name).all()
        
        self.department_id.choices = [
            (0, "-- Seleziona dipartimento --")
        ] + [
            (d.id, d.name) for d in departments
        ]
    
    def validate_department_id(self, field):
        """Valida che il dipartimento esista e sia valido."""
        if field.data == 0:
            raise ValidationError("Seleziona un dipartimento valido")
        
        dept = Department.query.get(field.data)
        if not dept:
            raise ValidationError("Dipartimento non valido")


# ────────────────────────────────────────────────────────────────────
#  Form gestione ticket (autenticati)
# ────────────────────────────────────────────────────────────────────

class TicketStatusChangeForm(FlaskForm):
    """
    Form per cambio stato ticket con messaggio obbligatorio.
    """
    
    new_status = SelectField(
        "Nuovo stato",
        choices=_status_choices(),
        validators=[DataRequired()],
        render_kw={"class": "form-select"}
    )
    
    message = TextAreaField(
        "Messaggio di aggiornamento *",
        validators=[
            DataRequired(message="Il messaggio è obbligatorio per il cambio stato"),
            Length(min=10, message="Il messaggio deve essere almeno 10 caratteri")
        ],
        render_kw={
            "rows": 4,
            "placeholder": "Descrivi il motivo del cambio stato o fornisci aggiornamenti...",
            "class": "form-control"
        }
    )
    
    notify_requester = BooleanField(
        "Invia notifica email al richiedente",
        default=True,
        render_kw={"class": "form-check-input"}
    )
    
    submit = SubmitField(
        "Cambia Stato",
        render_kw={"class": "btn btn-primary"}
    )
    
    def __init__(self, current_status=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Rimuovi lo stato corrente dalle opzioni
        if current_status:
            self.new_status.choices = [
                choice for choice in self.new_status.choices
                if choice[0] != current_status.value
            ]


class TicketShareForm(FlaskForm):
    """
    Form per condividere ticket con altri dipartimenti.
    """
    
    department_ids = SelectMultipleField(
        "Condividi con i dipartimenti",
        coerce=int,
        validators=[
            DataRequired(message="Seleziona almeno un dipartimento")
        ],
        render_kw={
            "class": "form-select",
            "multiple": True,
            "size": 5
        }
    )
    
    message = TextAreaField(
        "Messaggio per i dipartimenti (opzionale)",
        validators=[Optional()],
        render_kw={
            "rows": 3,
            "placeholder": "Aggiungi un messaggio per i dipartimenti con cui condividi...",
            "class": "form-control"
        }
    )
    
    submit = SubmitField(
        "Condividi Ticket",
        render_kw={"class": "btn btn-primary"}
    )
    
    def __init__(self, ticket=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Popola dipartimenti disponibili, escludendo CEO, Co-Founder e Test
        query = db.session.query(Department).filter(
            ~Department.name.in_(['CEO', 'Co-Founder', 'Test'])
        ).order_by(Department.name)

        if ticket:
            # Escludi SOLO i dipartimenti già condivisi (NON il dipartimento principale)
            # Questo permette di condividere il ticket con membri del proprio dipartimento
            already_shared_ids = [d.id for d in ticket.shared_departments]
            if already_shared_ids:
                query = query.filter(~Department.id.in_(already_shared_ids))

        departments = query.all()
        
        # Unifica Consulenti Sales 1 e Consulenti Sales 2 in un'unica voce
        choices = []
        sales_team_added = False
        
        for d in departments:
            if d.name in ['Consulenti Sales 1', 'Consulenti Sales 2']:
                if not sales_team_added:
                    # Usa l'ID del primo Consulenti Sales trovato e rinomina in "Sales Team"
                    choices.append((d.id, 'Sales Team'))
                    sales_team_added = True
                # Salta il secondo Consulenti Sales
            else:
                choices.append((d.id, d.name))
        
        self.department_ids.choices = choices


class TicketAssignUsersForm(FlaskForm):
    """
    Form per assegnare utenti a un ticket.
    Solo head e admin possono usarlo.
    """
    
    assigned_users = SelectMultipleField(
        "Assegna a",
        coerce=int,
        validators=[Optional()],
        render_kw={"class": "form-select", "size": 6}
    )
    
    submit = SubmitField(
        "Assegna Utenti",
        render_kw={"class": "btn btn-primary"}
    )
    
    def __init__(self, assignable_users=None, current_assigned=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if assignable_users:
            self.assigned_users.choices = [
                (u.id, f"{u.full_name} ({u.department.name if u.department else 'N/A'})") 
                for u in assignable_users
            ]
            
        if current_assigned:
            self.assigned_users.data = [u.id for u in current_assigned]


class TicketCommentForm(FlaskForm):
    """
    Form per aggiungere note interne al ticket.
    """
    
    content = TextAreaField(
        "Nota interna",
        validators=[
            DataRequired(message="La nota non può essere vuota"),
            Length(min=3, message="La nota deve essere almeno 3 caratteri")
        ],
        render_kw={
            "rows": 3,
            "placeholder": "Aggiungi una nota interna...",
            "class": "form-control"
        }
    )
    
    # Rimuoviamo il campo is_internal - sarà sempre True
    
    submit = SubmitField(
        "Aggiungi Nota",
        render_kw={"class": "btn btn-primary"}
    )


class TicketFilterForm(FlaskForm):
    """
    Form per filtrare la lista ticket nella dashboard.
    """
    
    status = SelectField(
        "Stato",
        choices=[("", "Tutti gli stati")] + _status_choices(),
        validators=[Optional()],
        render_kw={"class": "form-select form-select-sm"}
    )
    
    urgency = SelectField(
        "Urgenza",
        choices=[("", "Tutte le urgenze")] + _urgency_choices(),
        validators=[Optional()],
        render_kw={"class": "form-select form-select-sm"}
    )

    # Categoria (solo per admin e membri dept 13)
    category = SelectField(
        "Categoria",
        choices=[("", "Tutte le categorie")] + _category_choices(),
        validators=[Optional()],
        render_kw={"class": "form-select form-select-sm"}
    )

    department_id = SelectField(
        "Dipartimento",
        coerce=lambda x: int(x) if x and x != '' else None,
        choices=[],
        validators=[Optional()],
        render_kw={"class": "form-select form-select-sm"}
    )
    
    search = StringField(
        "Cerca",
        validators=[Optional()],
        render_kw={
            "placeholder": "Cerca per numero, titolo, email...",
            "class": "form-control form-control-sm"
        }
    )
    
    date_from = DateTimeField(
        "Da data",
        validators=[Optional()],
        format="%Y-%m-%d",
        render_kw={"class": "form-control form-control-sm", "type": "date"}
    )
    
    date_to = DateTimeField(
        "A data",
        validators=[Optional()],
        format="%Y-%m-%d",
        render_kw={"class": "form-control form-control-sm", "type": "date"}
    )
    
    include_closed = BooleanField(
        "Includi ticket chiusi",
        default=False,
        render_kw={"class": "form-check-input"}
    )
    
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Popola dipartimenti in base ai permessi utente
        if user and user.is_admin:
            # Admin vede tutti i dipartimenti tranne CEO, Co-Founder e Test
            departments = db.session.query(Department).filter(
                ~Department.name.in_(['CEO', 'Co-Founder', 'Test'])
            ).order_by(Department.name).all()
            self.department_id.choices = [
                (None, "Tutti i dipartimenti")
            ] + [
                (d.id, d.name) for d in departments
            ]
        elif user and user.department:
            # User normale vede solo il suo dipartimento
            self.department_id.choices = [
                (user.department_id, user.department.name)
            ]
            self.department_id.data = user.department_id
            # Disabilita il campo
            self.department_id.render_kw['disabled'] = True


class TicketMessageForm(FlaskForm):
    """Form per inviare un messaggio nella chat del ticket."""
    
    content = TextAreaField(
        "Messaggio",
        validators=[
            DataRequired(message="Il messaggio non può essere vuoto"),
            Length(min=1, max=2000, message="Il messaggio deve essere tra 1 e 2000 caratteri")
        ],
        render_kw={
            "class": "form-control",
            "rows": 3,
            "placeholder": "Scrivi il tuo messaggio..."
        }
    )
    
    submit = SubmitField(
        "Invia Messaggio",
        render_kw={"class": "btn btn-info"}
    )