import pytest
import sys
from corposostenibile import create_app
from corposostenibile.extensions import db
from tests.utils.db_helpers import setup_test_database
from sqlalchemy import text

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
    Session database isolata per ogni test.
    """
    session = db.session
    
    # Pulizia dati
    session.execute(text('TRUNCATE TABLE clienti, users, departments, teams RESTART IDENTITY CASCADE'))
    session.commit()
    
    yield session
    
    # Rollback
    session.rollback()
    session.remove()

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
