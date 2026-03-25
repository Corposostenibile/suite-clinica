"""
Factory Boy factories for test data generation.

Questo modulo contiene factories per i principali modelli suite-clinica.
"""

import factory
from factory.alchemy import SQLAlchemyModelFactory
from datetime import datetime, date, timedelta
from faker import Faker
from werkzeug.security import generate_password_hash
from corposostenibile.models import Department, Team, User, Cliente, TeamTypeEnum
from corposostenibile.extensions import db


fake = Faker('it_IT')


class DepartmentFactory(SQLAlchemyModelFactory):
    """Factory per Department (Dipartimento)."""
    
    class Meta:
        model = Department
        sqlalchemy_session = db.session
    
    name = factory.Faker('company')


class TeamFactory(SQLAlchemyModelFactory):
    """Factory per Team (Squadra)."""
    
    class Meta:
        model = Team
        sqlalchemy_session = db.session
    
    name = factory.Faker('job')
    team_type = TeamTypeEnum.nutrizione  # Default value, can be overridden
    department = factory.SubFactory(DepartmentFactory)


class UserFactory(SQLAlchemyModelFactory):
    """Factory per User (Utente)."""
    
    class Meta:
        model = User
        sqlalchemy_session = db.session
    
    email = factory.Faker('email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    password_hash = factory.LazyFunction(lambda: generate_password_hash('password'))
    is_active = True
    is_admin = False


class ClienteFactory(SQLAlchemyModelFactory):
    """Factory per Cliente (Cliente)."""
    
    class Meta:
        model = Cliente
        sqlalchemy_session = db.session
    
    nome_cognome = factory.Faker('name')
    # Nota: 'email' è una read-only property che ritorna consulente_alimentare, non settabile
    # Nota: 'numero_tel' è una read-only property, non settabile
    # Imposta solo i campi che hanno setter reali
    consulente_alimentare = factory.Faker('email')


# Placeholder factories for other models if needed
class CommunicationFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class CommunicationReadFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class NewsFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class NewsReadFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class NewsCommentFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class NewsLikeFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class ReviewFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class ReviewAcknowledgmentFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class ReviewMessageFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class ReviewRequestFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class DepartmentObjectiveFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class DepartmentKeyResultFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class DepartmentOKRUpdateFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class WeeklyReportFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class AnonymousSurveyFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class AnonymousSurveyResponseFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class DocumentAcknowledgmentFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class CertificationFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class UserEducationFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class UserSalaryHistoryFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class HRNoteFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class FoodCategoryFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class FoodFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class RecipeFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class MealPlanFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class TrainingPlanFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class TrainingLocationFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class RecruitingKanbanFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class KanbanStageFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class JobOfferFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class JobQuestionFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class JobApplicationFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class ApplicationAnswerFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class ApplicationStageHistoryFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class OnboardingTemplateFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class OnboardingTaskFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class OnboardingChecklistFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class OnboardingProgressFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class JobOfferAdvertisingCostFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class KBCategoryFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class KBArticleFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class KBAttachmentFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


# Additional factories for customers blueprint
class InfluencerFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class SalesPersonFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class CustomerCareInterventionFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class CheckInInterventionFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class ContinuityCallInterventionFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class CartellaClinicaFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class AllegatoFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class ClienteFreezeHistoryFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class ClienteProfessionistaHistoryFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder


class CallBonusFactory(factory.Factory):
    """Placeholder factory."""
    class Meta:
        model = object  # Placeholder
