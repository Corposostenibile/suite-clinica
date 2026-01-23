"""
WTForms per il modulo Nutrition
"""

from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, FloatField, IntegerField,
    DateField, SelectField, BooleanField, FieldList,
    FormField, HiddenField, SelectMultipleField
)
from wtforms.validators import DataRequired, Optional, NumberRange, Length
from datetime import date, timedelta

from corposostenibile.models import (
    NutritionalGoalEnum, ActivityLevelEnum, GenereEnum,
    MealTypeEnum, FoodUnitEnum, FoodCategory
)


class NutritionalProfileForm(FlaskForm):
    """Form per profilo nutrizionale cliente."""
    nutritional_goal = SelectField(
        'Obiettivo',
        choices=[(g.value, g.value.replace('_', ' ').title()) for g in NutritionalGoalEnum],
        validators=[DataRequired()]
    )
    target_weight = FloatField(
        'Peso obiettivo (kg)',
        validators=[Optional(), NumberRange(min=30, max=300)]
    )
    target_date = DateField(
        'Data obiettivo',
        validators=[Optional()]
    )
    activity_level = SelectField(
        'Livello attività',
        choices=[(a.value, a.value.replace('_', ' ').title()) for a in ActivityLevelEnum],
        validators=[DataRequired()]
    )
    training_frequency = IntegerField(
        'Allenamenti settimanali',
        validators=[Optional(), NumberRange(min=0, max=7)]
    )
    training_type = StringField(
        'Tipo allenamento',
        validators=[Optional(), Length(max=255)]
    )
    gender = SelectField(
        'Genere',
        choices=[(g.value, g.value.title()) for g in GenereEnum],
        validators=[DataRequired()]
    )
    medical_conditions = TextAreaField(
        'Condizioni mediche',
        validators=[Optional()]
    )
    medications = TextAreaField(
        'Farmaci assunti',
        validators=[Optional()]
    )
    supplements = TextAreaField(
        'Integratori',
        validators=[Optional()]
    )


class HealthAssessmentForm(FlaskForm):
    """Form per anamnesi salute."""
    # Stile di vita
    sleep_hours = FloatField(
        'Ore di sonno medie',
        validators=[Optional(), NumberRange(min=0, max=24)]
    )
    sleep_quality = SelectField(
        'Qualità del sonno',
        choices=[
            ('scarsa', 'Scarsa'),
            ('sufficiente', 'Sufficiente'),
            ('buona', 'Buona'),
            ('ottima', 'Ottima')
        ],
        validators=[Optional()]
    )
    stress_level = IntegerField(
        'Livello di stress (1-10)',
        validators=[Optional(), NumberRange(min=1, max=10)]
    )
    smoking = BooleanField('Fumatore')
    alcohol_frequency = SelectField(
        'Consumo alcol',
        choices=[
            ('mai', 'Mai'),
            ('occasionale', 'Occasionale'),
            ('moderato', 'Moderato'),
            ('frequente', 'Frequente')
        ],
        validators=[Optional()]
    )
    
    # Problematiche
    digestive_issues = TextAreaField(
        'Problemi digestivi',
        validators=[Optional()]
    )
    energy_levels = SelectField(
        'Livelli di energia',
        choices=[
            ('basso', 'Basso'),
            ('normale', 'Normale'),
            ('alto', 'Alto')
        ],
        validators=[Optional()]
    )
    
    # Anamnesi familiare (gestito via JavaScript come JSON)
    family_diabetes = BooleanField('Diabete')
    family_hypertension = BooleanField('Ipertensione')
    family_heart_disease = BooleanField('Malattie cardiache')
    family_obesity = BooleanField('Obesità')
    family_cancer = BooleanField('Tumori')
    family_other = StringField('Altro', validators=[Optional()])
    
    notes = TextAreaField(
        'Note aggiuntive',
        validators=[Optional()]
    )


class BiometricDataForm(FlaskForm):
    """Form per dati biometrici."""
    measurement_date = DateField(
        'Data misurazione',
        default=date.today,
        validators=[DataRequired()]
    )
    weight = FloatField(
        'Peso (kg)',
        validators=[DataRequired(), NumberRange(min=30, max=300)]
    )
    height = FloatField(
        'Altezza (cm)',
        validators=[DataRequired(), NumberRange(min=100, max=250)]
    )
    
    # Circonferenze
    waist = FloatField(
        'Vita (cm)',
        validators=[Optional(), NumberRange(min=40, max=200)]
    )
    hips = FloatField(
        'Fianchi (cm)',
        validators=[Optional(), NumberRange(min=40, max=200)]
    )
    chest = FloatField(
        'Torace (cm)',
        validators=[Optional(), NumberRange(min=40, max=200)]
    )
    arm_left = FloatField(
        'Braccio sx (cm)',
        validators=[Optional(), NumberRange(min=10, max=60)]
    )
    arm_right = FloatField(
        'Braccio dx (cm)',
        validators=[Optional(), NumberRange(min=10, max=60)]
    )
    thigh_left = FloatField(
        'Coscia sx (cm)',
        validators=[Optional(), NumberRange(min=20, max=100)]
    )
    thigh_right = FloatField(
        'Coscia dx (cm)',
        validators=[Optional(), NumberRange(min=20, max=100)]
    )
    
    # Composizione corporea
    body_fat_percentage = FloatField(
        'Massa grassa (%)',
        validators=[Optional(), NumberRange(min=3, max=60)]
    )
    muscle_mass = FloatField(
        'Massa muscolare (kg)',
        validators=[Optional(), NumberRange(min=10, max=150)]
    )
    bone_mass = FloatField(
        'Massa ossea (kg)',
        validators=[Optional(), NumberRange(min=1, max=10)]
    )
    water_percentage = FloatField(
        'Acqua corporea (%)',
        validators=[Optional(), NumberRange(min=30, max=80)]
    )
    
    # Parametri vitali
    blood_pressure_sys = IntegerField(
        'Pressione sistolica',
        validators=[Optional(), NumberRange(min=60, max=250)]
    )
    blood_pressure_dia = IntegerField(
        'Pressione diastolica',
        validators=[Optional(), NumberRange(min=40, max=150)]
    )
    resting_heart_rate = IntegerField(
        'Frequenza cardiaca a riposo',
        validators=[Optional(), NumberRange(min=30, max=150)]
    )
    
    notes = TextAreaField(
        'Note',
        validators=[Optional()]
    )


class MealPlanForm(FlaskForm):
    """Form per creazione piano alimentare."""
    name = StringField(
        'Nome piano',
        validators=[DataRequired(), Length(max=255)]
    )
    start_date = DateField(
        'Data inizio',
        default=date.today,
        validators=[DataRequired()]
    )
    end_date = DateField(
        'Data fine',
        default=lambda: date.today() + timedelta(days=30),
        validators=[DataRequired()]
    )
    
    # Target nutrizionali
    target_calories = FloatField(
        'Calorie target',
        validators=[Optional(), NumberRange(min=800, max=5000)]
    )
    target_proteins = FloatField(
        'Proteine (g)',
        validators=[Optional(), NumberRange(min=0, max=500)]
    )
    target_carbohydrates = FloatField(
        'Carboidrati (g)',
        validators=[Optional(), NumberRange(min=0, max=800)]
    )
    target_fats = FloatField(
        'Grassi (g)',
        validators=[Optional(), NumberRange(min=0, max=300)]
    )
    
    notes = TextAreaField(
        'Note',
        validators=[Optional()]
    )


class RecipeForm(FlaskForm):
    """Form per creazione ricetta."""
    name = StringField(
        'Nome ricetta',
        validators=[DataRequired(), Length(max=255)]
    )
    description = TextAreaField(
        'Descrizione',
        validators=[Optional()]
    )
    preparation_time = IntegerField(
        'Tempo preparazione (min)',
        validators=[Optional(), NumberRange(min=0, max=480)]
    )
    cooking_time = IntegerField(
        'Tempo cottura (min)',
        validators=[Optional(), NumberRange(min=0, max=480)]
    )
    servings = IntegerField(
        'Porzioni',
        default=1,
        validators=[DataRequired(), NumberRange(min=1, max=50)]
    )
    difficulty = SelectField(
        'Difficoltà',
        choices=[
            ('facile', 'Facile'),
            ('medio', 'Medio'),
            ('difficile', 'Difficile')
        ],
        validators=[Optional()]
    )
    instructions = TextAreaField(
        'Istruzioni',
        validators=[Optional()]
    )
    notes = TextAreaField(
        'Note',
        validators=[Optional()]
    )
    tags = StringField(
        'Tags (separati da virgola)',
        validators=[Optional()]
    )
    is_public = BooleanField(
        'Ricetta pubblica'
    )


class FoodForm(FlaskForm):
    """Form per creazione alimento."""
    name = StringField(
        'Nome',
        validators=[DataRequired(), Length(max=255)]
    )
    brand = StringField(
        'Marca',
        validators=[Optional(), Length(max=100)]
    )
    barcode = StringField(
        'Codice a barre',
        validators=[Optional(), Length(max=50)]
    )
    category_id = SelectField(
        'Categoria',
        coerce=int,
        validators=[Optional()]
    )
    
    # Valori nutrizionali per 100g
    calories = FloatField(
        'Calorie (kcal)',
        validators=[DataRequired(), NumberRange(min=0, max=900)]
    )
    proteins = FloatField(
        'Proteine (g)',
        validators=[DataRequired(), NumberRange(min=0, max=100)]
    )
    carbohydrates = FloatField(
        'Carboidrati (g)',
        validators=[DataRequired(), NumberRange(min=0, max=100)]
    )
    fats = FloatField(
        'Grassi (g)',
        validators=[DataRequired(), NumberRange(min=0, max=100)]
    )
    fibers = FloatField(
        'Fibre (g)',
        validators=[Optional(), NumberRange(min=0, max=100)]
    )
    sugars = FloatField(
        'Zuccheri (g)',
        validators=[Optional(), NumberRange(min=0, max=100)]
    )
    saturated_fats = FloatField(
        'Grassi saturi (g)',
        validators=[Optional(), NumberRange(min=0, max=100)]
    )
    sodium = FloatField(
        'Sodio (mg)',
        validators=[Optional(), NumberRange(min=0, max=5000)]
    )


class NutritionNoteForm(FlaskForm):
    """Form per note nutrizionista."""
    content = TextAreaField(
        'Nota',
        validators=[DataRequired()]
    )
    is_private = BooleanField(
        'Nota privata (solo per nutrizionista)'
    )