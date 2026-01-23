"""
Test per i modelli del blueprint client_checks.
"""
import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from corposostenibile.models import (
    CheckForm, CheckFormField, ClientCheckAssignment, ClientCheckResponse,
    CheckFormTypeEnum, CheckFormFieldTypeEnum, CheckFormStatusEnum, AssignmentStatusEnum
)


class TestCheckForm:
    """Test per il modello CheckForm."""
    
    def test_create_check_form(self, db, sample_user, sample_department):
        """Test creazione di un form."""
        form = CheckForm(
            name='Test Form',
            description='Form di test',
            form_type=CheckFormTypeEnum.iniziale,
            is_active=True,
            created_by_id=sample_user.id,
            department_id=sample_department.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(form)
        db.session.commit()
        
        assert form.id is not None
        assert form.name == 'Test Form'
        assert form.form_type == CheckFormTypeEnum.iniziale
        assert form.is_active is True
        assert form.created_by_id == sample_user.id
    
    def test_form_name_required(self, db, sample_user):
        """Test che il nome del form sia obbligatorio."""
        form = CheckForm(
            description='Form senza nome',
            form_type=CheckFormTypeEnum.settimanale,
            is_active=True,
            created_by_id=sample_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(form)
        
        with pytest.raises(IntegrityError):
            db.session.commit()
    
    def test_form_type_enum(self, db, sample_user):
        """Test che il tipo form accetti solo valori enum validi."""
        form = CheckForm(
            name='Test Form',
            form_type=CheckFormTypeEnum.iniziale,
            is_active=True,
            created_by_id=sample_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(form)
        db.session.commit()
        
        assert form.form_type in [CheckFormTypeEnum.iniziale, CheckFormTypeEnum.settimanale]
    
    def test_form_relationships(self, sample_check_form, sample_user, sample_department):
        """Test delle relazioni del form."""
        assert sample_check_form.created_by == sample_user
        assert sample_check_form.department == sample_department
    
    def test_form_str_representation(self, sample_check_form):
        """Test della rappresentazione string del form."""
        expected = f"CheckForm(id={sample_check_form.id}, name='{sample_check_form.name}')"
        assert str(sample_check_form) == expected


class TestCheckFormField:
    """Test per il modello CheckFormField."""
    
    def test_create_form_field(self, db, sample_check_form):
        """Test creazione di un campo form."""
        field = CheckFormField(
            form_id=sample_check_form.id,
            label='Test Field',
            field_type=CheckFormFieldTypeEnum.text,
            is_required=True,
            position=1,
            placeholder='Test placeholder',
            help_text='Test help text',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(field)
        db.session.commit()
        
        assert field.id is not None
        assert field.label == 'Test Field'
        assert field.field_type == CheckFormFieldTypeEnum.text
        assert field.is_required is True
        assert field.position == 1
    
    def test_field_types(self, db, sample_check_form):
        """Test tutti i tipi di campo supportati."""
        field_types = [
            CheckFormFieldTypeEnum.text,
            CheckFormFieldTypeEnum.number,
            CheckFormFieldTypeEnum.email,
            CheckFormFieldTypeEnum.textarea,
            CheckFormFieldTypeEnum.select,
            CheckFormFieldTypeEnum.multiselect,
            CheckFormFieldTypeEnum.radio,
            CheckFormFieldTypeEnum.checkbox,
            CheckFormFieldTypeEnum.scale,
            CheckFormFieldTypeEnum.date,
            CheckFormFieldTypeEnum.file,
            CheckFormFieldTypeEnum.rating,
            CheckFormFieldTypeEnum.yesno
        ]
        
        for i, field_type in enumerate(field_types):
            field = CheckFormField(
                form_id=sample_check_form.id,
                label=f'Field {field_type.value}',
                field_type=field_type,
                is_required=False,
                position=i + 1,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(field)
        
        db.session.commit()
        
        # Verifica che tutti i campi siano stati creati
        fields = CheckFormField.query.filter_by(form_id=sample_check_form.id).all()
        assert len(fields) == len(field_types)
    
    def test_field_with_options(self, db, sample_check_form):
        """Test campo con opzioni (select, radio, etc.)."""
        options = {
            'choices': ['Opzione 1', 'Opzione 2', 'Opzione 3'],
            'multiple': False
        }
        
        field = CheckFormField(
            form_id=sample_check_form.id,
            label='Campo Select',
            field_type=CheckFormFieldTypeEnum.select,
            is_required=True,
            position=1,
            options=options,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(field)
        db.session.commit()
        
        assert field.options == options
        assert field.options['choices'] == ['Opzione 1', 'Opzione 2', 'Opzione 3']
    
    def test_field_form_relationship(self, sample_form_field, sample_check_form):
        """Test della relazione campo-form."""
        assert sample_form_field.form == sample_check_form
        assert sample_form_field in sample_check_form.fields


class TestClientCheckAssignment:
    """Test per il modello ClientCheckAssignment."""
    
    def test_create_assignment(self, db, sample_cliente, sample_check_form, sample_user):
        """Test creazione di un'assegnazione."""
        assignment = ClientCheckAssignment(
            cliente_id=sample_cliente.cliente_id,
            form_id=sample_check_form.id,
            token='unique_token_123',
            response_count=0,
            assigned_by_id=sample_user.id,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(assignment)
        db.session.commit()
        
        assert assignment.id is not None
        assert assignment.cliente_id == sample_cliente.cliente_id
        assert assignment.form_id == sample_check_form.id
        assert assignment.token == 'unique_token_123'
        assert assignment.response_count == 0
        assert assignment.is_active is True
    
    def test_token_uniqueness(self, db, sample_cliente, sample_check_form, sample_user):
        """Test che il token sia univoco."""
        # Prima assegnazione
        assignment1 = ClientCheckAssignment(
            cliente_id=sample_cliente.cliente_id,
            form_id=sample_check_form.id,
            token='duplicate_token',
            assigned_by_id=sample_user.id,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(assignment1)
        db.session.commit()
        
        # Seconda assegnazione con stesso token
        assignment2 = ClientCheckAssignment(
            cliente_id=sample_cliente.cliente_id,
            form_id=sample_check_form.id,
            token='duplicate_token',
            assigned_by_id=sample_user.id,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(assignment2)
        
        with pytest.raises(IntegrityError):
            db.session.commit()
    
    def test_assignment_relationships(self, sample_assignment, sample_cliente, sample_check_form, sample_user):
        """Test delle relazioni dell'assegnazione."""
        assert sample_assignment.cliente == sample_cliente
        assert sample_assignment.form == sample_check_form
        assert sample_assignment.assigned_by == sample_user
    
    def test_increment_response_count(self, sample_assignment, db):
        """Test incremento contatore risposte."""
        initial_count = sample_assignment.response_count
        sample_assignment.response_count += 1
        sample_assignment.last_response_at = datetime.utcnow()
        db.session.commit()
        
        assert sample_assignment.response_count == initial_count + 1
        assert sample_assignment.last_response_at is not None


class TestClientCheckResponse:
    """Test per il modello ClientCheckResponse."""
    
    def test_create_response(self, db, sample_assignment):
        """Test creazione di una risposta."""
        responses_data = {
            'nome_completo': 'Mario Rossi',
            'eta': 35,
            'peso': 75.5,
            'obiettivi': ['Perdere peso', 'Aumentare massa muscolare']
        }
        
        response = ClientCheckResponse(
            assignment_id=sample_assignment.id,
            responses=responses_data,
            ip_address='192.168.1.100',
            user_agent='Mozilla/5.0 Test Browser',
            notifications_sent=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(response)
        db.session.commit()
        
        assert response.id is not None
        assert response.assignment_id == sample_assignment.id
        assert response.responses == responses_data
        assert response.ip_address == '192.168.1.100'
        assert response.notifications_sent is False
    
    def test_response_json_data(self, sample_response):
        """Test che i dati JSON siano correttamente memorizzati."""
        assert isinstance(sample_response.responses, dict)
        assert 'nome_completo' in sample_response.responses
        assert sample_response.responses['nome_completo'] == 'Mario Rossi'
        assert sample_response.responses['eta'] == 33
    
    def test_response_assignment_relationship(self, sample_response, sample_assignment):
        """Test della relazione risposta-assegnazione."""
        assert sample_response.assignment == sample_assignment
        assert sample_response in sample_assignment.responses
    
    def test_mark_notifications_sent(self, sample_response, db):
        """Test marcatura notifiche inviate."""
        assert sample_response.notifications_sent is False
        assert sample_response.notifications_sent_at is None
        
        sample_response.notifications_sent = True
        sample_response.notifications_sent_at = datetime.utcnow()
        db.session.commit()
        
        assert sample_response.notifications_sent is True
        assert sample_response.notifications_sent_at is not None


class TestEnums:
    """Test per gli enum del sistema."""
    
    def test_check_form_type_enum(self):
        """Test enum tipo form."""
        assert CheckFormTypeEnum.iniziale.value == 'iniziale'
        assert CheckFormTypeEnum.settimanale.value == 'settimanale'
    
    def test_check_form_field_type_enum(self):
        """Test enum tipo campo."""
        expected_types = [
            'text', 'number', 'email', 'textarea', 'select', 'multiselect',
            'radio', 'checkbox', 'scale', 'date', 'file', 'rating', 'yesno'
        ]
        
        for field_type in CheckFormFieldTypeEnum:
            assert field_type.value in expected_types
    
    def test_check_form_status_enum(self):
        """Test enum stato form."""
        assert CheckFormStatusEnum.draft.value == 'draft'
        assert CheckFormStatusEnum.active.value == 'active'
        assert CheckFormStatusEnum.archived.value == 'archived'
    
    def test_assignment_status_enum(self):
        """Test enum stato assegnazione."""
        assert AssignmentStatusEnum.pending.value == 'pending'
        assert AssignmentStatusEnum.completed.value == 'completed'
        assert AssignmentStatusEnum.overdue.value == 'overdue'


class TestModelIntegration:
    """Test di integrazione tra i modelli."""
    
    def test_complete_workflow(self, db, sample_user, sample_department, sample_cliente):
        """Test workflow completo: form -> campo -> assegnazione -> risposta."""
        # 1. Crea form
        form = CheckForm(
            name='Form Completo',
            description='Test workflow completo',
            form_type=CheckFormTypeEnum.iniziale,
            is_active=True,
            created_by_id=sample_user.id,
            department_id=sample_department.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(form)
        db.session.flush()
        
        # 2. Aggiungi campi
        fields_data = [
            ('Nome', CheckFormFieldTypeEnum.text, True, 1),
            ('Età', CheckFormFieldTypeEnum.number, True, 2),
            ('Email', CheckFormFieldTypeEnum.email, False, 3),
            ('Note', CheckFormFieldTypeEnum.textarea, False, 4)
        ]
        
        for label, field_type, required, position in fields_data:
            field = CheckFormField(
                form_id=form.id,
                label=label,
                field_type=field_type,
                is_required=required,
                position=position,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(field)
        
        db.session.flush()
        
        # 3. Crea assegnazione
        assignment = ClientCheckAssignment(
            cliente_id=sample_cliente.cliente_id,
            form_id=form.id,
            token='workflow_token_123',
            response_count=0,
            assigned_by_id=sample_user.id,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(assignment)
        db.session.flush()
        
        # 4. Crea risposta
        response_data = {
            'nome': 'Mario Rossi',
            'eta': 35,
            'email': 'mario@example.com',
            'note': 'Cliente molto motivato'
        }
        
        response = ClientCheckResponse(
            assignment_id=assignment.id,
            responses=response_data,
            ip_address='127.0.0.1',
            user_agent='Test Browser',
            notifications_sent=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(response)
        
        # 5. Aggiorna contatore
        assignment.response_count += 1
        assignment.last_response_at = datetime.utcnow()
        
        db.session.commit()
        
        # Verifica tutto il workflow
        assert form.id is not None
        assert len(form.fields) == 4
        assert assignment.form == form
        assert assignment.response_count == 1
        assert len(assignment.responses) == 1
        assert response.assignment == assignment
        assert response.responses['nome'] == 'Mario Rossi'
    
    def test_cascade_deletions(self, db, sample_check_form, sample_form_field, sample_assignment, sample_response):
        """Test che le eliminazioni a cascata funzionino correttamente."""
        form_id = sample_check_form.id
        
        # Verifica che esistano i record collegati
        assert CheckFormField.query.filter_by(form_id=form_id).count() > 0
        assert ClientCheckAssignment.query.filter_by(form_id=form_id).count() > 0
        
        # Elimina il form
        db.session.delete(sample_check_form)
        db.session.commit()
        
        # Verifica che i record collegati siano stati eliminati
        assert CheckFormField.query.filter_by(form_id=form_id).count() == 0
        assert ClientCheckAssignment.query.filter_by(form_id=form_id).count() == 0