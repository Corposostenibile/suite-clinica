#!/usr/bin/env python3
"""
Test end-to-end per il flusso AI delle assegnazioni:
1) crea un lead GHL via webhook /ghl/webhook/opportunity-data
2) analizza la storia con /api/team/assignments/analyze-lead
3) trova i professionisti con /api/team/assignments/match
4) conferma l'assegnazione con /api/team/assignments/confirm usando opportunity_data_id

Uso:
    cd backend && python test_ghl_ai_assignment_flow.py
"""
from __future__ import annotations

import json
import os
import sys
from contextlib import contextmanager
from unittest.mock import patch
from datetime import datetime, timezone
from uuid import uuid4

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("FLASK_ENV", "development")

from corposostenibile import create_app  # noqa: E402
from sqlalchemy import text  # noqa: E402
from corposostenibile.extensions import db  # noqa: E402
from corposostenibile.models import Cliente, GHLOpportunityData, ServiceClienteAssignment, User  # noqa: E402
from corposostenibile.blueprints.team.ai_matching_service import AIMatchingService  # noqa: E402


@contextmanager
def _disable_bridge():
    """Disabilita il bridge per mantenere il test isolato sul flusso AI."""
    import corposostenibile.blueprints.ghl_integration.opportunity_bridge as opportunity_bridge  # noqa: E402

    original = opportunity_bridge.process_opportunity_data_bridge
    opportunity_bridge.process_opportunity_data_bridge = lambda opp_data: {
        "success": True,
        "skipped": True,
        "reason": "disabled in AI test script",
    }
    try:
        yield
    finally:
        opportunity_bridge.process_opportunity_data_bridge = original


@contextmanager
def _mock_ai_analysis():
    """Sostituisce la chiamata Gemini con un'analisi deterministica."""
    mock_analysis = {
        "summary": "Analisi mock per test AI",
        "criteria": ["DONNE", "ETA' 18-55", "FAME EMOTIVA"],
        "suggested_focus": ["Gestione fame nervosa", "Educazione alimentare", "Costanza sul piano"]
    }
    with patch.object(AIMatchingService, "extract_lead_criteria", return_value=mock_analysis):
        yield


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _login_admin(client, app) -> User:
    with app.app_context():
        admin = (
            User.query.filter(User.is_admin.is_(True)).first()
            or User.query.filter(User.role == "admin").first()
        )
        if not admin:
            raise RuntimeError("Nessun utente admin trovato nel database")

    with client.session_transaction() as sess:
        sess["_user_id"] = str(admin.id)
        sess["_fresh"] = True

    return admin


def _build_webhook_payload() -> dict:
    uniq = uuid4().hex[:8]
    email = f"ai-flow-{uniq}@example.com"
    return {
        "event_type": "opportunity.data_ready",
        "timestamp": _utc_now(),
        "opportunity": {
            "id": f"opp_ai_{uniq}",
            "status": "new",
            "pipeline_name": "AI Assignment Pipeline",
            "custom_fields": {
                "nome": "Maria Rossi AI",
                "email": email,
                "telefono": "+39 333 2223344",
                "sales_consultant": "Sales Demo",
                "health_manager_email": "hm@example.com",
                "pacchetto": "Percorso Dimagrimento 90 giorni",
                "durata": "90",
                "storia": (
                    "La cliente riferisce aumento di peso negli ultimi anni, "
                    "fame nervosa serale, difficoltà a seguire la dieta con costanza "
                    "e desidera supporto nutrizionale per perdere 12 kg."
                ),
            },
        },
        "contact": {
            "id": f"contact_ai_{uniq}",
            "name": "Maria Rossi AI",
            "email": email,
            "phone": "+39 333 2223344",
        },
    }


def _extract_criteria(analysis):
    if isinstance(analysis, dict):
        criteria = analysis.get("criteria")
        if isinstance(criteria, list):
            return criteria
        # fallback per strutture annidate
        for key in ("nutrition", "coach", "psychology"):
            part = analysis.get(key)
            if isinstance(part, dict):
                criteria = part.get("criteria")
                if isinstance(criteria, list):
                    return criteria
    return []


def _sync_sequence(table_name: str, pk_column: str) -> None:
    db.session.execute(
        text(
            f"SELECT setval(pg_get_serial_sequence('{table_name}', '{pk_column}'), "
            f"(SELECT COALESCE(MAX({pk_column}), 1) FROM {table_name}), true)"
        )
    )


def _pick_first_match(matches):
    role_order = [
        ("nutrizione", "nutritionist_id"),
        ("nutrition", "nutritionist_id"),
        ("coach", "coach_id"),
        ("psicologia", "psychologist_id"),
        ("psychology", "psychologist_id"),
    ]
    for role_key, confirm_field in role_order:
        candidates = matches.get(role_key)
        if isinstance(candidates, list) and candidates:
            candidate = candidates[0]
            if isinstance(candidate, dict) and candidate.get("id"):
                return confirm_field, candidate
    return None, None


def main() -> int:
    app = create_app()
    with app.app_context():
        client = app.test_client()
        admin = _login_admin(client, app)
        print(f"Admin usato: {admin.full_name} <{admin.email}>")
        print("\n=== AI assignment flow test ===\n")

        webhook_payload = _build_webhook_payload()
        with _disable_bridge():
            res = client.post("/ghl/webhook/opportunity-data", json=webhook_payload)
        print(f"Webhook status: {res.status_code}")
        if not res.is_json or res.status_code != 200:
            print(res.data.decode("utf-8", errors="replace"))
            return 1
        webhook_data = res.get_json() or {}
        print("Webhook response:", json.dumps(webhook_data, indent=2, ensure_ascii=False))

        opp_id = int(webhook_data.get("id"))
        opp = db.session.get(GHLOpportunityData, opp_id)
        if not opp:
            print(f"Lead non trovato nel DB (id={opp_id})")
            return 1
        opp_email = opp.email
        opp_name = opp.nome
        opp_story = opp.storia

        print(f"Lead creato: #{opp_id} - {opp_name} - {opp_email}")

        with _mock_ai_analysis():
            analyze_payload = {
                "story": opp_story,
                "opportunity_id": opp_id,
                "role": "nutrition",
                "force_refresh": True,
            }
            res = client.post("/api/team/assignments/analyze-lead", json=analyze_payload)
            print(f"Analyze status: {res.status_code}")
            if not res.is_json or res.status_code != 200:
                print(res.data.decode("utf-8", errors="replace"))
                return 1
            analyze_data = res.get_json() or {}
            print("Analyze response:", json.dumps(analyze_data, indent=2, ensure_ascii=False))

            analysis = analyze_data.get("analysis")
            criteria = _extract_criteria(analysis)
            if not criteria:
                criteria = ["DONNE", "ETA' 18-55", "FAME EMOTIVA"]
                print("Nessun criterio estratto dall'analisi AI: uso fallback deterministico.")
            print(f"Criteri usati per il match: {criteria}")

            res = client.post("/api/team/assignments/match", json={"criteria": criteria})
            print(f"Match status: {res.status_code}")
            if not res.is_json or res.status_code != 200:
                print(res.data.decode("utf-8", errors="replace"))
                return 1
            match_data = res.get_json() or {}
            print("Match response:", json.dumps(match_data, indent=2, ensure_ascii=False))

            matches = match_data.get("matches") or {}
            confirm_field, candidate = _pick_first_match(matches)
            if not candidate:
                print("Nessun professionista trovato nei match AI.")
                return 1

            _sync_sequence('clienti', 'cliente_id')
            _sync_sequence('service_cliente_assignments', 'id')
            db.session.commit()

            confirm_payload = {
                "opportunity_data_id": opp_id,
                "ai_analysis": analysis,
                "notes": "Test automatico AI assignment flow",
                confirm_field: candidate["id"],
            }
            res = client.post("/api/team/assignments/confirm", json=confirm_payload)
            print(f"Confirm status: {res.status_code}")
            if not res.is_json or res.status_code != 200:
                print(res.data.decode("utf-8", errors="replace"))
                return 1
            confirm_data = res.get_json() or {}
            print("Confirm response:", json.dumps(confirm_data, indent=2, ensure_ascii=False))

        db.session.expire_all()
        refreshed_opp = db.session.get(GHLOpportunityData, opp_id)
        # La verifica migliore è per email cliente: il confirm crea il cliente/assignment se assenti.
        cliente = Cliente.query.filter(Cliente.mail.ilike(opp_email)).first()
        if not cliente:
            print("Cliente non creato durante la conferma.")
            return 1
        assignment = ServiceClienteAssignment.query.filter_by(cliente_id=cliente.cliente_id).first()
        if not assignment:
            print("Assegnazione non creata durante la conferma.")
            return 1

        print(
            "\nVerifica finale:",
            {
                "lead_processed": refreshed_opp.processed,
                "cliente_id": cliente.cliente_id,
                "assignment_id": assignment.id,
                "status": assignment.status,
                "nutritionist_id": assignment.nutrizionista_assigned_id,
                "coach_id": assignment.coach_assigned_id,
                "psychologist_id": assignment.psicologa_assigned_id,
            },
        )

        if not refreshed_opp.processed:
            print("Lead non marcato come processato.")
            return 1

        print("\nFlusso AI completato con successo.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
