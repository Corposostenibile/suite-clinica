"""
Forms per la gestione delle Novità.
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, BooleanField, SelectField, DateTimeField, SelectMultipleField
from wtforms.validators import DataRequired, Length, Optional
from wtforms.widgets import ListWidget, CheckboxInput
from datetime import datetime


class MultiCheckboxField(SelectMultipleField):
    """
    Campo custom per multi-select con checkbox invece di <select multiple>.
    """
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


class NewsForm(FlaskForm):
    """Form per creare/modificare una novità."""

    title = StringField(
        'Titolo',
        validators=[DataRequired(message="Il titolo è obbligatorio"), Length(max=200)],
        render_kw={"placeholder": "Es: Nuova funzionalità: Gestione Ordini Professionali"}
    )

    summary = StringField(
        'Sommario',
        validators=[Optional(), Length(max=500)],
        render_kw={"placeholder": "Breve descrizione della novità (opzionale)"}
    )

    content = TextAreaField(
        'Contenuto',
        validators=[DataRequired(message="Il contenuto è obbligatorio")],
        render_kw={"rows": 10, "placeholder": "Scrivi qui il contenuto completo della novità..."}
    )

    # DEPRECATED: Mantenuto per retrocompatibilità durante migrazione
    category = SelectField(
        'Categoria (Vecchio sistema)',
        choices=[
            ('', 'Seleziona categoria'),
            ('feature', '🚀 Nuova Funzionalità'),
            ('improvement', '✨ Miglioramento'),
            ('bugfix', '🐛 Correzione Bug'),
            ('announcement', '📢 Annuncio'),
            ('maintenance', '🔧 Manutenzione'),
        ],
        validators=[Optional()],
        render_kw={"style": "display:none;"}  # Nascosto, usato solo internamente
    )

    # Nuovo campo multi-select per categorie
    categories = MultiCheckboxField(
        'Categorie',
        choices=[],  # Popolato dinamicamente nel route
        coerce=int,
        validators=[Optional()]
    )

    cover_image = FileField(
        'Immagine di Copertina',
        validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Solo immagini (JPG, PNG, GIF, WEBP)!')]
    )

    is_published = BooleanField(
        'Pubblica immediatamente',
        default=True
    )
