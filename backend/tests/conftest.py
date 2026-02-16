"""
Configurazione pytest globale per i test del backend.
"""
import pytest
import os
from datetime import datetime, date, timedelta
from corposostenibile import create_app
from corposostenibile.extensions import db as _db
from corposostenibile.models import User, Cliente, Department, UserRoleEnum, TeamEnum, StatoClienteEnum

# Point to test database
os.environ['FLASK_ENV'] = 'testing'

@pytest.fixture(scope='session')
def app():
    """Crea l'app Flask per i test."""
    app = create_app('testing')
    # Use a separate test database or the dev one if safe (here using dev for simplicity in this env, 
    # but ideally should be separate. Given the environment, we'll use the configured one but valid to be careful)
    # For now, we assume the testing config handles the DB URI or we prioritize safety by using a transaction rollback.
    
    with app.app_context():
        # _db.create_all() # Using real DB, assume schema exists.
        yield app
        # _db.drop_all()

@pytest.fixture(scope='function')
def client(app):
    """Client di test Flask."""
    return app.test_client()

@pytest.fixture(scope='function')
def db_session(app):
    """
    Creates a new database session for a test.
    Rolls back any changes at the end of the test.
    Uses SAVEPOINT to handle commits within tests without persisting to DB.
    """
    from sqlalchemy import orm, event
    
    connection = _db.engine.connect()
    transaction = connection.begin()
    
    session_factory = orm.sessionmaker(bind=connection, expire_on_commit=False)
    session = orm.scoped_session(session_factory)
    
    _db.session = session
    
    # Begin a nested transaction (SAVEPOINT)
    session.begin_nested()
    
    # Each time that the SAVEPOINT ends, reopen it
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.expire_all()
            session.begin_nested()
    
    yield session
    
    session.remove()
    transaction.rollback()
    connection.close()

@pytest.fixture
def sample_admin_user(db_session):
    """Crea un utente admin per i test."""
    # Query first to check if it exists
    user = db_session.query(User).filter_by(email='admin_test@example.com').first()
    if not user:
        user = User(
            email='admin_test@example.com',
            first_name='Admin',
            last_name='Test',
            role=UserRoleEnum.admin,
            is_active=True,
            is_admin=True
        )
        user.set_password('password')
        db_session.add(user)
        db_session.commit()
    return user

@pytest.fixture
def authenticated_client(client, db_session):
    """Client autenticato come admin."""
    # Create admin user if not exists (avoid dependency on fixture object)
    user = db_session.query(User).filter_by(email='admin_test@example.com').first()
    if not user:
        user = User(
            email='admin_test@example.com',
            first_name='Admin',
            last_name='Test',
            role=UserRoleEnum.admin,
            is_active=True,
            is_admin=True
        )
        user.set_password('password')
        db_session.add(user)
        db_session.commit()
    
    # Login via endpoint
    res = client.post('/auth/login', data={
        'email': 'admin_test@example.com',
        'password': 'password'
    })
    assert res.status_code == 302
    return client
