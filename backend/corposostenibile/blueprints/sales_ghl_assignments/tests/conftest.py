"""Pytest fixtures per i test del blueprint sales_ghl_assignments."""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("FLASK_ENV", "development")


@pytest.fixture(scope="session")
def app():
    from corposostenibile import create_app
    from corposostenibile.extensions import db as _db

    app = create_app("development")
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["GHL_WEBHOOK_SECRET"] = "test-ghl-webhook-secret"
    app.config["MAIL_SUPPRESS_SEND"] = True
    with app.app_context():
        _db.create_all()
        yield app


@pytest.fixture(scope="function")
def db_session(app):
    from sqlalchemy import event, orm
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
