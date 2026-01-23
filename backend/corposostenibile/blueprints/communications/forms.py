"""
Form per il blueprint communications.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectMultipleField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError
from wtforms.widgets import CheckboxInput, ListWidget
from flask_login import current_user

from corposostenibile.models import Department
from .permissions import can_create_for_all_departments


class MultiCheckboxField(SelectMultipleField):
    """Campo per checkbox multipli."""
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


class CommunicationForm(FlaskForm):
    """Form per creare/modificare una comunicazione."""
    
    title = StringField(
        'Titolo',
        validators=[
            DataRequired(message="Il titolo è obbligatorio"),
            Length(min=3, max=200, message="Il titolo deve essere tra 3 e 200 caratteri")
        ],
        render_kw={
            "class": "form-control",
            "placeholder": "Inserisci il titolo della comunicazione"
        }
    )
    
    content = TextAreaField(
        'Contenuto',
        validators=[
            DataRequired(message="Il contenuto è obbligatorio"),
            Length(min=10, message="Il contenuto deve essere di almeno 10 caratteri")
        ],
        render_kw={
            "class": "form-control",
            "rows": "10"
        }
    )
    
    # Checkbox per inviare a tutti i dipartimenti
    send_to_all = BooleanField(
        'Invia a tutti i dipartimenti',
        render_kw={"class": "form-check-input"}
    )
    
    # Selezione dipartimenti (solo se non send_to_all)
    departments = MultiCheckboxField(
        'Dipartimenti',
        coerce=int,
        render_kw={"class": "form-check-input"}
    )
    
    submit = SubmitField(
        'Invia Comunicazione',
        render_kw={"class": "btn btn-primary"}
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Popola le scelte dei dipartimenti
        if current_user.is_admin:
            # Admin vedono tutti i dipartimenti
            self.departments.choices = [
                (dept.id, dept.name)
                for dept in Department.query.order_by(Department.name).all()
            ]
        elif current_user.department and current_user.department.head_id == current_user.id:
            # Head vedono solo il proprio dipartimento
            self.departments.choices = [(current_user.department.id, current_user.department.name)]
            # Preseleziona il proprio dipartimento
            if not self.departments.data:
                self.departments.data = [current_user.department.id]
        
        # Se non è admin, nasconde e disabilita l'opzione "tutti i dipartimenti"
        if not can_create_for_all_departments(current_user):
            self.send_to_all.data = False
            self.send_to_all.render_kw = {"class": "form-check-input", "style": "display: none;"}
    
    def validate_departments(self, field):
        """Valida la selezione dei dipartimenti."""
        # Se send_to_all è selezionato, non servono dipartimenti
        if hasattr(self, 'send_to_all') and self.send_to_all.data:
            return
        
        # Altrimenti, almeno un dipartimento deve essere selezionato
        if not field.data:
            raise ValidationError("Seleziona almeno un dipartimento")
        
        # Se è un head, può selezionare solo il proprio dipartimento
        if not current_user.is_admin:
            if current_user.department and current_user.department.head_id == current_user.id:
                if len(field.data) != 1 or field.data[0] != current_user.department.id:
                    raise ValidationError("Puoi inviare comunicazioni solo al tuo dipartimento")