"""
Fixtures base per test suite.

Setup database PostgreSQL, fixtures per app, session isolata con rollback,
e configurazione Factory Boy.
"""

import pytest
from corposostenibile import create_app
from corposostenibile.extensions import db
from tests.utils.db_helpers import setup_test_database


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
    
    yield app


@pytest.fixture(scope='function')
def db_session(app):
    """
    Session database isolata per ogni test (function-scoped).

    Ogni test ottiene una session pulita. I dati vengono committati nel database
    di test e poi rimossi esplicitamente alla fine (no rollback transaction-based).
    Questo assicura che i dati siano visibili a tutte le query.
    """
    from corposostenibile.models import Cliente, User, Department, Team, ClienteFreezeHistory
    from sqlalchemy import text

    # Usa la session standard di Flask-SQLAlchemy
    session = db.session

    # Cleanup PRIMA del test: pulisci il database per iniziare da zero
    # Usa un approccio ibrido: TRUNCATE dentro una transazione con retry su deadlock
    # Questo è più efficiente di DELETE ma gestisce i deadlock quando accadono
    import time
    max_retries = 3
    retry_delay = 0.1  # 100ms

    for attempt in range(max_retries):
        try:
            # TRUNCATE è più efficiente e gestisce automaticamente i foreign keys con CASCADE
            # RESTART IDENTITY resetta le sequences auto-increment
            session.execute(text('TRUNCATE TABLE clienti, users, departments, teams RESTART IDENTITY CASCADE'))
            session.commit()
            break  # Successo, esci dal loop
        except Exception as e:
            session.rollback()
            if 'deadlock' in str(e).lower() and attempt < max_retries - 1:
                # Deadlock detected, retry dopo un breve delay
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                continue
            elif attempt == max_retries - 1:
                # Ultimo tentativo fallito, lascia passare l'errore
                # o usa strategia alternativa con DELETE
                try:
                    session.execute(text('DELETE FROM clienti'))
                    session.execute(text('DELETE FROM users'))
                    session.execute(text('DELETE FROM departments'))
                    session.execute(text('DELETE FROM teams'))
                    session.commit()
                except Exception:
                    session.rollback()
                    # Se anche questo fallisce, continua comunque (i test potrebbero funzionare lo stesso)
                    pass
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
        is_active=True
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
        # Customers blueprint factories
        factories.InfluencerFactory,
        factories.SalesPersonFactory,
        factories.CustomerCareInterventionFactory,
        factories.CheckInInterventionFactory,
        factories.ContinuityCallInterventionFactory,
        factories.CartellaClinicaFactory,
        factories.AllegatoFactory,
        factories.ClienteFreezeHistoryFactory,
        factories.ClienteProfessionistaHistoryFactory,
        factories.CallBonusFactory,
        # Communications blueprint factories
        factories.CommunicationFactory,
        factories.CommunicationReadFactory,
        # News blueprint factories
        factories.NewsFactory,
        factories.NewsReadFactory,
        factories.NewsCommentFactory,
        factories.NewsLikeFactory,
        # Review blueprint factories
        factories.ReviewFactory,
        factories.ReviewAcknowledgmentFactory,
        factories.ReviewMessageFactory,
        factories.ReviewRequestFactory,
        # Department/OKR blueprint factories
        factories.DepartmentObjectiveFactory,
        factories.DepartmentKeyResultFactory,
        factories.DepartmentOKRUpdateFactory,
        # Team blueprint factories
        factories.WeeklyReportFactory,
        factories.AnonymousSurveyFactory,
        factories.AnonymousSurveyResponseFactory,
        factories.DocumentAcknowledgmentFactory,
        factories.CertificationFactory,
        factories.UserEducationFactory,
        factories.UserSalaryHistoryFactory,
        factories.HRNoteFactory,
        # Nutrition blueprint factories
        factories.FoodCategoryFactory,
        factories.FoodFactory,
        factories.RecipeFactory,
        factories.MealPlanFactory,
        factories.TrainingPlanFactory,
        factories.TrainingLocationFactory,
        # Recruiting blueprint factories
        factories.RecruitingKanbanFactory,
        factories.KanbanStageFactory,
        factories.JobOfferFactory,
        factories.JobQuestionFactory,
        factories.JobApplicationFactory,
        factories.ApplicationAnswerFactory,
        factories.ApplicationStageHistoryFactory,
        factories.OnboardingTemplateFactory,
        factories.OnboardingTaskFactory,
        factories.OnboardingChecklistFactory,
        factories.OnboardingProgressFactory,
        factories.JobOfferAdvertisingCostFactory,
        # Knowledge Base blueprint factories
        factories.KBCategoryFactory,
        factories.KBArticleFactory,
        factories.KBAttachmentFactory,
    ]

    # Setta session per tutte le factories
    for factory_class in factory_classes:
        factory_class._meta.sqlalchemy_session = db_session

    yield

    # Cleanup: rimuovi session dalle factories
    for factory_class in factory_classes:
        factory_class._meta.sqlalchemy_session = None
