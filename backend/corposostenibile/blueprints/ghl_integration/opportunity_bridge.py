"""
opportunity_bridge
=================

Bridge tra webhook opportunity-data e sistema Check Iniziali.
Quando GHL invia dati con email (lead vinta), crea Cliente, assegna Check 1/2/3
e invia una singola email con i tre link.
"""

from __future__ import annotations

from typing import Dict, Any, List

from flask import current_app

from corposostenibile.extensions import db
from corposostenibile.models import (
    Cliente, User, CheckForm, CheckFormTypeEnum,
    ClientCheckAssignment, GHLOpportunityData,
)


# Check iniziali da assegnare (come in processors.py)
INITIAL_CHECKS = [
    {"name": "Check 1 - Anagrafica", "type": "iniziale", "description": "Dati anagrafici e obiettivi"},
    {"name": "Check 2 - Fisico", "type": "iniziale", "description": "Misure e foto"},
    {"name": "Check 3 - Psico-Alimentare", "type": "iniziale", "description": "Questionario approfondito"},
]


def process_opportunity_data_bridge(opp_data: GHLOpportunityData) -> Dict[str, Any]:
    """
    Dopo il salvataggio di GHLOpportunityData, se email è presente:
    1. Crea/aggiorna Cliente (nome, email)
    2. Crea i 3 ClientCheckAssignment (Check 1, 2, 3) – con auto-seeding form se mancanti
    3. Invia una sola email con i 3 link

    Returns:
        Dict con success, cliente_id, assignments_count, email_sent
    """
    result = {"success": False, "cliente_id": None, "assignments_count": 0, "email_sent": False}

    if opp_data.processed:
        current_app.logger.info(f"[opportunity_bridge] Skipping opp_data {opp_data.id}: già processato")
        return result

    email = (opp_data.email or "").strip()
    if not email:
        current_app.logger.info(
            f"[opportunity_bridge] Skipping opp_data {opp_data.id}: nessuna email"
        )
        return result

    nome = (opp_data.nome or "N/D").strip()
    if nome == "N/D" and opp_data.raw_payload:
        payload = opp_data.raw_payload or {}
        custom = payload.get("customData", {})
        nome = (
            custom.get("nome") or payload.get("nome") or payload.get("full_name")
            or payload.get("opportunity_name")
            or f"{payload.get('first_name', '')} {payload.get('last_name', '')}".strip()
            or "N/D"
        )

    try:
        # 1. Crea o recupera Cliente
        cliente = Cliente.query.filter_by(mail=email).first()
        if not cliente:
            cliente = Cliente(
                nome_cognome=nome,
                mail=email,
                service_status='pending_assignment',
                show_in_clienti_lista=False,
            )
            db.session.add(cliente)
            db.session.flush()
            current_app.logger.info(f"[opportunity_bridge] Creato nuovo Cliente {cliente.cliente_id}")
        else:
            # Aggiorna nome se diverso
            if cliente.nome_cognome != nome:
                cliente.nome_cognome = nome
            current_app.logger.info(f"[opportunity_bridge] Riutilizzato Cliente {cliente.cliente_id}")

        # 2. Ottieni admin per assigned_by_id
        admin_user = User.query.filter_by(is_admin=True).first() or User.query.first()
        if not admin_user:
            raise RuntimeError("[opportunity_bridge] Nessun utente disponibile per assigned_by_id")
        admin_id = admin_user.id

        # 3. Crea/assegna i 3 Check (senza invio notifiche individuali)
        assignments: List[ClientCheckAssignment] = []
        for check_data in INITIAL_CHECKS:
            check_form = CheckForm.query.filter_by(
                name=check_data["name"],
                form_type=CheckFormTypeEnum.iniziale,
            ).first()

            # Auto-seeding se non esiste
            if not check_form:
                check_form = CheckForm(
                    name=check_data["name"],
                    description=check_data["description"],
                    form_type=CheckFormTypeEnum.iniziale,
                    is_active=True,
                    created_by_id=admin_id,
                    # In suite-clinica i form iniziali devono poter esistere anche senza reparti.
                    department_id=None,
                )
                db.session.add(check_form)
                db.session.flush()
                current_app.logger.info(f"[opportunity_bridge] Creato form: {check_form.name}")

            # Verifica se già assegnato
            existing = ClientCheckAssignment.query.filter_by(
                cliente_id=cliente.cliente_id,
                form_id=check_form.id,
                is_active=True,
            ).first()

            if existing:
                assignments.append(existing)
                current_app.logger.debug(f"[opportunity_bridge] Assegnazione già esistente: {check_form.name}")
            else:
                assignment = ClientCheckAssignment(
                    cliente_id=cliente.cliente_id,
                    form_id=check_form.id,
                    token=ClientCheckAssignment.generate_token(),
                    assigned_by_id=admin_id,
                    is_active=True,
                )
                db.session.add(assignment)
                assignments.append(assignment)

        db.session.commit()

        result["cliente_id"] = cliente.cliente_id
        result["assignments_count"] = len(assignments)

        # 4. Invia email con i 3 link (una sola email)
        if assignments:
            from corposostenibile.blueprints.client_checks.services import send_initial_checks_single_email
            send_initial_checks_single_email(cliente, assignments)
            result["email_sent"] = True

        # Marca come processato
        opp_data.processed = True
        db.session.commit()

        result["success"] = True
        current_app.logger.info(
            f"[opportunity_bridge] Completato: Cliente {cliente.cliente_id}, "
            f"{len(assignments)} check assegnati, email inviata={result['email_sent']}"
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"[opportunity_bridge] Errore: {e}")
        raise

    return result
