"""
Form per i Report Settimanali
=============================

Form multi-step per la compilazione dei report settimanali.
"""
from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Length, Optional


class WeeklyReportStep1Form(FlaskForm):
    """Step 1: Welcome - Solo visualizzazione, nessun campo."""
    submit = SubmitField("Inizia")


class WeeklyReportStep2Form(FlaskForm):
    """Step 2: OKR Dipartimento."""
    department_reflection = TextAreaField(
        "Cosa ha fatto il mio dipartimento per avvicinarsi a questi obiettivi?",
        validators=[
            DataRequired(message="Questo campo è obbligatorio"),
            Length(min=10, message="Inserisci almeno 10 caratteri")
        ],
        render_kw={
            "placeholder": "Descrivi le attività e i progressi del tuo dipartimento verso gli obiettivi...",
            "rows": 4,
            "class": "form-control"
        }
    )
    submit = SubmitField("Continua")


class WeeklyReportStep2UnifiedForm(FlaskForm):
    """Step 2 Unificato: OKR e Azioni - Per dipartimenti normali (6 step)."""
    unified_reflection = TextAreaField(
        "Quali azioni hai intrapreso?",
        validators=[
            DataRequired(message="Questo campo è obbligatorio"),
            Length(min=10, message="Inserisci almeno 10 caratteri")
        ],
        render_kw={
            "placeholder": "Descrivi le azioni concrete che hai intrapreso questa settimana...",
            "rows": 6,
            "class": "form-control"
        }
    )
    submit = SubmitField("Continua")


class WeeklyReportStep3Form(FlaskForm):
    """Step 3: OKR Personali."""
    personal_reflection = TextAreaField(
        "Cosa ho fatto io per avvicinarci a questo obiettivo della nostra azienda?",
        validators=[
            DataRequired(message="Questo campo è obbligatorio"),
            Length(min=10, message="Inserisci almeno 10 caratteri")
        ],
        render_kw={
            "placeholder": "Descrivi il tuo contributo personale agli obiettivi aziendali...",
            "rows": 4,
            "class": "form-control"
        }
    )
    submit = SubmitField("Continua")


class WeeklyReportStep4Form(FlaskForm):
    """Step 4: Vittoria settimanale."""
    weekly_victory = TextAreaField(
        "Qual è stata la tua più grande vittoria lavorativa questa settimana?",
        validators=[
            DataRequired(message="Questo campo è obbligatorio"),
            Length(min=10, message="Inserisci almeno 10 caratteri")
        ],
        render_kw={
            "placeholder": "Descrivi il tuo successo più importante di questa settimana...",
            "rows": 5,
            "class": "form-control"
        }
    )
    submit = SubmitField("Continua")


class WeeklyReportStep5Form(FlaskForm):
    """Step 5: Azioni da migliorare."""
    areas_to_improve = TextAreaField(
        "Su quali azioni quotidiane ti senti indietro, o sai di poter far meglio?",
        validators=[
            DataRequired(message="Questo campo è obbligatorio"),
            Length(min=10, message="Inserisci almeno 10 caratteri")
        ],
        render_kw={
            "placeholder": "Identifica le aree dove puoi migliorare...",
            "rows": 5,
            "class": "form-control"
        }
    )
    submit = SubmitField("Continua")


class WeeklyReportStep6Form(FlaskForm):
    """Step 6: Ostacolo principale."""
    main_obstacle = TextAreaField(
        "Qual è il più grande ostacolo lavorativo che stai affrontando?",
        validators=[
            DataRequired(message="Questo campo è obbligatorio"),
            Length(min=10, message="Inserisci almeno 10 caratteri")
        ],
        render_kw={
            "placeholder": "Descrivi la sfida principale che stai affrontando...",
            "rows": 5,
            "class": "form-control"
        }
    )
    submit = SubmitField("Continua")


class WeeklyReportStep6IdeasForm(FlaskForm):
    """Step 6: Idee (facoltativo) - Per dipartimenti normali nel flusso a 6 step."""
    ideas = TextAreaField(
        "Quali idee hai che potremmo implementare?",
        validators=[
            Optional()
        ],
        render_kw={
            "placeholder": "Condividi le tue idee per migliorare l'azienda (facoltativo)...",
            "rows": 5,
            "class": "form-control"
        }
    )
    submit = SubmitField("Completa Report")


class WeeklyReportStep7Form(FlaskForm):
    """Step 7: Idee (facoltativo) - Legacy per compatibilità."""
    ideas = TextAreaField(
        "Quali idee hai che potremmo implementare?",
        validators=[
            Optional()
        ],
        render_kw={
            "placeholder": "Condividi le tue idee per migliorare l'azienda (facoltativo)...",
            "rows": 5,
            "class": "form-control"
        }
    )
    submit = SubmitField("Completa Report")


class WeeklyReportCompleteForm(FlaskForm):
    """Form completo per modifica report esistente."""
    department_reflection = TextAreaField(
        "Riflessione sugli OKR del dipartimento",
        validators=[
            Optional()
        ],
        render_kw={"rows": 4, "class": "form-control"}
    )
    
    personal_reflection = TextAreaField(
        "Riflessione sui tuoi OKR personali",
        validators=[
            Optional()
        ],
        render_kw={"rows": 4, "class": "form-control"}
    )
    
    weekly_victory = TextAreaField(
        "Vittoria settimanale",
        validators=[
            DataRequired(message="Questo campo è obbligatorio"),
            Length(min=10, message="Inserisci almeno 10 caratteri")
        ],
        render_kw={"rows": 4, "class": "form-control"}
    )
    
    areas_to_improve = TextAreaField(
        "Azioni da migliorare",
        validators=[
            DataRequired(message="Questo campo è obbligatorio"),
            Length(min=10, message="Inserisci almeno 10 caratteri")
        ],
        render_kw={"rows": 4, "class": "form-control"}
    )
    
    main_obstacle = TextAreaField(
        "Ostacolo principale",
        validators=[
            DataRequired(message="Questo campo è obbligatorio"),
            Length(min=10, message="Inserisci almeno 10 caratteri")
        ],
        render_kw={"rows": 4, "class": "form-control"}
    )
    
    ideas = TextAreaField(
        "Idee (facoltativo)",
        validators=[
            Optional()
        ],
        render_kw={"rows": 4, "class": "form-control"}
    )
    
    submit = SubmitField("Salva Modifiche")


# Form specifici per i dipartimenti Sales
class SalesReportStep1Form(FlaskForm):
    """Step 1: Welcome per Sales - Solo visualizzazione."""
    submit = SubmitField("Inizia Report Mensile")


class SalesReportStep2Form(FlaskForm):
    """Step 2: Domande principali per Sales."""
    main_obstacle = TextAreaField(
        "Qual è il più grande ostacolo lavorativo/problema che stai affrontando?",
        validators=[
            DataRequired(message="Questo campo è obbligatorio"),
            Length(min=10, message="Inserisci almeno 10 caratteri")
        ],
        render_kw={
            "placeholder": "Descrivi l'ostacolo o problema principale che stai affrontando nel tuo lavoro...",
            "rows": 5,
            "class": "form-control"
        }
    )
    
    obstacle_suggestions = TextAreaField(
        "Hai idee o suggerimenti per sormontare l'ostacolo/il problema?",
        validators=[
            DataRequired(message="Questo campo è obbligatorio"),
            Length(min=10, message="Inserisci almeno 10 caratteri")
        ],
        render_kw={
            "placeholder": "Condividi le tue idee per superare l'ostacolo descritto sopra...",
            "rows": 4,
            "class": "form-control"
        }
    )
    
    work_improvements = TextAreaField(
        "Quali punti (più deboli e non) sul tuo lavoro vorresti migliorare?",
        validators=[
            DataRequired(message="Questo campo è obbligatorio"),
            Length(min=10, message="Inserisci almeno 10 caratteri")
        ],
        render_kw={
            "placeholder": "Identifica gli aspetti del tuo lavoro che vorresti migliorare, sia punti deboli che aree di crescita...",
            "rows": 4,
            "class": "form-control"
        }
    )
    submit = SubmitField("Continua")


class SalesReportStep3Form(FlaskForm):
    """Step 3: Idee generali per Sales."""
    ideas = TextAreaField(
        "Quali idee hai che potremmo implementare in azienda?",
        validators=[
            Optional()
        ],
        render_kw={
            "placeholder": "Condividi le tue idee per migliorare l'azienda in generale (facoltativo)...",
            "rows": 5,
            "class": "form-control"
        }
    )
    submit = SubmitField("Completa Report Mensile")