#!/usr/bin/env python3
"""
Webhook di prova per /ghl/webhook/opportunity-data.

Esegue 3 varianti del payload:
- JSON completo con opportunity.custom_fields
- JSON wrapper con payload stringificato
- form-data con customData stringa JSON

Uso:
    cd backend && python test_ghl_opportunity_data_webhooks.py
"""
from __future__ import annotations

import json
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("FLASK_ENV", "development")

from corposostenibile import create_app  # noqa: E402
from corposostenibile.extensions import db  # noqa: E402
from corposostenibile.models import GHLOpportunityData, SalesPerson, User  # noqa: E402

WEBHOOK_PATH = "/ghl/webhook/opportunity-data"


@dataclass
class WebhookCase:
    name: str
    mode: str
    payload: dict
    expected_email: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pick_sales_consultant(app) -> str:
    try:
        with app.app_context():
            sales_person = SalesPerson.query.first()
            if sales_person and getattr(sales_person, "full_name", None):
                return sales_person.full_name
            fallback = User.query.filter(User.role.in_(["team_leader", "admin"])).first()
            if fallback and getattr(fallback, "full_name", None):
                return fallback.full_name
    except Exception:
        pass
    return "Sales Demo"


def _build_cases(app) -> list[WebhookCase]:
    sales_consultant = _pick_sales_consultant(app)

    json_email = f"ghl-json-{uuid4().hex[:8]}@example.com"
    wrapper_email = f"ghl-wrapper-{uuid4().hex[:8]}@example.com"
    form_email = f"ghl-form-{uuid4().hex[:8]}@example.com"

    cases = [
        WebhookCase(
            name="JSON completo",
            mode="json",
            expected_email=json_email,
            payload={
                "event_type": "opportunity.data_ready",
                "timestamp": _utc_now(),
                "opportunity": {
                    "id": f"opp_json_{uuid4().hex[:8]}",
                    "status": "new",
                    "pipeline_name": "Sales Pipeline",
                    "custom_fields": {
                        "nome": "Mario Rossi JSON",
                        "email": json_email,
                        "telefono": "+39 333 1000001",
                        "sales_consultant": sales_consultant,
                        "health_manager_email": "hm@example.com",
                        "pacchetto": "Premium 90 giorni",
                        "durata": "90",
                        "storia": "Payload JSON completo per test webhook",
                    },
                },
                "contact": {
                    "id": f"contact_json_{uuid4().hex[:8]}",
                    "name": "Mario Rossi JSON",
                    "email": json_email,
                    "phone": "+39 333 1000001",
                },
            },
        ),
        WebhookCase(
            name="Wrapper payload string",
            mode="json-wrapper",
            expected_email=wrapper_email,
            payload={
                "payload": json.dumps(
                    {
                        "event_type": "opportunity.data_ready",
                        "timestamp": _utc_now(),
                        "opportunity": {
                            "id": f"opp_wrap_{uuid4().hex[:8]}",
                            "status": "new",
                            "pipeline_name": "Sales Pipeline",
                            "custom_fields": {
                                "nome": "Mario Rossi Wrapper",
                                "email": wrapper_email,
                                "phone": "+39 333 1000002",
                                "sales_person": sales_consultant,
                                "pacchetto": "Advanced 60 giorni",
                                "durata": "60",
                                "storia": "Payload annidato in una stringa JSON",
                            },
                        },
                        "contact": {
                            "id": f"contact_wrap_{uuid4().hex[:8]}",
                            "name": "Mario Rossi Wrapper",
                            "email": wrapper_email,
                            "phone": "+39 333 1000002",
                        },
                    }
                ),
            },
        ),
        WebhookCase(
            name="Form-data customData string",
            mode="form-data",
            expected_email=form_email,
            payload={
                "customData": json.dumps(
                    {
                        "nome": "Mario Rossi Form",
                        "email": form_email,
                        "telefono": "+39 333 1000003",
                        "sales_owner": sales_consultant,
                        "pacchetto": "Base 30 giorni",
                        "durata": "30",
                        "storia": "Payload form-data con customData stringa JSON",
                    }
                ),
                "full_name": "Mario Rossi Form",
            },
        ),
    ]

    return cases


@contextmanager
def _disable_bridge():
    """Disabilita il bridge per mantenere il test webhook isolato."""
    import corposostenibile.blueprints.ghl_integration.opportunity_bridge as opportunity_bridge  # noqa: E402

    original = opportunity_bridge.process_opportunity_data_bridge
    opportunity_bridge.process_opportunity_data_bridge = lambda opp_data: {
        "success": True,
        "skipped": True,
        "reason": "disabled in webhook test script",
    }
    try:
        yield
    finally:
        opportunity_bridge.process_opportunity_data_bridge = original


def _post_case(client, case: WebhookCase):
    if case.mode == "json":
        return client.post(WEBHOOK_PATH, json=case.payload)
    if case.mode == "json-wrapper":
        return client.post(WEBHOOK_PATH, json=case.payload)
    if case.mode == "form-data":
        return client.post(WEBHOOK_PATH, data=case.payload)
    raise ValueError(f"Modalità sconosciuta: {case.mode}")


def main() -> int:
    app = create_app()
    cases = _build_cases(app)

    with app.app_context():
        client = app.test_client()
        print("\n=== GHL opportunity-data webhook test ===\n")
        print("Bridge disattivato: test isolato del webhook e della normalizzazione payload.\n")

        with _disable_bridge():
            for case in cases:
                print(f"→ Caso: {case.name}")
                response = _post_case(client, case)
                print(f"  Status: {response.status_code}")

                if not response.is_json:
                    print(f"  Response: {response.data.decode('utf-8', errors='replace')}")
                    return 1

                data = response.get_json() or {}
                print(f"  Response JSON: {json.dumps(data, indent=2, ensure_ascii=False)}")

                if response.status_code != 200 or not data.get("success"):
                    print(f"  ❌ Webhook fallito per il caso: {case.name}")
                    return 1

                created_id = data.get("id")
                saved = db.session.get(GHLOpportunityData, created_id)
                if not saved:
                    print(f"  ❌ Record non trovato nel DB (id={created_id})")
                    return 1

                print(
                    "  ✅ Salvato:",
                    {
                        "id": saved.id,
                        "nome": saved.nome,
                        "email": saved.email,
                        "sales_consultant": saved.sales_consultant,
                        "sales_person_id": saved.sales_person_id,
                        "processed": saved.processed,
                    },
                )
                print()

        print("Tutti i webhook di prova sono andati a buon fine.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
