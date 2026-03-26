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
    from corposostenibile.extensions import db

    # Usa la session standard di Flask-SQLAlchemy
    session = db.session

    # Cleanup PRIMA del test: pulisci il database per iniziare da zero
    # Usa un approccio ibrido: TRUNCATE dentro una transazione con retry su deadlock
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
                try:
                    session.execute(text('DELETE FROM clienti'))
                    session.execute(text('DELETE FROM users'))
                    session.execute(text('DELETE FROM departments'))
                    session.execute(text('DELETE FROM teams'))
                    session.commit()
                except Exception:
                    session.rollback()
                    pass
            break

    yield session

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
        factories.DepartmentFactory, factories.TeamFactory, factories.UserFactory,
        factories.ClienteFactory, factories.InfluencerFactory, factories.SalesPersonFactory,
        factories.CustomerCareInterventionFactory, factories.CheckInInterventionFactory,
        factories.ContinuityCallInterventionFactory, factories.CartellaClinicaFactory,
        factories.AllegatoFactory, factories.ClienteFreezeHistoryFactory,
        factories.ClienteProfessionistaHistoryFactory, factories.CallBonusFactory,
        factories.CommunicationFactory, factories.CommunicationReadFactory,
        factories.NewsFactory, factories.NewsReadFactory, factories.NewsCommentFactory,
        factories.NewsLikeFactory, factories.ReviewFactory, factories.ReviewAcknowledgmentFactory,
        factories.ReviewMessageFactory, factories.ReviewRequestFactory,
        factories.DepartmentObjectiveFactory, factories.DepartmentKeyResultFactory,
        factories.DepartmentOKRUpdateFactory, factories.WeeklyReportFactory,
        factories.AnonymousSurveyFactory, factories.AnonymousSurveyResponseFactory,
        factories.DocumentAcknowledgmentFactory, factories.CertificationFactory,
        factories.UserEducationFactory, factories.UserSalaryHistoryFactory,
        factories.HRNoteFactory, factories.FoodCategoryFactory, factories.FoodFactory,
        factories.RecipeFactory, factories.MealPlanFactory, factories.TrainingPlanFactory,
        factories.TrainingLocationFactory, factories.RecruitingKanbanFactory,
        factories.KanbanStageFactory, factories.JobOfferFactory, factories.JobQuestionFactory,
        factories.JobApplicationFactory, factories.ApplicationAnswerFactory,
        factories.ApplicationStageHistoryFactory, factories.OnboardingTemplateFactory,
        factories.OnboardingTaskFactory, factories.OnboardingChecklistFactory,
        factories.OnboardingProgressFactory, factories.JobOfferAdvertisingCostFactory,
        factories.KBCategoryFactory, factories.KBArticleFactory, factories.KBAttachmentFactory,
    ]

    # Setta session per tutte le factories
    for factory_class in factory_classes:
        factory_class._meta.sqlalchemy_session = db_session

    yield

    # Cleanup: rimuovi session dalle factories
    for factory_class in factory_classes:
        factory_class._meta.sqlalchemy_session = None
