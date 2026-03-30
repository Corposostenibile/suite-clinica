import pytest
from corposostenibile import create_app
from corposostenibile.extensions import db
from tests.utils.db_helpers import setup_test_database

_app = None

def get_app():
    global _app
    if _app is None:
        setup_test_database()
        _app = create_app('testing')
        _app.config.update({
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,
        })
    return _app


@pytest.fixture(scope='session')
def app():
    return get_app()

@pytest.fixture(scope='function')
def db_session(app):
    """
    Transaction-based test isolation.

    Each test runs inside a database transaction that is rolled back
    at the end. All sessions (test code + request handlers) share the
    same connection via a monkey-patched get_bind().

    session.commit() creates/releases SAVEPOINTs instead of real COMMITs,
    so data is visible within the transaction but never persisted.

    This is ~10-50x faster than TRUNCATE-based cleanup on ~40 tables.
    """
    from flask_sqlalchemy.session import Session as FSASession

    with app.app_context():
        # Open a dedicated connection and begin the outer transaction
        # that will be rolled back at the end of the test.
        connection = db.engine.connect()
        transaction = connection.begin()

        # Monkey-patch get_bind so every Session instance (test code,
        # request handlers, teardown) routes queries through *this*
        # connection (and therefore this transaction).
        original_get_bind = FSASession.get_bind
        FSASession.get_bind = (
            lambda self, mapper=None, clause=None, bind=None, **kw: connection
        )

        # Reconfigure the session factory:
        # - join_transaction_mode="create_savepoint" makes the session
        #   create a SAVEPOINT when it joins our already-begun transaction.
        #   session.commit() → RELEASE SAVEPOINT (data visible in txn)
        #   session.rollback() → ROLLBACK TO SAVEPOINT
        # - expire_on_commit=False prevents DetachedInstanceError: after
        #   an HTTP request, Flask-SQLAlchemy teardown calls session.remove()
        #   which detaches ORM objects.  Without this, accessing attributes
        #   on fixtures (e.g. user.email) after a request triggers lazy-load
        #   on a detached instance.
        db.session.remove()
        db.session.configure(
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )

        yield db.session

        # --- teardown ---
        db.session.remove()
        FSASession.get_bind = original_get_bind
        db.session.configure(
            join_transaction_mode="conditional_savepoint",
            expire_on_commit=True,
        )
        transaction.rollback()
        connection.close()

@pytest.fixture(scope='function', autouse=True)
def set_factory_session(db_session):
    """
    Configura le factory per usare la sessione transazionale corrente.
    """
    from tests import factories

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

    for factory_class in factory_classes:
        factory_class._meta.sqlalchemy_session = db_session

    yield

    for factory_class in factory_classes:
        factory_class._meta.sqlalchemy_session = None
