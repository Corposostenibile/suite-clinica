"""
team.okr_forms
==============

Forms per la gestione OKR (Objectives and Key Results) personali.
Allineati con la struttura degli OKR dipartimentali.
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
    OKRPeriodEnum,
    OKRStatusEnum,
    User,
)


class KeyResultForm(FlaskForm):
    """Sub-form per un singolo Key Result personale."""
    
    class Meta:
        csrf = False  # Disabilita CSRF per sub-form
    
    # Hidden field per tracking in edit
    id = HiddenField()
    
    title = StringField(
        "Key Result",
        validators=[DataRequired()],
        render_kw={"placeholder": "es: Completare 3 certificazioni professionali"}
    )
    
    # Per ordinamento
    order_index = HiddenField()


class ObjectiveForm(FlaskForm):
    """Form principale per creare/modificare un Obiettivo OKR personale."""
    
    title = StringField(
        "Titolo",
        validators=[DataRequired()],
        render_kw={"placeholder": "es: Migliorare le mie competenze tecniche"}
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
        FormField(KeyResultForm),
        min_entries=1,
        max_entries=10  # Max 10 KR per obiettivo - allineato con department
    )
    
    submit = SubmitField("Salva Obiettivo")
    
    def __init__(self, *args, user: User = None, **kwargs):
        """
        Inizializza il form.
        
        Args:
            user: L'utente per cui si sta creando l'obiettivo
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