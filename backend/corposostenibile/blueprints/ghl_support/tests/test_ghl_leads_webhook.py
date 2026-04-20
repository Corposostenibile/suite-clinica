from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import patch

from corposostenibile.models import GHLOpportunityData

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
                "nome": f"Lead Test {uniq}",
                "email": f"ghl-leads-{uniq}@example.com",
                "telefono": "+39 333 4445566",
                "sales_consultant": "Sales Demo",
                "health_manager_email": "hm@example.com",
                "pacchetto": "Premium 90 giorni",
                "durata": "90",
                "storia": "Payload di test per il webhook GHL leads new",
            },
        },
        "contact": {
            "id": f"contact_{uniq}",
            "name": f"Lead Test {uniq}",
            "email": f"ghl-leads-{uniq}@example.com",
            "phone": "+39 333 4445566",
        },
    }


def test_ghl_leads_new_webhook_requires_valid_hmac_and_persists_lead(app, db_session):
    payload = _build_payload()
    body = json.dumps(payload).encode("utf-8")

    with app.app_context():
        client = app.test_client()
        with patch(
            "corposostenibile.blueprints.ghl_integration.opportunity_bridge.process_opportunity_data_bridge",
            return_value={"success": True, "skipped": True},
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
        assert data["id"]

        saved = GHLOpportunityData.query.filter_by(email=payload["contact"]["email"]).first()
        assert saved is not None
        assert saved.nome == payload["opportunity"]["custom_fields"]["nome"]
        assert saved.lead_phone == payload["contact"]["phone"]
        assert saved.sales_consultant == payload["opportunity"]["custom_fields"]["sales_consultant"]
        assert saved.raw_payload["opportunity"]["id"] == payload["opportunity"]["id"]


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


def test_webhook_urls_expose_ghl_leads_new_endpoint(app):
    with app.app_context():
        client = app.test_client()
        response = client.get("/ghl/api/webhook-urls")

    assert response.status_code == 200
    data = response.get_json()
    assert data["ghl_leads_new_url"].endswith("/webhooks/ghl-leads/new")
