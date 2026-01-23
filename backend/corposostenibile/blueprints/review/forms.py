"""
Form per il sistema di Review
"""

from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, SelectField, IntegerField,
    DateField, BooleanField, HiddenField, SubmitField
)
from wtforms.validators import DataRequired, Optional, Length, NumberRange
from datetime import date


class ReviewForm(FlaskForm):
    """Form per creare o modificare un training."""
    
    title = StringField(
        'Titolo Training',
        validators=[
            DataRequired(message="Il titolo è obbligatorio"),
            Length(min=3, max=200, message="Il titolo deve essere tra 3 e 200 caratteri")
        ],
        render_kw={
            "class": "form-control",
            "placeholder": "es. Training Mensile - Novembre 2024"
        }
    )
    
    review_type = SelectField(
        'Tipo di Training',
        choices=[
            ('settimanale', 'Settimanale'),
            ('mensile', 'Mensile'),
            ('progetto', 'Progetto'),
            ('miglioramento', 'Miglioramento')
        ],
        default='settimanale',
        validators=[DataRequired()],
        render_kw={"class": "form-select"}
    )
    
    content = TextAreaField(
        'Contenuto Training',
        validators=[
            DataRequired(message="Il contenuto è obbligatorio"),
            Length(min=10, message="La review deve contenere almeno 10 caratteri")
        ],
        render_kw={
            "class": "form-control",
            "rows": 6,
            "placeholder": "Scrivi qui la tua valutazione..."
        }
    )
    
    
    period_start = DateField(
        'Periodo - Dal',
        validators=[Optional()],
        format='%Y-%m-%d',
        render_kw={
            "class": "form-control",
            "type": "date"
        }
    )
    
    period_end = DateField(
        'Periodo - Al',
        validators=[Optional()],
        format='%Y-%m-%d',
        render_kw={
            "class": "form-control",
            "type": "date"
        }
    )
    
    strengths = TextAreaField(
        'Punti di Forza',
        validators=[Optional()],
        render_kw={
            "class": "form-control",
            "rows": 4,
            "placeholder": "Elenca i punti di forza osservati..."
        }
    )
    
    improvements = TextAreaField(
        'Aree di Miglioramento',
        validators=[Optional()],
        render_kw={
            "class": "form-control",
            "rows": 4,
            "placeholder": "Indica le aree che necessitano miglioramento..."
        }
    )
    
    goals = TextAreaField(
        'Obiettivi per il Prossimo Periodo',
        validators=[Optional()],
        render_kw={
            "class": "form-control",
            "rows": 4,
            "placeholder": "Definisci gli obiettivi da raggiungere..."
        }
    )
    
    is_private = BooleanField(
        'Training Privato (visibile solo ad admin e trainer)',
        default=False,
        render_kw={"class": "form-check-input"}
    )
    
    reviewee_id = HiddenField()
    
    submit = SubmitField(
        'Salva Training',
        render_kw={"class": "btn btn-primary"}
    )
    
    def validate_period_end(self, field):
        """Valida che la data di fine sia dopo la data di inizio."""
        if field.data and self.period_start.data:
            if field.data < self.period_start.data:
                raise ValueError("La data di fine deve essere successiva alla data di inizio")


class AcknowledgmentForm(FlaskForm):
    """Form per confermare la lettura di un training."""
    
    notes = TextAreaField(
        'Note (Opzionale)',
        validators=[Optional()],
        render_kw={
            "class": "form-control",
            "rows": 3,
            "placeholder": "Puoi aggiungere un commento o delle note..."
        }
    )
    
    confirm = BooleanField(
        'Confermo di aver letto e preso visione di questo training',
        validators=[DataRequired(message="Devi confermare la lettura")],
        render_kw={"class": "form-check-input"}
    )
    
    submit = SubmitField(
        'Conferma Lettura',
        render_kw={"class": "btn btn-success"}
    )


class ReviewFilterForm(FlaskForm):
    """Form per filtrare i training nella lista."""
    
    review_type = SelectField(
        'Tipo',
        choices=[
            ('all', 'Tutti i tipi'),
            ('settimanale', 'Settimanale'),
            ('mensile', 'Mensile'),
            ('progetto', 'Progetto'),
            ('miglioramento', 'Miglioramento')
        ],
        default='all',
        render_kw={"class": "form-select form-select-sm"}
    )
    
    status = SelectField(
        'Stato',
        choices=[
            ('all', 'Tutti'),
            ('acknowledged', 'Confermate'),
            ('pending', 'In attesa di conferma'),
            ('draft', 'Bozze')
        ],
        default='all',
        render_kw={"class": "form-select form-select-sm"}
    )
    
    period = SelectField(
        'Periodo',
        choices=[
            ('all', 'Tutto'),
            ('today', 'Oggi'),
            ('week', 'Ultima settimana'),
            ('month', 'Ultimo mese'),
            ('quarter', 'Ultimo trimestre'),
            ('year', 'Ultimo anno')
        ],
        default='all',
        render_kw={"class": "form-select form-select-sm"}
    )


class ReviewMessageForm(FlaskForm):
    """Form per inviare un messaggio nella chat di una review."""
    
    content = TextAreaField(
        'Messaggio',
        validators=[
            DataRequired(message="Il messaggio non può essere vuoto"),
            Length(min=1, max=5000, message="Il messaggio deve essere tra 1 e 5000 caratteri")
        ],
        render_kw={
            "class": "form-control",
            "rows": 3,
            "placeholder": "Scrivi il tuo messaggio...",
            "style": "resize: vertical;"
        }
    )
    
    submit = SubmitField(
        'Invia Messaggio',
        render_kw={"class": "btn btn-primary"}
    )


class ReviewRequestForm(FlaskForm):
    """Form per richiedere un training al responsabile."""

    recipient_id = SelectField(
        'Destinatario del Training',
        validators=[DataRequired(message="Seleziona un destinatario")],
        render_kw={"class": "form-select"}
    )

    subject = StringField(
        'Argomento del Training',
        validators=[
            DataRequired(message="L'argomento è obbligatorio"),
            Length(min=3, max=200, message="L'argomento deve essere tra 3 e 200 caratteri")
        ],
        render_kw={
            "class": "form-control",
            "placeholder": "es. Gestione del tempo, Comunicazione efficace, Obiettivi Q1..."
        }
    )

    description = TextAreaField(
        'Descrizione Dettagliata (Opzionale)',
        validators=[Optional()],
        render_kw={
            "class": "form-control",
            "rows": 4,
            "placeholder": "Spiega perché hai bisogno di questo training, quali aspetti vorresti approfondire..."
        }
    )

    priority = SelectField(
        'Priorità',
        choices=[
            ('low', '🟢 Bassa'),
            ('normal', '🟡 Normale'),
            ('high', '🟠 Alta'),
            ('urgent', '🔴 Urgente')
        ],
        default='normal',
        validators=[DataRequired()],
        render_kw={"class": "form-select"}
    )

    submit = SubmitField(
        'Invia Richiesta',
        render_kw={"class": "btn btn-success"}
    )


class ReviewRequestResponseForm(FlaskForm):
    """Form per rispondere a una richiesta di training."""
    
    action = SelectField(
        'Azione',
        choices=[
            ('accept', '✅ Accetta e Scrivi Training'),
            ('reject', '❌ Rifiuta Richiesta')
        ],
        validators=[DataRequired()],
        render_kw={"class": "form-select"}
    )
    
    response_notes = TextAreaField(
        'Note di Risposta',
        validators=[Optional()],
        render_kw={
            "class": "form-control",
            "rows": 3,
            "placeholder": "Aggiungi note sulla tua decisione (opzionale per accettazione, consigliato per rifiuto)..."
        }
    )
    
    submit = SubmitField(
        'Conferma',
        render_kw={"class": "btn btn-primary"}
    )