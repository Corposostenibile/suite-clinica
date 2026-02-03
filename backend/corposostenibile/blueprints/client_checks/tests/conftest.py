"""
Configurazione pytest per i test del blueprint client_checks.
"""
import pytest
from datetime import datetime
from corposostenibile import create_app
from corposostenibile.extensions import db as _db
from corposostenibile.models import User, Cliente, Department
from corposostenibile.models import (
    CheckForm, CheckFormField, ClientCheckAssignment, ClientCheckResponse,
    CheckFormTypeEnum, CheckFormFieldTypeEnum, CheckFormStatusEnum, AssignmentStatusEnum
)


@pytest.fixture(scope='session')
def app():
    """Crea l'app Flask per i test."""
    import os
    app = create_app('testing')
    test_db_uri = 'postgresql://corposostenibile:password@localhost:5432/corposostenibile_dev'
    
    app.config['SQLALCHEMY_DATABASE_URI'] = test_db_uri
    
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture
def client(app):
    """Client di test Flask."""
    return app.test_client()


@pytest.fixture
def db(app):
    """Database di test."""
    with app.app_context():
        yield _db


@pytest.fixture
def sample_user(db):
    """Crea un utente di test."""
    user = User(
        email='test@example.com',
        first_name='Test',
        last_name='User',
        password_hash='hashed_password'
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def sample_department(db):
    """Crea un dipartimento di test."""
    department = Department(
        name='Test Department',
        description='Dipartimento per test'
    )
    db.session.add(department)
    db.session.commit()
    return department


@pytest.fixture
def sample_cliente(db):
    """Crea un cliente di test."""
    cliente = Cliente(
        nome_cognome='Mario Rossi',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.session.add(cliente)
    db.session.commit()
    return cliente


@pytest.fixture
def sample_check_form(db, sample_user, sample_department):
    """Crea un form di test."""
    form = CheckForm(
        name='Form Test Iniziale',
        description='Form di test per check iniziali',
        form_type=CheckFormTypeEnum.iniziale,
        is_active=True,
        created_by_id=sample_user.id,
        department_id=sample_department.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.session.add(form)
    db.session.commit()
    return form


@pytest.fixture
def sample_form_field(db, sample_check_form):
    """Crea un campo form di test."""
    field = CheckFormField(
        form_id=sample_check_form.id,
        label='Nome completo',
        field_type=CheckFormFieldTypeEnum.text,
        is_required=True,
        position=1,
        placeholder='Inserisci il tuo nome completo',
        help_text='Nome e cognome del cliente',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.session.add(field)
    db.session.commit()
    return field


@pytest.fixture
def sample_assignment(db, sample_cliente, sample_check_form, sample_user):
    """Crea un'assegnazione di test."""
    assignment = ClientCheckAssignment(
        cliente_id=sample_cliente.cliente_id,
        form_id=sample_check_form.id,
        token='test_token_123456',
        response_count=0,
        assigned_by_id=sample_user.id,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.session.add(assignment)
    db.session.commit()
    return assignment


@pytest.fixture
def sample_response(db, sample_assignment):
    """Crea una risposta di test."""
    response = ClientCheckResponse(
        assignment_id=sample_assignment.id,
        responses={'nome_completo': 'Mario Rossi', 'eta': 33},
        ip_address='127.0.0.1',
        user_agent='Test Browser',
        notifications_sent=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.session.add(response)
    db.session.commit()
    return response


@pytest.fixture(autouse=True)
def cleanup_db(db):
    """Pulisce il database dopo ogni test."""
    yield
    db.session.rollback()
    # Rimuovi tutti i dati di test
    for table in reversed(_db.metadata.sorted_tables):
        db.session.execute(table.delete())
    db.session.commit()