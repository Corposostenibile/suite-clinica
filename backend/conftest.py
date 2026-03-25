"""
Root conftest.py per suite-clinica backend tests.
Fornisce fixture base per Flask app, database, e client per tutti i test.

Fixture disponibili globalmente:
- app: Flask app instance
- client: Flask test client (per HTTP requests)
- db: Database session
- db_session: Advanced DB session con nested transactions (rollback dopo ogni test)
"""

import os
import pytest
from datetime import date, datetime, timedelta
from sqlalchemy import orm, event


# Imposta ambiente testing
os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("TESTING", "true")


@pytest.fixture(scope="function")  # Cambiato da "session" a "function"
def app():
    """
    Crea l'app Flask per i test (scope=function, creato per ogni test).
    
    Per SQLite (testing), salta le enum registrations PostgreSQL.
    
    Returns:
        Flask app instance configured for testing
    """
    from corposostenibile import create_app
    from corposostenibile.extensions import db as _db
    import os
    
    # Skip register_enums per SQLite (non supporta PostgreSQL enums)
    os.environ["SKIP_ENUM_REGISTRATION"] = "true"
    
    app = create_app("testing")
    
    with app.app_context():
        # Per SQLite, usa create_all() invece delle migrations
        if "sqlite" in app.config.get("SQLALCHEMY_DATABASE_URI", ""):
            _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    """
    Flask test client per fare HTTP requests ai test endpoints.
    
    Returns:
        Flask test client (werkzeug.test.Client)
    """
    return app.test_client()


@pytest.fixture(scope="function")
def db_session(app):
    """
    Advanced DB session con rollback a fine test usando nested transactions (SAVEPOINT).
    
    Pattern consigliato per i test di integrazione che leggono/scrivono nel DB.
    Ogni test ha una transazione isolata che viene rollback automaticamente.
    
    Yields:
        SQLAlchemy scoped_session con nested transaction
    """
    from corposostenibile.extensions import db as _db
    
    with app.app_context():
        connection = _db.engine.connect()
        transaction = connection.begin()
        session_factory = orm.sessionmaker(bind=connection, expire_on_commit=False)
        session = orm.scoped_session(session_factory)
        _db.session = session
        session.begin_nested()

        @event.listens_for(session, "after_transaction_end")
        def restart_savepoint(sess, trans):
            if trans.nested and not trans._parent.nested:
                sess.expire_all()
                sess.begin_nested()

        yield session
        
        # Cleanup: rollback la transazione (annulla tutti i cambiamenti del test)
        session.remove()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def db(app):
    """
    Fixture DB semplice per test che non necessitano rollback avanzato.
    
    Nota: Per test di integrazione, preferire db_session (ha nested transactions).
    
    Yields:
        SQLAlchemy db instance
    """
    from corposostenibile.extensions import db as _db
    
    with app.app_context():
        yield _db
        # Cleanup after test
        _db.session.rollback()


# === Fixture generiche per oggetti comuni ===

@pytest.fixture
def sample_user(db_session):
    """
    Crea un utente di test generico.
    
    Returns:
        User instance
    """
    from corposostenibile.models import User
    
    user = User(
        email="test_user@example.com",
        first_name="Test",
        last_name="User",
        is_active=True,
    )
    user.password_hash = "dummy_hash"
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def sample_admin_user(db_session):
    """
    Crea un utente admin di test.
    
    Returns:
        User instance with is_admin=True
    """
    from corposostenibile.models import User
    
    user = User(
        email="test_admin@example.com",
        first_name="Admin",
        last_name="Test",
        is_active=True,
        is_admin=True,
    )
    user.password_hash = "dummy_hash"
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def sample_cliente(db_session):
    """
    Crea un cliente di test.
    
    Returns:
        Cliente instance
    """
    from corposostenibile.models import Cliente
    
    cliente = Cliente(
        nome_cognome="Test Cliente",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(cliente)
    db_session.commit()
    return cliente


# === Utilità per test ===

@pytest.fixture
def authenticated_client(client, sample_user, app):
    """
    Ritorna un test client già autenticato (con session/token del sample_user).
    
    Utile per test di endpoint che richiedono autenticazione.
    
    Returns:
        Authenticated Flask test client
    """
    # Questo dipende dalla implementazione di autenticazione (session, JWT, etc.)
    # Placeholder per ora - implementare in base a come funziona l'auth
    return client


@pytest.fixture
def mock_datetime_now():
    """
    Fornisce una data/ora fissa per test ripetibili.
    
    Returns:
        datetime instance (2025-01-15 12:00:00)
    """
    return datetime(2025, 1, 15, 12, 0, 0)
