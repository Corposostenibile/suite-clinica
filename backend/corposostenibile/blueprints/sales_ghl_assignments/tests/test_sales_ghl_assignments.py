from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import patch

from corposostenibile.extensions import db
from corposostenibile.models import SalesLead, User, UserRoleEnum

WEBHOOK_PATH = "/webhooks/ghl-leads/new"
WEBHOOK_SECRET = "test-ghl-webhook-secret"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _signature(body: bytes) -> str:
    digest = hmac.new(WEBHOOK_SECRET.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _build_payload() -> dict:
    uniq = uuid4().hex[:8]
    return {
        "event_type": "lead.created",
        "timestamp": _utc_now(),
        "opportunity": {
            "id": f"opp_{uniq}",
            "status": "new",
            "pipeline_name": "Sales Pipeline",
            "custom_fields": {
                "first_name": "Lead",
                "last_name": f"Test{uniq}",
                "email": f"ghl-leads-{uniq}@example.com",
                "telefono": "+39 333 4445566",
                "sales_user_email": f"sales-owner-{uniq}@example.com",
                "health_manager_email": f"hm-{uniq}@example.com",
                "pacchetto": "Premium 90 giorni",
                "storia": "Payload di test per il webhook GHL leads new",
                "origin": "Facebook Ads",
                "utm_campaign": "campagna-ghl",
            },
        },
        "contact": {
            "id": f"contact_{uniq}",
            "name": f"Lead Test {uniq}",
            "email": f"ghl-leads-{uniq}@example.com",
            "phone": "+39 333 4445566",
        },
    }


def _create_user(email: str, *, is_admin: bool = False, role=UserRoleEnum.professionista) -> int:
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
    return int(user.id)


def test_ghl_leads_new_webhook_saves_saleslead_and_matches_sales_user(app):
    payload = _build_payload()
    body = json.dumps(payload).encode("utf-8")
    sales_user_email = payload["opportunity"]["custom_fields"]["sales_user_email"]
    health_manager_email = payload["opportunity"]["custom_fields"]["health_manager_email"]

    with app.app_context():
        sales_user_id = _create_user(sales_user_email)
        health_manager_id = _create_user(health_manager_email)
        admin_id = _create_user(f"admin-{uuid4().hex[:6]}@example.com", is_admin=True, role=UserRoleEnum.admin)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as sess:
            sess["_user_id"] = str(admin_id)
            sess["_fresh"] = True

        with patch(
            "corposostenibile.blueprints.sales_form.services.LinkService.create_all_links_for_lead",
            return_value=[],
        ):
            response = client.post(
                WEBHOOK_PATH,
                data=body,
                content_type="application/json",
                headers={"X-GHL-Signature": _signature(body)},
            )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["created"] is True
        assert data["id"]

        saved = SalesLead.query.filter_by(
            email=payload["contact"]["email"],
            source_system="ghl",
        ).first()
        assert saved is not None
        assert saved.first_name == payload["opportunity"]["custom_fields"]["first_name"]
        assert saved.last_name == payload["opportunity"]["custom_fields"]["last_name"]
        assert saved.phone == payload["contact"]["phone"]
        assert saved.sales_user_id == sales_user_id
        assert saved.health_manager_id == health_manager_id
        assert saved.origin == payload["opportunity"]["custom_fields"]["origin"]
        assert saved.custom_package_name == payload["opportunity"]["custom_fields"]["pacchetto"]
        assert saved.source_campaign == payload["opportunity"]["custom_fields"]["utm_campaign"]
        assert saved.form_responses["source_system"] == "ghl"
        assert saved.form_responses["raw_payload"]["opportunity"]["id"] == payload["opportunity"]["id"]

        list_response = client.get("/api/ghl-assignments", query_string={"status": "all"})
        assert list_response.status_code == 200
        list_data = list_response.get_json()
        assert list_data["total"] >= 1
        assert any(item["id"] == saved.id for item in list_data["assignments"])


def test_ghl_leads_new_webhook_rejects_invalid_hmac(app):
    payload = _build_payload()
    body = json.dumps(payload).encode("utf-8")

    with app.app_context():
        client = app.test_client()
        response = client.post(
            WEBHOOK_PATH,
            data=body,
            content_type="application/json",
            headers={"X-GHL-Signature": "sha256=deadbeef"},
        )

    assert response.status_code == 401
