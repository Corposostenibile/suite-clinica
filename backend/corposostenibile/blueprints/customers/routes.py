# routes.py
# ---------------------------------------------------------------
# Blueprint "customers" – CRUD + Dashboard + REST API v1
# ---------------------------------------------------------------
from __future__ import annotations

from dataclasses import replace
import json
from datetime import date, datetime, timedelta
from http import HTTPStatus
import logging
from typing import Any, Dict
from urllib.parse import urlparse

from dateutil.relativedelta import relativedelta

from flask import (
    Blueprint,
    current_app,
    g,
    jsonify,
    request,
    url_for,
    abort,
)
from flask_login import current_user                    # type: ignore
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload
from werkzeug.exceptions import BadRequest, Forbidden, NotFound

from corposostenibile.extensions import db, csrf
from corposostenibile.models import (
    CartellaClinica,
    Cliente,
    ClientCheckAssignment,
    WeeklyCheck,
    WeeklyCheckResponse,
    MealPlan,
    TrainingPlan,
    TrainingLocation,
    StatoClienteEnum,
    LuogoAllenEnum,
    TipoProfessionistaEnum,
    UserRoleEnum,
    User,
    Origine,
    PagamentoInterno,
    PagamentoInternoApprovazione,
    PagamentoInternoStatusEnum,
    PagamentoEnum,
    AttribuibileAEnum,
    Package,
    PlanExtraFile,
    PlanTypeEnum,
    CallBonusStatusEnum,
    CallRinnovo,
    CallRinnovoStatusEnum,
    VideoFeedback,
    VideoFeedbackStatusEnum,
    TrustpilotReview,
    VideoReviewRequest,
)
from . import customers_bp                              # blueprint declared in __init__.py
from .filters import apply_customer_filters, parse_filter_args
from .permissions import CustomerPerm, permission_required
from .repository import customers_repo
from .schemas import ClienteSchema
from .services import (
    create_cliente,
    delete_cliente,
    restore_cliente_version,
    update_cliente,
    calculate_dashboard_kpis,
    apply_role_filtering,
)
from .trustpilot_service import (
    TrustpilotAPIError,
    TrustpilotConfigError,
    TrustpilotService,
)

logger = logging.getLogger(__name__)

# Backend template rendering is disabled: frontend app owns UI pages.
# --------------------------------------------------------------------------- #
#  Helper – metriche dashboard                                               #
# --------------------------------------------------------------------------- #
def _compute_dashboard_metrics() -> Dict[str, Any]:
    """
    Calcola KPI e dataset per la dashboard "Customers".

    Restituisce un dict serializzabile JSON:
        {
          "kpi": {...},
          "charts": {
              "new_customers_monthly": [...],
              "status_distribution": [...]
          }
        }
    """
    today = date.today()
    first_day_month = today.replace(day=1)
    threshold_scadenza = today + timedelta(days=30)

    # ▸ KPI -------------------------------------------------------------- #
    # ▸ KPI -------------------------------------------------------------- #
    query_base = db.session.query(Cliente)
    query_base = apply_role_filtering(query_base)

    total_clients = query_base.with_entities(func.count(Cliente.cliente_id)).scalar() or 0

    total_active = (
        query_base.filter(Cliente.stato_cliente == "attivo")
        .with_entities(func.count(Cliente.cliente_id))
        .scalar()
        or 0
    )

    new_month = (
        query_base
        .filter(Cliente.created_at >= first_day_month)
        .with_entities(func.count(Cliente.cliente_id))
        .scalar()
        or 0
    )

    in_scadenza = (
        query_base
        .filter(
            Cliente.data_rinnovo.isnot(None),
            Cliente.data_rinnovo <= threshold_scadenza,
        )
        .with_entities(func.count(Cliente.cliente_id))
        .scalar()
        or 0
    )

    percent_scadenza = round((in_scadenza / total_clients) * 100, 2) if total_clients else 0.0

    # ▸ KPI per Specialty (Nutrizione, Coach, Psicologia) --------------- #
    nutrizione_attivo = (
        query_base
        .filter(Cliente.stato_nutrizione == "attivo")
        .with_entities(func.count(Cliente.cliente_id))
        .scalar()
        or 0
    )

    coach_attivo = (
        query_base
        .filter(Cliente.stato_coach == "attivo")
        .with_entities(func.count(Cliente.cliente_id))
        .scalar()
        or 0
    )

    psicologia_attivo = (
        query_base
        .filter(Cliente.stato_psicologia == "attivo")
        .with_entities(func.count(Cliente.cliente_id))
        .scalar()
        or 0
    )

    # ▸ Nuovi clienti per mese (ultimi 12) ------------------------------- #
    start_period = (first_day_month - relativedelta(months=11)).replace(day=1)
    
    # Query aggregata con filtro applicato
    monthly_query = db.session.query(
        func.date_trunc("month", Cliente.created_at).label("month"),
        func.count(Cliente.cliente_id).label("count"),
    )
    monthly_query = apply_role_filtering(monthly_query)
        
    monthly_rows = (
        monthly_query
        .filter(Cliente.created_at >= start_period)
        .group_by("month")
        .order_by("month")
        .all()
    )
    new_customers_monthly = [
        {"month": row.month.strftime("%Y-%m"), "count": row.count}
        for row in monthly_rows
    ]

    # ▸ Distribuzione stato cliente -------------------------------------- #
    status_query = db.session.query(Cliente.stato_cliente, func.count(Cliente.cliente_id))
    status_query = apply_role_filtering(status_query)
    
    status_rows = (
        status_query
        .group_by(Cliente.stato_cliente)
        .all()
    )
    status_distribution = [
        {
            "status": status.value if status is not None else "undefined",
            "count": count,
        }
        for status, count in status_rows
    ]

    return {
        "kpi": {
            "total_active": total_active,
            "new_month": new_month,
            "percent_scadenza": percent_scadenza,
        },
        "charts": {
            "new_customers_monthly": new_customers_monthly,
            "status_distribution": status_distribution,
        },
        # Stats for React frontend
        "total_clienti": total_clients,
        "nutrizione_attivo": nutrizione_attivo,
        "coach_attivo": coach_attivo,
        "psicologia_attivo": psicologia_attivo,
    }

# --------------------------------------------------------------------------- #
#  Row-level loader (ACL "sales")                                             #
# --------------------------------------------------------------------------- #
@customers_bp.url_value_preprocessor
def _load_cliente(_endpoint, values):  # noqa: D401
    """Carica il cliente in g.cliente (o None) se <cliente_id> presente nella URL."""
    cid = values.get("cliente_id") if values else None
    if cid:
        try:
            g.cliente = customers_repo.get_one(int(cid), eager=True)
        except NotFound:
            g.cliente = None

# --------------------------------------------------------------------------- #
#  Context processor                                                          #
# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #
#  DASHBOARD                                                                  #
# --------------------------------------------------------------------------- #

@customers_bp.route("/dashboard/data", methods=["POST"])
@permission_required(CustomerPerm.VIEW)
def dashboard_data():
    """API endpoint per aggiornare i dati della dashboard con filtri."""
    filters = request.json
    
    # Applica filtri e ricalcola KPI
    kpi = calculate_dashboard_kpis(filters)
    
    # Ricalcola grafici con filtri
    charts = {
        'stati_cliente': _get_stati_distribution(filters),
        'tipologia': _get_tipologia_distribution(filters),
        'wellness_trend': _get_wellness_trend(filters)
    }
    
    return jsonify({
        'kpi': kpi,
        'charts': charts
    })

# --------------------------------------------------------------------------- #
#  LISTA / FILTRI                                                             #
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
#  VISUALE NUTRIZIONISTA                                                      #
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
#  VISUALE COACH                                                               #
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
#  VISUALE PSICOLOGIA                                                         #
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
#  VISUALE FINANCE                                                            #
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
#  CREATE                                                                     #
# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #
#  DETAIL                                                                     #
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
#  DETAIL                                                                     #
# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #
#  HISTORY                                                                    #
# --------------------------------------------------------------------------- #

@customers_bp.route("/<int:cliente_id>/history/json", methods=["GET"])
@permission_required(CustomerPerm.VIEW_HISTORY)
def history_json(cliente_id: int):
    """Restituisce lo storico versioni in formato JSON per AJAX."""
    try:
        # Start fresh session to avoid transaction issues
        db.session.rollback()
        
        cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).first()
        if not cliente:
            return jsonify({"error": "Cliente non trovato"}), HTTPStatus.NOT_FOUND
        
        # Import versioning classes and timezone
        from sqlalchemy_continuum import version_class, transaction_class
        import pytz
        from sqlalchemy import text
        from datetime import timedelta
        
        # Get version class and transaction class
        ClienteVersion = version_class(Cliente)
        Transaction = transaction_class(Cliente)
        
        # Query versions with transaction info
        versions_query = db.session.query(ClienteVersion).filter(
            ClienteVersion.cliente_id == cliente_id
        ).order_by(ClienteVersion.transaction_id.desc()).limit(50).all()
        
        versions_data = []
        
        # Italy timezone (handles DST automatically)
        italy_tz = pytz.timezone('Europe/Rome')
        
        for version in versions_query:
            # Get transaction info using raw SQL to avoid user_id column issue
            timestamp_str = 'Data non disponibile'
            user_str = None
            
            try:
                result = db.session.execute(
                    text("SELECT issued_at FROM transaction WHERE id = :tx_id"),
                    {"tx_id": version.transaction_id}
                ).first()
                
                if result and result[0]:
                    utc_time = pytz.utc.localize(result[0])
                    italy_time = utc_time.astimezone(italy_tz)
                    timestamp_str = italy_time.strftime('%d/%m/%Y %H:%M')
                    
                    # Try to get user from ActivityLog based on timestamp
                    from corposostenibile.blueprints.customers.models.activity_log import ActivityLog
                    from corposostenibile.models import User
                    
                    # Find ActivityLog entry near this timestamp for this cliente
                    activity = db.session.query(ActivityLog).filter(
                        ActivityLog.cliente_id == cliente_id,
                        ActivityLog.ts >= result[0] - timedelta(seconds=5),
                        ActivityLog.ts <= result[0] + timedelta(seconds=5)
                    ).first()
                    
                    if activity and activity.user_id:
                        user = db.session.query(User).filter_by(id=activity.user_id).first()
                        if user:
                            # Use full name if available, otherwise email
                            if hasattr(user, 'full_name') and user.full_name:
                                user_str = user.full_name
                            else:
                                user_str = user.email or f"User #{user.id}"
                            
            except Exception as e:
                logger.debug(f"Error getting transaction timestamp: {e}")
                db.session.rollback()  # Clear any error state
            
            # Build version info
            version_info = {
                'version_num': version.transaction_id,
                'tx_id': version.transaction_id,
                'timestamp': timestamp_str,
                'user': user_str,
                'changes': {},
                'can_restore': current_user.is_authenticated
            }
            
            # Get changeset safely
            try:
                if hasattr(version, 'changeset') and version.changeset:
                    for field_name, (old_val, new_val) in version.changeset.items():
                        # Skip system fields
                        if field_name in ['cliente_id', 'created_at', 'updated_at', 'search_vector', 'created_by']:
                            continue
                        
                        # Convert dates to string
                        if hasattr(old_val, 'strftime'):
                            old_val = old_val.strftime('%Y-%m-%d') if old_val else None
                        if hasattr(new_val, 'strftime'):
                            new_val = new_val.strftime('%Y-%m-%d') if new_val else None
                        
                        # Convert enums to string
                        if hasattr(old_val, 'value'):
                            old_val = old_val.value
                        if hasattr(new_val, 'value'):
                            new_val = new_val.value
                        
                        # Get human-readable field name
                        field_label = field_name.replace('_', ' ').title()

                        # Store the change
                        version_info['changes'][field_label] = {
                            'old': str(old_val) if old_val not in [None, ''] else 'vuoto',
                            'new': str(new_val) if new_val not in [None, ''] else 'vuoto'
                        }
            except Exception as e:
                logger.debug(f"Error getting changeset: {e}")
                # Continue without changeset
            
            # Determine operation type
            if version.operation_type == 0:  # Insert
                version_info['operation'] = 'Creazione'
            elif version.operation_type == 1:  # Update
                version_info['operation'] = 'Modifica'
            elif version.operation_type == 2:  # Delete
                version_info['operation'] = 'Eliminazione'
            else:
                version_info['operation'] = 'Sconosciuto'
            
            # Only add if there are changes or it's a special operation
            if version_info['changes'] or version.operation_type in [0, 2]:
                versions_data.append(version_info)
        
        return jsonify({'versions': versions_data}), HTTPStatus.OK
        
    except Exception as exc:
        logger.exception(f"Errore nel recupero della cronologia per cliente {cliente_id}: {exc}")
        return jsonify({"error": str(exc)}), HTTPStatus.INTERNAL_SERVER_ERROR

@customers_bp.route("/<int:cliente_id>/history/<int:tx_id>/restore", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def history_restore_view(cliente_id: int, tx_id: int):
    """Ripristina lo stato alla transazione *tx_id*."""
    logger.info(f"Restore request - Cliente: {cliente_id}, TX: {tx_id}, User: {current_user}")
    
    # Verifica che l'utente sia autenticato
    if not current_user.is_authenticated:
        logger.warning(f"Restore denied - User not authenticated: {current_user}")
        return jsonify({"error": "Devi essere autenticato per ripristinare versioni"}), HTTPStatus.FORBIDDEN
        
    try:
        logger.info(f"Attempting restore for cliente {cliente_id} to tx {tx_id}")
        restore_cliente_version(cliente_id, tx_id, current_user)
        db.session.commit()
        logger.info(f"Restore successful for cliente {cliente_id}")
        
        # Return JSON response for AJAX
        return jsonify({"success": True, "message": "Versione ripristinata con successo"}), HTTPStatus.OK
        
    except Exception as exc:  # pragma: no cover
        db.session.rollback()
        logger.exception(f"Errore ripristino versione cliente {cliente_id} tx {tx_id}: {exc}")
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST

# --------------------------------------------------------------------------- #
#  EDIT / DELETE                                                              #
# --------------------------------------------------------------------------- #

@customers_bp.route("/<int:cliente_id>/delete", methods=["POST"])
@permission_required(CustomerPerm.DELETE)
def delete_view(cliente_id: int):
    """Hard-delete di un cliente (solo admin)."""
    # Verifica che l'utente sia admin (trial users non possono cancellare)
    if not current_user.is_admin or current_user.is_trial:
        abort(403, "Solo gli amministratori possono eliminare i clienti")
    
    # Elimina definitivamente il cliente (hard delete)
    delete_cliente(g.cliente, current_user, soft=False)  # type: ignore[arg-type]
    return jsonify({"success": True, "message": "Cliente eliminato definitivamente."}), HTTPStatus.OK

# --------------------------------------------------------------------------- #
#  IN-PLACE FIELD UPDATE (AJAX)                                               #
# --------------------------------------------------------------------------- #
@customers_bp.route("/<int:cliente_id>/field", methods=["PATCH"])
@permission_required(CustomerPerm.EDIT)
def update_single_field(cliente_id: int):
    """
    Aggiorna un singolo campo del cliente via JSON:
        {\"field\": \"nome_cognome\", \"value\": \"Mario Rossi\"}
    """
    payload: Dict[str, Any] = request.get_json(force=True, silent=False) or {}

    field = payload.get("field")
    value = payload.get("value")

    if not field:
        raise BadRequest("Payload must include 'field'.")
    if not hasattr(Cliente, field):
        raise BadRequest(f"Campo non valido: {field!r}")

    cliente: Cliente = customers_repo.get_one(cliente_id)

    # Validazione parziale Marshmallow
    errors = ClienteSchema().validate({field: value}, partial=True)
    if errors:
        raise BadRequest(errors)

    try:
        update_cliente(cliente, {field: value}, current_user)
        db.session.commit()
    except Exception as exc:  # pragma: no cover
        db.session.rollback()
        logger.exception("Errore update_single_field")
        return jsonify({"ok": False, "error": str(exc)}), HTTPStatus.BAD_REQUEST

    return jsonify({"ok": True, "value": getattr(cliente, field)}), HTTPStatus.OK

@customers_bp.route("/<int:cliente_id>/update", methods=["POST", "OPTIONS"])
def update_multiple_fields(cliente_id: int):
    """
    Aggiorna più campi del cliente via JSON (per form editabili).
    Accetta un oggetto JSON con i campi da aggiornare.
    """
    # Handle OPTIONS request for CORS
    if request.method == "OPTIONS":
        return "", HTTPStatus.NO_CONTENT
    
    # Verifica che l'utente sia autenticato
    if not current_user.is_authenticated:
        logger.warning(f"Accesso negato per utente non autenticato: {current_user}")
        return jsonify({"error": "Devi essere autenticato per accedere"}), HTTPStatus.FORBIDDEN
    
    # Debug logging
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request headers: {dict(request.headers)}")
    logger.info(f"Request content type: {request.content_type}")
    logger.info(f"Request data: {request.data}")
    
    # Try to get JSON payload
    try:
        payload: Dict[str, Any] = request.get_json(force=True) or {}
        logger.info(f"Parsed payload: {payload}")
        
        # Debug: Log tutti i campi stato ricevuti
        for key in payload:
            if 'stato' in key.lower():
                logger.info(f"Campo stato ricevuto - {key}: {payload[key]} (tipo: {type(payload[key])})")
                
    except Exception as e:
        logger.error(f"Errore parsing JSON: {e}")
        logger.error(f"Raw data: {request.data}")
        return jsonify({"error": f"Errore nel parsing dei dati: {str(e)}"}), HTTPStatus.BAD_REQUEST
    
    if not payload:
        logger.warning("Payload vuoto ricevuto")
        return jsonify({"error": "Nessun dato da aggiornare"}), HTTPStatus.BAD_REQUEST
    
    # Usa query diretta invece di repository per evitare NotFound exception
    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).first()
    if not cliente:
        return jsonify({"error": f"Cliente {cliente_id} non trovato"}), HTTPStatus.NOT_FOUND
    
    # Gestione campi multipli (professionisti)
    multi_fields = {}
    
    # Estrai i campi multipli dal payload
    # IMPORTANTE: Aggiorniamo solo se il campo è presente nel payload
    # Se non è presente, le relazioni esistenti vengono preservate
    if 'nutrizionisti_ids' in payload:
        ids = payload.pop('nutrizionisti_ids')
        # Gestiamo anche array vuoti per permettere la rimozione esplicita
        if ids is not None:  # Accetta sia array vuoti che array con valori
            if ids:
                multi_fields['nutrizionisti'] = [int(id) for id in ids if id]
            else:
                multi_fields['nutrizionisti'] = []  # Array vuoto per rimuovere tutti
    
    if 'coaches_ids' in payload:
        ids = payload.pop('coaches_ids')
        if ids is not None:  # Accetta sia array vuoti che array con valori
            if ids:
                multi_fields['coaches'] = [int(id) for id in ids if id]
            else:
                multi_fields['coaches'] = []  # Array vuoto per rimuovere tutti
    
    if 'psicologi_ids' in payload:
        ids = payload.pop('psicologi_ids')
        if ids is not None:  # Accetta sia array vuoti che array con valori
            if ids:
                multi_fields['psicologi'] = [int(id) for id in ids if id]
            else:
                multi_fields['psicologi'] = []  # Array vuoto per rimuovere tutti
    
    if 'consulenti_ids' in payload:
        ids = payload.pop('consulenti_ids')
        if ids is not None:  # Accetta sia array vuoti che array con valori
            if ids:
                multi_fields['consulenti'] = [int(id) for id in ids if id]
            else:
                multi_fields['consulenti'] = []  # Array vuoto per rimuovere tutti
    
    # Filtra solo i campi validi del modello
    valid_fields = {}
    for field, value in payload.items():
        if hasattr(Cliente, field):
            # Gestione campi booleani (checkbox)
            if isinstance(value, str) and value in ['true', 'false']:
                value = value == 'true'
            # Gestione campi vuoti
            elif value == '' or value is None:
                value = None
            # Gestione campi FK per professionisti (conversione da stringa a intero)
            elif field in ['nutrizionista_id', 'coach_id', 'psicologa_id', 'consulente_alimentare_id', 'health_manager_id']:
                if value:
                    try:
                        value = int(value)
                    except (ValueError, TypeError):
                        logger.warning(f"Impossibile convertire ID per campo {field}: {value}")
                        value = None
                else:
                    value = None
            # Gestione campi Integer (es. recensione_stelle, durata_*_giorni)
            elif field in ['recensione_stelle', 'sedute_psicologia_comprate', 'sedute_psicologia_svolte',
                           'durata_programma_giorni', 'durata_nutrizione_giorni', 'durata_coach_giorni', 'durata_psicologia_giorni']:
                if value:
                    try:
                        value = int(value)
                    except (ValueError, TypeError):
                        logger.warning(f"Impossibile convertire valore numerico per campo {field}: {value}")
                        value = None
                else:
                    value = None
            # Gestione date (convert string to date object)
            elif field.startswith('data_') or field.endswith('_dal') or field.endswith('_il') or field.endswith('_date'):
                if value:
                    try:
                        from datetime import datetime
                        value = datetime.strptime(value, '%Y-%m-%d').date()
                    except (ValueError, TypeError):
                        logger.warning(f"Impossibile convertire data per campo {field}: {value}")
                        value = None
                else:
                    value = None
            valid_fields[field] = value
    
    # Calcolo automatico della Data Rinnovo se ci sono data_inizio_abbonamento e durata_programma_giorni
    if 'data_inizio_abbonamento' in valid_fields and 'durata_programma_giorni' in valid_fields:
        data_inizio = valid_fields.get('data_inizio_abbonamento')
        durata = valid_fields.get('durata_programma_giorni')
        
        if data_inizio and durata:
            try:
                from datetime import timedelta
                # Se durata è una stringa, convertila in intero
                if isinstance(durata, str):
                    durata = int(durata)
                
                # Calcola la data di rinnovo
                data_rinnovo_calcolata = data_inizio + timedelta(days=durata)
                valid_fields['data_rinnovo'] = data_rinnovo_calcolata
                logger.info(f"Data Rinnovo calcolata automaticamente: {data_inizio} + {durata} giorni = {data_rinnovo_calcolata}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Impossibile calcolare data_rinnovo: {e}")

    # Ricalcolo automatico scadenze per-servizio (inizio + durata)
    _servizio_map = {
        'nutrizione': ('data_inizio_nutrizione', 'durata_nutrizione_giorni', 'data_scadenza_nutrizione'),
        'coach':      ('data_inizio_coach',      'durata_coach_giorni',      'data_scadenza_coach'),
        'psicologia': ('data_inizio_psicologia',  'durata_psicologia_giorni', 'data_scadenza_psicologia'),
    }
    for servizio, (inizio_field, durata_field, scadenza_field) in _servizio_map.items():
        if inizio_field in valid_fields or durata_field in valid_fields:
            data_inizio = valid_fields.get(inizio_field) or (getattr(cliente, inizio_field, None) if inizio_field not in valid_fields else None)
            durata = valid_fields.get(durata_field) or (getattr(cliente, durata_field, None) if durata_field not in valid_fields else None)
            if data_inizio and durata:
                try:
                    from datetime import timedelta
                    if isinstance(durata, str):
                        durata = int(durata)
                    scadenza_calcolata = data_inizio + timedelta(days=durata)
                    valid_fields[scadenza_field] = scadenza_calcolata
                    logger.info(f"Scadenza {servizio} calcolata: {data_inizio} + {durata}gg = {scadenza_calcolata}")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Impossibile calcolare scadenza {servizio}: {e}")

    # Se non ci sono campi validi ma ci sono professionisti multipli da aggiornare, è ok
    if not valid_fields and not multi_fields:
        return jsonify({"error": "Nessun campo valido da aggiornare"}), HTTPStatus.BAD_REQUEST
    
    # Import degli enum necessari
    from corposostenibile.models import (
        TeamEnum, PagamentoEnum, GiornoEnum, StatoClienteEnum,
        CheckSaltatiEnum, LuogoAllenEnum, FiguraRifEnum,
        TrasformazioneEnum, TipologiaClienteEnum
    )
    
    # Mapping dei campi agli enum
    enum_fields = {
        'di_team': TeamEnum,
        'modalita_pagamento': PagamentoEnum,
        'check_day': GiornoEnum,
        'stato_cliente': StatoClienteEnum,
        'stato_cliente_chat': StatoClienteEnum,
        'stato_cliente_sedute_psico': StatoClienteEnum,
        'stato_psicologia': StatoClienteEnum,
        'stato_nutrizione': StatoClienteEnum,
        'stato_coach': StatoClienteEnum,
        'stato_cliente_chat_coaching': StatoClienteEnum,
        'stato_cliente_chat_nutrizione': StatoClienteEnum,
        'stato_cliente_chat_psicologia': StatoClienteEnum,
        'check_saltati': CheckSaltatiEnum,
        'luogo_di_allenamento': LuogoAllenEnum,
        'figura_di_riferimento': FiguraRifEnum,
        'trasformazione': TrasformazioneEnum,
        'tipologia_cliente': TipologiaClienteEnum,
    }
    
    # Mappatura per vecchi valori stato_cliente
    stato_cliente_mapping = {
        'cliente': 'attivo',
        'ex_cliente': 'stop',
        'ex cliente': 'stop',  # Gestisce anche con spazio
        'ex-cliente': 'stop',  # Gestisce anche con trattino
        'acconto': 'stop',
        'ghosting': 'ghost',
        'inattivo': 'stop',
        'sospeso': 'pausa',
        'insoluto': 'stop',
        'freeze': 'pausa',
    }
    
    try:
        # Process enum fields before updating
        processed_fields = {}
        for field, value in valid_fields.items():
            # Gestione enum
            if field in enum_fields and value is not None:
                # Applica mappatura per campi stato_cliente e varianti
                stato_fields = ['stato_cliente', 'stato_cliente_chat', 'stato_cliente_sedute_psico',
                               'stato_psicologia', 'stato_nutrizione', 'stato_coach',
                               'stato_cliente_chat_coaching', 'stato_cliente_chat_nutrizione', 'stato_cliente_chat_psicologia']
                if field in stato_fields:
                    original_value = value
                    # Converti in stringa e pulisci
                    if value:
                        value = str(value).strip().lower()
                    value = stato_cliente_mapping.get(value, value)
                    if original_value != value:
                        logger.info(f"Mappatura {field}: {original_value} -> {value}")
                try:
                    value = enum_fields[field](value)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Valore enum non valido per {field}: {value}. Errore: {e}")
                    # Se è un campo stato, proviamo con 'stop' come fallback
                    if field in stato_fields:
                        try:
                            # Prova prima con 'attivo' come default sicuro
                            value = enum_fields[field]('attivo')
                            logger.info(f"Utilizzato fallback 'attivo' per {field} (valore originale: {valid_fields[field]})")
                        except:
                            logger.error(f"Impossibile impostare anche il fallback per {field}")
                            continue
                    else:
                        continue
            processed_fields[field] = value
        
        # Log dei campi processati prima dell'update
        for field, value in processed_fields.items():
            if 'stato' in field.lower():
                logger.info(f"Campo stato processato - {field}: {value} (tipo: {type(value)})")
        
        # Use the service function update_cliente which handles ActivityLog
        # Passa multi_fields per gestire le relazioni many-to-many
        update_cliente(cliente, processed_fields, current_user, multi_fields=multi_fields)
        db.session.commit()
        
        logger.info(f"Cliente {cliente_id} aggiornato con successo da {current_user.id}")
        return jsonify({"ok": True, "message": "Dati salvati con successo"}), HTTPStatus.OK
    except Exception as exc:
        db.session.rollback()
        logger.exception(f"Errore update_multiple_fields per cliente {cliente_id}: {exc}")
        return jsonify({"error": f"Errore durante il salvataggio: {str(exc)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

# --------------------------------------------------------------------------- #
#  FREEZE MANAGEMENT                                                          #
# --------------------------------------------------------------------------- #
@customers_bp.route("/<int:cliente_id>/freeze", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def freeze_cliente_route(cliente_id: int):
    """
    Mette un cliente in stato FREEZE.
    Solo Health Manager (dept_id=13) o admin possono eseguire questa azione.
    """
    from corposostenibile.blueprints.customers.services import freeze_cliente

    # Ottieni i dati dal form
    data = request.get_json() if request.is_json else request.form
    reason = data.get('freeze_reason', '').strip() if data else None

    result = freeze_cliente(cliente_id, current_user, reason)

    if result["status"] == "success":
        return jsonify(result), HTTPStatus.OK
    elif result["status"] == "warning":
        return jsonify(result), HTTPStatus.OK  # Already frozen, not an error
    else:
        return jsonify(result), HTTPStatus.BAD_REQUEST


@customers_bp.route("/<int:cliente_id>/unfreeze", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def unfreeze_cliente_route(cliente_id: int):
    """
    Rimuove un cliente dallo stato FREEZE.
    Solo Health Manager (dept_id=13) o admin possono eseguire questa azione.
    """
    from corposostenibile.blueprints.customers.services import unfreeze_cliente

    # Ottieni i dati dal form
    data = request.get_json() if request.is_json else request.form
    resolution = data.get('freeze_resolution', '').strip() if data else None

    result = unfreeze_cliente(cliente_id, current_user, resolution)

    if result["status"] == "success":
        return jsonify(result), HTTPStatus.OK
    elif result["status"] == "warning":
        return jsonify(result), HTTPStatus.OK  # Already unfrozen, not an error
    else:
        return jsonify(result), HTTPStatus.BAD_REQUEST


@customers_bp.route("/<int:cliente_id>/freeze-history", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def get_freeze_history(cliente_id: int):
    """
    Restituisce lo storico freeze del cliente.
    """
    from corposostenibile.models import ClienteFreezeHistory

    history = db.session.query(ClienteFreezeHistory).filter_by(
        cliente_id=cliente_id
    ).order_by(ClienteFreezeHistory.freeze_date.desc()).all()

    data = []
    for h in history:
        data.append({
            'id': h.id,
            'freeze_date': h.freeze_date.strftime('%d/%m/%Y %H:%M') if h.freeze_date else None,
            'freeze_reason': h.freeze_reason,
            'frozen_by': h.frozen_by.full_name if h.frozen_by else 'N/A',
            'unfreeze_date': h.unfreeze_date.strftime('%d/%m/%Y %H:%M') if h.unfreeze_date else None,
            'unfreeze_resolution': h.unfreeze_resolution,
            'unfrozen_by': h.unfrozen_by.full_name if h.unfrozen_by else None,
            'is_active': h.is_active
        })

    return jsonify({'history': data}), HTTPStatus.OK


# --------------------------------------------------------------------------- #
#  GESTIONE STORICO PROFESSIONISTI                                            #
# --------------------------------------------------------------------------- #

@customers_bp.route("/<int:cliente_id>/professionisti/assign", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def assign_professionista(cliente_id: int):
    """
    Assegna un professionista al cliente e registra l'azione nello storico.
    """
    from corposostenibile.models import ClienteProfessionistaHistory
    from datetime import datetime as dt

    payload = request.get_json(force=True) or {}

    # Valida campi richiesti
    required_fields = ['tipo_professionista', 'user_id', 'data_dal', 'motivazione_aggiunta']
    for field in required_fields:
        if field not in payload:
            return jsonify({"error": f"Campo {field} obbligatorio"}), HTTPStatus.BAD_REQUEST

    # Verifica che il cliente esista
    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).first()
    if not cliente:
        return jsonify({"error": f"Cliente {cliente_id} non trovato"}), HTTPStatus.NOT_FOUND

    # Converti data_dal da stringa a date
    try:
        data_dal = dt.strptime(payload['data_dal'], '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return jsonify({"error": "Formato data non valido. Usa YYYY-MM-DD"}), HTTPStatus.BAD_REQUEST

    # Crea record storico
    history = ClienteProfessionistaHistory(
        cliente_id=cliente_id,
        user_id=payload['user_id'],
        tipo_professionista=payload['tipo_professionista'],
        data_dal=data_dal,
        motivazione_aggiunta=payload['motivazione_aggiunta'],
        assegnato_da_id=current_user.id,
        is_active=True
    )

    db.session.add(history)

    # IMPORTANTE: Aggiungi il professionista alle relazioni del cliente
    user_id = payload['user_id']
    tipo = payload['tipo_professionista']
    professionista = db.session.query(User).get(user_id)

    if professionista:
        if tipo == 'nutrizionista' and professionista not in cliente.nutrizionisti_multipli:
            cliente.nutrizionisti_multipli.append(professionista)
        elif tipo == 'coach' and professionista not in cliente.coaches_multipli:
            cliente.coaches_multipli.append(professionista)
        elif tipo == 'psicologa' and professionista not in cliente.psicologi_multipli:
            cliente.psicologi_multipli.append(professionista)
        elif tipo == 'consulente' and professionista not in cliente.consulenti_multipli:
            cliente.consulenti_multipli.append(professionista)
        elif tipo == 'health_manager':
            cliente.health_manager_id = user_id

    db.session.commit()

    return jsonify({
        "ok": True,
        "message": "Professionista assegnato con successo",
        "history_id": history.id
    }), HTTPStatus.OK


@customers_bp.route("/<int:cliente_id>/professionisti/<int:history_id>/interrupt", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def interrupt_professionista(cliente_id: int, history_id: int):
    """
    Interrompe un'assegnazione di professionista e registra la motivazione.
    """
    from corposostenibile.models import ClienteProfessionistaHistory
    from datetime import datetime as dt, date

    payload = request.get_json(force=True) or {}

    # Valida campo obbligatorio
    if 'motivazione_interruzione' not in payload:
        return jsonify({"error": "Campo motivazione_interruzione obbligatorio"}), HTTPStatus.BAD_REQUEST

    # Recupera il record di storico
    history = db.session.query(ClienteProfessionistaHistory).filter_by(
        id=history_id,
        cliente_id=cliente_id
    ).first()

    if not history:
        return jsonify({"error": "Assegnazione non trovata"}), HTTPStatus.NOT_FOUND

    if not history.is_active:
        return jsonify({"error": "Assegnazione già interrotta"}), HTTPStatus.BAD_REQUEST

    # Gestione data_al: usa quella fornita o oggi
    if 'data_al' in payload and payload['data_al']:
        try:
            data_al = dt.strptime(payload['data_al'], '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return jsonify({"error": "Formato data non valido. Usa YYYY-MM-DD"}), HTTPStatus.BAD_REQUEST
    else:
        data_al = date.today()

    # Recupera il cliente
    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).first()
    if not cliente:
        return jsonify({"error": "Cliente non trovato"}), HTTPStatus.NOT_FOUND

    # Aggiorna il record
    history.data_al = data_al
    history.motivazione_interruzione = payload['motivazione_interruzione']
    history.interrotto_da_id = current_user.id
    history.is_active = False

    # IMPORTANTE: Rimuovi il professionista dalle relazioni del cliente
    # Pulisci sia la relazione M2M sia la FK singola legacy
    professionista = history.professionista
    tipo = history.tipo_professionista

    if tipo == 'nutrizionista':
        if professionista in cliente.nutrizionisti_multipli:
            cliente.nutrizionisti_multipli.remove(professionista)
        if cliente.nutrizionista_id == professionista.id:
            cliente.nutrizionista_id = None
    elif tipo == 'coach':
        if professionista in cliente.coaches_multipli:
            cliente.coaches_multipli.remove(professionista)
        if cliente.coach_id == professionista.id:
            cliente.coach_id = None
    elif tipo == 'psicologa':
        if professionista in cliente.psicologi_multipli:
            cliente.psicologi_multipli.remove(professionista)
        if cliente.psicologa_id == professionista.id:
            cliente.psicologa_id = None
    elif tipo == 'consulente':
        if professionista in cliente.consulenti_multipli:
            cliente.consulenti_multipli.remove(professionista)
        if cliente.consulente_alimentare_id == professionista.id:
            cliente.consulente_alimentare_id = None
    elif tipo == 'health_manager' and cliente.health_manager_id == professionista.id:
        cliente.health_manager_id = None

    db.session.commit()

    return jsonify({
        "ok": True,
        "message": "Assegnazione interrotta con successo"
    }), HTTPStatus.OK


@customers_bp.route("/<int:cliente_id>/professionisti/legacy/interrupt", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def interrupt_professionista_legacy(cliente_id: int):
    """
    Interrompe un professionista legacy (senza storico) creando prima il record storico.
    """
    from corposostenibile.models import ClienteProfessionistaHistory
    from datetime import datetime as dt, date

    payload = request.get_json(force=True) or {}

    # Valida campi obbligatori
    required_fields = ['user_id', 'tipo_professionista', 'motivazione_interruzione']
    for field in required_fields:
        if field not in payload:
            return jsonify({"error": f"Campo {field} obbligatorio"}), HTTPStatus.BAD_REQUEST

    # Verifica che il cliente esista
    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).first()
    if not cliente:
        return jsonify({"error": f"Cliente {cliente_id} non trovato"}), HTTPStatus.NOT_FOUND

    # Gestione data_al: usa quella fornita o oggi
    if 'data_al' in payload and payload['data_al']:
        try:
            data_al = dt.strptime(payload['data_al'], '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return jsonify({"error": "Formato data non valido. Usa YYYY-MM-DD"}), HTTPStatus.BAD_REQUEST
    else:
        data_al = date.today()

    # Crea record storico già interrotto (per professionista legacy)
    # Non abbiamo data_dal precisa, quindi la impostiamo a None o a oggi
    history = ClienteProfessionistaHistory(
        cliente_id=cliente_id,
        user_id=payload['user_id'],
        tipo_professionista=payload['tipo_professionista'],
        data_dal=data_al,  # Usiamo la data di interruzione anche come data inizio
        motivazione_aggiunta='Assegnazione precedente (storico creato durante interruzione)',
        assegnato_da_id=current_user.id,
        data_al=data_al,
        motivazione_interruzione=payload['motivazione_interruzione'],
        interrotto_da_id=current_user.id,
        is_active=False  # Già interrotto
    )

    db.session.add(history)

    # IMPORTANTE: Rimuovi il professionista dalle relazioni del cliente
    # Pulisci sia la relazione M2M sia la FK singola legacy
    user_id = payload['user_id']
    tipo = payload['tipo_professionista']
    professionista = db.session.query(User).get(user_id)

    if professionista:
        if tipo == 'nutrizionista':
            if professionista in cliente.nutrizionisti_multipli:
                cliente.nutrizionisti_multipli.remove(professionista)
            if cliente.nutrizionista_id == user_id:
                cliente.nutrizionista_id = None
        elif tipo == 'coach':
            if professionista in cliente.coaches_multipli:
                cliente.coaches_multipli.remove(professionista)
            if cliente.coach_id == user_id:
                cliente.coach_id = None
        elif tipo == 'psicologa':
            if professionista in cliente.psicologi_multipli:
                cliente.psicologi_multipli.remove(professionista)
            if cliente.psicologa_id == user_id:
                cliente.psicologa_id = None
        elif tipo == 'consulente':
            if professionista in cliente.consulenti_multipli:
                cliente.consulenti_multipli.remove(professionista)
            if cliente.consulente_alimentare_id == user_id:
                cliente.consulente_alimentare_id = None
        elif tipo == 'health_manager' and cliente.health_manager_id == user_id:
            cliente.health_manager_id = None

    db.session.commit()

    return jsonify({
        "ok": True,
        "message": "Assegnazione legacy interrotta con successo"
    }), HTTPStatus.OK


@customers_bp.route("/<int:cliente_id>/professionisti/history", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def get_professionisti_history(cliente_id: int):
    """
    Restituisce lo storico completo delle assegnazioni professionisti per un cliente.
    Include sia le assegnazioni con storico che quelle legacy (senza storico).
    """
    from corposostenibile.models import ClienteProfessionistaHistory

    # Verifica che il cliente esista
    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).first()
    if not cliente:
        return jsonify({"error": f"Cliente {cliente_id} non trovato"}), HTTPStatus.NOT_FOUND

    # Recupera storico con tracking
    history_records = db.session.query(ClienteProfessionistaHistory).filter_by(
        cliente_id=cliente_id
    ).order_by(ClienteProfessionistaHistory.data_dal.desc()).all()

    data = []
    for h in history_records:
        data.append({
            'id': h.id,
            'tipo_professionista': h.tipo_professionista,
            'professionista_nome': h.professionista.full_name if h.professionista else 'N/A',
            'professionista_id': h.user_id,
            'data_dal': h.data_dal.strftime('%d/%m/%Y') if h.data_dal else None,
            'data_al': h.data_al.strftime('%d/%m/%Y') if h.data_al else None,
            'motivazione_aggiunta': h.motivazione_aggiunta,
            'motivazione_interruzione': h.motivazione_interruzione,
            'assegnato_da': h.assegnato_da.full_name if h.assegnato_da else 'N/A',
            'interrotto_da': h.interrotto_da.full_name if h.interrotto_da else None,
            'is_active': h.is_active,
            'has_history': True  # Indica che questo ha tracking completo
        })

    # Aggiungi professionisti attualmente assegnati SENZA storico (legacy)
    legacy_professionisti = []

    # Nutrizionisti
    for nutri in cliente.nutrizionisti_multipli:
        # Verifica se c'è già nello storico
        if not any(h.user_id == nutri.id and h.tipo_professionista == 'nutrizionista' and h.is_active for h in history_records):
            legacy_professionisti.append({
                'id': None,  # Nessun ID storico
                'tipo_professionista': 'nutrizionista',
                'professionista_nome': nutri.full_name or nutri.email,
                'professionista_id': nutri.id,
                'data_dal': None,
                'data_al': None,
                'motivazione_aggiunta': 'Assegnazione precedente (senza storico)',
                'motivazione_interruzione': None,
                'assegnato_da': 'N/A',
                'interrotto_da': None,
                'is_active': True,
                'has_history': False  # Legacy senza tracking
            })

    # Coach
    for coach in cliente.coaches_multipli:
        if not any(h.user_id == coach.id and h.tipo_professionista == 'coach' and h.is_active for h in history_records):
            legacy_professionisti.append({
                'id': None,
                'tipo_professionista': 'coach',
                'professionista_nome': coach.full_name or coach.email,
                'professionista_id': coach.id,
                'data_dal': None,
                'data_al': None,
                'motivazione_aggiunta': 'Assegnazione precedente (senza storico)',
                'motivazione_interruzione': None,
                'assegnato_da': 'N/A',
                'interrotto_da': None,
                'is_active': True,
                'has_history': False
            })

    # Psicologi
    for psi in cliente.psicologi_multipli:
        if not any(h.user_id == psi.id and h.tipo_professionista == 'psicologa' and h.is_active for h in history_records):
            legacy_professionisti.append({
                'id': None,
                'tipo_professionista': 'psicologa',
                'professionista_nome': psi.full_name or psi.email,
                'professionista_id': psi.id,
                'data_dal': None,
                'data_al': None,
                'motivazione_aggiunta': 'Assegnazione precedente (senza storico)',
                'motivazione_interruzione': None,
                'assegnato_da': 'N/A',
                'interrotto_da': None,
                'is_active': True,
                'has_history': False
            })

    # Consulenti Alimentari
    for consulente in cliente.consulenti_multipli:
        if not any(h.user_id == consulente.id and h.tipo_professionista == 'consulente' and h.is_active for h in history_records):
            legacy_professionisti.append({
                'id': None,
                'tipo_professionista': 'consulente',
                'professionista_nome': consulente.full_name or consulente.email,
                'professionista_id': consulente.id,
                'data_dal': None,
                'data_al': None,
                'motivazione_aggiunta': 'Assegnazione precedente (senza storico)',
                'motivazione_interruzione': None,
                'assegnato_da': 'N/A',
                'interrotto_da': None,
                'is_active': True,
                'has_history': False
            })

    # Health Manager (singolo)
    if cliente.health_manager_user:
        if not any(h.user_id == cliente.health_manager_user.id and h.tipo_professionista == 'health_manager' and h.is_active for h in history_records):
            legacy_professionisti.append({
                'id': None,
                'tipo_professionista': 'health_manager',
                'professionista_nome': cliente.health_manager_user.full_name or cliente.health_manager_user.email,
                'professionista_id': cliente.health_manager_user.id,
                'data_dal': None,
                'data_al': None,
                'motivazione_aggiunta': 'Assegnazione precedente (senza storico)',
                'motivazione_interruzione': None,
                'assegnato_da': 'N/A',
                'interrotto_da': None,
                'is_active': True,
                'has_history': False
            })

    # Unisci storico + legacy
    all_history = data + legacy_professionisti

    return jsonify({'history': all_history}), HTTPStatus.OK


@customers_bp.route("/<int:cliente_id>/evaluations/<string:service_type>", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def get_service_evaluations(cliente_id: int, service_type: str):
    """
    Recupera l'andamento delle valutazioni del cliente per un servizio specifico.
    Include dati da Check Settimanali (vecchi) e Check 2.0 (WeeklyCheckResponse).

    Args:
        cliente_id: ID del cliente
        service_type: Tipo servizio ('nutrizione', 'coaching', 'psicologia')

    Returns:
        JSON con lista valutazioni ordinate per data
    """
    from corposostenibile.models import WeeklyCheckResponse, WeeklyCheck

    cliente = db.session.get(Cliente, cliente_id)
    if not cliente:
        return jsonify({'error': 'Cliente non trovato'}), HTTPStatus.NOT_FOUND

    # Valida service_type
    valid_services = ['nutrizione', 'coaching', 'psicologia']
    if service_type not in valid_services:
        return jsonify({'error': f'Servizio non valido. Valori accettati: {", ".join(valid_services)}'}), HTTPStatus.BAD_REQUEST

    # Mappatura service_type -> campo valutazione in WeeklyCheckResponse
    rating_field_map = {
        'nutrizione': 'nutritionist_rating',
        'coaching': 'coach_rating',
        'psicologia': 'psychologist_rating'
    }

    feedback_field_map = {
        'nutrizione': 'nutritionist_feedback',
        'coaching': 'coach_feedback',
        'psicologia': 'psychologist_feedback'
    }

    rating_field = rating_field_map[service_type]
    feedback_field = feedback_field_map[service_type]

    # Recupera valutazioni dai Check 2.0 (WeeklyCheckResponse)
    weekly_checks = db.session.query(WeeklyCheck).filter_by(cliente_id=cliente_id).all()
    weekly_check_ids = [wc.id for wc in weekly_checks]

    evaluations = []

    if weekly_check_ids:
        # Query per recuperare le risposte con valutazione per questo servizio
        responses = db.session.query(WeeklyCheckResponse).filter(
            WeeklyCheckResponse.weekly_check_id.in_(weekly_check_ids),
            getattr(WeeklyCheckResponse, rating_field).isnot(None)
        ).order_by(WeeklyCheckResponse.submit_date.asc()).all()

        for response in responses:
            rating = getattr(response, rating_field)
            feedback = getattr(response, feedback_field)

            evaluations.append({
                'date': response.submit_date.isoformat() if response.submit_date else None,
                'check_type': 'Check 2.0',
                'rating': rating,
                'notes': feedback if feedback else None
            })

    # TODO: Aggiungi anche valutazioni da ClientCheckResponse (check vecchi) se necessario
    # Per ora includiamo solo i Check 2.0

    return jsonify({
        'evaluations': evaluations,
        'service_type': service_type,
        'total_count': len(evaluations)
    }), HTTPStatus.OK


# --------------------------------------------------------------------------- #
#  CREA LEAD PER CHECK (Clienti senza Lead originale)                         #
# --------------------------------------------------------------------------- #
@customers_bp.route("/<int:cliente_id>/create-lead-for-checks", methods=["POST"])
@permission_required(CustomerPerm.VIEW)
def create_lead_for_checks(cliente_id: int):
    """
    Crea una SalesLead retroattiva per un cliente esistente che non ha una lead associata.
    Questo permette al cliente di compilare i Check 1, 2, 3 anche se non proviene dal flusso lead standard.

    La lead viene creata con:
    - Dati anagrafici copiati dal cliente
    - Status 'CONVERTED' (già convertito)
    - Link ai check 1, 2, 3 generati automaticamente
    """
    import secrets
    from corposostenibile.models import SalesLead, SalesFormLink, SalesFormConfig
    from corposostenibile.models import LeadStatusEnum

    cliente = db.session.get(Cliente, cliente_id)
    if not cliente:
        return jsonify({'success': False, 'error': 'Cliente non trovato'}), HTTPStatus.NOT_FOUND

    # Verifica che non abbia già una lead associata
    if cliente.original_lead:
        return jsonify({
            'success': False,
            'error': 'Il cliente ha già una lead associata',
            'lead_id': cliente.original_lead.id
        }), HTTPStatus.BAD_REQUEST

    try:
        # Genera codice unico per la lead
        lead_unique_code = f"RETRO-{cliente_id}-{secrets.token_hex(4).upper()}"

        # Estrai nome e cognome dal nome_cognome del cliente
        nome_parts = (cliente.nome_cognome or "").strip().split(" ", 1)
        first_name = nome_parts[0] if nome_parts else "N/D"
        last_name = nome_parts[1] if len(nome_parts) > 1 else ""

        # Crea la SalesLead
        new_lead = SalesLead(
            first_name=first_name,
            last_name=last_name,
            email=cliente.mail or f"cliente_{cliente_id}@placeholder.local",
            phone=cliente.numero_telefono,
            birth_date=cliente.data_di_nascita,
            gender=cliente.genere,
            unique_code=lead_unique_code,
            status=LeadStatusEnum.CONVERTED,
            converted_to_client_id=cliente_id,
            converted_at=datetime.now(),
            converted_by=current_user.id,
            conversion_notes="Lead creata retroattivamente per permettere compilazione Check 1, 2, 3",
            form_responses={},
            sales_user_id=current_user.id,
        )
        db.session.add(new_lead)
        db.session.flush()  # Per ottenere l'ID

        # Recupera i config_id per i check (assumiamo ID 1, 2, 3 per check 1, 2, 3)
        check_configs = {
            1: SalesFormConfig.query.get(1),
            2: SalesFormConfig.query.get(2),
            3: SalesFormConfig.query.get(3)
        }

        # Crea i link per i check 1, 2, 3
        check_urls = {}
        for check_num in [1, 2, 3]:
            link_code = f"{lead_unique_code}-CHECK{check_num}"

            check_link = SalesFormLink(
                lead_id=new_lead.id,
                check_number=check_num,
                config_id=check_configs[check_num].id if check_configs[check_num] else check_num,
                unique_code=link_code,
                is_active=True,
            )
            db.session.add(check_link)
            check_urls[f'check{check_num}'] = url_for('welcome_form', unique_code=link_code, _external=True)

        db.session.commit()

        logger.info(f"Lead retroattiva #{new_lead.id} creata per cliente #{cliente_id} da utente #{current_user.id}")

        return jsonify({
            'success': True,
            'message': 'Lead creata con successo. Il cliente può ora compilare i Check 1, 2, 3.',
            'lead_id': new_lead.id,
            'check_urls': check_urls
        }), HTTPStatus.CREATED

    except Exception as e:
        db.session.rollback()
        logger.error(f"Errore nella creazione lead retroattiva per cliente #{cliente_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Errore nella creazione della lead: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR


# --------------------------------------------------------------------------- #
#  API REST v1                                                                #
# --------------------------------------------------------------------------- #
api_bp = Blueprint("customers_api_v1", __name__, url_prefix="/api/v1/customers")
csrf.exempt(api_bp)  # Exclude API blueprint from CSRF protection

cliente_schema = ClienteSchema()
clienti_schema = ClienteSchema(many=True)

# – JSON error handler ------------------------------------------------------ #
@api_bp.errorhandler(BadRequest)
@api_bp.errorhandler(NotFound)
@api_bp.errorhandler(Forbidden)
def _json_error(err):  # type: ignore[override]
    return (
        jsonify({"error": err.name, "description": err.description}),
        getattr(err, "code", HTTPStatus.BAD_REQUEST),
    )

# – ORIGINS API ------------------------------------------------------------- #
@api_bp.route("/origins", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_origins_list():
    origins = Origine.query.all()
    # Manual serialization since no schema yet
    return jsonify([{"id": o.id, "name": o.name, "active": o.active} for o in origins])

@api_bp.route("/origins", methods=["POST"])
@permission_required(CustomerPerm.MANAGE)
def api_origins_create():
    data = request.json
    if not data or not data.get("name"):
        return jsonify({"error": "Name required"}), 400
    
    # Check if exists
    existing = Origine.query.filter_by(name=data["name"]).first()
    if existing:
        return jsonify({"error": "Origin already exists"}), 400

    origin = Origine(name=data["name"], active=data.get("active", True))
    db.session.add(origin)
    db.session.commit()
    return jsonify({"id": origin.id, "name": origin.name, "active": origin.active}), 201

@api_bp.route("/origins/<int:origin_id>", methods=["PUT"])
@permission_required(CustomerPerm.MANAGE)
def api_origins_update(origin_id):
    origin = Origine.query.get_or_404(origin_id)
    data = request.json
    if "name" in data:
        origin.name = data["name"]
    if "active" in data:
        origin.active = data["active"]
    db.session.commit()
    return jsonify({"id": origin.id, "name": origin.name, "active": origin.active})

@api_bp.route("/origins/<int:origin_id>", methods=["DELETE"])
@permission_required(CustomerPerm.MANAGE)
def api_origins_delete(origin_id):
    origin = Origine.query.get_or_404(origin_id)
    db.session.delete(origin)
    db.session.commit()
    return jsonify({"success": True})

# – CRUD -------------------------------------------------------------------- #
@api_bp.route("/", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_list() -> Any:
    """Get list of customers with trial user access control."""
    # Trial user access check
    if current_user.is_authenticated and current_user.is_trial:
        if current_user.trial_stage < 2:
            # Stage 1: No access to customers list
            return jsonify({
                "data": [],
                "pagination": {"page": 1, "pages": 0, "total": 0},
                "message": "Accesso clienti non disponibile in Stage 1"
            })
    
    params = parse_filter_args(request.args)

    # Filtro per Influencer: vincola alle origini assegnate (M2M)
    if current_user.role == UserRoleEnum.influencer:
        origine_ids = [o.id for o in current_user.influencer_origins]
        if not origine_ids:
            return jsonify({
                "items": [],
                "pagination": {"page": 1, "pages": 0, "total": 0},
                "message": "Nessuna origine associata"
            })
        params = replace(params, origine_ids=origine_ids)

    # Apply trial user filter to query
    from corposostenibile.blueprints.customers.trial_integration import apply_trial_user_filter
    
    pagination = customers_repo.list(
        filters=params,
        order_by=request.args.get("order_by"),
        page=request.args.get("page", 1, type=int),
        per_page=request.args.get("per_page", 50, type=int),
        eager=True,
    )
    
    # Filter results for trial users (additional safety layer)
    if current_user.is_authenticated and current_user.is_trial and current_user.trial_stage == 2:
        # Stage 2: Only show assigned clients
        assigned_ids = {c.cliente_id for c in current_user.trial_assigned_clients}
        filtered_items = [item for item in pagination.items if item.cliente_id in assigned_ids]
        pagination.items = filtered_items
        pagination.total = len(filtered_items)
    
    result = {
        "data": clienti_schema.dump(pagination.items),
        "pagination": {
            "page": pagination.page,
            "pages": pagination.pages,
            "total": pagination.total,
        },
    }

    # Compute KPI aggregates for specialty views (coach, nutrizione, psicologia)
    view = request.args.get("view", "").lower()
    _VIEW_KPI_FIELDS = {
        "coach": ("stato_coach", "stato_cliente_chat_coaching"),
        "nutrizione": ("stato_nutrizione", "stato_cliente_chat_nutrizione"),
        "psicologia": ("stato_psicologia", "stato_cliente_chat_psicologia"),
    }
    if view in _VIEW_KPI_FIELDS:
        stato_field_name, chat_field_name = _VIEW_KPI_FIELDS[view]
        stato_col = getattr(Cliente, stato_field_name, None)
        chat_col = getattr(Cliente, chat_field_name, None)
        if stato_col is not None and chat_col is not None:
            # Build filtered (unpaginated) base query with same filters + RBAC
            kpi_qry = db.session.query(Cliente).filter(
                Cliente.show_in_clienti_lista.is_(True)
            )
            kpi_qry = apply_customer_filters(kpi_qry, params)
            kpi_qry = apply_role_filtering(kpi_qry)

            stato_rows = (
                kpi_qry.with_entities(stato_col, func.count(Cliente.cliente_id))
                .order_by(None)
                .group_by(stato_col)
                .all()
            )
            chat_rows = (
                kpi_qry.with_entities(chat_col, func.count(Cliente.cliente_id))
                .order_by(None)
                .group_by(chat_col)
                .all()
            )
            stato_counts = {
                (s.value if hasattr(s, "value") else str(s) if s else "null"): c
                for s, c in stato_rows
            }
            chat_counts = {
                (s.value if hasattr(s, "value") else str(s) if s else "null"): c
                for s, c in chat_rows
            }
            result["kpi"] = {
                "stato_attivo": stato_counts.get("attivo", 0),
                "stato_ghost": stato_counts.get("ghost", 0),
                "stato_pausa": stato_counts.get("pausa", 0),
                "stato_stop": stato_counts.get("stop", 0),
                "chat_attivo": chat_counts.get("attivo", 0),
                "chat_ghost": chat_counts.get("ghost", 0),
                "chat_pausa": chat_counts.get("pausa", 0),
                "chat_stop": chat_counts.get("stop", 0),
            }

    return jsonify(result)


@api_bp.route("/expiring", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_expiring() -> Any:
    """Clienti in scadenza filtrati per fascia temporale (30/60/90 giorni)."""
    from datetime import date, timedelta

    days = request.args.get("days", 30, type=int)
    if days not in (30, 60, 90):
        days = 30

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)
    q = (request.args.get("q") or "").strip()

    today = date.today()
    limit_date = today + timedelta(days=days)
    # Range: 30 = 0-30, 60 = 30-60, 90 = 60-90
    range_start = today if days == 30 else today + timedelta(days=days - 30)
    hm_filter = request.args.get("health_manager_id", type=int)

    query = apply_role_filtering(
        db.session.query(Cliente).filter(
            Cliente.show_in_clienti_lista.is_(True),
            Cliente.data_rinnovo.isnot(None),
            Cliente.data_rinnovo >= range_start,
            Cliente.data_rinnovo <= limit_date,
            Cliente.stato_cliente.in_(["attivo", "ghost", "pausa"]),
        )
    )

    if hm_filter:
        query = query.filter(Cliente.health_manager_id == hm_filter)

    if q:
        query = query.filter(Cliente.nome_cognome.ilike(f"%{q}%"))

    query = query.order_by(Cliente.data_rinnovo.asc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    data = []
    for c in pagination.items:
        giorni = (c.data_rinnovo - today).days if c.data_rinnovo else None
        data.append({
            "cliente_id": c.cliente_id,
            "nome_cognome": c.nome_cognome,
            "stato_cliente": c.stato_cliente.value if hasattr(c.stato_cliente, "value") else c.stato_cliente,
            "data_rinnovo": c.data_rinnovo.isoformat() if c.data_rinnovo else None,
            "giorni_rimanenti": giorni,
            "programma_attuale": c.programma_attuale or None,
            "health_manager_user": {
                "id": c.health_manager_user.id,
                "full_name": c.health_manager_user.full_name,
                "first_name": c.health_manager_user.first_name,
                "last_name": c.health_manager_user.last_name,
            } if c.health_manager_user else None,
            "nutrizionista_user": {
                "id": c.nutrizionista_user.id,
                "full_name": c.nutrizionista_user.full_name,
                "first_name": c.nutrizionista_user.first_name,
                "last_name": c.nutrizionista_user.last_name,
            } if c.nutrizionista_user else None,
            "coach_user": {
                "id": c.coach_user.id,
                "full_name": c.coach_user.full_name,
                "first_name": c.coach_user.first_name,
                "last_name": c.coach_user.last_name,
            } if c.coach_user else None,
            "psicologa_user": {
                "id": c.psicologa_user.id,
                "full_name": c.psicologa_user.full_name,
                "first_name": c.psicologa_user.first_name,
                "last_name": c.psicologa_user.last_name,
            } if c.psicologa_user else None,
        })

    # Conteggi per fascia
    count_base = apply_role_filtering(
        db.session.query(db.func.count(Cliente.cliente_id)).filter(
            Cliente.show_in_clienti_lista.is_(True),
            Cliente.data_rinnovo.isnot(None),
            Cliente.data_rinnovo >= today,
            Cliente.stato_cliente.in_(["attivo", "ghost", "pausa"]),
        )
    )
    count_30 = count_base.filter(Cliente.data_rinnovo >= today, Cliente.data_rinnovo <= today + timedelta(days=30)).scalar() or 0
    count_60 = count_base.filter(Cliente.data_rinnovo > today + timedelta(days=30), Cliente.data_rinnovo <= today + timedelta(days=60)).scalar() or 0
    count_90 = count_base.filter(Cliente.data_rinnovo > today + timedelta(days=60), Cliente.data_rinnovo <= today + timedelta(days=90)).scalar() or 0

    return jsonify({
        "data": data,
        "pagination": {
            "page": pagination.page,
            "pages": pagination.pages,
            "total": pagination.total,
        },
        "counts": {
            "30": count_30,
            "60": count_60,
            "90": count_90,
        },
    })


@api_bp.route("/unsatisfied", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_unsatisfied() -> Any:
    """Clienti insoddisfatti in base alla media voti weekly check."""
    from sqlalchemy import func as sa_func

    threshold = request.args.get("threshold", 8, type=int)
    if threshold not in (6, 7, 8):
        threshold = 8

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)
    q = (request.args.get("q") or "").strip()
    hm_filter = request.args.get("health_manager_id", type=int)

    # Subquery: media dei voti professionista + progresso per cliente
    # Prende solo le ultime 4 risposte (ultimo mese circa) per ciascun weekly check
    rating_cols = [
        WeeklyCheckResponse.nutritionist_rating,
        WeeklyCheckResponse.coach_rating,
        WeeklyCheckResponse.psychologist_rating,
        WeeklyCheckResponse.progress_rating,
    ]

    # Calcolo media: AVG di tutti i rating non-null tra professionisti + progresso
    avg_expr = sa_func.avg(
        sa_func.coalesce(WeeklyCheckResponse.nutritionist_rating, None)
    )

    # Subquery con join per ottenere cliente_id e media combinata
    from sqlalchemy import case, literal_column, and_

    # Calcoliamo la media di tutti i rating disponibili per response
    # (nutritionist + coach + psychologist + progress) / count_non_null
    subq = (
        db.session.query(
            WeeklyCheck.cliente_id.label("cliente_id"),
            sa_func.avg(
                (
                    sa_func.coalesce(WeeklyCheckResponse.nutritionist_rating.cast(db.Float), 0)
                    + sa_func.coalesce(WeeklyCheckResponse.coach_rating.cast(db.Float), 0)
                    + sa_func.coalesce(WeeklyCheckResponse.psychologist_rating.cast(db.Float), 0)
                    + sa_func.coalesce(WeeklyCheckResponse.progress_rating.cast(db.Float), 0)
                ) / sa_func.nullif(
                    (
                        case((WeeklyCheckResponse.nutritionist_rating.isnot(None), 1), else_=0)
                        + case((WeeklyCheckResponse.coach_rating.isnot(None), 1), else_=0)
                        + case((WeeklyCheckResponse.psychologist_rating.isnot(None), 1), else_=0)
                        + case((WeeklyCheckResponse.progress_rating.isnot(None), 1), else_=0)
                    ),
                    0,
                )
            ).label("avg_rating"),
            sa_func.avg(WeeklyCheckResponse.nutritionist_rating.cast(db.Float)).label("avg_nutrizione"),
            sa_func.avg(WeeklyCheckResponse.coach_rating.cast(db.Float)).label("avg_coach"),
            sa_func.avg(WeeklyCheckResponse.psychologist_rating.cast(db.Float)).label("avg_psicologia"),
            sa_func.avg(WeeklyCheckResponse.progress_rating.cast(db.Float)).label("avg_percorso"),
            sa_func.max(WeeklyCheckResponse.submit_date).label("last_check_date"),
            sa_func.count(WeeklyCheckResponse.id).label("total_responses"),
        )
        .join(WeeklyCheck, WeeklyCheckResponse.weekly_check_id == WeeklyCheck.id)
        .filter(
            # Almeno un rating deve essere compilato
            db.or_(
                WeeklyCheckResponse.nutritionist_rating.isnot(None),
                WeeklyCheckResponse.coach_rating.isnot(None),
                WeeklyCheckResponse.psychologist_rating.isnot(None),
                WeeklyCheckResponse.progress_rating.isnot(None),
            )
        )
        .group_by(WeeklyCheck.cliente_id)
        .subquery()
    )

    # Query principale: clienti con media sotto la soglia
    query = apply_role_filtering(
        db.session.query(
            Cliente, subq.c.avg_rating,
            subq.c.avg_nutrizione, subq.c.avg_coach, subq.c.avg_psicologia, subq.c.avg_percorso,
            subq.c.last_check_date, subq.c.total_responses,
        )
        .join(subq, Cliente.cliente_id == subq.c.cliente_id)
        .filter(
            Cliente.show_in_clienti_lista.is_(True),
            Cliente.stato_cliente.in_(["attivo", "ghost", "pausa"]),
            subq.c.avg_rating < threshold,
            *([subq.c.avg_rating >= threshold - 1] if threshold > 6 else []),
        )
    )

    if hm_filter:
        query = query.filter(Cliente.health_manager_id == hm_filter)

    if q:
        query = query.filter(Cliente.nome_cognome.ilike(f"%{q}%"))

    query = query.order_by(subq.c.avg_rating.asc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    data = []
    for row in pagination.items:
        c = row[0]
        avg_r = row[1]
        avg_n = row[2]
        avg_c = row[3]
        avg_p = row[4]
        avg_perc = row[5]
        last_date = row[6]
        total_resp = row[7]

        data.append({
            "cliente_id": c.cliente_id,
            "nome_cognome": c.nome_cognome,
            "stato_cliente": c.stato_cliente.value if hasattr(c.stato_cliente, "value") else c.stato_cliente,
            "avg_rating": round(float(avg_r), 1) if avg_r else None,
            "avg_nutrizione": round(float(avg_n), 1) if avg_n else None,
            "avg_coach": round(float(avg_c), 1) if avg_c else None,
            "avg_psicologia": round(float(avg_p), 1) if avg_p else None,
            "avg_percorso": round(float(avg_perc), 1) if avg_perc else None,
            "last_check_date": last_date.isoformat() if last_date else None,
            "total_responses": total_resp or 0,
            "health_manager_user": {
                "id": c.health_manager_user.id,
                "full_name": c.health_manager_user.full_name,
                "first_name": c.health_manager_user.first_name,
                "last_name": c.health_manager_user.last_name,
            } if c.health_manager_user else None,
            "nutrizionista_user": {
                "id": c.nutrizionista_user.id,
                "full_name": c.nutrizionista_user.full_name,
                "first_name": c.nutrizionista_user.first_name,
                "last_name": c.nutrizionista_user.last_name,
            } if c.nutrizionista_user else None,
            "coach_user": {
                "id": c.coach_user.id,
                "full_name": c.coach_user.full_name,
                "first_name": c.coach_user.first_name,
                "last_name": c.coach_user.last_name,
            } if c.coach_user else None,
            "psicologa_user": {
                "id": c.psicologa_user.id,
                "full_name": c.psicologa_user.full_name,
                "first_name": c.psicologa_user.first_name,
                "last_name": c.psicologa_user.last_name,
            } if c.psicologa_user else None,
        })

    # Conteggi per soglia
    count_base = (
        db.session.query(sa_func.count(sa_func.distinct(subq.c.cliente_id)))
        .select_from(Cliente)
        .join(subq, Cliente.cliente_id == subq.c.cliente_id)
        .filter(
            Cliente.show_in_clienti_lista.is_(True),
            Cliente.stato_cliente.in_(["attivo", "ghost", "pausa"]),
        )
    )
    count_base = apply_role_filtering(count_base)
    count_8 = count_base.filter(subq.c.avg_rating < 8, subq.c.avg_rating >= 7).scalar() or 0
    count_7 = count_base.filter(subq.c.avg_rating < 7, subq.c.avg_rating >= 6).scalar() or 0
    count_6 = count_base.filter(subq.c.avg_rating < 6).scalar() or 0

    return jsonify({
        "data": data,
        "pagination": {
            "page": pagination.page,
            "pages": pagination.pages,
            "total": pagination.total,
        },
        "counts": {
            "8": count_8,
            "7": count_7,
            "6": count_6,
        },
    })


def _require_cliente_scope_or_403(cliente_id: int) -> None:
    """
    Verifica che il cliente sia nel perimetro RBAC dell'utente corrente
    (admin=globale, TL=team, professionista=propri clienti).
    """
    scoped_query = apply_role_filtering(db.session.query(Cliente.cliente_id))
    if scoped_query.filter(Cliente.cliente_id == cliente_id).first() is None:
        abort(HTTPStatus.FORBIDDEN, description="Cliente fuori dal perimetro autorizzato.")


def _export_pdf_format_value(value: Any) -> str:
    if value is None:
        return "-"
    if hasattr(value, "value"):
        value = value.value
    if isinstance(value, bool):
        return "Si" if value else "No"
    if isinstance(value, (date, datetime)):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, (list, tuple, set)):
        if not value:
            return "-"
        return ", ".join(_export_pdf_format_value(item) for item in value)
    text = str(value).strip()
    return text or "-"


def _export_pdf_user_label(user: Any) -> str:
    if not user:
        return "-"
    full_name = getattr(user, "full_name", None)
    if full_name:
        return str(full_name)
    email = getattr(user, "email", None)
    if email:
        return str(email)
    user_id = getattr(user, "id", None)
    if user_id:
        return f"Utente #{user_id}"
    return "-"


def _append_export_section(story: list[Any], styles: Any, title: str, rows: list[tuple[str, Any]], col_widths: list[float]) -> None:
    from reportlab.lib import colors
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    story.append(Paragraph(title, styles["Heading2"]))
    data: list[list[Any]] = []
    for label, value in rows:
        rendered = _export_pdf_format_value(value)
        data.append([
            Paragraph(f"<b>{label}</b>", styles["Normal"]),
            Paragraph(rendered.replace("\n", "<br/>"), styles["Normal"]),
        ])

    if not data:
        data = [[Paragraph("<b>Info</b>", styles["Normal"]), Paragraph("Nessun dato disponibile", styles["Normal"])]]

    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    story.append(Spacer(1, 10))


@api_bp.route("/<int:cliente_id>/clinical-folder-export", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_clinical_folder_export_pdf(cliente_id: int):
    from io import BytesIO

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm, mm
    from reportlab.platypus import (
        BaseDocTemplate, Frame, PageBreak, PageTemplate, Paragraph,
        Spacer, Table, TableStyle, Image
    )
    from reportlab.pdfgen import canvas

    _require_cliente_scope_or_403(cliente_id)
    cliente = customers_repo.get_one(cliente_id, eager=True)

    # Import additional models needed for comprehensive export
    from corposostenibile.models import (
        ServiceAnamnesi,
        ServiceDiaryEntry,
        MinorCheckResponse,
        MinorCheck,
        DCACheckResponse,
        DCACheck,
        ClienteProfessionistaHistory,
        CustomerCareIntervention,
        CheckInIntervention,
        ClientCheckResponse,
        ClientCheckAssignment,
    )

    # Fetch all data needed for comprehensive PDF
    weekly_checks_count = (
        db.session.query(func.count(WeeklyCheck.id))
        .filter(WeeklyCheck.cliente_id == cliente_id)
        .scalar()
        or 0
    )
    weekly_responses = (
        db.session.query(WeeklyCheckResponse)
        .join(WeeklyCheck, WeeklyCheckResponse.weekly_check_id == WeeklyCheck.id)
        .filter(WeeklyCheck.cliente_id == cliente_id)
        .order_by(WeeklyCheckResponse.submit_date.desc())
        .all()
    )
    weekly_responses_count = len(weekly_responses)
    latest_check_response_date = (
        db.session.query(func.max(WeeklyCheckResponse.submit_date))
        .join(WeeklyCheck, WeeklyCheckResponse.weekly_check_id == WeeklyCheck.id)
        .filter(WeeklyCheck.cliente_id == cliente_id)
        .scalar()
    )

    initial_checks_count = (
        db.session.query(func.count(ClientCheckAssignment.id))
        .filter(ClientCheckAssignment.cliente_id == cliente_id)
        .scalar()
        or 0
    )
    initial_checks_completed_count = (
        db.session.query(func.count(ClientCheckAssignment.id))
        .filter(
            ClientCheckAssignment.cliente_id == cliente_id,
            ClientCheckAssignment.response_count > 0,
        )
        .scalar()
        or 0
    )

    # Fetch all historical data from services
    anamnesi_entries = (
        db.session.query(ServiceAnamnesi)
        .filter(ServiceAnamnesi.cliente_id == cliente_id)
        .order_by(ServiceAnamnesi.service_type)
        .all()
    )

    diary_entries = (
        db.session.query(ServiceDiaryEntry)
        .filter(ServiceDiaryEntry.cliente_id == cliente_id)
        .order_by(ServiceDiaryEntry.service_type, ServiceDiaryEntry.entry_date.desc())
        .all()
    )

    # Fetch all check responses
    minor_checks = (
        db.session.query(MinorCheckResponse)
        .join(MinorCheck, MinorCheckResponse.minor_check_id == MinorCheck.id)
        .filter(MinorCheck.cliente_id == cliente_id)
        .order_by(MinorCheckResponse.submit_date.desc())
        .all()
    )

    dca_checks = (
        db.session.query(DCACheckResponse)
        .join(DCACheck, DCACheckResponse.dca_check_id == DCACheck.id)
        .filter(DCACheck.cliente_id == cliente_id)
        .order_by(DCACheckResponse.submit_date.desc())
        .all()
    )

    # Fetch team member history
    team_history = (
        db.session.query(ClienteProfessionistaHistory)
        .filter(ClienteProfessionistaHistory.cliente_id == cliente_id)
        .order_by(ClienteProfessionistaHistory.data_dal.desc())
        .all()
    )

    # Fetch all meals and training plans
    meal_plans = (
        db.session.query(MealPlan)
        .filter(MealPlan.cliente_id == cliente_id)
        .order_by(MealPlan.created_at.desc())
        .all()
    )
    training_plans = (
        db.session.query(TrainingPlan)
        .filter(TrainingPlan.cliente_id == cliente_id)
        .order_by(TrainingPlan.created_at.desc())
        .all()
    )
    training_locations = (
        db.session.query(TrainingLocation)
        .filter(TrainingLocation.cliente_id == cliente_id)
        .order_by(TrainingLocation.created_at.desc())
        .all()
    )

    trustpilot_reviews = (
        db.session.query(TrustpilotReview)
        .filter(TrustpilotReview.cliente_id == cliente_id)
        .order_by(TrustpilotReview.data_richiesta.desc())
        .all()
    )
    video_review_requests = (
        db.session.query(VideoReviewRequest)
        .filter(VideoReviewRequest.cliente_id == cliente_id)
        .order_by(VideoReviewRequest.created_at.desc())
        .all()
    )

    call_bonus_items = []
    tickets_count: int | None = None
    try:
        from corposostenibile.models import CallBonus, Ticket

        call_bonus_items = (
            db.session.query(CallBonus)
            .filter(CallBonus.cliente_id == cliente_id)
            .order_by(CallBonus.created_at.desc())
            .all()
        )
        tickets_count = (
            db.session.query(func.count(Ticket.id))
            .filter(Ticket.cliente_id == cliente_id)
            .scalar()
            or 0
        )
    except Exception:
        tickets_count = None

    cartelle = (
        db.session.query(CartellaClinica)
        .filter(CartellaClinica.cliente_id == cliente_id)
        .all()
    )
    attachments_count = sum(len(item.allegati or []) for item in cartelle)

    latest_meal_plan = meal_plans[0] if meal_plans else None
    latest_training_plan = training_plans[0] if training_plans else None
    latest_training_location = training_locations[0] if training_locations else None
    latest_trustpilot = trustpilot_reviews[0] if trustpilot_reviews else None
    latest_video_review = video_review_requests[0] if video_review_requests else None
    latest_call_bonus = call_bonus_items[0] if call_bonus_items else None

    # Fetch Health Manager interventions
    customer_care_interventions = (
        db.session.query(CustomerCareIntervention)
        .filter(CustomerCareIntervention.cliente_id == cliente_id)
        .order_by(CustomerCareIntervention.intervention_date.desc())
        .all()
    )
    check_in_interventions = (
        db.session.query(CheckInIntervention)
        .filter(CheckInIntervention.cliente_id == cliente_id)
        .order_by(CheckInIntervention.intervention_date.desc())
        .all()
    )

    # Fetch initial check responses (check_1, check_2, check_3)
    initial_check_responses = (
        db.session.query(ClientCheckResponse)
        .join(ClientCheckAssignment, ClientCheckResponse.assignment_id == ClientCheckAssignment.id)
        .filter(ClientCheckAssignment.cliente_id == cliente_id)
        .order_by(ClientCheckResponse.created_at.desc())
        .all()
    )

    # Calculate progress metrics from weekly responses
    weight_values = [r.weight for r in weekly_responses if r.weight]
    first_weight = weight_values[-1] if weight_values else None
    last_weight = weight_values[0] if weight_values else None
    weight_delta = last_weight - first_weight if (first_weight and last_weight) else None

    avg_ratings = {}
    rating_fields = ['energy_rating', 'sleep_rating', 'mood_rating', 'motivation_rating', 
                     'digestion_rating', 'strength_rating', 'hunger_rating']
    for field in rating_fields:
        values = [getattr(r, field) for r in weekly_responses if getattr(r, field)]
        if values:
            avg_ratings[field.replace('_rating', '')] = sum(values) / len(values)

    # === PDF PROFESSIONAL DESIGN ===
    pdf_buffer = BytesIO()
    
    # Professional color palette - Corposostenibile brand (green #25B36A from frontend)
    PRIMARY_GREEN = colors.HexColor("#25B36A")
    SECONDARY_GREEN = colors.HexColor("#1a8a50")
    ACCENT_GREEN = colors.HexColor("#20a757")
    DARK_GRAY = colors.HexColor("#1f2937")
    MEDIUM_GRAY = colors.HexColor("#6b7280")
    LIGHT_GRAY = colors.HexColor("#f3f4f6")
    WHITE = colors.white
    LIGHT_GREEN_BG = colors.HexColor("#e8f5e9")
    SECTION_BG = colors.HexColor("#f1f8f4")

    # Create custom document with header/footer
    page_width, page_height = A4
    doc = BaseDocTemplate(
        pdf_buffer,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.0 * cm,
        title=f"Cartella Clinica - {cliente.nome_cognome}",
    )

    # Header/Footer template
    def header_footer(canvas_obj, doc):
        canvas_obj.saveState()
        
        # Header background
        canvas_obj.setFillColor(PRIMARY_GREEN)
        canvas_obj.rect(0, page_height - 1.5 * cm, page_width, 1.5 * cm, fill=1, stroke=0)
        
        # Header text
        canvas_obj.setFillColor(WHITE)
        canvas_obj.setFont("Helvetica-Bold", 12)
        canvas_obj.drawString(1.5 * cm, page_height - 1.0 * cm, "Cartella Clinica")
        canvas_obj.setFont("Helvetica", 9)
        canvas_obj.drawRightString(page_width - 1.5 * cm, page_height - 1.0 * cm, f"Paziente: {cliente.nome_cognome or 'N/A'}")
        
        # Footer line
        canvas_obj.setStrokeColor(SECONDARY_GREEN)
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(1.5 * cm, 1.5 * cm, page_width - 1.5 * cm, 1.5 * cm)
        
        # Footer text
        canvas_obj.setFillColor(MEDIUM_GRAY)
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.drawString(1.5 * cm, 1.1 * cm, f"Generato: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        canvas_obj.drawRightString(page_width - 1.5 * cm, 1.1 * cm, f"Pagina {doc.page}")
        
        canvas_obj.restoreState()

    # Create page template
    page_template = PageTemplate(
        id='standard',
        frames=[
            Frame(
                1.5 * cm, 2.0 * cm,
                page_width - 3 * cm, page_height - 4.0 * cm,
                id='main_frame'
            )
        ],
        onPage=header_footer
    )
    doc.addPageTemplates([page_template])

    # Create professional styles
    styles = getSampleStyleSheet()
    
    # Title style - Cover page
    styles.add(ParagraphStyle(
        name="CoverTitle",
        parent=styles["Title"],
        fontSize=28,
        leading=34,
        textColor=PRIMARY_GREEN,
        spaceAfter=20,
        alignment=1,  # Center
        fontName="Helvetica-Bold",
    ))
    
    styles.add(ParagraphStyle(
        name="CoverSubtitle",
        parent=styles["Normal"],
        fontSize=14,
        leading=18,
        textColor=MEDIUM_GRAY,
        spaceAfter=30,
        alignment=1,
    ))
    
    # Section headers
    styles.add(ParagraphStyle(
        name="SectionHeader",
        parent=styles["Heading1"],
        fontSize=14,
        leading=18,
        textColor=PRIMARY_GREEN,
        spaceBefore=15,
        spaceAfter=10,
        fontName="Helvetica-Bold",
        borderPadding=(0, 0, 5, 0),
    ))
    
    # Sub-section headers
    styles.add(ParagraphStyle(
        name="SubSectionHeader",
        parent=styles["Heading2"],
        fontSize=12,
        leading=16,
        textColor=SECONDARY_GREEN,
        spaceBefore=12,
        spaceAfter=8,
        fontName="Helvetica-Bold",
    ))
    
    # Normal text - improved
    styles.add(ParagraphStyle(
        name="PDFBody",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=DARK_GRAY,
        spaceAfter=6,
    ))
    
    # Small meta text
    styles.add(ParagraphStyle(
        name="MetaText",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=MEDIUM_GRAY,
        spaceAfter=4,
    ))
    
    # Highlight label
    styles.add(ParagraphStyle(
        name="HighlightLabel",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=PRIMARY_GREEN,
        fontName="Helvetica-Bold",
        spaceAfter=2,
    ))

    # Build story
    story: list[Any] = []
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    # === COVER PAGE ===
    story.append(Spacer(1, 3 * cm))
    story.append(Paragraph("Cartella Clinica", styles["CoverTitle"]))
    story.append(Paragraph(f"Paziente: {cliente.nome_cognome or 'N/A'}", styles["CoverSubtitle"]))
    story.append(Spacer(1, 0.5 * cm))
    
    # Patient summary card
    cover_data = [
        [Paragraph("<b>ID Paziente</b>", styles["PDFBody"]), Paragraph(str(cliente.cliente_id), styles["PDFBody"])],
        [Paragraph("<b>Data di nascita</b>", styles["PDFBody"]), Paragraph(_export_pdf_format_value(cliente.data_di_nascita), styles["PDFBody"])],
        [Paragraph("<b>Stato</b>", styles["PDFBody"]), Paragraph(_export_pdf_format_value(cliente.stato_cliente), styles["PDFBody"])],
        [Paragraph("<b>Programma</b>", styles["PDFBody"]), Paragraph(_export_pdf_format_value(cliente.programma_attuale), styles["PDFBody"])],
        [Paragraph("<b>Generato il</b>", styles["PDFBody"]), Paragraph(generated_at, styles["PDFBody"])],
    ]
    cover_table = Table(cover_data, colWidths=[5 * cm, 10 * cm])
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREEN_BG),
        ("BOX", (0, 0), (-1, -1), 1, PRIMARY_GREEN),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#a7f3d0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(cover_table)
    story.append(Spacer(1, 1 * cm))
    
    # Column widths for tables
    col_widths = [5.2 * cm, 11.6 * cm]

    # === PART 1: BASIC INFORMATION ===
    story.append(Paragraph("Anagrafica e Programma", styles["SectionHeader"]))
    _append_export_section(story, styles, "Anagrafica", [
        ("Nome e cognome", cliente.nome_cognome),
        ("Data di nascita", cliente.data_di_nascita),
        ("Sesso / Genere", cliente.genere),
        ("Email", cliente.mail),
        ("Telefono", cliente.numero_telefono),
        ("Professione", cliente.professione),
        ("Paese", cliente.paese),
        ("Indirizzo", cliente.indirizzo),
    ], col_widths)

    # Storia e problematiche
    if cliente.storia_cliente or cliente.problema or cliente.paure or cliente.conseguenze:
        story.append(Paragraph("Storia e Problematiche", styles["SubSectionHeader"]))
        if cliente.storia_cliente:
            story.append(Paragraph(f"<b>Storia cliente:</b> {cliente.storia_cliente}", styles["PDFBody"]))
        if cliente.problema:
            story.append(Paragraph(f"<b>Problema:</b> {cliente.problema}", styles["PDFBody"]))
        if cliente.paure:
            story.append(Paragraph(f"<b>Paure:</b> {cliente.paure}", styles["PDFBody"]))
        if cliente.conseguenze:
            story.append(Paragraph(f"<b>Conseguenze:</b> {cliente.conseguenze}", styles["PDFBody"]))
        story.append(Spacer(1, 0.3 * cm))

    _append_export_section(story, styles, "Programma", [
        ("Programma attuale", cliente.programma_attuale),
        ("Dettaglio programma", cliente.programma_attuale_dettaglio),
        ("Macrocategoria", cliente.macrocategoria),
        ("Obiettivo", cliente.obiettivo_cliente or cliente.obiettivo_semplicato),
        ("Tipologia cliente", cliente.tipologia_cliente),
        ("Stato cliente", cliente.stato_cliente),
        ("Data inizio abbonamento", cliente.data_inizio_abbonamento),
        ("Data rinnovo", cliente.data_rinnovo),
        ("Note rinnovo", cliente.note_rinnovo),
    ], col_widths)

    # Date Piani (Nutrizione, Coach, Psicologia)
    date_piani = []
    if cliente.data_inizio_nutrizione:
        date_piani.append(f"Nutrizione: dal {cliente.data_inizio_nutrizione} ({cliente.durata_nutrizione_giorni or '-'} gg) → {cliente.data_scadenza_nutrizione or '-'}")
    if cliente.data_inizio_coach:
        date_piani.append(f"Coach: dal {cliente.data_inizio_coach} ({cliente.durata_coach_giorni or '-'} gg) → {cliente.data_scadenza_coach or '-'}")
    if cliente.data_inizio_psicologia:
        date_piani.append(f"Psicologia: dal {cliente.data_inizio_psicologia} ({cliente.durata_psicologia_giorni or '-'} gg) → {cliente.data_scadenza_psicologia or '-'}")
    if date_piani:
        story.append(Paragraph("Date Piani Servizio", styles["SubSectionHeader"]))
        for dp in date_piani:
            story.append(Paragraph(dp, styles["PDFBody"]))
        story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("Team Attuale", styles["SectionHeader"]))
    _append_export_section(story, styles, "Team", [
        ("Nutrizionista", cliente.nutrizionista or _export_pdf_user_label(getattr(cliente, "nutrizionista_user", None))),
        ("Coach", cliente.coach or _export_pdf_user_label(getattr(cliente, "coach_user", None))),
        ("Psicologia", cliente.psicologa or _export_pdf_user_label(getattr(cliente, "psicologa_user", None))),
        ("Health Manager", _export_pdf_user_label(getattr(cliente, "health_manager_user", None))),
        ("Consulente", _export_pdf_user_label(getattr(cliente, "consulente_alimentare_user", None))),
    ], col_widths)

    # === PART 2: TEAM HISTORY ===
    if team_history:
        story.append(Paragraph("Storico Team", styles["SectionHeader"]))
        for entry in team_history:
            type_label = _export_pdf_format_value(entry.tipo_professionista)
            user_label = _export_pdf_user_label(entry.professionista)
            start_date = entry.data_dal.strftime("%d/%m/%Y") if entry.data_dal else "-"
            end_date = entry.data_al.strftime("%d/%m/%Y") if entry.data_al else ("Attivo" if entry.is_active else "-")
            status = "Attivo" if entry.is_active else "Terminato"
            story.append(Paragraph(f"<b>{type_label}</b>: {user_label} ({start_date} → {end_date}) [{status}]", styles["PDFBody"]))
        story.append(Spacer(1, 10))

    # === PART 2.5: HEALTH MANAGER ===
    if customer_care_interventions or check_in_interventions:
        story.append(Paragraph("Health Manager", styles["SectionHeader"]))
        
        if customer_care_interventions:
            story.append(Paragraph("Interventi Customer Care", styles["SubSectionHeader"]))
            for intv in customer_care_interventions[:20]:
                date_str = intv.intervention_date.strftime("%d/%m/%Y") if intv.intervention_date else "-"
                author_str = _export_pdf_user_label(intv.created_by) if intv.created_by else "-"
                story.append(Paragraph(f"<b>{date_str}</b> - {author_str}: {intv.notes or '-'}", styles["PDFBody"]))
                if intv.loom_link:
                    story.append(Paragraph(f"<i>Loom: {intv.loom_link}</i>", styles["MetaText"]))
            story.append(Spacer(1, 0.3 * cm))
        
        if check_in_interventions:
            story.append(Paragraph("Interventi Check-in", styles["SubSectionHeader"]))
            for intv in check_in_interventions[:20]:
                date_str = intv.intervention_date.strftime("%d/%m/%Y") if intv.intervention_date else "-"
                author_str = _export_pdf_user_label(intv.created_by) if intv.created_by else "-"
                story.append(Paragraph(f"<b>{date_str}</b> - {author_str}: {intv.notes or '-'}", styles["PDFBody"]))
                if intv.loom_link:
                    story.append(Paragraph(f"<i>Loom: {intv.loom_link}</i>", styles["MetaText"]))
            story.append(Spacer(1, 0.3 * cm))
        story.append(Spacer(1, 0.3 * cm))

    # === PART 3: SERVICE DATA ===
    story.append(Spacer(1, 0.5 * cm))
    
    # Nutrizione section
    story.append(Paragraph("Nutrizione", styles["SectionHeader"]))
    _append_export_section(story, styles, "Stato Nutrizione", [
        ("Stato nutrizione", cliente.stato_nutrizione),
        ("Stato chat nutrizione", cliente.stato_cliente_chat_nutrizione),
        ("Reach out nutrizione", cliente.reach_out_nutrizione),
        ("Call iniziale", "Si" if cliente.call_iniziale_nutrizionista else "No"),
        ("Piani alimentari totali", len(meal_plans)),
        ("Ultimo piano alimentare", getattr(latest_meal_plan, "name", None)),
        ("Ultimo piano - inizio", getattr(latest_meal_plan, "start_date", None)),
        ("Ultimo piano - fine", getattr(latest_meal_plan, "end_date", None)),
    ], col_widths)

    # Scelte anamnesi (checkbox nutrizione)
    patologie_nutrizione = []
    if cliente.nessuna_patologia: patologie_nutrizione.append("Nessuna patologia")
    if cliente.patologia_ibs: patologie_nutrizione.append("IBS")
    if cliente.patologia_reflusso: patologie_nutrizione.append("Reflusso")
    if cliente.patologia_gastrite: patologie_nutrizione.append("Gastrite")
    if cliente.patologia_dca: patologie_nutrizione.append("DCA")
    if cliente.patologia_insulino_resistenza: patologie_nutrizione.append("Insulino Resistenza")
    if cliente.patologia_diabete: patologie_nutrizione.append("Diabete")
    if cliente.patologia_dislipidemie: patologie_nutrizione.append("Dislipidemie")
    if cliente.patologia_steatosi_epatica: patologie_nutrizione.append("Steatosi Epatica")
    if cliente.patologia_ipertensione: patologie_nutrizione.append("Ipertensione")
    if cliente.patologia_pcos: patologie_nutrizione.append("PCOS")
    if cliente.patologia_endometriosi: patologie_nutrizione.append("Endometriosi")
    if cliente.patologia_obesita_sindrome: patologie_nutrizione.append("Obesità")
    if cliente.patologia_osteoporosi: patologie_nutrizione.append("Osteoporosi")
    if cliente.patologia_diverticolite: patologie_nutrizione.append("Diverticolite")
    if cliente.patologia_crohn: patologie_nutrizione.append("Crohn")
    if cliente.patologia_stitichezza: patologie_nutrizione.append("Stitichezza")
    if cliente.patologia_tiroidee: patologie_nutrizione.append("Tiroidee")
    if cliente.patologia_altro: patologie_nutrizione.append(f"Altro: {cliente.patologia_altro}")
    # Alert nutrizione
    if cliente.alert_nutrizione:
        story.append(Paragraph("Alert Nutrizione", styles["SubSectionHeader"]))
        story.append(Paragraph(f"<b>{cliente.alert_nutrizione}</b>", styles["PDFBody"]))
        story.append(Spacer(1, 0.2 * cm))

    # Storia e note nutrizione
    if cliente.storia_nutrizione:
        story.append(Paragraph("Storia Nutrizione", styles["SubSectionHeader"]))
        story.append(Paragraph(cliente.storia_nutrizione.replace("\n", "<br/>"), styles["PDFBody"]))
        story.append(Spacer(1, 0.2 * cm))
    if cliente.note_extra_nutrizione:
        story.append(Paragraph("Note Extra Nutrizione", styles["SubSectionHeader"]))
        story.append(Paragraph(cliente.note_extra_nutrizione.replace("\n", "<br/>"), styles["PDFBody"]))
        story.append(Spacer(1, 0.2 * cm))

    # Anamnesi nutrizione
    anamnesi_nutrizione = next((a for a in anamnesi_entries if a.service_type == "nutrizione"), None)
    if anamnesi_nutrizione:
        story.append(Paragraph("Anamnesi Nutrizione", styles["SubSectionHeader"]))
        if patologie_nutrizione:
            story.append(Paragraph("<b>Anamnesi:</b> " + ", ".join(patologie_nutrizione), styles["PDFBody"]))
            story.append(Spacer(1, 0.1 * cm))
        story.append(Paragraph(f"<i>Creato il: {anamnesi_nutrizione.created_at.strftime('%d/%m/%Y')}</i>", styles["MetaText"]))
        story.append(Paragraph(anamnesi_nutrizione.content.replace("\n", "<br/>"), styles["PDFBody"]))
        story.append(Spacer(1, 10))
    elif patologie_nutrizione:
        story.append(Paragraph("Anamnesi Nutrizione", styles["SubSectionHeader"]))
        story.append(Paragraph("<b>Anamnesi:</b> " + ", ".join(patologie_nutrizione), styles["PDFBody"]))
        story.append(Spacer(1, 0.2 * cm))

    # Diario nutrizione
    diario_nutrizione = [d for d in diary_entries if d.service_type == "nutrizione"]
    if diario_nutrizione:
        story.append(Paragraph("Diario Nutrizione", styles["SubSectionHeader"]))
        for entry in diario_nutrizione[:15]:
            story.append(Paragraph(f"<b>{entry.entry_date.strftime('%d/%m/%Y')}</b> - {_export_pdf_user_label(entry.author)}", styles["HighlightLabel"]))
            story.append(Paragraph(entry.content.replace("\n", "<br/>"), styles["PDFBody"]))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 6))

    story.append(Spacer(1, 0.5 * cm))
    # Coaching section
    story.append(Paragraph("Coaching", styles["SectionHeader"]))
    _append_export_section(story, styles, "Stato Coaching", [
        ("Stato coaching", cliente.stato_coach),
        ("Stato chat coaching", cliente.stato_cliente_chat_coaching),
        ("Reach out coaching", cliente.reach_out_coaching),
        ("Call iniziale", "Si" if cliente.call_iniziale_coach else "No"),
        ("Luogo allenamento", cliente.luogo_di_allenamento),
        ("Piani allenamento totali", len(training_plans)),
        ("Ultimo piano allenamento", getattr(latest_training_plan, "name", None)),
        ("Ultimo piano - inizio", getattr(latest_training_plan, "start_date", None)),
        ("Ultimo piano - fine", getattr(latest_training_plan, "end_date", None)),
        ("Ultima location allenamento", getattr(latest_training_location, "location", None)),
    ], col_widths)

    # Scelte anamnesi (checkbox coaching)
    patologie_coaching = []
    if cliente.nessuna_patologia_coach: patologie_coaching.append("Nessuna patologia")
    if cliente.patologia_coach_infortuni: patologie_coaching.append("Infortuni pregressi")
    if cliente.patologia_coach_dolori_cronici: patologie_coaching.append("Dolori cronici")
    if cliente.patologia_coach_limitazioni_articolari: patologie_coaching.append("Limitazioni articolari")
    if cliente.patologia_coach_posturali: patologie_coaching.append("Problematiche posturali")
    if cliente.patologia_coach_cardiovascolari: patologie_coaching.append("Problematiche cardiovascolari")
    if cliente.patologia_coach_altro: patologie_coaching.append(f"Altro: {cliente.patologia_coach_altro}")
    # Alert coaching
    if cliente.alert_coaching:
        story.append(Paragraph("Alert Coaching", styles["SubSectionHeader"]))
        story.append(Paragraph(f"<b>{cliente.alert_coaching}</b>", styles["PDFBody"]))
        story.append(Spacer(1, 0.2 * cm))

    # Storia e note coaching
    if cliente.storia_coach:
        story.append(Paragraph("Storia Coaching", styles["SubSectionHeader"]))
        story.append(Paragraph(cliente.storia_coach.replace("\n", "<br/>"), styles["PDFBody"]))
        story.append(Spacer(1, 0.2 * cm))
    if cliente.note_extra_coach:
        story.append(Paragraph("Note Extra Coaching", styles["SubSectionHeader"]))
        story.append(Paragraph(cliente.note_extra_coach.replace("\n", "<br/>"), styles["PDFBody"]))
        story.append(Spacer(1, 0.2 * cm))

    # Anamnesi coaching
    anamnesi_coaching = next((a for a in anamnesi_entries if a.service_type == "coaching"), None)
    if anamnesi_coaching:
        story.append(Paragraph("Anamnesi Coaching", styles["SubSectionHeader"]))
        if patologie_coaching:
            story.append(Paragraph("<b>Anamnesi:</b> " + ", ".join(patologie_coaching), styles["PDFBody"]))
            story.append(Spacer(1, 0.1 * cm))
        story.append(Paragraph(f"<i>Creato il: {anamnesi_coaching.created_at.strftime('%d/%m/%Y')}</i>", styles["MetaText"]))
        story.append(Paragraph(anamnesi_coaching.content.replace("\n", "<br/>"), styles["PDFBody"]))
        story.append(Spacer(1, 10))
    elif patologie_coaching:
        story.append(Paragraph("Anamnesi Coaching", styles["SubSectionHeader"]))
        story.append(Paragraph("<b>Anamnesi:</b> " + ", ".join(patologie_coaching), styles["PDFBody"]))
        story.append(Spacer(1, 0.2 * cm))

    # Diario coaching
    diario_coaching = [d for d in diary_entries if d.service_type == "coaching"]
    if diario_coaching:
        story.append(Paragraph("Diario Coaching", styles["SubSectionHeader"]))
        for entry in diario_coaching[:15]:
            story.append(Paragraph(f"<b>{entry.entry_date.strftime('%d/%m/%Y')}</b> - {_export_pdf_user_label(entry.author)}", styles["HighlightLabel"]))
            story.append(Paragraph(entry.content.replace("\n", "<br/>"), styles["PDFBody"]))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 6))

    story.append(Spacer(1, 0.5 * cm))
    # Psicologia section
    story.append(Paragraph("Psicologia", styles["SectionHeader"]))

    _append_export_section(story, styles, "Stato Psicologia", [
        ("Stato psicologia", cliente.stato_psicologia),
        ("Stato chat psicologia", cliente.stato_cliente_chat_psicologia),
        ("Reach out psicologia", cliente.reach_out_psicologia),
        ("Call iniziale", "Si" if cliente.call_iniziale_psicologa else "No"),
    ], col_widths)

    # Scelte anamnesi (checkbox psicologia)
    patologie_psico = []
    if cliente.nessuna_patologia_psico: patologie_psico.append("Nessuna patologia")
    if cliente.patologia_psico_dca: patologie_psico.append("DCA")
    if cliente.patologia_psico_obesita_psicoemotiva: patologie_psico.append("Obesità psicoemotiva")
    if cliente.patologia_psico_ansia_umore_cibo: patologie_psico.append("Ansia/umore/cibo")
    if cliente.patologia_psico_comportamenti_disfunzionali: patologie_psico.append("Comportamenti disfunzionali")
    if cliente.patologia_psico_immagine_corporea: patologie_psico.append("Immagine corporea")
    if cliente.patologia_psico_psicosomatiche: patologie_psico.append("Psicosomatiche")
    if cliente.patologia_psico_relazionali_altro: patologie_psico.append("Relazionali/Altro")
    if cliente.patologia_psico_altro: patologie_psico.append(f"Altro: {cliente.patologia_psico_altro}")
    # Alert psicologia
    if cliente.alert_psicologia:
        story.append(Paragraph("Alert Psicologia", styles["SubSectionHeader"]))
        story.append(Paragraph(f"<b>{cliente.alert_psicologia}</b>", styles["PDFBody"]))
        story.append(Spacer(1, 0.2 * cm))

    # Storia e note psicologia
    if cliente.storia_psicologica:
        story.append(Paragraph("Storia Psicologica", styles["SubSectionHeader"]))
        story.append(Paragraph(cliente.storia_psicologica.replace("\n", "<br/>"), styles["PDFBody"]))
        story.append(Spacer(1, 0.2 * cm))
    if cliente.note_extra_psicologa:
        story.append(Paragraph("Note Extra Psicologia", styles["SubSectionHeader"]))
        story.append(Paragraph(cliente.note_extra_psicologa.replace("\n", "<br/>"), styles["PDFBody"]))
        story.append(Spacer(1, 0.2 * cm))

    # Anamnesi psicologia
    anamnesi_psicologia = next((a for a in anamnesi_entries if a.service_type == "psicologia"), None)
    if anamnesi_psicologia:
        story.append(Paragraph("Anamnesi Psicologia", styles["SubSectionHeader"]))
        if patologie_psico:
            story.append(Paragraph("<b>Anamnesi:</b> " + ", ".join(patologie_psico), styles["PDFBody"]))
            story.append(Spacer(1, 0.1 * cm))
        story.append(Paragraph(f"<i>Creato il: {anamnesi_psicologia.created_at.strftime('%d/%m/%Y')}</i>", styles["MetaText"]))
        story.append(Paragraph(anamnesi_psicologia.content.replace("\n", "<br/>"), styles["PDFBody"]))
        story.append(Spacer(1, 10))
    elif patologie_psico:
        story.append(Paragraph("Anamnesi Psicologia", styles["SubSectionHeader"]))
        story.append(Paragraph("<b>Anamnesi:</b> " + ", ".join(patologie_psico), styles["PDFBody"]))
        story.append(Spacer(1, 0.2 * cm))

    # Diario psicologia
    diario_psicologia = [d for d in diary_entries if d.service_type == "psicologia"]
    if diario_psicologia:
        story.append(Paragraph("Diario Psicologia", styles["SubSectionHeader"]))
        for entry in diario_psicologia[:15]:
            story.append(Paragraph(f"<b>{entry.entry_date.strftime('%d/%m/%Y')}</b> - {_export_pdf_user_label(entry.author)}", styles["HighlightLabel"]))
            story.append(Paragraph(entry.content.replace("\n", "<br/>"), styles["PDFBody"]))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 6))

    # === PART 4: PROGRESSO ===
    if weight_values or avg_ratings:
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph("Progresso", styles["SectionHeader"]))
        
        # Weight trend
        if weight_values:
            story.append(Paragraph("Andamento Peso", styles["SubSectionHeader"]))
            weight_data = [
                [Paragraph("<b>Prima</b>", styles["PDFBody"]), Paragraph("<b>Attuale</b>", styles["PDFBody"]), Paragraph("<b>Delta</b>", styles["PDFBody"])],
                [Paragraph(f"{first_weight} kg" if first_weight else "-", styles["PDFBody"]),
                 Paragraph(f"{last_weight} kg" if last_weight else "-", styles["PDFBody"]),
                 Paragraph(f"{weight_delta:+.1f} kg" if weight_delta else "-", styles["PDFBody"])],
            ]
            weight_table = Table(weight_data, colWidths=[4 * cm, 4 * cm, 4 * cm])
            weight_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GREEN_BG),
                ("BACKGROUND", (0, 1), (-1, 1), WHITE),
                ("BOX", (0, 0), (-1, -1), 1, PRIMARY_GREEN),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#a7f3d0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(weight_table)
            story.append(Spacer(1, 0.3 * cm))

        # Average ratings
        if avg_ratings:
            story.append(Paragraph("Valutazioni Medie (Check Settimanali)", styles["SubSectionHeader"]))
            ratings_data = [[Paragraph(f"<b>{k.title()}</b>", styles["PDFBody"]), Paragraph(f"<b>{v:.1f}/10</b>", styles["PDFBody"])] for k, v in avg_ratings.items()]
            ratings_table = Table(ratings_data, colWidths=[8 * cm, 4 * cm])
            ratings_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), LIGHT_GREEN_BG),
                ("BACKGROUND", (1, 0), (1, -1), WHITE),
                ("BOX", (0, 0), (-1, -1), 1, PRIMARY_GREEN),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#a7f3d0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(ratings_table)
            story.append(Spacer(1, 0.3 * cm))

    # === PART 5: CHECKS ===
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("Check e Valutazioni", styles["SectionHeader"]))
    _append_export_section(story, styles, "Riepilogo Check", [
        ("Check settimanali configurati", weekly_checks_count),
        ("Risposte check settimanali", weekly_responses_count),
        ("Ultima risposta check", latest_check_response_date),
        ("Check iniziali assegnati", initial_checks_count),
        ("Check iniziali completati", initial_checks_completed_count),
        ("Check minori completati", len(minor_checks)),
        ("Check DCA completati", len(dca_checks)),
        ("Giorno check", cliente.check_day),
        ("Check saltati", cliente.check_saltati),
    ], col_widths)

    # Check minori
    if minor_checks:
        story.append(Paragraph("Check Minori", styles["SubSectionHeader"]))
        for resp in minor_checks[:10]:
            submit_date = resp.submit_date.strftime("%d/%m/%Y") if resp.submit_date else "-"
            story.append(Paragraph(f"<b>{submit_date}</b>", styles["HighlightLabel"]))
            if resp.notes:
                story.append(Paragraph(f"Note: {resp.notes[:200]}", styles["PDFBody"]))
            story.append(Spacer(1, 0.1 * cm))
        story.append(Spacer(1, 0.3 * cm))

    # Check DCA
    if dca_checks:
        story.append(Paragraph("Check DCA", styles["SubSectionHeader"]))
        for resp in dca_checks[:10]:
            submit_date = resp.submit_date.strftime("%d/%m/%Y") if resp.submit_date else "-"
            story.append(Paragraph(f"<b>{submit_date}</b>", styles["HighlightLabel"]))
            if resp.notes:
                story.append(Paragraph(f"Note: {resp.notes[:200]}", styles["PDFBody"]))
            story.append(Spacer(1, 0.1 * cm))
        story.append(Spacer(1, 0.3 * cm))

    # === PART 6: OTHER SECTIONS ===
    _append_export_section(story, styles, "Loom e Ticket", [
        ("Loom link", cliente.loom_link),
        ("Ticket associati", tickets_count),
    ], col_widths)

    _append_export_section(story, styles, "Marketing", [
        ("Richieste Trustpilot", len(trustpilot_reviews)),
        ("Video review richieste", len(video_review_requests)),
        ("Richieste call bonus", len(call_bonus_items)),
    ], col_widths)

    _append_export_section(story, styles, "Documentazione", [
        ("Cartelle cliniche", len(cartelle)),
        ("Allegati totali", attachments_count),
        ("Alert", cliente.alert),
    ], col_widths)

    # === PART 6: CHECK RESPONSES DETAILS ===
    if initial_check_responses or weekly_responses or minor_checks or dca_checks:
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph("Dettaglio Risposte Check", styles["SectionHeader"]))
        story.append(Spacer(1, 0.3 * cm))

        # Initial check responses (compact layout)
        if initial_check_responses:
            story.append(Paragraph("Check Iniziali", styles["SubSectionHeader"]))
            for idx, resp in enumerate(initial_check_responses[:10], 1):
                assignment = resp.assignment
                form_name = assignment.form.name if assignment and assignment.form else f"Check {idx}"
                submit_date = resp.created_at.strftime("%d/%m/%Y") if resp.created_at else "-"
                story.append(Paragraph(f"<b>{form_name}</b> - Compilato il: {submit_date}", styles["HighlightLabel"]))

                formatted_responses = resp.get_formatted_responses()
                if not formatted_responses and isinstance(resp.responses, dict):
                    formatted_responses = resp.responses

                if formatted_responses:
                    items = []
                    for key, value in formatted_responses.items():
                        if value is None or str(value).strip() == "":
                            continue
                        if isinstance(value, (dict, list)):
                            value = json.dumps(value, ensure_ascii=True)
                        value_str = str(value)
                        if len(value_str) > 180:
                            value_str = value_str[:180] + "..."
                        items.append((str(key), value_str))

                    rows = []
                    for i in range(0, len(items), 2):
                        left_key, left_val = items[i]
                        right_key, right_val = ("", "")
                        if i + 1 < len(items):
                            right_key, right_val = items[i + 1]
                        rows.append([
                            Paragraph(f"<b>{left_key}</b>", styles["MetaText"]),
                            Paragraph(left_val, styles["PDFBody"]),
                            Paragraph(f"<b>{right_key}</b>" if right_key else "", styles["MetaText"]),
                            Paragraph(right_val, styles["PDFBody"]),
                        ])

                    table = Table(rows, colWidths=[4 * cm, 5 * cm, 4 * cm, 5 * cm])
                    table.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (0, -1), LIGHT_GREEN_BG),
                        ("BACKGROUND", (2, 0), (2, -1), LIGHT_GREEN_BG),
                        ("BACKGROUND", (1, 0), (1, -1), WHITE),
                        ("BACKGROUND", (3, 0), (3, -1), WHITE),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ]))
                    story.append(table)
                else:
                    story.append(Paragraph("Nessuna risposta disponibile", styles["MetaText"]))

                story.append(Spacer(1, 0.2 * cm))
            story.append(Spacer(1, 0.3 * cm))

        # Weekly check responses
        if weekly_responses:
            story.append(Paragraph(f"Check Settimanali ({len(weekly_responses)} risposte)", styles["SubSectionHeader"]))
            for resp in weekly_responses[:15]:
                submit_str = resp.submit_date.strftime("%d/%m/%Y") if resp.submit_date else "-"
                
                # Header con data
                story.append(Paragraph(f"<b>{submit_str}</b>", styles["HighlightLabel"]))
                
                # Foto
                photos_list = []
                if resp.photo_front:
                    photos_list.append("Frontale")
                if resp.photo_side:
                    photos_list.append("Laterale")
                if resp.photo_back:
                    photos_list.append("Posteriore")
                if photos_list:
                    story.append(Paragraph(f"<b>Foto:</b> {', '.join(photos_list)}", styles["PDFBody"]))
                
                # Riflessioni
                if resp.what_worked:
                    story.append(Paragraph(f"<b>Cosa ha funzionato:</b> {resp.what_worked[:200]}" + ("..." if len(resp.what_worked) > 200 else ""), styles["PDFBody"]))
                if resp.what_didnt_work:
                    story.append(Paragraph(f"<b>Cosa non ha funzionato:</b> {resp.what_didnt_work[:200]}" + ("..." if len(resp.what_didnt_work) > 200 else ""), styles["PDFBody"]))
                if resp.what_learned:
                    story.append(Paragraph(f"<b>Cosa hai imparato:</b> {resp.what_learned[:200]}" + ("..." if len(resp.what_learned) > 200 else ""), styles["PDFBody"]))
                
                # Benessere - Valutazioni
                wellbeing_ratings = []
                if resp.digestion_rating:
                    wellbeing_ratings.append(f"Digestione: {resp.digestion_rating}")
                if resp.energy_rating:
                    wellbeing_ratings.append(f"Energia: {resp.energy_rating}")
                if resp.strength_rating:
                    wellbeing_ratings.append(f"Forza: {resp.strength_rating}")
                if resp.hunger_rating:
                    wellbeing_ratings.append(f"Fame: {resp.hunger_rating}")
                if resp.sleep_rating:
                    wellbeing_ratings.append(f"Sonno: {resp.sleep_rating}")
                if resp.mood_rating:
                    wellbeing_ratings.append(f"Umore: {resp.mood_rating}")
                if resp.motivation_rating:
                    wellbeing_ratings.append(f"Motivazione: {resp.motivation_rating}")
                if wellbeing_ratings:
                    story.append(Paragraph(f"<b>Benessere:</b> {' | '.join(wellbeing_ratings)}", styles["PDFBody"]))
                
                # Peso
                if resp.weight:
                    story.append(Paragraph(f"<b>Peso:</b> {resp.weight} kg", styles["PDFBody"]))
                
                # Programmi
                program_info = []
                if resp.nutrition_program_adherence:
                    program_info.append(f"Nutrizione: {resp.nutrition_program_adherence[:50]}")
                if resp.training_program_adherence:
                    program_info.append(f"Allenamento: {resp.training_program_adherence[:50]}")
                if resp.exercise_modifications:
                    program_info.append(f"Esercizi modificati: {resp.exercise_modifications[:50]}")
                if program_info:
                    story.append(Paragraph(f"<b>Programmi:</b> {' | '.join(program_info)}", styles["PDFBody"]))
                
                # Valutazioni Professionisti
                prof_ratings = []
                if resp.nutritionist_rating:
                    prof_ratings.append(f"Nutrizionista: {resp.nutritionist_rating}/10")
                if resp.coach_rating:
                    prof_ratings.append(f"Coach: {resp.coach_rating}/10")
                if resp.psychologist_rating:
                    prof_ratings.append(f"Psicologo: {resp.psychologist_rating}/10")
                if resp.progress_rating:
                    prof_ratings.append(f"Progresso: {resp.progress_rating}/10")
                if prof_ratings:
                    story.append(Paragraph(f"<b>Valutazioni:</b> {' | '.join(prof_ratings)}", styles["PDFBody"]))
                
                # Feedback professionisti
                if resp.nutritionist_feedback:
                    story.append(Paragraph(f"<b>Feedback nutrizionista:</b> {resp.nutritionist_feedback[:150]}" + ("..." if len(resp.nutritionist_feedback) > 150 else ""), styles["PDFBody"]))
                if resp.coach_feedback:
                    story.append(Paragraph(f"<b>Feedback coach:</b> {resp.coach_feedback[:150]}" + ("..." if len(resp.coach_feedback) > 150 else ""), styles["PDFBody"]))
                if resp.psychologist_feedback:
                    story.append(Paragraph(f"<b>Feedback psicologo:</b> {resp.psychologist_feedback[:150]}" + ("..." if len(resp.psychologist_feedback) > 150 else ""), styles["PDFBody"]))
                
                # Referral
                if resp.referral:
                    story.append(Paragraph(f"<b>Referral:</b> {resp.referral[:150]}", styles["PDFBody"]))
                
                # Commenti extra
                if resp.extra_comments:
                    story.append(Paragraph(f"<b>Commenti:</b> {resp.extra_comments[:150]}" + ("..." if len(resp.extra_comments) > 150 else ""), styles["PDFBody"]))
                
                story.append(Spacer(1, 10))

        # Minor check responses
        if minor_checks:
            story.append(Paragraph(f"Minor Check - EDE-Q6 ({len(minor_checks)} risposte)", styles["SubSectionHeader"]))
            for resp in minor_checks[:10]:
                submit_str = resp.submit_date.strftime("%d/%m/%Y") if resp.submit_date else "-"
                story.append(Paragraph(f"<b>{submit_str}</b> | Score: {resp.score_global or '-'} | Weight: {resp.peso_attuale or '-'} kg | Height: {resp.altezza or '-'} cm", styles["PDFBody"]))
            story.append(Spacer(1, 6))

        # DCA check responses
        if dca_checks:
            story.append(Paragraph(f"DCA Check ({len(dca_checks)} risposte)", styles["SubSectionHeader"]))
            for resp in dca_checks[:10]:
                submit_str = resp.submit_date.strftime("%d/%m/%Y") if resp.submit_date else "-"
                story.append(Paragraph(f"<b>{submit_str}</b> | Mood: {resp.mood_balance_rating or '-'} | Motivation: {resp.motivation_level or '-'}", styles["PDFBody"]))

    doc.build(story)
    pdf_buffer.seek(0)

    safe_name = (cliente.nome_cognome or f"cliente_{cliente_id}").strip().replace(" ", "_")
    safe_name = "".join(ch for ch in safe_name if ch.isalnum() or ch in {"_", "-"}) or f"cliente_{cliente_id}"

    from flask import send_file

    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"cartella_clinica_{safe_name}.pdf",
    )

@api_bp.route("/<int:cliente_id>", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_detail(cliente_id: int) -> Any:
    """Get customer detail with trial user access control."""
    # Trial user access check
    if current_user.is_authenticated and current_user.is_trial:
        if current_user.trial_stage < 2:
            # Stage 1: No access to any customer
            return jsonify({
                "error": "Accesso non autorizzato",
                "message": "Non hai accesso ai clienti in Stage 1"
            }), HTTPStatus.FORBIDDEN
        elif current_user.trial_stage == 2:
            # Stage 2: Only assigned clients
            if not current_user.can_view_client(cliente_id):
                return jsonify({
                    "error": "Accesso non autorizzato",
                    "message": "Puoi visualizzare solo i clienti assegnati a te"
                }), HTTPStatus.FORBIDDEN
    
    _require_cliente_scope_or_403(cliente_id)
    cliente = customers_repo.get_one(cliente_id, eager=True)
    result = cliente_schema.dump(cliente)

    # Latest front photo from weekly checks or typeform as client avatar
    from corposostenibile.models import WeeklyCheckResponse, WeeklyCheck, TypeFormResponse
    from corposostenibile.blueprints.client_checks.routes import _photo_path_to_url
    latest_photo = None
    # Try WeeklyCheckResponse first (newer system)
    wc = (
        db.session.query(WeeklyCheckResponse.photo_front)
        .join(WeeklyCheck)
        .filter(WeeklyCheck.cliente_id == cliente_id, WeeklyCheckResponse.photo_front.isnot(None))
        .order_by(WeeklyCheckResponse.submit_date.desc())
        .first()
    )
    if wc and wc[0]:
        latest_photo = _photo_path_to_url(wc[0])
    else:
        # Fallback to TypeFormResponse
        tf = (
            db.session.query(TypeFormResponse.photo_front)
            .filter(TypeFormResponse.cliente_id == cliente_id, TypeFormResponse.photo_front.isnot(None))
            .order_by(TypeFormResponse.submit_date.desc())
            .first()
        )
        if tf and tf[0]:
            latest_photo = _photo_path_to_url(tf[0])
    result['latest_photo_front'] = latest_photo

    return jsonify({"data": result})

@api_bp.route("/", methods=["POST"])
@permission_required(CustomerPerm.CREATE)
def api_create() -> Any:
    data: Dict[str, Any] = request.get_json(force=True, silent=False)
    
    # Use schema with session for validation (required for unique checks)
    with db.session.no_autoflush:
        errors = cliente_schema.validate(data, session=db.session)
        
    if errors:
        raise BadRequest(errors)
    cliente = create_cliente(data, current_user)
    return jsonify({"data": cliente_schema.dump(cliente)}), HTTPStatus.CREATED

@api_bp.route("/<int:cliente_id>", methods=["PATCH"])
@permission_required(CustomerPerm.EDIT)
def api_update(cliente_id: int) -> Any:
    _require_cliente_scope_or_403(cliente_id)
    cliente = customers_repo.get_one(cliente_id)
    data: Dict[str, Any] = request.get_json(force=True, silent=False)
    # Use schema with session for validation
    with db.session.no_autoflush:
        errors = cliente_schema.validate(data, partial=True, session=db.session)
    if errors:
        raise BadRequest(errors)
    update_cliente(cliente, data, current_user)
    return jsonify({"data": cliente_schema.dump(cliente)})

@api_bp.route("/<int:cliente_id>", methods=["DELETE"])
@permission_required(CustomerPerm.DELETE)
def api_delete(cliente_id: int) -> Any:
    _require_cliente_scope_or_403(cliente_id)
    cliente = customers_repo.get_one(cliente_id)
    delete_cliente(cliente, current_user)
    return "", HTTPStatus.NO_CONTENT

# – HISTORY ----------------------------------------------------------------- #
@api_bp.route("/<int:cliente_id>/history", methods=["GET"])
@permission_required(CustomerPerm.VIEW_HISTORY)
def api_history(cliente_id: int) -> Any:
    _require_cliente_scope_or_403(cliente_id)
    limit = request.args.get("limit", 100, type=int)
    versions = customers_repo.history_for_cliente(cliente_id, limit=limit)

    op_map = {0: "insert", 1: "update", 2: "delete"}
    data = []
    for v in versions:
        tx = getattr(v, "transaction", None)
        data.append(
            {
                "txId": getattr(tx, "id", None) if tx else None,
                "op": op_map.get(getattr(v, "operation_type", None), "unknown"),
                "userId": getattr(tx, "user_id", None) if tx else None,
                "timestamp": getattr(tx, "issued_at", None).isoformat() if tx and hasattr(tx, "issued_at") else None,
                "changes": getattr(v, "changeset", {}) or {},
            }
        )
    return jsonify({"data": data})

# – STATS ------------------------------------------------------------------- #
@api_bp.route("/stats", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_stats() -> Any:
    """Espone le metriche di dashboard in JSON."""
    return jsonify(_compute_dashboard_metrics())

# – ADMIN DASHBOARD STATS -------------------------------------------------- #
def _admin_dashboard_base_query():
    """Query base clienti con filtro per ruolo (Admin / TL / Professionista)."""
    return apply_role_filtering(db.session.query(Cliente))


@api_bp.route("/admin-dashboard-stats", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_admin_dashboard_stats() -> Any:
    """Comprehensive patient dashboard stats; data filtered by role (admin=all, TL=team, member=own)."""
    today = date.today()
    first_day_month = today.replace(day=1)
    threshold_scadenza = today + timedelta(days=30)

    # Base query con filtro ruolo
    def q():
        return _admin_dashboard_base_query()

    # ─── KPI ─────────────────────────────────────────────────────────── #
    total = q().with_entities(func.count(Cliente.cliente_id)).scalar() or 0
    active = q().filter(Cliente.stato_cliente == "attivo").with_entities(func.count(Cliente.cliente_id)).scalar() or 0
    ghost = q().filter(Cliente.stato_cliente == "ghost").with_entities(func.count(Cliente.cliente_id)).scalar() or 0
    pausa = q().filter(Cliente.stato_cliente == "pausa").with_entities(func.count(Cliente.cliente_id)).scalar() or 0
    stop = q().filter(Cliente.stato_cliente == "stop").with_entities(func.count(Cliente.cliente_id)).scalar() or 0
    new_month = q().filter(Cliente.created_at >= first_day_month).with_entities(func.count(Cliente.cliente_id)).scalar() or 0
    in_scadenza = q().filter(
        Cliente.data_rinnovo.isnot(None),
        Cliente.data_rinnovo <= threshold_scadenza,
        Cliente.stato_cliente == "attivo",
    ).with_entities(func.count(Cliente.cliente_id)).scalar() or 0

    # Previous month new clients for comparison
    prev_month_start = (first_day_month - relativedelta(months=1))
    prev_month_end = first_day_month - timedelta(days=1)
    new_prev_month = q().filter(
        Cliente.created_at >= prev_month_start,
        Cliente.created_at <= prev_month_end,
    ).with_entities(func.count(Cliente.cliente_id)).scalar() or 0

    # ─── STATUS DISTRIBUTION ─────────────────────────────────────────── #
    status_rows = (
        q()
        .with_entities(Cliente.stato_cliente, func.count(Cliente.cliente_id))
        .group_by(Cliente.stato_cliente)
        .all()
    )
    status_distribution_acc = {}
    for s, c in status_rows:
        raw_status = (s.value if hasattr(s, "value") else str(s)) if s else "non_definito"
        normalized_status = {"insoluto": "stop", "freeze": "pausa"}.get(raw_status, raw_status)
        status_distribution_acc[normalized_status] = status_distribution_acc.get(normalized_status, 0) + c
    status_distribution = [{"status": k, "count": v} for k, v in status_distribution_acc.items()]

    # ─── TIPOLOGIA DISTRIBUTION ──────────────────────────────────────── #
    tipologia_rows = (
        q()
        .with_entities(Cliente.tipologia_cliente, func.count(Cliente.cliente_id))
        .group_by(Cliente.tipologia_cliente)
        .all()
    )
    tipologia_distribution = [
        {"tipologia": (t.value if hasattr(t, 'value') else str(t)) if t else "non_definito", "count": c}
        for t, c in tipologia_rows
    ]

    # ─── SPECIALTY SERVICES ──────────────────────────────────────────── #
    def get_service_stats(col):
        rows = (
            q()
            .with_entities(col, func.count(Cliente.cliente_id))
            .group_by(col)
            .all()
        )
        out = {}
        for s, c in rows:
            raw_status = ((s.value if hasattr(s, "value") else str(s)) if s else "non_definito")
            normalized_status = {"insoluto": "stop", "freeze": "pausa"}.get(raw_status, raw_status)
            out[normalized_status] = out.get(normalized_status, 0) + c
        return out

    nutrizione_stats = get_service_stats(Cliente.stato_nutrizione)
    coach_stats = get_service_stats(Cliente.stato_coach)
    psicologia_stats = get_service_stats(Cliente.stato_psicologia)

    # ─── MONTHLY TREND (last 12 months) ──────────────────────────────── #
    start_period = (first_day_month - relativedelta(months=11)).replace(day=1)
    monthly_rows = (
        q()
        .filter(Cliente.created_at >= start_period)
        .with_entities(
            func.date_trunc("month", Cliente.created_at).label("month"),
            func.count(Cliente.cliente_id).label("count"),
        )
        .group_by("month")
        .order_by("month")
        .all()
    )
    monthly_trend = [
        {"month": row.month.strftime("%Y-%m"), "count": row.count}
        for row in monthly_rows
    ]

    # ─── PATOLOGIE (top occurrences) ─────────────────────────────────── #
    patologie_fields = [
        ("IBS", Cliente.patologia_ibs),
        ("Reflusso", Cliente.patologia_reflusso),
        ("Gastrite", Cliente.patologia_gastrite),
        ("DCA", Cliente.patologia_dca),
        ("Insulino-resistenza", Cliente.patologia_insulino_resistenza),
        ("Diabete", Cliente.patologia_diabete),
        ("Dislipidemie", Cliente.patologia_dislipidemie),
        ("Steatosi epatica", Cliente.patologia_steatosi_epatica),
        ("Ipertensione", Cliente.patologia_ipertensione),
        ("PCOS", Cliente.patologia_pcos),
        ("Endometriosi", Cliente.patologia_endometriosi),
        ("Obesità", Cliente.patologia_obesita_sindrome),
        ("Osteoporosi", Cliente.patologia_osteoporosi),
        ("Diverticolite", Cliente.patologia_diverticolite),
        ("Crohn", Cliente.patologia_crohn),
        ("Stitichezza", Cliente.patologia_stitichezza),
        ("Tiroidee", Cliente.patologia_tiroidee),
    ]
    patologie = []
    for name, col in patologie_fields:
        count = q().filter(col == True).with_entities(func.count(Cliente.cliente_id)).scalar() or 0
        if count > 0:
            patologie.append({"name": name, "count": count})
    patologie.sort(key=lambda x: x["count"], reverse=True)

    # ─── GENDER DISTRIBUTION ─────────────────────────────────────────── #
    gender_rows = (
        q()
        .with_entities(Cliente.genere, func.count(Cliente.cliente_id))
        .group_by(Cliente.genere)
        .all()
    )
    gender_distribution = [
        {"gender": g if g else "non_definito", "count": c}
        for g, c in gender_rows
    ]

    # ─── PROGRAMMA DISTRIBUTION ──────────────────────────────────────── #
    programma_rows = (
        q()
        .filter(Cliente.programma_attuale.isnot(None), Cliente.stato_cliente == "attivo")
        .with_entities(Cliente.programma_attuale, func.count(Cliente.cliente_id))
        .group_by(Cliente.programma_attuale)
        .order_by(func.count(Cliente.cliente_id).desc())
        .limit(10)
        .all()
    )
    programma_distribution = [
        {"programma": p if p else "N/D", "count": c}
        for p, c in programma_rows
    ]

    # ─── PAYMENT METHOD DISTRIBUTION ─────────────────────────────────── #
    payment_rows = (
        q()
        .filter(Cliente.stato_cliente == "attivo")
        .with_entities(Cliente.modalita_pagamento, func.count(Cliente.cliente_id))
        .group_by(Cliente.modalita_pagamento)
        .all()
    )
    payment_distribution = [
        {"method": (m.value if hasattr(m, 'value') else str(m)) if m else "non_definito", "count": c}
        for m, c in payment_rows
    ]

    return jsonify({
        "kpi": {
            "total": total,
            "active": active,
            "ghost": ghost,
            "pausa": pausa,
            "stop": stop,
            "newMonth": new_month,
            "newPrevMonth": new_prev_month,
            "inScadenza": in_scadenza,
        },
        "statusDistribution": status_distribution,
        "tipologiaDistribution": tipologia_distribution,
        "services": {
            "nutrizione": nutrizione_stats,
            "coach": coach_stats,
            "psicologia": psicologia_stats,
        },
        "monthlyTrend": monthly_trend,
        "patologie": patologie,
        "genderDistribution": gender_distribution,
        "programmaDistribution": programma_distribution,
        "paymentDistribution": payment_distribution,
    })


# – FEEDBACK METRICS ------------------------------------------------------- #
@api_bp.route("/<int:cliente_id>/feedback-metrics", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_feedback_metrics(cliente_id: int) -> Any:
    """
    Restituisce le metriche dei feedback per un cliente specifico.
    Dati organizzati per grafici Chart.js.
    """
    from corposostenibile.models import TypeFormResponse
    _require_cliente_scope_or_403(cliente_id)
    
    # Recupera tutti i feedback del cliente ordinati per data
    responses = (
        db.session.query(TypeFormResponse)
        .filter_by(cliente_id=cliente_id)
        .order_by(TypeFormResponse.submit_date.asc())
        .all()
    )
    
    if not responses:
        return jsonify({
            "has_data": False,
            "message": "Nessun feedback disponibile per questo cliente"
        })
    
    # Prepara i dati per i grafici
    metrics_data = {
        "has_data": True,
        "typeform_count": len(responses),  # Numero di risposte
        "labels": [],  # Date dei feedback
        "metrics": {
            "weight": {"label": "Peso (kg)", "data": [], "color": "rgb(46, 204, 113)"},
            "digestion": {"label": "Digestione", "data": [], "color": "rgb(75, 192, 192)"},
            "energy": {"label": "Energia", "data": [], "color": "rgb(255, 206, 86)"},
            "strength": {"label": "Forza", "data": [], "color": "rgb(255, 99, 132)"},
            "sleep": {"label": "Sonno", "data": [], "color": "rgb(153, 102, 255)"},
            "mood": {"label": "Umore", "data": [], "color": "rgb(255, 159, 64)"},
            "motivation": {"label": "Motivazione", "data": [], "color": "rgb(46, 204, 113)"},
            "hunger": {"label": "Fame", "data": [], "color": "rgb(231, 76, 60)"},
            "progress": {"label": "Progresso", "data": [], "color": "rgb(52, 152, 219)"},
        }
    }
    
    # Estrai i dati da ogni risposta
    for response in responses:
        # Aggiungi etichetta data
        date_label = response.submit_date.strftime("%d/%m/%Y") if response.submit_date else "N/A"
        metrics_data["labels"].append(date_label)
        
        # Metriche fisiche/mentali (rating 1-10)
        metrics_data["metrics"]["weight"]["data"].append(response.weight)
        metrics_data["metrics"]["digestion"]["data"].append(response.digestion_rating)
        metrics_data["metrics"]["energy"]["data"].append(response.energy_rating)
        metrics_data["metrics"]["strength"]["data"].append(response.strength_rating)
        metrics_data["metrics"]["sleep"]["data"].append(response.sleep_rating)
        metrics_data["metrics"]["mood"]["data"].append(response.mood_rating)
        metrics_data["metrics"]["motivation"]["data"].append(response.motivation_rating)
        metrics_data["metrics"]["hunger"]["data"].append(response.hunger_rating)
        metrics_data["metrics"]["progress"]["data"].append(response.progress_rating)
    
    # Calcola statistiche aggregate
    stats = {
        "total_responses": len(responses),
        "latest_response": responses[-1].submit_date.strftime("%d/%m/%Y") if responses else None,
        "averages": {}
    }
    
    # Calcola medie per ogni metrica
    for key, metric in metrics_data["metrics"].items():
        values = [v for v in metric["data"] if v is not None]
        if values:
            if key == "weight":
                stats["averages"][key] = round(sum(values) / len(values), 1)
            else:
                stats["averages"][key] = round(sum(values) / len(values), 1)
        else:
            stats["averages"][key] = None
    
    metrics_data["stats"] = stats
    
    return jsonify(metrics_data)


@api_bp.route("/<int:cliente_id>/weekly-checks-metrics", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_weekly_checks_metrics(cliente_id: int) -> Any:
    """
    Restituisce le metriche dei Weekly Checks per un cliente specifico.
    Dati organizzati per grafici Chart.js (stesso formato di TypeForm).
    """
    from corposostenibile.models import WeeklyCheckResponse, WeeklyCheck
    _require_cliente_scope_or_403(cliente_id)

    # Recupera tutte le risposte ai weekly checks del cliente ordinate per data
    # WeeklyCheckResponse si collega a WeeklyCheck che ha cliente_id
    responses = (
        db.session.query(WeeklyCheckResponse)
        .join(WeeklyCheck, WeeklyCheckResponse.weekly_check_id == WeeklyCheck.id)
        .filter(WeeklyCheck.cliente_id == cliente_id)
        .order_by(WeeklyCheckResponse.submit_date.asc())
        .all()
    )

    if not responses:
        return jsonify({
            "has_data": False,
            "weekly_count": 0,
            "message": "Nessun weekly check disponibile per questo cliente"
        })

    # Prepara i dati per i grafici (stesso formato di TypeForm)
    metrics_data = {
        "has_data": True,
        "weekly_count": len(responses),
        "labels": [],  # Date dei check
        "metrics": {
            "digestion": {"label": "Digestione", "data": [], "color": "rgb(75, 192, 192)"},
            "energy": {"label": "Energia", "data": [], "color": "rgb(255, 206, 86)"},
            "strength": {"label": "Forza", "data": [], "color": "rgb(255, 99, 132)"},
            "sleep": {"label": "Sonno", "data": [], "color": "rgb(153, 102, 255)"},
            "mood": {"label": "Umore", "data": [], "color": "rgb(255, 159, 64)"},
            "motivation": {"label": "Motivazione", "data": [], "color": "rgb(46, 204, 113)"},
            "hunger": {"label": "Fame", "data": [], "color": "rgb(231, 76, 60)"},
            "progress": {"label": "Progresso", "data": [], "color": "rgb(52, 152, 219)"},
        },
        "weight_data": []  # Array di {date, weight}
    }

    # Estrai i dati da ogni risposta
    for response in responses:
        # Aggiungi etichetta data
        date_label = response.submit_date.strftime("%d/%m/%Y") if response.submit_date else "N/A"
        metrics_data["labels"].append(date_label)

        # Metriche fisiche/mentali (rating 0-10)
        metrics_data["metrics"]["digestion"]["data"].append(response.digestion_rating)
        metrics_data["metrics"]["energy"]["data"].append(response.energy_rating)
        metrics_data["metrics"]["strength"]["data"].append(response.strength_rating)
        metrics_data["metrics"]["sleep"]["data"].append(response.sleep_rating)
        metrics_data["metrics"]["mood"]["data"].append(response.mood_rating)
        metrics_data["metrics"]["motivation"]["data"].append(response.motivation_rating)
        metrics_data["metrics"]["hunger"]["data"].append(response.hunger_rating)
        metrics_data["metrics"]["progress"]["data"].append(response.progress_rating)

        # Peso (se disponibile)
        if response.weight:
            metrics_data["weight_data"].append({
                "date": date_label,
                "weight": float(response.weight)
            })

    return jsonify(metrics_data)


# – INITIAL CHECKS (FROM LEAD o ClientCheckAssignment) -------------------- #
@api_bp.route("/<int:cliente_id>/initial-checks", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_initial_checks(cliente_id: int) -> Any:
    """
    Restituisce i dati dei Check 1, 2 e 3 (Iniziali).
    Priorità: dati compilati dal Lead originale (se presenti), altrimenti
    fallback su ClientCheckAssignment con link pubblico da inviare.
    """
    from corposostenibile.models import CheckForm, CheckFormTypeEnum
    _require_cliente_scope_or_403(cliente_id)

    cliente = customers_repo.get_one(cliente_id, eager=True)
    base_url = current_app.config.get("BASE_URL", request.url_root.rstrip("/"))

    _empty_check = lambda: {
        "completed_at": None,
        "responses": {},
        "url": None,
        "response_count": 0,
    }
    checks_payload = {
        "check_1": _empty_check(),
        "check_2": _empty_check(),
        "check_3": _empty_check(),
    }

    has_any_data = False
    source = "none"

    # 1) Dati già compilati sul lead convertito (se presenti)
    if cliente.original_lead:
        lead = cliente.original_lead
        source = "lead"
        for idx in (1, 2, 3):
            key = f"check_{idx}"
            completed_at = getattr(lead, f"check{idx}_completed_at", None)
            responses = getattr(lead, f"check{idx}_responses", None) or {}
            if completed_at or responses:
                has_any_data = True
                checks_payload[key]["completed_at"] = completed_at.isoformat() if completed_at else None
                checks_payload[key]["responses"] = responses
                checks_payload[key]["response_count"] = 1
                # Extra metadata per check 3
                if idx == 3:
                    score = getattr(lead, "check3_score", None)
                    ctype = getattr(lead, "check3_type", None)
                    if score is not None:
                        checks_payload[key]["score"] = score
                    if ctype is not None:
                        checks_payload[key]["type"] = ctype

    # 2) Fallback/merge da ClientCheckAssignment (es. clienti creati da GHL)
    assignments = (
        db.session.query(ClientCheckAssignment)
        .join(CheckForm)
        .filter(
            ClientCheckAssignment.cliente_id == cliente_id,
            ClientCheckAssignment.is_active == True,
            CheckForm.form_type == CheckFormTypeEnum.iniziale
        )
        .options(
            selectinload(ClientCheckAssignment.form),
            selectinload(ClientCheckAssignment.responses)
        )
        .order_by(CheckForm.name)
        .all()
    )

    def _check_key_from_form_name(name):
        if not name:
            return None
        n = name.lower()
        if "check 1" in n or "anagrafica" in n:
            return "check_1"
        if "check 2" in n or "fisico" in n:
            return "check_2"
        if "check 3" in n or "psicolog" in n:
            return "check_3"
        return None

    for ass in assignments:
        key = _check_key_from_form_name(ass.form.name if ass.form else None)
        if key not in ("check_1", "check_2", "check_3"):
            continue

        latest_response = ass.responses[0] if ass.responses else None
        completed_at = None
        responses_dict = {}
        if latest_response:
            completed_at = latest_response.created_at.isoformat() if latest_response.created_at else None
            responses_dict = latest_response.get_formatted_responses()
            has_any_data = True

        public_url = f"{base_url}/client-checks/public/{ass.token}"

        # Mantieni priorità al compilato da lead; altrimenti usa assignment
        if not checks_payload[key]["completed_at"] and completed_at:
            checks_payload[key]["completed_at"] = completed_at
            checks_payload[key]["responses"] = responses_dict
            checks_payload[key]["response_count"] = 1

        # Il link pubblico va sempre valorizzato se assignment esiste (utile se non compilato)
        checks_payload[key]["url"] = public_url
        if source == "none":
            source = "client_check"

    # 3) Allegati dal Lead (foto, analisi, ecc.)
    if cliente.original_lead:
        lead = cliente.original_lead
        if lead.form_attachments and isinstance(lead.form_attachments, list):
            for att in lead.form_attachments:
                check_num = att.get("check_number")
                if check_num is None:
                    continue
                key = f"check_{check_num}"
                if key not in checks_payload:
                    continue
                if "attachments" not in checks_payload[key]:
                    checks_payload[key]["attachments"] = []
                att_path = att.get("path", "")
                # Estrai solo il filename (senza lead_files/{id}/ prefix)
                filename = att_path.split("/")[-1] if att_path else ""
                checks_payload[key]["attachments"].append({
                    "field_name": att.get("field_name", ""),
                    "filename": att.get("filename", filename),
                    "download_url": f"/v1/customers/{cliente_id}/initial-checks/attachment/{lead.id}/{filename}",
                    "size": att.get("size"),
                    "uploaded_at": att.get("uploaded_at"),
                })
                has_any_data = True

    if not has_any_data and not assignments:
        return jsonify({
            "has_data": False,
            "message": "Nessun check iniziale assegnato a questo cliente."
        })

    return jsonify({
        "has_data": True if has_any_data or assignments else False,
        "source": source,
        "checks": checks_payload
    })


@api_bp.route("/<int:cliente_id>/initial-checks/attachment/<int:lead_id>/<path:filename>", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_initial_check_attachment(cliente_id: int, lead_id: int, filename: str) -> Any:
    """Scarica un allegato (foto/file) dai check iniziali di un cliente."""
    from flask import send_file
    import os

    _require_cliente_scope_or_403(cliente_id)

    # Verifica che il lead appartenga a questo cliente
    cliente = customers_repo.get_one(cliente_id, eager=True)
    if not cliente.original_lead or cliente.original_lead.id != lead_id:
        abort(403, description="Lead non associato a questo cliente")

    # I file lead possono trovarsi in diverse posizioni:
    # 1) {root_path}/uploads/  (dove sales_form li salva)
    # 2) UPLOAD_FOLDER/        (PVC montato in produzione)
    # 3) UPLOAD_FOLDER/corposostenibile/uploads/ (copia migrata del vecchio sistema)
    upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads")
    lead_subpath = os.path.join("lead_files", str(lead_id), filename)
    candidates = [
        os.path.join(current_app.root_path, "uploads", lead_subpath),
        os.path.join(upload_folder, lead_subpath),
        os.path.join(upload_folder, "corposostenibile", "uploads", lead_subpath),
    ]

    file_path = None
    for candidate in candidates:
        if os.path.exists(candidate):
            file_path = candidate
            break

    if not file_path:
        logger.error(f"Lead attachment not found. Tried: {candidates}")
        abort(404, description="File non trovato")

    # Path traversal protection
    real_path = os.path.realpath(file_path)
    base_dir = os.path.dirname(real_path)
    if not base_dir.endswith(str(lead_id)):
        abort(403, description="Accesso negato")

    file_ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
    is_image = file_ext in ("jpg", "jpeg", "png", "gif", "webp")

    return send_file(
        file_path,
        as_attachment=not is_image,
        download_name=filename,
        mimetype=f"image/{file_ext}" if is_image else None,
    )


# --------------------------------------------------------------------------- #
#  CUSTOMER CARE INTERVENTIONS API                                            #
# --------------------------------------------------------------------------- #
@api_bp.route("/<int:cliente_id>/customer-care-interventions", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def get_customer_care_interventions(cliente_id: int):
    """Ottiene tutti gli interventi di customer care per un cliente."""
    from corposostenibile.models import CustomerCareIntervention

    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).first_or_404()

    interventions = db.session.query(CustomerCareIntervention).filter_by(
        cliente_id=cliente_id
    ).order_by(CustomerCareIntervention.intervention_date.desc()).all()

    return jsonify({
        "success": True,
        "data": [intervention.to_dict() for intervention in interventions]
    })


@api_bp.route("/<int:cliente_id>/customer-care-interventions", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def create_customer_care_intervention(cliente_id: int):
    """Crea un nuovo intervento di customer care."""
    from corposostenibile.models import CustomerCareIntervention
    from datetime import datetime

    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).first_or_404()

    data = request.get_json()

    # Validazione
    if not data.get('intervention_date'):
        return jsonify({"success": False, "error": "Data intervento richiesta"}), 400
    if not data.get('notes'):
        return jsonify({"success": False, "error": "Note richieste"}), 400

    try:
        # Parse date
        intervention_date = datetime.strptime(data['intervention_date'], '%Y-%m-%d').date()

        # Crea intervento
        intervention = CustomerCareIntervention(
            cliente_id=cliente_id,
            intervention_date=intervention_date,
            notes=data['notes'],
            loom_link=data.get('loom_link'),
            created_by_id=current_user.id
        )

        db.session.add(intervention)
        db.session.commit()

        return jsonify({
            "success": True,
            "data": intervention.to_dict(),
            "message": "Intervento registrato con successo"
        }), 201

    except ValueError as e:
        return jsonify({"success": False, "error": "Formato data non valido"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/customer-care-interventions/<int:intervention_id>", methods=["PUT"])
@permission_required(CustomerPerm.EDIT)
def update_customer_care_intervention(intervention_id: int):
    """Aggiorna un intervento di customer care esistente."""
    from corposostenibile.models import CustomerCareIntervention
    from datetime import datetime

    intervention = db.session.query(CustomerCareIntervention).filter_by(
        id=intervention_id
    ).first_or_404()

    data = request.get_json()

    try:
        if 'intervention_date' in data:
            intervention.intervention_date = datetime.strptime(
                data['intervention_date'], '%Y-%m-%d'
            ).date()

        if 'notes' in data:
            intervention.notes = data['notes']

        if 'loom_link' in data:
            intervention.loom_link = data['loom_link']

        db.session.commit()

        return jsonify({
            "success": True,
            "data": intervention.to_dict(),
            "message": "Intervento aggiornato con successo"
        })

    except ValueError:
        return jsonify({"success": False, "error": "Formato data non valido"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/customer-care-interventions/<int:intervention_id>", methods=["DELETE"])
@permission_required(CustomerPerm.EDIT)
def delete_customer_care_intervention(intervention_id: int):
    """Elimina un intervento di customer care."""
    from corposostenibile.models import CustomerCareIntervention

    intervention = db.session.query(CustomerCareIntervention).filter_by(
        id=intervention_id
    ).first_or_404()

    try:
        db.session.delete(intervention)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Intervento eliminato con successo"
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


# --------------------------------------------------------------------------- #
#  CHECK IN INTERVENTIONS API                                                 #
# --------------------------------------------------------------------------- #
@api_bp.route("/<int:cliente_id>/check-in-interventions", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def get_check_in_interventions(cliente_id: int):
    """Ottiene tutti gli interventi di check-in per un cliente."""
    from corposostenibile.models import CheckInIntervention

    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).first_or_404()

    interventions = db.session.query(CheckInIntervention).filter_by(
        cliente_id=cliente_id
    ).order_by(CheckInIntervention.intervention_date.desc()).all()

    return jsonify({
        "success": True,
        "data": [intervention.to_dict() for intervention in interventions]
    })


@api_bp.route("/<int:cliente_id>/check-in-interventions", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def create_check_in_intervention(cliente_id: int):
    """Crea un nuovo intervento di check-in."""
    from corposostenibile.models import CheckInIntervention
    from datetime import datetime

    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).first_or_404()

    data = request.get_json()

    if not data.get('intervention_date'):
        return jsonify({"success": False, "error": "Data intervento richiesta"}), 400
    if not data.get('notes'):
        return jsonify({"success": False, "error": "Note richieste"}), 400

    try:
        intervention_date = datetime.strptime(data['intervention_date'], '%Y-%m-%d').date()

        intervention = CheckInIntervention(
            cliente_id=cliente_id,
            intervention_date=intervention_date,
            notes=data['notes'],
            loom_link=data.get('loom_link'),
            created_by_id=current_user.id
        )

        db.session.add(intervention)
        db.session.commit()

        return jsonify({
            "success": True,
            "data": intervention.to_dict(),
            "message": "Check-in registrato con successo"
        }), 201

    except ValueError:
        return jsonify({"success": False, "error": "Formato data non valido"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/check-in-interventions/<int:intervention_id>", methods=["PUT"])
@permission_required(CustomerPerm.EDIT)
def update_check_in_intervention(intervention_id: int):
    """Aggiorna un intervento di check-in esistente."""
    from corposostenibile.models import CheckInIntervention
    from datetime import datetime

    intervention = db.session.query(CheckInIntervention).filter_by(
        id=intervention_id
    ).first_or_404()

    data = request.get_json()

    try:
        if 'intervention_date' in data:
            intervention.intervention_date = datetime.strptime(
                data['intervention_date'], '%Y-%m-%d'
            ).date()

        if 'notes' in data:
            intervention.notes = data['notes']

        if 'loom_link' in data:
            intervention.loom_link = data['loom_link']

        db.session.commit()

        return jsonify({
            "success": True,
            "data": intervention.to_dict(),
            "message": "Check-in aggiornato con successo"
        })

    except ValueError:
        return jsonify({"success": False, "error": "Formato data non valido"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/check-in-interventions/<int:intervention_id>", methods=["DELETE"])
@permission_required(CustomerPerm.EDIT)
def delete_check_in_intervention(intervention_id: int):
    """Elimina un intervento di check-in."""
    from corposostenibile.models import CheckInIntervention

    intervention = db.session.query(CheckInIntervention).filter_by(
        id=intervention_id
    ).first_or_404()

    try:
        db.session.delete(intervention)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Check-in eliminato con successo"
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


# --------------------------------------------------------------------------- #
#  CONTINUITY CALL INTERVENTIONS API                                          #
# --------------------------------------------------------------------------- #
@api_bp.route("/<int:cliente_id>/continuity-call-interventions", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def get_continuity_call_interventions(cliente_id: int):
    """Ottiene tutti gli interventi di continuity call per un cliente."""
    from corposostenibile.models import ContinuityCallIntervention

    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).first_or_404()

    interventions = db.session.query(ContinuityCallIntervention).filter_by(
        cliente_id=cliente_id
    ).order_by(ContinuityCallIntervention.intervention_date.desc()).all()

    return jsonify({
        "success": True,
        "data": [intervention.to_dict() for intervention in interventions]
    })


@api_bp.route("/<int:cliente_id>/continuity-call-interventions", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def create_continuity_call_intervention(cliente_id: int):
    """Crea un nuovo intervento di continuity call."""
    from corposostenibile.models import ContinuityCallIntervention
    from datetime import datetime

    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).first_or_404()

    data = request.get_json()

    if not data.get('intervention_date'):
        return jsonify({"success": False, "error": "Data intervento richiesta"}), 400
    if not data.get('notes'):
        return jsonify({"success": False, "error": "Note richieste"}), 400

    try:
        intervention_date = datetime.strptime(data['intervention_date'], '%Y-%m-%d').date()

        intervention = ContinuityCallIntervention(
            cliente_id=cliente_id,
            intervention_date=intervention_date,
            notes=data['notes'],
            loom_link=data.get('loom_link'),
            created_by_id=current_user.id
        )

        db.session.add(intervention)
        db.session.commit()

        return jsonify({
            "success": True,
            "data": intervention.to_dict(),
            "message": "Continuity call registrata con successo"
        }), 201

    except ValueError:
        return jsonify({"success": False, "error": "Formato data non valido"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/continuity-call-interventions/<int:intervention_id>", methods=["PUT"])
@permission_required(CustomerPerm.EDIT)
def update_continuity_call_intervention(intervention_id: int):
    """Aggiorna un intervento di continuity call esistente."""
    from corposostenibile.models import ContinuityCallIntervention
    from datetime import datetime

    intervention = db.session.query(ContinuityCallIntervention).filter_by(
        id=intervention_id
    ).first_or_404()

    data = request.get_json()

    try:
        if 'intervention_date' in data:
            intervention.intervention_date = datetime.strptime(
                data['intervention_date'], '%Y-%m-%d'
            ).date()

        if 'notes' in data:
            intervention.notes = data['notes']

        if 'loom_link' in data:
            intervention.loom_link = data['loom_link']

        db.session.commit()

        return jsonify({
            "success": True,
            "data": intervention.to_dict(),
            "message": "Continuity call aggiornata con successo"
        })

    except ValueError:
        return jsonify({"success": False, "error": "Formato data non valido"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/continuity-call-interventions/<int:intervention_id>", methods=["DELETE"])
@permission_required(CustomerPerm.EDIT)
def delete_continuity_call_intervention(intervention_id: int):
    """Elimina un intervento di continuity call."""
    from corposostenibile.models import ContinuityCallIntervention

    intervention = db.session.query(ContinuityCallIntervention).filter_by(
        id=intervention_id
    ).first_or_404()

    try:
        db.session.delete(intervention)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Continuity call eliminata con successo"
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


# --------------------------------------------------------------------------- #
#  GESTIONE PROFESSIONISTI - Assegnazione / Interruzione / Storico           #
# --------------------------------------------------------------------------- #

@api_bp.route("/<int:cliente_id>/professionisti/history", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def get_professionisti_history(cliente_id: int):
    """
    Ottiene lo storico completo delle assegnazioni professionisti per un cliente.
    Include sia le assegnazioni tracciate che quelle legacy (senza history).
    """
    from corposostenibile.models import ClienteProfessionistaHistory, User

    _require_cliente_scope_or_403(cliente_id)
    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).first_or_404()

    # Ottieni storico tracciato
    history_records = db.session.query(ClienteProfessionistaHistory).filter_by(
        cliente_id=cliente_id
    ).order_by(ClienteProfessionistaHistory.data_dal.desc()).all()

    # Mappa user_id -> nome per ottimizzazione
    user_ids = set()
    for h in history_records:
        user_ids.add(h.user_id)
        if h.assegnato_da_id:
            user_ids.add(h.assegnato_da_id)
        if h.interrotto_da_id:
            user_ids.add(h.interrotto_da_id)

    users_map = {}
    users_avatar_map = {}
    if user_ids:
        users = db.session.query(User).filter(User.id.in_(user_ids)).all()
        users_map = {u.id: u.full_name or u.email for u in users}
        users_avatar_map = {u.id: u.avatar_path for u in users}

    history_list = []
    tracked_user_types = set()  # (user_id, tipo) per identificare assegnazioni legacy

    for h in history_records:
        tracked_user_types.add((h.user_id, h.tipo_professionista))
        history_list.append({
            "id": h.id,
            "tipo_professionista": h.tipo_professionista,
            "professionista_nome": users_map.get(h.user_id, "Sconosciuto"),
            "professionista_id": h.user_id,
            "avatar_path": users_avatar_map.get(h.user_id),
            "data_dal": h.data_dal.strftime("%d/%m/%Y") if h.data_dal else None,
            "data_al": h.data_al.strftime("%d/%m/%Y") if h.data_al else None,
            "motivazione_aggiunta": h.motivazione_aggiunta,
            "motivazione_interruzione": h.motivazione_interruzione,
            "assegnato_da": users_map.get(h.assegnato_da_id) if h.assegnato_da_id else None,
            "interrotto_da": users_map.get(h.interrotto_da_id) if h.interrotto_da_id else None,
            "is_active": h.is_active,
            "has_history": True,
        })

    # Aggiungi assegnazioni legacy (senza history record attivo)
    legacy_assignments = []

    # Nutrizionisti
    for n in cliente.nutrizionisti_multipli:
        if (n.id, "nutrizionista") not in tracked_user_types or not any(
            h["professionista_id"] == n.id and h["tipo_professionista"] == "nutrizionista" and h["is_active"]
            for h in history_list
        ):
            legacy_assignments.append({
                "id": None,
                "tipo_professionista": "nutrizionista",
                "professionista_nome": n.full_name or n.email,
                "professionista_id": n.id,
                "avatar_path": n.avatar_path,
                "data_dal": None,
                "data_al": None,
                "motivazione_aggiunta": None,
                "motivazione_interruzione": None,
                "assegnato_da": None,
                "interrotto_da": None,
                "is_active": True,
                "has_history": False,
            })

    # Coach
    for c in cliente.coaches_multipli:
        if (c.id, "coach") not in tracked_user_types or not any(
            h["professionista_id"] == c.id and h["tipo_professionista"] == "coach" and h["is_active"]
            for h in history_list
        ):
            legacy_assignments.append({
                "id": None,
                "tipo_professionista": "coach",
                "professionista_nome": c.full_name or c.email,
                "professionista_id": c.id,
                "avatar_path": c.avatar_path,
                "data_dal": None,
                "data_al": None,
                "motivazione_aggiunta": None,
                "motivazione_interruzione": None,
                "assegnato_da": None,
                "interrotto_da": None,
                "is_active": True,
                "has_history": False,
            })

    # Psicologi
    for p in cliente.psicologi_multipli:
        if (p.id, "psicologa") not in tracked_user_types or not any(
            h["professionista_id"] == p.id and h["tipo_professionista"] == "psicologa" and h["is_active"]
            for h in history_list
        ):
            legacy_assignments.append({
                "id": None,
                "tipo_professionista": "psicologa",
                "professionista_nome": p.full_name or p.email,
                "professionista_id": p.id,
                "avatar_path": p.avatar_path,
                "data_dal": None,
                "data_al": None,
                "motivazione_aggiunta": None,
                "motivazione_interruzione": None,
                "assegnato_da": None,
                "interrotto_da": None,
                "is_active": True,
                "has_history": False,
            })

    # Health Manager (singolo)
    if cliente.health_manager_user:
        hm_user = cliente.health_manager_user
        if not any(
            h["professionista_id"] == hm_user.id and h["tipo_professionista"] == "health_manager" and h["is_active"]
            for h in history_list
        ):
            legacy_assignments.append({
                "id": None,
                "tipo_professionista": "health_manager",
                "professionista_nome": hm_user.full_name or hm_user.email,
                "professionista_id": hm_user.id,
                "avatar_path": hm_user.avatar_path,
                "data_dal": None,
                "data_al": None,
                "motivazione_aggiunta": None,
                "motivazione_interruzione": None,
                "assegnato_da": None,
                "interrotto_da": None,
                "is_active": True,
                "has_history": False,
            })

    # Combina e ordina per data (legacy senza data vanno in fondo)
    all_history = history_list + legacy_assignments

    return jsonify({"history": all_history})


@api_bp.route("/<int:cliente_id>/professionisti/assign", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def assign_professionista(cliente_id: int):
    """
    Assegna un professionista a un cliente.
    Crea un record in ClienteProfessionistaHistory e aggiunge alla relazione many-to-many.
    """
    from corposostenibile.models import ClienteProfessionistaHistory, User
    from flask_login import current_user

    _require_cliente_scope_or_403(cliente_id)
    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).first_or_404()
    if _is_professionista_standard(current_user):
        return jsonify({"ok": False, "error": "Non autorizzato ad assegnare professionisti"}), 403
    data = request.get_json() or {}

    # Validazione campi obbligatori
    tipo_professionista = data.get("tipo_professionista")
    user_id = data.get("user_id")
    data_dal_str = data.get("data_dal")
    motivazione = data.get("motivazione_aggiunta")

    if not all([tipo_professionista, user_id, data_dal_str, motivazione]):
        return jsonify({
            "ok": False,
            "error": "Campi obbligatori: tipo_professionista, user_id, data_dal, motivazione_aggiunta"
        }), 400

    # Valida tipo professionista
    valid_types = ["nutrizionista", "coach", "psicologa", "medico", "health_manager", "consulente"]
    if tipo_professionista not in valid_types:
        return jsonify({
            "ok": False,
            "error": f"Tipo professionista non valido. Valori accettati: {valid_types}"
        }), 400

    # Verifica che l'utente esista
    user = db.session.query(User).filter_by(id=user_id).first()
    if not user:
        return jsonify({"ok": False, "error": "Utente non trovato"}), 404
    _require_team_leader_assignment_scope_or_403(current_user, tipo_professionista, int(user_id))

    # Parse data
    try:
        data_dal = datetime.strptime(data_dal_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"ok": False, "error": "Formato data non valido (usa YYYY-MM-DD)"}), 400

    try:
        # Crea record history
        history = ClienteProfessionistaHistory(
            cliente_id=cliente_id,
            user_id=user_id,
            tipo_professionista=tipo_professionista,
            data_dal=data_dal,
            motivazione_aggiunta=motivazione,
            assegnato_da_id=current_user.id if current_user.is_authenticated else None,
            is_active=True,
        )
        db.session.add(history)

        # Aggiungi alla relazione many-to-many appropriata
        if tipo_professionista == "nutrizionista":
            if user not in cliente.nutrizionisti_multipli:
                cliente.nutrizionisti_multipli.append(user)
        elif tipo_professionista == "coach":
            if user not in cliente.coaches_multipli:
                cliente.coaches_multipli.append(user)
        elif tipo_professionista == "psicologa":
            if user not in cliente.psicologi_multipli:
                cliente.psicologi_multipli.append(user)
        elif tipo_professionista == "consulente":
            if user not in cliente.consulenti_multipli:
                cliente.consulenti_multipli.append(user)
        elif tipo_professionista == "health_manager":
            cliente.health_manager_id = user_id

        db.session.commit()

        return jsonify({
            "ok": True,
            "message": "Professionista assegnato con successo",
            "history_id": history.id
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500


@api_bp.route("/<int:cliente_id>/professionisti/<int:history_id>/interrupt", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def interrupt_professionista(cliente_id: int, history_id: int):
    """
    Interrompe un'assegnazione professionista tracciata.
    """
    from corposostenibile.models import ClienteProfessionistaHistory, User
    from flask_login import current_user

    _require_cliente_scope_or_403(cliente_id)
    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).first_or_404()
    if _is_professionista_standard(current_user):
        return jsonify({"ok": False, "error": "Non autorizzato a interrompere assegnazioni"}), 403
    history = db.session.query(ClienteProfessionistaHistory).filter_by(
        id=history_id,
        cliente_id=cliente_id,
        is_active=True
    ).first_or_404()
    _require_team_leader_assignment_scope_or_403(current_user, history.tipo_professionista, int(history.user_id))

    data = request.get_json() or {}
    motivazione = data.get("motivazione_interruzione")
    data_al_str = data.get("data_al")

    if not motivazione:
        return jsonify({"ok": False, "error": "Motivazione interruzione obbligatoria"}), 400

    try:
        # Parse data fine (default: oggi)
        data_al = date.today()
        if data_al_str:
            data_al = datetime.strptime(data_al_str, "%Y-%m-%d").date()

        # Aggiorna record history
        history.is_active = False
        history.data_al = data_al
        history.motivazione_interruzione = motivazione
        history.interrotto_da_id = current_user.id if current_user.is_authenticated else None

        # Rimuovi dalla relazione many-to-many
        user = db.session.query(User).filter_by(id=history.user_id).first()
        if user:
            if history.tipo_professionista == "nutrizionista":
                if user in cliente.nutrizionisti_multipli:
                    cliente.nutrizionisti_multipli.remove(user)
            elif history.tipo_professionista == "coach":
                if user in cliente.coaches_multipli:
                    cliente.coaches_multipli.remove(user)
            elif history.tipo_professionista == "psicologa":
                if user in cliente.psicologi_multipli:
                    cliente.psicologi_multipli.remove(user)
            elif history.tipo_professionista == "consulente":
                if user in cliente.consulenti_multipli:
                    cliente.consulenti_multipli.remove(user)
            elif history.tipo_professionista == "health_manager":
                if cliente.health_manager_id == history.user_id:
                    cliente.health_manager_id = None

        db.session.commit()

        return jsonify({
            "ok": True,
            "message": "Assegnazione interrotta con successo"
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500


@api_bp.route("/<int:cliente_id>/professionisti/legacy/interrupt", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def interrupt_legacy_professionista(cliente_id: int):
    """
    Interrompe un'assegnazione legacy (senza record history).
    Crea un record history con data_dal = oggi e lo marca come interrotto.
    """
    from corposostenibile.models import ClienteProfessionistaHistory, User
    from flask_login import current_user

    _require_cliente_scope_or_403(cliente_id)
    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).first_or_404()
    if _is_professionista_standard(current_user):
        return jsonify({"ok": False, "error": "Non autorizzato a interrompere assegnazioni"}), 403
    data = request.get_json() or {}

    user_id = data.get("user_id")
    tipo_professionista = data.get("tipo_professionista")
    motivazione = data.get("motivazione_interruzione")

    if not all([user_id, tipo_professionista, motivazione]):
        return jsonify({
            "ok": False,
            "error": "Campi obbligatori: user_id, tipo_professionista, motivazione_interruzione"
        }), 400

    user = db.session.query(User).filter_by(id=user_id).first()
    if not user:
        return jsonify({"ok": False, "error": "Utente non trovato"}), 404
    _require_team_leader_assignment_scope_or_403(current_user, tipo_professionista, int(user_id))

    try:
        today = date.today()

        # Crea record history già interrotto
        history = ClienteProfessionistaHistory(
            cliente_id=cliente_id,
            user_id=user_id,
            tipo_professionista=tipo_professionista,
            data_dal=today,  # Non conosciamo la data reale di inizio
            motivazione_aggiunta="Assegnazione legacy (data inizio sconosciuta)",
            assegnato_da_id=current_user.id,
            is_active=False,
            data_al=today,
            motivazione_interruzione=motivazione,
            interrotto_da_id=current_user.id if current_user.is_authenticated else None,
        )
        db.session.add(history)

        # Rimuovi dalla relazione many-to-many
        if tipo_professionista == "nutrizionista":
            if user in cliente.nutrizionisti_multipli:
                cliente.nutrizionisti_multipli.remove(user)
        elif tipo_professionista == "coach":
            if user in cliente.coaches_multipli:
                cliente.coaches_multipli.remove(user)
        elif tipo_professionista == "psicologa":
            if user in cliente.psicologi_multipli:
                cliente.psicologi_multipli.remove(user)
        elif tipo_professionista == "consulente":
            if user in cliente.consulenti_multipli:
                cliente.consulenti_multipli.remove(user)
        elif tipo_professionista == "health_manager":
            if cliente.health_manager_id == user_id:
                cliente.health_manager_id = None

        db.session.commit()

        return jsonify({
            "ok": True,
            "message": "Assegnazione legacy interrotta con successo"
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500


# --------------------------------------------------------------------------- #
#  LISTA CLIENTI IN SCADENZA (< 30 gg)                                        #
# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #
#  RECUPERO GHOST - Clienti in stato ghost da recuperare                     #
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
#  IN SCADENZA - Clienti con rinnovo entro 30 giorni                         #
# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #
#  Helper functions per dashboard 360°                                        #
# --------------------------------------------------------------------------- #
def _get_stati_distribution(filters=None):
    """Ottiene distribuzione stati cliente."""
    query = db.session.query(
        Cliente.stato_cliente,
        func.count(Cliente.cliente_id).label('count')
    )
    
    if filters:
        query = _apply_dashboard_filters(query, filters)
    
    results = query.group_by(Cliente.stato_cliente).all()
    
    return [r.count for r in results]

def _get_tipologia_distribution(filters=None):
    """Ottiene distribuzione tipologia clienti."""
    query = db.session.query(
        Cliente.tipologia_cliente,
        func.count(Cliente.cliente_id).label('count')
    )
    
    if filters:
        query = _apply_dashboard_filters(query, filters)
    
    results = query.group_by(Cliente.tipologia_cliente).all()
    
    return [r.count for r in results]

def _get_team_distribution(filters=None):
    """Ottiene distribuzione per team."""
    query = db.session.query(
        Cliente.di_team,
        func.count(Cliente.cliente_id).label('count')
    )
    
    if filters:
        query = _apply_dashboard_filters(query, filters)
    
    results = query.group_by(Cliente.di_team).all()
    
    return [r.count for r in results]

def _get_pagamento_distribution(filters=None):
    """Ottiene distribuzione modalità pagamento."""
    query = db.session.query(
        Cliente.modalita_pagamento,
        func.count(Cliente.cliente_id).label('count')
    )
    
    if filters:
        query = _apply_dashboard_filters(query, filters)
    
    results = query.group_by(Cliente.modalita_pagamento).all()
    
    return [r.count for r in results]

def _get_check_saltati_distribution(filters=None):
    """Ottiene distribuzione check saltati."""
    query = db.session.query(
        Cliente.check_saltati,
        func.count(Cliente.cliente_id).label('count')
    )
    
    if filters:
        query = _apply_dashboard_filters(query, filters)
    
    results = query.group_by(Cliente.check_saltati).all()
    
    return [r.count for r in results]

def _get_wellness_trend(filters=None):
    """Ottiene trend wellness nel tempo."""
    from corposostenibile.models import TypeFormResponse
    
    # Query per ottenere medie wellness per settimana
    query = db.session.query(
        func.date_trunc('week', TypeFormResponse.submit_date).label('week'),
        func.avg(TypeFormResponse.energy_rating).label('energy'),
        func.avg(TypeFormResponse.mood_rating).label('mood'),
        func.avg(TypeFormResponse.sleep_rating).label('sleep'),
        func.avg(TypeFormResponse.motivation_rating).label('motivation')
    ).join(Cliente, TypeFormResponse.cliente_id == Cliente.cliente_id)
    
    # Applica filtro per ruolo
    query = apply_role_filtering(query)
    
    if filters and filters.get('dateRange'):
        # Applica filtro date
        pass
    
    results = query.group_by('week').order_by('week').limit(12).all()
    
    return {
        'labels': [r.week.strftime('%d/%m') for r in results],
        'energy': [float(r.energy or 0) for r in results],
        'mood': [float(r.mood or 0) for r in results],
        'sleep': [float(r.sleep or 0) for r in results],
        'motivation': [float(r.motivation or 0) for r in results]
    }

def _apply_dashboard_filters(query, filters):
    """Applica filtri alla query."""
    # Applica filtro per ruolo
    query = apply_role_filtering(query)
    
    if filters.get('statoCliente'):
        query = query.filter(Cliente.stato_cliente.in_(filters['statoCliente']))
    
    if filters.get('team'):
        query = query.filter(Cliente.di_team.in_(filters['team']))
    
    if filters.get('tipologia'):
        query = query.filter(Cliente.tipologia_cliente.in_(filters['tipologia']))
    
    return query


# --------------------------------------------------------------------------- #
#  CALL BONUS ROUTES                                                          #
# --------------------------------------------------------------------------- #

@customers_bp.route("/<int:cliente_id>/call-bonus", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def create_call_bonus_route(cliente_id: int):
    """Crea una nuova richiesta di call bonus per un cliente."""
    from .services import create_call_bonus
    from flask_login import current_user

    cliente = db.session.get(Cliente, cliente_id)
    if not cliente:
        return jsonify({"success": False, "error": "Cliente non trovato."}), HTTPStatus.NOT_FOUND

    # Estrai tipo e ID dal campo professionista_data (formato: "tipo_id")
    professionista_data = request.form.get('professionista_data', '')
    data_richiesta_str = request.form.get('data_richiesta', '')

    if not professionista_data:
        return jsonify({"success": False, "error": "Seleziona un professionista."}), HTTPStatus.BAD_REQUEST

    try:
        # Splitta il valore per ottenere tipo e ID
        tipo_str, professionista_id_str = professionista_data.split('_', 1)
        professionista_id = int(professionista_id_str)
        tipo_professionista = TipoProfessionistaEnum(tipo_str)

        # Converti la data
        from datetime import datetime
        data_richiesta = datetime.strptime(data_richiesta_str, '%Y-%m-%d').date() if data_richiesta_str else date.today()

        # Crea la call bonus
        call_bonus = create_call_bonus(
            cliente_id=cliente_id,
            professionista_id=professionista_id,
            tipo_professionista=tipo_professionista,
            created_by_user=current_user,
            data_richiesta=data_richiesta
        )
        return jsonify({
            "success": True,
            "message": "Call bonus creata con successo.",
            "call_bonus_id": call_bonus.id,
        }), HTTPStatus.CREATED
    except ValueError as e:
        return jsonify({"success": False, "error": f"Errore nei dati del form: {str(e)}"}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        return jsonify({"success": False, "error": f"Errore nella creazione della call bonus: {str(e)}"}), HTTPStatus.BAD_REQUEST


@customers_bp.route("/call-bonus/<int:call_bonus_id>/response", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def update_call_bonus_response_route(call_bonus_id: int):
    """Aggiorna la risposta del cliente (accettata/rifiutata)."""
    from .forms import CallBonusResponseForm
    from .services import update_call_bonus_response

    form = CallBonusResponseForm()

    if form.validate_on_submit():
        try:
            call_bonus = update_call_bonus_response(
                call_bonus_id=call_bonus_id,
                status=form.status.data,
                motivazione_rifiuto=form.motivazione_rifiuto.data if form.status.data == 'rifiutata' else None,
                data_risposta=form.data_risposta.data
            )
            return jsonify({
                "success": True,
                "message": f"Risposta cliente salvata: {form.status.data.upper()}",
                "call_bonus_id": call_bonus.id,
                "cliente_id": call_bonus.cliente_id,
            }), HTTPStatus.OK
        except Exception as e:
            return jsonify({"success": False, "error": f"Errore nell'aggiornamento della risposta: {str(e)}"}), HTTPStatus.BAD_REQUEST
    else:
        return jsonify({"success": False, "errors": form.errors}), HTTPStatus.BAD_REQUEST


@customers_bp.route("/call-bonus/<int:call_bonus_id>/hm-confirm", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def update_call_bonus_hm_confirm_route(call_bonus_id: int):
    """Conferma/gestione health manager della call bonus."""
    from .forms import CallBonusHMConfirmForm
    from .services import update_call_bonus_hm_confirm
    from flask_login import current_user

    form = CallBonusHMConfirmForm()

    if form.validate_on_submit():
        try:
            call_bonus = update_call_bonus_hm_confirm(
                call_bonus_id=call_bonus_id,
                confermata_hm=form.confermata_hm.data,
                note_hm=form.note_hm.data,
                hm_user=current_user,
                data_conferma_hm=form.data_conferma_hm.data
            )
            esito = "CONFERMATA" if form.confermata_hm.data else "NON ANDATA A BUON FINE"
            return jsonify({
                "success": True,
                "message": f"Call bonus {esito} dall'Health Manager",
                "call_bonus_id": call_bonus.id,
            }), HTTPStatus.OK
        except Exception as e:
            return jsonify({"success": False, "error": f"Errore nella conferma HM: {str(e)}"}), HTTPStatus.BAD_REQUEST
    else:
        return jsonify({"success": False, "errors": form.errors}), HTTPStatus.BAD_REQUEST




# --------------------------------------------------------------------------- #
#  DIET MANAGEMENT API (Gestione Storico Diete)                              #
# --------------------------------------------------------------------------- #

def _can_manage_meal_plans(cliente: Cliente) -> bool:
    """True se l'utente corrente può creare/chiudere piani del cliente.
    Ammette admin oppure nutrizionisti assegnati al cliente.
    """
    if current_user.is_admin:
        return True
    # Utenti in dipartimento nutrizione assegnati al cliente
    try:
        if getattr(cliente, 'nutrizionisti_multipli', None):
            return any(n.id == current_user.id for n in cliente.nutrizionisti_multipli)
        # fallback legacy: attributo enum/stringa
        nutritionist_name = (current_user.full_name or '').lower().replace(' ', '_')
        return bool(getattr(cliente, 'nutrizionista', None)) and nutritionist_name in cliente.nutrizionista
    except Exception:
        return False


@customers_bp.route("/<int:cliente_id>/diet/add", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def api_diet_add(cliente_id: int):
    """Aggiunge una nuova dieta (continuazione normale del periodo).

    Chiude il piano attivo (se necessario), crea nuovo MealPlan con start_date
    default (end_date precedente + 1 giorno), is_active=True.
    """
    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).one_or_404()
    if not _can_manage_meal_plans(cliente):
        abort(403)

    payload = request.get_json(silent=True) or {}

    # Parse date
    start_str = payload.get("start_date")
    end_str = payload.get("end_date")
    piano_alimentare = payload.get("piano_alimentare", "").strip()
    notes = payload.get("notes", "").strip()

    try:
        if start_str:
            start_date = datetime.fromisoformat(start_str).date()
        else:
            # Calcola start_date default dal piano precedente
            start_date = MealPlan.calculate_next_start_date(cliente_id) or date.today()

        if not end_str:
            return jsonify({"error": "end_date è obbligatorio"}), HTTPStatus.BAD_REQUEST
        end_date = datetime.fromisoformat(end_str).date()
    except Exception as exc:
        return jsonify({"error": f"Date non valide: {exc}"}), HTTPStatus.BAD_REQUEST

    # Validazione date
    if start_date >= end_date:
        return jsonify({"error": "start_date deve essere precedente a end_date"}), HTTPStatus.BAD_REQUEST

    # Chiudi piano attivo se esiste
    active_plan = (
        db.session.query(MealPlan)
        .filter_by(cliente_id=cliente_id, is_active=True)
        .first()
    )

    if active_plan:
        # Verifica che il piano attivo abbia end_date
        if not active_plan.end_date:
            # Imposta end_date al giorno prima di start_date
            active_plan.end_date = start_date - timedelta(days=1)
        elif active_plan.end_date >= start_date:
            # Aggiorna end_date se necessario
            active_plan.end_date = start_date - timedelta(days=1)
        active_plan.is_active = False
        db.session.flush()  # Commit changes to active plan before validation

    # Crea nuovo piano
    name = payload.get("name", "").strip() or f"Dieta {start_date.strftime('%d/%m/%Y')}"

    plan = MealPlan(
        cliente_id=cliente_id,
        created_by_id=getattr(current_user, "id", None),
        name=name,
        start_date=start_date,
        end_date=end_date,
        piano_alimentare=piano_alimentare,
        notes=notes,
        is_active=True,
        target_calories=payload.get("target_calories"),
        target_proteins=payload.get("target_proteins"),
        target_carbohydrates=payload.get("target_carbohydrates"),
        target_fats=payload.get("target_fats"),
    )

    # Valida sovrapposizioni
    try:
        plan.validate_no_overlap()
    except ValueError as e:
        return jsonify({"error": str(e)}), HTTPStatus.BAD_REQUEST

    db.session.add(plan)

    # Aggiorna campi legacy sul Cliente per compatibilità
    cliente.dieta_dal = start_date
    cliente.nuova_dieta_dal = end_date

    db.session.commit()

    return jsonify({
        "ok": True,
        "plan_id": plan.id,
        "message": "Dieta aggiunta con successo"
    }), HTTPStatus.CREATED


@customers_bp.route("/<int:cliente_id>/diet/change", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def api_diet_change(cliente_id: int):
    """Cambia dieta esistente (modifica/chiusura con flessibilità date).

    Permette modificare date (soprattutto end_date), tipo, piano.
    Valida che non ci siano sovrapposizioni.
    """
    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).one_or_404()
    if not _can_manage_meal_plans(cliente):
        abort(403)

    payload = request.get_json(silent=True) or {}

    # Identifica piano da modificare
    plan_id = payload.get("plan_id")
    if not plan_id:
        return jsonify({"error": "plan_id è obbligatorio"}), HTTPStatus.BAD_REQUEST

    plan = db.session.query(MealPlan).filter_by(id=plan_id, cliente_id=cliente_id).one_or_404()

    # Parse modifiche
    change_reason = payload.get("change_reason", "").strip()

    # Modalità 1: Modifica piano esistente
    if payload.get("start_date") or payload.get("end_date") or payload.get("piano_alimentare"):
        # Aggiorna campi
        if payload.get("start_date"):
            try:
                plan.start_date = datetime.fromisoformat(payload["start_date"]).date()
            except Exception as exc:
                return jsonify({"error": f"start_date non valida: {exc}"}), HTTPStatus.BAD_REQUEST

        if payload.get("end_date"):
            try:
                plan.end_date = datetime.fromisoformat(payload["end_date"]).date()
            except Exception as exc:
                return jsonify({"error": f"end_date non valida: {exc}"}), HTTPStatus.BAD_REQUEST

        if plan.start_date >= plan.end_date:
            return jsonify({"error": "start_date deve essere precedente a end_date"}), HTTPStatus.BAD_REQUEST

        if "piano_alimentare" in payload:
            plan.piano_alimentare = payload.get("piano_alimentare", "").strip()

        if "notes" in payload:
            plan.notes = payload.get("notes", "").strip()

        if "is_active" in payload:
            plan.is_active = bool(payload.get("is_active"))

        plan.changed_by_id = getattr(current_user, "id", None)
        plan.change_reason = change_reason

        # Valida sovrapposizioni (escludendo questo piano)
        try:
            plan.validate_no_overlap(exclude_id=plan.id)
        except ValueError as e:
            return jsonify({"error": str(e)}), HTTPStatus.BAD_REQUEST

        # Aggiorna campi legacy se è il piano attivo
        if plan.is_active:
            cliente.dieta_dal = plan.start_date
            cliente.nuova_dieta_dal = plan.end_date
            if plan.tipo_attuale:
                cliente.tipo_attuale = plan.tipo_attuale

        db.session.commit()

        return jsonify({
            "ok": True,
            "plan_id": plan.id,
            "message": "Piano aggiornato con successo"
        }), HTTPStatus.OK

    return jsonify({"error": "Nessuna modifica specificata"}), HTTPStatus.BAD_REQUEST


@customers_bp.route("/<int:cliente_id>/diet/history", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_diet_history(cliente_id: int):
    """Restituisce lo storico completo delle diete per il cliente."""
    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).one_or_404()

    plans = (
        db.session.query(MealPlan)
        .filter_by(cliente_id=cliente_id)
        .order_by(MealPlan.start_date.desc())
        .all()
    )

    def _serialize(plan: MealPlan):
        return {
            "id": plan.id,
            "name": plan.name,
            "start_date": plan.start_date.isoformat() if plan.start_date else None,
            "end_date": plan.end_date.isoformat() if plan.end_date else None,
            "is_active": bool(plan.is_active),
            "piano_alimentare": plan.piano_alimentare,
            "notes": plan.notes,
            "change_reason": plan.change_reason,
            "duration_days": plan.duration_days,
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
            "created_by": plan.created_by.full_name if plan.created_by else None,
        }

    # Aggiungi piano legacy se esiste
    legacy_plan = None
    if cliente.dieta_dal:
        legacy_plan = {
            "id": None,
            "name": "Piano Legacy (da vecchi campi)",
            "start_date": cliente.dieta_dal.isoformat() if cliente.dieta_dal else None,
            "end_date": cliente.nuova_dieta_dal.isoformat() if cliente.nuova_dieta_dal else None,
            "is_active": False,
            "piano_alimentare": cliente.piano_alimentare if hasattr(cliente, 'piano_alimentare') else None,
            "notes": "Dati legacy dalla vecchia gestione",
            "is_legacy": True,
        }

    plans_data = [_serialize(p) for p in plans]

    # Aggiungi piano legacy solo se non ci sono MealPlan o se le date non si sovrappongono
    if legacy_plan and (not plans_data or all(p["start_date"] != legacy_plan["start_date"] for p in plans_data)):
        plans_data.append(legacy_plan)

    return jsonify({
        "plans": plans_data,
        "can_manage": _can_manage_meal_plans(cliente),
    })


# --------------------------------------------------------------------------- #
#  TRAINING PLANS API                                                         #
# --------------------------------------------------------------------------- #

def _can_manage_training_plans(cliente: Cliente) -> bool:
    """True se l'utente corrente può creare/chiudere piani allenamento del cliente."""
    if current_user.is_admin:
        return True
    try:
        if getattr(cliente, 'coaches_multipli', None):
            return any(c.id == current_user.id for c in cliente.coaches_multipli)
        return False
    except Exception:
        return False


@customers_bp.route("/<int:cliente_id>/training/add", methods=["POST"])
@csrf.exempt
@permission_required(CustomerPerm.EDIT)
def api_training_add(cliente_id: int):
    """Aggiunge un nuovo piano allenamento con upload PDF."""
    from werkzeug.utils import secure_filename
    import os
    from flask import current_app

    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).one_or_404()
    _require_service_scope_or_403(cliente_id, "coaching")
    if not _can_manage_training_plans(cliente):
        abort(403)

    # Gestione multipart form data invece di JSON
    start_str = request.form.get("start_date")
    end_str = request.form.get("end_date")
    notes = request.form.get("notes", "").strip()

    # Gestione upload file PDF
    piano_allenamento_file_path = None
    if 'piano_allenamento_file' in request.files:
        file = request.files['piano_allenamento_file']
        if file and file.filename:
            # Validazione file
            if not file.filename.lower().endswith('.pdf'):
                return jsonify({"error": "Il file deve essere in formato PDF"}), HTTPStatus.BAD_REQUEST

            # Sanitizza filename
            filename = secure_filename(file.filename)
            if not filename:
                return jsonify({"error": "Nome file non valido"}), HTTPStatus.BAD_REQUEST

            # Crea directory: uploads/training_plans/{cliente_id}/
            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
            training_folder = os.path.join(upload_folder, 'training_plans', str(cliente_id))
            os.makedirs(training_folder, exist_ok=True)

            # Genera filename unico con timestamp
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            name, ext = os.path.splitext(filename)
            final_filename = f"training_{timestamp}_{name}{ext}"
            filepath = os.path.join(training_folder, final_filename)

            try:
                file.save(filepath)
                # Salva path relativo per il database
                piano_allenamento_file_path = f"training_plans/{cliente_id}/{final_filename}"
                logger.info(f"File piano allenamento salvato: {piano_allenamento_file_path}")
            except Exception as e:
                logger.exception(f"Errore salvataggio file: {e}")
                return jsonify({"error": f"Errore durante il salvataggio del file: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
    else:
        return jsonify({"error": "File PDF del piano allenamento è obbligatorio"}), HTTPStatus.BAD_REQUEST

    try:
        if start_str:
            start_date = datetime.fromisoformat(start_str).date()
        else:
            start_date = TrainingPlan.calculate_next_start_date(cliente_id) or date.today()

        if not end_str:
            return jsonify({"error": "end_date è obbligatorio"}), HTTPStatus.BAD_REQUEST
        end_date = datetime.fromisoformat(end_str).date()
    except Exception as exc:
        return jsonify({"error": f"Date non valide: {exc}"}), HTTPStatus.BAD_REQUEST

    if start_date >= end_date:
        return jsonify({"error": "start_date deve essere precedente a end_date"}), HTTPStatus.BAD_REQUEST

    active_plan = db.session.query(TrainingPlan).filter_by(cliente_id=cliente_id, is_active=True).first()
    if active_plan:
        if not active_plan.end_date:
            active_plan.end_date = start_date - timedelta(days=1)
        elif active_plan.end_date >= start_date:
            active_plan.end_date = start_date - timedelta(days=1)
        active_plan.is_active = False
        db.session.flush()

    name = request.form.get("name", "").strip() or f"Allenamento {start_date.strftime('%d/%m/%Y')}"
    plan = TrainingPlan(
        cliente_id=cliente_id,
        created_by_id=getattr(current_user, "id", None),
        name=name,
        start_date=start_date,
        end_date=end_date,
        piano_allenamento=None,  # Deprecato, ora usiamo il file
        piano_allenamento_file_path=piano_allenamento_file_path,
        notes=notes,
        is_active=True,
    )

    try:
        plan.validate_no_overlap()
    except ValueError as e:
        return jsonify({"error": str(e)}), HTTPStatus.BAD_REQUEST

    db.session.add(plan)
    cliente.allenamento_dal = start_date
    cliente.nuovo_allenamento_il = end_date
    db.session.commit()

    return jsonify({"ok": True, "plan_id": plan.id, "message": "Allenamento aggiunto con successo"}), HTTPStatus.CREATED


@customers_bp.route("/<int:cliente_id>/training/change", methods=["POST"])
@csrf.exempt
@permission_required(CustomerPerm.EDIT)
def api_training_change(cliente_id: int):
    """Cambia piano allenamento esistente."""
    from werkzeug.utils import secure_filename
    import os
    from flask import current_app

    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).one_or_404()
    _require_service_scope_or_403(cliente_id, "coaching")
    if not _can_manage_training_plans(cliente):
        abort(403)

    # Gestione multipart form data invece di JSON
    plan_id = request.form.get("plan_id")
    if not plan_id:
        return jsonify({"error": "plan_id è obbligatorio"}), HTTPStatus.BAD_REQUEST

    try:
        plan_id = int(plan_id)
    except ValueError:
        return jsonify({"error": "plan_id non valido"}), HTTPStatus.BAD_REQUEST

    plan = db.session.query(TrainingPlan).filter_by(id=plan_id, cliente_id=cliente_id).one_or_404()
    change_reason = request.form.get("change_reason", "").strip()

    # Verifica se c'è almeno un campo da modificare
    has_changes = False

    # Gestione date
    start_str = request.form.get("start_date")
    end_str = request.form.get("end_date")

    if start_str:
        try:
            new_start_date = datetime.fromisoformat(start_str).date()
            plan.start_date = new_start_date
            has_changes = True
        except Exception as exc:
            return jsonify({"error": f"start_date non valida: {exc}"}), HTTPStatus.BAD_REQUEST

    if end_str:
        try:
            new_end_date = datetime.fromisoformat(end_str).date()
            plan.end_date = new_end_date
            has_changes = True
        except Exception as exc:
            return jsonify({"error": f"end_date non valida: {exc}"}), HTTPStatus.BAD_REQUEST

    if plan.start_date >= plan.end_date:
        return jsonify({"error": "start_date deve essere precedente a end_date"}), HTTPStatus.BAD_REQUEST

    # Gestione upload file PDF (se presente)
    if 'piano_allenamento_file' in request.files:
        file = request.files['piano_allenamento_file']
        if file and file.filename:
            # Validazione file
            if not file.filename.lower().endswith('.pdf'):
                return jsonify({"error": "Il file deve essere in formato PDF"}), HTTPStatus.BAD_REQUEST

            # Sanitizza filename
            filename = secure_filename(file.filename)
            if not filename:
                return jsonify({"error": "Nome file non valido"}), HTTPStatus.BAD_REQUEST

            # Crea directory: uploads/training_plans/{cliente_id}/
            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
            training_folder = os.path.join(upload_folder, 'training_plans', str(cliente_id))
            os.makedirs(training_folder, exist_ok=True)

            # Genera filename unico con timestamp
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            name, ext = os.path.splitext(filename)
            final_filename = f"training_{timestamp}_{name}{ext}"
            filepath = os.path.join(training_folder, final_filename)

            try:
                file.save(filepath)
                # Salva path relativo per il database
                plan.piano_allenamento_file_path = f"training_plans/{cliente_id}/{final_filename}"
                has_changes = True
                logger.info(f"File piano allenamento salvato: {plan.piano_allenamento_file_path}")
            except Exception as e:
                logger.exception(f"Errore salvataggio file: {e}")
                return jsonify({"error": f"Errore durante il salvataggio del file: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

    # Gestione notes
    if "notes" in request.form:
        plan.notes = request.form.get("notes", "").strip()
        has_changes = True

    # Gestione is_active
    if "is_active" in request.form:
        plan.is_active = request.form.get("is_active") == "true"
        has_changes = True

    if has_changes:
        plan.changed_by_id = getattr(current_user, "id", None)
        plan.change_reason = change_reason

        try:
            plan.validate_no_overlap(exclude_id=plan.id)
        except ValueError as e:
            return jsonify({"error": str(e)}), HTTPStatus.BAD_REQUEST

        db.session.commit()

    return jsonify({"ok": True, "message": "Piano allenamento aggiornato"})


@customers_bp.route("/<int:cliente_id>/training/history", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_training_history(cliente_id: int):
    """Restituisce lo storico completo dei piani allenamento."""
    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).one_or_404()
    _require_service_scope_or_403(cliente_id, "coaching")
    plans = db.session.query(TrainingPlan).filter_by(cliente_id=cliente_id).order_by(TrainingPlan.start_date.desc()).all()

    def _serialize(plan: TrainingPlan):
        # Recupera file extra per questo piano
        extra_files = db.session.query(PlanExtraFile).filter_by(
            plan_type=PlanTypeEnum.training_plan,
            plan_id=plan.id
        ).order_by(PlanExtraFile.created_at).all()

        return {
            "id": plan.id,
            "name": plan.name,
            "start_date": plan.start_date.isoformat() if plan.start_date else None,
            "end_date": plan.end_date.isoformat() if plan.end_date else None,
            "is_active": bool(plan.is_active),
            "piano_allenamento": plan.piano_allenamento,
            "piano_allenamento_file_path": plan.piano_allenamento_file_path,
            "has_file": bool(plan.piano_allenamento_file_path),
            "notes": plan.notes,
            "change_reason": plan.change_reason,
            "duration_days": plan.duration_days,
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
            "created_by": plan.created_by.full_name if plan.created_by else None,
            "extra_files": [
                {"id": f.id, "file_name": f.file_name, "file_size": f.file_size}
                for f in extra_files
            ],
        }

    legacy_plan = None
    if cliente.allenamento_dal:
        legacy_plan = {
            "id": None,
            "name": "Piano Legacy (da vecchi campi)",
            "start_date": cliente.allenamento_dal.isoformat() if cliente.allenamento_dal else None,
            "end_date": cliente.nuovo_allenamento_il.isoformat() if cliente.nuovo_allenamento_il else None,
            "is_active": False,
            "piano_allenamento": None,
            "notes": "Dati legacy dalla vecchia gestione",
            "is_legacy": True,
        }

    plans_data = [_serialize(p) for p in plans]
    if legacy_plan and (not plans_data or all(p["start_date"] != legacy_plan["start_date"] for p in plans_data)):
        plans_data.append(legacy_plan)

    return jsonify({"plans": plans_data, "can_manage": _can_manage_training_plans(cliente)})


@customers_bp.route("/<int:cliente_id>/training/<int:plan_id>/versions", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_training_versions(cliente_id: int, plan_id: int):
    """Restituisce lo storico delle versioni di un piano allenamento specifico."""
    _require_service_scope_or_403(cliente_id, "coaching")
    # Verifica che il piano appartenga al cliente
    plan = db.session.query(TrainingPlan).filter_by(
        id=plan_id,
        cliente_id=cliente_id
    ).one_or_404()

    # Recupera tutte le versioni usando SQLAlchemy-Continuum
    versions = []
    if hasattr(TrainingPlan, 'versions'):
        # Ottieni tutte le versioni del piano
        plan_versions = plan.versions.all()

        for idx, version in enumerate(plan_versions):
            file_path = version.piano_allenamento_file_path if hasattr(version, 'piano_allenamento_file_path') else None
            version_data = {
                "version_number": idx + 1,
                "transaction_id": version.transaction_id if hasattr(version, 'transaction_id') else None,
                "name": version.name if hasattr(version, 'name') else None,
                "start_date": version.start_date.isoformat() if hasattr(version, 'start_date') and version.start_date else None,
                "end_date": version.end_date.isoformat() if hasattr(version, 'end_date') and version.end_date else None,
                "notes": version.notes if hasattr(version, 'notes') else None,
                "change_reason": version.change_reason if hasattr(version, 'change_reason') else None,
                "changed_by_id": version.changed_by_id if hasattr(version, 'changed_by_id') else None,
                "changed_at": version.updated_at.isoformat() if hasattr(version, 'updated_at') and version.updated_at else None,
                "has_file": bool(file_path),
                "piano_allenamento_file_path": file_path,
            }

            # Aggiungi il nome dell'utente che ha fatto la modifica
            if version_data["changed_by_id"]:
                from corposostenibile.models import User
                user = db.session.query(User).filter_by(id=version_data["changed_by_id"]).first()
                version_data["changed_by"] = user.full_name if user else None

            versions.append(version_data)

    # Se ci sono versioni storiche, la versione corrente è len(versions) + 1
    # Se NON ci sono versioni storiche, la versione corrente è la versione 1
    current_version_number = len(versions) + 1 if versions else 1

    # Aggiungi la versione corrente (quella nel record principale)
    current_version_data = {
        "version_number": current_version_number,
        "transaction_id": None,
        "name": plan.name,
        "start_date": plan.start_date.isoformat() if plan.start_date else None,
        "end_date": plan.end_date.isoformat() if plan.end_date else None,
        "notes": plan.notes,
        "change_reason": plan.change_reason,
        "changed_by_id": plan.changed_by_id,
        "changed_at": plan.updated_at.isoformat() if plan.updated_at else None,
        "has_file": bool(plan.piano_allenamento_file_path),
        "piano_allenamento_file_path": plan.piano_allenamento_file_path,
        "is_current": True,
    }

    # Aggiungi il nome dell'utente per la versione corrente
    if current_version_data["changed_by_id"]:
        from corposostenibile.models import User
        user = db.session.query(User).filter_by(id=current_version_data["changed_by_id"]).first()
        current_version_data["changed_by"] = user.full_name if user else None

    versions.append(current_version_data)

    # Ordina per versione (più recente prima)
    versions.reverse()

    return jsonify({
        "ok": True,
        "plan_id": plan_id,
        "current_version": {
            "name": plan.name,
            "start_date": plan.start_date.isoformat() if plan.start_date else None,
            "end_date": plan.end_date.isoformat() if plan.end_date else None,
            "notes": plan.notes,
            "change_reason": plan.change_reason,
        },
        "versions": versions
    }), HTTPStatus.OK


@customers_bp.route("/<int:cliente_id>/training/<int:plan_id>/download", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_training_download(cliente_id: int, plan_id: int):
    """Download del PDF del piano allenamento."""
    import os
    from flask import current_app, send_from_directory

    _require_service_scope_or_403(cliente_id, "coaching")
    # Verifica che il cliente e il piano esistano e siano collegati
    plan = db.session.query(TrainingPlan).filter_by(
        id=plan_id,
        cliente_id=cliente_id
    ).one_or_404()

    if not plan.piano_allenamento_file_path:
        abort(404, description="File PDF non trovato per questo piano allenamento")

    # Costruisci il path completo al file
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    file_path = os.path.join(upload_folder, plan.piano_allenamento_file_path)

    # Verifica che il file esista fisicamente
    if not os.path.exists(file_path):
        logger.error(f"File piano allenamento non trovato: {file_path}")
        abort(404, description="File PDF non trovato sul server")

    # Estrai directory e filename
    directory = os.path.dirname(file_path)
    filename = os.path.basename(file_path)

    # Invia il file
    return send_from_directory(
        directory,
        filename,
        as_attachment=True,
        download_name=f"piano_allenamento_{plan.name or plan.id}.pdf"
    )


@customers_bp.route("/<int:cliente_id>/training/<int:plan_id>/extra-files/add", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def api_training_extra_file_add(cliente_id: int, plan_id: int):
    """Aggiunge un file extra a un piano allenamento."""
    from werkzeug.utils import secure_filename
    import os
    from flask import current_app

    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).one_or_404()
    _require_service_scope_or_403(cliente_id, "coaching")
    plan = db.session.query(TrainingPlan).filter_by(
        id=plan_id,
        cliente_id=cliente_id
    ).one_or_404()

    # Verifica limite di 5 file extra
    existing_files = db.session.query(PlanExtraFile).filter_by(
        plan_type=PlanTypeEnum.training_plan,
        plan_id=plan_id
    ).count()

    if existing_files >= 5:
        return jsonify({"error": "Massimo 5 file extra consentiti per piano"}), HTTPStatus.BAD_REQUEST

    # Gestione upload file PDF
    if 'extra_file' not in request.files:
        return jsonify({"error": "Nessun file fornito"}), HTTPStatus.BAD_REQUEST

    file = request.files['extra_file']
    if not file or not file.filename:
        return jsonify({"error": "Nessun file selezionato"}), HTTPStatus.BAD_REQUEST

    # Validazione file
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "Il file deve essere in formato PDF"}), HTTPStatus.BAD_REQUEST

    # Sanitizza filename
    filename = secure_filename(file.filename)
    if not filename:
        return jsonify({"error": "Nome file non valido"}), HTTPStatus.BAD_REQUEST

    # Verifica dimensione (max 50MB)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > 50 * 1024 * 1024:
        return jsonify({"error": "Il file è troppo grande. Dimensione massima: 50MB"}), HTTPStatus.BAD_REQUEST

    # Crea directory: uploads/training_plans/{cliente_id}/extra/
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    extra_folder = os.path.join(upload_folder, 'training_plans', str(cliente_id), 'extra')
    os.makedirs(extra_folder, exist_ok=True)

    # Genera filename unico con timestamp
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    name, ext = os.path.splitext(filename)
    final_filename = f"extra_{timestamp}_{name}{ext}"
    filepath = os.path.join(extra_folder, final_filename)

    try:
        file.save(filepath)
        # Salva path relativo per il database
        relative_path = f"training_plans/{cliente_id}/extra/{final_filename}"

        extra_file = PlanExtraFile(
            plan_type=PlanTypeEnum.training_plan,
            plan_id=plan_id,
            file_path=relative_path,
            file_name=filename,
            file_size=file_size,
            uploaded_by_id=getattr(current_user, "id", None)
        )
        db.session.add(extra_file)
        db.session.commit()

        logger.info(f"File extra aggiunto al piano allenamento {plan_id}: {relative_path}")
        return jsonify({
            "ok": True,
            "file_id": extra_file.id,
            "file_name": extra_file.file_name,
            "file_size": extra_file.file_size,
            "message": "File extra aggiunto con successo"
        })
    except Exception as e:
        logger.exception(f"Errore salvataggio file extra: {e}")
        db.session.rollback()
        return jsonify({"error": f"Errore durante il salvataggio del file: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR


@customers_bp.route("/<int:cliente_id>/training/<int:plan_id>/extra-files/<int:file_id>", methods=["DELETE"])
@permission_required(CustomerPerm.EDIT)
def api_training_extra_file_delete(cliente_id: int, plan_id: int, file_id: int):
    """Rimuove un file extra da un piano allenamento."""
    import os
    from flask import current_app

    _require_service_scope_or_403(cliente_id, "coaching")
    # Verifica che il piano appartenga al cliente
    plan = db.session.query(TrainingPlan).filter_by(
        id=plan_id,
        cliente_id=cliente_id
    ).one_or_404()

    # Verifica che il file appartenga al piano
    extra_file = db.session.query(PlanExtraFile).filter_by(
        id=file_id,
        plan_type=PlanTypeEnum.training_plan,
        plan_id=plan_id
    ).one_or_404()

    # Rimuovi il file fisico
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    filepath = os.path.join(upload_folder, extra_file.file_path)

    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        logger.warning(f"Errore rimozione file fisico {filepath}: {e}")

    # Rimuovi il record dal database
    db.session.delete(extra_file)
    db.session.commit()

    logger.info(f"File extra {file_id} rimosso dal piano allenamento {plan_id}")
    return jsonify({"ok": True, "message": "File extra rimosso con successo"})


@customers_bp.route("/<int:cliente_id>/training/<int:plan_id>/extra-files/<int:file_id>/download", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_training_extra_file_download(cliente_id: int, plan_id: int, file_id: int):
    """Scarica un file extra di un piano allenamento."""
    from flask import send_file, current_app
    import os

    _require_service_scope_or_403(cliente_id, "coaching")
    # Verifica che il piano appartenga al cliente
    plan = db.session.query(TrainingPlan).filter_by(
        id=plan_id,
        cliente_id=cliente_id
    ).one_or_404()

    # Verifica che il file appartenga al piano
    extra_file = db.session.query(PlanExtraFile).filter_by(
        id=file_id,
        plan_type=PlanTypeEnum.training_plan,
        plan_id=plan_id
    ).one_or_404()

    # Costruisci il path completo del file
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    filepath = os.path.abspath(os.path.join(upload_folder, extra_file.file_path))

    if not os.path.exists(filepath):
        logger.error(f"File extra non trovato: {filepath}")
        abort(404, description="File non trovato sul server")

    return send_file(
        filepath,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=extra_file.file_name
    )


# --------------------------------------------------------------------------- #
#  STORICO STATI API                                                          #
# --------------------------------------------------------------------------- #

@customers_bp.route("/<int:cliente_id>/stati/<servizio>/storico", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_storico_stati(cliente_id: int, servizio: str):
    """
    Recupera lo storico degli stati per un servizio specifico.

    servizio può essere: 'coach', 'nutrizione', 'psicologia',
                         'chat_coaching', 'chat_nutrizione', 'chat_psicologia'
    """
    from corposostenibile.models import StatoServizioLog

    # Verifica scope servizio (chat_* mappate al servizio principale)
    servizio_scope_map = {
        "nutrizione": "nutrizione",
        "chat_nutrizione": "nutrizione",
        "coach": "coaching",
        "chat_coaching": "coaching",
        "psicologia": "psicologia",
        "chat_psicologia": "psicologia",
    }
    servizio_scope = servizio_scope_map.get(servizio)
    if not servizio_scope:
        return jsonify({"ok": False, "error": "Servizio non valido"}), HTTPStatus.BAD_REQUEST
    _require_service_scope_or_403(cliente_id, servizio_scope)

    # Verifica che il cliente esista (coerenza con API legacy)
    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).one_or_404()

    # Recupera lo storico ordinato per data (dal più recente al più vecchio)
    storico = StatoServizioLog.query.filter_by(
        cliente_id=cliente_id,
        servizio=servizio
    ).order_by(StatoServizioLog.data_inizio.desc()).all()

    # Prepara la risposta JSON
    result = []
    for log in storico:
        result.append({
            'id': log.id,
            'stato': log.stato.value if log.stato else None,
            'data_inizio': log.data_inizio.strftime('%d/%m/%Y') if log.data_inizio else None,
            'data_fine': log.data_fine.strftime('%d/%m/%Y') if log.data_fine else None,
            'is_attivo': log.is_attivo,
            'durata_giorni': log.durata_giorni
        })

    return jsonify({
        'ok': True,
        'servizio': servizio,
        'storico': result
    }), HTTPStatus.OK


@customers_bp.route("/<int:cliente_id>/patologie/storico", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_storico_patologie(cliente_id: int):
    """
    Recupera lo storico completo delle patologie del cliente.
    Mostra quando ogni patologia è stata aggiunta o rimossa.
    """
    from corposostenibile.models import PatologiaLog

    # Verifica che il cliente esista
    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).one_or_404()
    _require_service_scope_or_403(cliente_id, "nutrizione")

    # Recupera lo storico ordinato per data (dal più recente al più vecchio)
    storico = PatologiaLog.query.filter_by(
        cliente_id=cliente_id
    ).order_by(PatologiaLog.data_inizio.desc()).all()

    # Prepara la risposta JSON
    result = []
    for log in storico:
        result.append({
            'id': log.id,
            'patologia': log.patologia,
            'patologia_nome': log.patologia_nome,
            'azione': log.azione,
            'data_inizio': log.data_inizio.strftime('%d/%m/%Y') if log.data_inizio else None,
            'data_fine': log.data_fine.strftime('%d/%m/%Y') if log.data_fine else None,
            'is_attiva': log.is_attiva,
            'durata_giorni': log.durata_giorni,
            'note': log.note
        })

    return jsonify({
        'ok': True,
        'storico': result
    }), HTTPStatus.OK


@customers_bp.route("/<int:cliente_id>/patologie_psico/storico", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_storico_patologie_psico(cliente_id: int):
    """
    Recupera lo storico completo delle patologie psicologiche del cliente.
    Mostra quando ogni patologia psicologica è stata aggiunta o rimossa.
    """
    from corposostenibile.models import PatologiaPsicoLog

    # Verifica che il cliente esista
    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).one_or_404()
    _require_service_scope_or_403(cliente_id, "psicologia")

    # Recupera lo storico ordinato per data (dal più recente al più vecchio)
    storico = PatologiaPsicoLog.query.filter_by(
        cliente_id=cliente_id
    ).order_by(PatologiaPsicoLog.data_inizio.desc()).all()

    # Prepara la risposta JSON
    result = []
    for log in storico:
        result.append({
            'id': log.id,
            'patologia': log.patologia,
            'patologia_nome': log.patologia_nome,
            'azione': log.azione,
            'data_inizio': log.data_inizio.strftime('%d/%m/%Y') if log.data_inizio else None,
            'data_fine': log.data_fine.strftime('%d/%m/%Y') if log.data_fine else None,
            'is_attiva': log.is_attiva,
            'durata_giorni': log.durata_giorni,
            'note': log.note
        })

    return jsonify({
        'ok': True,
        'storico': result
    }), HTTPStatus.OK


# --------------------------------------------------------------------------- #
#  TRAINING LOCATIONS API                                                     #
# --------------------------------------------------------------------------- #

@customers_bp.route("/<int:cliente_id>/location/add", methods=["POST"])
@csrf.exempt
@permission_required(CustomerPerm.EDIT)
def api_location_add(cliente_id: int):
    """Aggiunge un nuovo storico luogo allenamento."""
    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).one_or_404()
    _require_service_scope_or_403(cliente_id, "coaching")
    if not _can_manage_training_plans(cliente):
        abort(403)

    payload = request.get_json(silent=True) or {}
    start_str = payload.get("start_date")
    end_str = payload.get("end_date")
    location = payload.get("location", "").strip()
    notes = payload.get("notes", "").strip()

    if not location:
        return jsonify({"error": "location è obbligatorio"}), HTTPStatus.BAD_REQUEST

    try:
        if start_str:
            start_date = datetime.fromisoformat(start_str).date()
        else:
            start_date = TrainingLocation.calculate_next_start_date(cliente_id) or date.today()

        end_date = None
        if end_str:
            end_date = datetime.fromisoformat(end_str).date()
    except Exception as exc:
        return jsonify({"error": f"Date non valide: {exc}"}), HTTPStatus.BAD_REQUEST

    if end_date and start_date >= end_date:
        return jsonify({"error": "start_date deve essere precedente a end_date"}), HTTPStatus.BAD_REQUEST

    # Chiudi location attiva se esiste
    active_loc = db.session.query(TrainingLocation).filter_by(cliente_id=cliente_id, is_active=True).first()
    if active_loc:
        if not active_loc.end_date:
            active_loc.end_date = start_date - timedelta(days=1)
        elif active_loc.end_date >= start_date:
            active_loc.end_date = start_date - timedelta(days=1)
        active_loc.is_active = False
        db.session.flush()

    loc = TrainingLocation(
        cliente_id=cliente_id,
        created_by_id=getattr(current_user, "id", None),
        start_date=start_date,
        end_date=end_date,
        location=location,
        notes=notes,
        is_active=True,
    )

    try:
        loc.validate_no_overlap()
    except ValueError as e:
        return jsonify({"error": str(e)}), HTTPStatus.BAD_REQUEST

    try:
        db.session.add(loc)
        cliente.luogo_di_allenamento = LuogoAllenEnum(location)  # Aggiorna campo legacy
        db.session.commit()
    except ValueError as e:
        db.session.rollback()
        return jsonify({"error": f"Errore enum: {str(e)}"}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore aggiunta location per cliente {cliente_id}: {e}")
        return jsonify({"error": "Errore durante il salvataggio"}), HTTPStatus.INTERNAL_SERVER_ERROR

    return jsonify({"ok": True, "location_id": loc.id, "message": "Luogo allenamento aggiunto con successo"}), HTTPStatus.CREATED


@customers_bp.route("/<int:cliente_id>/location/change/<int:loc_id>", methods=["POST"])
@csrf.exempt
@permission_required(CustomerPerm.EDIT)
def api_location_change(cliente_id: int, loc_id: int):
    """Cambia storico luogo allenamento esistente."""
    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).one_or_404()
    _require_service_scope_or_403(cliente_id, "coaching")
    if not _can_manage_training_plans(cliente):
        abort(403)

    payload = request.get_json(silent=True) or {}
    loc = db.session.query(TrainingLocation).filter_by(id=loc_id, cliente_id=cliente_id).one_or_404()
    change_reason = payload.get("change_reason", "").strip()

    if payload.get("start_date") or payload.get("end_date") or payload.get("location"):
        if payload.get("start_date"):
            try:
                loc.start_date = datetime.fromisoformat(payload["start_date"]).date()
            except Exception as exc:
                return jsonify({"error": f"start_date non valida: {exc}"}), HTTPStatus.BAD_REQUEST

        if "end_date" in payload:
            if payload["end_date"]:
                try:
                    loc.end_date = datetime.fromisoformat(payload["end_date"]).date()
                except Exception as exc:
                    return jsonify({"error": f"end_date non valida: {exc}"}), HTTPStatus.BAD_REQUEST
            else:
                loc.end_date = None

        if loc.end_date and loc.start_date >= loc.end_date:
            return jsonify({"error": "start_date deve essere precedente a end_date"}), HTTPStatus.BAD_REQUEST

        if "location" in payload:
            loc.location = payload.get("location", "").strip()

        if "notes" in payload:
            loc.notes = payload.get("notes", "").strip()

        if "is_active" in payload:
            loc.is_active = bool(payload.get("is_active"))

        loc.changed_by_id = getattr(current_user, "id", None)
        loc.change_reason = change_reason

        try:
            loc.validate_no_overlap(exclude_id=loc.id)
        except ValueError as e:
            return jsonify({"error": str(e)}), HTTPStatus.BAD_REQUEST

        # Aggiorna campo legacy se questa è la location attiva
        if loc.is_active and loc.location:
            cliente.luogo_di_allenamento = LuogoAllenEnum(loc.location)

        db.session.commit()

    return jsonify({"ok": True, "message": "Luogo allenamento aggiornato"})


@customers_bp.route("/<int:cliente_id>/location/history", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_location_history(cliente_id: int):
    """Restituisce lo storico completo dei luoghi allenamento."""
    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).one_or_404()
    _require_service_scope_or_403(cliente_id, "coaching")
    locations = db.session.query(TrainingLocation).filter_by(cliente_id=cliente_id).order_by(TrainingLocation.start_date.desc()).all()

    def _serialize(loc: TrainingLocation):
        return {
            "id": loc.id,
            "start_date": loc.start_date.isoformat() if loc.start_date else None,
            "end_date": loc.end_date.isoformat() if loc.end_date else None,
            "location": loc.location,
            "is_active": bool(loc.is_active),
            "notes": loc.notes,
            "change_reason": loc.change_reason,
            "duration_days": loc.duration_days,
            "created_at": loc.created_at.isoformat() if loc.created_at else None,
            "created_by": loc.created_by.full_name if loc.created_by else None,
        }

    # Aggiungi location legacy se esiste
    legacy_loc = None
    if cliente.luogo_di_allenamento:
        legacy_loc = {
            "id": None,
            "start_date": None,
            "end_date": None,
            "location": cliente.luogo_di_allenamento,
            "is_active": False,
            "notes": "Dati legacy dalla vecchia gestione",
            "is_legacy": True,
        }

    locs_data = [_serialize(l) for l in locations]
    if legacy_loc and not any(l["location"] == legacy_loc["location"] and l["is_active"] for l in locs_data):
        locs_data.append(legacy_loc)

    return jsonify({"history": locs_data, "legacy_location": legacy_loc, "can_manage": _can_manage_training_plans(cliente)})


@customers_bp.route("/<int:cliente_id>/location/<int:location_id>/versions", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_location_versions(cliente_id: int, location_id: int):
    """Restituisce lo storico delle versioni di un luogo allenamento specifico."""
    _require_service_scope_or_403(cliente_id, "coaching")
    # Verifica che il luogo appartenga al cliente
    location = db.session.query(TrainingLocation).filter_by(
        id=location_id,
        cliente_id=cliente_id
    ).one_or_404()

    # Recupera tutte le versioni usando SQLAlchemy-Continuum
    versions = []
    if hasattr(TrainingLocation, 'versions'):
        # Ottieni tutte le versioni del luogo
        location_versions = location.versions.all()

        for idx, version in enumerate(location_versions):
            version_data = {
                "version_number": idx + 1,
                "transaction_id": version.transaction_id if hasattr(version, 'transaction_id') else None,
                "start_date": version.start_date.isoformat() if hasattr(version, 'start_date') and version.start_date else None,
                "end_date": version.end_date.isoformat() if hasattr(version, 'end_date') and version.end_date else None,
                "location": version.location if hasattr(version, 'location') else None,
                "notes": version.notes if hasattr(version, 'notes') else None,
                "change_reason": version.change_reason if hasattr(version, 'change_reason') else None,
                "changed_by_id": version.changed_by_id if hasattr(version, 'changed_by_id') else None,
                "changed_at": version.updated_at.isoformat() if hasattr(version, 'updated_at') and version.updated_at else None,
            }

            # Aggiungi il nome dell'utente che ha fatto la modifica
            if version_data["changed_by_id"]:
                from corposostenibile.models import User
                user = db.session.query(User).filter_by(id=version_data["changed_by_id"]).first()
                version_data["changed_by"] = user.full_name if user else None

            versions.append(version_data)

    # Se ci sono versioni storiche, la versione corrente è len(versions) + 1
    # Se NON ci sono versioni storiche, la versione corrente è la versione 1
    current_version_number = len(versions) + 1 if versions else 1

    # Aggiungi la versione corrente (quella nel record principale)
    current_version_data = {
        "version_number": current_version_number,
        "transaction_id": None,
        "start_date": location.start_date.isoformat() if location.start_date else None,
        "end_date": location.end_date.isoformat() if location.end_date else None,
        "location": location.location,
        "notes": location.notes,
        "change_reason": location.change_reason,
        "changed_by_id": location.changed_by_id,
        "changed_at": location.updated_at.isoformat() if location.updated_at else None,
        "is_current": True,
    }

    # Aggiungi il nome dell'utente per la versione corrente
    if current_version_data["changed_by_id"]:
        from corposostenibile.models import User
        user = db.session.query(User).filter_by(id=current_version_data["changed_by_id"]).first()
        current_version_data["changed_by"] = user.full_name if user else None

    versions.append(current_version_data)

    # Ordina per versione (più recente prima)
    versions.reverse()

    return jsonify({
        "ok": True,
        "location_id": location_id,
        "current_version": {
            "start_date": location.start_date.isoformat() if location.start_date else None,
            "end_date": location.end_date.isoformat() if location.end_date else None,
            "location": location.location,
            "notes": location.notes,
            "change_reason": location.change_reason,
        },
        "versions": versions
    }), HTTPStatus.OK


# --------------------------------------------------------------------------- #
#  API: Nutrition (Piani Alimentari) - Sistema Storico e Versionamento       #
# --------------------------------------------------------------------------- #

@customers_bp.route("/<int:cliente_id>/nutrition/add", methods=["POST"])
@csrf.exempt
@permission_required(CustomerPerm.EDIT)
def api_nutrition_add(cliente_id: int):
    """Aggiunge un nuovo piano alimentare con upload PDF."""
    from werkzeug.utils import secure_filename
    import os
    from flask import current_app

    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).one_or_404()
    _require_service_scope_or_403(cliente_id, "nutrizione")
    if not _can_manage_meal_plans(cliente):
        abort(403)

    # Gestione multipart form data invece di JSON
    start_str = request.form.get("start_date")
    end_str = request.form.get("end_date")
    notes = request.form.get("notes", "").strip()

    # Gestione upload file PDF
    piano_alimentare_file_path = None
    if 'piano_alimentare_file' in request.files:
        file = request.files['piano_alimentare_file']
        if file and file.filename:
            # Validazione file
            if not file.filename.lower().endswith('.pdf'):
                return jsonify({"error": "Il file deve essere in formato PDF"}), HTTPStatus.BAD_REQUEST

            # Sanitizza filename
            filename = secure_filename(file.filename)
            if not filename:
                return jsonify({"error": "Nome file non valido"}), HTTPStatus.BAD_REQUEST

            # Crea directory: uploads/meal_plans/{cliente_id}/
            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
            nutrition_folder = os.path.join(upload_folder, 'meal_plans', str(cliente_id))
            os.makedirs(nutrition_folder, exist_ok=True)

            # Genera filename unico con timestamp
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            name, ext = os.path.splitext(filename)
            final_filename = f"nutrition_{timestamp}_{name}{ext}"
            filepath = os.path.join(nutrition_folder, final_filename)

            try:
                file.save(filepath)
                # Salva path relativo per il database
                piano_alimentare_file_path = f"meal_plans/{cliente_id}/{final_filename}"
                logger.info(f"File piano alimentare salvato: {piano_alimentare_file_path}")
            except Exception as e:
                logger.exception(f"Errore salvataggio file: {e}")
                return jsonify({"error": f"Errore durante il salvataggio del file: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
    else:
        return jsonify({"error": "File PDF del piano alimentare è obbligatorio"}), HTTPStatus.BAD_REQUEST

    try:
        if start_str:
            start_date = datetime.fromisoformat(start_str).date()
        else:
            start_date = MealPlan.calculate_next_start_date(cliente_id) or date.today()

        if not end_str:
            return jsonify({"error": "end_date è obbligatorio"}), HTTPStatus.BAD_REQUEST
        end_date = datetime.fromisoformat(end_str).date()
    except Exception as exc:
        return jsonify({"error": f"Date non valide: {exc}"}), HTTPStatus.BAD_REQUEST

    if start_date >= end_date:
        return jsonify({"error": "start_date deve essere precedente a end_date"}), HTTPStatus.BAD_REQUEST

    active_plan = db.session.query(MealPlan).filter_by(cliente_id=cliente_id, is_active=True).first()
    if active_plan:
        if not active_plan.end_date:
            active_plan.end_date = start_date - timedelta(days=1)
        elif active_plan.end_date >= start_date:
            active_plan.end_date = start_date - timedelta(days=1)
        active_plan.is_active = False
        db.session.flush()

    name = request.form.get("name", "").strip() or f"Piano Alimentare {start_date.strftime('%d/%m/%Y')}"
    plan = MealPlan(
        cliente_id=cliente_id,
        created_by_id=getattr(current_user, "id", None),
        name=name,
        start_date=start_date,
        end_date=end_date,
        piano_alimentare=None,  # Deprecato, ora usiamo il file
        piano_alimentare_file_path=piano_alimentare_file_path,
        notes=notes,
        is_active=True,
    )

    try:
        plan.validate_no_overlap()
    except ValueError as e:
        return jsonify({"error": str(e)}), HTTPStatus.BAD_REQUEST

    db.session.add(plan)
    cliente.dieta_dal = start_date
    cliente.nuova_dieta_dal = end_date
    db.session.commit()

    return jsonify({"ok": True, "plan_id": plan.id, "message": "Piano alimentare aggiunto con successo"}), HTTPStatus.CREATED


@customers_bp.route("/<int:cliente_id>/nutrition/change", methods=["POST"])
@csrf.exempt
@permission_required(CustomerPerm.EDIT)
def api_nutrition_change(cliente_id: int):
    """Cambia piano alimentare esistente."""
    from werkzeug.utils import secure_filename
    import os
    from flask import current_app

    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).one_or_404()
    _require_service_scope_or_403(cliente_id, "nutrizione")
    if not _can_manage_meal_plans(cliente):
        abort(403)

    # Gestione multipart form data invece di JSON
    plan_id = request.form.get("plan_id")
    if not plan_id:
        return jsonify({"error": "plan_id è obbligatorio"}), HTTPStatus.BAD_REQUEST

    try:
        plan_id = int(plan_id)
    except ValueError:
        return jsonify({"error": "plan_id non valido"}), HTTPStatus.BAD_REQUEST

    plan = db.session.query(MealPlan).filter_by(id=plan_id, cliente_id=cliente_id).one_or_404()
    change_reason = request.form.get("change_reason", "").strip()

    # Verifica se c'è almeno un campo da modificare
    has_changes = False

    # Gestione date
    start_str = request.form.get("start_date")
    end_str = request.form.get("end_date")

    if start_str:
        try:
            new_start_date = datetime.fromisoformat(start_str).date()
            plan.start_date = new_start_date
            has_changes = True
        except Exception as exc:
            return jsonify({"error": f"start_date non valida: {exc}"}), HTTPStatus.BAD_REQUEST

    if end_str:
        try:
            new_end_date = datetime.fromisoformat(end_str).date()
            plan.end_date = new_end_date
            has_changes = True
        except Exception as exc:
            return jsonify({"error": f"end_date non valida: {exc}"}), HTTPStatus.BAD_REQUEST

    if plan.start_date >= plan.end_date:
        return jsonify({"error": "start_date deve essere precedente a end_date"}), HTTPStatus.BAD_REQUEST

    # Gestione upload file PDF (se presente)
    if 'piano_alimentare_file' in request.files:
        file = request.files['piano_alimentare_file']
        if file and file.filename:
            # Validazione file
            if not file.filename.lower().endswith('.pdf'):
                return jsonify({"error": "Il file deve essere in formato PDF"}), HTTPStatus.BAD_REQUEST

            # Sanitizza filename
            filename = secure_filename(file.filename)
            if not filename:
                return jsonify({"error": "Nome file non valido"}), HTTPStatus.BAD_REQUEST

            # Crea directory: uploads/meal_plans/{cliente_id}/
            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
            nutrition_folder = os.path.join(upload_folder, 'meal_plans', str(cliente_id))
            os.makedirs(nutrition_folder, exist_ok=True)

            # Genera filename unico con timestamp
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            name, ext = os.path.splitext(filename)
            final_filename = f"nutrition_{timestamp}_{name}{ext}"
            filepath = os.path.join(nutrition_folder, final_filename)

            try:
                file.save(filepath)
                # Salva path relativo per il database
                plan.piano_alimentare_file_path = f"meal_plans/{cliente_id}/{final_filename}"
                has_changes = True
                logger.info(f"File piano alimentare salvato: {plan.piano_alimentare_file_path}")
            except Exception as e:
                logger.exception(f"Errore salvataggio file: {e}")
                return jsonify({"error": f"Errore durante il salvataggio del file: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

    # Gestione notes
    if "notes" in request.form:
        plan.notes = request.form.get("notes", "").strip()
        has_changes = True

    # Gestione is_active
    if "is_active" in request.form:
        plan.is_active = request.form.get("is_active") == "true"
        has_changes = True

    if has_changes:
        plan.changed_by_id = getattr(current_user, "id", None)
        plan.change_reason = change_reason

        try:
            plan.validate_no_overlap(exclude_id=plan.id)
        except ValueError as e:
            return jsonify({"error": str(e)}), HTTPStatus.BAD_REQUEST

        db.session.commit()

    return jsonify({"ok": True, "message": "Piano alimentare aggiornato"})


@customers_bp.route("/<int:cliente_id>/nutrition/history", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_nutrition_history(cliente_id: int):
    """Restituisce lo storico completo dei piani alimentari."""
    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).one_or_404()
    _require_service_scope_or_403(cliente_id, "nutrizione")
    plans = db.session.query(MealPlan).filter_by(cliente_id=cliente_id).order_by(MealPlan.start_date.desc()).all()

    def _serialize(plan: MealPlan):
        # Recupera file extra per questo piano
        extra_files = db.session.query(PlanExtraFile).filter_by(
            plan_type=PlanTypeEnum.meal_plan,
            plan_id=plan.id
        ).order_by(PlanExtraFile.created_at).all()

        return {
            "id": plan.id,
            "name": plan.name,
            "start_date": plan.start_date.isoformat() if plan.start_date else None,
            "end_date": plan.end_date.isoformat() if plan.end_date else None,
            "is_active": bool(plan.is_active),
            "piano_alimentare": plan.piano_alimentare,
            "piano_alimentare_file_path": plan.piano_alimentare_file_path,
            "has_file": bool(plan.piano_alimentare_file_path),
            "notes": plan.notes,
            "change_reason": plan.change_reason,
            "duration_days": plan.duration_days,
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
            "created_by": plan.created_by.full_name if plan.created_by else None,
            "extra_files": [
                {"id": f.id, "file_name": f.file_name, "file_size": f.file_size}
                for f in extra_files
            ],
        }

    legacy_plan = None
    if cliente.dieta_dal:
        legacy_plan = {
            "id": None,
            "name": "Piano Legacy (da vecchi campi)",
            "start_date": cliente.dieta_dal.isoformat() if cliente.dieta_dal else None,
            "end_date": cliente.nuova_dieta_dal.isoformat() if cliente.nuova_dieta_dal else None,
            "is_active": False,
            "piano_alimentare": None,
            "notes": "Dati legacy dalla vecchia gestione",
            "is_legacy": True,
        }

    plans_data = [_serialize(p) for p in plans]
    if legacy_plan and (not plans_data or all(p["start_date"] != legacy_plan["start_date"] for p in plans_data)):
        plans_data.append(legacy_plan)

    return jsonify({"ok": True, "plans": plans_data})


@customers_bp.route("/<int:cliente_id>/nutrition/<int:plan_id>/versions", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_nutrition_versions(cliente_id: int, plan_id: int):
    """Restituisce lo storico delle versioni di un piano alimentare specifico."""
    _require_service_scope_or_403(cliente_id, "nutrizione")
    # Verifica che il piano appartenga al cliente
    plan = db.session.query(MealPlan).filter_by(
        id=plan_id,
        cliente_id=cliente_id
    ).one_or_404()

    # Recupera tutte le versioni usando SQLAlchemy-Continuum
    versions = []
    if hasattr(MealPlan, 'versions'):
        # Ottieni tutte le versioni del piano (ordinate per transaction_id)
        plan_versions = list(plan.versions.all())
        total_versions = len(plan_versions)

        for idx, version in enumerate(plan_versions):
            file_path = version.piano_alimentare_file_path if hasattr(version, 'piano_alimentare_file_path') else None
            is_latest = (idx == total_versions - 1)  # L'ultima versione è quella corrente

            version_data = {
                "version_number": idx + 1,
                "transaction_id": version.transaction_id if hasattr(version, 'transaction_id') else None,
                "name": version.name if hasattr(version, 'name') else None,
                "start_date": version.start_date.isoformat() if hasattr(version, 'start_date') and version.start_date else None,
                "end_date": version.end_date.isoformat() if hasattr(version, 'end_date') and version.end_date else None,
                "notes": version.notes if hasattr(version, 'notes') else None,
                "change_reason": version.change_reason if hasattr(version, 'change_reason') else None,
                "changed_by_id": version.changed_by_id if hasattr(version, 'changed_by_id') else None,
                "changed_at": version.updated_at.isoformat() if hasattr(version, 'updated_at') and version.updated_at else None,
                "has_file": bool(file_path),
                "piano_alimentare_file_path": file_path,
                "is_current": is_latest,
            }

            # Aggiungi il nome dell'utente che ha fatto la modifica
            if version_data["changed_by_id"]:
                from corposostenibile.models import User
                user = db.session.query(User).filter_by(id=version_data["changed_by_id"]).first()
                version_data["changed_by"] = user.full_name if user else None

            versions.append(version_data)

    # Se non ci sono versioni (Continuum non attivo), mostra solo il record corrente
    if not versions:
        current_version_data = {
            "version_number": 1,
            "transaction_id": None,
            "name": plan.name,
            "start_date": plan.start_date.isoformat() if plan.start_date else None,
            "end_date": plan.end_date.isoformat() if plan.end_date else None,
            "notes": plan.notes,
            "change_reason": plan.change_reason,
            "changed_by_id": plan.changed_by_id,
            "changed_at": plan.updated_at.isoformat() if plan.updated_at else None,
            "has_file": bool(plan.piano_alimentare_file_path),
            "piano_alimentare_file_path": plan.piano_alimentare_file_path,
            "is_current": True,
        }
        if current_version_data["changed_by_id"]:
            from corposostenibile.models import User
            user = db.session.query(User).filter_by(id=current_version_data["changed_by_id"]).first()
            current_version_data["changed_by"] = user.full_name if user else None
        versions.append(current_version_data)

    # Ordina per versione (più recente prima)
    versions.reverse()

    return jsonify({
        "ok": True,
        "plan_id": plan_id,
        "current_version": {
            "name": plan.name,
            "start_date": plan.start_date.isoformat() if plan.start_date else None,
            "end_date": plan.end_date.isoformat() if plan.end_date else None,
            "notes": plan.notes,
            "change_reason": plan.change_reason,
        },
        "versions": versions
    }), HTTPStatus.OK


@customers_bp.route("/<int:cliente_id>/nutrition/<int:plan_id>/download", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_nutrition_download(cliente_id: int, plan_id: int):
    """Scarica il PDF del piano alimentare."""
    from flask import send_file, current_app
    import os

    cliente = _require_service_scope_or_403(cliente_id, "nutrizione")
    # Verifica che il piano appartenga al cliente
    plan = db.session.query(MealPlan).filter_by(
        id=plan_id,
        cliente_id=cliente_id
    ).one_or_404()

    if not plan.piano_alimentare_file_path:
        abort(404, description="Nessun file PDF disponibile per questo piano alimentare")

    # Costruisci il path completo del file
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    filepath = os.path.join(upload_folder, plan.piano_alimentare_file_path)

    if not os.path.exists(filepath):
        logger.error(f"File piano alimentare non trovato: {filepath}")
        abort(404, description="File PDF non trovato sul server")

    # Estrae il nome del file dal path
    filename = os.path.basename(plan.piano_alimentare_file_path)

    return send_file(
        filepath,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"piano_alimentare_{cliente.nome}_{cliente.cognome}.pdf"
    )


@customers_bp.route("/<int:cliente_id>/nutrition/<int:plan_id>/extra-files/add", methods=["POST"])
@csrf.exempt
@permission_required(CustomerPerm.EDIT)
def api_nutrition_extra_file_add(cliente_id: int, plan_id: int):
    """Aggiunge un file extra a un piano alimentare."""
    from werkzeug.utils import secure_filename
    import os
    from flask import current_app

    cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).one_or_404()
    _require_service_scope_or_403(cliente_id, "nutrizione")
    plan = db.session.query(MealPlan).filter_by(
        id=plan_id,
        cliente_id=cliente_id
    ).one_or_404()

    # Verifica limite di 5 file extra
    existing_files = db.session.query(PlanExtraFile).filter_by(
        plan_type=PlanTypeEnum.meal_plan,
        plan_id=plan_id
    ).count()

    if existing_files >= 5:
        return jsonify({"error": "Massimo 5 file extra consentiti per piano"}), HTTPStatus.BAD_REQUEST

    # Gestione upload file PDF
    if 'extra_file' not in request.files:
        return jsonify({"error": "Nessun file fornito"}), HTTPStatus.BAD_REQUEST

    file = request.files['extra_file']
    if not file or not file.filename:
        return jsonify({"error": "Nessun file selezionato"}), HTTPStatus.BAD_REQUEST

    # Validazione file
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "Il file deve essere in formato PDF"}), HTTPStatus.BAD_REQUEST

    # Sanitizza filename
    filename = secure_filename(file.filename)
    if not filename:
        return jsonify({"error": "Nome file non valido"}), HTTPStatus.BAD_REQUEST

    # Verifica dimensione (max 50MB)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    if file_size > 50 * 1024 * 1024:
        return jsonify({"error": "Il file è troppo grande. Dimensione massima: 50MB"}), HTTPStatus.BAD_REQUEST

    # Crea directory: uploads/meal_plans/{cliente_id}/extra/
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    extra_folder = os.path.join(upload_folder, 'meal_plans', str(cliente_id), 'extra')
    os.makedirs(extra_folder, exist_ok=True)

    # Genera filename unico con timestamp
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    name, ext = os.path.splitext(filename)
    final_filename = f"extra_{timestamp}_{name}{ext}"
    filepath = os.path.join(extra_folder, final_filename)

    try:
        file.save(filepath)
        # Salva path relativo per il database
        relative_path = f"meal_plans/{cliente_id}/extra/{final_filename}"

        extra_file = PlanExtraFile(
            plan_type=PlanTypeEnum.meal_plan,
            plan_id=plan_id,
            file_path=relative_path,
            file_name=filename,
            file_size=file_size,
            uploaded_by_id=getattr(current_user, "id", None)
        )
        db.session.add(extra_file)
        db.session.commit()

        logger.info(f"File extra aggiunto al piano alimentare {plan_id}: {relative_path}")
        return jsonify({
            "ok": True,
            "file_id": extra_file.id,
            "file_name": extra_file.file_name,
            "file_size": extra_file.file_size,
            "message": "File extra aggiunto con successo"
        })
    except Exception as e:
        logger.exception(f"Errore salvataggio file extra: {e}")
        db.session.rollback()
        return jsonify({"error": f"Errore durante il salvataggio del file: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR


@customers_bp.route("/<int:cliente_id>/nutrition/<int:plan_id>/extra-files/<int:file_id>", methods=["DELETE"])
@csrf.exempt
@permission_required(CustomerPerm.EDIT)
def api_nutrition_extra_file_delete(cliente_id: int, plan_id: int, file_id: int):
    """Rimuove un file extra da un piano alimentare."""
    import os
    from flask import current_app

    _require_service_scope_or_403(cliente_id, "nutrizione")
    # Verifica che il piano appartenga al cliente
    plan = db.session.query(MealPlan).filter_by(
        id=plan_id,
        cliente_id=cliente_id
    ).one_or_404()

    # Verifica che il file appartenga al piano
    extra_file = db.session.query(PlanExtraFile).filter_by(
        id=file_id,
        plan_type=PlanTypeEnum.meal_plan,
        plan_id=plan_id
    ).one_or_404()

    # Rimuovi il file fisico
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    filepath = os.path.join(upload_folder, extra_file.file_path)

    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        logger.warning(f"Errore rimozione file fisico {filepath}: {e}")

    # Rimuovi il record dal database
    db.session.delete(extra_file)
    db.session.commit()

    logger.info(f"File extra {file_id} rimosso dal piano alimentare {plan_id}")
    return jsonify({"ok": True, "message": "File extra rimosso con successo"})


@customers_bp.route("/<int:cliente_id>/nutrition/<int:plan_id>/extra-files/<int:file_id>/download", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_nutrition_extra_file_download(cliente_id: int, plan_id: int, file_id: int):
    """Scarica un file extra di un piano alimentare."""
    from flask import send_file, current_app
    import os

    _require_service_scope_or_403(cliente_id, "nutrizione")
    # Verifica che il piano appartenga al cliente
    plan = db.session.query(MealPlan).filter_by(
        id=plan_id,
        cliente_id=cliente_id
    ).one_or_404()

    # Verifica che il file appartenga al piano
    extra_file = db.session.query(PlanExtraFile).filter_by(
        id=file_id,
        plan_type=PlanTypeEnum.meal_plan,
        plan_id=plan_id
    ).one_or_404()

    # Costruisci il path completo del file
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    filepath = os.path.abspath(os.path.join(upload_folder, extra_file.file_path))

    if not os.path.exists(filepath):
        logger.error(f"File extra non trovato: {filepath}")
        abort(404, description="File non trovato sul server")

    return send_file(
        filepath,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=extra_file.file_name
    )


# --------------------------------------------------------------------------- #
#  PAGAMENTI INTERNI - CRUD                                                   #
# --------------------------------------------------------------------------- #

@customers_bp.route("/<int:cliente_id>/pagamenti/interni", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_pagamenti_interni_list(cliente_id: int):
    """Lista pagamenti interni di un cliente."""
    cliente = customers_repo.get_one(cliente_id)
    if not cliente:
        return jsonify({"success": False, "message": "Cliente non trovato"}), HTTPStatus.NOT_FOUND

    pagamenti = PagamentoInterno.query.filter_by(cliente_id=cliente_id).order_by(
        PagamentoInterno.data_pagamento.desc()
    ).all()

    result = []
    for p in pagamenti:
        approvazione = p.approvazione
        result.append({
            "id": p.id,
            "data_pagamento": p.data_pagamento.isoformat() if p.data_pagamento else None,
            "importo": float(p.importo) if p.importo else 0,
            "servizio_acquistato": p.servizio_acquistato,
            "sotto_categoria": p.sotto_categoria,
            "durata": p.durata,
            "metodo_pagamento": p.metodo_pagamento.value if p.metodo_pagamento else None,
            "contabile": p.contabile,
            "note": p.note,
            "status": p.status.value if p.status else "completato",
            "created_by": p.created_by.full_name if p.created_by else None,
            "stato_approvazione": approvazione.stato_approvazione if approvazione else "da_valutare",
            "tipo_pagamento": approvazione.tipo_pagamento.value if approvazione and approvazione.tipo_pagamento else None,
        })

    return jsonify({"success": True, "pagamenti": result}), HTTPStatus.OK


@customers_bp.route("/pagamenti/interni", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def create_pagamento_interno():
    """Crea un nuovo pagamento interno."""
    try:
        data = request.get_json()
        if not data:
            raise BadRequest("Dati mancanti")

        cliente_id = data.get("cliente_id")
        if not cliente_id:
            raise BadRequest("cliente_id mancante")

        # Converti cliente_id in intero e usa db.session.get per poter modificare l'oggetto
        try:
            cliente_id = int(cliente_id)
        except (ValueError, TypeError):
            raise BadRequest("cliente_id non valido")

        cliente = db.session.get(Cliente, cliente_id)
        if not cliente:
            raise NotFound("Cliente non trovato")

        # Normalizza metodo pagamento
        metodo_pagamento = data.get("modalita_pagamento", "")
        if metodo_pagamento:
            metodo_map = {
                "bonifico": PagamentoEnum.bonifico,
                "bonifico bancario": PagamentoEnum.bonifico,
                "klarna": PagamentoEnum.klarna,
                "stripe": PagamentoEnum.stripe,
                "paypal": PagamentoEnum.paypal,
                "carta": PagamentoEnum.carta,
                "carta di credito": PagamentoEnum.carta,
                "contanti": PagamentoEnum.contanti,
            }
            metodo_lower = str(metodo_pagamento).strip().lower()
            metodo_pagamento = metodo_map.get(metodo_lower)

        # servizio_acquistato può essere inviato come "servizio_acquistato" (con nome pacchetto)
        # oppure come "tipologia_servizio" (solo tipologia)
        servizio = data.get("servizio_acquistato") or data.get("tipologia_servizio")

        # Normalizza attribuibile_a (solo per rinnovi)
        attribuibile_a_value = data.get("attribuibile_a")
        attribuibile_a = None
        if attribuibile_a_value:
            attribuibile_map = {
                "sales": AttribuibileAEnum.sales,
                "team_interno": AttribuibileAEnum.team_interno,
                "nutrizionista": AttribuibileAEnum.nutrizionista,
                "coach": AttribuibileAEnum.coach,
                "psicologo": AttribuibileAEnum.psicologo,
                "health_manager": AttribuibileAEnum.health_manager,
            }
            attribuibile_a = attribuibile_map.get(str(attribuibile_a_value).strip().lower())

        pagamento = PagamentoInterno(
            cliente_id=cliente_id,
            importo=data.get("importo"),
            data_pagamento=date.fromisoformat(data.get("data_pagamento")) if data.get("data_pagamento") else date.today(),
            metodo_pagamento=metodo_pagamento,
            servizio_acquistato=servizio,
            sotto_categoria=data.get("sotto_categoria") or None,
            attribuibile_a=attribuibile_a,
            pacchetto_id=data.get("pacchetto_id") or None,
            durata=data.get("durata"),
            contabile=data.get("contabile"),
            note=data.get("note"),
            status=PagamentoInternoStatusEnum.completato,
            created_by_id=current_user.id,
        )
        db.session.add(pagamento)

        # ─────────────────────────────────────────────────────────────────────
        # AGGIORNAMENTO AUTOMATICO DURATA E DATA RINNOVO
        # Quando si inserisce un pagamento con un pacchetto, aggiungi i giorni
        # del pacchetto alla durata_programma_giorni e ricalcola data_rinnovo
        # ─────────────────────────────────────────────────────────────────────
        giorni_aggiunti = 0
        nuova_data_rinnovo = None

        pacchetto_id = data.get("pacchetto_id")
        if pacchetto_id:
            try:
                package = db.session.get(Package, int(pacchetto_id))
                if package and package.duration_months:
                    # Converti mesi in giorni (approssimazione: 1 mese = 30 giorni)
                    giorni_aggiunti = package.duration_months * 30

                    # Aggiorna durata_programma_giorni del cliente
                    durata_attuale = cliente.durata_programma_giorni or 0
                    cliente.durata_programma_giorni = durata_attuale + giorni_aggiunti

                    # Ricalcola data_rinnovo
                    if cliente.data_inizio_abbonamento:
                        nuova_data_rinnovo = cliente.data_inizio_abbonamento + timedelta(days=cliente.durata_programma_giorni)
                        cliente.data_rinnovo = nuova_data_rinnovo

                    logger.info(
                        f"Cliente {cliente_id}: aggiunta durata {giorni_aggiunti}gg "
                        f"(pacchetto {package.name}, {package.duration_months}m). "
                        f"Nuova durata totale: {cliente.durata_programma_giorni}gg, "
                        f"Nuova data rinnovo: {nuova_data_rinnovo}"
                    )
            except (ValueError, TypeError) as e:
                logger.warning(f"Errore nel calcolo durata/rinnovo per pacchetto {pacchetto_id}: {e}")

        db.session.commit()

        # Prepara risposta con info aggiornamento
        response_data = {
            "success": True,
            "message": "Pagamento salvato con successo",
            "id": pagamento.id
        }

        if giorni_aggiunti > 0:
            response_data["durata_aggiunta"] = giorni_aggiunti
            response_data["nuova_durata_totale"] = cliente.durata_programma_giorni
            if nuova_data_rinnovo:
                response_data["nuova_data_rinnovo"] = nuova_data_rinnovo.isoformat()
                response_data["message"] = f"Pagamento salvato. Aggiunti {giorni_aggiunti} giorni. Nuova data rinnovo: {nuova_data_rinnovo.strftime('%d/%m/%Y')}"

        return jsonify(response_data), HTTPStatus.CREATED

    except BadRequest as e:
        return jsonify({"success": False, "message": str(e)}), HTTPStatus.BAD_REQUEST
    except NotFound as e:
        return jsonify({"success": False, "message": str(e)}), HTTPStatus.NOT_FOUND
    except (SQLAlchemyError, ValueError) as e:
        db.session.rollback()
        logging.error(f"Errore creazione pagamento interno: {e}")
        return jsonify({"success": False, "message": "Errore durante il salvataggio"}), HTTPStatus.INTERNAL_SERVER_ERROR


# --------------------------------------------------------------------------- #
#  PAGAMENTI INTERNI - APPROVAZIONE                                           #
# --------------------------------------------------------------------------- #



@customers_bp.route("/api/pagamenti-interni/<int:pagamento_id>/approva", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def approva_pagamento_interno(pagamento_id: int):
    """Approva un pagamento interno."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "Dati mancanti"}), HTTPStatus.BAD_REQUEST

        pagamento = db.session.get(PagamentoInterno, pagamento_id)
        if not pagamento:
            return jsonify({"success": False, "message": "Pagamento non trovato"}), HTTPStatus.NOT_FOUND

        approvazione = PagamentoInternoApprovazione.query.filter_by(
            pagamento_interno_id=pagamento_id
        ).first()

        if not approvazione:
            approvazione = PagamentoInternoApprovazione(
                pagamento_interno_id=pagamento_id,
                tipo_pagamento=data.get("tipo_pagamento", "rinnovo"),
                costo_nutrizionista=data.get("costo_nutrizionista", 0),
                costo_coach=data.get("costo_coach", 0),
                costo_psicologo=data.get("costo_psicologo", 0),
                costo_transazione=data.get("costo_transazione", 0),
                stato_approvazione="in_attesa",
            )
            db.session.add(approvazione)

        approvazione.tipo_pagamento = data.get("tipo_pagamento", approvazione.tipo_pagamento)
        approvazione.costo_nutrizionista = data.get("costo_nutrizionista", approvazione.costo_nutrizionista)
        approvazione.costo_coach = data.get("costo_coach", approvazione.costo_coach)
        approvazione.costo_psicologo = data.get("costo_psicologo", approvazione.costo_psicologo)
        approvazione.costo_transazione = data.get("costo_transazione", approvazione.costo_transazione)
        approvazione.stato_approvazione = "approvato"
        approvazione.note_approvazione = data.get("note_approvazione")
        approvazione.approvato_da_id = current_user.id
        approvazione.data_approvazione = datetime.utcnow()

        pagamento.status = PagamentoInternoStatusEnum.completato

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Pagamento approvato con successo",
            "importo_totale": str(approvazione.importo_totale),
        }), HTTPStatus.OK

    except Exception as e:
        db.session.rollback()
        logging.error(f"Errore approvazione pagamento {pagamento_id}: {e}")
        return jsonify({"success": False, "message": "Errore durante l'approvazione"}), HTTPStatus.INTERNAL_SERVER_ERROR


@customers_bp.route("/api/pagamenti-interni/<int:pagamento_id>/rifiuta", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def rifiuta_pagamento_interno(pagamento_id: int):
    """Rifiuta un pagamento interno."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "Dati mancanti"}), HTTPStatus.BAD_REQUEST

        pagamento = db.session.get(PagamentoInterno, pagamento_id)
        if not pagamento:
            return jsonify({"success": False, "message": "Pagamento non trovato"}), HTTPStatus.NOT_FOUND

        approvazione = PagamentoInternoApprovazione.query.filter_by(
            pagamento_interno_id=pagamento_id
        ).first()

        if not approvazione:
            approvazione = PagamentoInternoApprovazione(
                pagamento_interno_id=pagamento_id,
                tipo_pagamento=data.get("tipo_pagamento", "rinnovo"),
                stato_approvazione="in_attesa",
            )
            db.session.add(approvazione)

        approvazione.stato_approvazione = "rifiutato"
        approvazione.note_approvazione = data.get("note_approvazione", "")
        approvazione.approvato_da_id = current_user.id
        approvazione.data_approvazione = datetime.utcnow()

        pagamento.status = PagamentoInternoStatusEnum.annullato

        db.session.commit()

        return jsonify({"success": True, "message": "Pagamento rifiutato"}), HTTPStatus.OK

    except Exception as e:
        db.session.rollback()
        logging.error(f"Errore rifiuto pagamento {pagamento_id}: {e}")
        return jsonify({"success": False, "message": "Errore durante il rifiuto"}), HTTPStatus.INTERNAL_SERVER_ERROR


# --------------------------------------------------------------------------- #
#  API RICERCA CLIENTI (per modal pagamenti)                                  #
# --------------------------------------------------------------------------- #

@customers_bp.route("/api/search", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_search_clienti():
    """Ricerca clienti per autocomplete.

    Query params:
        q: stringa di ricerca (min 2 caratteri)
        limit: numero massimo risultati (default 15)

    Returns:
        JSON con lista clienti trovati (id, nome, email)
    """
    q = request.args.get("q", "").strip()
    limit = request.args.get("limit", 15, type=int)

    if len(q) < 2:
        return jsonify({"success": True, "clienti": []}), HTTPStatus.OK

    # Ricerca per nome, email o telefono
    clienti = apply_role_filtering(Cliente.query).filter(
        db.or_(
            Cliente.nome_cognome.ilike(f"%{q}%"),
            Cliente.mail.ilike(f"%{q}%"),
            Cliente.numero_telefono.ilike(f"%{q}%")
        )
    ).order_by(
        Cliente.nome_cognome.asc()
    ).limit(limit).all()

    risultati = []
    for c in clienti:
        risultati.append({
            "id": c.cliente_id,
            "nome": c.nome_cognome or "N/D",
            "email": c.mail or "",
            "telefono": c.numero_telefono or "",
            "stato": c.stato_cliente.value if c.stato_cliente else "N/D"
        })

    return jsonify({"success": True, "clienti": risultati}), HTTPStatus.OK


# --------------------------------------------------------------------------- #
#  Generate Progress Collage                                                 #
# --------------------------------------------------------------------------- #
@customers_bp.route("/<int:cliente_id>/generate-progress-collage", methods=["POST"])
@permission_required(CustomerPerm.VIEW)
def generate_progress_collage(cliente_id: int):
    """
    Genera un collage confrontando le PRIME foto disponibili con le ULTIME.

    Cerca foto in ordine cronologico tra:
    - Check iniziali della Lead (Check 1, 2, 3) tramite form_attachments
    - TypeFormResponse (vecchio sistema)
    - WeeklyCheckResponse (nuovo sistema)

    Trova la PRIMA e l'ULTIMA foto disponibile per creare il confronto.
    """
    from corposostenibile.models import (
        WeeklyCheck,
        WeeklyCheckResponse,
        TypeFormResponse,
        Allegato,
        SalesLead,
    )
    from corposostenibile.blueprints.customers.utils import create_progress_collage
    from werkzeug.utils import secure_filename
    import os
    from datetime import datetime

    try:
        # Verifica che il cliente esista
        cliente = db.session.query(Cliente).filter_by(cliente_id=cliente_id).first_or_404()

        # ─── RACCOLTA TUTTE LE FOTO CON DATE ─────────────────────────────────
        # Lista di tuple: (date, photos_dict, source_type)
        all_photo_records = []

        # 1. FOTO DA LEAD INIZIALE (Check 1, 2, 3 - form_attachments)
        if cliente.original_lead:
            lead = cliente.original_lead
            # form_attachments è un JSONB con lista di allegati
            if lead.form_attachments:
                # Raggruppa allegati per check_number
                attachments_by_check = {}
                for att in lead.form_attachments:
                    check_num = att.get('check_number')
                    if check_num:
                        if check_num not in attachments_by_check:
                            attachments_by_check[check_num] = {'front': None, 'side': None, 'back': None}

                        field_name = (att.get('field_name') or '').lower()
                        file_path = att.get('path')

                        if file_path:
                            if 'frontale' in field_name or 'front' in field_name:
                                attachments_by_check[check_num]['front'] = file_path
                            elif 'laterale' in field_name or 'side' in field_name:
                                attachments_by_check[check_num]['side'] = file_path
                            elif 'posteriore' in field_name or 'back' in field_name:
                                attachments_by_check[check_num]['back'] = file_path

                # Usa le date di completamento dei check
                check_dates = {
                    1: lead.check1_completed_at,
                    2: lead.check2_completed_at,
                    3: lead.check3_completed_at,
                }

                for check_num, photos in attachments_by_check.items():
                    if any(photos.values()):
                        check_date = check_dates.get(check_num) or lead.created_at
                        all_photo_records.append((
                            check_date,
                            photos,
                            f"Check {check_num} iniziale"
                        ))

        # 2. FOTO DA TYPEFORM RESPONSES
        typeform_responses = (
            db.session.query(TypeFormResponse)
            .filter(TypeFormResponse.cliente_id == cliente_id)
            .order_by(TypeFormResponse.submit_date.asc())
            .all()
        )

        for tf_resp in typeform_responses:
            photos = {
                'front': tf_resp.photo_front,
                'side': tf_resp.photo_side,
                'back': tf_resp.photo_back
            }
            if any(photos.values()):
                all_photo_records.append((
                    tf_resp.submit_date or tf_resp.created_at,
                    photos,
                    "TypeForm"
                ))

        # 3. FOTO DA WEEKLY CHECK RESPONSES
        weekly_responses = (
            db.session.query(WeeklyCheckResponse)
            .join(WeeklyCheck)
            .filter(WeeklyCheck.cliente_id == cliente_id)
            .order_by(WeeklyCheckResponse.submit_date.asc())
            .all()
        )

        for wc_resp in weekly_responses:
            photos = {
                'front': wc_resp.photo_front,
                'side': wc_resp.photo_side,
                'back': wc_resp.photo_back
            }
            if any(photos.values()):
                all_photo_records.append((
                    wc_resp.submit_date or wc_resp.created_at,
                    photos,
                    "Check Settimanale"
                ))

        # ─── ORDINA PER DATA E TROVA PRIMA/ULTIMA ────────────────────────────
        if not all_photo_records:
            return jsonify({
                "success": False,
                "message": "Nessuna foto disponibile. Il cliente non ha foto nei check iniziali, TypeForm o check settimanali."
            }), HTTPStatus.BAD_REQUEST

        # Ordina per data (gestendo None)
        all_photo_records.sort(key=lambda x: x[0] or datetime.min)

        # PRIMA foto disponibile (la più vecchia)
        first_record = all_photo_records[0]
        initial_photos = first_record[1]
        initial_date = first_record[0].strftime('%d/%m/%Y') if first_record[0] else None
        initial_source = first_record[2]

        # ULTIMA foto disponibile (la più recente)
        last_record = all_photo_records[-1]
        latest_photos = last_record[1]
        latest_date = last_record[0].strftime('%d/%m/%Y') if last_record[0] else None
        latest_source = last_record[2]

        # Se abbiamo solo un record, non ha senso fare un confronto
        if len(all_photo_records) < 2:
            return jsonify({
                "success": False,
                "message": f"È disponibile solo un set di foto ({initial_source} del {initial_date}). Servono almeno due check con foto per creare un confronto."
            }), HTTPStatus.BAD_REQUEST

        # ─── GENERA COLLAGE ──────────────────────────────────────────────────
        try:
            collage_bytes = create_progress_collage(
                initial_photos=initial_photos,
                latest_photos=latest_photos,
                initial_date=initial_date,
                latest_date=latest_date
            )
        except ValueError as e:
            return jsonify({
                "success": False,
                "message": str(e)
            }), HTTPStatus.BAD_REQUEST
        except Exception as e:
            logger.error(f"Errore generazione collage per cliente {cliente_id}: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "message": f"Errore durante la generazione del collage: {str(e)}"
            }), HTTPStatus.INTERNAL_SERVER_ERROR

        # ─── SALVA COLLAGE ────────────────────────────────────────────────────
        # Crea/recupera cartella clinica "Progresso"
        cartella = (
            db.session.query(CartellaClinica)
            .filter_by(cliente_id=cliente_id, nome="Progresso")
            .first()
        )

        if not cartella:
            cartella = CartellaClinica(
                cliente_id=cliente_id,
                nome="Progresso",
                note="Cartella per documenti di progresso del cliente"
            )
            db.session.add(cartella)
            db.session.flush()  # Per ottenere l'ID

        # Salva file collage
        upload_folder = os.path.join(current_app.static_folder or 'static', 'uploads', 'collages')
        os.makedirs(upload_folder, exist_ok=True)

        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = secure_filename(f"collage_progresso_{cliente_id}_{timestamp}.jpg")
        filepath = os.path.join(upload_folder, filename)

        with open(filepath, 'wb') as f:
            f.write(collage_bytes)

        # Path relativo per il database (da static/)
        relative_path = os.path.join('uploads', 'collages', filename).replace('\\', '/')

        # Crea record Allegato
        allegato = Allegato(
            cartella_id=cartella.id,
            file_path=relative_path,
            file_type="image/jpeg",
            note=f"Collage progresso: {initial_source} ({initial_date}) vs {latest_source} ({latest_date})"
        )
        db.session.add(allegato)
        db.session.commit()

        # URL per accedere al collage
        collage_url = url_for('static', filename=relative_path)

        return jsonify({
            "success": True,
            "message": "Collage generato con successo",
            "collage_url": collage_url,
            "allegato_id": allegato.id,
            "initial_source": initial_source,
            "latest_source": latest_source,
            "initial_date": initial_date,
            "latest_date": latest_date,
            "total_photo_records": len(all_photo_records)
        }), HTTPStatus.OK

    except Exception as e:
        db.session.rollback()
        logger.error(f"Errore generazione collage progresso per cliente {cliente_id}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Errore durante la generazione del collage: {str(e)}"
        }), HTTPStatus.INTERNAL_SERVER_ERROR


# ============================================================================
# SERVICE NOTES: Anamnesi & Diario
# ============================================================================

@api_bp.route("/<int:cliente_id>/anamnesi/<service_type>", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def get_anamnesi(cliente_id: int, service_type: str):
    """Recupera l'anamnesi per un servizio specifico."""
    from corposostenibile.models import ServiceAnamnesi

    if service_type not in ['nutrizione', 'coaching', 'psicologia']:
        return jsonify({"success": False, "error": "Tipo servizio non valido"}), HTTPStatus.BAD_REQUEST
    _require_service_scope_or_403(cliente_id, service_type)

    anamnesi = ServiceAnamnesi.query.filter_by(
        cliente_id=cliente_id,
        service_type=service_type
    ).first()

    if not anamnesi:
        return jsonify({"success": True, "anamnesi": None})

    return jsonify({
        "success": True,
        "anamnesi": {
            "id": anamnesi.id,
            "content": anamnesi.content,
            "created_at": anamnesi.created_at.strftime('%d/%m/%Y %H:%M') if anamnesi.created_at else None,
            "updated_at": anamnesi.updated_at.strftime('%d/%m/%Y %H:%M') if anamnesi.updated_at else None,
            "created_by": anamnesi.created_by.full_name if anamnesi.created_by else None,
            "last_modified_by": anamnesi.last_modified_by.full_name if anamnesi.last_modified_by else None
        }
    })


@api_bp.route("/<int:cliente_id>/anamnesi/<service_type>", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def save_anamnesi(cliente_id: int, service_type: str):
    """Crea o aggiorna l'anamnesi per un servizio (sempre modificabile)."""
    from corposostenibile.models import ServiceAnamnesi

    if service_type not in ['nutrizione', 'coaching', 'psicologia']:
        return jsonify({"success": False, "error": "Tipo servizio non valido"}), HTTPStatus.BAD_REQUEST
    _require_service_scope_or_403(cliente_id, service_type)

    data = request.get_json()
    content = data.get('content', '').strip()

    if not content:
        return jsonify({"success": False, "error": "Il contenuto è obbligatorio"}), HTTPStatus.BAD_REQUEST

    try:
        anamnesi = ServiceAnamnesi.query.filter_by(
            cliente_id=cliente_id,
            service_type=service_type
        ).first()

        if anamnesi:
            # Aggiorna esistente
            anamnesi.content = content
            anamnesi.last_modified_by_user_id = current_user.id
            message = "Anamnesi aggiornata con successo"
        else:
            # Crea nuova
            anamnesi = ServiceAnamnesi(
                cliente_id=cliente_id,
                service_type=service_type,
                content=content,
                created_by_user_id=current_user.id
            )
            db.session.add(anamnesi)
            message = "Anamnesi creata con successo"

        db.session.commit()

        return jsonify({
            "success": True,
            "message": message,
            "anamnesi_id": anamnesi.id
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Errore salvataggio anamnesi: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@api_bp.route("/<int:cliente_id>/diary/<service_type>", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def get_diary_entries(cliente_id: int, service_type: str):
    """Recupera tutte le voci del diario per un servizio."""
    from corposostenibile.models import ServiceDiaryEntry

    if service_type not in ['nutrizione', 'coaching', 'psicologia']:
        return jsonify({"success": False, "error": "Tipo servizio non valido"}), HTTPStatus.BAD_REQUEST
    _require_service_scope_or_403(cliente_id, service_type)

    entries = ServiceDiaryEntry.query.filter_by(
        cliente_id=cliente_id,
        service_type=service_type
    ).order_by(ServiceDiaryEntry.entry_date.desc()).all()

    return jsonify({
        "success": True,
        "entries": [{
            "id": e.id,
            "entry_date": e.entry_date.strftime('%Y-%m-%d') if e.entry_date else None,
            "entry_date_display": e.entry_date.strftime('%d/%m/%Y') if e.entry_date else None,
            "content": e.content,
            "author": e.author.full_name if e.author else 'Staff',
            "created_at": e.created_at.strftime('%d/%m/%Y %H:%M') if e.created_at else None
        } for e in entries]
    })


@csrf.exempt
@api_bp.route("/<int:cliente_id>/diary/<service_type>", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def create_diary_entry(cliente_id: int, service_type: str):
    """Crea una nuova voce del diario."""
    from corposostenibile.models import ServiceDiaryEntry

    if service_type not in ['nutrizione', 'coaching', 'psicologia']:
        return jsonify({"success": False, "error": "Tipo servizio non valido"}), HTTPStatus.BAD_REQUEST
    _require_service_scope_or_403(cliente_id, service_type)

    data = request.get_json()
    content = data.get('content', '').strip()
    entry_date_str = data.get('entry_date')

    if not content:
        return jsonify({"success": False, "error": "Il contenuto è obbligatorio"}), HTTPStatus.BAD_REQUEST

    try:
        # Parse data o usa oggi
        if entry_date_str:
            entry_date = datetime.strptime(entry_date_str, '%Y-%m-%d').date()
        else:
            entry_date = date.today()

        entry = ServiceDiaryEntry(
            cliente_id=cliente_id,
            service_type=service_type,
            entry_date=entry_date,
            content=content,
            author_user_id=current_user.id
        )
        db.session.add(entry)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Nota del diario creata con successo",
            "entry": {
                "id": entry.id,
                "entry_date": entry.entry_date.strftime('%Y-%m-%d'),
                "entry_date_display": entry.entry_date.strftime('%d/%m/%Y'),
                "content": entry.content,
                "author": current_user.full_name or 'Staff'
            }
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Errore creazione diary entry: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@csrf.exempt
@api_bp.route("/<int:cliente_id>/diary/<service_type>/<int:entry_id>", methods=["PUT"])
@permission_required(CustomerPerm.EDIT)
def update_diary_entry(cliente_id: int, service_type: str, entry_id: int):
    """Aggiorna una voce del diario esistente."""
    from corposostenibile.models import ServiceDiaryEntry

    if service_type not in ['nutrizione', 'coaching', 'psicologia']:
        return jsonify({"success": False, "error": "Tipo servizio non valido"}), HTTPStatus.BAD_REQUEST
    _require_service_scope_or_403(cliente_id, service_type)

    entry = ServiceDiaryEntry.query.filter_by(
        id=entry_id,
        cliente_id=cliente_id,
        service_type=service_type
    ).first()

    if not entry:
        return jsonify({"success": False, "error": "Voce non trovata"}), HTTPStatus.NOT_FOUND

    data = request.get_json()
    content = data.get('content', '').strip()
    entry_date_str = data.get('entry_date')

    if not content:
        return jsonify({"success": False, "error": "Il contenuto è obbligatorio"}), HTTPStatus.BAD_REQUEST

    try:
        entry.content = content
        if entry_date_str:
            entry.entry_date = datetime.strptime(entry_date_str, '%Y-%m-%d').date()

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Nota del diario aggiornata con successo",
            "entry": {
                "id": entry.id,
                "entry_date": entry.entry_date.strftime('%Y-%m-%d'),
                "entry_date_display": entry.entry_date.strftime('%d/%m/%Y'),
                "content": entry.content,
                "author": entry.author.full_name if entry.author else 'Staff'
            }
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Errore aggiornamento diary entry: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@csrf.exempt
@api_bp.route("/<int:cliente_id>/diary/<service_type>/<int:entry_id>", methods=["DELETE"])
@permission_required(CustomerPerm.EDIT)
def delete_diary_entry(cliente_id: int, service_type: str, entry_id: int):
    """Elimina una voce del diario."""
    from corposostenibile.models import ServiceDiaryEntry

    if service_type not in ['nutrizione', 'coaching', 'psicologia']:
        return jsonify({"success": False, "error": "Tipo servizio non valido"}), HTTPStatus.BAD_REQUEST
    _require_service_scope_or_403(cliente_id, service_type)

    if not current_user.is_admin:
        return jsonify({"success": False, "error": "Solo gli amministratori possono eliminare le note del diario"}), HTTPStatus.FORBIDDEN

    entry = ServiceDiaryEntry.query.filter_by(
        id=entry_id,
        cliente_id=cliente_id,
        service_type=service_type
    ).first()

    if not entry:
        return jsonify({"success": False, "error": "Voce non trovata"}), HTTPStatus.NOT_FOUND

    try:
        db.session.delete(entry)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Nota del diario eliminata con successo"
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Errore eliminazione diary entry: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@csrf.exempt
@api_bp.route("/<int:cliente_id>/diary/<service_type>/<int:entry_id>/history", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def get_diary_entry_history(cliente_id: int, service_type: str, entry_id: int):
    """Recupera lo storico delle modifiche per una voce del diario."""
    from corposostenibile.models import ServiceDiaryEntry, User
    from sqlalchemy_continuum import version_class
    
    if service_type not in ['nutrizione', 'coaching', 'psicologia']:
        return jsonify({"success": False, "error": "Tipo servizio non valido"}), HTTPStatus.BAD_REQUEST
    _require_service_scope_or_403(cliente_id, service_type)

    ServiceDiaryEntryVersion = version_class(ServiceDiaryEntry)
    
    versions = ServiceDiaryEntryVersion.query.filter(
        ServiceDiaryEntryVersion.id == entry_id
    ).order_by(ServiceDiaryEntryVersion.transaction_id.desc()).all()

    history = []
    for version in versions:
        author_name = "Sistema"
        # Continuum transaction.user_id non disponibile (user_cls=None)
        # Usiamo author_user_id salvato nella versione
        if version.author_user_id:
             user = User.query.get(version.author_user_id)
             if user:
                 author_name = user.full_name

        history.append({
            "content": version.content,
            # transaction.issued_at è disponibile anche senza user_cls
            "modified_at": version.transaction.issued_at.strftime('%d/%m/%Y %H:%M') if version.transaction else "N/D",
            "author": author_name
        })

    return jsonify({
        "success": True,
        "history": history
    })

# --------------------------------------------------------------------------- #
#  CALL BONUS API (AI-driven flow)                                            #
# --------------------------------------------------------------------------- #

def _is_assigned_to_cliente(user, cliente) -> bool:
    """Verifica se l'utente è assegnato al paziente come professionista (o admin).
    Include anche professionisti coinvolti in call bonus sul paziente.
    """
    if user.is_admin or user.role == UserRoleEnum.admin:
        return True
    role = getattr(user, "role", None)
    role_value = role.value if hasattr(role, "value") else str(role or "")
    if role_value == "team_leader":
        try:
            scoped_query = apply_role_filtering(db.session.query(Cliente.cliente_id))
            return scoped_query.filter(Cliente.cliente_id == cliente.cliente_id).first() is not None
        except Exception:
            logger.exception("Errore verifica scope team_leader su cliente %s", getattr(cliente, "cliente_id", None))
            return False
    if role_value == "influencer":
        client_origin = getattr(cliente, "origine_id", None)
        return client_origin is not None and client_origin in [o.id for o in (user.influencer_origins or [])]
    if (
        getattr(cliente, "nutrizionista_id", None) == user.id
        or getattr(cliente, "coach_id", None) == user.id
        or getattr(cliente, "psicologa_id", None) == user.id
        or getattr(cliente, "consulente_alimentare_id", None) == user.id
        or getattr(cliente, "health_manager_id", None) == user.id
        or user in cliente.nutrizionisti_multipli
        or user in cliente.coaches_multipli
        or user in cliente.psicologi_multipli
        or user in cliente.consulenti_multipli
    ):
        return True
    # Professionista assegnato tramite call bonus (anche dopo la risposta interesse)
    from corposostenibile.models import CallBonus
    has_active_cb = db.session.query(CallBonus.id).filter(
        CallBonus.cliente_id == cliente.cliente_id,
        CallBonus.professionista_id == user.id,
        CallBonus.status.in_([
            CallBonusStatusEnum.accettata,
            CallBonusStatusEnum.interessato,
            CallBonusStatusEnum.non_interessato,
            CallBonusStatusEnum.confermata,
            CallBonusStatusEnum.rifiutata,
            CallBonusStatusEnum.non_andata_buon_fine,
        ]),
    ).first()
    return has_active_cb is not None


def _is_professionista_standard(user) -> bool:
    role = getattr(user, "role", None)
    role_value = role.value if hasattr(role, "value") else str(role or "")
    return (not getattr(user, "is_admin", False)) and role_value == "professionista"


def _is_health_manager_user(user) -> bool:
    role = getattr(user, "role", None)
    role_value = role.value if hasattr(role, "value") else str(role or "")
    return (not getattr(user, "is_admin", False)) and role_value == "health_manager"


def _normalize_specialty_group_for_rbac(user) -> str | None:
    specialty = getattr(user, "specialty", None)
    specialty_value = specialty.value if hasattr(specialty, "value") else str(specialty or "")
    specialty_value = specialty_value.strip().lower()
    if specialty_value in ("nutrizionista", "nutrizione"):
        return "nutrizione"
    if specialty_value in ("psicologo", "psicologia", "psicologa"):
        return "psicologia"
    if specialty_value == "coach":
        return "coach"
    if specialty_value == "medico":
        return "medico"
    return None


def _is_team_leader_health_manager_scope(user) -> bool:
    role = getattr(user, "role", None)
    role_value = role.value if hasattr(role, "value") else str(role or "")
    if role_value != "team_leader":
        return False
    teams_led = getattr(user, "teams_led", []) or []
    for team in teams_led:
        team_type = getattr(getattr(team, "team_type", None), "value", getattr(team, "team_type", None))
        if str(team_type or "").strip().lower() == "health_manager":
            return True
    specialty = getattr(user, "specialty", None)
    specialty_value = specialty.value if hasattr(specialty, "value") else str(specialty or "")
    specialty_value = specialty_value.strip().lower()
    if specialty_value == "health_manager":
        return True
    department_name = getattr(getattr(user, "department", None), "name", "")
    department_name = str(department_name or "").strip().lower()
    return ("health" in department_name) or ("customer success" in department_name)


def _team_leader_visible_member_ids(user) -> set[int]:
    visible_ids = {getattr(user, "id", None)}
    for team in getattr(user, "teams_led", []) or []:
        if not getattr(team, "is_active", True):
            continue
        for member in getattr(team, "members", []) or []:
            visible_ids.add(member.id)
    return {uid for uid in visible_ids if uid is not None}


def _team_leader_can_manage_assignment_type(user, tipo_professionista: str | None) -> bool:
    tipo = (tipo_professionista or "").strip().lower()
    if tipo == "health_manager":
        return _is_team_leader_health_manager_scope(user)
    allowed_by_specialty = {
        "nutrizione": {"nutrizionista"},
        "coach": {"coach"},
        "psicologia": {"psicologa"},
        "medico": {"medico"},
    }
    specialty_group = _normalize_specialty_group_for_rbac(user)
    if not specialty_group:
        return False
    return tipo in allowed_by_specialty.get(specialty_group, set())


def _require_team_leader_assignment_scope_or_403(user, tipo_professionista: str, target_user_id: int) -> None:
    role = getattr(user, "role", None)
    role_value = role.value if hasattr(role, "value") else str(role or "")
    if role_value != "team_leader":
        return
    if not _team_leader_can_manage_assignment_type(user, tipo_professionista):
        abort(HTTPStatus.FORBIDDEN, description="Tipo professionista non gestibile per la tua specialità.")
    if int(target_user_id) not in _team_leader_visible_member_ids(user):
        abort(HTTPStatus.FORBIDDEN, description="Professionista fuori dal perimetro del tuo team.")


def _is_assigned_to_cliente_for_service(user, cliente, service_type: str) -> bool:
    """Scope granulare per i professionisti sulle sezioni servizio-specifiche."""
    if getattr(user, "is_admin", False):
        return True
    role = getattr(user, "role", None)
    role_value = role.value if hasattr(role, "value") else str(role or "")
    if role_value == "admin":
        return True
    if role_value == "team_leader":
        # TL: almeno cliente nel perimetro dei team gestiti (specialità gestita lato UI / altri filtri)
        try:
            from corposostenibile.blueprints.client_checks.rbac import get_accessible_clients_query
            accessible_query = get_accessible_clients_query()
            if accessible_query is None:
                return True
            return accessible_query.filter(Cliente.cliente_id == cliente.cliente_id).first() is not None
        except Exception:
            logger.exception("Errore verifica scope team_leader su cliente %s", getattr(cliente, "cliente_id", None))
            return False
    if role_value == "health_manager":
        return getattr(cliente, "health_manager_id", None) == user.id
    if role_value == "influencer":
        # Influencer: accesso read-only ai clienti delle proprie origini
        client_origin = getattr(cliente, "origine_id", None)
        return client_origin is not None and client_origin in [o.id for o in (user.influencer_origins or [])]
    if role_value != "professionista":
        return False

    if service_type == "nutrizione":
        return getattr(cliente, "nutrizionista_id", None) == user.id or user in (cliente.nutrizionisti_multipli or [])
    if service_type == "coaching":
        return getattr(cliente, "coach_id", None) == user.id or user in (cliente.coaches_multipli or [])
    if service_type == "psicologia":
        return getattr(cliente, "psicologa_id", None) == user.id or user in (cliente.psicologi_multipli or [])
    return False


def _require_service_scope_or_403(cliente_id: int, service_type: str) -> "Cliente":
    cliente = db.session.get(Cliente, cliente_id)
    if not cliente:
        abort(HTTPStatus.NOT_FOUND, description="Cliente non trovato.")
    if not _is_assigned_to_cliente_for_service(current_user, cliente, service_type):
        abort(HTTPStatus.FORBIDDEN, description="Non autorizzato per questo servizio del paziente.")
    return cliente


@api_bp.route("/<int:cliente_id>/call-bonus-history", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_call_bonus_history(cliente_id: int):
    """Storico call bonus del paziente."""
    from .services import get_cliente_call_bonus_history

    cliente = db.session.get(Cliente, cliente_id)
    if not cliente:
        abort(HTTPStatus.NOT_FOUND, description="Cliente non trovato.")
    if not _is_assigned_to_cliente(current_user, cliente):
        abort(HTTPStatus.FORBIDDEN, description="Non sei assegnato a questo paziente.")

    import json as _json

    records = get_cliente_call_bonus_history(cliente_id)

    # Get HM calendar link once for this client
    hm_name = None
    hm_calendar_link = ""
    if cliente.health_manager_user:
        hm_name = cliente.health_manager_user.full_name
        ai_notes = cliente.health_manager_user.assignment_ai_notes or {}
        if isinstance(ai_notes, str):
            try:
                ai_notes = _json.loads(ai_notes)
            except (ValueError, TypeError):
                ai_notes = {}
        hm_calendar_link = ai_notes.get("link_calendario", "")

    data = []
    for cb in records:
        prof_name = None
        if cb.professionista:
            prof_name = cb.professionista.full_name
        data.append({
            "id": cb.id,
            "data_richiesta": cb.data_richiesta.isoformat() if cb.data_richiesta else None,
            "tipo_professionista": cb.tipo_professionista.value if cb.tipo_professionista else None,
            "professionista_nome": prof_name,
            "professionista_id": cb.professionista_id,
            "is_assigned_professional": cb.professionista_id == current_user.id if cb.professionista_id else False,
            "is_requester": cb.created_by_id == current_user.id,
            "status": cb.status.value if cb.status else None,
            "created_by_nome": cb.created_by.full_name if cb.created_by else None,
            "created_by_id": cb.created_by_id,
            "note_richiesta": cb.note_richiesta,
            "booking_confirmed": cb.booking_confirmed or False,
            "hm_booking_confirmed": cb.hm_booking_confirmed or False,
            "hm_name": hm_name,
            "hm_calendar_link": hm_calendar_link,
        })

    return jsonify({"data": data})


@api_bp.route("/call-bonus-interest/<int:call_bonus_id>", methods=["POST"])
@permission_required(CustomerPerm.VIEW)
def api_call_bonus_interest(call_bonus_id: int):
    """Professionista assegnato risponde sull'interesse del paziente."""
    from corposostenibile.models import CallBonus
    from .call_bonus_webhooks import dispatch_call_bonus_webhook

    call_bonus = db.session.get(CallBonus, call_bonus_id)
    if not call_bonus:
        abort(HTTPStatus.NOT_FOUND, description="Call bonus non trovata.")

    if call_bonus.professionista_id != current_user.id:
        abort(HTTPStatus.FORBIDDEN, description="Non sei il professionista assegnato a questa call bonus.")

    if call_bonus.status != CallBonusStatusEnum.accettata:
        abort(HTTPStatus.CONFLICT, description="Questa call bonus non è in stato 'accettata'.")

    payload = request.get_json() or {}
    interested = payload.get("interested")
    if interested is None:
        abort(HTTPStatus.BAD_REQUEST, description="Campo 'interested' obbligatorio.")

    if interested:
        call_bonus.status = CallBonusStatusEnum.interessato
        call_bonus.data_interesse = datetime.utcnow()
        call_bonus.hm_booking_confirmed = True
        call_bonus.data_hm_booking_confirmed = datetime.utcnow()
        db.session.flush()
        dispatch_call_bonus_webhook(call_bonus)
    else:
        call_bonus.status = CallBonusStatusEnum.non_interessato
        call_bonus.data_interesse = datetime.utcnow()
        motivazione = payload.get("motivazione", "").strip()
        if motivazione:
            call_bonus.motivazione_rifiuto = motivazione

    db.session.commit()

    return jsonify({
        "success": True,
        "call_bonus_id": call_bonus.id,
        "status": call_bonus.status.value,
        "message": "Interesse confermato." if interested else "Paziente non interessato.",
    })


@api_bp.route("/<int:cliente_id>/call-bonus-request", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def api_call_bonus_request(cliente_id: int):
    """Crea richiesta call bonus + analisi AI + matching professionisti."""
    from corposostenibile.blueprints.team.ai_matching_service import AIMatchingService
    from corposostenibile.models import CallBonus, CallBonusStatusEnum
    import json as _json

    cliente = db.session.get(Cliente, cliente_id)
    if not cliente:
        abort(HTTPStatus.NOT_FOUND, description="Cliente non trovato.")

    if not _is_assigned_to_cliente(current_user, cliente):
        abort(HTTPStatus.FORBIDDEN, description="Non sei assegnato a questo paziente.")

    payload = request.get_json() or {}
    tipo_str = payload.get("tipo_professionista", "").strip()
    note_richiesta = payload.get("note_richiesta", "").strip()

    if not tipo_str:
        abort(HTTPStatus.BAD_REQUEST, description="Seleziona un tipo di professionista.")

    try:
        tipo = TipoProfessionistaEnum(tipo_str)
    except ValueError:
        abort(HTTPStatus.BAD_REQUEST, description=f"Tipo professionista non valido: {tipo_str}")

    # Map tipo to AI role
    role_map = {
        TipoProfessionistaEnum.nutrizionista: "nutrition",
        TipoProfessionistaEnum.coach: "coach",
        TipoProfessionistaEnum.psicologa: "psychology",
    }
    target_role = role_map.get(tipo, "nutrition")

    # 1. Create CallBonus with professionista_id=NULL
    call_bonus = CallBonus(
        cliente_id=cliente_id,
        professionista_id=None,
        tipo_professionista=tipo,
        status=CallBonusStatusEnum.proposta,
        data_richiesta=date.today(),
        created_by_id=current_user.id,
        note_richiesta=note_richiesta,
    )
    db.session.add(call_bonus)
    db.session.flush()

    # 2. Compose story from note_richiesta + storia_cliente
    story_parts = []
    if note_richiesta:
        story_parts.append(f"Richiesta call bonus: {note_richiesta}")
    if cliente.storia_cliente:
        story_parts.append(f"Storia cliente: {cliente.storia_cliente}")
    story = "\n".join(story_parts) if story_parts else "Nessuna informazione disponibile."

    # 3. AI analysis + matching
    try:
        analysis = AIMatchingService.extract_lead_criteria(story, target_role=target_role)
        criteria = analysis.get("criteria", [])
        all_matches = AIMatchingService.match_professionals(criteria)

        # Filter only for the requested type
        category_map = {
            TipoProfessionistaEnum.nutrizionista: "nutrizione",
            TipoProfessionistaEnum.coach: "coach",
            TipoProfessionistaEnum.psicologa: "psicologia",
        }
        category = category_map.get(tipo, "nutrizione")
        matches = all_matches.get(category, [])

        # Add link_call_bonus from assignment_ai_notes for each match
        for match in matches:
            prof = db.session.get(User, match["id"])
            if prof:
                ai_notes = prof.assignment_ai_notes or {}
                if isinstance(ai_notes, str):
                    try:
                        ai_notes = _json.loads(ai_notes)
                    except (ValueError, TypeError):
                        ai_notes = {}
                match["link_call_bonus"] = ai_notes.get("link_call_bonus", "")

        # 4. Save analysis and matches on the record
        call_bonus.ai_analysis = analysis
        call_bonus.ai_matches = matches
        db.session.commit()

        return jsonify({
            "success": True,
            "call_bonus_id": call_bonus.id,
            "analysis": analysis,
            "matches": matches,
        }), HTTPStatus.CREATED

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore AI call bonus: {e}")
        # Still save the call_bonus without AI data
        db.session.add(call_bonus)
        db.session.commit()
        return jsonify({
            "success": True,
            "call_bonus_id": call_bonus.id,
            "analysis": {"summary": "Analisi AI non disponibile", "criteria": [], "suggested_focus": []},
            "matches": [],
            "ai_error": str(e),
        }), HTTPStatus.CREATED


@api_bp.route("/call-bonus-select/<int:call_bonus_id>", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def api_call_bonus_select_professional(call_bonus_id: int):
    """Seleziona professionista per la call bonus → ritorna link_call_bonus."""
    from corposostenibile.models import CallBonus
    import json as _json

    call_bonus = db.session.get(CallBonus, call_bonus_id)
    if not call_bonus:
        abort(HTTPStatus.NOT_FOUND, description="Call bonus non trovata.")
    cliente = db.session.get(Cliente, call_bonus.cliente_id)
    if not cliente:
        abort(HTTPStatus.NOT_FOUND, description="Cliente non trovato.")
    if not _is_assigned_to_cliente(current_user, cliente):
        abort(HTTPStatus.FORBIDDEN, description="Non sei assegnato a questo paziente.")

    payload = request.get_json() or {}
    professional_id = payload.get("professional_id")
    if not professional_id:
        abort(HTTPStatus.BAD_REQUEST, description="Seleziona un professionista.")

    prof = db.session.get(User, professional_id)
    if not prof:
        abort(HTTPStatus.NOT_FOUND, description="Professionista non trovato.")

    # Update call bonus with selected professional
    call_bonus.professionista_id = professional_id
    call_bonus.status = CallBonusStatusEnum.accettata
    call_bonus.data_risposta = date.today()

    db.session.commit()

    # Create a Task for the assigned professional (so they get notified)
    try:
        from corposostenibile.models import Task, TaskStatusEnum, TaskPriorityEnum, TaskCategoryEnum

        task_title = f"Call Bonus — Rispondi interesse paziente (CB#{call_bonus.id})"
        base_url = (current_app.config.get("BASE_URL") or "").rstrip("/")
        path = f"/clienti-dettaglio/{cliente.cliente_id}?tab=call_bonus"
        detail_url = f"{base_url}{path}" if base_url else path

        existing = (
            Task.query
            .filter(
                Task.assignee_id == prof.id,
                Task.title == task_title,
                Task.status.in_([TaskStatusEnum.todo, TaskStatusEnum.in_progress]),
            )
            .first()
        )
        if not existing:
            t = Task(
                title=task_title,
                description=(
                    f"Paziente: {getattr(cliente, 'nome_cognome', '')}\n"
                    f"Richiesta da: {current_user.full_name}\n"
                    f"Note: {call_bonus.note_richiesta or '-'}\n"
                    f"Apri: {detail_url}\n"
                ),
                category=TaskCategoryEnum.generico,
                priority=TaskPriorityEnum.high,
                status=TaskStatusEnum.todo,
                assignee_id=prof.id,
                client_id=cliente.cliente_id,
                payload={"call_bonus_id": call_bonus.id, "cliente_id": cliente.cliente_id},
            )
            db.session.add(t)
            db.session.commit()

            try:
                from corposostenibile.blueprints.tasks.teams_tasks import send_task_notification_task
                send_task_notification_task.delay(t.id, assigner_name=current_user.full_name)
            except Exception:
                current_app.logger.warning(
                    "[call_bonus] Impossibile accodare notifica Teams per task %s", t.id
                )
    except Exception:
        current_app.logger.exception("[call_bonus] Errore creazione task per professionista assegnato")
        try:
            db.session.rollback()
        except Exception:
            pass

    # Get link_call_bonus from professional's ai_notes
    ai_notes = prof.assignment_ai_notes or {}
    if isinstance(ai_notes, str):
        try:
            ai_notes = _json.loads(ai_notes)
        except (ValueError, TypeError):
            ai_notes = {}
    link_call_bonus = ai_notes.get("link_call_bonus", "")

    return jsonify({
        "success": True,
        "call_bonus_id": call_bonus.id,
        "professional_name": prof.full_name,
        "link_call_bonus": link_call_bonus,
    })


@api_bp.route("/call-bonus-confirm/<int:call_bonus_id>", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def api_call_bonus_confirm_booking(call_bonus_id: int):
    """Conferma prenotazione call bonus."""
    from corposostenibile.models import CallBonus

    call_bonus = db.session.get(CallBonus, call_bonus_id)
    if not call_bonus:
        abort(HTTPStatus.NOT_FOUND, description="Call bonus non trovata.")
    cliente = db.session.get(Cliente, call_bonus.cliente_id)
    if not cliente:
        abort(HTTPStatus.NOT_FOUND, description="Cliente non trovato.")
    is_internal_owner = (
        getattr(current_user, "is_admin", False)
        or call_bonus.created_by_id == current_user.id
        or call_bonus.professionista_id == current_user.id
    )
    if not is_internal_owner:
        role = getattr(current_user, "role", None)
        role_value = role.value if hasattr(role, "value") else str(role or "")
        if role_value == "professionista" or not _is_assigned_to_cliente(current_user, cliente):
            abort(HTTPStatus.FORBIDDEN, description="Non autorizzato a confermare questa call bonus.")

    call_bonus.booking_confirmed = True
    call_bonus.data_booking_confirmed = datetime.utcnow()

    db.session.commit()

    return jsonify({
        "success": True,
        "call_bonus_id": call_bonus.id,
        "message": "Prenotazione confermata.",
    })


@api_bp.route("/call-bonus-decline/<int:call_bonus_id>", methods=["POST"])
@permission_required(CustomerPerm.VIEW)
def api_call_bonus_decline(call_bonus_id: int):
    """Professionista rifiuta la call bonus assegnata."""
    from corposostenibile.models import CallBonus

    call_bonus = db.session.get(CallBonus, call_bonus_id)
    if not call_bonus:
        abort(HTTPStatus.NOT_FOUND, description="Call bonus non trovata.")

    if call_bonus.professionista_id != current_user.id:
        abort(HTTPStatus.FORBIDDEN, description="Non sei il professionista assegnato.")

    call_bonus.status = CallBonusStatusEnum.rifiutata
    call_bonus.data_risposta = date.today()

    db.session.commit()

    return jsonify({
        "success": True,
        "call_bonus_id": call_bonus.id,
        "message": "Call bonus rifiutata.",
    })


# --------------------------------------------------------------------------- #
#  Call Rinnovo                                                              #
# --------------------------------------------------------------------------- #
def _serialize_call_rinnovo(item) -> dict[str, Any]:
    return {
        "id": item.id,
        "cliente_id": item.cliente_id,
        "professionista_id": item.professionista_id,
        "professionista_name": getattr(item.professionista, "full_name", None),
        "tipo_professionista": item.tipo_professionista.value if hasattr(item.tipo_professionista, 'value') else item.tipo_professionista,
        "status": item.status.value if hasattr(item.status, 'value') else item.status,
        "data_richiesta": item.data_richiesta.isoformat() if item.data_richiesta else None,
        "data_risposta": item.data_risposta.isoformat() if item.data_risposta else None,
        "data_conferma_hm": item.data_conferma_hm.isoformat() if item.data_conferma_hm else None,
        "note_richiesta": item.note_richiesta,
        "booking_confirmed": item.booking_confirmed,
        "note_hm": item.note_hm,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


@api_bp.route("/<int:cliente_id>/call-rinnovo-history", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_call_rinnovo_history(cliente_id: int):
    """Storico call rinnovo del paziente."""
    cliente = db.session.get(Cliente, cliente_id)
    if not cliente:
        abort(HTTPStatus.NOT_FOUND, description="Cliente non trovato.")
    
    rows = db.session.query(CallRinnovo).filter(
        CallRinnovo.cliente_id == cliente_id
    ).order_by(CallRinnovo.data_richiesta.desc()).all()
    
    return jsonify({
        "data": [_serialize_call_rinnovo(r) for r in rows]
    })


@api_bp.route("/<int:cliente_id>/call-rinnovo-request", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def api_call_rinnovo_request(cliente_id: int):
    """Crea richiesta call rinnovo."""
    from corposostenibile.models import CallRinnovo, CallRinnovoStatusEnum
    
    cliente = db.session.get(Cliente, cliente_id)
    if not cliente:
        abort(HTTPStatus.NOT_FOUND, description="Cliente non trovato.")
    
    data = request.get_json() or {}
    
    call_rinnovo = CallRinnovo(
        cliente_id=cliente_id,
        tipo_professionista=data.get("tipo_professionista"),
        note_richiesta=data.get("note_richiesta"),
        created_by_id=current_user.id,
        status=CallRinnovoStatusEnum.proposta,
        data_richiesta=date.today(),
    )
    
    db.session.add(call_rinnovo)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "data": _serialize_call_rinnovo(call_rinnovo)
    }), HTTPStatus.CREATED


@api_bp.route("/call-rinnovo/<int:call_rinnovo_id>/accept", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def api_call_rinnovo_accept(call_rinnovo_id: int):
    """Accetta call rinnovo."""
    from corposostenibile.models import CallRinnovo, CallRinnovoStatusEnum
    
    call_rinnovo = db.session.get(CallRinnovo, call_rinnovo_id)
    if not call_rinnovo:
        abort(HTTPStatus.NOT_FOUND, description="Call rinnovo non trovata.")
    
    call_rinnovo.status = CallRinnovoStatusEnum.accettata
    call_rinnovo.data_risposta = date.today()
    db.session.commit()
    
    return jsonify({
        "success": True,
        "data": _serialize_call_rinnovo(call_rinnovo)
    })


@api_bp.route("/call-rinnovo/<int:call_rinnovo_id>/decline", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def api_call_rinnovo_decline(call_rinnovo_id: int):
    """Rifiuta call rinnovo."""
    from corposostenibile.models import CallRinnovo, CallRinnovoStatusEnum
    
    call_rinnovo = db.session.get(CallRinnovo, call_rinnovo_id)
    if not call_rinnovo:
        abort(HTTPStatus.NOT_FOUND, description="Call rinnovo non trovata.")
    
    call_rinnovo.status = CallRinnovoStatusEnum.rifiutata
    call_rinnovo.data_risposta = date.today()
    db.session.commit()
    
    return jsonify({
        "success": True,
        "data": _serialize_call_rinnovo(call_rinnovo)
    })


@api_bp.route("/call-rinnovo/<int:call_rinnovo_id>/confirm", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def api_call_rinnovo_confirm(call_rinnovo_id: int):
    """Conferma call rinnovo completata."""
    from corposostenibile.models import CallRinnovo, CallRinnovoStatusEnum
    
    call_rinnovo = db.session.get(CallRinnovo, call_rinnovo_id)
    if not call_rinnovo:
        abort(HTTPStatus.NOT_FOUND, description="Call rinnovo non trovata.")
    
    data = request.get_json() or {}
    call_rinnovo.status = CallRinnovoStatusEnum.confermata
    call_rinnovo.data_conferma_hm = date.today()
    call_rinnovo.note_hm = data.get("note_hm")
    db.session.commit()
    
    return jsonify({
        "success": True,
        "data": _serialize_call_rinnovo(call_rinnovo)
    })


# --------------------------------------------------------------------------- #
#  Video Feedback                                                            #
# --------------------------------------------------------------------------- #
def _serialize_video_feedback(item) -> dict[str, Any]:
    return {
        "id": item.id,
        "cliente_id": item.cliente_id,
        "professionista_id": item.professionista_id,
        "professionista_name": getattr(item.professionista, "full_name", None),
        "tipo_professionista": item.tipo_professionista.value if hasattr(item.tipo_professionista, 'value') else item.tipo_professionista,
        "status": item.status.value if hasattr(item.status, 'value') else item.status,
        "data_richiesta": item.data_richiesta.isoformat() if item.data_richiesta else None,
        "data_risposta": item.data_risposta.isoformat() if item.data_risposta else None,
        "data_conferma_hm": item.data_conferma_hm.isoformat() if item.data_conferma_hm else None,
        "note_richiesta": item.note_richiesta,
        "booking_confirmed": item.booking_confirmed,
        "loom_link": item.loom_link,
        "note_hm": item.note_hm,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


@api_bp.route("/<int:cliente_id>/video-feedback-history", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_video_feedback_history(cliente_id: int):
    """Storico video feedback del paziente."""
    cliente = db.session.get(Cliente, cliente_id)
    if not cliente:
        abort(HTTPStatus.NOT_FOUND, description="Cliente non trovato.")
    
    rows = db.session.query(VideoFeedback).filter(
        VideoFeedback.cliente_id == cliente_id
    ).order_by(VideoFeedback.data_richiesta.desc()).all()
    
    return jsonify({
        "data": [_serialize_video_feedback(r) for r in rows]
    })


@api_bp.route("/<int:cliente_id>/video-feedback-request", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def api_video_feedback_request(cliente_id: int):
    """Crea richiesta video feedback."""
    from corposostenibile.models import VideoFeedback, VideoFeedbackStatusEnum
    
    cliente = db.session.get(Cliente, cliente_id)
    if not cliente:
        abort(HTTPStatus.NOT_FOUND, description="Cliente non trovato.")
    
    data = request.get_json() or {}
    
    video_feedback = VideoFeedback(
        cliente_id=cliente_id,
        tipo_professionista=data.get("tipo_professionista"),
        note_richiesta=data.get("note_richiesta"),
        created_by_id=current_user.id,
        status=VideoFeedbackStatusEnum.proposta,
        data_richiesta=date.today(),
    )
    
    db.session.add(video_feedback)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "data": _serialize_video_feedback(video_feedback)
    }), HTTPStatus.CREATED


@api_bp.route("/video-feedback/<int:video_feedback_id>/accept", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def api_video_feedback_accept(video_feedback_id: int):
    """Accetta video feedback."""
    from corposostenibile.models import VideoFeedback, VideoFeedbackStatusEnum
    
    video_feedback = db.session.get(VideoFeedback, video_feedback_id)
    if not video_feedback:
        abort(HTTPStatus.NOT_FOUND, description="Video feedback non trovato.")
    
    video_feedback.status = VideoFeedbackStatusEnum.accettata
    video_feedback.data_risposta = date.today()
    db.session.commit()
    
    return jsonify({
        "success": True,
        "data": _serialize_video_feedback(video_feedback)
    })


@api_bp.route("/video-feedback/<int:video_feedback_id>/complete", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def api_video_feedback_complete(video_feedback_id: int):
    """Completa video feedback con link loom."""
    from corposostenibile.models import VideoFeedback, VideoFeedbackStatusEnum
    
    video_feedback = db.session.get(VideoFeedback, video_feedback_id)
    if not video_feedback:
        abort(HTTPStatus.NOT_FOUND, description="Video feedback non trovato.")
    
    data = request.get_json() or {}
    video_feedback.status = VideoFeedbackStatusEnum.completata
    video_feedback.data_conferma_hm = date.today()
    video_feedback.loom_link = data.get("loom_link")
    video_feedback.note_hm = data.get("note_hm")
    db.session.commit()
    
    return jsonify({
        "success": True,
        "data": _serialize_video_feedback(video_feedback)
    })


# --------------------------------------------------------------------------- #
#  Video Review (Marketing Tab)                                               #
# --------------------------------------------------------------------------- #
def _serialize_video_review_request(item: VideoReviewRequest) -> dict[str, Any]:
    hm_calendar_link = ""
    hm_user = item.hm_user or None
    if hm_user is not None:
        import json as _json

        ai_notes = hm_user.assignment_ai_notes or {}
        if isinstance(ai_notes, str):
            try:
                ai_notes = _json.loads(ai_notes)
            except (ValueError, TypeError):
                ai_notes = {}
        if isinstance(ai_notes, dict):
            hm_calendar_link = str(ai_notes.get("link_calendario") or "").strip()

    return {
        "id": item.id,
        "cliente_id": item.cliente_id,
        "status": item.status,
        "booking_confirmed_at": item.booking_confirmed_at.isoformat() if item.booking_confirmed_at else None,
        "booking_date": item.booking_date.isoformat() if item.booking_date else None,
        "booking_time": item.booking_time.isoformat() if item.booking_time else None,
        "hm_confirmed_at": item.hm_confirmed_at.isoformat() if item.hm_confirmed_at else None,
        "loom_link": item.loom_link,
        "hm_note": item.hm_note,
        "requested_by_user_id": item.requested_by_user_id,
        "requested_by_name": getattr(item.requested_by_user, "full_name", None),
        "hm_user_id": item.hm_user_id,
        "hm_name": getattr(item.hm_user, "full_name", None),
        "hm_calendar_link": hm_calendar_link,
    }


def _is_valid_absolute_url(url_value: str) -> bool:
    try:
        parsed = urlparse(url_value)
    except Exception:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


@api_bp.route("/<int:cliente_id>/video-review-requests", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_video_review_requests(cliente_id: int):
    cliente = db.session.get(Cliente, cliente_id)
    if not cliente:
        abort(HTTPStatus.NOT_FOUND, description="Cliente non trovato.")
    if not _is_assigned_to_cliente(current_user, cliente):
        abort(HTTPStatus.FORBIDDEN, description="Non sei assegnato a questo paziente.")

    rows = (
        db.session.query(VideoReviewRequest)
        .filter(VideoReviewRequest.cliente_id == cliente_id)
        .order_by(VideoReviewRequest.created_at.desc(), VideoReviewRequest.id.desc())
        .all()
    )
    return jsonify({"success": True, "data": [_serialize_video_review_request(r) for r in rows]})


@api_bp.route("/<int:cliente_id>/video-review-requests/booked", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def api_video_review_booked(cliente_id: int):
    cliente = db.session.get(Cliente, cliente_id)
    if not cliente:
        abort(HTTPStatus.NOT_FOUND, description="Cliente non trovato.")
    if not _is_assigned_to_cliente(current_user, cliente):
        abort(HTTPStatus.FORBIDDEN, description="Non sei assegnato a questo paziente.")
    if not getattr(cliente, "health_manager_id", None):
        abort(
            HTTPStatus.CONFLICT,
            description="Nessun Health Manager assegnato al paziente: assegna HM prima della prenotazione video recensione.",
        )

    existing_open = (
        db.session.query(VideoReviewRequest)
        .filter(
            VideoReviewRequest.cliente_id == cliente_id,
            VideoReviewRequest.status == "booked",
        )
        .order_by(VideoReviewRequest.id.desc())
        .first()
    )
    if existing_open:
        return jsonify({
            "success": True,
            "data": _serialize_video_review_request(existing_open),
            "message": "Esiste già una richiesta video recensione in stato prenotata.",
        }), HTTPStatus.OK

    payload = request.get_json(silent=True) or {}
    booking_date_str = (payload.get("booking_date") or "").strip()
    booking_time_str = (payload.get("booking_time") or "").strip()

    booking_date = None
    if booking_date_str:
        try:
            booking_date = datetime.strptime(booking_date_str, "%Y-%m-%d").date()
        except ValueError:
            abort(HTTPStatus.BAD_REQUEST, description="Formato data non valido. Usa YYYY-MM-DD.")

    booking_time = None
    if booking_time_str:
        try:
            booking_time = datetime.strptime(booking_time_str, "%H:%M").time()
        except ValueError:
            abort(HTTPStatus.BAD_REQUEST, description="Formato orario non valido. Usa HH:MM.")

    request_item = VideoReviewRequest(
        cliente_id=cliente_id,
        requested_by_user_id=current_user.id,
        hm_user_id=cliente.health_manager_id,
        status="booked",
        booking_confirmed_at=datetime.utcnow(),
        booking_date=booking_date,
        booking_time=booking_time,
    )
    db.session.add(request_item)
    db.session.commit()
    return jsonify({
        "success": True,
        "data": _serialize_video_review_request(request_item),
        "message": "Prenotazione video recensione registrata.",
    }), HTTPStatus.CREATED


@api_bp.route("/video-review-requests/<int:request_id>/hm-confirm", methods=["POST"])
@permission_required(CustomerPerm.EDIT)
def api_video_review_hm_confirm(request_id: int):
    item = db.session.get(VideoReviewRequest, request_id)
    if not item:
        abort(HTTPStatus.NOT_FOUND, description="Richiesta video recensione non trovata.")

    cliente = db.session.get(Cliente, item.cliente_id)
    if not cliente:
        abort(HTTPStatus.NOT_FOUND, description="Cliente non trovato.")

    is_admin = bool(getattr(current_user, "is_admin", False))
    role = getattr(current_user, "role", None)
    role_value = role.value if hasattr(role, "value") else str(role or "")
    is_hm = role_value == "health_manager"
    if not (is_admin or (is_hm and getattr(cliente, "health_manager_id", None) == current_user.id)):
        abort(HTTPStatus.FORBIDDEN, description="Solo HM assegnato o admin possono confermare.")

    payload = request.get_json(silent=True) or {}
    loom_link = (payload.get("loom_link") or "").strip()
    hm_note = (payload.get("hm_note") or "").strip()
    if not loom_link:
        abort(HTTPStatus.BAD_REQUEST, description="Campo 'loom_link' obbligatorio.")
    if not _is_valid_absolute_url(loom_link):
        abort(HTTPStatus.BAD_REQUEST, description="Loom link non valido.")

    item.status = "hm_confirmed"
    item.hm_confirmed_at = datetime.utcnow()
    item.loom_link = loom_link
    item.hm_note = hm_note or None
    item.hm_user_id = getattr(cliente, "health_manager_id", None) or current_user.id

    db.session.commit()
    return jsonify({
        "success": True,
        "data": _serialize_video_review_request(item),
        "message": "Video recensione confermata da HM.",
    }), HTTPStatus.OK


# --------------------------------------------------------------------------- #
#  Trustpilot Integration                                                     #
# --------------------------------------------------------------------------- #

def _can_manage_trustpilot(user) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_admin", False):
        return True
    role = getattr(user, "role", None)
    role_val = role.value if hasattr(role, "value") else str(role) if role else ""
    specialty = getattr(user, "specialty", None)
    spec_val = specialty.value if hasattr(specialty, "value") else str(specialty) if specialty else ""
    return role_val == "health_manager" or spec_val == "cco"


def _require_trustpilot_manager_or_403():
    if not _can_manage_trustpilot(current_user):
        abort(HTTPStatus.FORBIDDEN, description="Operazione Trustpilot non consentita.")


def _is_trustpilot_webhook_configured() -> bool:
    username = (current_app.config.get("TRUSTPILOT_WEBHOOK_USERNAME") or "").strip()
    password = (current_app.config.get("TRUSTPILOT_WEBHOOK_PASSWORD") or "").strip()
    return bool(username and password)


def _get_trustpilot_missing_config() -> list[str]:
    required = [
        "TRUSTPILOT_API_KEY",
        "TRUSTPILOT_API_SECRET",
        "TRUSTPILOT_BUSINESS_UNIT_ID",
    ]
    missing = []
    for key in required:
        if not (current_app.config.get(key) or "").strip():
            missing.append(key)
    return missing


def _parse_iso_datetime(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _extract_trustpilot_webhook_fields(payload: dict[str, Any]) -> dict[str, Any]:
    event_type = (
        payload.get("eventType")
        or payload.get("event_type")
        or payload.get("type")
        or payload.get("action")
        or ""
    )
    review = payload.get("review") if isinstance(payload.get("review"), dict) else {}
    invitation = payload.get("invitation") if isinstance(payload.get("invitation"), dict) else {}

    reference_id = (
        payload.get("referenceId")
        or payload.get("reference_id")
        or invitation.get("referenceId")
        or invitation.get("reference_id")
        or review.get("referenceId")
        or review.get("reference_id")
    )
    invitation_id = (
        payload.get("invitationId")
        or payload.get("invitation_id")
        or invitation.get("id")
        or invitation.get("invitationId")
    )
    review_id = (
        payload.get("reviewId")
        or payload.get("review_id")
        or review.get("id")
        or review.get("reviewId")
    )

    stars_raw = payload.get("stars")
    if stars_raw is None:
        stars_raw = review.get("stars")
    try:
        stars = int(stars_raw) if stars_raw is not None else None
    except (TypeError, ValueError):
        stars = None

    title = payload.get("title") or review.get("title")
    text = payload.get("text") or payload.get("content") or review.get("text") or review.get("content")
    published_at = (
        _parse_iso_datetime(payload.get("publishedAt"))
        or _parse_iso_datetime(payload.get("published_at"))
        or _parse_iso_datetime(review.get("publishedAt"))
        or _parse_iso_datetime(review.get("published_at"))
    )
    deleted_at = (
        _parse_iso_datetime(payload.get("deletedAt"))
        or _parse_iso_datetime(payload.get("deleted_at"))
        or _parse_iso_datetime(review.get("deletedAt"))
        or _parse_iso_datetime(review.get("deleted_at"))
    )

    event_lower = str(event_type or "").strip().lower()
    is_deleted_event = any(k in event_lower for k in ("delete", "removed", "unpublish"))
    is_published_event = any(k in event_lower for k in ("publish", "created", "review"))

    return {
        "event_type": str(event_type or ""),
        "reference_id": reference_id,
        "invitation_id": invitation_id,
        "review_id": review_id,
        "stars": stars,
        "title": title,
        "text": text,
        "published_at": published_at,
        "deleted_at": deleted_at,
        "is_deleted_event": is_deleted_event,
        "is_published_event": is_published_event,
    }


def _locate_trustpilot_review(payload_fields: dict[str, Any]) -> TrustpilotReview | None:
    review_id = payload_fields.get("review_id")
    reference_id = payload_fields.get("reference_id")
    invitation_id = payload_fields.get("invitation_id")

    if review_id:
        found = db.session.query(TrustpilotReview).filter(
            TrustpilotReview.trustpilot_review_id == str(review_id)
        ).first()
        if found:
            return found

    if reference_id:
        found = db.session.query(TrustpilotReview).filter(
            TrustpilotReview.trustpilot_reference_id == str(reference_id)
        ).order_by(TrustpilotReview.id.desc()).first()
        if found:
            return found

    if invitation_id:
        found = db.session.query(TrustpilotReview).filter(
            TrustpilotReview.trustpilot_invitation_id == str(invitation_id)
        ).order_by(TrustpilotReview.id.desc()).first()
        if found:
            return found

    return None


def _serialize_trustpilot_review(review: TrustpilotReview) -> dict:
    return {
        "id": review.id,
        "cliente_id": review.cliente_id,
        "requested_by_user_id": review.richiesta_da_professionista_id,
        "requested_by_name": getattr(review.richiesta_da, "full_name", None),
        "data_richiesta": review.data_richiesta.isoformat() if review.data_richiesta else None,
        "invitation_method": review.invitation_method,
        "invitation_status": review.invitation_status,
        "trustpilot_reference_id": review.trustpilot_reference_id,
        "trustpilot_invitation_id": review.trustpilot_invitation_id,
        "trustpilot_review_id": review.trustpilot_review_id,
        "trustpilot_link": review.trustpilot_link,
        "pubblicata": bool(review.pubblicata),
        "data_pubblicazione": review.data_pubblicazione.isoformat() if review.data_pubblicazione else None,
        "stelle": review.stelle,
        "titolo_recensione": review.titolo_recensione,
        "testo_recensione": review.testo_recensione,
        "deleted_at_trustpilot": review.deleted_at_trustpilot.isoformat() if review.deleted_at_trustpilot else None,
        "webhook_received_at": review.webhook_received_at.isoformat() if review.webhook_received_at else None,
        "created_at": review.created_at.isoformat() if review.created_at else None,
        "updated_at": review.updated_at.isoformat() if review.updated_at else None,
    }


def _get_latest_trustpilot_review(cliente_id: int):
    return (
        db.session.query(TrustpilotReview)
        .filter(TrustpilotReview.cliente_id == cliente_id)
        .order_by(TrustpilotReview.data_richiesta.desc(), TrustpilotReview.id.desc())
        .first()
    )


def _get_trustpilot_history(cliente_id: int, limit: int = 20):
    return (
        db.session.query(TrustpilotReview)
        .filter(TrustpilotReview.cliente_id == cliente_id)
        .order_by(TrustpilotReview.data_richiesta.desc(), TrustpilotReview.id.desc())
        .limit(limit)
        .all()
    )


@api_bp.route("/trustpilot-overview", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_trustpilot_overview():
    """Panoramica Trustpilot: tutti i clienti attivi con lo stato review."""
    from sqlalchemy import outerjoin
    from sqlalchemy.orm import aliased

    page = max(request.args.get('page', 1, type=int), 1)
    per_page = min(max(request.args.get('per_page', 25, type=int), 1), 100)
    search = (request.args.get('q') or '').strip()
    hm_filter = request.args.get('health_manager_id', type=int)
    status_filter = request.args.get('status', '').strip()  # all, pending, reviewed, none

    query = db.session.query(Cliente).filter(
        Cliente.stato_cliente == StatoClienteEnum.attivo,
        Cliente.show_in_clienti_lista == True,
    )
    if search:
        query = query.filter(Cliente.nome_cognome.ilike(f'%{search}%'))
    if hm_filter:
        query = query.filter(Cliente.health_manager_id == hm_filter)

    query = query.order_by(Cliente.nome_cognome)
    total = query.count()
    clienti = query.offset((page - 1) * per_page).limit(per_page).all()

    client_ids = [c.cliente_id for c in clienti]
    reviews_map = {}
    if client_ids:
        latest_reviews = (
            db.session.query(TrustpilotReview)
            .filter(TrustpilotReview.cliente_id.in_(client_ids))
            .order_by(TrustpilotReview.data_richiesta.desc())
            .all()
        )
        for r in latest_reviews:
            if r.cliente_id not in reviews_map:
                reviews_map[r.cliente_id] = []
            reviews_map[r.cliente_id].append(r)

    data = []
    for c in clienti:
        reviews = reviews_map.get(c.cliente_id, [])
        latest = reviews[0] if reviews else None
        has_published = any(r.pubblicata for r in reviews)
        best_stars = max((r.stelle for r in reviews if r.stelle), default=None)

        row = {
            'cliente_id': c.cliente_id,
            'nome_cognome': c.nome_cognome,
            'mail': c.mail,
            'stato_cliente': c.stato_cliente.value if c.stato_cliente else None,
            'programma_attuale': c.programma_attuale,
            'health_manager_user': {
                'id': c.health_manager_user.id,
                'full_name': c.health_manager_user.full_name,
            } if c.health_manager_user else None,
            'trustpilot': {
                'total_inviti': len(reviews),
                'ha_recensione': has_published,
                'stelle_migliore': best_stars,
                'ultimo_invito': _serialize_trustpilot_review(latest) if latest else None,
            },
        }

        if status_filter == 'reviewed' and not has_published:
            continue
        if status_filter == 'pending' and not (latest and not has_published):
            continue
        if status_filter == 'none' and len(reviews) > 0:
            continue

        data.append(row)

    # Count stats
    all_client_ids_q = db.session.query(Cliente.cliente_id).filter(
        Cliente.stato_cliente == StatoClienteEnum.attivo,
        Cliente.show_in_clienti_lista == True,
    )
    if hm_filter:
        all_client_ids_q = all_client_ids_q.filter(Cliente.health_manager_id == hm_filter)
    all_ids = [r[0] for r in all_client_ids_q.all()]

    reviewed_ids = set()
    pending_ids = set()
    if all_ids:
        all_reviews = db.session.query(
            TrustpilotReview.cliente_id, TrustpilotReview.pubblicata
        ).filter(TrustpilotReview.cliente_id.in_(all_ids)).all()
        clients_with_reviews = set()
        for cid, pub in all_reviews:
            clients_with_reviews.add(cid)
            if pub:
                reviewed_ids.add(cid)
        pending_ids = clients_with_reviews - reviewed_ids

    return jsonify({
        'success': True,
        'enabled': TrustpilotService.is_enabled(),
        'missing_config': _get_trustpilot_missing_config(),
        'webhook_configured': _is_trustpilot_webhook_configured(),
        'data': data,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': max(1, (total + per_page - 1) // per_page),
        },
        'counts': {
            'totale_attivi': len(all_ids),
            'con_recensione': len(reviewed_ids),
            'in_attesa': len(pending_ids),
            'mai_invitati': len(all_ids) - len(reviewed_ids) - len(pending_ids),
        },
    })


@api_bp.route("/<int:cliente_id>/trustpilot", methods=["GET"])
@permission_required(CustomerPerm.VIEW)
def api_trustpilot_status(cliente_id: int):
    cliente = customers_repo.get_one(cliente_id)
    latest_review = _get_latest_trustpilot_review(cliente_id)
    history = _get_trustpilot_history(cliente_id, limit=10)
    missing_config = _get_trustpilot_missing_config()

    return jsonify({
        "success": True,
        "enabled": TrustpilotService.is_enabled(),
        "missing_config": missing_config,
        "is_fully_configured": len(missing_config) == 0,
        "webhook_configured": _is_trustpilot_webhook_configured(),
        "can_manage": _can_manage_trustpilot(current_user),
        "email_configured": bool(
            current_app.config.get("TRUSTPILOT_EMAIL_TEMPLATE_ID")
            and current_app.config.get("TRUSTPILOT_SENDER_EMAIL")
            and current_app.config.get("TRUSTPILOT_REPLY_TO")
        ),
        "cliente": {
            "cliente_id": cliente.cliente_id,
            "nome_cognome": cliente.nome_cognome,
            "mail": cliente.mail,
        },
        "latest": _serialize_trustpilot_review(latest_review) if latest_review else None,
        "history": [_serialize_trustpilot_review(item) for item in history],
    })


@api_bp.route("/<int:cliente_id>/trustpilot/link", methods=["POST"])
@permission_required(CustomerPerm.VIEW)
def api_trustpilot_generate_link(cliente_id: int):
    _require_trustpilot_manager_or_403()
    cliente = customers_repo.get_one(cliente_id)

    if not cliente.mail:
        abort(HTTPStatus.BAD_REQUEST, description="Il paziente non ha una email configurata.")

    payload = request.get_json(silent=True) or {}
    locale = (payload.get("locale") or TrustpilotService.get_default_locale()).strip()

    try:
        TrustpilotService.ensure_enabled()
        reference_id = TrustpilotService.generate_reference_id(cliente_id)
        response = TrustpilotService.create_invitation_link(
            email=cliente.mail,
            name=cliente.nome_cognome,
            reference_id=reference_id,
            locale=locale,
        )
    except TrustpilotConfigError as exc:
        abort(HTTPStatus.BAD_REQUEST, description=str(exc))
    except TrustpilotAPIError as exc:
        abort(HTTPStatus.BAD_GATEWAY, description=str(exc))

    invitation_link = response.get("url") or response.get("invitationLink") or response.get("href")
    invitation_id = response.get("id") or response.get("invitationId")

    review = TrustpilotReview(
        cliente_id=cliente.cliente_id,
        richiesta_da_professionista_id=current_user.id,
        data_richiesta=datetime.utcnow(),
        invitation_method="generated_link",
        invitation_status="generated",
        trustpilot_reference_id=reference_id,
        trustpilot_invitation_id=invitation_id,
        trustpilot_link=invitation_link,
        trustpilot_payload_last=response,
        note_interne="Link recensione generato via API Trustpilot.",
    )
    db.session.add(review)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Link Trustpilot generato.",
        "data": _serialize_trustpilot_review(review),
    }), HTTPStatus.CREATED


@api_bp.route("/<int:cliente_id>/trustpilot/invite", methods=["POST"])
@permission_required(CustomerPerm.VIEW)
def api_trustpilot_send_invite(cliente_id: int):
    _require_trustpilot_manager_or_403()
    cliente = customers_repo.get_one(cliente_id)

    if not cliente.mail:
        abort(HTTPStatus.BAD_REQUEST, description="Il paziente non ha una email configurata.")

    payload = request.get_json(silent=True) or {}
    locale = (payload.get("locale") or TrustpilotService.get_default_locale()).strip()
    tags = payload.get("tags") if isinstance(payload.get("tags"), list) else None

    try:
        TrustpilotService.ensure_enabled()
        reference_id = TrustpilotService.generate_reference_id(cliente_id)
        response = TrustpilotService.create_email_invitation(
            email=cliente.mail,
            name=cliente.nome_cognome,
            reference_id=reference_id,
            locale=locale,
            tags=tags,
        )
    except TrustpilotConfigError as exc:
        abort(HTTPStatus.BAD_REQUEST, description=str(exc))
    except TrustpilotAPIError as exc:
        abort(HTTPStatus.BAD_GATEWAY, description=str(exc))

    invitation_id = response.get("id") or response.get("invitationId")

    review = TrustpilotReview(
        cliente_id=cliente.cliente_id,
        richiesta_da_professionista_id=current_user.id,
        data_richiesta=datetime.utcnow(),
        invitation_method="email_invitation",
        invitation_status="sent",
        trustpilot_reference_id=reference_id,
        trustpilot_invitation_id=invitation_id,
        trustpilot_payload_last=response,
        note_interne="Invito email Trustpilot inviato via API.",
    )
    db.session.add(review)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Invito email Trustpilot inviato.",
        "data": _serialize_trustpilot_review(review),
    }), HTTPStatus.CREATED


@api_bp.route("/trustpilot/webhook", methods=["POST"])
@csrf.exempt
def api_trustpilot_webhook():
    """Webhook Trustpilot per aggiornare stato recensione e metadata."""
    if not _is_trustpilot_webhook_configured():
        return jsonify({
            "success": False,
            "error": "Webhook Trustpilot non configurato: mancano username/password.",
        }), HTTPStatus.SERVICE_UNAVAILABLE

    username = (current_app.config.get("TRUSTPILOT_WEBHOOK_USERNAME") or "").strip()
    password = (current_app.config.get("TRUSTPILOT_WEBHOOK_PASSWORD") or "").strip()
    auth = request.authorization

    if not auth or auth.username != username or auth.password != password:
        return jsonify({"success": False, "error": "Unauthorized webhook credentials."}), HTTPStatus.UNAUTHORIZED

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"success": False, "error": "Payload JSON non valido."}), HTTPStatus.BAD_REQUEST

    fields = _extract_trustpilot_webhook_fields(payload)
    review = _locate_trustpilot_review(fields)
    if not review:
        current_app.logger.warning(
            "[trustpilot] webhook ignored: no review match (event=%s, reference=%s, invitation=%s, review=%s)",
            fields.get("event_type"),
            fields.get("reference_id"),
            fields.get("invitation_id"),
            fields.get("review_id"),
        )
        return jsonify({"success": True, "message": "Webhook ricevuto ma nessuna review associata."}), HTTPStatus.ACCEPTED

    now = datetime.utcnow()
    review.webhook_received_at = now
    review.trustpilot_payload_last = payload

    if fields.get("review_id"):
        review.trustpilot_review_id = str(fields["review_id"])
    if fields.get("invitation_id"):
        review.trustpilot_invitation_id = str(fields["invitation_id"])
    if fields.get("reference_id"):
        review.trustpilot_reference_id = str(fields["reference_id"])

    stars = fields.get("stars")
    if stars is not None:
        review.stelle = stars
    if fields.get("title"):
        review.titolo_recensione = str(fields["title"])
    if fields.get("text"):
        review.testo_recensione = str(fields["text"])

    published_at = fields.get("published_at")
    if published_at:
        review.data_pubblicazione = published_at

    deleted_at = fields.get("deleted_at")
    if deleted_at:
        review.deleted_at_trustpilot = deleted_at

    if fields.get("is_deleted_event"):
        review.pubblicata = False
        review.invitation_status = "deleted"
        review.deleted_at_trustpilot = review.deleted_at_trustpilot or now
    elif fields.get("is_published_event") or review.stelle or review.data_pubblicazione:
        review.pubblicata = True
        review.invitation_status = "published"
        review.data_pubblicazione = review.data_pubblicazione or now
        if review.cliente:
            review.cliente.ultima_recensione_trustpilot_data = review.data_pubblicazione

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Webhook Trustpilot processato.",
        "event_type": fields.get("event_type"),
        "review_id": review.id,
    }), HTTPStatus.OK


# --------------------------------------------------------------------------- #
#  Blueprint registration helper                                              #
# --------------------------------------------------------------------------- #
def register_routes(app):  # noqa: D401
    """Registra blueprint HTML + API sull'istanza Flask *app*."""
    # Import and register service dashboard routes
    from . import service_dashboard

    app.register_blueprint(customers_bp)
    app.register_blueprint(api_bp)
