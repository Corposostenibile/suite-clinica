"""
opportunity_bridge
=================

Bridge tra webhook opportunity-data e sistema Check Iniziali.
Quando GHL invia dati con email (lead vinta), crea Cliente, assegna 2 check iniziali
e invia una singola email con i link.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional

from flask import current_app

from corposostenibile.extensions import db
from corposostenibile.models import (
    Cliente, User, CheckForm, CheckFormTypeEnum,
    ClientCheckAssignment, GHLOpportunityData,
)
from corposostenibile.blueprints.client_checks.services import _public_checks_base_url


# Check iniziali da assegnare
INITIAL_CHECKS = [
    {
        "name": "Check 1 - PRE-CHECK INIZIALE",
        "type": "iniziale",
        "description": "Questionario iniziale completo (profilo clinico, alimentare e stile di vita).",
    },
    {
        "name": "Check 2 - Mockup Follow-up Iniziale",
        "type": "iniziale",
        "description": "Mockup temporaneo in attesa del secondo questionario definitivo.",
    },
]


def _resolve_health_manager_id_by_email(email: Optional[str]) -> Optional[int]:
    if not email:
        return None

    hm_user = User.query.filter(
        User.email.ilike(email.strip()),
        User.is_active == True,
    ).first()
    return hm_user.id if hm_user else None


def process_opportunity_data_bridge(opp_data: GHLOpportunityData) -> Dict[str, Any]:
    """
    Dopo il salvataggio di GHLOpportunityData, se email è presente:
    1. Crea/aggiorna Cliente (nome, email)
    2. Crea i 2 ClientCheckAssignment – con auto-seeding form se mancanti
    3. Invia una sola email con i link

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
    lead_phone = (opp_data.lead_phone or "").strip()
    hm_id = opp_data.health_manager_id or _resolve_health_manager_id_by_email(opp_data.health_manager_email)
    if nome == "N/D" and opp_data.raw_payload:
        payload = opp_data.raw_payload or {}
        custom = payload.get("customData", {})
        nome = (
            custom.get("nome") or payload.get("nome") or payload.get("full_name")
            or payload.get("opportunity_name")
            or f"{payload.get('first_name', '')} {payload.get('last_name', '')}".strip()
            or "N/D"
        )
        if not lead_phone:
            contact = payload.get("contact", {}) if isinstance(payload.get("contact"), dict) else {}
            lead_phone = (
                custom.get("telefono")
                or custom.get("phone")
                or custom.get("cellulare")
                or payload.get("telefono")
                or payload.get("phone")
                or payload.get("cellulare")
                or contact.get("phone")
                or ""
            ).strip()

    try:
        # 1. Crea o recupera Cliente
        cliente = Cliente.query.filter_by(mail=email).first()
        if not cliente:
            cliente = Cliente(
                nome_cognome=nome,
                mail=email,
                health_manager_id=hm_id,
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
            if lead_phone:
                cliente.cellulare = lead_phone
            if hm_id and not getattr(cliente, "health_manager_id", None):
                cliente.health_manager_id = hm_id
            current_app.logger.info(f"[opportunity_bridge] Riutilizzato Cliente {cliente.cliente_id}")

        if lead_phone and not getattr(cliente, "cellulare", None):
            cliente.cellulare = lead_phone
        if hm_id and not getattr(cliente, "health_manager_id", None):
            cliente.health_manager_id = hm_id

        # 2. Ottieni admin per assigned_by_id
        admin_user = User.query.filter_by(is_admin=True).first() or User.query.first()
        if not admin_user:
            raise RuntimeError("[opportunity_bridge] Nessun utente disponibile per assigned_by_id")
        admin_id = admin_user.id

        # 3. Crea/assegna i check iniziali (senza invio notifiche individuali)
        assignments: List[ClientCheckAssignment] = []
        attempted_seed = False
        for check_data in INITIAL_CHECKS:
            check_form = CheckForm.query.filter_by(
                name=check_data["name"],
                form_type=CheckFormTypeEnum.iniziale,
            ).first()

            # Prova seed completo dei check iniziali se i form non sono presenti
            if not check_form and not attempted_seed:
                try:
                    from corposostenibile.blueprints.client_checks.scripts.seed_initial_checks import seed_initial_checks

                    seed_initial_checks()
                    attempted_seed = True
                    check_form = CheckForm.query.filter_by(
                        name=check_data["name"],
                        form_type=CheckFormTypeEnum.iniziale,
                    ).first()
                    current_app.logger.info("[opportunity_bridge] Seed check iniziali eseguito on-demand")
                except Exception as seed_err:
                    current_app.logger.warning(
                        f"[opportunity_bridge] Seed on-demand fallito: {seed_err}"
                    )

            # Fallback minimo se ancora non esiste
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

        # 4. Invia email con i link (una sola email)
        if assignments:
            from corposostenibile.blueprints.client_checks.services import send_initial_checks_single_email
            send_initial_checks_single_email(cliente, assignments)
            result["email_sent"] = True

            # 5. Sync verso Respond.io (assegna chat a HM + messaggio presentazione + messaggio link check)
            respond_sync = _sync_respond_io_on_initial_checks_sent(
                cliente=cliente,
                lead_phone=(opp_data.lead_phone or getattr(cliente, "cellulare", None) or "").strip(),
                health_manager_email=(opp_data.health_manager_email or "").strip().lower() or None,
                assignments=assignments,
            )
            result["respond_io"] = respond_sync

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


def _build_respond_identifier(*, phone: str, email: str) -> Optional[str]:
    phone_clean = (phone or "").strip().replace(" ", "")
    if phone_clean:
        return f"phone:{phone_clean}"

    email_clean = (email or "").strip().lower()
    if email_clean:
        return f"email:{email_clean}"

    return None


def _sync_respond_io_on_initial_checks_sent(
    *,
    cliente: Cliente,
    lead_phone: str,
    health_manager_email: Optional[str],
    assignments: List[ClientCheckAssignment],
) -> Dict[str, Any]:
    """
    Chiamate Respond.io nel momento in cui inviamo la mail con i check iniziali:
    1) Assign conversazione all'HM
    2) Template 1: suite_benvenuto (presentazione HM)
    3) Template 2: suite_check (link ai check iniziali)
    """
    sync_result: Dict[str, Any] = {
        "enabled": False,
        "identifier": None,
        "assigned": False,
        "presentation_sent": False,
        "check_links_sent": False,
        "errors": [],
    }

    api_token = current_app.config.get("RESPOND_IO_API_TOKEN")
    if not api_token:
        current_app.logger.info(
            "[opportunity_bridge] Respond.io non configurato (RESPOND_IO_API_TOKEN assente), skip sync"
        )
        return sync_result

    identifier = _build_respond_identifier(
        phone=lead_phone,
        email=getattr(cliente, "mail", None) or getattr(cliente, "email", None) or "",
    )
    if not identifier:
        sync_result["errors"].append("missing_identifier")
        current_app.logger.warning(
            "[opportunity_bridge] Respond.io skip: nessun identifier (telefono/email) per cliente %s",
            cliente.cliente_id,
        )
        return sync_result

    sync_result["enabled"] = True
    sync_result["identifier"] = identifier

    try:
        from corposostenibile.blueprints.respond_io.client import RespondIOClient
        respond_client = RespondIOClient(current_app.config)
    except Exception as client_err:
        sync_result["errors"].append(f"client_init_error:{client_err}")
        current_app.logger.error(
            "[opportunity_bridge] Respond.io client init error: %s",
            client_err,
        )
        return sync_result

    import time
    from datetime import datetime as _dt

    channel_id = current_app.config.get("RESPOND_IO_DEFAULT_CHANNEL_ID")

    def _ts():
        return _dt.now().strftime("%H:%M:%S.%f")[:-3]

    # ── 1) Assign conversazione a HM ──
    if health_manager_email:
        current_app.logger.info(f"[opportunity_bridge] [{_ts()}] → Invio assign a {identifier}")
        try:
            respond_client.assign_conversation(
                contact_id=identifier,
                assignee=health_manager_email,
            )
            sync_result["assigned"] = True
            current_app.logger.info(f"[opportunity_bridge] [{_ts()}] ✓ assign OK")
        except Exception as assign_err:
            err_msg = str(assign_err).lower()
            if "400" in str(assign_err) and "already assigned" in err_msg:
                sync_result["assigned"] = True
                current_app.logger.info(f"[opportunity_bridge] [{_ts()}] ✓ assign: già assegnato (ok)")
            else:
                sync_result["errors"].append(f"assign_error:{assign_err}")
                current_app.logger.error(
                    "[opportunity_bridge] [%s] ✗ assign error: %s", _ts(), assign_err,
                )
    else:
        sync_result["errors"].append("missing_health_manager_email")
        current_app.logger.warning(
            "[opportunity_bridge] Respond.io assign skip: health_manager_email assente per cliente %s",
            cliente.cliente_id,
        )

    current_app.logger.info(f"[opportunity_bridge] [{_ts()}] Pausa 15s prima di suite_benvenuto...")
    time.sleep(15)

    # ── 2) Template 1: suite_benvenuto (nessuna variabile) ──
    current_app.logger.info(f"[opportunity_bridge] [{_ts()}] → Invio suite_benvenuto a {identifier}")
    try:
        respond_client.send_template_message(
            contact_id=identifier,
            template_name="suite_benvenuto",
            channel_id=channel_id,
            language="it",
        )
        sync_result["presentation_sent"] = True
        current_app.logger.info(f"[opportunity_bridge] [{_ts()}] ✓ suite_benvenuto OK")
    except Exception as msg_err:
        sync_result["errors"].append(f"presentation_error:{msg_err}")
        current_app.logger.error(
            "[opportunity_bridge] [%s] ✗ suite_benvenuto error: %s", _ts(), msg_err,
        )

    current_app.logger.info(f"[opportunity_bridge] [{_ts()}] Pausa 15s prima di suite_check...")
    time.sleep(15)

    # ── 3) Template 2: suite_check ({{1}} = URL check 1, {{2}} = URL check 2) ──
    current_app.logger.info(f"[opportunity_bridge] [{_ts()}] → Invio suite_check a {identifier}")
    try:
        base_url = _public_checks_base_url()
        check_urls = [a.get_public_url(base_url=base_url) for a in assignments]

        parameters = [
            {"type": "text", "text": check_urls[0] if len(check_urls) > 0 else "LINK CHECK 1"},
            {"type": "text", "text": check_urls[1] if len(check_urls) > 1 else "LINK CHECK 2"},
        ]

        respond_client.send_template_message(
            contact_id=identifier,
            template_name="suite_check",
            channel_id=channel_id,
            language="it",
            parameters=parameters,
        )
        sync_result["check_links_sent"] = True
        current_app.logger.info(f"[opportunity_bridge] [{_ts()}] ✓ suite_check OK")
    except Exception as msg_err:
        sync_result["errors"].append(f"check_links_error:{msg_err}")
        current_app.logger.error(
            "[opportunity_bridge] [%s] ✗ suite_check error: %s", _ts(), msg_err,
        )

    return sync_result
