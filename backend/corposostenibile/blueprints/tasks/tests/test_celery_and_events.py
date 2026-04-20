from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import (
    CheckForm,
    CheckFormTypeEnum,
    ClientCheckAssignment,
    ClientCheckResponse,
    Cliente,
    GiornoEnum,
    Review,
    StatoClienteEnum,
    Task,
    TaskCategoryEnum,
    User,
    UserRoleEnum,
    UserSpecialtyEnum,
)
from corposostenibile.blueprints.tasks import tasks as celery_tasks


@pytest.fixture(scope="module")
def app():
    return create_app()


@pytest.fixture(autouse=True)
def cleanup_test_data(app):
    marker = f"pytest-tasks-{uuid4().hex[:8]}"
    created = {
        "users": [],
        "clients": [],
        "forms": [],
        "assignments": [],
        "responses": [],
        "reviews": [],
        "tasks": [],
    }

    yield marker, created

    with app.app_context():
        db.session.rollback()
        if created["tasks"]:
            Task.query.filter(Task.id.in_(set(created["tasks"]))).delete(synchronize_session=False)
        if created["responses"]:
            ClientCheckResponse.query.filter(
                ClientCheckResponse.id.in_(set(created["responses"]))
            ).delete(synchronize_session=False)
        if created["assignments"]:
            ClientCheckAssignment.query.filter(
                ClientCheckAssignment.id.in_(set(created["assignments"]))
            ).delete(synchronize_session=False)
        if created["forms"]:
            CheckForm.query.filter(CheckForm.id.in_(set(created["forms"]))).delete(synchronize_session=False)
        if created["reviews"]:
            Review.query.filter(Review.id.in_(set(created["reviews"]))).delete(synchronize_session=False)
        if created["clients"]:
            Cliente.query.filter(Cliente.cliente_id.in_(set(created["clients"]))).delete(
                synchronize_session=False
            )
        if created["users"]:
            User.query.filter(User.id.in_(set(created["users"]))).delete(synchronize_session=False)
        db.session.commit()


def _mk_user(marker: str, created: dict, suffix: str, **kwargs) -> User:
    user = User(
        email=f"{marker}-{suffix}@example.com",
        password_hash="x",
        first_name="Pytest",
        last_name=suffix,
        role=kwargs.pop("role", UserRoleEnum.professionista),
        specialty=kwargs.pop("specialty", UserSpecialtyEnum.nutrizione),
        is_admin=False,
        **kwargs,
    )
    db.session.add(user)
    db.session.flush()
    created["users"].append(user.id)
    return user


def _mk_client(marker: str, created: dict, suffix: str, **kwargs) -> Cliente:
    client = Cliente(
        nome_cognome=f"{marker}-{suffix}",
        stato_cliente=kwargs.pop("stato_cliente", StatoClienteEnum.attivo),
        **kwargs,
    )
    db.session.add(client)
    db.session.flush()
    created["clients"].append(client.cliente_id)
    return client


def test_generate_solicitations_task_creates_once_per_day(app, monkeypatch, cleanup_test_data):
    marker, created = cleanup_test_data

    class FrozenDateTime(datetime):
        @classmethod
        def utcnow(cls):
            # Monday
            return datetime(2026, 2, 16, 9, 0, 0)

    with app.app_context():
        monkeypatch.setattr(celery_tasks, "datetime", FrozenDateTime)
        nutrizionista = _mk_user(marker, created, "nutri", specialty=UserSpecialtyEnum.nutrizione)
        client = _mk_client(
            marker,
            created,
            "sollecito",
            check_day=GiornoEnum.lun,
            nutrizionista_id=nutrizionista.id,
        )
        db.session.commit()

        out1 = celery_tasks.generate_solicitations_task()
        assert "Generated 1 solicitation tasks." in out1

        tasks = Task.query.filter_by(
            client_id=client.cliente_id,
            assignee_id=nutrizionista.id,
            category=TaskCategoryEnum.sollecito,
        ).all()
        created["tasks"].extend([t.id for t in tasks])
        assert len(tasks) == 1

        out2 = celery_tasks.generate_solicitations_task()
        assert "Generated 0 solicitation tasks." in out2
        assert (
            Task.query.filter_by(
                client_id=client.cliente_id,
                assignee_id=nutrizionista.id,
                category=TaskCategoryEnum.sollecito,
            ).count()
            == 1
        )


def test_generate_reminders_task_creates_expected_payloads(app, monkeypatch, cleanup_test_data):
    marker, created = cleanup_test_data

    class FrozenDateTime(datetime):
        @classmethod
        def utcnow(cls):
            return datetime(2026, 2, 16, 9, 0, 0)

    with app.app_context():
        monkeypatch.setattr(celery_tasks, "datetime", FrozenDateTime)
        nutri = _mk_user(marker, created, "nutri-rem", specialty=UserSpecialtyEnum.nutrizione)
        coach = _mk_user(marker, created, "coach-rem", specialty=UserSpecialtyEnum.coach)

        client = _mk_client(
            marker,
            created,
            "reminder",
            nutrizionista_id=nutri.id,
            coach_id=coach.id,
            data_rinnovo=FrozenDateTime.utcnow().date() + timedelta(days=7),
            nuova_dieta_dal=FrozenDateTime.utcnow().date() + timedelta(days=3),
            nuovo_allenamento_il=FrozenDateTime.utcnow().date(),
        )
        db.session.commit()

        out = celery_tasks.generate_reminders_task()
        assert "Generated 3 reminder tasks." in out

        reminder_tasks = Task.query.filter_by(
            client_id=client.cliente_id,
            category=TaskCategoryEnum.reminder,
        ).all()
        created["tasks"].extend([t.id for t in reminder_tasks])
        assert len(reminder_tasks) >= 3

        payload_types = {
            f"{(t.payload or {}).get('type')}:{(t.payload or {}).get('subtype')}" for t in reminder_tasks
        }
        assert "client_expiration:None" in payload_types
        assert "plan_expiration:nutrition" in payload_types
        assert "plan_expiration:training" in payload_types


def test_db_events_create_onboarding_training_and_check_tasks(app, cleanup_test_data):
    marker, created = cleanup_test_data

    with app.app_context():
        onboard_prof = _mk_user(
            marker, created, "onboard-prof", specialty=UserSpecialtyEnum.nutrizione
        )
        reviewer = _mk_user(
            marker,
            created,
            "reviewer",
            role=UserRoleEnum.team_leader,
            specialty=UserSpecialtyEnum.coach,
        )
        reviewee = _mk_user(marker, created, "reviewee", specialty=UserSpecialtyEnum.psicologia)
        coach = _mk_user(marker, created, "coach-check", specialty=UserSpecialtyEnum.coach)
        form_owner = _mk_user(marker, created, "form-owner", specialty=UserSpecialtyEnum.nutrizione)
        db.session.commit()

        # onboarding event (M2M append on nutrizionisti_multipli).
        # Nota: l'assegnazione via health_manager_id non genera piu' task (solo
        # nutrizionisti/coach/psicologi ricevono task).
        onboard_client = _mk_client(marker, created, "onboard-m2m")
        db.session.commit()
        onboard_client.nutrizionisti_multipli.append(onboard_prof)
        db.session.commit()

        onboarding_task = Task.query.filter_by(
            client_id=onboard_client.cliente_id,
            assignee_id=onboard_prof.id,
            category=TaskCategoryEnum.onboarding,
        ).order_by(Task.id.desc()).first()
        assert onboarding_task is not None
        created["tasks"].append(onboarding_task.id)

        # training event (after_insert Review)
        review = Review(
            reviewer_id=reviewer.id,
            reviewee_id=reviewee.id,
            title=f"{marker}-review",
            content="contenuto test",
            review_type="general",
        )
        db.session.add(review)
        db.session.commit()
        created["reviews"].append(review.id)

        training_task = Task.query.filter_by(
            assignee_id=reviewee.id,
            category=TaskCategoryEnum.formazione,
        ).order_by(Task.id.desc()).first()
        assert training_task is not None
        assert (training_task.payload or {}).get("review_id") == review.id
        created["tasks"].append(training_task.id)

        # check event (after_insert ClientCheckResponse)
        form = CheckForm(
            name=f"{marker}-form",
            description="form test",
            form_type=CheckFormTypeEnum.settimanale,
            created_by_id=form_owner.id,
            is_active=True,
        )
        db.session.add(form)
        db.session.commit()
        created["forms"].append(form.id)

        check_client = _mk_client(marker, created, "check-event")
        db.session.commit()

        assignment = ClientCheckAssignment(
            cliente_id=check_client.cliente_id,
            form_id=form.id,
            token=f"{marker}-tok",
            assigned_by_id=coach.id,
            is_active=True,
        )
        db.session.add(assignment)
        db.session.commit()
        created["assignments"].append(assignment.id)

        response = ClientCheckResponse(
            assignment_id=assignment.id,
            responses={"q1": "ok"},
            notifications_sent=False,
        )
        db.session.add(response)
        db.session.commit()
        created["responses"].append(response.id)

        check_task = Task.query.filter_by(
            client_id=check_client.cliente_id,
            assignee_id=coach.id,
            category=TaskCategoryEnum.check,
        ).order_by(Task.id.desc()).first()
        assert check_task is not None
        assert (check_task.payload or {}).get("check_response_id") == response.id
        created["tasks"].append(check_task.id)
