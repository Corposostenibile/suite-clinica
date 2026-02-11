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

import requests
from flask import current_app
from sqlalchemy import desc, func, or_
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from corposostenibile.extensions import celery, db
from corposostenibile.models import (                 # pylint: disable=too-many-imports
    CallBonus,
    CallBonusStatusEnum,
    Cliente,
    PaymentTransaction,
    SalesPerson,
    SubscriptionContract,
    SubscriptionRenewal,
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

__all__ = [
    # CRUD & API pubblica
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
    # call bonus management
    "create_call_bonus",
    "update_call_bonus_response",
    "update_call_bonus_hm_confirm",
    "get_cliente_call_bonus_history",
    "get_call_bonus_accettate",
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

        cliente = Cliente(
            **{k: v for k, v in data.items() if hasattr(Cliente, k)},
            created_by=_user_id(created_by_user),
        )
        if consultant:
            cliente.personal_consultant = consultant
        session.add(cliente)
        session.flush()

        # Contratto iniziale (facoltativo)
        if "initial_contract" in data:
            _create_contract_for_cliente(cliente, data["initial_contract"], session)

    # post-commit
    emit_created(cliente, user_id=_user_id(created_by_user))
    _enqueue_async("customers.tasks.new_customer_notification", cliente_id=cliente.cliente_id)
    current_app.logger.info("Creato cliente %s", cliente.cliente_id)
    return cliente


def _check_and_update_global_ghost_status(cliente: Cliente, updated_by_user) -> bool:
    """
    Controlla se tutti i servizi assegnati (con almeno un professionista) sono in ghost.
    Se sì, aggiorna automaticamente lo stato_cliente a 'ghost'.
    Se il cliente è in ghost e almeno un servizio assegnato esce da ghost, riattiva (stato_cliente = 'attivo').

    Considera assegnato un servizio se il cliente ha:
    - professionisti multipli (lista non vuota) O
    - professionista singolo (nutrizionista_id/coach_id/psicologa_id) O
    - nome professionista legacy (nutrizionista/coach/psicologa stringa).

    Returns:
        bool: True se lo stato_cliente è stato aggiornato (ghost o attivo), False altrimenti
    """
    from datetime import datetime

    def _get_stato_value(stato) -> str | None:
        """Helper per ottenere il valore dello stato sia che sia Enum o stringa."""
        if stato is None:
            return None
        if hasattr(stato, 'value'):
            return stato.value
        return str(stato)

    def _has_nutrizione(cliente):
        return (
            (cliente.nutrizionisti_multipli and len(cliente.nutrizionisti_multipli) > 0)
            or cliente.nutrizionista_id
            or (getattr(cliente, 'nutrizionista', None) and str(cliente.nutrizionista).strip())
        )

    def _has_coach(cliente):
        return (
            (cliente.coaches_multipli and len(cliente.coaches_multipli) > 0)
            or cliente.coach_id
            or (getattr(cliente, 'coach', None) and str(cliente.coach).strip())
        )

    def _has_psicologia(cliente):
        return (
            (cliente.psicologi_multipli and len(cliente.psicologi_multipli) > 0)
            or cliente.psicologa_id
            or (getattr(cliente, 'psicologa', None) and str(cliente.psicologa).strip())
        )

    # Servizi da controllare (solo quelli con almeno un professionista assegnato: multipli o singolo)
    servizi_assegnati = []

    if _has_nutrizione(cliente):
        count = len(cliente.nutrizionisti_multipli) if cliente.nutrizionisti_multipli else 1
        servizi_assegnati.append({
            'nome': 'nutrizione',
            'stato': _get_stato_value(cliente.stato_nutrizione),
            'professionisti_count': count,
        })

    if _has_coach(cliente):
        count = len(cliente.coaches_multipli) if cliente.coaches_multipli else 1
        servizi_assegnati.append({
            'nome': 'coaching',
            'stato': _get_stato_value(cliente.stato_coach),
            'professionisti_count': count,
        })

    if _has_psicologia(cliente):
        count = len(cliente.psicologi_multipli) if cliente.psicologi_multipli else 1
        servizi_assegnati.append({
            'nome': 'psicologia',
            'stato': _get_stato_value(cliente.stato_psicologia),
            'professionisti_count': count,
        })

    # Se non ci sono servizi assegnati, non fare nulla
    if not servizi_assegnati:
        current_app.logger.info(
            f"Cliente {cliente.cliente_id} - Nessun servizio assegnato, skip controllo ghost globale"
        )
        return False

    # Controlla se TUTTI i servizi assegnati sono in ghost
    servizi_in_ghost = [s for s in servizi_assegnati if s['stato'] and s['stato'] == 'ghost']
    tutti_ghost = len(servizi_in_ghost) == len(servizi_assegnati)
    almeno_uno_non_ghost = any(
        s['stato'] and s['stato'] != 'ghost' for s in servizi_assegnati
    )

    current_app.logger.info(
        f"Cliente {cliente.cliente_id} - Servizi assegnati: {len(servizi_assegnati)}, "
        f"In ghost: {len(servizi_in_ghost)}, Tutti ghost: {tutti_ghost}"
    )

    stato_cliente_value = _get_stato_value(cliente.stato_cliente)

    # Se tutti i servizi assegnati sono in ghost → stato_cliente = ghost
    if tutti_ghost and stato_cliente_value != 'ghost':
        old_stato = cliente.stato_cliente
        cliente.stato_cliente = StatoClienteEnum.ghost
        cliente.stato_cliente_data = datetime.utcnow()

        db.session.add(
            ActivityLog(
                cliente_id=cliente.cliente_id,
                field='stato_cliente',
                before=_get_stato_value(old_stato),
                after='ghost',
                user_id=_user_id(updated_by_user),
            )
        )

        current_app.logger.info(
            f"Cliente {cliente.cliente_id} - Stato cliente aggiornato automaticamente a GHOST "
            f"(tutti i servizi assegnati sono in ghost)"
        )
        return True

    # Se il cliente è in ghost e almeno un servizio assegnato non è ghost → riattiva
    if stato_cliente_value == 'ghost' and almeno_uno_non_ghost:
        old_stato = cliente.stato_cliente
        cliente.stato_cliente = StatoClienteEnum.attivo
        cliente.stato_cliente_data = datetime.utcnow()

        db.session.add(
            ActivityLog(
                cliente_id=cliente.cliente_id,
                field='stato_cliente',
                before='ghost',
                after='attivo',
                user_id=_user_id(updated_by_user),
            )
        )

        current_app.logger.info(
            f"Cliente {cliente.cliente_id} - Stato cliente riattivato ad ATTIVO "
            f"(almeno un servizio assegnato non è più in ghost)"
        )
        return True

    return False


def _check_and_update_global_pausa_status(cliente: Cliente, updated_by_user) -> bool:
    """
    Controlla se tutti i servizi assegnati sono in pausa.
    Se sì, aggiorna automaticamente lo stato_cliente a 'pausa'.
    Se il cliente è in pausa e almeno un servizio esce da pausa, riattiva (stato_cliente = 'attivo').
    Stessa logica di _check_and_update_global_ghost_status ma per pausa.
    """
    from datetime import datetime

    def _get_stato_value(stato) -> str | None:
        if stato is None:
            return None
        if hasattr(stato, 'value'):
            return stato.value
        return str(stato)

    def _has_nutrizione(c):
        return (
            (c.nutrizionisti_multipli and len(c.nutrizionisti_multipli) > 0)
            or c.nutrizionista_id
            or (getattr(c, 'nutrizionista', None) and str(c.nutrizionista).strip())
        )

    def _has_coach(c):
        return (
            (c.coaches_multipli and len(c.coaches_multipli) > 0)
            or c.coach_id
            or (getattr(c, 'coach', None) and str(c.coach).strip())
        )

    def _has_psicologia(c):
        return (
            (c.psicologi_multipli and len(c.psicologi_multipli) > 0)
            or c.psicologa_id
            or (getattr(c, 'psicologa', None) and str(c.psicologa).strip())
        )

    servizi_assegnati = []
    if _has_nutrizione(cliente):
        count = len(cliente.nutrizionisti_multipli) if cliente.nutrizionisti_multipli else 1
        servizi_assegnati.append({'nome': 'nutrizione', 'stato': _get_stato_value(cliente.stato_nutrizione), 'professionisti_count': count})
    if _has_coach(cliente):
        count = len(cliente.coaches_multipli) if cliente.coaches_multipli else 1
        servizi_assegnati.append({'nome': 'coaching', 'stato': _get_stato_value(cliente.stato_coach), 'professionisti_count': count})
    if _has_psicologia(cliente):
        count = len(cliente.psicologi_multipli) if cliente.psicologi_multipli else 1
        servizi_assegnati.append({'nome': 'psicologia', 'stato': _get_stato_value(cliente.stato_psicologia), 'professionisti_count': count})

    if not servizi_assegnati:
        return False

    servizi_in_pausa = [s for s in servizi_assegnati if s['stato'] and s['stato'] == 'pausa']
    tutti_pausa = len(servizi_in_pausa) == len(servizi_assegnati)
    almeno_uno_non_pausa = any(s['stato'] and s['stato'] != 'pausa' for s in servizi_assegnati)
    stato_cliente_value = _get_stato_value(cliente.stato_cliente)

    if tutti_pausa and stato_cliente_value != 'pausa':
        old_stato = cliente.stato_cliente
        cliente.stato_cliente = StatoClienteEnum.pausa
        cliente.stato_cliente_data = datetime.utcnow()
        db.session.add(
            ActivityLog(
                cliente_id=cliente.cliente_id,
                field='stato_cliente',
                before=_get_stato_value(old_stato),
                after='pausa',
                user_id=_user_id(updated_by_user),
            )
        )
        current_app.logger.info(
            f"Cliente {cliente.cliente_id} - Stato cliente aggiornato automaticamente a PAUSA "
            f"(tutti i servizi assegnati sono in pausa)"
        )
        return True

    if stato_cliente_value == 'pausa' and almeno_uno_non_pausa:
        cliente.stato_cliente = StatoClienteEnum.attivo
        cliente.stato_cliente_data = datetime.utcnow()
        db.session.add(
            ActivityLog(
                cliente_id=cliente.cliente_id,
                field='stato_cliente',
                before='pausa',
                after='attivo',
                user_id=_user_id(updated_by_user),
            )
        )
        current_app.logger.info(
            f"Cliente {cliente.cliente_id} - Stato cliente riattivato ad ATTIVO "
            f"(almeno un servizio assegnato non è più in pausa)"
        )
        return True

    return False


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

    def _is_ghost_val(val) -> bool:
        if val is None:
            return False
        v = getattr(val, "value", val)
        return str(v) == "ghost"

    def _is_pausa_val(val) -> bool:
        if val is None:
            return False
        v = getattr(val, "value", val)
        return str(v) == "pausa"

    stato_cliente_prima = getattr(cliente, "stato_cliente", None)
    with _commit_or_rollback():
        # Traccia i cambiamenti delle patologie PRIMA di modificare i valori
        _track_patologie_changes(cliente, data)
        _track_patologie_psico_changes(cliente, data)

        # Gestione campi normali
        for k, v in data.items():
            if k in readonly or not hasattr(cliente, k):
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

        # ⚡ LOGICA GHOST AUTOMATICA ⚡
        # Se sono stati modificati stati servizi o professionisti, controlla se devo aggiornare stato_cliente
        stati_servizi_modificati = any(k in changes for k in ['stato_nutrizione', 'stato_coach', 'stato_psicologia'])
        professionisti_modificati = any(k in changes for k in ['nutrizionisti_multipli', 'coaches_multipli', 'psicologi_multipli'])

        if stati_servizi_modificati or professionisti_modificati:
            # Flush per assicurarsi che le modifiche siano visibili
            db.session.flush()
            # Controlla e aggiorna automaticamente stato_cliente (ghost e pausa) se necessario
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

    # Webhook GHL: quando il paziente passa in ghost (manuale, automatico in service o nel model)
    transitioned_to_ghost = not _is_ghost_val(stato_cliente_prima) and _is_ghost_val(
        getattr(cliente, "stato_cliente", None)
    )
    if transitioned_to_ghost:
        try:
            from corposostenibile.blueprints.ghl_integration.outbound import send_ghost_webhook_to_ghl
            send_ghost_webhook_to_ghl(cliente)
        except Exception as e:  # best-effort, non bloccare il flusso
            current_app.logger.warning(
                "Invio webhook GHL ghost per cliente %s fallito: %s",
                cliente.cliente_id,
                e,
            )

    transitioned_to_pausa = not _is_pausa_val(stato_cliente_prima) and _is_pausa_val(
        getattr(cliente, "stato_cliente", None)
    )
    if transitioned_to_pausa:
        try:
            from corposostenibile.blueprints.ghl_integration.outbound import send_pausa_webhook_to_ghl
            send_pausa_webhook_to_ghl(cliente)
        except Exception as e:
            current_app.logger.warning(
                "Invio webhook GHL pausa per cliente %s fallito: %s",
                cliente.cliente_id,
                e,
            )

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
    """
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
        else:
            for k, v in data.items():
                if hasattr(cliente, k):
                    setattr(cliente, k, v)
            updated += 1
    return created, updated


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
    
    # Admin: vede tutto
    if user_role == UserRoleEnum.admin:
        return query
    
    # Team Leader: vede i pazienti assegnati ai membri del suo team
    elif user_role == UserRoleEnum.team_leader:
        team_member_ids = set()
        for team in (current_user.teams_led or []):
            for member in (team.members or []):
                team_member_ids.add(member.id)
        
        if team_member_ids:
            member_ids_list = list(team_member_ids)
            return query.filter(
                or_(
                    exists(select(cliente_nutrizionisti.c.cliente_id).where(cliente_nutrizionisti.c.cliente_id == Cliente.cliente_id).where(cliente_nutrizionisti.c.user_id.in_(member_ids_list))),
                    exists(select(cliente_coaches.c.cliente_id).where(cliente_coaches.c.cliente_id == Cliente.cliente_id).where(cliente_coaches.c.user_id.in_(member_ids_list))),
                    exists(select(cliente_psicologi.c.cliente_id).where(cliente_psicologi.c.cliente_id == Cliente.cliente_id).where(cliente_psicologi.c.user_id.in_(member_ids_list))),
                    exists(select(cliente_consulenti.c.cliente_id).where(cliente_consulenti.c.cliente_id == Cliente.cliente_id).where(cliente_consulenti.c.user_id.in_(member_ids_list))),
                )
            )
        return query.filter(False)
    
    # Professionista: vede solo i propri pazienti
    elif user_role == UserRoleEnum.professionista:
        user_id = current_user.id
        return query.filter(
            or_(
                exists(select(cliente_nutrizionisti.c.cliente_id).where(cliente_nutrizionisti.c.cliente_id == Cliente.cliente_id).where(cliente_nutrizionisti.c.user_id == user_id)),
                exists(select(cliente_coaches.c.cliente_id).where(cliente_coaches.c.cliente_id == Cliente.cliente_id).where(cliente_coaches.c.user_id == user_id)),
                exists(select(cliente_psicologi.c.cliente_id).where(cliente_psicologi.c.cliente_id == Cliente.cliente_id).where(cliente_psicologi.c.user_id == user_id)),
                exists(select(cliente_consulenti.c.cliente_id).where(cliente_consulenti.c.cliente_id == Cliente.cliente_id).where(cliente_consulenti.c.user_id == user_id)),
            )
        )
        
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
        cliente.stato_cliente = StatoClienteEnum.freeze
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
                after="freeze",
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
                before="freeze",
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
