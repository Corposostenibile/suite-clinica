"""
Configurazione pytest per i test delle API customers.
"""
import os
import pytest

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
    """Sessione DB con rollback a fine test (SAVEPOINT)."""
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
