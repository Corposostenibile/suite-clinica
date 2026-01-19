"""
Knowledge Base Forms
====================
Forms per la gestione della documentazione.
"""

from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, SelectField, BooleanField,
    IntegerField, FileField, HiddenField, FieldList, FormField
)
from wtforms.validators import DataRequired, Optional, Length, URL, NumberRange
from flask_wtf.file import FileAllowed, FileSize

from corposostenibile.models import KBDocumentStatusEnum, KBVisibilityEnum


class ArticleForm(FlaskForm):
    """Form per creazione/modifica articolo."""
    
    title = StringField(
        'Titolo',
        validators=[
            DataRequired(message='Il titolo è obbligatorio'),
            Length(min=3, max=255, message='Il titolo deve essere tra 3 e 255 caratteri')
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': 'Inserisci il titolo dell\'articolo...'
        }
    )
    
    summary = TextAreaField(
        'Riassunto',
        validators=[
            Optional(),
            Length(max=500, message='Il riassunto non può superare i 500 caratteri')
        ],
        render_kw={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Breve descrizione dell\'articolo (opzionale)...'
        }
    )
    
    content = TextAreaField(
        'Contenuto',
        validators=[
            DataRequired(message='Il contenuto è obbligatorio')
        ],
        render_kw={
            'class': 'form-control editor-wysiwyg',
            'rows': 20
        }
    )
    
    category_id = SelectField(
        'Categoria',
        coerce=lambda x: int(x) if x and x != '' else None,
        validators=[Optional()],
        render_kw={'class': 'form-select'}
    )
    
    status = SelectField(
        'Stato',
        choices=[
            (KBDocumentStatusEnum.draft.value, 'Bozza'),
            (KBDocumentStatusEnum.published.value, 'Pubblicato'),
            (KBDocumentStatusEnum.archived.value, 'Archiviato')
        ],
        default=KBDocumentStatusEnum.draft.value,
        validators=[DataRequired()],
        render_kw={'class': 'form-select'}
    )
    
    visibility = SelectField(
        'Visibilità',
        choices=[
            (KBVisibilityEnum.department.value, '🏢 Solo Dipartimento'),
            (KBVisibilityEnum.company.value, '🌍 Tutta l\'Azienda'),
            (KBVisibilityEnum.only_heads.value, '🔒 Solo Responsabili')
        ],
        default=KBVisibilityEnum.department.value,
        validators=[DataRequired()],
        render_kw={'class': 'form-select'}
    )
    
    meta_keywords = StringField(
        'Parole chiave SEO',
        validators=[
            Optional(),
            Length(max=255)
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': 'parola1, parola2, parola3...'
        }
    )
    
    tags = StringField(
        'Tags',
        validators=[Optional()],
        render_kw={
            'class': 'form-control',
            'placeholder': 'tag1, tag2, tag3...',
            'data-role': 'tagsinput'
        }
    )
    
    template_type = SelectField(
        'Tipo Template',
        choices=[
            ('standard', 'Standard'),
            ('faq', 'FAQ'),
            ('guide', 'Guida Step-by-Step'),
            ('policy', 'Policy/Procedura'),
            ('checklist', 'Checklist')
        ],
        default='standard',
        render_kw={'class': 'form-select'}
    )
    
    is_featured = BooleanField(
        'In evidenza',
        render_kw={'class': 'form-check-input'}
    )
    
    is_pinned = BooleanField(
        'Fissa in alto',
        render_kw={'class': 'form-check-input'}
    )
    
    allow_comments = BooleanField(
        'Permetti commenti',
        default=True,
        render_kw={'class': 'form-check-input'}
    )
    
    require_acknowledgment = BooleanField(
        'Richiedi conferma lettura',
        render_kw={'class': 'form-check-input'}
    )


class CategoryForm(FlaskForm):
    """Form per creazione/modifica categoria."""
    
    name = StringField(
        'Nome Categoria',
        validators=[
            DataRequired(message='Il nome è obbligatorio'),
            Length(min=2, max=100)
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': 'Es: Procedure Operative'
        }
    )
    
    description = TextAreaField(
        'Descrizione',
        validators=[Optional()],
        render_kw={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Descrizione della categoria (opzionale)'
        }
    )
    
    parent_id = SelectField(
        'Categoria Padre',
        coerce=lambda x: int(x) if x and x != '' else None,
        validators=[Optional()],
        render_kw={'class': 'form-select'}
    )
    
    icon = StringField(
        'Icona',
        validators=[
            Optional(),
            Length(max=50)
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': 'fa-folder (FontAwesome class)'
        }
    )
    
    color = StringField(
        'Colore',
        validators=[
            Optional(),
            Length(max=7)
        ],
        render_kw={
            'class': 'form-control color-picker',
            'placeholder': '#3788d8'
        }
    )
    
    order_index = IntegerField(
        'Ordine',
        default=0,
        validators=[
            NumberRange(min=0, max=9999)
        ],
        render_kw={
            'class': 'form-control',
            'placeholder': '0'
        }
    )
    
    is_active = BooleanField(
        'Attiva',
        default=True,
        render_kw={'class': 'form-check-input'}
    )


class SearchForm(FlaskForm):
    """Form di ricerca."""
    
    q = StringField(
        'Cerca',
        validators=[
            DataRequired(message='Inserisci un termine di ricerca'),
            Length(min=2, message='Almeno 2 caratteri')
        ],
        render_kw={
            'class': 'form-control search-input',
            'placeholder': 'Cerca nella documentazione...',
            'autocomplete': 'off'
        }
    )
    
    department = SelectField(
        'Dipartimento',
        coerce=lambda x: int(x) if x and x != '' else None,
        validators=[Optional()],
        render_kw={'class': 'form-select'}
    )
    
    category = SelectField(
        'Categoria',
        coerce=lambda x: int(x) if x and x != '' else None,
        validators=[Optional()],
        render_kw={'class': 'form-select'}
    )


class UploadForm(FlaskForm):
    """Form per upload file."""
    
    files = FileField(
        'Seleziona file',
        validators=[
            FileAllowed(
                ['jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx', 
                 'xls', 'xlsx', 'ppt', 'pptx', 'mp3', 'mp4', 'mov'],
                'Tipo file non permesso'
            ),
            FileSize(max_size=100 * 1024 * 1024, message='File troppo grande (max 100MB)')
        ],
        render_kw={
            'class': 'form-control',
            'multiple': True,
            'accept': 'image/*,application/pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,audio/*,video/*'
        }
    )
    
    title = StringField(
        'Titolo',
        validators=[Optional()],
        render_kw={
            'class': 'form-control',
            'placeholder': 'Titolo allegato (opzionale)'
        }
    )
    
    description = TextAreaField(
        'Descrizione',
        validators=[Optional()],
        render_kw={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Descrizione allegato (opzionale)'
        }
    )
    
    alt_text = StringField(
        'Testo alternativo',
        validators=[Optional()],
        render_kw={
            'class': 'form-control',
            'placeholder': 'Testo alternativo per accessibilità (immagini)'
        }
    )


class BulkActionForm(FlaskForm):
    """Form per azioni bulk su articoli."""
    
    action = SelectField(
        'Azione',
        choices=[
            ('', '-- Seleziona azione --'),
            ('publish', 'Pubblica selezionati'),
            ('archive', 'Archivia selezionati'),
            ('delete', 'Elimina selezionati'),
            ('change_visibility', 'Cambia visibilità'),
            ('move_category', 'Sposta in categoria')
        ],
        validators=[DataRequired()],
        render_kw={'class': 'form-select'}
    )
    
    article_ids = HiddenField(
        'IDs',
        validators=[DataRequired()]
    )
    
    new_visibility = SelectField(
        'Nuova visibilità',
        choices=[
            ('', '-- Seleziona --'),
            (KBVisibilityEnum.department.value, 'Solo Dipartimento'),
            (KBVisibilityEnum.company.value, 'Tutta l\'Azienda'),
            (KBVisibilityEnum.only_heads.value, 'Solo Responsabili')
        ],
        render_kw={'class': 'form-select'}
    )
    
    new_category_id = SelectField(
        'Nuova categoria',
        coerce=lambda x: int(x) if x and x != '' else None,
        render_kw={'class': 'form-select'}
    )