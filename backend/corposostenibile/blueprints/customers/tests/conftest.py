"""
Conftest pytest per i test del blueprint customers.
Fornisce app, db_session e fixture specifiche per il flusso Call Bonus.
"""
from __future__ import annotations

import os
import pytest

os.environ.setdefault("FLASK_ENV", "testing")


@pytest.fixture(scope="session")
def app():
    """Crea l'app Flask in modalità testing."""
    import os
    from corposostenibile import create_app
    from corposostenibile.extensions import db as _db
    
    # Mock hard di sqlalchemy_searchable DDL per SQLite
    import sqlalchemy_searchable
    from sqlalchemy_searchable import types as sa_search_types
    from sqlalchemy.ext.compiler import compiles
    
    original_sync = sqlalchemy_searchable.sync_trigger
    sqlalchemy_searchable.sync_trigger = lambda *args, **kwargs: None
    
    # Fa sì che TSVectorType compili come TEXT su SQLite, evitando l'errore
    @compiles(sa_search_types.TSVectorType, 'sqlite')
    def compile_tsvector_sqlite(element, compiler, **kw):
        return "TEXT"
        
    application = create_app("testing")
    with application.app_context():
        # Rimuove i listener DDL di sqlalchemy_searchable su connection
        from sqlalchemy import event
        from sqlalchemy.schema import DDL
        
        # Facciamo una try-except granulare per singola tabella
        # in quanto db.create_all() fallisce atomicamente se incontra DDL postgres
        
        # Disabilita gli eventi DDL di sqlalchemy-searchable sulle tabelle
        for table in _db.metadata.tables.values():
            event.listen(table, 'after_create', lambda *a, **kw: None)
            
        try:
            # SQLAlchemy 2.0: evitiamo il patching di execute e cerchiamo di catturare
            # gli errori PostgreSQL direttamente se le tabelle supportate FTS si inizializzano.
            # Metodo più sicuro: intercettare create_all e passare su SQLite
            
            with _db.engine.connect() as conn:
                for name, table in _db.metadata.tables.items():
                    if "google" in name or "oauth" in name or name == "google_auth":
                        continue  # Skippa tabelle Flask-Dance OAuth non compatibili con SQLite
                    try:
                        table.create(conn, checkfirst=True)
                    except Exception as e:
                        if "syntax error" in str(e) or "parse_websearch" in str(e):
                            pass
                        else:
                            raise e
        finally:
            pass
            
        yield application
        _db.drop_all()
        
    sqlalchemy_searchable.sync_trigger = original_sync


@pytest.fixture(scope="function")
def db_session(app):
    """
    Sessione DB con rollback a fine test (SAVEPOINT).
    Ogni test inizia pulito senza lasciare dati residui.
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


@pytest.fixture
def admin_user(db_session):
    """Utente admin per operazioni privilegiate."""
    from corposostenibile.models import User, UserRoleEnum
    user = User(
        email="admin_cb_test@test.suite",
        first_name="Admin",
        last_name="Test",
        role=UserRoleEnum.admin,
        is_admin=True,
        is_active=True,
    )
    user.set_password("TestAdmin123!")
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def prof_nutrizionista(db_session):
    """Professionista nutrizionista con link_call_bonus."""
    from corposostenibile.models import User, UserRoleEnum, UserSpecialtyEnum
    user = User(
        email="nutri_cb_test@test.suite",
        first_name="Nutri",
        last_name="TestCB",
        role=UserRoleEnum.professionista,
        specialty=UserSpecialtyEnum.nutrizionista,
        is_active=True,
        is_admin=False,
        assignment_ai_notes={
            "link_call_bonus": "https://calendly.com/test-nutri/call-bonus",
            "disponibilita": "lun-ven 9-18",
            "specializzazione_dettaglio": "Nutrizionista test",
        },
    )
    user.set_password("TestPass123!")
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def prof_coach(db_session):
    """Professionista coach con link_call_bonus."""
    from corposostenibile.models import User, UserRoleEnum, UserSpecialtyEnum
    user = User(
        email="coach_cb_test@test.suite",
        first_name="Coach",
        last_name="TestCB",
        role=UserRoleEnum.professionista,
        specialty=UserSpecialtyEnum.coach,
        is_active=True,
        is_admin=False,
        assignment_ai_notes={
            "link_call_bonus": "https://calendly.com/test-coach/call-bonus",
        },
    )
    user.set_password("TestPass123!")
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def prof_nutrizionista_no_link(db_session):
    """Professionista SENZA link_call_bonus (test caso critico)."""
    from corposostenibile.models import User, UserRoleEnum, UserSpecialtyEnum
    user = User(
        email="nutri_nolink_cb_test@test.suite",
        first_name="NutriNoLink",
        last_name="TestCB",
        role=UserRoleEnum.professionista,
        specialty=UserSpecialtyEnum.nutrizionista,
        is_active=True,
        is_admin=False,
        assignment_ai_notes={},  # Nessun link_call_bonus
    )
    user.set_password("TestPass123!")
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def prof_altro(db_session):
    """Professionista non assegnato alla call bonus (per test RBAC)."""
    from corposostenibile.models import User, UserRoleEnum, UserSpecialtyEnum
    user = User(
        email="altro_cb_test@test.suite",
        first_name="Altro",
        last_name="TestCB",
        role=UserRoleEnum.professionista,
        specialty=UserSpecialtyEnum.nutrizionista,
        is_active=True,
        is_admin=False,
        assignment_ai_notes={"link_call_bonus": "https://calendly.com/altro/cb"},
    )
    user.set_password("TestPass123!")
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def cliente_test(db_session, prof_nutrizionista):
    """Cliente attivo con nutrizionista assegnato e storia compilata."""
    from corposostenibile.models import Cliente, StatoClienteEnum
    cliente = Cliente(
        cliente_id=9999801,
        nome_cognome="Cliente Test CallBonus",
        mail="cliente_cb_test@test.suite",
        storia_cliente=(
            "Donna 32 anni, vuole aggiungere coaching per gestire lo stress. "
            "Ottimi progressi con la nutrizione, motivata e costante."
        ),
        programma_attuale="Piano Test",
        stato_cliente=StatoClienteEnum.attivo,
        nutrizionista_id=prof_nutrizionista.id,
    )
    db_session.add(cliente)
    db_session.flush()
    cliente.nutrizionisti_multipli.append(prof_nutrizionista)
    db_session.flush()
    return cliente


@pytest.fixture
def call_bonus_proposta(db_session, cliente_test, prof_coach, admin_user):
    """Call bonus in stato 'proposta' (step 1 completato)."""
    from datetime import date
    from corposostenibile.models import CallBonus, CallBonusStatusEnum, TipoProfessionistaEnum
    cb = CallBonus(
        cliente_id=cliente_test.cliente_id,
        professionista_id=None,
        tipo_professionista=TipoProfessionistaEnum.coach,
        status=CallBonusStatusEnum.proposta,
        data_richiesta=date.today(),
        created_by_id=admin_user.id,
        note_richiesta="Vuole un coach per la gestione dello stress",
        ai_analysis={"summary": "Analisi test", "criteria": [], "suggested_focus": []},
        ai_matches=[
            {
                "id": prof_coach.id,
                "nome": prof_coach.full_name,
                "score": 0.85,
                "link_call_bonus": "https://calendly.com/test-coach/call-bonus",
            }
        ],
    )
    db_session.add(cb)
    db_session.flush()
    return cb


@pytest.fixture
def call_bonus_accettata(db_session, call_bonus_proposta, prof_coach):
    """Call bonus in stato 'accettata' con professionista assegnato (step 2 completato)."""
    from datetime import date
    from corposostenibile.models import CallBonusStatusEnum
    cb = call_bonus_proposta
    cb.professionista_id = prof_coach.id
    cb.status = CallBonusStatusEnum.accettata
    cb.data_risposta = date.today()
    db_session.flush()
    return cb
