"""
customers.services
==================

Layer di **business-logic “WRITE”** per il dominio *customers*.

• Centralizza tutte le operazioni mutative (CRUD + KPI).  
• Incapsula transazioni, side-effects (Celery / Slack / WS) e segnali.  
• La registrazione dei movimenti monetari è delegata al package
  ``blueprints.accounting`` (commissioni, validazioni, ecc.).

⚠️ NOVITÀ – Integrazione feedback *Typeform*
-------------------------------------------
* ``process_typeform_payload(payload)``
  - Aggiorna media ``satisfaction_avg`` sul cliente
  - Se rating < 7 → ActivityLog, signal *customer_updated*, alert Slack/e-mail

* ``_match_cliente(first, last)``
  1. match esatto (case-insensitive) su ``nome_cognome``
  2. match *fuzzy* (SOUNDEX o trigramma – pg_trgm, se installato)
  3. fallback → None  (feedback marcato *unmatched*)
"""
from __future__ import annotations

import decimal
import json
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple
from urllib.parse import quote_plus

import requests
from flask import current_app, render_template
from flask_mail import Message
from sqlalchemy import desc, func, or_, cast, String
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from corposostenibile.extensions import celery, db
from corposostenibile.models import (                 # pylint: disable=too-many-imports
    CallBonus,
    CallBonusStatusEnum,
    Cliente,
    ClienteProfessionistaHistory,
    PaymentTransaction,
    SalesPerson,
    SubscriptionContract,
    User,
    SubscriptionRenewal,
    WeeklyCheck,
    DCACheck,
    # ENUM
    CommissionRoleEnum,
    StatoClienteEnum,
    TransactionTypeEnum,
    TipoProfessionistaEnum,
    UserRoleEnum,
    cliente_nutrizionisti,
    cliente_coaches,
    cliente_psicologi,
    cliente_consulenti
)
from flask_login import current_user
from sqlalchemy import desc, func, or_, exists, select

# —— layer contabile centrale (rimosso) ——————————————————————————————— #

# Changelog granulare
from .models.activity_log import ActivityLog                               # pragma: no cover
# SIGNALS
from .signals import emit_created, emit_deleted, emit_updated
from .rbac_scope import professionista_visibility_clause

__all__ = [
    # CRUD & API pubblica
    "select_hm_for_new_client",
    "send_onboarding_email",
    "create_cliente",
    "update_cliente",
    "delete_cliente",
    "create_contract",
    "update_contract",
    "create_payment",
    "create_renewal",
    "create_meeting",
    "restore_cliente_version",
    # webhook Typeform
    "process_typeform_payload",
    # bulk & KPI helper
    "bulk_create_or_update_clienti",
    "calculate_ltv_for_clienti",
    "find_potential_duplicates",
    # dashboard 360° functions
    "calculate_dashboard_kpis",
    "calculate_health_scores",
    "calculate_temporal_metrics",
    "calculate_segments",
    "apply_role_filtering",
    # freeze management
    "freeze_cliente",
    "unfreeze_cliente",
    # marketing metrics
    "get_marketing_metrics_for_clienti",
    "get_marketing_filtered_cliente_ids",
    # call bonus management
    "create_call_bonus",
    "update_call_bonus_response",
    "update_call_bonus_hm_confirm",
    "get_cliente_call_bonus_history",
    "get_call_bonus_accettate",
    "reconcile_stato_cliente_from_services",
]

# --------------------------------------------------------------------------- #
#  Config Typeform (override-able in instance/config.py)                      #
# --------------------------------------------------------------------------- #
TYPEFORM_CONFIG: Dict[str, Any] = {
    "form_id": "NMA7wAUZ",
    "field_mapping": {
        "first_name":   "xUZ7AHHvXcDc",
        "last_name":    "j00YnBJPzweV",
        "satisfaction": "T6qaQ7Kun42s",
    },
}
try:
    # se l’app espone una config custom la fondiamo
    TYPEFORM_CONFIG.update(current_app.config["TYPEFORM_CUSTOMER_SATISFACTION"])  # type: ignore[index]
except Exception:       # pragma: no cover
    pass

# --------------------------------------------------------------------------- #
#  Helpers                                                                    #
# --------------------------------------------------------------------------- #
@contextmanager
def _commit_or_rollback(session: Session = db.session):
    """Esegue il commit a fine blocco; rollback automatico su eccezione."""
    try:
        yield session
        session.commit()
    except Exception:            # pragma: no cover
        session.rollback()
        raise


def _as_decimal(value) -> decimal.Decimal | None:
    if value in (None, "", "nan"):
        return None
    try:
        return decimal.Decimal(str(value))
    except decimal.InvalidOperation:
        raise ValueError(f"Valore non numerico: {value!r}")


def _user_id(actor) -> int | None:           # pragma: no cover
    """Ritorna l’id (se esiste) dell’oggetto passato."""
    return getattr(actor, "id", None)


def _get_hm_capacity_candidates(db_session: Session) -> list[dict[str, Any]]:
    """Costruisce i candidati HM con metriche target/current/residual."""
    hm_users = (
        db_session.query(User)
        .filter(
            User.is_active == True,
            cast(User.role, String) == "health_manager",
            User.hm_capacity_target.isnot(None),
        )
        .all()
    )

    if not hm_users:
        return []

    hm_ids = [u.id for u in hm_users]
    count_rows = (
        db_session.query(
            Cliente.health_manager_id,
            func.count(Cliente.cliente_id),
        )
        .filter(
            Cliente.health_manager_id.in_(hm_ids),
            or_(
                Cliente.stato_cliente.is_(None),
                ~func.lower(cast(Cliente.stato_cliente, String)).in_(["stop", "archiviato"]),
            ),
        )
        .group_by(Cliente.health_manager_id)
        .all()
    )
    active_counts = {int(hm_id): int(cnt) for hm_id, cnt in count_rows if hm_id is not None}

    candidates: list[dict[str, Any]] = []
    for hm in hm_users:
        target = hm.hm_capacity_target
        current_assigned = active_counts.get(hm.id, 0)
        residual = int(target) - current_assigned if target is not None else None
        candidates.append(
            {
                "user": hm,
                "target": target,
                "current_assigned": current_assigned,
                "residual": residual,
            }
        )
    return candidates


def select_hm_for_new_client(db_session: Session) -> User | None:
    """
    Seleziona HM per nuovo cliente in base alla capacità residua:
    - residual DESC
    - current_assigned ASC (tie-break)
    - id ASC (tie-break finale)

    Ritorna None se non ci sono HM con residual > 0.
    """
    candidates = _get_hm_capacity_candidates(db_session)
    eligible = [
        c for c in candidates
        if c.get("target") is not None and (c.get("residual") or 0) > 0
    ]
    if not eligible:
        return None

    eligible.sort(
        key=lambda c: (
            -int(c["residual"]),
            int(c["current_assigned"]),
            int(c["user"].id),
        )
    )
    return eligible[0]["user"]


def _resolve_package_name(cliente: Cliente) -> str:
    """Best-effort: ricava nome pacchetto/programa per email onboarding."""
    pacchetto = getattr(cliente, "pacchetto", None)
    if isinstance(pacchetto, str) and pacchetto.strip():
        return pacchetto.strip()
    if pacchetto is not None:
        for attr in ("name", "nome", "title"):
            value = getattr(pacchetto, attr, None)
            if isinstance(value, str) and value.strip():
                return value.strip()

    for attr in ("programma", "programma_attuale"):
        value = getattr(cliente, attr, None)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return "Percorso Corposostenibile"


def _public_base_url() -> str:
    cfg = current_app.config
    return (
        cfg.get("PUBLIC_BASE_URL")
        or cfg.get("FRONTEND_BASE_URL")
        or cfg.get("FRONTEND_URL")
        or cfg.get("BASE_URL")
        or ""
    ).rstrip("/")


def _build_check_links_for_onboarding(db_session: Session, cliente: Cliente) -> dict[str, str | None]:
    base_url = _public_base_url()
    check_base_path = (current_app.config.get("ONBOARDING_CHECKS_BASE_PATH") or "/client-checks").rstrip("/")

    weekly = (
        db_session.query(WeeklyCheck)
        .filter(
            WeeklyCheck.cliente_id == cliente.cliente_id,
            WeeklyCheck.is_active == True,
        )
        .order_by(WeeklyCheck.assigned_at.desc())
        .first()
    )
    dca = (
        db_session.query(DCACheck)
        .filter(
            DCACheck.cliente_id == cliente.cliente_id,
            DCACheck.is_active == True,
        )
        .order_by(DCACheck.assigned_at.desc())
        .first()
    )

    weekly_url = f"{base_url}{check_base_path}/weekly/{weekly.token}" if (base_url and weekly) else None
    monthly_url = f"{base_url}{check_base_path}/dca/{dca.token}" if (base_url and dca) else None

    check_portal_url = current_app.config.get("ONBOARDING_CHECK_PORTAL_URL")
    if not check_portal_url and base_url:
        check_portal_url = f"{base_url}/check"

    return {
        "weekly_url": weekly_url,
        "monthly_url": monthly_url,
        "check_portal_url": check_portal_url,
    }


def _build_onboarding_whatsapp_url(cliente: Cliente) -> str:
    hm = getattr(cliente, "health_manager_user", None)
    hm_name = getattr(hm, "full_name", None) or "il tuo Health Manager"
    text = current_app.config.get(
        "ONBOARDING_WHATSAPP_TEXT",
        "Ciao {hm_name}, sono {cliente_name}. Ho appena iniziato il percorso e vorrei avviare la chat di onboarding.",
    ).format(
        hm_name=hm_name,
        cliente_name=cliente.nome_cognome or "Cliente",
    )

    phone = (
        current_app.config.get("ONBOARDING_WHATSAPP_PHONE")
        or getattr(hm, "phone", None)
        or getattr(hm, "numero_telefono", None)
        or ""
    )
    phone_digits = "".join(ch for ch in str(phone) if ch.isdigit())
    encoded_text = quote_plus(text)

    if phone_digits:
        return f"https://wa.me/{phone_digits}?text={encoded_text}"
    return f"https://wa.me/?text={encoded_text}"


def send_onboarding_email(cliente_id: int) -> bool:
    """
    Invia email onboarding cliente in modo idempotente.

    Regole:
    - skip se cliente inesistente o senza email
    - skip se onboarding_email_sent_at già valorizzato
    - aggiorna onboarding_email_sent_at al successo
    """
    cliente = db.session.get(Cliente, cliente_id)
    if not cliente:
        current_app.logger.warning("[onboarding-email] Cliente %s non trovato", cliente_id)
        return False

    if getattr(cliente, "onboarding_email_sent_at", None):
        current_app.logger.info(
            "[onboarding-email] già inviata per cliente %s", cliente_id
        )
        return False

    recipient_email = (cliente.mail or "").strip()
    if not recipient_email:
        current_app.logger.warning(
            "[onboarding-email] cliente %s senza email destinatario", cliente_id
        )
        return False

    if not current_app.config.get("MAIL_SERVER"):
        current_app.logger.warning("[onboarding-email] MAIL_SERVER non configurato")
        return False

    check_links = _build_check_links_for_onboarding(db.session, cliente)
    package_name = _resolve_package_name(cliente)
    tc_url = current_app.config.get(
        "ONBOARDING_TERMS_URL",
        "https://www.corposostenibile.com/termini-e-condizioni",
    )
    whatsapp_url = _build_onboarding_whatsapp_url(cliente)

    html = render_template(
        "email/onboarding_cliente.html",
        cliente=cliente,
        package_name=package_name,
        tc_url=tc_url,
        weekly_check_url=check_links["weekly_url"],
        monthly_check_url=check_links["monthly_url"],
        check_portal_url=check_links["check_portal_url"],
        whatsapp_url=whatsapp_url,
    )

    msg = Message(
        subject=current_app.config.get(
            "ONBOARDING_EMAIL_SUBJECT",
            "Benvenutə in Corposostenibile: recap percorso, check e chat con il tuo HM",
        ),
        recipients=[recipient_email],
        html=html,
        sender=current_app.config.get("MAIL_DEFAULT_SENDER", "noreply@corposostenibile.com"),
    )

    try:
        from corposostenibile.extensions import mail

        mail.send(msg)
        cliente.onboarding_email_sent_at = datetime.utcnow()
        db.session.commit()
        current_app.logger.info(
            "[onboarding-email] inviata a cliente %s <%s>",
            cliente_id,
            recipient_email,
        )
        return True
    except Exception:
        db.session.rollback()
        current_app.logger.exception(
            "[onboarding-email] errore invio per cliente %s",
            cliente_id,
        )
        return False


# ........................................................................... #
#  Algoritmo di matching cliente                                              #
# ........................................................................... #
def _match_cliente(first: str, last: str) -> Tuple[Cliente | None, str | None]:
    """
    1. exact-match case-insensitive  
    2. fuzzy trigramma (pg_trgm) oppure SOUNDEX  
    3. fallback → None
    """
    full_name = f"{first.strip()} {last.strip()}".lower()

    # 1) exact
    cliente = (
        Cliente.query
        .filter(func.lower(Cliente.nome_cognome) == full_name)
        .one_or_none()
    )
    if cliente:
        return cliente, "exact"

    # 2) trigram (pg_trgm)
    try:
        cliente = (
            Cliente.query
            .order_by(func.similarity(func.lower(Cliente.nome_cognome), full_name).desc())
            .filter(func.similarity(func.lower(Cliente.nome_cognome), full_name) > 0.4)
            .limit(1)
            .one_or_none()
        )
        if cliente:
            return cliente, "trigram"
    except ProgrammingError:
        pass

    # 3) SOUNDEX (fallback)
    try:
        sx_full = func.soundex(full_name)
        cliente = (
            Cliente.query
            .filter(func.soundex(func.lower(Cliente.nome_cognome)) == sx_full)
            .first()
        )
        if cliente:
            return cliente, "soundex"
    except ProgrammingError:                # pragma: no cover
        pass

    return None, None


# ........................................................................... #
#  Slack helper                                                               #
# ........................................................................... #
def _send_slack_message(text: str) -> None:
    """Invia msg al webhook Slack (best-effort)."""
    url: str | None = current_app.config.get("SLACK_FEEDBACK_WEBHOOK_URL")
    if not url:
        current_app.logger.debug("Slack webhook non configurato; skip.")
        return
    try:
        resp = requests.post(url, data=json.dumps({"text": text}), timeout=5)
        if resp.status_code >= 400:
            current_app.logger.warning("Slack webhook error %s – %s", resp.status_code, resp.text)
    except Exception:                        # pragma: no cover
        current_app.logger.exception("Errore invio Slack webhook")

# ════════════════════════════════════════════════════════════════════════════
#                                CRUD CLIENTI
# ════════════════════════════════════════════════════════════════════════════
def create_cliente(data: Mapping[str, Any], created_by_user) -> Cliente:
    """Crea un nuovo cliente (+ eventuale contratto / deposito iniziale)."""
    with _commit_or_rollback() as session:
        consultant = session.get(SalesPerson, data.get("personal_consultant_id")) \
            if data.get("personal_consultant_id") else None
        if data.get("personal_consultant_id") and not consultant:
            raise ValueError("Consulente personale non trovato.")

        explicit_hm_id = data.get("health_manager_id")
        should_auto_assign_hm = explicit_hm_id in (None, "")
        selected_hm = select_hm_for_new_client(session) if should_auto_assign_hm else None

        cliente = Cliente(
            **{k: v for k, v in data.items() if hasattr(Cliente, k)},
            created_by=_user_id(created_by_user),
        )
        if selected_hm:
            cliente.health_manager_id = selected_hm.id

        if consultant:
            cliente.personal_consultant = consultant
        session.add(cliente)
        session.flush()

        if selected_hm:
            session.add(
                ActivityLog(
                    cliente_id=cliente.cliente_id,
                    field="health_manager_id",
                    before=None,
                    after=str(selected_hm.id),
                    user_id=_user_id(created_by_user),
                )
            )
            current_app.logger.info(
                "Auto-assegnato HM %s al nuovo cliente %s",
                selected_hm.id,
                cliente.cliente_id,
            )
        elif should_auto_assign_hm:
            current_app.logger.warning(
                "Nessun HM auto-assegnabile trovato per nuovo cliente %s",
                cliente.cliente_id,
            )

        # Contratto iniziale (facoltativo)
        if "initial_contract" in data:
            _create_contract_for_cliente(cliente, data["initial_contract"], session)

        # Riallinea stato globale con gli stati servizio già presenti nel payload
        # (evita clienti con stato_cliente NULL ma servizi attivi).
        _update_stato_cliente_from_services(cliente, created_by_user)

    # post-commit
    emit_created(cliente, user_id=_user_id(created_by_user))
    _enqueue_async("customers.tasks.new_customer_notification", cliente_id=cliente.cliente_id)
    _enqueue_async("customers.tasks.send_onboarding_email_task", cliente_id=cliente.cliente_id)
    current_app.logger.info("Creato cliente %s", cliente.cliente_id)
    return cliente


def _get_stato_value(stato) -> str | None:
    """Helper per ottenere il valore dello stato sia che sia Enum o stringa."""
    if stato is None:
        return None
    if hasattr(stato, 'value'):
        return stato.value
    return str(stato)


def _has_professionista_assigned(cliente: Cliente, servizio: str) -> bool:
    """Verifica se un servizio ha almeno un professionista assegnato."""
    if servizio == 'nutrizione':
        return (
            (cliente.nutrizionisti_multipli and len(cliente.nutrizionisti_multipli) > 0)
            or cliente.nutrizionista_id
            or (getattr(cliente, "nutrizionista", None) and str(cliente.nutrizionista).strip())
        )
    elif servizio == 'coach':
        return (
            (cliente.coaches_multipli and len(cliente.coaches_multipli) > 0)
            or cliente.coach_id
            or (getattr(cliente, "coach", None) and str(cliente.coach).strip())
        )
    elif servizio == 'psicologia':
        return (
            (cliente.psicologi_multipli and len(cliente.psicologi_multipli) > 0)
            or cliente.psicologa_id
            or (getattr(cliente, "psicologa", None) and str(cliente.psicologa).strip())
        )
    return False


def _get_servizi_assegnati(cliente: Cliente) -> list[dict]:
    """Raccoglie tutti i servizi assegnati con il loro stato."""
    servizi = []
    
    mapping = {
        'nutrizione': ('stato_nutrizione', cliente.stato_nutrizione),
        'coach': ('stato_coach', cliente.stato_coach),
        'psicologia': ('stato_psicologia', cliente.stato_psicologia),
    }
    
    for servizio, (campo, stato) in mapping.items():
        if _has_professionista_assigned(cliente, servizio):
            servizi.append({
                'nome': servizio,
                'campo': campo,
                'stato': _get_stato_value(stato),
            })
    
    return servizi


def _update_stato_cliente_from_services(cliente: Cliente, updated_by_user) -> bool:
    """
    Aggiorna lo stato_cliente basandosi sugli stati dei servizi M2M.
    
    Logica semplificata:
    - stato_cliente = ATTIVO se ALMENO UN servizio è ATTIVO
    - stato_cliente = GHOST se TUTTI i servizi sono GHOST
    - stato_cliente = PAUSA se TUTTI i servizi sono PAUSA
    
    Args:
        cliente: Il cliente da aggiornare
        updated_by_user: L'utente che ha fatto la modifica (per ActivityLog)
        
    Returns:
        bool: True se lo stato_cliente è stato modificato, False altrimenti
    """
    from datetime import datetime
    
    servizi = _get_servizi_assegnati(cliente)
    
    if not servizi:
        current_app.logger.debug(
            f"Cliente {cliente.cliente_id} - Nessun servizio assegnato, skip aggiornamento stato globale"
        )
        return False
    
    stati = [s['stato'] for s in servizi]
    stato_corrente = _get_stato_value(cliente.stato_cliente)
    
    current_app.logger.info(
        f"Cliente {cliente.cliente_id} - Servizi: {[s['nome'] for s in servizi]}, "
        f"Stati: {stati}, Stato cliente attuale: {stato_corrente}"
    )
    
    # Logica: priorità ATTIVO > GHOST > PAUSA
    # 1. Se c'è almeno un servizio ATTIVO → stato_cliente = ATTIVO
    if any(s == 'attivo' for s in stati):
        nuovo_stato = 'attivo'
    # 2. Altrimenti se tutti sono GHOST → stato_cliente = GHOST
    elif all(s == 'ghost' for s in stati):
        nuovo_stato = 'ghost'
    # 3. Altrimenti se tutti sono PAUSA → stato_cliente = PAUSA
    elif all(s == 'pausa' for s in stati):
        nuovo_stato = 'pausa'
    else:
        # Caso misto (es. ghost + pausa, o nessun servizio con stato definito)
        # Non cambiamo stato automaticamente
        return False
    
    # Se il nuovo stato è diverso da quello attuale, aggiorna
    if nuovo_stato != stato_corrente:
        old_stato = cliente.stato_cliente
        cliente.stato_cliente = StatoClienteEnum(nuovo_stato)
        cliente.stato_cliente_data = datetime.utcnow()
        
        db.session.add(
            ActivityLog(
                cliente_id=cliente.cliente_id,
                field='stato_cliente',
                before=_get_stato_value(old_stato),
                after=nuovo_stato,
                user_id=_user_id(updated_by_user),
            )
        )
        
        current_app.logger.info(
            f"Cliente {cliente.cliente_id} - Stato cliente aggiornato: "
            f"{_get_stato_value(old_stato)} -> {nuovo_stato} "
            f"(basato su stati servizi: {stati})"
        )
        return True
    
    return False


# Alias per retrocompatibilità con il resto del codice
def _check_and_update_global_ghost_status(cliente: Cliente, updated_by_user) -> bool:
    """Deprecato: usa _update_stato_cliente_from_services"""
    return _update_stato_cliente_from_services(cliente, updated_by_user)


def _check_and_update_global_pausa_status(cliente: Cliente, updated_by_user) -> bool:
    """Deprecato: usa _update_stato_cliente_from_services"""
    return _update_stato_cliente_from_services(cliente, updated_by_user)


def reconcile_stato_cliente_from_services(cliente: Cliente, updated_by_user) -> bool:
    """API pubblica: riallinea stato_cliente in base agli stati servizio assegnati."""
    return _update_stato_cliente_from_services(cliente, updated_by_user)


def _handle_call_to_status_trigger(
    cliente: Cliente,
    data: Mapping[str, Any],
    updated_by_user,
    existing_changes: Dict[str, Tuple[Any, Any]] = None
) -> Dict[str, Tuple[Any, Any]]:
    """
    Gestisce il trigger automatico: quando call_iniziale_X diventa True,
    imposta automaticamente stato_X = ATTIVO se non già impostato.

    Mapping:
        - call_iniziale_nutrizionista = True → stato_nutrizione = ATTIVO
        - call_iniziale_coach = True → stato_coach = ATTIVO
        - call_iniziale_psicologa = True → stato_psicologia = ATTIVO

    Inoltre, se tutti i servizi assegnati (con almeno un professionista) hanno
    effettuato la call iniziale, aggiorna automaticamente stato_cliente = ATTIVO.

    Args:
        existing_changes: Dict dei cambiamenti già rilevati (contiene old, new values)

    Returns:
        Dict di cambiamenti effettuati (per ActivityLog)
    """
    from datetime import datetime

    changes: Dict[str, Tuple[Any, Any]] = {}
    existing_changes = existing_changes or {}

    # Mapping call → stato servizio
    call_to_status_map = {
        'call_iniziale_nutrizionista': 'stato_nutrizione',
        'call_iniziale_coach': 'stato_coach',
        'call_iniziale_psicologa': 'stato_psicologia',
    }

    # Per ogni campo call nel data, controlla se sta diventando True
    for call_field, status_field in call_to_status_map.items():
        if call_field not in data:
            continue

        new_call_value = data.get(call_field)

        # Prendi il valore vecchio da existing_changes se disponibile (perché il cliente è già stato aggiornato)
        if call_field in existing_changes:
            old_call_value = existing_changes[call_field][0]  # (old, new) tuple
        else:
            old_call_value = getattr(cliente, call_field, False)

        # Se la call sta diventando True (e prima non lo era)
        if new_call_value and not old_call_value:
            current_status = getattr(cliente, status_field, None)

            # Estrai il valore dello stato corrente
            status_value = current_status.value if hasattr(current_status, 'value') else current_status

            # Se lo stato servizio non è già ATTIVO, impostalo
            if status_value != 'attivo':
                old_status = current_status
                new_status = StatoClienteEnum.attivo

                # Usa il metodo update_stato_servizio se disponibile
                servizio_map = {
                    'stato_nutrizione': 'nutrizione',
                    'stato_coach': 'coach',
                    'stato_psicologia': 'psicologia',
                }

                if servizio_map.get(status_field):
                    cliente.update_stato_servizio(servizio_map[status_field], new_status)
                else:
                    setattr(cliente, status_field, new_status)
                    # Aggiorna anche la data di cambio stato
                    data_field = f"{status_field}_data"
                    if hasattr(cliente, data_field):
                        setattr(cliente, data_field, datetime.utcnow())

                changes[status_field] = (old_status, new_status)

                current_app.logger.info(
                    f"Cliente {cliente.cliente_id} - {status_field} impostato automaticamente a ATTIVO "
                    f"(call iniziale effettuata)"
                )

    # Se ci sono stati cambiamenti, controlla se aggiornare stato_cliente globale
    if changes:
        _check_and_update_global_active_status(cliente, data, updated_by_user, changes)

    return changes


def _check_and_update_global_active_status(
    cliente: Cliente,
    data: Mapping[str, Any],
    updated_by_user,
    pending_changes: Dict[str, Tuple[Any, Any]]
) -> bool:
    """
    Controlla se tutti i servizi assegnati (con almeno un professionista) hanno
    effettuato la call iniziale. Se sì, aggiorna automaticamente stato_cliente = ATTIVO.

    Questo trigger si attiva solo quando lo stato_cliente NON è già ATTIVO.

    Returns:
        bool: True se lo stato_cliente è stato aggiornato a ATTIVO, False altrimenti
    """
    from datetime import datetime

    def _get_stato_value(stato) -> str | None:
        if stato is None:
            return None
        if hasattr(stato, 'value'):
            return stato.value
        return str(stato)

    # Controlla lo stato cliente attuale
    stato_cliente_value = _get_stato_value(cliente.stato_cliente)
    if stato_cliente_value == 'attivo':
        # Già attivo, non fare nulla
        return False

    # Servizi assegnati e loro stato call/servizio
    servizi_check = []

    # Nutrizione - ha professionisti assegnati?
    if cliente.nutrizionisti_multipli and len(cliente.nutrizionisti_multipli) > 0:
        # Controlla il valore della call (prima nel data, poi nell'oggetto)
        call_value = data.get('call_iniziale_nutrizionista', getattr(cliente, 'call_iniziale_nutrizionista', False))
        servizi_check.append({
            'nome': 'nutrizione',
            'call_effettuata': bool(call_value),
            'professionisti_count': len(cliente.nutrizionisti_multipli)
        })

    # Coach - ha professionisti assegnati?
    if cliente.coaches_multipli and len(cliente.coaches_multipli) > 0:
        call_value = data.get('call_iniziale_coach', getattr(cliente, 'call_iniziale_coach', False))
        servizi_check.append({
            'nome': 'coaching',
            'call_effettuata': bool(call_value),
            'professionisti_count': len(cliente.coaches_multipli)
        })

    # Psicologia - ha professionisti assegnati?
    if cliente.psicologi_multipli and len(cliente.psicologi_multipli) > 0:
        call_value = data.get('call_iniziale_psicologa', getattr(cliente, 'call_iniziale_psicologa', False))
        servizi_check.append({
            'nome': 'psicologia',
            'call_effettuata': bool(call_value),
            'professionisti_count': len(cliente.psicologi_multipli)
        })

    # Se non ci sono servizi assegnati, non fare nulla
    if not servizi_check:
        current_app.logger.debug(
            f"Cliente {cliente.cliente_id} - Nessun servizio assegnato, skip controllo attivo globale"
        )
        return False

    # Controlla se TUTTI i servizi assegnati hanno fatto la call
    servizi_con_call = [s for s in servizi_check if s['call_effettuata']]
    tutti_con_call = len(servizi_con_call) == len(servizi_check)

    current_app.logger.info(
        f"Cliente {cliente.cliente_id} - Servizi assegnati: {len(servizi_check)}, "
        f"Con call effettuata: {len(servizi_con_call)}, Tutti con call: {tutti_con_call}"
    )

    # Se tutti i servizi assegnati hanno fatto la call, imposta stato_cliente = ATTIVO
    if tutti_con_call:
        old_stato = cliente.stato_cliente
        cliente.stato_cliente = StatoClienteEnum.attivo
        cliente.stato_cliente_data = datetime.utcnow()

        # Log automatico
        db.session.add(
            ActivityLog(
                cliente_id=cliente.cliente_id,
                field='stato_cliente',
                before=_get_stato_value(old_stato),
                after='attivo',
                user_id=_user_id(updated_by_user),
            )
        )

        current_app.logger.info(
            f"Cliente {cliente.cliente_id} - Stato cliente aggiornato automaticamente a ATTIVO "
            f"(tutti i servizi assegnati hanno effettuato la call iniziale)"
        )

        # Aggiungi ai pending changes per tracciabilità
        pending_changes['stato_cliente'] = (old_stato, StatoClienteEnum.attivo)
        return True

    return False


def _track_patologie_changes(cliente: Cliente, data: Mapping[str, Any]) -> None:
    """
    Traccia i cambiamenti delle patologie nel log.
    Registra quando una patologia viene aggiunta o rimossa.
    """
    from corposostenibile.models import PatologiaLog
    from datetime import datetime

    # Mappa dei campi patologia -> nome visualizzato
    patologie_map = {
        'patologia_ibs': 'IBS',
        'patologia_reflusso': 'Reflusso',
        'patologia_gastrite': 'Gastrite',
        'patologia_dca': 'DCA',
        'patologia_insulino_resistenza': 'Insulino-resistenza',
        'patologia_diabete': 'Diabete',
        'patologia_dislipidemie': 'Dislipidemie',
        'patologia_steatosi_epatica': 'Steatosi epatica',
        'patologia_ipertensione': 'Ipertensione',
        'patologia_pcos': 'PCOS',
        'patologia_endometriosi': 'Endometriosi',
        'patologia_obesita_sindrome': 'Obesità-sindrome metabolica',
        'patologia_osteoporosi': 'Osteoporosi',
        'patologia_diverticolite': 'Diverticolite',
        'patologia_crohn': 'Morbo di Crohn',
        'patologia_stitichezza': 'Stitichezza',
        'patologia_tiroidee': 'Malattie tiroidee',
    }

    now = datetime.utcnow()

    for field_name, display_name in patologie_map.items():
        if field_name not in data:
            continue

        old_value = getattr(cliente, field_name, False)
        new_value = data[field_name]

        # Converti None a False per confronto
        old_value = bool(old_value)
        new_value = bool(new_value)

        if old_value == new_value:
            continue  # Nessun cambiamento

        if new_value and not old_value:
            # Patologia AGGIUNTA
            # Chiudi eventuali log precedenti di questa patologia
            logs_aperti = PatologiaLog.query.filter_by(
                cliente_id=cliente.cliente_id,
                patologia=field_name,
                data_fine=None
            ).all()
            for log in logs_aperti:
                log.data_fine = now

            # Crea nuovo log di aggiunta
            nuovo_log = PatologiaLog(
                cliente_id=cliente.cliente_id,
                patologia=field_name,
                patologia_nome=display_name,
                azione='aggiunta',
                data_inizio=now,
                data_fine=None
            )
            db.session.add(nuovo_log)

        elif old_value and not new_value:
            # Patologia RIMOSSA
            # Trova il log aperto (con data_fine=NULL) e chiudilo
            log_aperto = PatologiaLog.query.filter_by(
                cliente_id=cliente.cliente_id,
                patologia=field_name,
                data_fine=None
            ).order_by(PatologiaLog.data_inizio.desc()).first()

            if log_aperto:
                log_aperto.data_fine = now

            # Crea nuovo log di rimozione
            nuovo_log = PatologiaLog(
                cliente_id=cliente.cliente_id,
                patologia=field_name,
                patologia_nome=display_name,
                azione='rimossa',
                data_inizio=now,
                data_fine=None
            )
            db.session.add(nuovo_log)


def _track_patologie_psico_changes(cliente: Cliente, data: Mapping[str, Any]) -> None:
    """
    Traccia i cambiamenti delle patologie psicologiche nel log.
    Registra quando una patologia psicologica viene aggiunta o rimossa.
    """
    from corposostenibile.models import PatologiaPsicoLog
    from datetime import datetime

    # Mappa dei campi patologia psicologica -> nome visualizzato
    patologie_psico_map = {
        'patologia_psico_dca': 'Disturbi del comportamento alimentare (DCA)',
        'patologia_psico_obesita_psicoemotiva': 'Obesità con componente psicoemotiva',
        'patologia_psico_ansia_umore_cibo': 'Disturbi d\'ansia e dell\'umore legati al rapporto con il cibo',
        'patologia_psico_comportamenti_disfunzionali': 'Comportamenti alimentari disfunzionali',
        'patologia_psico_immagine_corporea': 'Difficoltà relazionate all\'immagine corporea',
        'patologia_psico_psicosomatiche': 'Problematiche psicosomatiche',
        'patologia_psico_relazionali_altro': 'Problematiche relazionali di altro tipo',
    }

    now = datetime.utcnow()

    for field_name, display_name in patologie_psico_map.items():
        if field_name not in data:
            continue

        old_value = getattr(cliente, field_name, False)
        new_value = data[field_name]

        # Converti None a False per confronto
        old_value = bool(old_value)
        new_value = bool(new_value)

        if old_value == new_value:
            continue  # Nessun cambiamento

        if new_value and not old_value:
            # Patologia AGGIUNTA
            # Chiudi eventuali log precedenti di questa patologia
            logs_aperti = PatologiaPsicoLog.query.filter_by(
                cliente_id=cliente.cliente_id,
                patologia=field_name,
                data_fine=None
            ).all()
            for log in logs_aperti:
                log.data_fine = now

            # Crea nuovo log di aggiunta
            nuovo_log = PatologiaPsicoLog(
                cliente_id=cliente.cliente_id,
                patologia=field_name,
                patologia_nome=display_name,
                azione='aggiunta',
                data_inizio=now,
                data_fine=None
            )
            db.session.add(nuovo_log)

        elif old_value and not new_value:
            # Patologia RIMOSSA
            # Trova il log aperto (con data_fine=NULL) e chiudilo
            log_aperto = PatologiaPsicoLog.query.filter_by(
                cliente_id=cliente.cliente_id,
                patologia=field_name,
                data_fine=None
            ).order_by(PatologiaPsicoLog.data_inizio.desc()).first()

            if log_aperto:
                log_aperto.data_fine = now

            # Crea nuovo log di rimozione
            nuovo_log = PatologiaPsicoLog(
                cliente_id=cliente.cliente_id,
                patologia=field_name,
                patologia_nome=display_name,
                azione='rimossa',
                data_inizio=now,
                data_fine=None
            )
            db.session.add(nuovo_log)


def _track_patologie_coach_changes(cliente: Cliente, data: Mapping[str, Any]) -> None:
    """
    Traccia i cambiamenti delle patologie coaching nel log.
    Registra quando una patologia coaching viene aggiunta o rimossa.
    """
    from corposostenibile.models import PatologiaCoachLog
    from datetime import datetime

    # Mappa dei campi patologia coaching -> nome visualizzato
    patologie_coach_map = {
        'patologia_coach_dca': 'DCA',
        'patologia_coach_ipertensione': 'Ipertensione',
        'patologia_coach_pcos': 'PCOS',
        'patologia_coach_sindrome_metabolica': 'Sindrome metabolica - Obesità',
        'patologia_coach_endometriosi': 'Endometriosi',
        'patologia_coach_osteoporosi': 'Osteoporosi',
        'patologia_coach_menopausa': 'Menopausa',
        'patologia_coach_artrosi': 'Artrosi',
        'patologia_coach_artrite': 'Artrite',
        'patologia_coach_sclerosi_multipla': 'Sclerosi Multipla',
        'patologia_coach_fibromialgia': 'Fibromialgia',
        'patologia_coach_lipedema': 'Lipedema',
        'patologia_coach_linfedema': 'Linfedema',
        'patologia_coach_gravidanza': 'Gravidanza',
        'patologia_coach_riabilitazione_anca': 'Riabilitazione anca',
        'patologia_coach_riabilitazione_spalla': 'Riabilitazione spalla',
        'patologia_coach_riabilitazione_ginocchio': 'Riabilitazione ginocchio',
        'patologia_coach_lombalgia': 'Lombalgia',
        'patologia_coach_spondilolistesi': 'Spondilolistesi',
        'patologia_coach_spondilolisi': 'Spondilolisi',
    }

    now = datetime.utcnow()

    for field_name, display_name in patologie_coach_map.items():
        if field_name not in data:
            continue

        old_value = getattr(cliente, field_name, False)
        new_value = data[field_name]

        # Converti None a False per confronto
        old_value = bool(old_value)
        new_value = bool(new_value)

        if old_value == new_value:
            continue  # Nessun cambiamento

        if new_value and not old_value:
            # Patologia AGGIUNTA
            # Chiudi eventuali log precedenti di questa patologia
            logs_aperti = PatologiaCoachLog.query.filter_by(
                cliente_id=cliente.cliente_id,
                patologia=field_name,
                data_fine=None
            ).all()
            for log in logs_aperti:
                log.data_fine = now

            # Crea nuovo log di aggiunta
            nuovo_log = PatologiaCoachLog(
                cliente_id=cliente.cliente_id,
                patologia=field_name,
                patologia_nome=display_name,
                azione='aggiunta',
                data_inizio=now,
                data_fine=None
            )
            db.session.add(nuovo_log)

        elif old_value and not new_value:
            # Patologia RIMOSSA
            # Trova il log aperto (con data_fine=NULL) e chiudilo
            log_aperto = PatologiaCoachLog.query.filter_by(
                cliente_id=cliente.cliente_id,
                patologia=field_name,
                data_fine=None
            ).order_by(PatologiaCoachLog.data_inizio.desc()).first()

            if log_aperto:
                log_aperto.data_fine = now

            # Crea nuovo log di rimozione
            nuovo_log = PatologiaCoachLog(
                cliente_id=cliente.cliente_id,
                patologia=field_name,
                patologia_nome=display_name,
                azione='rimossa',
                data_inizio=now,
                data_fine=None
            )
            db.session.add(nuovo_log)


def update_cliente(
    cliente: Cliente,
    data: Mapping[str, Any],
    updated_by_user,
    *,
    recalc_ltv: bool = True,
    multi_fields: Dict[str, List[int]] = None,
) -> Cliente:
    """Aggiorna attributi e logga le differenze in ActivityLog."""
    readonly = {"cliente_id", "created_at", "updated_at", "created_by"}
    changes: Dict[str, Tuple[Any, Any]] = {}

    with _commit_or_rollback():
        # Traccia i cambiamenti delle patologie PRIMA di modificare i valori
        _track_patologie_changes(cliente, data)
        _track_patologie_psico_changes(cliente, data)
        _track_patologie_coach_changes(cliente, data)

        # Evita race tra stato globale e stati servizi + scadenze ricalcolate.
        # Nota: consideriamo "cambio stato servizio" solo quando il valore cambia davvero,
        # non solo perché la chiave è presente nel payload.
        _servizi_stato_keys = {"stato_nutrizione", "stato_coach", "stato_psicologia"}

        def _normalize_state_value(value):
            if hasattr(value, "value"):
                return value.value
            return value

        _service_state_keys_in_payload = _servizi_stato_keys & data.keys()
        _has_service_state_change = any(
            _normalize_state_value(data.get(service_key))
            != _normalize_state_value(getattr(cliente, service_key, None))
            for service_key in _service_state_keys_in_payload
        )
        _scadenza_skip_if_stato_updated = {
            "data_scadenza_nutrizione": "stato_nutrizione",
            "data_scadenza_coach": "stato_coach",
            "data_scadenza_psicologia": "stato_psicologia",
        }

        # Gestione campi normali
        for k, v in data.items():
            if k in readonly or not hasattr(cliente, k):
                continue
            if k == "stato_cliente" and _has_service_state_change:
                continue
            if k in _scadenza_skip_if_stato_updated and _scadenza_skip_if_stato_updated[k] in data:
                continue
            old = getattr(cliente, k)
            if v != old:
                changes[k] = (old, v)

                # Gestione speciale per cambi di stato dei servizi - usa i metodi che registrano lo storico
                if k == 'stato_coach':
                    cliente.update_stato_servizio('coach', v)
                elif k == 'stato_nutrizione':
                    cliente.update_stato_servizio('nutrizione', v)
                elif k == 'stato_psicologia':
                    cliente.update_stato_servizio('psicologia', v)
                elif k == 'stato_cliente_chat_coaching':
                    cliente.update_stato_chat('coaching', v)
                elif k == 'stato_cliente_chat_nutrizione':
                    cliente.update_stato_chat('nutrizione', v)
                elif k == 'stato_cliente_chat_psicologia':
                    cliente.update_stato_chat('psicologia', v)
                else:
                    # Per tutti gli altri campi, usa setattr normale
                    setattr(cliente, k, v)

        # Gestione relazioni many-to-many
        # IMPORTANTE: Aggiorniamo solo le relazioni che sono esplicitamente presenti in multi_fields
        # Le relazioni non presenti in multi_fields vengono preservate
        if multi_fields is not None:
            from corposostenibile.models import User

            # Nutrizionisti multipli - aggiorna solo se esplicitamente richiesto
            if 'nutrizionisti' in multi_fields:
                old_ids = [u.id for u in cliente.nutrizionisti_multipli]
                new_users = db.session.query(User).filter(User.id.in_(multi_fields['nutrizionisti'])).all() if multi_fields['nutrizionisti'] else []
                cliente.nutrizionisti_multipli = new_users
                if old_ids != multi_fields['nutrizionisti']:
                    changes['nutrizionisti_multipli'] = (old_ids, multi_fields['nutrizionisti'])

            # Coaches multipli - aggiorna solo se esplicitamente richiesto
            if 'coaches' in multi_fields:
                old_ids = [u.id for u in cliente.coaches_multipli]
                new_users = db.session.query(User).filter(User.id.in_(multi_fields['coaches'])).all() if multi_fields['coaches'] else []
                cliente.coaches_multipli = new_users
                if old_ids != multi_fields['coaches']:
                    changes['coaches_multipli'] = (old_ids, multi_fields['coaches'])

            # Psicologi multipli - aggiorna solo se esplicitamente richiesto
            if 'psicologi' in multi_fields:
                old_ids = [u.id for u in cliente.psicologi_multipli]
                new_users = db.session.query(User).filter(User.id.in_(multi_fields['psicologi'])).all() if multi_fields['psicologi'] else []
                cliente.psicologi_multipli = new_users
                if old_ids != multi_fields['psicologi']:
                    changes['psicologi_multipli'] = (old_ids, multi_fields['psicologi'])

            # Consulenti multipli - aggiorna solo se esplicitamente richiesto
            if 'consulenti' in multi_fields:
                old_ids = [u.id for u in cliente.consulenti_multipli]
                new_users = db.session.query(User).filter(User.id.in_(multi_fields['consulenti'])).all() if multi_fields['consulenti'] else []
                cliente.consulenti_multipli = new_users
                if old_ids != multi_fields['consulenti']:
                    changes['consulenti_multipli'] = (old_ids, multi_fields['consulenti'])

        # KPI – campo ltv nel modello ridotto è placeholder
        # Commented out because ltv is a read-only property
        # if recalc_ltv and changes and hasattr(cliente, "ltv"):
        #     cliente.ltv = _calculate_ltv(cliente)
        #     cliente.ltv_90_gg = _calculate_ltv(cliente, days=90)

        # ⚡ LOGICA CALL → STATO ATTIVO ⚡
        # Se call_iniziale_X diventa True, stato_X diventa ATTIVO automaticamente
        # Inoltre se tutti i servizi hanno fatto call, stato_cliente = ATTIVO
        call_fields_in_data = any(k.startswith('call_iniziale_') for k in data.keys())
        if call_fields_in_data:
            # Passa i changes esistenti per recuperare i valori vecchi (il cliente è già stato aggiornato)
            call_changes = _handle_call_to_status_trigger(cliente, data, updated_by_user, existing_changes=changes)
            # Merge dei cambiamenti (nota: gli stati servizio potrebbero già essere in changes)
            for k, v in call_changes.items():
                if k not in changes:
                    changes[k] = v

        # ⚡ LOGICA STATO GLOBALE DERIVATA DA SERVIZI M2M ⚡
        # Lo stato globale non deve mai contraddire gli stati servizio assegnati.
        # Se cambia manualmente stato_cliente, ricalcoliamo comunque per riallineare.
        stati_servizi_modificati = any(k in changes for k in ['stato_nutrizione', 'stato_coach', 'stato_psicologia'])
        professionisti_modificati = any(k in changes for k in ['nutrizionisti_multipli', 'coaches_multipli', 'psicologi_multipli'])
        stato_globale_modificato = 'stato_cliente' in changes

        if stati_servizi_modificati or professionisti_modificati or stato_globale_modificato:
            # Flush per assicurarsi che le modifiche siano visibili
            db.session.flush()
            # Controlla e aggiorna automaticamente stato_cliente (ghost/pausa),
            # applicando le regole M2M anche dopo eventuali edit manuali.
            _check_and_update_global_ghost_status(cliente, updated_by_user)
            _check_and_update_global_pausa_status(cliente, updated_by_user)

        # changelog
        for field, (before, after) in changes.items():
            db.session.add(
                ActivityLog(
                    cliente_id=cliente.cliente_id,
                    field=field,
                    before=None if before is None else str(before),
                    after=None if after is None else str(after),
                    user_id=_user_id(updated_by_user),
                )
            )

    if changes:
        emit_updated(cliente, user_id=_user_id(updated_by_user), changed=list(changes))
    current_app.logger.info("Aggiornato cliente %s (%d campi)", cliente.cliente_id, len(changes))
    return cliente


def delete_cliente(cliente: Cliente, deleted_by_user, *, soft: bool = True):
    """Soft-delete (default) oppure hard-delete se ``soft=False``."""
    with _commit_or_rollback():
        if soft:
            cliente.stato_cliente = StatoClienteEnum.stop
            cliente.stop = True
        else:
            db.session.delete(cliente)

    emit_deleted(cliente, user_id=_user_id(deleted_by_user), soft=soft)
    current_app.logger.warning("Cliente %s eliminato (soft=%s)", cliente.cliente_id, soft)

# ════════════════════════════════════════════════════════════════════════════
#                              CONTRATTI
# ════════════════════════════════════════════════════════════════════════════
def _create_contract_for_cliente(
    cliente: Cliente,
    payload: Mapping[str, Any],
    session: Session,
) -> SubscriptionContract:
    """Crea SubscriptionContract + eventuale deposito iniziale."""
    contract = SubscriptionContract(
        cliente_id=cliente.cliente_id,
        sale_date=payload.get("sale_date", date.today()),
        start_date=payload.get("start_date", date.today()),
        end_date=payload.get("end_date"),
        duration_days=payload.get("duration_days"),
        initial_deposit=_as_decimal(payload.get("initial_deposit")),
        service_type=payload.get("service_type"),
        seller_id=payload.get("seller_id"),
    )
    session.add(contract)
    session.flush()

    if contract.initial_deposit:
        # TODO: Gestione pagamento rimossa dopo rimozione modulo accounting
        # accounting_create_payment(
        #     subscription_id=contract.subscription_id,
        #     amount=contract.initial_deposit,
        #     payment_method=payload.get("payment_method"),
        #     transaction_type=TransactionTypeEnum.deposito,
        # )
        pass

    return contract


def create_contract(cliente: Cliente, payload: Mapping[str, Any], created_by_user) -> SubscriptionContract:
    """Wrapper pubblico (commit incluso)."""
    with _commit_or_rollback() as session:
        contract = _create_contract_for_cliente(cliente, payload, session)
    current_app.logger.info("Creato contratto %s per cliente %s", contract.subscription_id, cliente.cliente_id)
    return contract


def update_contract(contract: SubscriptionContract, data: Mapping[str, Any], updated_by_user) -> SubscriptionContract:
    """Aggiorna i campi mutabili di un contratto esistente."""
    readonly = {"subscription_id", "cliente_id", "created_at", "updated_at"}
    with _commit_or_rollback():
        for k, v in data.items():
            if k not in readonly and hasattr(contract, k):
                setattr(contract, k, v)
    current_app.logger.info("Aggiornato contratto %s", contract.subscription_id)
    return contract

# ════════════════════════════════════════════════════════════════════════════
#                              PAGAMENTI
# ════════════════════════════════════════════════════════════════════════════
def _resolve_contract(cliente: Cliente, payload: Mapping[str, Any], session: Session) -> SubscriptionContract:
    """Ritorna il contratto corretto per un pagamento/rinnovo."""
    sid = payload.get("subscription_id")
    if sid:
        contract = session.get(SubscriptionContract, sid)
        if not contract or contract.cliente_id != cliente.cliente_id:
            raise ValueError("subscription_id non valido per il cliente.")
        return contract
    contract = (
        session.query(SubscriptionContract)
        .filter_by(cliente_id=cliente.cliente_id)
        .order_by(SubscriptionContract.start_date.desc())
        .first()
    )
    if not contract:
        raise ValueError("Cliente privo di contratti.")
    return contract


def create_payment(cliente: Cliente, payload: Mapping[str, Any], created_by_user) -> PaymentTransaction:
    """Registra un pagamento tramite *accounting*."""
    amount = _as_decimal(payload.get("amount"))
    if amount is None:
        raise ValueError("'amount' obbligatorio.")

    tx_type = TransactionTypeEnum(payload.get("transaction_type", TransactionTypeEnum.rinnovo))

    with _commit_or_rollback() as session:
        contract = _resolve_contract(cliente, payload, session)

    # TODO: Gestione pagamento rimossa dopo rimozione modulo accounting
    # payment = accounting_create_payment(
    #     subscription_id=contract.subscription_id,
    #     amount=amount,
    #     payment_method=payload.get("payment_method"),
    #     transaction_type=tx_type,
    #     note=payload.get("note"),
    # )
    payment = None

    db.session.commit()
    # current_app.logger.info("Creato pagamento %s (€%s) cliente %s", payment.payment_id, amount, cliente.cliente_id)
    current_app.logger.info("Pagamento (€%s) cliente %s - modulo accounting rimosso", amount, cliente.cliente_id)
    return payment

# ════════════════════════════════════════════════════════════════════════════
#                                RINNOVI
# ════════════════════════════════════════════════════════════════════════════
def create_renewal(cliente: Cliente, payload: Mapping[str, Any], created_by_user) -> SubscriptionRenewal:
    """Registra rinnovo + pagamento."""
    amount = _as_decimal(payload.get("renewal_amount"))
    if amount is None:
        raise ValueError("'renewal_amount' obbligatorio.")

    with _commit_or_rollback() as session:
        contract = _resolve_contract(cliente, payload, session)

        renewal = SubscriptionRenewal(
            subscription_id=contract.subscription_id,
            renewal_payment_date=payload.get("renewal_payment_date", date.today()),
            renewal_amount=amount,
            renewal_duration_days=payload.get("renewal_duration_days"),
            renewal_responsible=_user_id(created_by_user),
            payment_method=payload.get("payment_method"),
            note=payload.get("note"),
        )
        session.add(renewal)
        session.flush()

    # TODO: Gestione pagamento rimossa dopo rimozione modulo accounting
    # accounting_create_payment(
    #     subscription_id=contract.subscription_id,
    #     amount=amount,
    #     payment_method=payload.get("payment_method"),
    #     transaction_type=TransactionTypeEnum.rinnovo,
    #     note=f"Autogenerato da renewal {renewal.renewal_id}",
    # )
    pass

    if renewal.renewal_duration_days:
        contract.end_date = (contract.end_date or date.today()) + timedelta(days=renewal.renewal_duration_days)
    db.session.commit()

    current_app.logger.info("Registrato rinnovo %s per contratto %s", renewal.renewal_id, contract.subscription_id)
    return renewal

# ════════════════════════════════════════════════════════════════════════════
#                                MEETING
# ════════════════════════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════════════════════════
#                          VERSIONING ROLLBACK
# ════════════════════════════════════════════════════════════════════════════
def restore_cliente_version(cliente_id: int, tx_id: int, actor) -> Cliente:
    """Ripristina lo stato del cliente alla transazione *tx_id* di Continuum."""
    from sqlalchemy_continuum import version_class          # import lazy
    ClienteVersion = version_class(Cliente)

    with _commit_or_rollback() as session:
        cliente = session.get(Cliente, cliente_id)
        if not cliente:
            raise ValueError("Cliente non trovato.")
        version = (
            session.query(ClienteVersion)
            .filter_by(transaction_id=tx_id, cliente_id=cliente_id)
            .one_or_none()
        )
        if not version:
            raise ValueError("Versione non trovata.")
        version.revert()
        session.flush()

    emit_updated(cliente, user_id=_user_id(actor))
    current_app.logger.info("Ripristinata versione %s cliente %s", tx_id, cliente_id)
    return cliente

# ════════════════════════════════════════════════════════════════════════════
#                             KPI / BULK UTILITIES
# ════════════════════════════════════════════════════════════════════════════
def _calculate_ltv(cliente: Cliente, *, days: int | None = None) -> decimal.Decimal:
    """Somma i pagamenti incassati dal cliente (placeholder schema ridotto)."""
    q = (
        db.session.query(func.coalesce(func.sum(PaymentTransaction.amount), 0))
        .filter(PaymentTransaction.cliente_id == cliente.cliente_id)
        .filter(PaymentTransaction.amount.isnot(None))
    )
    if days:
        cutoff = date.today() - timedelta(days=days)
        q = q.filter(PaymentTransaction.payment_date >= cutoff)
    return q.scalar() or decimal.Decimal(0)


def bulk_create_or_update_clienti(records: Sequence[Mapping[str, Any]]) -> Tuple[int, int]:
    """
    Upsert di massa basato su *email* o *numero_tel*.
    Ritorna ``(created, updated)``; il commit è delegato al caller.

    Nota: Quando vengono aggiornate le FK dei professionisti (nutrizionista_id, coach_id, etc.),
    viene effettuata la sincronizzazione con le relazioni M2M per garantire consistenza.
    """
    from corposostenibile.models import User

    # Mappatura FK -> campo M2M e tipo professionista
    FK_TO_M2M = {
        'nutrizionista_id': ('nutrizionisti_multipli', 'nutrizionista'),
        'coach_id': ('coaches_multipli', 'coach'),
        'psicologa_id': ('psicologi_multipli', 'psicologa'),
        'consulente_alimentare_id': ('consulenti_multipli', 'consulente'),
    }

    created = updated = 0
    for data in records:
        email = (data.get("email") or "").lower()
        tel = data.get("numero_tel")

        cliente = None
        if email:
            cliente = Cliente.query.filter(func.lower(Cliente.email) == email).one_or_none()
        if not cliente and tel:
            cliente = Cliente.query.filter(Cliente.numero_tel == tel).one_or_none()

        if cliente is None:
            cliente = Cliente(**{k: v for k, v in data.items() if hasattr(Cliente, k)})
            db.session.add(cliente)
            created += 1
            # Per nuovi clienti creati, sincronizza subito M2M con FK
            _sync_m2m_from_fk(cliente)
        else:
            for k, v in data.items():
                if hasattr(cliente, k):
                    setattr(cliente, k, v)
            updated += 1
            # Sincronizza M2M con FK dopo l'aggiornamento
            _sync_m2m_from_fk(cliente)
    return created, updated


def _sync_m2m_from_fk(cliente: Cliente) -> None:
    """
    Sincronizza le relazioni M2M con le FK del cliente.

    Quando una FK (nutrizionista_id, etc.) è impostata, assicura che l'utente
    corrispondente sia presente nella relazione M2M appropriata.
    Quando una FK viene rimossa (None), rimuove l'utente dalla M2M.

    Args:
        cliente: Il cliente da sincronizzare
    """
    from corposostenibile.models import User

    FK_TO_M2M = {
        'nutrizionista_id': 'nutrizionisti_multipli',
        'coach_id': 'coaches_multipli',
        'psicologa_id': 'psicologi_multipli',
        'consulente_alimentare_id': 'consulenti_multipli',
    }

    for fk_field, m2m_field in FK_TO_M2M.items():
        fk_value = getattr(cliente, fk_field, None)
        m2m_relation = getattr(cliente, m2m_field, None)

        if m2m_relation is None:
            continue

        # Ottieni gli ID degli utenti attualmente nella M2M
        current_m2m_ids = [u.id for u in m2m_relation]

        if fk_value is not None:
            # FK è impostata - assicura che l'utente sia nella M2M
            if fk_value not in current_m2m_ids:
                user = db.session.get(User, fk_value)
                if user and user not in m2m_relation:
                    m2m_relation.append(user)
        else:
            # FK è None - pulisci la M2M da utenti senza FK attiva
            # Rimuovi dalla M2M gli utenti che non hanno più FK
            users_to_remove = [u for u in m2m_relation if u.id not in current_m2m_ids or getattr(cliente, fk_field) is None]
            for user in users_to_remove:
                if user in m2m_relation:
                    m2m_relation.remove(user)


def calculate_ltv_for_clienti(ids: Sequence[int]) -> None:
    """Ricalcola LTV (totale + 90 gg) per i clienti indicati."""
    for cliente in Cliente.query.filter(Cliente.cliente_id.in_(ids)):
        cliente.ltv = _calculate_ltv(cliente)
        cliente.ltv_90_gg = _calculate_ltv(cliente, days=90)


def find_potential_duplicates(*, key: str = "email") -> List[List[Dict[str, Any]]]:
    """
    Ritorna gruppi di potenziali duplicati basati su **email** o **numero_tel**.
    """
    if key not in {"email", "numero_tel"}:
        raise ValueError("key must be 'email' or 'numero_tel'")

    column = getattr(Cliente, key)
    if key == "email":
        column = func.lower(column)

    dup_vals: Iterable[Tuple[str]] = (
        db.session.query(column)
        .filter(column.isnot(None))
        .group_by(column)
        .having(func.count(Cliente.cliente_id) > 1)
        .all()
    )

    groups: List[List[Dict[str, Any]]] = []
    for (val,) in dup_vals:
        q = Cliente.query.filter((func.lower(Cliente.email) == val) if key == "email"
                                 else (column == val))
        groups.append(
            [
                {
                    "cliente_id": c.cliente_id,
                    "nome": c.nome_cognome,
                    "email": getattr(c, "email", None),
                    "numero_tel": getattr(c, "numero_tel", None),
                }
                for c in q.order_by(Cliente.cliente_id)
            ]
        )
    return groups


# ════════════════════════════════════════════════════════════════════════════
#                             CELERY HELPER
# ════════════════════════════════════════════════════════════════════════════
def _enqueue_async(task_name: str, **kwargs):
    """Invoca un task Celery senza fallire in ambiente test."""
    try:
        if celery.conf.task_always_eager:            # type: ignore[attr-defined]
            celery.tasks[task_name].apply(kwargs=kwargs)     # type: ignore[index]
        else:
            celery.send_task(task_name, kwargs=kwargs)
    except (KeyError, AttributeError):
        current_app.logger.debug("Task %s non registrato – skip.", task_name)
    except Exception:                                # pragma: no cover
        current_app.logger.exception("Errore enqueue task %s", task_name)


# ════════════════════════════════════════════════════════════════════════════
#                          DASHBOARD 360° FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════
def apply_role_filtering(query):
    """
    Applica il filtro per ruolo (Admin, Team Leader, Professionista) alla query Clienti.
    Logica sincronizzata con CustomerRepository.list e global_search.
    """
    if not current_user.is_authenticated or current_user.is_trial:
        return query
        
    user_role = getattr(current_user, 'role', None)

    specialty = getattr(current_user, 'specialty', None)
    if hasattr(specialty, 'value'):
        specialty = specialty.value
    is_cco = str(specialty).strip().lower() == 'cco' if specialty else False

    # Un Team Leader che guida un team Health Manager deve vedere tutto:
    # il suo team contiene solo HM, quindi il filtro per FK clinica non
    # matcherebbe quasi nulla. Allineato al comportamento di HM regolare.
    is_hm_tl = False
    if user_role == UserRoleEnum.team_leader:
        for team in (getattr(current_user, 'teams_led', []) or []):
            team_type = getattr(getattr(team, 'team_type', None), 'value', getattr(team, 'team_type', None))
            if str(team_type or '').strip().lower() == 'health_manager':
                is_hm_tl = True
                break

    # Admin/CCO/Health Manager/HM Team Leader/Marketing: vede tutto e modifica tutto
    # Marketing: placeholder — scope di visibilita da ridefinire quando saranno note le regole
    if user_role == UserRoleEnum.admin or current_user.is_admin or is_cco or user_role == UserRoleEnum.health_manager or is_hm_tl or user_role == UserRoleEnum.marketing:
        return query
    
    # Team Leader: vede i pazienti assegnati ai membri del suo team
    elif user_role == UserRoleEnum.team_leader:
        team_member_ids = set()
        team_member_ids.add(current_user.id)  # Il TL deve vedere anche i propri pazienti
        for team in (current_user.teams_led or []):
            for member in (team.members or []):
                team_member_ids.add(member.id)
        
        if team_member_ids:
            member_ids_list = list(team_member_ids)
            return query.filter(
                or_(
                    # Assegnazione tramite FK singola
                    Cliente.nutrizionista_id.in_(member_ids_list),
                    Cliente.coach_id.in_(member_ids_list),
                    Cliente.psicologa_id.in_(member_ids_list),
                    Cliente.consulente_alimentare_id.in_(member_ids_list),
                    # Assegnazione tramite M2M
                    exists(select(cliente_nutrizionisti.c.cliente_id).where(cliente_nutrizionisti.c.cliente_id == Cliente.cliente_id).where(cliente_nutrizionisti.c.user_id.in_(member_ids_list))),
                    exists(select(cliente_coaches.c.cliente_id).where(cliente_coaches.c.cliente_id == Cliente.cliente_id).where(cliente_coaches.c.user_id.in_(member_ids_list))),
                    exists(select(cliente_psicologi.c.cliente_id).where(cliente_psicologi.c.cliente_id == Cliente.cliente_id).where(cliente_psicologi.c.user_id.in_(member_ids_list))),
                    exists(select(cliente_consulenti.c.cliente_id).where(cliente_consulenti.c.cliente_id == Cliente.cliente_id).where(cliente_consulenti.c.user_id.in_(member_ids_list))),
                    # Assegnazione tramite history (es. Medico nel team)
                    exists(
                        select(ClienteProfessionistaHistory.cliente_id).where(
                            ClienteProfessionistaHistory.cliente_id == Cliente.cliente_id,
                            ClienteProfessionistaHistory.user_id.in_(member_ids_list),
                            ClienteProfessionistaHistory.is_active == True,
                        )
                    ),
                )
            )
        return query.filter(False)
    
    # Professionista: per nutrizione / coach / psicologia usiamo la M2M della
    # specialità; il medico resta legato allo storico attivo di tipo medico.
    elif user_role == UserRoleEnum.professionista:
        return query.filter(professionista_visibility_clause(current_user))

    # Influencer: vede solo i clienti con origine tra quelle assegnate (M2M)
    elif user_role == UserRoleEnum.influencer:
        origine_ids = [o.id for o in current_user.influencer_origins]
        if not origine_ids:
            return query.filter(False)  # Nessuna origine → nessun cliente
        return query.filter(Cliente.origine_id.in_(origine_ids))

    # health_manager: gestito sopra con admin/CCO (vede e modifica tutti i clienti)

    return query


def calculate_dashboard_kpis(filters: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Calcola i KPI principali per la dashboard 360°.
    
    Returns:
        Dict con i KPI calcolati
    """
    from corposostenibile.models import TypeFormResponse
    
    # Query base
    query = db.session.query(Cliente)
    query = apply_role_filtering(query)
    
    # Applica filtri se presenti
    if filters:
        if filters.get('statoCliente'):
            query = query.filter(Cliente.stato_cliente.in_(filters['statoCliente']))
        if filters.get('team'):
            query = query.filter(Cliente.di_team.in_(filters['team']))
        if filters.get('tipologia'):
            query = query.filter(Cliente.tipologia_cliente.in_(filters['tipologia']))
    
    # Calcola KPI
    total_clients = query.count()
    clienti_attivi = query.filter(Cliente.stato_cliente == 'attivo').count()
    
    # Calcola retention rate
    retention_query = query.filter(
        Cliente.data_rinnovo.isnot(None),
        Cliente.created_at <= datetime.now() - timedelta(days=90)
    )
    retained = retention_query.filter(Cliente.stato_cliente == 'attivo').count()
    total_eligible = retention_query.count()
    retention_rate = round((retained / total_eligible * 100) if total_eligible > 0 else 0, 1)
    
    # Health Score medio (semplificato)
    health_score_avg = 75  # Placeholder - calcoleremo in dettaglio nella funzione dedicata
    
    # Permanenza media in mesi
    avg_permanenza_query = db.session.query(
        func.avg(func.extract('epoch', datetime.now() - Cliente.data_inizio_abbonamento) / 2592000)
    )
    avg_permanenza_query = apply_role_filtering(avg_permanenza_query)
    avg_permanenza = avg_permanenza_query.filter(Cliente.stato_cliente == 'attivo').scalar() or 0
    avg_permanenza = round(float(avg_permanenza), 1)
    
    # Alert critici
    alert_critici = query.filter(Cliente.alert == True).count()
    
    # In scadenza
    today = date.today()
    in_scadenza_7 = query.filter(
        Cliente.data_rinnovo.isnot(None),
        Cliente.data_rinnovo <= today + timedelta(days=7),
        Cliente.data_rinnovo >= today
    ).count()
    
    in_scadenza_30 = query.filter(
        Cliente.data_rinnovo.isnot(None),
        Cliente.data_rinnovo <= today + timedelta(days=30),
        Cliente.data_rinnovo >= today
    ).count()
    
    return {
        'clienti_attivi': clienti_attivi,
        'retention_rate': retention_rate,
        'health_score_avg': health_score_avg,
        'avg_permanenza': avg_permanenza,
        'alert_critici': alert_critici,
        'in_scadenza': in_scadenza_7,
        'in_scadenza_30': in_scadenza_30
    }


def calculate_health_scores(filters: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Calcola Health Score e metriche wellness dai TypeForm responses.
    
    Returns:
        Dict con health scores e wellness metrics
    """
    from corposostenibile.models import TypeFormResponse
    
    # Query per l'ultimo TypeForm di ogni cliente
    subquery = db.session.query(
        TypeFormResponse.cliente_id,
        func.max(TypeFormResponse.submit_date).label('max_date')
    ).group_by(TypeFormResponse.cliente_id).subquery()
    
    query = db.session.query(TypeFormResponse).join(
        subquery,
        (TypeFormResponse.cliente_id == subquery.c.cliente_id) &
        (TypeFormResponse.submit_date == subquery.c.max_date)
    ).join(Cliente, TypeFormResponse.cliente_id == Cliente.cliente_id)
    
    # Applica filtro per ruolo
    query = apply_role_filtering(query)
    
    # Calcola medie wellness
    wellness_avgs = db.session.query(
        func.avg(TypeFormResponse.energy_rating).label('energy'),
        func.avg(TypeFormResponse.mood_rating).label('mood'),
        func.avg(TypeFormResponse.sleep_rating).label('sleep'),
        func.avg(TypeFormResponse.motivation_rating).label('motivation'),
        func.avg(TypeFormResponse.digestion_rating).label('digestion'),
        func.avg(TypeFormResponse.strength_rating).label('strength'),
        func.avg(TypeFormResponse.hunger_rating).label('hunger')
    ).join(Cliente, TypeFormResponse.cliente_id == Cliente.cliente_id)
    
    # Applica filtro per ruolo anche qui
    wellness_avgs_query = apply_role_filtering(wellness_avgs)
    wellness_avgs = wellness_avgs_query.filter(TypeFormResponse.submit_date >= datetime.now() - timedelta(days=30)).first()
    
    # Calcola health score globale (formula composita)
    health_components = []
    
    # Performance fisica (40%)
    if wellness_avgs.energy and wellness_avgs.strength:
        physical = (float(wellness_avgs.energy or 0) + float(wellness_avgs.strength or 0)) / 2
        health_components.append(physical * 0.4)
    
    # Benessere mentale (30%)
    if wellness_avgs.mood and wellness_avgs.motivation:
        mental = (float(wellness_avgs.mood or 0) + float(wellness_avgs.motivation or 0)) / 2
        health_components.append(mental * 0.3)
    
    # Qualità del sonno e digestione (20%)
    if wellness_avgs.sleep and wellness_avgs.digestion:
        recovery = (float(wellness_avgs.sleep or 0) + float(wellness_avgs.digestion or 0)) / 2
        health_components.append(recovery * 0.2)
    
    # Aderenza (10%) - placeholder
    adherence_score = 7  # Da calcolare basandosi su check_saltati
    health_components.append(adherence_score * 0.1)
    
    global_score = round(sum(health_components) * 10, 1) if health_components else 0
    
    return {
        'global_score': global_score,
        'total_clients': query.count(),
        'wellness': {
            'energy': round(float(wellness_avgs.energy or 0), 1),
            'mood': round(float(wellness_avgs.mood or 0), 1),
            'sleep': round(float(wellness_avgs.sleep or 0), 1),
            'motivation': round(float(wellness_avgs.motivation or 0), 1),
            'digestion': round(float(wellness_avgs.digestion or 0), 1),
            'strength': round(float(wellness_avgs.strength or 0), 1),
            'hunger': round(float(wellness_avgs.hunger or 0), 1)
        }
    }


def calculate_temporal_metrics(filters: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Calcola metriche temporali e ciclo di vita dei clienti.
    
    Returns:
        Dict con metriche temporali suddivise per fase
    """
    today = date.today()
    
    # Query base
    query = db.session.query(Cliente)
    query = apply_role_filtering(query)
    
    # Applica filtri se presenti
    if filters:
        if filters.get('statoCliente'):
            query = query.filter(Cliente.stato_cliente.in_(filters['statoCliente']))
    
    # Fase Onboarding (0-30gg)
    onboarding_query = query.filter(
        Cliente.data_inizio_abbonamento >= today - timedelta(days=30),
        Cliente.data_inizio_abbonamento.isnot(None)
    )
    onboarding_count = onboarding_query.count()
    
    # Calcola % call iniziali completate
    onboarding_with_calls = onboarding_query.filter(
        or_(
            Cliente.call_iniziale_nutrizionista == True,
            Cliente.call_iniziale_coach == True,
            Cliente.call_iniziale_psicologa == True
        )
    ).count()
    onboarding_calls_perc = round((onboarding_with_calls / onboarding_count * 100) if onboarding_count > 0 else 0)
    
    # Fase Attivazione (30-90gg)
    activation_query = query.filter(
        Cliente.data_inizio_abbonamento <= today - timedelta(days=30),
        Cliente.data_inizio_abbonamento >= today - timedelta(days=90),
        Cliente.data_inizio_abbonamento.isnot(None)
    )
    activation_count = activation_query.count()
    
    # % con piani attivi
    activation_with_plans = activation_query.filter(
        or_(
            Cliente.piano_alimentare.isnot(None),
            Cliente.allenamento_dal.isnot(None)
        )
    ).count()
    activation_plans_perc = round((activation_with_plans / activation_count * 100) if activation_count > 0 else 0)
    
    # Fase Crescita (90-180gg)
    growth_query = query.filter(
        Cliente.data_inizio_abbonamento <= today - timedelta(days=90),
        Cliente.data_inizio_abbonamento >= today - timedelta(days=180),
        Cliente.data_inizio_abbonamento.isnot(None)
    )
    growth_count = growth_query.count()
    
    # % con trasformazioni
    growth_with_transformations = growth_query.filter(
        Cliente.trasformazione_fisica == True
    ).count()
    growth_transformations_perc = round((growth_with_transformations / growth_count * 100) if growth_count > 0 else 0)
    
    # Fase Maturità (180+gg)
    maturity_query = query.filter(
        Cliente.data_inizio_abbonamento <= today - timedelta(days=180),
        Cliente.data_inizio_abbonamento.isnot(None)
    )
    maturity_count = maturity_query.count()
    
    # % retention nella fase maturità
    maturity_active = maturity_query.filter(Cliente.stato_cliente == 'attivo').count()
    maturity_retention_perc = round((maturity_active / maturity_count * 100) if maturity_count > 0 else 0)
    
    return {
        'onboarding_count': onboarding_count,
        'onboarding_calls': onboarding_calls_perc,
        'activation_count': activation_count,
        'activation_plans': activation_plans_perc,
        'growth_count': growth_count,
        'growth_transformations': growth_transformations_perc,
        'maturity_count': maturity_count,
        'maturity_retention': maturity_retention_perc
    }


def calculate_segments(filters: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Calcola segmentazione comportamentale dei clienti.
    
    Returns:
        Dict con conteggi per segmento
    """
    from corposostenibile.models import TypeFormResponse
    
    # Query base
    query = db.session.query(Cliente)
    
    # Applica filtro per ruolo
    query = apply_role_filtering(query)
    
    # Champions: Health Score >85%, Zero o uno check saltati
    champions = query.filter(
        Cliente.stato_cliente == 'attivo',
        or_(Cliente.check_saltati == '1', Cliente.check_saltati.is_(None))
    ).count()
    
    # Potenziali: attivi con 2 check saltati
    potenziali = query.filter(
        Cliente.stato_cliente == 'attivo',
        Cliente.check_saltati == '2'
    ).count()
    
    # A Rischio: Check saltati >2 o in pausa
    rischio = query.filter(
        or_(
            Cliente.check_saltati.in_(['3', '3_plus']),
            Cliente.stato_cliente == 'pausa'
        )
    ).count()
    
    # Critici: Ghost/Ghosting o con alert
    critici = query.filter(
        or_(
            Cliente.stato_cliente == 'ghost',
            Cliente.alert == True
        )
    ).count()
    
    return {
        'champions': champions,
        'potenziali': potenziali,
        'rischio': rischio,
        'critici': critici
    }


# ════════════════════════════════════════════════════════════════════════════
#                               FREEZE MANAGEMENT
# ════════════════════════════════════════════════════════════════════════════
def freeze_cliente(cliente_id: int, user, reason: str = None) -> dict:
    """
    Mette un cliente in stato FREEZE.
    Solo Health Manager (dept_id=13) o admin possono eseguire questa azione.

    Args:
        cliente_id: ID del cliente da freezare
        user: Utente che esegue l'azione
        reason: Motivazione del freeze (opzionale)

    Returns:
        dict con status e messaggio
    """
    from corposostenibile.models import Cliente, ClienteFreezeHistory, StatoClienteEnum
    from corposostenibile.blueprints.customers.notifications import send_freeze_notification
    from datetime import datetime

    # Verifica permessi
    if not user.is_admin and (not user.department or user.department.id != 13):
        return {"status": "error", "message": "Solo Health Manager o admin possono eseguire questa azione"}

    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).first()
    if not cliente:
        return {"status": "error", "message": "Cliente non trovato"}

    # Se già in freeze, non fare nulla
    if cliente.is_frozen:
        return {"status": "warning", "message": "Cliente già in stato FREEZE"}

    try:
        # 1. Aggiorna stato cliente
        # "freeze" non è più uno stato ufficiale: usiamo PAUSA come stato globale.
        cliente.stato_cliente = StatoClienteEnum.pausa
        cliente.is_frozen = True
        cliente.freeze_date = datetime.utcnow()
        cliente.freeze_reason = reason
        cliente.frozen_by_id = user.id

        # 2. Crea record nello storico
        history = ClienteFreezeHistory(
            cliente_id=cliente_id,
            freeze_date=datetime.utcnow(),
            freeze_reason=reason,
            frozen_by_id=user.id,
            is_active=True
        )
        db.session.add(history)

        # 3. Log activity (import and use ActivityLog if available)
        try:
            from corposostenibile.blueprints.customers.models.activity_log import ActivityLog
            log = ActivityLog(
                cliente_id=cliente_id,
                user_id=user.id,
                field="stato_cliente",
                before=str(cliente.stato_cliente.value) if cliente.stato_cliente else "attivo",
                after="pausa",
                ts=datetime.utcnow()
            )
            db.session.add(log)
        except (ImportError, TypeError) as e:
            # ActivityLog non disponibile o errore parametri, skip logging
            current_app.logger.debug(f"Skip ActivityLog: {e}")

        db.session.commit()

        # 4. Invia notifiche email ai professionisti
        try:
            send_freeze_notification(cliente, user, reason)
        except Exception as e:
            # Log dell'errore ma non bloccare l'operazione
            current_app.logger.warning(f"Errore invio notifiche freeze: {e}")

        return {
            "status": "success",
            "message": "Cliente messo in FREEZE con successo",
            "history_id": history.id
        }

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore freeze cliente {cliente_id}: {str(e)}")
        return {"status": "error", "message": f"Errore durante il freeze: {str(e)}"}


def unfreeze_cliente(cliente_id: int, user, resolution: str = None) -> dict:
    """
    Rimuove un cliente dallo stato FREEZE.
    Solo Health Manager (dept_id=13) o admin possono eseguire questa azione.

    Args:
        cliente_id: ID del cliente da unfreezare
        user: Utente che esegue l'azione
        resolution: Storia/risoluzione del freeze (opzionale)

    Returns:
        dict con status e messaggio
    """
    from corposostenibile.models import Cliente, ClienteFreezeHistory, StatoClienteEnum
    from corposostenibile.blueprints.customers.notifications import send_unfreeze_notification
    from datetime import datetime

    # Verifica permessi
    if not user.is_admin and (not user.department or user.department.id != 13):
        return {"status": "error", "message": "Solo Health Manager o admin possono eseguire questa azione"}

    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).first()
    if not cliente:
        return {"status": "error", "message": "Cliente non trovato"}

    # Se non è in freeze, non fare nulla
    if not cliente.is_frozen:
        return {"status": "warning", "message": "Cliente non è in stato FREEZE"}

    try:
        # 1. Aggiorna stato cliente (torna ad attivo)
        cliente.stato_cliente = StatoClienteEnum.attivo
        cliente.is_frozen = False
        cliente.freeze_resolution = resolution
        cliente.unfrozen_by_id = user.id

        # 2. Aggiorna record storico attivo
        history = db.session.query(ClienteFreezeHistory).filter_by(
            cliente_id=cliente_id,
            is_active=True
        ).first()

        if history:
            history.unfreeze_date = datetime.utcnow()
            history.unfreeze_resolution = resolution
            history.unfrozen_by_id = user.id
            history.is_active = False

        # 3. Log activity (import and use ActivityLog if available)
        try:
            from corposostenibile.blueprints.customers.models.activity_log import ActivityLog
            log = ActivityLog(
                cliente_id=cliente_id,
                user_id=user.id,
                field="stato_cliente",
                before="pausa",
                after="attivo",
                ts=datetime.utcnow()
            )
            db.session.add(log)
        except (ImportError, TypeError) as e:
            # ActivityLog non disponibile o errore parametri, skip logging
            current_app.logger.debug(f"Skip ActivityLog: {e}")

        db.session.commit()

        # 4. Invia notifiche email ai professionisti
        try:
            send_unfreeze_notification(cliente, user, resolution)
        except Exception as e:
            # Log dell'errore ma non bloccare l'operazione
            current_app.logger.warning(f"Errore invio notifiche unfreeze: {e}")

        return {
            "status": "success",
            "message": "Cliente rimosso da FREEZE con successo"
        }

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore unfreeze cliente {cliente_id}: {str(e)}")
        return {"status": "error", "message": f"Errore durante l'unfreeze: {str(e)}"}


# ════════════════════════════════════════════════════════════════════════════
#                             CALL BONUS MANAGEMENT
# ════════════════════════════════════════════════════════════════════════════

def create_call_bonus(
    cliente_id: int,
    professionista_id: int,
    tipo_professionista: TipoProfessionistaEnum,
    created_by_user,
    data_richiesta: date = None
) -> CallBonus:
    """
    Crea una nuova richiesta di call bonus per un cliente.

    Args:
        cliente_id: ID del cliente
        professionista_id: ID del professionista con cui proporre la call
        tipo_professionista: Tipo di professionista (nutrizionista, coach, psicologa)
        created_by_user: Utente che crea la richiesta
        data_richiesta: Data della richiesta (default: oggi)

    Returns:
        CallBonus: La richiesta creata
    """
    with _commit_or_rollback() as session:
        call_bonus = CallBonus(
            cliente_id=cliente_id,
            professionista_id=professionista_id,
            tipo_professionista=tipo_professionista,
            status=CallBonusStatusEnum.proposta,
            data_richiesta=data_richiesta or date.today(),
            created_by_id=_user_id(created_by_user)
        )
        session.add(call_bonus)
        session.flush()

    current_app.logger.info(
        f"Creata call bonus {call_bonus.id} per cliente {cliente_id} "
        f"con professionista {professionista_id}"
    )
    return call_bonus


def update_call_bonus_response(
    call_bonus_id: int,
    status: str,
    motivazione_rifiuto: str = None,
    data_risposta: date = None
) -> CallBonus:
    """
    Aggiorna la risposta del cliente alla call bonus (accettata/rifiutata).

    Args:
        call_bonus_id: ID della call bonus
        status: 'accettata' o 'rifiutata'
        motivazione_rifiuto: Motivazione se rifiutata
        data_risposta: Data della risposta (default: oggi)

    Returns:
        CallBonus: La call bonus aggiornata
    """
    with _commit_or_rollback() as session:
        call_bonus = session.get(CallBonus, call_bonus_id)
        if not call_bonus:
            raise ValueError("Call bonus non trovata.")

        # Aggiorna stato
        if status == 'accettata':
            call_bonus.status = CallBonusStatusEnum.accettata
        elif status == 'rifiutata':
            call_bonus.status = CallBonusStatusEnum.rifiutata
            call_bonus.motivazione_rifiuto = motivazione_rifiuto
        else:
            raise ValueError("Status non valido. Usa 'accettata' o 'rifiutata'.")

        call_bonus.data_risposta = data_risposta or date.today()
        session.flush()

    current_app.logger.info(
        f"Call bonus {call_bonus_id} aggiornata: {status}"
    )
    return call_bonus


def update_call_bonus_hm_confirm(
    call_bonus_id: int,
    confermata_hm: bool,
    note_hm: str,
    hm_user,
    data_conferma_hm: date = None
) -> CallBonus:
    """
    Aggiorna la conferma dell'health manager per la call bonus.

    Args:
        call_bonus_id: ID della call bonus
        confermata_hm: True = confermata/adottata, False = non andata a buon fine
        note_hm: Note dell'health manager
        hm_user: Utente health manager che gestisce
        data_conferma_hm: Data della conferma (default: oggi)

    Returns:
        CallBonus: La call bonus aggiornata
    """
    with _commit_or_rollback() as session:
        call_bonus = session.get(CallBonus, call_bonus_id)
        if not call_bonus:
            raise ValueError("Call bonus non trovata.")

        if call_bonus.status != CallBonusStatusEnum.accettata:
            raise ValueError("Puoi confermare solo call bonus accettate.")

        # Aggiorna conferma
        call_bonus.confermata_hm = confermata_hm
        call_bonus.note_hm = note_hm
        call_bonus.gestita_da_hm_id = _user_id(hm_user)
        call_bonus.data_conferma_hm = data_conferma_hm or date.today()

        # Aggiorna stato
        if confermata_hm:
            call_bonus.status = CallBonusStatusEnum.confermata
        else:
            call_bonus.status = CallBonusStatusEnum.non_andata_buon_fine

        session.flush()

    current_app.logger.info(
        f"Call bonus {call_bonus_id} confermata da HM: {confermata_hm}"
    )
    return call_bonus


def get_cliente_call_bonus_history(cliente_id: int) -> List[CallBonus]:
    """
    Ottiene tutto lo storico delle call bonus di un cliente.

    Args:
        cliente_id: ID del cliente

    Returns:
        List[CallBonus]: Lista delle call bonus ordinate per data
    """
    results = (
        db.session.query(CallBonus)
        .filter(CallBonus.cliente_id == cliente_id)
        .all()
    )
    # Ordina in Python invece che in SQL
    return sorted(results, key=lambda x: x.id, reverse=True)


def get_call_bonus_accettate(health_manager_id: int = None) -> List[CallBonus]:
    """
    Ottiene tutte le call bonus accettate, opzionalmente filtrate per health manager.

    Args:
        health_manager_id: ID dell'health manager (opzionale, per filtro)

    Returns:
        List[CallBonus]: Lista delle call bonus accettate
    """
    query = (
        db.session.query(CallBonus)
        .filter(CallBonus.status == CallBonusStatusEnum.accettata)
        .join(Cliente, CallBonus.cliente_id == Cliente.cliente_id)
    )

    # Filtro per health manager se specificato
    if health_manager_id:
        query = query.filter(Cliente.health_manager_id == health_manager_id)

    results = query.all()
    # Ordina in Python invece che in SQL
    return sorted(results, key=lambda x: x.id, reverse=True)


# ════════════════════════════════════════════════════════════════════════════
#                          MARKETING METRICS
# ════════════════════════════════════════════════════════════════════════════
def get_marketing_metrics_for_clienti(cliente_ids: Sequence[int]) -> Dict[int, Dict[str, Any]]:
    """
    Calcola per ciascun cliente:
      - peso_perso_kg: differenza tra il primo peso registrato (TypeFormResponse
        check iniziale + WeeklyCheckResponse settimanali) e l'ultimo in ordine
        cronologico. Positivo = peso perso.
      - media_soddisfazione: media dei voti nutrizionista + coach + psicologa +
        progress_rating presi dai WeeklyCheckResponse del cliente, escludendo
        i NULL dal denominatore (formula identica a unsatisfied_customers in
        routes.py).

    Ritorna un dict `{cliente_id: {peso_perso_kg, media_soddisfazione}}`.
    Se il cliente non ha dati, i valori sono None.
    """
    from corposostenibile.models import (
        TypeFormResponse,
        WeeklyCheck,
        WeeklyCheckResponse,
    )
    from sqlalchemy import case

    if not cliente_ids:
        return {}

    ids_list = list({int(c) for c in cliente_ids if c is not None})
    if not ids_list:
        return {}

    # ── Peso: raccogli tutti i weight (iniziali + settimanali) e scegli primo/ultimo ── #
    pesi_iniziali = (
        db.session.query(
            TypeFormResponse.cliente_id.label("cid"),
            TypeFormResponse.weight.label("w"),
            TypeFormResponse.submit_date.label("dt"),
        )
        .filter(
            TypeFormResponse.cliente_id.in_(ids_list),
            TypeFormResponse.weight.isnot(None),
        )
    )
    pesi_settimanali = (
        db.session.query(
            WeeklyCheck.cliente_id.label("cid"),
            WeeklyCheckResponse.weight.label("w"),
            WeeklyCheckResponse.submit_date.label("dt"),
        )
        .join(WeeklyCheck, WeeklyCheck.id == WeeklyCheckResponse.weekly_check_id)
        .filter(
            WeeklyCheck.cliente_id.in_(ids_list),
            WeeklyCheckResponse.weight.isnot(None),
        )
    )

    from collections import defaultdict
    pesi_by_cliente: Dict[int, List[Tuple[datetime, float]]] = defaultdict(list)
    for cid, w, dt in pesi_iniziali.all():
        if cid is None or w is None:
            continue
        pesi_by_cliente[int(cid)].append((dt, float(w)))
    for cid, w, dt in pesi_settimanali.all():
        if cid is None or w is None:
            continue
        pesi_by_cliente[int(cid)].append((dt, float(w)))

    peso_metrics: Dict[int, float] = {}
    for cid, rows in pesi_by_cliente.items():
        rows.sort(key=lambda r: r[0] or datetime.min)
        peso_iniziale = rows[0][1]
        peso_attuale = rows[-1][1]
        peso_metrics[cid] = round(peso_iniziale - peso_attuale, 1)

    # ── Media soddisfazione: formula replicata da routes.py:1918-1956 ── #
    avg_query = (
        db.session.query(
            WeeklyCheck.cliente_id.label("cliente_id"),
            func.avg(
                (
                    func.coalesce(WeeklyCheckResponse.nutritionist_rating.cast(db.Float), 0)
                    + func.coalesce(WeeklyCheckResponse.coach_rating.cast(db.Float), 0)
                    + func.coalesce(WeeklyCheckResponse.psychologist_rating.cast(db.Float), 0)
                    + func.coalesce(WeeklyCheckResponse.progress_rating.cast(db.Float), 0)
                ) / func.nullif(
                    (
                        case((WeeklyCheckResponse.nutritionist_rating.isnot(None), 1), else_=0)
                        + case((WeeklyCheckResponse.coach_rating.isnot(None), 1), else_=0)
                        + case((WeeklyCheckResponse.psychologist_rating.isnot(None), 1), else_=0)
                        + case((WeeklyCheckResponse.progress_rating.isnot(None), 1), else_=0)
                    ),
                    0,
                )
            ).label("avg_rating"),
        )
        .join(WeeklyCheck, WeeklyCheckResponse.weekly_check_id == WeeklyCheck.id)
        .filter(
            WeeklyCheck.cliente_id.in_(ids_list),
            or_(
                WeeklyCheckResponse.nutritionist_rating.isnot(None),
                WeeklyCheckResponse.coach_rating.isnot(None),
                WeeklyCheckResponse.psychologist_rating.isnot(None),
                WeeklyCheckResponse.progress_rating.isnot(None),
            ),
        )
        .group_by(WeeklyCheck.cliente_id)
    )
    media_metrics: Dict[int, float] = {}
    for cid, avg_val in avg_query.all():
        if cid is None or avg_val is None:
            continue
        media_metrics[int(cid)] = round(float(avg_val), 2)

    # ── Merge ── #
    result: Dict[int, Dict[str, Any]] = {}
    for cid in ids_list:
        result[cid] = {
            "peso_perso_kg": peso_metrics.get(cid),
            "media_soddisfazione": media_metrics.get(cid),
        }
    return result


def get_marketing_filtered_cliente_ids(
    *,
    media_min: float | None = None,
    media_max: float | None = None,
    peso_perso_min: float | None = None,
    peso_perso_max: float | None = None,
) -> list[int] | None:
    """
    Ritorna la lista di `cliente_id` che rispettano i range di media_soddisfazione
    e peso_perso_kg. Se nessun filtro è impostato ritorna None (non applicare
    restrizione). I vincoli sono calcolati come in
    `get_marketing_metrics_for_clienti` (stesse formule).
    """
    from corposostenibile.models import (
        TypeFormResponse,
        WeeklyCheck,
        WeeklyCheckResponse,
    )
    from sqlalchemy import case
    from collections import defaultdict

    if all(v is None for v in (media_min, media_max, peso_perso_min, peso_perso_max)):
        return None

    eligible: set[int] | None = None

    # ── Media soddisfazione: aggregazione GLOBALE per cliente ── #
    if media_min is not None or media_max is not None:
        avg_query = (
            db.session.query(
                WeeklyCheck.cliente_id.label("cid"),
                func.avg(
                    (
                        func.coalesce(WeeklyCheckResponse.nutritionist_rating.cast(db.Float), 0)
                        + func.coalesce(WeeklyCheckResponse.coach_rating.cast(db.Float), 0)
                        + func.coalesce(WeeklyCheckResponse.psychologist_rating.cast(db.Float), 0)
                        + func.coalesce(WeeklyCheckResponse.progress_rating.cast(db.Float), 0)
                    )
                    / func.nullif(
                        (
                            case((WeeklyCheckResponse.nutritionist_rating.isnot(None), 1), else_=0)
                            + case((WeeklyCheckResponse.coach_rating.isnot(None), 1), else_=0)
                            + case((WeeklyCheckResponse.psychologist_rating.isnot(None), 1), else_=0)
                            + case((WeeklyCheckResponse.progress_rating.isnot(None), 1), else_=0)
                        ),
                        0,
                    )
                ).label("media"),
            )
            .join(WeeklyCheck, WeeklyCheckResponse.weekly_check_id == WeeklyCheck.id)
            .filter(
                or_(
                    WeeklyCheckResponse.nutritionist_rating.isnot(None),
                    WeeklyCheckResponse.coach_rating.isnot(None),
                    WeeklyCheckResponse.psychologist_rating.isnot(None),
                    WeeklyCheckResponse.progress_rating.isnot(None),
                )
            )
            .group_by(WeeklyCheck.cliente_id)
        )
        matching_media: set[int] = set()
        for cid, media in avg_query.all():
            if cid is None or media is None:
                continue
            m = float(media)
            if media_min is not None and m < media_min:
                continue
            if media_max is not None and m > media_max:
                continue
            matching_media.add(int(cid))
        eligible = matching_media

    # ── Peso perso: calcolo per-cliente su tutti i weight disponibili ── #
    if peso_perso_min is not None or peso_perso_max is not None:
        # Pool di candidati: se abbiamo già filtrato per media, restringi a
        # quelli; altrimenti raccogli tutti i clienti con almeno un weight.
        pool_ids: set[int] | None = eligible
        q_initial = db.session.query(
            TypeFormResponse.cliente_id.label("cid"),
            TypeFormResponse.weight.label("w"),
            TypeFormResponse.submit_date.label("dt"),
        ).filter(TypeFormResponse.weight.isnot(None))
        q_weekly = (
            db.session.query(
                WeeklyCheck.cliente_id.label("cid"),
                WeeklyCheckResponse.weight.label("w"),
                WeeklyCheckResponse.submit_date.label("dt"),
            )
            .join(WeeklyCheck, WeeklyCheck.id == WeeklyCheckResponse.weekly_check_id)
            .filter(WeeklyCheckResponse.weight.isnot(None))
        )
        if pool_ids is not None:
            if not pool_ids:
                # Media già filtrata a 0 candidati → nessun cliente possibile
                return []
            q_initial = q_initial.filter(TypeFormResponse.cliente_id.in_(pool_ids))
            q_weekly = q_weekly.filter(WeeklyCheck.cliente_id.in_(pool_ids))

        rows_by_cid: Dict[int, List[Tuple[datetime, float]]] = defaultdict(list)
        for cid, w, dt in q_initial.all():
            if cid is None or w is None:
                continue
            rows_by_cid[int(cid)].append((dt, float(w)))
        for cid, w, dt in q_weekly.all():
            if cid is None or w is None:
                continue
            rows_by_cid[int(cid)].append((dt, float(w)))

        matching_peso: set[int] = set()
        for cid, rows in rows_by_cid.items():
            rows.sort(key=lambda r: r[0] or datetime.min)
            peso_perso = round(rows[0][1] - rows[-1][1], 1)
            if peso_perso_min is not None and peso_perso < peso_perso_min:
                continue
            if peso_perso_max is not None and peso_perso > peso_perso_max:
                continue
            matching_peso.add(cid)
        eligible = matching_peso if eligible is None else (eligible & matching_peso)

    return sorted(eligible) if eligible is not None else None
