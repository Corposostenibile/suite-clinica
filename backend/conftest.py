"""
Fixtures base per test suite.

Setup database PostgreSQL, fixtures per app, session isolata con TRUNCATE,
e configurazione Factory Boy.

IMPORTANTE: Gli URL del database test sono configurati in:
- corposostenibile/config.py → TestingConfig.SQLALCHEMY_DATABASE_URI
  (default: postgresql://suite_clinica:password@localhost/corposostenibile_test da .env)

Per eseguire i test:
1. Assicurati che PostgreSQL sia in esecuzione
2. I test creeranno/pulieranno automaticamente il database
3. Esegui: poetry run pytest tests/

Per problemi di permessi, vedi TestingConfig nella documentazione.
"""

import pytest
import os
from corposostenibile import create_app
from corposostenibile.extensions import db
from tests.utils.db_helpers import setup_test_database

# Abilita test mode per saltare operazioni di DDL problematiche
os.environ["TESTING_DB_SETUP"] = "1"


@pytest.fixture(scope='session')
def app():
    """
    App Flask per test (session-scoped).
    
    Setup database PRIMA di creare app (perché create_app chiama register_enums
    che richiede che il database esista già), poi crea app con config 'testing'.
    """
    # Setup database PRIMA di creare app
    # (setup_test_database crea il DB, applica migrazioni e registra ENUM)
    setup_test_database()
    
    # Ora crea app (il database esiste già e le migrazioni sono applicate)
    app = create_app('testing')
    
    # Ensure LoginManager loaders are set
    from corposostenibile.extensions import login_manager
    from corposostenibile.models import User
    from werkzeug.security import check_password_hash
    
    @login_manager.user_loader
    def _load_user(user_id: str):
        try:
            return User.query.get(int(user_id))
        except Exception:
            return None

    @login_manager.request_loader
    def _request_loader(req):
        auth = req.authorization
        if not auth:
            return None
        user = User.query.filter_by(email=auth.username).first()
        if user and check_password_hash(user.password_hash, auth.password):
            return user
        return None
    
    yield app


@pytest.fixture(scope='function')
def db_session(app):
    """
    Session database isolata per ogni test (function-scoped).

    Ogni test ottiene una session pulita. I dati vengono committati nel database
    di test e poi rimossi esplicitamente alla fine (TRUNCATE-based cleanup).
    Questo assicura che i dati siano visibili a tutte le query.
    """
    from sqlalchemy import text

    # Usa la session standard di Flask-SQLAlchemy
    session = db.session

    # Cleanup PRIMA del test: pulisci il database per iniziare da zero
    # Usiamo TRUNCATE che è più efficiente di DELETE
    import time
    max_retries = 3
    retry_delay = 0.1  # 100ms

    for attempt in range(max_retries):
        try:
            # TRUNCATE è più efficiente e gestisce automaticamente i foreign keys con CASCADE
            # RESTART IDENTITY resetta le sequences auto-increment
            # La lista di tabelle deve includere tutte le tabelle che vogliamo ripulire
            tables_to_truncate = [
                'clienti',
                'users',
                'departments',
                'teams',
                'carousel_items',
                'news',
                'news_comments',
                'news_likes',
                'news_reads',
                'communications',
                'communication_reads',
                'reviews',
                'reviews_acknowledgments',
                'review_messages',
                'review_requests',
                'tickets',
                'ticket_comments',
                'weekly_reports',
                'anonymous_surveys',
                'anonymous_survey_responses',
                'documents_acknowledgments',
                'certifications',
                'user_educations',
                'user_salary_histories',
                'hr_notes',
                'foods',
                'food_categories',
                'recipes',
                'meal_plans',
                'training_plans',
                'training_locations',
                'recruiting_kanbans',
                'kanban_stages',
                'job_offers',
                'job_questions',
                'job_applications',
                'application_answers',
                'application_stage_histories',
                'onboarding_templates',
                'onboarding_tasks',
                'onboarding_checklists',
                'onboarding_progresses',
                'job_offer_advertising_costs',
                'kb_categories',
                'kb_articles',
                'kb_attachments'
            ]
            
            truncate_sql = ', '.join(f'"{table}"' for table in tables_to_truncate)
            session.execute(text(f'TRUNCATE TABLE {truncate_sql} RESTART IDENTITY CASCADE'))
            session.commit()
            break  # Successo, esci dal loop
        except Exception as e:
            session.rollback()
            if 'deadlock' in str(e).lower() and attempt < max_retries - 1:
                # Deadlock detected, retry dopo un breve delay
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                continue
            elif 'does not exist' in str(e).lower():
                # Tabella non esiste, continua (potrebbe succedere in test nuovi)
                # Fallback: prova con DELETE su poche tabelle critiche
                try:
                    for table in ['clienti', 'users']:
                        try:
                            session.execute(text(f'DELETE FROM "{table}"'))
                        except:
                            pass
                    session.commit()
                except:
                    session.rollback()
                    pass
                break
            else:
                # Errore sconosciuto, log e continua
                print(f"⚠️  Errore TRUNCATE: {e}")
                break

    yield session

    # Nota: il cleanup è fatto all'inizio del test successivo, non alla fine
    # Questo evita problemi con sequences e garantisce uno stato pulito


@pytest.fixture
def client(app, db_session):
    """
    Test client Flask con database isolato.

    Ogni richiesta HTTP viene eseguita con la session isolata del test.
    """
    return app.test_client()


@pytest.fixture
def authenticated_client(client, db_session, app):
    """
    Client autenticato per test route protette.

    Crea un utente admin e mocka current_user per i test.
    """
    from tests.factories import UserFactory, DepartmentFactory
    from corposostenibile.models import User
    from unittest.mock import patch
    import uuid

    # Crea utente di test con nomi univoci per evitare collisioni
    unique_id = str(uuid.uuid4())[:8]
    dept = DepartmentFactory(name=f"Test Department {unique_id}")
    user = UserFactory(
        email=f"admin-{unique_id}@test.com",
        first_name="Admin",
        last_name="Test",
        is_admin=True,
        is_active=True,
        department=dept
    )
    db_session.commit()  # Commit per rendere visibili i dati

    # Mock current_user per ritornare sempre il nostro utente di test
    # Questo bypassa completamente Flask-Login e il user_loader
    mock_current_user = patch('flask_login.utils._get_user')
    mock_user = mock_current_user.start()
    mock_user.return_value = user

    # Aggiungi riferimento all'utente per i test
    client.test_user = user

    yield client

    # Cleanup: ferma il mock
    mock_current_user.stop()


@pytest.fixture(scope='function', autouse=True)
def set_factory_session(db_session):
    """
    Setta session per Factory Boy (autouse).

    Questa fixture viene eseguita automaticamente per ogni test e
    setta la session di Factory Boy alla session isolata del test.
    """
    from tests import factories

    # Lista di tutte le factory classes
    factory_classes = [
        # Core factories
        factories.DepartmentFactory,
        factories.TeamFactory,
        factories.UserFactory,
        factories.ClienteFactory,
    ]

    # Setta session per tutte le factories
    for factory_class in factory_classes:
        factory_class._meta.sqlalchemy_session = db_session

    yield

    # Cleanup: rimuovi session dalle factories
    for factory_class in factory_classes:
        factory_class._meta.sqlalchemy_session = None
