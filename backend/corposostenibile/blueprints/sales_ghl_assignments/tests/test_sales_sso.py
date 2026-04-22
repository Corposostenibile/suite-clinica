from __future__ import annotations

import jwt as pyjwt
from uuid import uuid4

from corposostenibile.extensions import db
from corposostenibile.models import LeadStatusEnum, SalesLead, User, UserRoleEnum


def _create_user(email: str, *, is_admin: bool = False, role=UserRoleEnum.professionista) -> User:
    user = User(
        email=email,
        password_hash="x",
        first_name="Test",
        last_name=email.split("@")[0],
        role=role,
        is_admin=is_admin,
        is_active=True,
    )
    db.session.add(user)
    db.session.flush()
    return user


def _create_sales_lead(email: str, *, sales_user_id: int | None = None) -> SalesLead:
    lead = SalesLead(
        source_system="ghl",
        unique_code=f"GHL-LEAD-{uuid4().hex[:8].upper()}",
        first_name="Lead",
        last_name="Queue",
        email=email,
        status=LeadStatusEnum.NEW,
        sales_user_id=sales_user_id,
    )
    db.session.add(lead)
    db.session.flush()
    return lead


def test_sales_sso_exchange_returns_jwt_and_allows_queue_access(app):
    sales_email = f"sales-{uuid4().hex[:6]}@example.com"

    with app.app_context():
        sales_user = _create_user(sales_email)
        _create_sales_lead(f"lead-{uuid4().hex[:6]}@example.com", sales_user_id=sales_user.id)
        db.session.commit()

        client = app.test_client()
        exchange_response = client.post(
            "/api/ghl-assignments/sso/exchange",
            json={"user_email": sales_email},
        )

        assert exchange_response.status_code == 200
        exchange_data = exchange_response.get_json()
        assert exchange_data["success"] is True
        assert exchange_data["scope"] == "sales"
        assert exchange_data["sales_user"]["sales_user_id"] == sales_user.id
        assert exchange_data["token"]

        token_payload = pyjwt.decode(
            exchange_data["token"],
            app.config["GHL_SSO_SIGNING_KEY"],
            algorithms=["HS256"],
            issuer="suite-clinica-sales-ghl",
        )
        assert token_payload["scope"] == "sales"
        assert token_payload["sales_user_id"] == sales_user.id

        list_response = client.get(
            "/api/ghl-assignments",
            headers={"Authorization": f"Bearer {exchange_data['token']}"},
        )

        assert list_response.status_code == 200
        list_data = list_response.get_json()
        assert list_data["auth_mode"] == "jwt"
        assert list_data["current_user_id"] == sales_user.id
        assert any(item["email"].startswith("lead-") for item in list_data["assignments"])


def test_sales_sso_exchange_rejects_unknown_email(app):
    with app.app_context():
        client = app.test_client()
        response = client.post(
            "/api/ghl-assignments/sso/exchange",
            json={"user_email": f"missing-{uuid4().hex[:6]}@example.com"},
        )

    assert response.status_code == 401


def test_sales_assignments_rejects_wrong_scope_token(app):
    sales_email = f"sales-{uuid4().hex[:6]}@example.com"

    with app.app_context():
        sales_user = _create_user(sales_email)
        _create_sales_lead(f"lead-{uuid4().hex[:6]}@example.com", sales_user_id=sales_user.id)
        db.session.commit()

        bad_token = pyjwt.encode(
            {
                "sub": str(sales_user.id),
                "user_id": sales_user.id,
                "sales_user_id": sales_user.id,
                "email": sales_email,
                "scope": "admin",
                "iss": "suite-clinica-sales-ghl",
            },
            app.config["GHL_SSO_SIGNING_KEY"],
            algorithm="HS256",
        )
        if not isinstance(bad_token, str):
            bad_token = bad_token.decode("utf-8")

        client = app.test_client()
        response = client.get(
            "/api/ghl-assignments",
            headers={"Authorization": f"Bearer {bad_token}"},
        )

    assert response.status_code == 401
