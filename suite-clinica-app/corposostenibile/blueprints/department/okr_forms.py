"""
department/okr_forms.py
=======================

Flask-WTF forms per la gestione OKR dipartimentali.
"""

from __future__ import annotations

from datetime import date
from typing import List, Tuple

from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    DecimalField,
    FieldList,
    FormField,
    HiddenField,
    IntegerField,
    RadioField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Length,
    NumberRange,
    Optional,
    ValidationError,
)

from corposostenibile.extensions import db
from corposostenibile.models import (
    Department,
    OKRPeriodEnum,
    OKRStatusEnum,
    User,
)


# ────────────────────────────────────────────────────────────────────
#  Sub-form per Key Results
# ────────────────────────────────────────────────────────────────────
class DepartmentKeyResultForm(FlaskForm):
    """Sub-form per un singolo Key Result dipartimentale."""
    
    class Meta:
        csrf = False  # Disabilita CSRF per sub-form
    
    # Hidden field per tracking in edit
    id = HiddenField()
    
    title = StringField(
        "Key Result",
        validators=[DataRequired()],
        render_kw={"placeholder": "es: Aumentare i clienti attivi del 30%"}
    )
    
    # Per ordinamento
    order_index = HiddenField()


# ────────────────────────────────────────────────────────────────────
#  Form principale Obiettivo Dipartimento
# ────────────────────────────────────────────────────────────────────
class DepartmentObjectiveForm(FlaskForm):
    """Form principale per creare/modificare un Obiettivo OKR dipartimentale."""
    
    title = StringField(
        "Titolo",
        validators=[DataRequired()],
        render_kw={"placeholder": "es: Migliorare l'efficienza operativa del reparto"}
    )
    
    periods = SelectMultipleField(
        "Trimestri",
        choices=[
            ("q1", "Trimestre 1"),
            ("q2", "Trimestre 2"),
            ("q3", "Trimestre 3"),
            ("q4", "Trimestre 4"),
        ],
        validators=[DataRequired(message="Seleziona almeno un trimestre")],
        default=[],  # Default vuoto per evitare NoneType
        render_kw={"class": "form-check-input"}
    )
    
    okr_type = RadioField(
        "Tipo di OKR",
        choices=[
            ("concreto", "Concreto"),
            ("aspirazionale", "Aspirazionale"),
        ],
        validators=[DataRequired()],
        default="concreto"
    )
    
    # FieldList per Key Results dinamici
    key_results = FieldList(
        FormField(DepartmentKeyResultForm),
        min_entries=1,
        max_entries=10  # Max 10 KR per obiettivo dipartimentale
    )
    
    submit = SubmitField("Salva Obiettivo")
    
    def __init__(self, *args, department: Department = None, **kwargs):
        """
        Inizializza il form.
        
        Args:
            department: Il dipartimento per cui si sta creando l'obiettivo
        """
        super().__init__(*args, **kwargs)
    
    def validate_key_results(self, field):
        """Verifica che ci sia almeno un key result valido."""
        valid_count = 0
        for kr in field.data:
            if kr and kr.get('title'):
                valid_count += 1
        
        if valid_count == 0:
            raise ValidationError("Devi definire almeno un Key Result.")


# ────────────────────────────────────────────────────────────────────
#  Form Update Settimanale
# ────────────────────────────────────────────────────────────────────
class DepartmentWeeklyUpdateForm(FlaskForm):
    """Form per l'aggiornamento settimanale degli OKR dipartimentali."""
    
    notes = TextAreaField(
        "Note settimanali del team",
        validators=[Optional()],
        render_kw={
            "rows": 3,
            "placeholder": "Cosa è successo questa settimana nel dipartimento?"
        }
    )
    
    achievements = TextAreaField(
        "Risultati ottenuti dal team",
        validators=[Optional()],
        render_kw={
            "rows": 3,
            "placeholder": "Quali traguardi ha raggiunto il team?"
        }
    )
    
    blockers = TextAreaField(
        "Ostacoli/Problemi del dipartimento",
        validators=[Optional()],
        render_kw={
            "rows": 3,
            "placeholder": "Cosa sta bloccando il progresso del team?"
        }
    )
    
    next_steps = TextAreaField(
        "Prossimi passi",
        validators=[Optional()],
        render_kw={
            "rows": 3,
            "placeholder": "Cosa farà il team la prossima settimana?"
        }
    )
    
    # Campi specifici per dipartimento
    team_morale = SelectField(
        "Morale del team",
        choices=[
            ("", "-- Seleziona --"),
            ("1", "😞 Molto basso"),
            ("2", "😔 Basso"),
            ("3", "😐 Neutrale"),
            ("4", "😊 Alto"),
            ("5", "🚀 Molto alto"),
        ],
        coerce=lambda x: int(x) if x else None
    )
    
    confidence_level = SelectField(
        "Livello di fiducia nel raggiungimento",
        choices=[
            ("", "-- Seleziona --"),
            ("1", "😟 Molto preoccupato"),
            ("2", "😕 Preoccupato"),
            ("3", "😐 Neutrale"),
            ("4", "😊 Fiducioso"),
            ("5", "😎 Molto fiducioso"),
        ],
        coerce=lambda x: int(x) if x else None
    )
    
    # Metriche aggiuntive del team (opzionali)
    tickets_completed = IntegerField(
        "Ticket completati",
        validators=[Optional(), NumberRange(min=0)],
        render_kw={"placeholder": "0"}
    )
    
    team_hours_saved = DecimalField(
        "Ore risparmiate dal team",
        validators=[Optional(), NumberRange(min=0)],
        render_kw={"placeholder": "0.0"}
    )
    
    customer_satisfaction = DecimalField(
        "Soddisfazione clienti (%)",
        validators=[Optional(), NumberRange(min=0, max=100)],
        render_kw={"placeholder": "0-100"}
    )
    
    submit = SubmitField("Salva Aggiornamento")


# ────────────────────────────────────────────────────────────────────
#  Form Update Rapido Progress
# ────────────────────────────────────────────────────────────────────
class DepartmentQuickProgressForm(FlaskForm):
    """Form per aggiornamento rapido del progresso di un Key Result dipartimentale."""
    
    current_value = DecimalField(
        "Valore Attuale",
        validators=[DataRequired()]
    )
    
    notes = TextAreaField(
        "Note (opzionale)",
        validators=[Optional(), Length(max=500)],
        render_kw={
            "rows": 2,
            "placeholder": "Breve nota sull'aggiornamento..."
        }
    )
    
    submit = SubmitField("Aggiorna")


# ────────────────────────────────────────────────────────────────────
#  Form per collegare OKR personali (opzionale)
# ────────────────────────────────────────────────────────────────────
class LinkPersonalOKRForm(FlaskForm):
    """Form per collegare OKR personali dei membri agli obiettivi del dipartimento."""
    
    personal_objective_ids = SelectField(
        "Obiettivi personali collegati",
        validators=[Optional()],
        coerce=int,
        choices=[],  # Popolato dinamicamente
        render_kw={
            "multiple": True,
            "class": "form-select select2",
            "data-placeholder": "Seleziona obiettivi personali correlati..."
        }
    )
    
    submit = SubmitField("Collega Obiettivi")
    
    def __init__(self, *args, department: Department = None, **kwargs):
        """Inizializza con gli obiettivi personali dei membri del dipartimento."""
        super().__init__(*args, **kwargs)
        
        if department:
            # Recupera tutti gli obiettivi attivi dei membri del dipartimento
            from corposostenibile.models import Objective, OKRStatusEnum
            
            # FIX: Query active members properly
            active_members = db.session.query(User).filter(
                User.department_id == department.id,
                User.is_active.is_(True)
            ).all()
            
            choices = []
            for member in active_members:
                member_objectives = member.objectives.filter(
                    Objective.status == OKRStatusEnum.active
                ).all()
                
                if member_objectives:
                    for obj in member_objectives:
                        choices.append((
                            obj.id,
                            f"{member.full_name}: {obj.title}"
                        ))
            
            self.personal_objective_ids.choices = choices