"""
Configurazione pytest per i test del blueprint Quality.
Fornisce app, db_session e fixture specifiche per Quality (date, professionisti, clienti, score).
"""
import os
import pytest
from datetime import date, datetime, timedelta

# Ambiente testing per scoperta test sotto backend/
os.environ.setdefault("FLASK_ENV", "testing")


@pytest.fixture(scope="session")
def app():
    """Crea l'app Flask per i test."""
    from corposostenibile import create_app
    app = create_app("testing")
    with app.app_context():
        yield app


@pytest.fixture(scope="function")
def db_session(app):
    """
    Sessione DB con rollback a fine test (SAVEPOINT).
    Per test di integrazione che leggono/scrivono DB.
    """
    from sqlalchemy import orm, event
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
        session.remove()
        transaction.rollback()
        connection.close()


# --- Fixture dati per test Quality (usare con db_session) ---

@pytest.fixture
def week_start():
    """Data inizio settimana (lunedì) per test ripetibili."""
    return date(2025, 1, 6)  # Lun 6 gen 2025


@pytest.fixture
def week_end(week_start):
    return week_start + timedelta(days=6)


@pytest.fixture
def quarter_string():
    return "2025-Q1"


# --- Fixture per test Super Malus (User, Cliente) ---

@pytest.fixture
def sample_prof_nutrizionista(db_session):
    """Utente professionista nutrizionista per test."""
    from corposostenibile.models import User, UserSpecialtyEnum
    user = User(
        email="prof_nutri_quality_test@example.com",
        first_name="Nutri",
        last_name="Test",
        specialty=UserSpecialtyEnum.nutrizionista,
        is_active=True,
    )
    user.password_hash = "dummy"
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def sample_prof_coach(db_session):
    """Utente professionista coach per test."""
    from corposostenibile.models import User, UserSpecialtyEnum
    user = User(
        email="prof_coach_quality_test@example.com",
        first_name="Coach",
        last_name="Test",
        specialty=UserSpecialtyEnum.coach,
        is_active=True,
    )
    user.password_hash = "dummy"
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def sample_prof_psicologo(db_session):
    """Utente professionista psicologo per test (sempre primario)."""
    from corposostenibile.models import User, UserSpecialtyEnum
    user = User(
        email="prof_psico_quality_test@example.com",
        first_name="Psico",
        last_name="Test",
        specialty=UserSpecialtyEnum.psicologo,
        is_active=True,
    )
    user.password_hash = "dummy"
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def sample_cliente_quality(db_session, sample_prof_nutrizionista, sample_prof_coach, sample_prof_psicologo):
    """Cliente con tutti e tre i professionisti assegnati (per test Super Malus)."""
    from corposostenibile.models import Cliente, FiguraRifEnum
    # cliente_id arbitrario ma univoco per test
    cliente = Cliente(
        cliente_id=99990001,
        nome_cognome="Cliente Quality Test",
        nutrizionista_id=sample_prof_nutrizionista.id,
        coach_id=sample_prof_coach.id,
        psicologa_id=sample_prof_psicologo.id,
        figura_di_riferimento=FiguraRifEnum.nutrizionista,
    )
    db_session.add(cliente)
    db_session.commit()
    return cliente
