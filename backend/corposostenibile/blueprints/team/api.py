"""
Team API endpoints for React frontend.

This module provides JSON API endpoints for team member CRUD operations.
All endpoints are prefixed with /api/team.
"""

import os
import uuid
from datetime import datetime
from http import HTTPStatus
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import and_, or_, func, cast, String, select, union_all, distinct
from sqlalchemy.orm import joinedload, selectinload
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from corposostenibile.extensions import db, csrf
from corposostenibile.models import (
    User, Department, Team, UserRoleEnum, UserSpecialtyEnum, TeamTypeEnum,
    team_members, Origine, ServiceClienteAssignment, ClienteProfessionistaHistory,
    ServiceClienteNote, Cliente, GHLOpportunityData, GHLOpportunity,
    ProfessionistCapacity, StatoClienteEnum, cliente_nutrizionisti, cliente_coaches,
    cliente_psicologi, cliente_consulenti, SalesLead,
    CapacityRoleTypeWeight, TipologiaClienteEnum,
)


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
CAPACITY_SUPPORT_TYPES = ("a", "b", "c", "secondario")
DEFAULT_CAPACITY_WEIGHTS = {
    "nutrizione": {
        "a": 2.0,
        "b": 1.5,
        "c": 1.0,
        "secondario": 0.5,
    },
    "coach": {
        "a": 2.0,
        "b": 1.5,
        "c": 1.0,
        "secondario": 0.5,
    },
}


def allowed_file(filename):
    """Check if file has allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _get_capacity_weight_role(role_type: str | None) -> str | None:
    if role_type == "nutrizionista":
        return "nutrizione"
    if role_type == "coach":
        return "coach"
    return None


def _get_capacity_weights_by_role() -> dict[str, dict[str, float]]:
    weights = {
        area: values.copy()
        for area, values in DEFAULT_CAPACITY_WEIGHTS.items()
    }
    for row in CapacityRoleTypeWeight.query.all():
        area = row.role_type.value if hasattr(row.role_type, "value") else row.role_type
        if area in weights and row.tipo in CAPACITY_SUPPORT_TYPES:
            weights[area][row.tipo] = row.peso
    return weights


# Create API blueprint with /api/team prefix
team_api_bp = Blueprint(
    "team_api",
    __name__,
    url_prefix="/api/team",
)

# Exempt entire blueprint from CSRF (JSON API)
csrf.exempt(team_api_bp)


# =============================================================================
# Permission Helpers
# =============================================================================

def _require_admin():
    """Check if user is admin."""
    if not (current_user.is_authenticated and current_user.is_admin):
        return jsonify({
            'success': False,
            'message': 'Accesso non autorizzato'
        }), HTTPStatus.FORBIDDEN
    return None


def _get_visible_user_ids_for_dashboard():
    """
    For dashboard stats: which user IDs the current user can see.
    - Admin: None (all users)
    - Team Leader: members of teams they lead, plus themselves
    - Professionista: only current_user.id
    Returns None = no filter (see all), or a list of user ids.
    """
    if not current_user.is_authenticated:
        return []
    if current_user.is_admin:
        return None
    if getattr(current_user, 'role', None) == UserRoleEnum.team_leader and current_user.teams_led:
        visible = {current_user.id}
        for team in current_user.teams_led:
            if team.members:
                for m in team.members:
                    visible.add(m.id)
        return list(visible)
    # Professionista or other: only self
    return [current_user.id]


def _get_user_role(user):
    """Get user role from model field."""
    if hasattr(user, 'role') and user.role:
        return user.role.value if hasattr(user.role, 'value') else str(user.role)
    return 'professionista'


def _get_user_specialty(user):
    """Get user specialty from model field."""
    if hasattr(user, 'specialty') and user.specialty:
        return user.specialty.value if hasattr(user.specialty, 'value') else str(user.specialty)
    return None


def _is_cco_user(user) -> bool:
    """True se utente CCO (specialty CCO o dipartimento CCO)."""
    specialty = _get_user_specialty(user)
    if specialty == 'cco':
        return True
    department_name = getattr(getattr(user, 'department', None), 'name', None)
    return str(department_name).strip().lower() == 'cco' if department_name else False


def _can_view_professional_capacity(user) -> bool:
    """ACL visualizzazione capienza: admin/CCO tutto, team leader solo membri."""
    if not user.is_authenticated:
        return False
    if user.is_admin or _is_cco_user(user):
        return True
    role = _get_user_role(user)
    return role in {'team_leader', 'health_manager'}


def _can_edit_professional_capacity(user) -> bool:
    """ACL modifica capienza contrattuale: admin/CCO + qualsiasi Team Leader."""
    return user.is_authenticated and (user.is_admin or _is_cco_user(user) or _get_user_role(user) == 'team_leader')


def _can_view_all_team_module_data(user) -> bool:
    """Admin/CCO can view all data in Team module."""
    return bool(user.is_authenticated and (user.is_admin or _is_cco_user(user)))


def _get_capacity_role_type(user) -> str | None:
    """Normalizza role_type per tabella professionist_capacity."""
    if _get_user_role(user) == 'health_manager':
        return 'health_manager'
    specialty = _get_user_specialty(user)
    if specialty in ('nutrizione', 'nutrizionista'):
        return 'nutrizionista'
    if specialty in ('psicologia', 'psicologo'):
        return 'psicologa'
    if specialty == 'coach':
        return 'coach'
    return None


def _is_health_manager_team_leader(user) -> bool:
    """True se team leader HM (team_type HM guidato, specialty o dipartimento)."""
    if _get_user_role(user) != 'team_leader':
        return False
    teams_led = getattr(user, 'teams_led', []) or []
    for team in teams_led:
        team_type = getattr(getattr(team, 'team_type', None), 'value', getattr(team, 'team_type', None))
        if str(team_type or '').strip().lower() == 'health_manager':
            return True
    specialty = (_get_user_specialty(user) or '').strip().lower()
    if specialty == 'health_manager':
        return True
    department_name = str(getattr(getattr(user, 'department', None), 'name', '') or '').strip().lower()
    return ('health' in department_name) or ('customer success' in department_name)


def _get_team_leader_member_ids(user_id: int) -> set[int]:
    """Ritorna ID membri dei team guidati dal team leader (incluso il TL stesso)."""
    team_ids = db.session.query(Team.id).filter(
        Team.head_id == user_id,
        Team.is_active == True
    )
    rows = db.session.query(team_members.c.user_id).filter(
        team_members.c.team_id.in_(team_ids)
    ).distinct().all()
    result = {row[0] for row in rows}
    result.add(user_id)  # Il TL deve vedere anche i propri pazienti
    return result


def _can_access_member_scoped_data(requesting_user, target_user_id: int) -> bool:
    """
    ACL per endpoint /members/<id>/* usati in profilo/team.
    - admin/CCO: tutto
    - team leader: sé stesso + membri dei propri team
    - altri: solo sé stessi
    """
    if not getattr(requesting_user, 'is_authenticated', False):
        return False
    if _can_view_all_team_module_data(requesting_user):
        return True

    requester_id = getattr(requesting_user, 'id', None)
    if requester_id is None:
        return False

    if _get_user_role(requesting_user) == 'team_leader':
        allowed_ids = _get_team_leader_member_ids(requester_id) | {requester_id}
        return int(target_user_id) in allowed_ids

    return int(target_user_id) == int(requester_id)


def _promote_team_head_to_team_leader(user_id: int | None) -> None:
    """
    Mantiene coerente users.role con teams.head_id.
    Promozione solo in salita (non effettua downgrade automatici).
    """
    if not user_id:
        return
    user = User.query.get(user_id)
    if not user or getattr(user, 'is_admin', False):
        return

    current_role = _get_user_role(user)
    if current_role in ('admin', 'team_leader'):
        return

    user.role = UserRoleEnum.team_leader


def _get_assigned_clients_count_map(user_ids: list[int]) -> dict[int, int]:
    """
    Conteggio clienti assegnati per utente (FK + many-to-many), con count distinct per cliente.
    """
    if not user_ids:
        return {}

    sources = [
        select(Cliente.nutrizionista_id.label('user_id'), Cliente.cliente_id.label('cliente_id')).where(
            Cliente.nutrizionista_id.in_(user_ids)
        ),
        select(Cliente.coach_id.label('user_id'), Cliente.cliente_id.label('cliente_id')).where(
            Cliente.coach_id.in_(user_ids)
        ),
        select(Cliente.psicologa_id.label('user_id'), Cliente.cliente_id.label('cliente_id')).where(
            Cliente.psicologa_id.in_(user_ids)
        ),
        select(Cliente.consulente_alimentare_id.label('user_id'), Cliente.cliente_id.label('cliente_id')).where(
            Cliente.consulente_alimentare_id.in_(user_ids)
        ),
        select(Cliente.health_manager_id.label('user_id'), Cliente.cliente_id.label('cliente_id')).where(
            Cliente.health_manager_id.in_(user_ids)
        ),
        select(cliente_nutrizionisti.c.user_id.label('user_id'), cliente_nutrizionisti.c.cliente_id.label('cliente_id')).where(
            cliente_nutrizionisti.c.user_id.in_(user_ids)
        ),
        select(cliente_coaches.c.user_id.label('user_id'), cliente_coaches.c.cliente_id.label('cliente_id')).where(
            cliente_coaches.c.user_id.in_(user_ids)
        ),
        select(cliente_psicologi.c.user_id.label('user_id'), cliente_psicologi.c.cliente_id.label('cliente_id')).where(
            cliente_psicologi.c.user_id.in_(user_ids)
        ),
        select(cliente_consulenti.c.user_id.label('user_id'), cliente_consulenti.c.cliente_id.label('cliente_id')).where(
            cliente_consulenti.c.user_id.in_(user_ids)
        ),
    ]

    assignments_sq = union_all(*sources).subquery()
    rows = db.session.query(
        assignments_sq.c.user_id,
        func.count(distinct(assignments_sq.c.cliente_id)).label('assigned_clients')
    ).group_by(assignments_sq.c.user_id).all()
    return {int(user_id): int(count) for user_id, count in rows}


def _get_assigned_clients_count_map_active_by_role(user_ids: list[int]) -> dict[tuple[int, str], int]:
    """
    Conteggio clienti assegnati per (user_id, role_type) considerando solo
    lo stato servizio 'attivo' (stato_nutrizione, stato_coach, stato_psicologia).
    Usato per la tabella capienza professionisti.
    """
    if not user_ids:
        return {}

    result: dict[tuple[int, str], int] = {}

    # Nutrizionista: nutrizionista_id, consulente_alimentare_id, m2m nutrizionisti/consulenti + stato_nutrizione = attivo
    nut_sources = [
        select(Cliente.nutrizionista_id.label('user_id'), Cliente.cliente_id.label('cliente_id')).where(
            Cliente.nutrizionista_id.in_(user_ids),
            Cliente.stato_nutrizione == StatoClienteEnum.attivo,
        ),
        select(Cliente.consulente_alimentare_id.label('user_id'), Cliente.cliente_id.label('cliente_id')).where(
            Cliente.consulente_alimentare_id.in_(user_ids),
            Cliente.stato_nutrizione == StatoClienteEnum.attivo,
        ),
        select(cliente_nutrizionisti.c.user_id.label('user_id'), cliente_nutrizionisti.c.cliente_id.label('cliente_id')).select_from(
            cliente_nutrizionisti.join(Cliente, cliente_nutrizionisti.c.cliente_id == Cliente.cliente_id)
        ).where(
            cliente_nutrizionisti.c.user_id.in_(user_ids),
            Cliente.stato_nutrizione == StatoClienteEnum.attivo,
        ),
        select(cliente_consulenti.c.user_id.label('user_id'), cliente_consulenti.c.cliente_id.label('cliente_id')).select_from(
            cliente_consulenti.join(Cliente, cliente_consulenti.c.cliente_id == Cliente.cliente_id)
        ).where(
            cliente_consulenti.c.user_id.in_(user_ids),
            Cliente.stato_nutrizione == StatoClienteEnum.attivo,
        ),
    ]
    nut_sq = union_all(*nut_sources).subquery()
    nut_rows = db.session.query(
        nut_sq.c.user_id,
        func.count(distinct(nut_sq.c.cliente_id)).label('cnt'),
    ).group_by(nut_sq.c.user_id).all()
    for user_id, cnt in nut_rows:
        result[(int(user_id), 'nutrizionista')] = int(cnt)

    # Coach: coach_id, cliente_coaches + stato_coach = attivo
    coach_sources = [
        select(Cliente.coach_id.label('user_id'), Cliente.cliente_id.label('cliente_id')).where(
            Cliente.coach_id.in_(user_ids),
            Cliente.stato_coach == StatoClienteEnum.attivo,
        ),
        select(cliente_coaches.c.user_id.label('user_id'), cliente_coaches.c.cliente_id.label('cliente_id')).select_from(
            cliente_coaches.join(Cliente, cliente_coaches.c.cliente_id == Cliente.cliente_id)
        ).where(
            cliente_coaches.c.user_id.in_(user_ids),
            Cliente.stato_coach == StatoClienteEnum.attivo,
        ),
    ]
    coach_sq = union_all(*coach_sources).subquery()
    coach_rows = db.session.query(
        coach_sq.c.user_id,
        func.count(distinct(coach_sq.c.cliente_id)).label('cnt'),
    ).group_by(coach_sq.c.user_id).all()
    for user_id, cnt in coach_rows:
        result[(int(user_id), 'coach')] = int(cnt)

    # Psicologa: psicologa_id, cliente_psicologi + stato_psicologia = attivo
    psico_sources = [
        select(Cliente.psicologa_id.label('user_id'), Cliente.cliente_id.label('cliente_id')).where(
            Cliente.psicologa_id.in_(user_ids),
            Cliente.stato_psicologia == StatoClienteEnum.attivo,
        ),
        select(cliente_psicologi.c.user_id.label('user_id'), cliente_psicologi.c.cliente_id.label('cliente_id')).select_from(
            cliente_psicologi.join(Cliente, cliente_psicologi.c.cliente_id == Cliente.cliente_id)
        ).where(
            cliente_psicologi.c.user_id.in_(user_ids),
            Cliente.stato_psicologia == StatoClienteEnum.attivo,
        ),
    ]
    psico_sq = union_all(*psico_sources).subquery()
    psico_rows = db.session.query(
        psico_sq.c.user_id,
        func.count(distinct(psico_sq.c.cliente_id)).label('cnt'),
    ).group_by(psico_sq.c.user_id).all()
    for user_id, cnt in psico_rows:
        result[(int(user_id), 'psicologa')] = int(cnt)

    # Health Manager:
    # - clienti effettivi attivi
    # - lead pre-onboarding (service_status = pending_assignment)
    # Entrambi conteggiati da Cliente.health_manager_id, valorizzato dal bridge GHL.
    hm_rows = db.session.query(
        Cliente.health_manager_id.label('user_id'),
        func.count(distinct(Cliente.cliente_id)).label('cnt'),
    ).filter(
        Cliente.health_manager_id.in_(user_ids),
        or_(
            Cliente.stato_cliente == StatoClienteEnum.attivo,
            Cliente.service_status == 'pending_assignment',
        ),
    ).group_by(Cliente.health_manager_id).all()
    for user_id, cnt in hm_rows:
        result[(int(user_id), 'health_manager')] = int(cnt)

    return result


def _get_hm_split_counts(user_ids: list[int]) -> dict[int, dict]:
    """Return per-HM split: clienti_convertiti (attivo) vs lead_in_attesa (pending_assignment)."""
    if not user_ids:
        return {}

    rows = db.session.query(
        Cliente.health_manager_id.label('user_id'),
        Cliente.stato_cliente,
        Cliente.service_status,
        func.count(distinct(Cliente.cliente_id)).label('cnt'),
    ).filter(
        Cliente.health_manager_id.in_(user_ids),
        or_(
            Cliente.stato_cliente == StatoClienteEnum.attivo,
            Cliente.service_status == 'pending_assignment',
        ),
    ).group_by(
        Cliente.health_manager_id,
        Cliente.stato_cliente,
        Cliente.service_status,
    ).all()

    result: dict[int, dict] = {}
    for uid, stato, svc_status, cnt in rows:
        uid = int(uid)
        if uid not in result:
            result[uid] = {'clienti_convertiti': 0, 'lead_in_attesa': 0}
        if stato and stato.value == 'attivo':
            result[uid]['clienti_convertiti'] += int(cnt)
        elif svc_status == 'pending_assignment':
            result[uid]['lead_in_attesa'] += int(cnt)

    return result


def _get_assigned_clients_by_type(user_ids: list[int]) -> dict[tuple[int, str], dict[str, int]]:
    """
    Conteggio clienti assegnati per (user_id, role_type) raggruppati per tipologia.
    Per nutrizione/coach usa i nuovi campi di supporto; per HM continua a usare tipologia_cliente.
    """
    if not user_ids:
        return {}

    result: dict[tuple[int, str], dict[str, int]] = {}

    def _merge(rows, role_type):
        for user_id, tipo, cnt in rows:
            key = (int(user_id), role_type)
            if key not in result:
                result[key] = {}
            tipo_val = tipo.value if hasattr(tipo, 'value') else (tipo or '')
            if tipo_val in CAPACITY_SUPPORT_TYPES:
                result[key][tipo_val] = result[key].get(tipo_val, 0) + int(cnt)

    # Nutrizionista: nutrizionista_id, consulente_alimentare_id, m2m nutrizionisti/consulenti + stato_nutrizione = attivo
    nut_sources = [
        select(
            Cliente.nutrizionista_id.label('user_id'),
            Cliente.tipologia_supporto_nutrizione.label('tipo'),
            Cliente.cliente_id.label('cliente_id'),
        ).where(
            Cliente.nutrizionista_id.in_(user_ids),
            Cliente.stato_nutrizione == StatoClienteEnum.attivo,
            Cliente.tipologia_supporto_nutrizione.isnot(None),
        ),
        select(
            Cliente.consulente_alimentare_id.label('user_id'),
            Cliente.tipologia_supporto_nutrizione.label('tipo'),
            Cliente.cliente_id.label('cliente_id'),
        ).where(
            Cliente.consulente_alimentare_id.in_(user_ids),
            Cliente.stato_nutrizione == StatoClienteEnum.attivo,
            Cliente.tipologia_supporto_nutrizione.isnot(None),
        ),
        select(
            cliente_nutrizionisti.c.user_id.label('user_id'),
            Cliente.tipologia_supporto_nutrizione.label('tipo'),
            cliente_nutrizionisti.c.cliente_id.label('cliente_id'),
        ).select_from(
            cliente_nutrizionisti.join(Cliente, cliente_nutrizionisti.c.cliente_id == Cliente.cliente_id)
        ).where(
            cliente_nutrizionisti.c.user_id.in_(user_ids),
            Cliente.stato_nutrizione == StatoClienteEnum.attivo,
            Cliente.tipologia_supporto_nutrizione.isnot(None),
        ),
        select(
            cliente_consulenti.c.user_id.label('user_id'),
            Cliente.tipologia_supporto_nutrizione.label('tipo'),
            cliente_consulenti.c.cliente_id.label('cliente_id'),
        ).select_from(
            cliente_consulenti.join(Cliente, cliente_consulenti.c.cliente_id == Cliente.cliente_id)
        ).where(
            cliente_consulenti.c.user_id.in_(user_ids),
            Cliente.stato_nutrizione == StatoClienteEnum.attivo,
            Cliente.tipologia_supporto_nutrizione.isnot(None),
        ),
    ]
    nut_sq = union_all(*nut_sources).subquery()
    nut_rows = db.session.query(
        nut_sq.c.user_id,
        nut_sq.c.tipo,
        func.count(distinct(nut_sq.c.cliente_id)).label('cnt'),
    ).group_by(nut_sq.c.user_id, nut_sq.c.tipo).all()
    _merge(nut_rows, 'nutrizionista')

    # Coach: coach_id, cliente_coaches + stato_coach = attivo
    coach_sources = [
        select(
            Cliente.coach_id.label('user_id'),
            Cliente.tipologia_supporto_coach.label('tipo'),
            Cliente.cliente_id.label('cliente_id'),
        ).where(
            Cliente.coach_id.in_(user_ids),
            Cliente.stato_coach == StatoClienteEnum.attivo,
            Cliente.tipologia_supporto_coach.isnot(None),
        ),
        select(
            cliente_coaches.c.user_id.label('user_id'),
            Cliente.tipologia_supporto_coach.label('tipo'),
            cliente_coaches.c.cliente_id.label('cliente_id'),
        ).select_from(
            cliente_coaches.join(Cliente, cliente_coaches.c.cliente_id == Cliente.cliente_id)
        ).where(
            cliente_coaches.c.user_id.in_(user_ids),
            Cliente.stato_coach == StatoClienteEnum.attivo,
            Cliente.tipologia_supporto_coach.isnot(None),
        ),
    ]
    coach_sq = union_all(*coach_sources).subquery()
    coach_rows = db.session.query(
        coach_sq.c.user_id,
        coach_sq.c.tipo,
        func.count(distinct(coach_sq.c.cliente_id)).label('cnt'),
    ).group_by(coach_sq.c.user_id, coach_sq.c.tipo).all()
    _merge(coach_rows, 'coach')

    # Psicologa: psicologa_id, cliente_psicologi + stato_psicologia = attivo
    psico_sources = [
        select(
            Cliente.psicologa_id.label('user_id'),
            cast(None, String).label('tipo'),
            Cliente.cliente_id.label('cliente_id'),
        ).where(
            Cliente.psicologa_id.in_(user_ids),
            Cliente.stato_psicologia == StatoClienteEnum.attivo,
        ),
        select(
            cliente_psicologi.c.user_id.label('user_id'),
            cast(None, String).label('tipo'),
            cliente_psicologi.c.cliente_id.label('cliente_id'),
        ).select_from(
            cliente_psicologi.join(Cliente, cliente_psicologi.c.cliente_id == Cliente.cliente_id)
        ).where(
            cliente_psicologi.c.user_id.in_(user_ids),
            Cliente.stato_psicologia == StatoClienteEnum.attivo,
        ),
    ]
    psico_sq = union_all(*psico_sources).subquery()
    psico_rows = db.session.query(
        psico_sq.c.user_id,
        psico_sq.c.tipo,
        func.count(distinct(psico_sq.c.cliente_id)).label('cnt'),
    ).group_by(psico_sq.c.user_id, psico_sq.c.tipo).all()
    _merge(psico_rows, 'psicologa')

    # Health Manager: health_manager_id, stato_cliente = attivo OR service_status = pending_assignment
    hm_rows = db.session.query(
        Cliente.health_manager_id.label('user_id'),
        Cliente.tipologia_cliente.label('tipo'),
        func.count(distinct(Cliente.cliente_id)).label('cnt'),
    ).filter(
        Cliente.health_manager_id.in_(user_ids),
        or_(
            Cliente.stato_cliente == StatoClienteEnum.attivo,
            Cliente.service_status == 'pending_assignment',
        ),
    ).group_by(Cliente.health_manager_id, Cliente.tipologia_cliente).all()
    _merge(hm_rows, 'health_manager')

    return result


def _calculate_capacity_metrics(
    role_type: str,
    assigned_clients: int,
    contractual_capacity: int,
    type_counts: dict[str, int] | None,
    weights_by_role: dict[str, dict[str, float]],
) -> dict[str, float | int | bool]:
    """
    Calcola breakdown e metriche di capienza.

    Per nutrizione/coach la percentuale segue la capienza ponderata, come richiesto in call.
    Psicologia e Health Manager restano count-based.
    """
    counts = type_counts or {}
    clienti_a = int(counts.get("a", 0) or 0)
    clienti_b = int(counts.get("b", 0) or 0)
    clienti_c = int(counts.get("c", 0) or 0)
    clienti_secondario = int(counts.get("secondario", 0) or 0)

    if role_type == "psicologa":
        weighted_load = float(assigned_clients)
    elif role_type == "health_manager":
        weighted_load = float(assigned_clients)
    else:
        weight_role = _get_capacity_weight_role(role_type)
        role_weights = weights_by_role.get(weight_role or "", {})
        weighted_load = (
            clienti_a * role_weights.get("a", 1.0)
            + clienti_b * role_weights.get("b", 1.0)
            + clienti_c * role_weights.get("c", 1.0)
            + clienti_secondario * role_weights.get("secondario", 1.0)
        )

    capacity_percentage = (
        0
        if contractual_capacity <= 0
        else round((weighted_load / contractual_capacity) * 100, 2)
    )

    return {
        "clienti_tipo_a": clienti_a,
        "clienti_tipo_b": clienti_b,
        "clienti_tipo_c": clienti_c,
        "clienti_tipo_secondario": clienti_secondario,
        "capienza_ponderata": round(float(weighted_load), 2),
        "percentuale_capienza": capacity_percentage,
        "is_over_capacity": contractual_capacity > 0 and weighted_load > contractual_capacity,
    }


def _serialize_user(user, include_details=False, include_teams_led=True):
    """Serialize user object to JSON-safe dict."""
    data = {
        'id': user.id,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'full_name': user.full_name,
        'avatar_path': user.avatar_path,
        'is_admin': user.is_admin,
        'is_active': user.is_active,
        'is_external': getattr(user, 'is_external', False),
        'role': _get_user_role(user),
        'specialty': _get_user_specialty(user),
    }

    # Only load teams_led when explicitly requested (causes N+1 queries)
    if include_teams_led and hasattr(user, 'teams_led'):
        data['teams_led'] = [
            {'id': t.id, 'name': t.name, 'team_type': t.team_type.value if t.team_type else None}
            for t in (user.teams_led or [])
        ]
    else:
        data['teams_led'] = []

    # Include teams where user is a member
    if include_details and hasattr(user, 'teams'):
        data['teams'] = [
            {'id': t.id, 'name': t.name, 'team_type': t.team_type.value if t.team_type else None}
            for t in (user.teams or [])
        ]
    else:
        data['teams'] = []

    if include_details:
        data.update({
            'last_login_at': user.last_login_at.isoformat() if user.last_login_at else None,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'is_trial': user.is_trial,
            'trial_stage': user.trial_stage,
            'assignment_ai_notes': user.assignment_ai_notes or {},
        })

    return data

def _serialize_origins(user):
    """Serialize user origins (for influencers) - M2M relationship."""
    if hasattr(user, 'influencer_origins') and user.influencer_origins:
        return [{'id': o.id, 'name': o.name} for o in user.influencer_origins]
    return []


# =============================================================================
# API Endpoints
# =============================================================================

@team_api_bp.route("/members", methods=["GET"])
@login_required
def get_members():
    """
    Get paginated list of team members.

    Query params:
        - page: Page number (default 1)
        - per_page: Items per page (default 25, max 10000)
        - q: Search query (searches name, email)
        - role: Filter by role (admin, team_leader, professionista, team_esterno, health_manager)
        - specialty: Filter by specialty
        - active: Filter by active status ('1' or '0')
        - department_id: Filter by department
    """
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 25, type=int), 10000)
    search_query = request.args.get('q', '').strip()
    role_filter = request.args.get('role', '').strip().lower()
    specialty_filter = request.args.get('specialty', '').strip()
    active_filter = request.args.get('active', '').strip()
    department_id = request.args.get('department_id', type=int)

    # Base query: escludi utenti legacy/senza ruolo dal modulo Team
    query = User.query.filter(User.role.isnot(None))

    # RBAC base scope
    if _can_view_all_team_module_data(current_user):
        pass
    elif _get_user_role(current_user) == 'team_leader':
        visible_ids = _get_team_leader_member_ids(current_user.id)
        visible_ids.add(current_user.id)
        query = query.filter(User.id.in_(list(visible_ids)))
    else:
        query = query.filter(User.id == current_user.id)

    # Search filter
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            or_(
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
                User.email.ilike(search_term),
                func.concat(User.first_name, ' ', User.last_name).ilike(search_term)
            )
        )

    # Active filter
    if active_filter == '1':
        query = query.filter(User.is_active == True)
    elif active_filter == '0':
        query = query.filter(User.is_active == False)

    # Department filter
    if department_id:
        query = query.filter(User.department_id == department_id)

    # Role filter - include team leader as "grade" of professional domains.
    if role_filter:
        hm_team_leader_ids_sq = db.session.query(Team.head_id).filter(
            Team.head_id.isnot(None),
            Team.is_active == True,
            Team.team_type == TeamTypeEnum.health_manager,
        ).distinct().subquery()

        if role_filter == 'admin':
            # Fallback for old API calls
            query = query.filter(User.is_admin == True)
        elif role_filter == 'professionista':
            # Include standard professionals + team leaders not in HM domain.
            query = query.filter(
                or_(
                    cast(User.role, String) == 'professionista',
                    and_(
                        cast(User.role, String) == 'team_leader',
                        cast(User.specialty, String) != 'health_manager',
                        ~User.id.in_(select(hm_team_leader_ids_sq.c.head_id)),
                    ),
                )
            )
        elif role_filter == 'health_manager':
            # Include HM users + HM team leaders.
            query = query.filter(
                or_(
                    cast(User.role, String) == 'health_manager',
                    and_(
                        cast(User.role, String) == 'team_leader',
                        or_(
                            cast(User.specialty, String) == 'health_manager',
                            User.id.in_(select(hm_team_leader_ids_sq.c.head_id)),
                        ),
                    ),
                )
            )
        else:
            # Robust text-based filter to avoid enum drift across branches/environments.
            query = query.filter(cast(User.role, String) == role_filter)

    # Specialty filter - use new specialty field directly
    # Supports comma-separated values (e.g., "nutrizione,nutrizionista")
    if specialty_filter:
        specialty_values = [s.strip() for s in specialty_filter.split(',')]
        valid_specialties = []
        for sv in specialty_values:
            if sv in [e.value for e in UserSpecialtyEnum]:
                valid_specialties.append(UserSpecialtyEnum(sv))
        if valid_specialties:
            # Team leaders must always see themselves in their team's dropdown
            if _get_user_role(current_user) == 'team_leader':
                query = query.filter(
                    or_(
                        User.specialty.in_(valid_specialties),
                        User.id == current_user.id,
                    )
                )
            else:
                query = query.filter(User.specialty.in_(valid_specialties))

    # Order by name
    query = query.order_by(User.first_name, User.last_name)

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Serialize results
    members = [_serialize_user(user) for user in pagination.items]

    return jsonify({
        'success': True,
        'members': members,
        'total': pagination.total,
        'page': pagination.page,
        'per_page': pagination.per_page,
        'total_pages': pagination.pages,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev,
    })


@team_api_bp.route("/members/<int:user_id>", methods=["GET"])
@login_required
def get_member(user_id):
    """Get single team member details."""
    user = User.query.get_or_404(user_id)

    if not _can_view_all_team_module_data(current_user):
        if _get_user_role(current_user) == 'team_leader':
            visible_ids = _get_team_leader_member_ids(current_user.id)
            visible_ids.add(current_user.id)
            if user_id not in visible_ids:
                return jsonify({'success': False, 'message': 'Accesso non autorizzato'}), HTTPStatus.FORBIDDEN
        elif user_id != current_user.id:
            return jsonify({'success': False, 'message': 'Accesso non autorizzato'}), HTTPStatus.FORBIDDEN

    return jsonify({
        'success': True,
        **_serialize_user(user, include_details=True),
        'influencer_origins': _serialize_origins(user)
    })


@team_api_bp.route("/members", methods=["POST"])
@login_required
def create_member():
    """Create new team member."""
    # Check admin permission
    perm_error = _require_admin()
    if perm_error:
        return perm_error

    data = request.get_json()
    if not data:
        return jsonify({
            'success': False,
            'message': 'Dati non validi'
        }), HTTPStatus.BAD_REQUEST

    # Validate required fields
    required_fields = ['email', 'password', 'first_name', 'last_name']
    for field in required_fields:
        if not data.get(field):
            return jsonify({
                'success': False,
                'message': f'Campo obbligatorio mancante: {field}'
            }), HTTPStatus.BAD_REQUEST

    # Check email uniqueness
    if User.query.filter_by(email=data['email'].lower()).first():
        return jsonify({
            'success': False,
            'message': 'Email già registrata'
        }), HTTPStatus.BAD_REQUEST

    try:
        # Determine role and flags from input
        role_str = data.get('role', 'professionista')
        is_admin = data.get('is_admin', False) or role_str == 'admin'
        is_external = data.get('is_external', False) or role_str == 'team_esterno'

        # Map role string to enum
        role_enum = UserRoleEnum.professionista  # default
        if role_str in [e.value for e in UserRoleEnum]:
            role_enum = UserRoleEnum(role_str)

        # Map specialty string to enum (if provided)
        specialty_enum = None
        specialty_str = data.get('specialty')
        if specialty_str and specialty_str in [e.value for e in UserSpecialtyEnum]:
            specialty_enum = UserSpecialtyEnum(specialty_str)

        # Create user
        user = User(
            email=data['email'].lower(),
            first_name=data['first_name'],
            last_name=data['last_name'],
            is_admin=is_admin,
            is_active=True,
            role=role_enum,
            specialty=specialty_enum,
            is_external=is_external,
        )

        # Set password
        user.set_password(data['password'])

        db.session.add(user)
        db.session.flush()  # get user.id before M2M assignment

        # Handle Origin assignment for Influencers (M2M)
        if role_enum == UserRoleEnum.influencer and 'origin_ids' in data:
            origin_ids = data['origin_ids'] or []
            origins = Origine.query.filter(Origine.id.in_(origin_ids)).all()
            user.influencer_origins = origins

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Membro creato con successo',
            'id': user.id,
            **_serialize_user(user),
            'influencer_origins': _serialize_origins(user)
        }), HTTPStatus.CREATED

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating team member: {e}")
        return jsonify({
            'success': False,
            'message': f'Errore durante la creazione: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@team_api_bp.route("/members/<int:user_id>", methods=["PUT"])
@login_required
def update_member(user_id):
    """Update team member."""
    # Check admin permission
    perm_error = _require_admin()
    if perm_error:
        return perm_error

    user = User.query.get_or_404(user_id)
    data = request.get_json()

    if not data:
        return jsonify({
            'success': False,
            'message': 'Dati non validi'
        }), HTTPStatus.BAD_REQUEST

    try:
        # Update allowed fields
        updatable_fields = ['first_name', 'last_name', 'is_admin', 'is_external']

        for field in updatable_fields:
            if field in data:
                setattr(user, field, data[field])

        # Update role (enum field)
        if 'role' in data:
            role_str = data['role']
            if role_str in [e.value for e in UserRoleEnum]:
                user.role = UserRoleEnum(role_str)
                # Sync is_admin and is_external flags
                user.is_admin = role_str == 'admin'
                user.is_external = role_str == 'team_esterno'

        # Update specialty (enum field)
        if 'specialty' in data:
            specialty_str = data['specialty']
            if specialty_str and specialty_str in [e.value for e in UserSpecialtyEnum]:
                user.specialty = UserSpecialtyEnum(specialty_str)
            elif not specialty_str:
                user.specialty = None

        # Update email (check uniqueness)
        if 'email' in data and data['email'].lower() != user.email:
            if User.query.filter_by(email=data['email'].lower()).first():
                return jsonify({
                    'success': False,
                    'message': 'Email già registrata'
                }), HTTPStatus.BAD_REQUEST
            user.email = data['email'].lower()

        # Update password if provided
        if data.get('password'):
            user.set_password(data['password'])

        # Update Origin assignment for Influencers (M2M)
        if 'origin_ids' in data:
            current_role = user.role
            new_role_str = data.get('role')
            new_role = UserRoleEnum(new_role_str) if new_role_str in [e.value for e in UserRoleEnum] else current_role

            if new_role == UserRoleEnum.influencer:
                origin_ids = data['origin_ids'] or []
                origins = Origine.query.filter(Origine.id.in_(origin_ids)).all()
                user.influencer_origins = origins
            else:
                # If not influencer, clear origins
                user.influencer_origins = []

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Membro aggiornato con successo',
            **_serialize_user(user, include_details=True),
            'influencer_origins': _serialize_origins(user)
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating team member: {e}")
        return jsonify({
            'success': False,
            'message': f'Errore durante l\'aggiornamento: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@team_api_bp.route("/members/<int:user_id>", methods=["DELETE"])
@login_required
def delete_member(user_id):
    """Delete team member (soft delete by deactivating)."""
    # Check admin permission
    perm_error = _require_admin()
    if perm_error:
        return perm_error

    user = User.query.get_or_404(user_id)

    # Prevent self-deletion
    if user.id == current_user.id:
        return jsonify({
            'success': False,
            'message': 'Non puoi eliminare il tuo account'
        }), HTTPStatus.BAD_REQUEST

    try:
        # Soft delete - just deactivate
        user.is_active = False
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Membro disattivato con successo'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting team member: {e}")
        return jsonify({
            'success': False,
            'message': f'Errore durante l\'eliminazione: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@team_api_bp.route("/members/<int:user_id>/toggle", methods=["POST"])
@login_required
def toggle_member_status(user_id):
    """Toggle team member active status."""
    # Check admin permission
    perm_error = _require_admin()
    if perm_error:
        return perm_error

    user = User.query.get_or_404(user_id)

    # Prevent toggling own status
    if user.id == current_user.id:
        return jsonify({
            'success': False,
            'message': 'Non puoi disattivare il tuo account'
        }), HTTPStatus.BAD_REQUEST

    try:
        user.is_active = not user.is_active
        db.session.commit()

        status = 'attivato' if user.is_active else 'disattivato'
        return jsonify({
            'success': True,
            'message': f'Account {status} con successo',
            'is_active': user.is_active
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling team member status: {e}")
        return jsonify({
            'success': False,
            'message': f'Errore: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@team_api_bp.route("/members/<int:user_id>/avatar", methods=["POST"])
@login_required
def upload_avatar(user_id):
    """Upload avatar for team member."""
    # Check admin permission or self
    if not (current_user.is_admin or current_user.id == user_id):
        return jsonify({
            'success': False,
            'message': 'Accesso non autorizzato'
        }), HTTPStatus.FORBIDDEN

    user = User.query.get_or_404(user_id)

    if 'avatar' not in request.files:
        return jsonify({
            'success': False,
            'message': 'Nessun file caricato'
        }), HTTPStatus.BAD_REQUEST

    file = request.files['avatar']
    if file.filename == '':
        return jsonify({
            'success': False,
            'message': 'Nessun file selezionato'
        }), HTTPStatus.BAD_REQUEST

    if not allowed_file(file.filename):
        return jsonify({
            'success': False,
            'message': 'Tipo di file non consentito. Usa PNG, JPG, JPEG, GIF o WEBP'
        }), HTTPStatus.BAD_REQUEST

    try:
        # Generate unique filename
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"

        # Use configured UPLOAD_FOLDER
        base_upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        upload_folder = os.path.join(base_upload_folder, 'avatars')
        os.makedirs(upload_folder, exist_ok=True)

        # Delete old avatar if exists
        if user.avatar_path and user.avatar_path.startswith('/uploads/'):
            old_filename = user.avatar_path.replace('/uploads/avatars/', '')
            old_path = os.path.join(upload_folder, old_filename)
            if os.path.exists(old_path):
                os.remove(old_path)

        # Save new file
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)

        # Update user avatar_path - matches /uploads/<path:filename> route
        user.avatar_path = f"/uploads/avatars/{filename}"
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Avatar caricato con successo',
            'avatar_path': user.avatar_path
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error uploading avatar: {e}")
        return jsonify({
            'success': False,
            'message': f'Errore durante il caricamento: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@team_api_bp.route("/departments", methods=["GET"])
@login_required
def get_departments():
    """Get list of departments."""
    departments = Department.query.order_by(Department.name).all()

    return jsonify({
        'success': True,
        'departments': [
            {
                'id': dept.id,
                'name': dept.name,
                'head_id': dept.head_id,
                'member_count': len(dept.members) if hasattr(dept, 'members') else 0
            }
            for dept in departments
        ]
    })


@team_api_bp.route("/stats", methods=["GET"])
@login_required
def get_team_stats():
    """Get team statistics."""
    visible_users = User.query.filter(User.role.isnot(None))

    # Total counts
    total_members = visible_users.count()
    total_active = visible_users.filter(User.is_active == True).count()
    total_admins = visible_users.filter(User.is_admin == True, User.is_active == True).count()
    total_trial = visible_users.filter(User.is_trial == True, User.is_active == True).count()

    # Count team leaders by active teams' head_id (source of truth), not only by user.role
    total_team_leaders = db.session.query(func.count(distinct(Team.head_id))).join(
        User, User.id == Team.head_id
    ).filter(
        Team.is_active == True,
        Team.head_id.isnot(None),
        User.is_active == True,
        User.role.isnot(None),
    ).scalar() or 0

    total_professionisti = visible_users.filter(
        User.is_active == True,
        User.role == UserRoleEnum.professionista
    ).count()
    total_external = visible_users.filter(
        User.is_active == True,
        User.is_external == True
    ).count()

    return jsonify({
        'success': True,
        'total_members': total_members,
        'total_active': total_active,
        'total_admins': total_admins,
        'total_trial': total_trial,
        'total_team_leaders': total_team_leaders,
        'total_professionisti': total_professionisti,
        'total_external': total_external
    })



@team_api_bp.route("/professionals/criteria", methods=["GET"])
@login_required
def api_get_professionals_criteria():
    """Restituisce lista professionisti con i loro criteri di assegnazione."""
    current_app.logger.info(f"Fetching professionals criteria for user {current_user.id}")
    
    # Target specialties using Enum instances for robustness
    target_specialties = [
        UserSpecialtyEnum.nutrizionista, UserSpecialtyEnum.nutrizione,
        UserSpecialtyEnum.coach,
        UserSpecialtyEnum.psicologo, UserSpecialtyEnum.psicologia
    ]
    
    prof_query = User.query.options(
        selectinload(User.teams)
    ).filter(
        User.specialty.in_(target_specialties),
        User.is_active == True
    )

    if not _can_view_all_team_module_data(current_user) and _get_user_role(current_user) == 'team_leader':
        led_team_ids = [t.id for t in (current_user.teams_led or []) if getattr(t, 'is_active', True)]
        if not led_team_ids:
            return jsonify({'success': True, 'professionals': []})
        prof_query = prof_query.filter(User.teams.any(Team.id.in_(led_team_ids)))

    professionals = prof_query.order_by(User.first_name, User.last_name).all()

    current_app.logger.info(f"Found {len(professionals)} professionals with target specialties")

    results = []
    import json
    
    for p in professionals:
        # Determina "department_id" e nome basato su specialty
        dept_id = 0
        dept_name = 'N/A'
        
        # Get value safely
        spec_val = p.specialty.value if hasattr(p.specialty, 'value') else str(p.specialty)
        if spec_val.startswith('UserSpecialtyEnum.'):
            spec_val = spec_val.split('.')[-1]
        
        if spec_val in ['nutrizionista', 'nutrizione']:
            dept_id = 2 # Nutrizione
            dept_name = 'Nutrizione'
        elif spec_val == 'coach':
            dept_id = 3 # Coach
            dept_name = 'Coach'
        elif spec_val in ['psicologo', 'psicologia']:
            dept_id = 4 # Psicologia
            dept_name = 'Psicologia'
            
        criteria = p.assignment_criteria or {}
        ai_notes = p.assignment_ai_notes or {}
        if isinstance(ai_notes, str):
            try:
                ai_notes = json.loads(ai_notes)
            except:
                ai_notes = {}
                
        results.append({
            'id': p.id,
            'name': f"{p.first_name} {p.last_name}",
            'department_id': dept_id,
            'department_name': dept_name,
            'avatar_path': p.avatar_path,
            'criteria': criteria,
            'ai_notes_summary': ai_notes.get('specializzazione', '') + ' ' + ai_notes.get('target_ideale', ''),
            'is_available': ai_notes.get('disponibile_assegnazioni', True),
            'teams': [
                {
                    'id': t.id,
                    'name': t.name,
                    'team_type': t.team_type.value if t.team_type else None
                }
                for t in (p.teams or [])
            ],
        })

    return jsonify({
        'success': True,
        'professionals': results
    })


@team_api_bp.route("/professionals/<int:user_id>/criteria", methods=["PUT"])
@login_required
# @csrf.exempt # Already exempt at blueprint level
def api_update_professional_criteria(user_id: int):
    """Aggiorna i criteri di assegnazione per un professionista."""
    # Check permissions
    if not current_user.is_admin and not (current_user.role.value in ['team_leader']):
         return jsonify({'success': False, 'message': 'Non autorizzato'}), 403
    
    user = User.query.get_or_404(user_id)

    if not current_user.is_admin and _get_user_role(current_user) == 'team_leader':
        allowed_ids = _get_team_leader_member_ids(current_user.id) | {current_user.id}
        if user.id not in allowed_ids:
            return jsonify({'success': False, 'message': 'Puoi modificare solo membri dei tuoi team'}), 403
    data = request.get_json()
    
    if not data or 'criteria' not in data:
        return jsonify({'success': False, 'message': 'Dati mancanti'}), 400
        
    criteria = data['criteria']
    
    # Validazione tramite Service
    from .criteria_service import CriteriaService
    
    spec_val = user.specialty.value if hasattr(user.specialty, 'value') else str(user.specialty)
    role_key = None
    
    if spec_val in ['nutrizionista', 'nutrizione']:
        role_key = 'nutrizione'
    elif spec_val == 'coach':
        role_key = 'coach'
    elif spec_val in ['psicologo', 'psicologia']:
        role_key = 'psicologia'
    
    if role_key:
        valid_criteria = CriteriaService.validate_criteria(role_key, criteria)
        user.assignment_criteria = valid_criteria
        db.session.commit()
        return jsonify({'success': True, 'message': 'Criteri aggiornati'})
    else:
        return jsonify({'success': False, 'message': 'Ruolo non supportato per assegnazione AI'}), 400

@team_api_bp.route("/professionals/<int:user_id>/toggle-available", methods=["PUT"])
@login_required
def api_toggle_professional_available(user_id: int):
    """Toggle disponibilità assegnazioni per un professionista."""
    if not current_user.is_admin and not (current_user.role.value in ['team_leader']):
        return jsonify({'success': False, 'message': 'Non autorizzato'}), 403

    user = User.query.get_or_404(user_id)

    if not current_user.is_admin and _get_user_role(current_user) == 'team_leader':
        allowed_ids = _get_team_leader_member_ids(current_user.id) | {current_user.id}
        if user.id not in allowed_ids:
            return jsonify({'success': False, 'message': 'Puoi modificare solo membri dei tuoi team'}), 403

    ai_notes = user.assignment_ai_notes or {}
    if isinstance(ai_notes, str):
        import json
        try:
            ai_notes = json.loads(ai_notes)
        except (json.JSONDecodeError, TypeError):
            ai_notes = {}

    current_value = ai_notes.get('disponibile_assegnazioni', True)
    ai_notes['disponibile_assegnazioni'] = not current_value
    user.assignment_ai_notes = ai_notes

    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(user, 'assignment_ai_notes')

    try:
        db.session.commit()
        new_status = "disponibile" if ai_notes['disponibile_assegnazioni'] else "non disponibile"
        return jsonify({
            'success': True,
            'disponibile': ai_notes['disponibile_assegnazioni'],
            'message': f'{user.full_name} ora è {new_status} per nuove assegnazioni'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore toggle disponibilità: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@team_api_bp.route("/criteria/schema", methods=["GET"])
@login_required
def api_get_criteria_schema():
    """Restituisce lo schema dei criteri disponibili."""
    from .criteria_service import CriteriaService
    return jsonify({
        'success': True,
        'schema': CriteriaService.get_schema()
    })

# =============================================================================
# AI Assignment Endpoints
# =============================================================================

@team_api_bp.route("/assignments/analyze-lead", methods=["POST"])
@login_required
def api_analyze_lead_story():
    """
    Analizza la storia del lead con l'AI per estrarre i criteri.
    Supporta la persistenza se viene passato opportunity_id o assignment_id.
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Dati mancanti'}), 400
        
    story = data.get('story')
    opportunity_id = data.get('opportunity_id')
    assignment_id = data.get('assignment_id')
    sales_lead_id = data.get('sales_lead_id')  # Old Suite integration
    role = data.get('role') # 'nutrition', 'coach', 'psychology', or None (legacy)
    force_refresh = data.get('force_refresh', False)

    # 1. Tenta di recuperare dai dati già salvati (se non forzato)
    existing_analysis = None
    existing_obj = None # Store the object to update later

    if assignment_id:
        existing_obj = ServiceClienteAssignment.query.get(assignment_id)
        if existing_obj:
            existing_analysis = existing_obj.ai_analysis
    elif sales_lead_id:
        existing_obj = SalesLead.query.get(sales_lead_id)
        if existing_obj:
            existing_analysis = existing_obj.ai_analysis
    elif opportunity_id:
        existing_obj = GHLOpportunityData.query.get(opportunity_id)
        if existing_obj:
            existing_analysis = existing_obj.ai_analysis

    if not force_refresh and existing_analysis:
        # Se è un formato nuovo (dizionario con chiavi ruolo)
        if role and isinstance(existing_analysis, dict) and role in existing_analysis:
             return jsonify({
                'success': True,
                'analysis': existing_analysis[role], # Restituisci solo la parte richiesta
                'full_analysis': existing_analysis,
                'cached': True
            })
        # Se non è specificato ruolo e abbiamo dati (comportamento legacy o full)
        elif not role:
             return jsonify({
                'success': True,
                'analysis': existing_analysis,
                'cached': True
            })

    # 2. Se non abbiamo cache per il ruolo richiesto, procediamo con l'analisi AI
    if not story:
        return jsonify({'success': False, 'message': 'Storia mancante'}), 400
        
    from .ai_matching_service import AIMatchingService
    try:
        # Passiamo il role al service
        result = AIMatchingService.extract_lead_criteria(story, target_role=role)
        
        # Formattazione risultato standardizzata dal service
        analysis_part = result
            
        # 3. Salva nel database per persistenza (Merge con esistente)
        if existing_obj:
            current_data = dict(existing_obj.ai_analysis) if existing_obj.ai_analysis else {}
            
            if role:
                # Aggiorna solo la chiave del ruolo
                current_data[role] = analysis_part
            else:
                # Legacy/Full overwrite se non c'è ruolo
                current_data = analysis_part

            existing_obj.ai_analysis = current_data
            
            if assignment_id:
                existing_obj.ai_suggested_at = datetime.utcnow()
            elif sales_lead_id:
                existing_obj.ai_analyzed_at = datetime.utcnow()
            elif opportunity_id:
                existing_obj.ai_analyzed_at = datetime.utcnow()
                
            db.session.commit()
            
            return jsonify({
                'success': True,
                'analysis': analysis_part
            })
            
        return jsonify({
            'success': True,
            'analysis': analysis_part,
            'warning': 'Not saved (no ID provided)'
        })
            
        return jsonify({
            'success': True,
            'analysis': analysis,
            'cached': False
        })
    except Exception as e:
        current_app.logger.error(f"Error analyzing lead: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@team_api_bp.route("/assignments/match", methods=["POST"])
@login_required
def api_match_professionals():
    """
    Trova i professionisti migliori in base ai criteri estratti.
    Input: { "criteria": ["TAG1", "TAG2"] }
    Output: { "success": true, "matches": { "nutrizione": [...], ... } }
    """
    data = request.get_json()
    criteria = data.get('criteria', [])
    
    from .ai_matching_service import AIMatchingService
    try:
        matches = AIMatchingService.match_professionals(criteria)

        if not _can_view_all_team_module_data(current_user) and _get_user_role(current_user) == 'team_leader':
            allowed_ids = _get_team_leader_member_ids(current_user.id) | {current_user.id}
            filtered_matches = {}
            for role_key, candidates in (matches or {}).items():
                if isinstance(candidates, list):
                    filtered_matches[role_key] = [
                        c for c in candidates
                        if isinstance(c, dict) and c.get('id') in allowed_ids
                    ]
                else:
                    filtered_matches[role_key] = candidates
            matches = filtered_matches

        return jsonify({
            'success': True,
            'matches': matches
        })
    except Exception as e:
        current_app.logger.error(f"Error matching professionals: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@team_api_bp.route("/assignments/confirm", methods=["POST"])
@login_required
def api_confirm_assignment():
    """
    Conferma l'assegnazione dei professionisti per un cliente.
    Input: {
        "assignment_id": 123,
        "nutritionist_id": 456,
        "coach_id": 789,
        "psychologist_id": 101,
        "notes": "Note opzionali"
    }
    Output: { "success": true, "message": "Assegnazione confermata" }
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Dati mancanti'}), 400
        
    assignment_id = data.get('assignment_id')
    opportunity_data_id = data.get('opportunity_data_id')

    if not assignment_id and not opportunity_data_id:
        return jsonify({'success': False, 'message': 'ID assegnazione o ID Lead mancante'}), 400
        
    try:
        assignment = None
        
        # Se abbiamo assignment_id, usiamolo direttamente
        if assignment_id:
            assignment = ServiceClienteAssignment.query.get(assignment_id)
            
        # Altrimenti, creiamo l'assegnazione da GHLOpportunityData
        elif opportunity_data_id:
            opp_data = GHLOpportunityData.query.get(opportunity_data_id)
            if not opp_data:
                return jsonify({'success': False, 'message': 'Lead non trovato'}), 404
            
            # Estrai email dal payload se possibile
            payload = opp_data.raw_payload or {}
            email = payload.get('email') or payload.get('contact', {}).get('email')
            
            if not email:
                # Fallback email se non trovata nel payload
                email = f"lead-{opp_data.id}@ghl-lead.com"
                
            # Verifica se esiste già un cliente con questa email
            cliente = Cliente.query.filter_by(mail=email).first()
            if not cliente:
                cliente = Cliente(
                    nome_cognome=opp_data.nome,
                    mail=email,
                    storia_cliente=opp_data.storia,
                    programma_attuale=opp_data.pacchetto,
                    acquisition_source='ghl_manual_ai',
                    service_status='pending_assignment',
                    show_in_clienti_lista=False,
                    created_at=datetime.utcnow()
                )
                db.session.add(cliente)
                db.session.flush()
                
            # Crea o trova assignment
            assignment = ServiceClienteAssignment.query.filter_by(cliente_id=cliente.cliente_id).first()
            if not assignment:
                assignment = ServiceClienteAssignment(
                    cliente_id=cliente.cliente_id,
                    status='pending_assignment',
                    created_at=datetime.utcnow()
                )
                db.session.add(assignment)
                db.session.flush()
            
            # Segna lead come processato
            opp_data.processed = True
            db.session.add(opp_data)

        if not assignment:
            return jsonify({'success': False, 'message': 'Impossibile trovare o creare l\'assegnazione'}), 404
            
        cliente = assignment.cliente
        if not cliente:
            return jsonify({'success': False, 'message': 'Cliente non trovato'}), 404
            
        if not _can_view_all_team_module_data(current_user) and _get_user_role(current_user) == 'team_leader':
            allowed_ids = _get_team_leader_member_ids(current_user.id) | {current_user.id}
            requested_prof_ids = {
                pid for pid in [
                    data.get('nutritionist_id'),
                    data.get('coach_id'),
                    data.get('psychologist_id'),
                ]
                if pid
            }
            if any(int(pid) not in allowed_ids for pid in requested_prof_ids):
                return jsonify({'success': False, 'message': 'Puoi assegnare solo professionisti dei tuoi team'}), 403

        # Update assignment
        if data.get('ai_analysis'):
            assignment.ai_analysis = data.get('ai_analysis')
            assignment.ai_suggested_at = datetime.utcnow()
            
        if data.get('nutritionist_id'):
            assignment.nutrizionista_assigned_id = data.get('nutritionist_id')
            assignment.nutrizionista_assigned_at = datetime.utcnow()
            assignment.nutrizionista_assigned_by = current_user.id
            
        if data.get('coach_id'):
            assignment.coach_assigned_id = data.get('coach_id')
            assignment.coach_assigned_at = datetime.utcnow()
            assignment.coach_assigned_by = current_user.id
            
        if data.get('psychologist_id'):
            assignment.psicologa_assigned_id = data.get('psychologist_id')
            assignment.psicologa_assigned_at = datetime.utcnow()
            assignment.psicologa_assigned_by = current_user.id
        
        # Update status
        assignment.update_status()
        
        # Add notes
        if data.get('notes'):
            note = ServiceClienteNote(
                assignment_id=assignment.id,
                cliente_id=cliente.cliente_id,
                note_text=data['notes'],
                note_type='assignment',
                created_by=current_user.id
            )
            db.session.add(note)
            
        # Create history entries
        motivazione = "Assegnazione manuale da pannello AI"
        data_inizio = datetime.utcnow().date()
        
        if data.get('nutritionist_id'):
            h_nutri = ClienteProfessionistaHistory(
                cliente_id=cliente.cliente_id,
                user_id=data.get('nutritionist_id'),
                tipo_professionista='nutrizionista',
                data_dal=data_inizio,
                motivazione_aggiunta=motivazione,
                assegnato_da_id=current_user.id,
                is_active=True
            )
            db.session.add(h_nutri)
            
            # Add to many-to-many
            nutri = User.query.get(data.get('nutritionist_id'))
            if nutri and nutri not in cliente.nutrizionisti_multipli:
                cliente.nutrizionisti_multipli.append(nutri)
            
        if data.get('coach_id'):
            h_coach = ClienteProfessionistaHistory(
                cliente_id=cliente.cliente_id,
                user_id=data.get('coach_id'),
                tipo_professionista='coach',
                data_dal=data_inizio,
                motivazione_aggiunta=motivazione,
                assegnato_da_id=current_user.id,
                is_active=True
            )
            db.session.add(h_coach)
            
            # Add to many-to-many
            coach = User.query.get(data.get('coach_id'))
            if coach and coach not in cliente.coaches_multipli:
                cliente.coaches_multipli.append(coach)
            
        if data.get('psychologist_id'):
            h_psico = ClienteProfessionistaHistory(
                cliente_id=cliente.cliente_id,
                user_id=data.get('psychologist_id'),
                tipo_professionista='psicologa',
                data_dal=data_inizio,
                motivazione_aggiunta=motivazione,
                assegnato_da_id=current_user.id,
                is_active=True
            )
            db.session.add(h_psico)
            
            # Add to many-to-many
            psico = User.query.get(data.get('psychologist_id'))
            if psico and psico not in cliente.psicologi_multipli:
                cliente.psicologi_multipli.append(psico)

        # Update Cliente status
        cliente.service_status = 'assigned'
        if assignment.status in ('fully_assigned', 'active'):
            cliente.show_in_clienti_lista = True
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Assegnazione completata con successo',
            'status': assignment.status
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error validating assignment: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500
    except Exception as e:
        current_app.logger.error(f"Error matching professionals: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@team_api_bp.route("/admin-dashboard-stats", methods=["GET"])
@login_required
def get_admin_dashboard_stats():
    """
    Dashboard statistics for professionals; data filtered by role
    (admin=all, TL=team members, professionista=own).
    """
    from corposostenibile.models import QualityWeeklyScore, Cliente, StatoClienteEnum
    from corposostenibile.models import cliente_nutrizionisti, cliente_coaches, cliente_psicologi
    from datetime import datetime, timedelta
    from sqlalchemy import select, case, literal_column

    try:
        today = datetime.now().date()
        visible_ids = _get_visible_user_ids_for_dashboard()

        def _user_query(base=None):
            q = base if base is not None else User.query
            if visible_ids is not None:
                q = q.filter(User.id.in_(visible_ids))
            return q

        # ─── KPI: Counts ───
        total_all = _user_query().count()
        total_active = _user_query(User.query.filter_by(is_active=True)).count()
        total_inactive = total_all - total_active
        total_admins = _user_query(User.query.filter_by(is_admin=True, is_active=True)).count()
        total_trial = _user_query(User.query.filter_by(is_trial=True, is_active=True)).count()
        total_team_leaders = _user_query(User.query.filter(
            User.is_active == True,
            User.role == UserRoleEnum.team_leader
        )).count()
        total_professionisti = _user_query(User.query.filter(
            User.is_active == True,
            User.role == UserRoleEnum.professionista
        )).count()
        total_external = _user_query(User.query.filter(
            User.is_active == True,
            User.is_external == True
        )).count()

        # ─── Specialty Distribution ───
        specialty_q = db.session.query(User.specialty, func.count(User.id)).filter(
            User.is_active == True,
            User.specialty.isnot(None)
        )
        if visible_ids is not None:
            specialty_q = specialty_q.filter(User.id.in_(visible_ids))
        specialty_counts = specialty_q.group_by(User.specialty).all()

        specialty_distribution = {}
        specialty_labels = {
            'nutrizione': 'Nutrizione (TL)',
            'nutrizionista': 'Nutrizionisti',
            'psicologia': 'Psicologia (TL)',
            'psicologo': 'Psicologi',
            'coach': 'Coach',
            'amministrazione': 'Amministrazione',
            'cco': 'CCO',
        }
        for spec, count in specialty_counts:
            key = spec.value if hasattr(spec, 'value') else str(spec)
            specialty_distribution[key] = {
                'count': count,
                'label': specialty_labels.get(key, key.capitalize())
            }

        # ─── Role Distribution ───
        role_q = db.session.query(User.role, func.count(User.id)).filter(
            User.is_active == True,
            User.role.isnot(None)
        )
        if visible_ids is not None:
            role_q = role_q.filter(User.id.in_(visible_ids))
        role_counts = role_q.group_by(User.role).all()

        role_distribution = {}
        role_labels = {
            'admin': 'Admin',
            'team_leader': 'Team Leader',
            'professionista': 'Professionista',
            'team_esterno': 'Team Esterno',
        }
        for role, count in role_counts:
            key = role.value if hasattr(role, 'value') else str(role)
            role_distribution[key] = {
                'count': count,
                'label': role_labels.get(key, key.capitalize())
            }

        # ─── Quality Scores (latest week) ───
        latest_week = db.session.query(
            func.max(QualityWeeklyScore.week_start_date)
        ).scalar()

        quality_summary = {
            'avgQuality': None,
            'avgMonth': None,
            'avgTrim': None,
            'bonusBands': {'100%': 0, '60%': 0, '30%': 0, '0%': 0},
            'trendUp': 0,
            'trendDown': 0,
            'trendStable': 0,
        }

        if latest_week:
            latest_scores_q = QualityWeeklyScore.query.filter_by(
                week_start_date=latest_week,
                calculation_status='completed'
            )
            if visible_ids is not None:
                latest_scores_q = latest_scores_q.filter(QualityWeeklyScore.professionista_id.in_(visible_ids))
            latest_scores = latest_scores_q.all()

            if latest_scores:
                finals = [s.quality_final for s in latest_scores if s.quality_final is not None]
                months = [s.quality_month for s in latest_scores if s.quality_month is not None]
                trims = [s.quality_trim for s in latest_scores if s.quality_trim is not None]

                quality_summary['avgQuality'] = round(sum(finals) / len(finals), 2) if finals else None
                quality_summary['avgMonth'] = round(sum(months) / len(months), 2) if months else None
                quality_summary['avgTrim'] = round(sum(trims) / len(trims), 2) if trims else None

                for s in latest_scores:
                    band = s.bonus_band or '0%'
                    if band in quality_summary['bonusBands']:
                        quality_summary['bonusBands'][band] += 1

                    trend = s.trend_indicator
                    if trend == 'up':
                        quality_summary['trendUp'] += 1
                    elif trend == 'down':
                        quality_summary['trendDown'] += 1
                    else:
                        quality_summary['trendStable'] += 1

        # ─── Top Performers (by quality_final, latest week) ───
        top_performers = []
        if latest_week:
            top_scores_q = QualityWeeklyScore.query.filter_by(
                week_start_date=latest_week,
                calculation_status='completed'
            ).filter(QualityWeeklyScore.quality_final.isnot(None))
            if visible_ids is not None:
                top_scores_q = top_scores_q.filter(QualityWeeklyScore.professionista_id.in_(visible_ids))
            top_scores = top_scores_q.order_by(
                QualityWeeklyScore.quality_final.desc()
            ).limit(10).all()

            for s in top_scores:
                prof = s.professionista
                if prof:
                    top_performers.append({
                        'id': prof.id,
                        'name': prof.full_name,
                        'specialty': _get_user_specialty(prof),
                        'quality_final': round(s.quality_final, 2) if s.quality_final else None,
                        'quality_month': round(s.quality_month, 2) if s.quality_month else None,
                        'bonus_band': s.bonus_band,
                        'trend': s.trend_indicator,
                        'avatar_path': prof.avatar_path,
                    })

        # ─── Trial Users ───
        trial_q = User.query.filter_by(is_trial=True, is_active=True)
        if visible_ids is not None:
            trial_q = trial_q.filter(User.id.in_(visible_ids))
        trial_users = trial_q.order_by(User.created_at.desc()).limit(10).all()

        trial_list = []
        for u in trial_users:
            trial_list.append({
                'id': u.id,
                'name': u.full_name,
                'specialty': _get_user_specialty(u),
                'trial_stage': u.trial_stage,
                'avatar_path': u.avatar_path,
                'created_at': u.created_at.isoformat() if u.created_at else None,
            })

        # ─── Quality Weekly Trend (last 8 weeks) ───
        quality_trend = []
        if latest_week:
            eight_weeks_ago = latest_week - timedelta(weeks=8)
            trend_q = db.session.query(
                QualityWeeklyScore.week_start_date,
                func.avg(QualityWeeklyScore.quality_final),
                func.count(QualityWeeklyScore.id)
            ).filter(
                QualityWeeklyScore.week_start_date >= eight_weeks_ago,
                QualityWeeklyScore.calculation_status == 'completed',
                QualityWeeklyScore.quality_final.isnot(None)
            )
            if visible_ids is not None:
                trend_q = trend_q.filter(QualityWeeklyScore.professionista_id.in_(visible_ids))
            weekly_avgs = trend_q.group_by(
                QualityWeeklyScore.week_start_date
            ).order_by(
                QualityWeeklyScore.week_start_date
            ).all()

            for week_date, avg_quality, count in weekly_avgs:
                quality_trend.append({
                    'week': week_date.isoformat(),
                    'avgQuality': round(float(avg_quality), 2),
                    'count': count
                })

        # ─── Teams Summary ───
        if visible_ids is None:
            teams = Team.query.filter_by(is_active=True).all()
        elif getattr(current_user, 'role', None) == UserRoleEnum.team_leader and current_user.teams_led:
            team_ids = [t.id for t in current_user.teams_led]
            teams = Team.query.filter(Team.id.in_(team_ids), Team.is_active == True).all()
        else:
            # Professionista: teams of which they are a member
            teams = Team.query.filter_by(is_active=True).filter(
                Team.members.any(User.id == current_user.id)
            ).all()
        teams_summary = []
        for team in teams:
            member_count = len(team.members) if team.members else 0
            teams_summary.append({
                'id': team.id,
                'name': team.name,
                'team_type': team.team_type.value if team.team_type else None,
                'head_name': team.head.full_name if team.head else None,
                'member_count': member_count,
            })

        # ─── Client Load per Specialty ───
        # Count active clients per specialty (only for visible professionals when filtered)
        nutri_clients_q = db.session.query(func.count(Cliente.cliente_id)).filter(
            Cliente.stato_cliente.in_([StatoClienteEnum.attivo, StatoClienteEnum.pausa]),
            or_(
                Cliente.nutrizionista_id.isnot(None),
                Cliente.cliente_id.in_(select(cliente_nutrizionisti.c.cliente_id))
            )
        )
        if visible_ids is not None:
            nutri_clients_q = nutri_clients_q.filter(
                or_(
                    Cliente.nutrizionista_id.in_(visible_ids),
                    Cliente.nutrizionisti_multipli.any(User.id.in_(visible_ids))
                )
            )
        nutri_clients = nutri_clients_q.scalar() or 0

        coach_clients_q = db.session.query(func.count(Cliente.cliente_id)).filter(
            Cliente.stato_cliente.in_([StatoClienteEnum.attivo, StatoClienteEnum.pausa]),
            or_(
                Cliente.coach_id.isnot(None),
                Cliente.cliente_id.in_(select(cliente_coaches.c.cliente_id))
            )
        )
        if visible_ids is not None:
            coach_clients_q = coach_clients_q.filter(
                or_(
                    Cliente.coach_id.in_(visible_ids),
                    Cliente.coaches_multipli.any(User.id.in_(visible_ids))
                )
            )
        coach_clients = coach_clients_q.scalar() or 0

        psico_clients_q = db.session.query(func.count(Cliente.cliente_id)).filter(
            Cliente.stato_cliente.in_([StatoClienteEnum.attivo, StatoClienteEnum.pausa]),
            or_(
                Cliente.psicologa_id.isnot(None),
                Cliente.cliente_id.in_(select(cliente_psicologi.c.cliente_id))
            )
        )
        if visible_ids is not None:
            psico_clients_q = psico_clients_q.filter(
                or_(
                    Cliente.psicologa_id.in_(visible_ids),
                    Cliente.psicologi_multipli.any(User.id.in_(visible_ids))
                )
            )
        psico_clients = psico_clients_q.scalar() or 0

        # Professionals count per clinical specialty (visible only when filtered)
        nutri_profs = _user_query(User.query.filter(
            User.is_active == True,
            User.specialty.in_([UserSpecialtyEnum.nutrizione, UserSpecialtyEnum.nutrizionista])
        )).count()
        coach_profs = _user_query(User.query.filter(
            User.is_active == True,
            User.specialty == UserSpecialtyEnum.coach
        )).count()
        psico_profs = _user_query(User.query.filter(
            User.is_active == True,
            User.specialty.in_([UserSpecialtyEnum.psicologia, UserSpecialtyEnum.psicologo])
        )).count()

        client_load = {
            'nutrizione': {
                'clients': nutri_clients,
                'professionals': nutri_profs,
                'avgLoad': round(nutri_clients / nutri_profs, 1) if nutri_profs > 0 else 0
            },
            'coach': {
                'clients': coach_clients,
                'professionals': coach_profs,
                'avgLoad': round(coach_clients / coach_profs, 1) if coach_profs > 0 else 0
            },
            'psicologia': {
                'clients': psico_clients,
                'professionals': psico_profs,
                'avgLoad': round(psico_clients / psico_profs, 1) if psico_profs > 0 else 0
            },
        }

        return jsonify({
            'success': True,
            'kpi': {
                'totalAll': total_all,
                'totalActive': total_active,
                'totalInactive': total_inactive,
                'totalAdmins': total_admins,
                'totalTrial': total_trial,
                'totalTeamLeaders': total_team_leaders,
                'totalProfessionisti': total_professionisti,
                'totalExternal': total_external,
            },
            'specialtyDistribution': specialty_distribution,
            'roleDistribution': role_distribution,
            'qualitySummary': quality_summary,
            'topPerformers': top_performers,
            'trialUsers': trial_list,
            'qualityTrend': quality_trend,
            'teamsSummary': teams_summary,
            'clientLoad': client_load,
        })

    except Exception as e:
        current_app.logger.error(f"Error in admin-dashboard-stats: {e}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'Errore nel calcolo statistiche: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR


# =============================================================================
# Team Entity Management - Gestione Team per Specializzazione
# =============================================================================

# Mapping team_type -> specialties compatibili per Team Leader
TEAM_TYPE_LEADER_SPECIALTIES = {
    'nutrizione': [UserSpecialtyEnum.nutrizione],
    'coach': [UserSpecialtyEnum.coach],
    'psicologia': [UserSpecialtyEnum.psicologia],
    'health_manager': [],
}

# Mapping team_type -> specialties compatibili per Professionisti
TEAM_TYPE_PROFESSIONAL_SPECIALTIES = {
    'nutrizione': [UserSpecialtyEnum.nutrizione, UserSpecialtyEnum.nutrizionista],
    'coach': [UserSpecialtyEnum.coach],
    'psicologia': [UserSpecialtyEnum.psicologia, UserSpecialtyEnum.psicologo],
    'health_manager': [],
}


def _serialize_team(team, include_members=False):
    """Serialize team object to JSON-safe dict."""
    data = {
        'id': team.id,
        'name': team.name,
        'description': team.description,
        'team_type': team.team_type.value if team.team_type else None,
        'is_active': team.is_active,
        'head_id': team.head_id,
        'head': _serialize_user(team.head, include_teams_led=False) if team.head else None,
        'member_count': len(team.members) if team.members else 0,
        'created_at': team.created_at.isoformat() if team.created_at else None,
        'updated_at': team.updated_at.isoformat() if team.updated_at else None,
    }

    # Only load members when explicitly requested (expensive)
    if include_members:
        data['members'] = [_serialize_user(m, include_teams_led=False) for m in (team.members or [])]

    return data


@team_api_bp.route("/teams", methods=["GET"])
@login_required
def get_teams():
    """
    Get list of teams with server-side pagination.

    Query params:
        - page: Page number (default 1)
        - per_page: Items per page (default 12, max 100)
        - team_type: Filter by team type (nutrizione, coach, psicologia)
        - active: Filter by active status ('1' or '0')
        - q: Search query (searches team name)
        - include_members: Include team members in response ('1' to include)
    """
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 12, type=int), 100)
    team_type_filter = request.args.get('team_type', '').strip()
    active_filter = request.args.get('active', '').strip()
    search_query = request.args.get('q', '').strip()
    include_members_raw = request.args.get('include_members', '').strip().lower()
    include_members = include_members_raw in {'1', 'true', 'yes', 'on'}

    # Base query with eager loading for head only (fast)
    query = Team.query.options(
        joinedload(Team.head)  # Eager load team head only
    )

    # RBAC base scope
    if _can_view_all_team_module_data(current_user):
        pass
    elif _get_user_role(current_user) == 'team_leader':
        query = query.filter(Team.head_id == current_user.id)
    else:
        query = query.filter(Team.members.any(User.id == current_user.id))

    # Filter by team_type
    if team_type_filter and team_type_filter in [e.value for e in TeamTypeEnum]:
        query = query.filter(Team.team_type == TeamTypeEnum(team_type_filter))

    # Filter by active
    if active_filter == '1':
        query = query.filter(Team.is_active == True)
    elif active_filter == '0':
        query = query.filter(Team.is_active == False)

    # Search filter
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(Team.name.ilike(search_term))

    # Order by team_type, then name
    query = query.order_by(Team.team_type, Team.name)

    # Server-side pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'success': True,
        'teams': [_serialize_team(t, include_members=include_members) for t in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'per_page': pagination.per_page,
        'total_pages': pagination.pages
    })


@team_api_bp.route("/teams/<int:team_id>", methods=["GET"])
@login_required
def get_team(team_id):
    """Get single team details with members."""
    team = Team.query.get_or_404(team_id)

    if not _can_view_all_team_module_data(current_user):
        if _get_user_role(current_user) == 'team_leader':
            if team.head_id != current_user.id:
                return jsonify({'success': False, 'message': 'Accesso non autorizzato'}), HTTPStatus.FORBIDDEN
        elif not any(m.id == current_user.id for m in (team.members or [])):
            return jsonify({'success': False, 'message': 'Accesso non autorizzato'}), HTTPStatus.FORBIDDEN

    return jsonify({
        'success': True,
        **_serialize_team(team, include_members=True)
    })


@team_api_bp.route("/teams", methods=["POST"])
@login_required
def create_team():
    """Create new team."""
    # Check admin permission
    perm_error = _require_admin()
    if perm_error:
        return perm_error

    data = request.get_json()
    if not data:
        return jsonify({
            'success': False,
            'message': 'Dati non validi'
        }), HTTPStatus.BAD_REQUEST

    # Validate required fields
    if not data.get('name'):
        return jsonify({
            'success': False,
            'message': 'Nome team obbligatorio'
        }), HTTPStatus.BAD_REQUEST

    if not data.get('team_type'):
        return jsonify({
            'success': False,
            'message': 'Tipo team obbligatorio'
        }), HTTPStatus.BAD_REQUEST

    team_type_str = data['team_type']
    if team_type_str not in [e.value for e in TeamTypeEnum]:
        return jsonify({
            'success': False,
            'message': 'Tipo team non valido'
        }), HTTPStatus.BAD_REQUEST

    # Check unique name per type
    existing = Team.query.filter_by(
        team_type=TeamTypeEnum(team_type_str),
        name=data['name']
    ).first()
    if existing:
        return jsonify({
            'success': False,
            'message': 'Esiste già un team con questo nome per questo tipo'
        }), HTTPStatus.BAD_REQUEST

    try:
        team = Team(
            name=data['name'],
            description=data.get('description'),
            team_type=TeamTypeEnum(team_type_str),
            head_id=data.get('head_id'),
            is_active=True
        )

        # Add initial members if provided
        member_ids = data.get('member_ids', [])
        if member_ids:
            members = User.query.filter(User.id.in_(member_ids)).all()
            team.members = members

        _promote_team_head_to_team_leader(team.head_id)

        db.session.add(team)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Team creato con successo',
            **_serialize_team(team, include_members=True)
        }), HTTPStatus.CREATED

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating team: {e}")
        return jsonify({
            'success': False,
            'message': f'Errore durante la creazione: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@team_api_bp.route("/teams/<int:team_id>", methods=["PUT"])
@login_required
def update_team(team_id):
    """Update team."""
    # Check admin permission
    perm_error = _require_admin()
    if perm_error:
        return perm_error

    team = Team.query.get_or_404(team_id)
    data = request.get_json()

    if not data:
        return jsonify({
            'success': False,
            'message': 'Dati non validi'
        }), HTTPStatus.BAD_REQUEST

    try:
        # Update name
        if 'name' in data:
            # Check uniqueness if changing name
            if data['name'] != team.name:
                existing = Team.query.filter_by(
                    team_type=team.team_type,
                    name=data['name']
                ).first()
                if existing:
                    return jsonify({
                        'success': False,
                        'message': 'Esiste già un team con questo nome per questo tipo'
                    }), HTTPStatus.BAD_REQUEST
            team.name = data['name']

        # Update description
        if 'description' in data:
            team.description = data['description']

        # Update head_id
        if 'head_id' in data:
            team.head_id = data['head_id'] if data['head_id'] else None
            _promote_team_head_to_team_leader(team.head_id)

        # Update is_active
        if 'is_active' in data:
            team.is_active = data['is_active']

        # Update members if provided
        if 'member_ids' in data:
            members = User.query.filter(User.id.in_(data['member_ids'])).all()
            team.members = members

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Team aggiornato con successo',
            **_serialize_team(team, include_members=True)
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating team: {e}")
        return jsonify({
            'success': False,
            'message': f'Errore durante l\'aggiornamento: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@team_api_bp.route("/teams/<int:team_id>", methods=["DELETE"])
@login_required
def delete_team(team_id):
    """Delete team (soft delete by deactivating)."""
    # Check admin permission
    perm_error = _require_admin()
    if perm_error:
        return perm_error

    team = Team.query.get_or_404(team_id)

    try:
        # Soft delete - just deactivate
        team.is_active = False
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Team disattivato con successo'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting team: {e}")
        return jsonify({
            'success': False,
            'message': f'Errore durante l\'eliminazione: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@team_api_bp.route("/teams/<int:team_id>/members", methods=["POST"])
@login_required
def add_team_member(team_id):
    """Add member to team."""
    # Check admin permission
    perm_error = _require_admin()
    if perm_error:
        return perm_error

    team = Team.query.get_or_404(team_id)
    data = request.get_json()

    if not data or not data.get('user_id'):
        return jsonify({
            'success': False,
            'message': 'user_id obbligatorio'
        }), HTTPStatus.BAD_REQUEST

    user = User.query.get_or_404(data['user_id'])

    # Check if already member
    if user in team.members:
        return jsonify({
            'success': False,
            'message': 'L\'utente è già membro del team'
        }), HTTPStatus.BAD_REQUEST

    try:
        team.members.append(user)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Membro aggiunto con successo',
            **_serialize_team(team, include_members=True)
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding team member: {e}")
        return jsonify({
            'success': False,
            'message': f'Errore: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@team_api_bp.route("/teams/<int:team_id>/members/<int:user_id>", methods=["DELETE"])
@login_required
def remove_team_member(team_id, user_id):
    """Remove member from team."""
    # Check admin permission
    perm_error = _require_admin()
    if perm_error:
        return perm_error

    team = Team.query.get_or_404(team_id)
    user = User.query.get_or_404(user_id)

    # Check if actually member
    if user not in team.members:
        return jsonify({
            'success': False,
            'message': 'L\'utente non è membro del team'
        }), HTTPStatus.BAD_REQUEST

    try:
        team.members.remove(user)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Membro rimosso con successo',
            **_serialize_team(team, include_members=True)
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error removing team member: {e}")
        return jsonify({
            'success': False,
            'message': f'Errore: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@team_api_bp.route("/available-leaders/<team_type>", methods=["GET"])
@login_required
def get_available_leaders(team_type):
    """
    Get available team leaders for a specific team type.

    Team leaders must have:
    - role = team_leader
    - specialty compatible with team_type
    """
    team_type = (team_type or "").strip().lower()
    if team_type not in [e.value for e in TeamTypeEnum]:
        return jsonify({
            'success': False,
            'message': 'Tipo team non valido'
        }), HTTPStatus.BAD_REQUEST

    if team_type == "health_manager":
        hm_team_heads = db.session.query(Team.head_id).filter(
            Team.team_type == TeamTypeEnum.health_manager,
            Team.head_id.isnot(None),
        )
        leaders = User.query.filter(
            User.is_active == True,
            User.role == UserRoleEnum.team_leader,
            User.id.in_(hm_team_heads),
        ).order_by(User.first_name, User.last_name).all()
        return jsonify({
            'success': True,
            'leaders': [_serialize_user(u) for u in leaders],
            'total': len(leaders)
        })

    # Get compatible specialties
    compatible_specialties = TEAM_TYPE_LEADER_SPECIALTIES.get(team_type, [])

    # Query users with team_leader role and compatible specialty
    query = User.query.filter(
        User.is_active == True,
        User.role == UserRoleEnum.team_leader,
        User.specialty.in_(compatible_specialties)
    ).order_by(User.first_name, User.last_name)

    leaders = query.all()

    return jsonify({
        'success': True,
        'leaders': [_serialize_user(u) for u in leaders],
        'total': len(leaders)
    })


@team_api_bp.route("/available-professionals/<team_type>", methods=["GET"])
@login_required
def get_available_professionals(team_type):
    """
    Get available professionals for a specific team type.

    For nutrizione/coach/psicologia: role = professionista and compatible specialty.
    For medico: role = professionista and specialty = medico.
    For health_manager: role = health_manager (or department_id = 13 if present).
    """
    team_type = (team_type or "").strip().lower()
    team_type_aliases = {
        "health-manager": "health_manager",
        "healthmanager": "health_manager",
    }
    team_type = team_type_aliases.get(team_type, team_type)
    requesting_role = _get_user_role(current_user)
    tl_visible_member_ids = None
    if requesting_role == "team_leader" and not _can_view_all_team_module_data(current_user):
        tl_visible_member_ids = _get_team_leader_member_ids(current_user.id) | {current_user.id}

    # Health Manager: return users with role health_manager
    if team_type == "health_manager":
        query = User.query.filter(
            User.is_active == True,
            cast(User.role, String) == "health_manager",
        )
        if tl_visible_member_ids is not None:
            query = query.filter(User.id.in_(tl_visible_member_ids))
        professionals = query.order_by(User.first_name, User.last_name).all()
        return jsonify({
            'success': True,
            'professionals': [_serialize_user(u) for u in professionals],
            'total': len(professionals)
        })

    if team_type == "medico":
        query = User.query.filter(
            User.is_active == True,
            User.role == UserRoleEnum.professionista,
            cast(User.specialty, String) == "medico",
        )
        if tl_visible_member_ids is not None:
            query = query.filter(User.id.in_(tl_visible_member_ids))
        professionals = query.order_by(User.first_name, User.last_name).all()
        return jsonify({
            'success': True,
            'professionals': [_serialize_user(u) for u in professionals],
            'total': len(professionals)
        })

    if team_type not in [e.value for e in TeamTypeEnum]:
        return jsonify({
            'success': False,
            'message': 'Tipo team non valido'
        }), HTTPStatus.BAD_REQUEST

    # Get compatible specialties
    compatible_specialties = TEAM_TYPE_PROFESSIONAL_SPECIALTIES.get(team_type, [])

    # Query users with professionista role and compatible specialty
    query = User.query.filter(
        User.is_active == True,
        User.role == UserRoleEnum.professionista,
        User.specialty.in_(compatible_specialties)
    ).order_by(User.first_name, User.last_name)
    if tl_visible_member_ids is not None:
        query = query.filter(User.id.in_(tl_visible_member_ids))

    professionals = query.all()

    return jsonify({
        'success': True,
        'professionals': [_serialize_user(u) for u in professionals],
        'total': len(professionals)
    })


# =============================================================================
# Professional Capacity Endpoints
# =============================================================================

@team_api_bp.route("/capacity", methods=["GET"])
@login_required
def get_professionals_capacity():
    """
    Tabella capienza professionisti.

    ACL visualizzazione:
    - admin/CCO: tutti i professionisti
    - team_leader: solo i propri membri
    - altri ruoli: nessun accesso
    """
    if not _can_view_professional_capacity(current_user):
        return jsonify({
            'success': False,
            'message': 'Non autorizzato a visualizzare la capienza professionisti'
        }), HTTPStatus.FORBIDDEN

    user_id_filter = request.args.get('user_id', type=int)

    clinical_specialties = [
        UserSpecialtyEnum.nutrizione,
        UserSpecialtyEnum.nutrizionista,
        UserSpecialtyEnum.coach,
        UserSpecialtyEnum.psicologia,
        UserSpecialtyEnum.psicologo,
        UserSpecialtyEnum.medico,
    ]

    query = User.query.filter(
        User.is_active == True,
        or_(
            and_(
                User.role == UserRoleEnum.professionista,
                User.specialty.in_(clinical_specialties),
            ),
            and_(
                User.role == UserRoleEnum.team_leader,
                User.specialty.in_(clinical_specialties),
            ),
            User.role == UserRoleEnum.health_manager,
        ),
    )

    # Team Leader: visibilità limitata ai membri dei team guidati + sé stesso.
    if not (current_user.is_admin or _is_cco_user(current_user)):
        current_role = _get_user_role(current_user)
        if current_role == 'team_leader':
            visible_member_ids = _get_team_leader_member_ids(current_user.id)
            visible_member_ids.add(current_user.id)  # TL vede anche sé stesso
            query = query.filter(User.id.in_(visible_member_ids))
            if not _is_health_manager_team_leader(current_user):
                query = query.filter(User.role.in_([UserRoleEnum.professionista, UserRoleEnum.team_leader]))
        elif current_role == 'health_manager':
            query = query.filter(User.id == current_user.id)

    if user_id_filter:
        query = query.filter(User.id == user_id_filter)

    professionals = query.order_by(User.first_name, User.last_name).all()
    if not professionals:
        return jsonify({
            'success': True,
            'rows': [],
            'total': 0,
            'can_edit': _can_edit_professional_capacity(current_user)
        })

    user_ids = [u.id for u in professionals]
    assigned_map = _get_assigned_clients_count_map_active_by_role(user_ids)
    type_breakdown_map = _get_assigned_clients_by_type(user_ids)
    weights_by_role = _get_capacity_weights_by_role()
    hm_ids = [u.id for u in professionals if _get_capacity_role_type(u) == 'health_manager']
    hm_split = _get_hm_split_counts(hm_ids) if hm_ids else {}

    capacities = ProfessionistCapacity.query.filter(
        ProfessionistCapacity.user_id.in_(user_ids)
    ).all()
    capacity_by_pair = {(c.user_id, c.role_type): c for c in capacities}

    rows = []
    changed = False

    for prof in professionals:
        role_type = _get_capacity_role_type(prof)
        if not role_type:
            continue

        capacity = capacity_by_pair.get((prof.id, role_type))
        if not capacity:
            capacity = ProfessionistCapacity(
                user_id=prof.id,
                role_type=role_type,
                max_clients=30,
                current_clients=0,
                is_available=True,
            )
            db.session.add(capacity)
            capacity_by_pair[(prof.id, role_type)] = capacity
            changed = True

        assigned_clients = assigned_map.get((prof.id, role_type), 0)
        if capacity.current_clients != assigned_clients:
            capacity.current_clients = assigned_clients
            changed = True

        contractual_capacity = capacity.max_clients or 0
        type_counts = type_breakdown_map.get((prof.id, role_type), {})
        metrics = _calculate_capacity_metrics(
            role_type=role_type,
            assigned_clients=assigned_clients,
            contractual_capacity=contractual_capacity,
            type_counts=type_counts,
            weights_by_role=weights_by_role,
        )

        row_data = {
            'user_id': prof.id,
            'full_name': prof.full_name,
            'first_name': prof.first_name,
            'last_name': prof.last_name,
            'avatar_path': prof.avatar_path,
            'specialty': _get_user_specialty(prof),
            'role_type': role_type,
            'teams': [
                {
                    'id': t.id,
                    'name': t.name,
                    'team_type': t.team_type.value if t.team_type else None,
                }
                for t in (prof.teams or [])
            ],
            'capienza_contrattuale': contractual_capacity,
            'clienti_assegnati': assigned_clients,
            'percentuale_capienza': metrics['percentuale_capienza'],
            'is_over_capacity': metrics['is_over_capacity'],
        }

        row_data['clienti_tipo_a'] = metrics['clienti_tipo_a']
        row_data['clienti_tipo_b'] = metrics['clienti_tipo_b']
        row_data['clienti_tipo_c'] = metrics['clienti_tipo_c']
        row_data['clienti_tipo_secondario'] = metrics['clienti_tipo_secondario']
        row_data['capienza_ponderata'] = metrics['capienza_ponderata']

        if role_type == 'health_manager':
            split = hm_split.get(prof.id, {})
            row_data['clienti_convertiti'] = split.get('clienti_convertiti', 0)
            row_data['lead_in_attesa'] = split.get('lead_in_attesa', 0)

        rows.append(row_data)

    if changed:
        db.session.commit()

    return jsonify({
        'success': True,
        'rows': rows,
        'total': len(rows),
        'can_edit': _can_edit_professional_capacity(current_user),
        'weights': weights_by_role,
    })


@team_api_bp.route("/capacity-weights", methods=["GET"])
@login_required
def get_capacity_weights():
    """Get capacity type weights (admin only)."""
    if not (current_user.is_admin or _is_cco_user(current_user)):
        return jsonify({'success': False, 'message': 'Non autorizzato'}), 403

    existing = {
        (
            row.role_type.value if hasattr(row.role_type, "value") else row.role_type,
            row.tipo,
        ): row
        for row in CapacityRoleTypeWeight.query.all()
    }
    changed = False
    for area, values in DEFAULT_CAPACITY_WEIGHTS.items():
        for tipo, peso in values.items():
            if (area, tipo) not in existing:
                db.session.add(CapacityRoleTypeWeight(role_type=area, tipo=tipo, peso=peso))
                changed = True
    if changed:
        db.session.commit()

    return jsonify({
        'success': True,
        'weights': _get_capacity_weights_by_role(),
    })


@team_api_bp.route("/capacity-weights", methods=["PUT"])
@login_required
def update_capacity_weights():
    """Update capacity type weights (admin only)."""
    if not (current_user.is_admin or _is_cco_user(current_user)):
        return jsonify({'success': False, 'message': 'Non autorizzato'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Dati mancanti'}), 400

    for area in DEFAULT_CAPACITY_WEIGHTS:
        area_data = data.get(area)
        if not isinstance(area_data, dict):
            continue
        for tipo in CAPACITY_SUPPORT_TYPES:
            if tipo not in area_data:
                continue
            peso = float(area_data[tipo])
            weight = CapacityRoleTypeWeight.query.filter_by(role_type=area, tipo=tipo).first()
            if weight:
                weight.peso = peso
            else:
                db.session.add(CapacityRoleTypeWeight(role_type=area, tipo=tipo, peso=peso))

    db.session.commit()
    return jsonify({
        'success': True,
        'weights': _get_capacity_weights_by_role(),
    })


@team_api_bp.route("/capacity/<int:user_id>", methods=["PUT"])
@login_required
def update_professional_capacity(user_id: int):
    """Aggiorna capienza contrattuale (admin/CCO/Team Leader)."""
    if not _can_edit_professional_capacity(current_user):
        return jsonify({
            'success': False,
            'message': 'Non autorizzato a modificare la capienza contrattuale'
        }), HTTPStatus.FORBIDDEN

    # Team Leader: può modificare solo membri dei propri team o sé stesso
    if not (current_user.is_admin or _is_cco_user(current_user)):
        if _get_user_role(current_user) == 'team_leader':
            allowed_ids = _get_team_leader_member_ids(current_user.id) | {current_user.id}
            if user_id not in allowed_ids:
                return jsonify({
                    'success': False,
                    'message': 'Puoi modificare solo la capienza dei membri del tuo team'
                }), HTTPStatus.FORBIDDEN

    user = User.query.get_or_404(user_id)
    role_type = _get_capacity_role_type(user)
    if not role_type or _get_user_role(user) not in {'professionista', 'health_manager', 'team_leader'}:
        return jsonify({
            'success': False,
            'message': 'Utente non gestibile nella tabella capienza professionisti'
        }), HTTPStatus.BAD_REQUEST

    data = request.get_json() or {}
    max_clients = data.get('capienza_contrattuale', data.get('max_clients'))
    if max_clients is None:
        return jsonify({
            'success': False,
            'message': 'Campo capienza_contrattuale obbligatorio'
        }), HTTPStatus.BAD_REQUEST

    try:
        max_clients = int(max_clients)
    except (TypeError, ValueError):
        return jsonify({
            'success': False,
            'message': 'capienza_contrattuale deve essere un numero intero'
        }), HTTPStatus.BAD_REQUEST

    if max_clients < 0:
        return jsonify({
            'success': False,
            'message': 'capienza_contrattuale non può essere negativa'
        }), HTTPStatus.BAD_REQUEST

    capacity = ProfessionistCapacity.query.filter_by(
        user_id=user.id,
        role_type=role_type
    ).first()

    if not capacity:
        capacity = ProfessionistCapacity(
            user_id=user.id,
            role_type=role_type,
            max_clients=max_clients,
            current_clients=0,
            is_available=True,
        )
        db.session.add(capacity)
    else:
        capacity.max_clients = max_clients

    assigned_map = _get_assigned_clients_count_map_active_by_role([user.id])
    assigned_clients = assigned_map.get((user.id, role_type), 0)
    capacity.current_clients = assigned_clients

    db.session.commit()

    type_counts = _get_assigned_clients_by_type([user.id]).get((user.id, role_type), {})
    metrics = _calculate_capacity_metrics(
        role_type=role_type,
        assigned_clients=assigned_clients,
        contractual_capacity=max_clients,
        type_counts=type_counts,
        weights_by_role=_get_capacity_weights_by_role(),
    )
    return jsonify({
        'success': True,
        'message': 'Capienza contrattuale aggiornata',
        'row': {
            'user_id': user.id,
            'full_name': user.full_name,
            'specialty': _get_user_specialty(user),
            'role_type': role_type,
            'teams': [
                {
                    'id': t.id,
                    'name': t.name,
                    'team_type': t.team_type.value if t.team_type else None,
                }
                for t in (user.teams or [])
            ],
            'capienza_contrattuale': max_clients,
            'clienti_assegnati': assigned_clients,
            'clienti_tipo_a': metrics['clienti_tipo_a'],
            'clienti_tipo_b': metrics['clienti_tipo_b'],
            'clienti_tipo_c': metrics['clienti_tipo_c'],
            'clienti_tipo_secondario': metrics['clienti_tipo_secondario'],
            'capienza_ponderata': metrics['capienza_ponderata'],
            'percentuale_capienza': metrics['percentuale_capienza'],
            'is_over_capacity': metrics['is_over_capacity'],
        }
    })


# =============================================================================
# =============================================================================
# Professional's Clients Endpoint
# =============================================================================

@team_api_bp.route("/members/<int:user_id>/clients", methods=["GET"])
@login_required
def get_member_clients(user_id):
    """
    Get paginated list of clients associated with a professional.

    Query params:
        - page: Page number (default 1)
        - per_page: Items per page (default 5, max 50)
        - q: Search query (searches client name)
        - stato: Filter by stato_cliente

    Returns clients where the professional is assigned via:
    - Single FK (nutrizionista_id, coach_id, psicologa_id)
    - Many-to-many relationships (nutrizionisti_multipli, coaches_multipli, psicologi_multipli)
    """
    from corposostenibile.models import Cliente, cliente_nutrizionisti, cliente_coaches, cliente_psicologi, cliente_consulenti
    from sqlalchemy import select, exists

    if not _can_access_member_scoped_data(current_user, user_id):
        return jsonify({
            'success': False,
            'message': 'Non autorizzato a visualizzare i clienti di questo professionista'
        }), HTTPStatus.FORBIDDEN

    user = User.query.get_or_404(user_id)

    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 5, type=int), 50)
    search_query = request.args.get('q', '').strip()
    stato_filter = request.args.get('stato', '').strip()

    # Build exists clauses for many-to-many relationships
    nutri_exists = exists(
        select(cliente_nutrizionisti.c.cliente_id).where(
            cliente_nutrizionisti.c.cliente_id == Cliente.cliente_id,
            cliente_nutrizionisti.c.user_id == user_id
        )
    )

    coach_exists = exists(
        select(cliente_coaches.c.cliente_id).where(
            cliente_coaches.c.cliente_id == Cliente.cliente_id,
            cliente_coaches.c.user_id == user_id
        )
    )

    psico_exists = exists(
        select(cliente_psicologi.c.cliente_id).where(
            cliente_psicologi.c.cliente_id == Cliente.cliente_id,
            cliente_psicologi.c.user_id == user_id
        )
    )

    consulente_exists = exists(
        select(cliente_consulenti.c.cliente_id).where(
            cliente_consulenti.c.cliente_id == Cliente.cliente_id,
            cliente_consulenti.c.user_id == user_id
        )
    )

    # Base query: find clients where this user is assigned
    # Relationships already have lazy="selectin" in the model, so no need for explicit loading
    query = Cliente.query.filter(
        or_(
            # Single FK relationships
            Cliente.nutrizionista_id == user_id,
            Cliente.coach_id == user_id,
            Cliente.psicologa_id == user_id,
            Cliente.consulente_alimentare_id == user_id,
            Cliente.health_manager_id == user_id,
            # Many-to-many relationships
            nutri_exists,
            coach_exists,
            psico_exists,
            consulente_exists,
        )
    )

    # Search filter
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(Cliente.nome_cognome.ilike(search_term))

    # Stato filter
    if stato_filter:
        query = query.filter(Cliente.stato_cliente == stato_filter)

    # Eager load HM for HM column in team profile clients table
    query = query.options(selectinload(Cliente.health_manager_user))

    # Order by nome_cognome
    query = query.order_by(Cliente.nome_cognome)

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Serialize clients - include all fields needed for table display
    def serialize_client(c):
        # Check roles
        is_nutri = c.nutrizionista_id == user_id
        is_coach = c.coach_id == user_id
        is_psico = c.psicologa_id == user_id

        # Also check many-to-many (already loaded via selectin)
        if not is_nutri and c.nutrizionisti_multipli:
            is_nutri = any(u.id == user_id for u in c.nutrizionisti_multipli)
        if not is_coach and c.coaches_multipli:
            is_coach = any(u.id == user_id for u in c.coaches_multipli)
        if not is_psico and c.psicologi_multipli:
            is_psico = any(u.id == user_id for u in c.psicologi_multipli)

        # Serialize team member helper
        def serialize_team_member(u):
            if not u:
                return None
            return {
                'id': u.id,
                'first_name': u.first_name or '',
                'last_name': u.last_name or '',
                'full_name': f"{u.first_name or ''} {u.last_name or ''}".strip(),
                'avatar_path': u.avatar_path,
            }

        # Build result
        result = {
            'id': c.cliente_id,
            'cliente_id': c.cliente_id,
            'nome_cognome': c.nome_cognome or '-',
            'full_name': c.nome_cognome or '-',
            'email': c.mail,
            'telefono': c.numero_telefono,
            'stato_cliente': c.stato_cliente.value if c.stato_cliente else None,
            'tipologia_cliente': c.tipologia_cliente.value if c.tipologia_cliente else None,
            'data_inizio_abbonamento': c.data_inizio_abbonamento.isoformat() if c.data_inizio_abbonamento else None,
            'data_rinnovo': c.data_rinnovo.isoformat() if c.data_rinnovo else None,
            'programma_attuale': c.programma_attuale,
            'storico_programma': c.storico_programma,
            'is_nutrizionista': is_nutri,
            'is_coach': is_coach,
            'is_psicologo': is_psico,
            # Team members
            'health_manager_user': serialize_team_member(c.health_manager_user) if c.health_manager_user else None,
            'nutrizionisti_multipli': [serialize_team_member(u) for u in (c.nutrizionisti_multipli or [])],
            'coaches_multipli': [serialize_team_member(u) for u in (c.coaches_multipli or [])],
            'psicologi_multipli': [serialize_team_member(u) for u in (c.psicologi_multipli or [])],
            'consulenti_multipli': [serialize_team_member(u) for u in (c.consulenti_multipli or [])],
        }
        return result

    clients = [serialize_client(c) for c in pagination.items]

    return jsonify({
        'success': True,
        'clients': clients,
        'total': pagination.total,
        'page': pagination.page,
        'per_page': pagination.per_page,
        'total_pages': pagination.pages,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev,
    })


# =============================================================================
# Professional's Client Checks Endpoint
# =============================================================================

@team_api_bp.route("/members/<int:user_id>/checks", methods=["GET"])
@login_required
def get_member_client_checks(user_id):
    """
    Get check responses for clients associated with a professional.

    Query params:
        - period: 'week', 'month', 'trimester', 'year', or 'custom' (default 'month')
        - start_date: Start date for custom period (YYYY-MM-DD)
        - end_date: End date for custom period (YYYY-MM-DD)
        - check_type: 'all', 'weekly', 'dca' (default 'all')
        - q: Search query on client name
        - page: Page number (default 1)
        - per_page: Items per page (default 25, max 50)

    Returns check responses from clients where the professional is assigned.
    """
    from corposostenibile.models import (
        Cliente, WeeklyCheck, WeeklyCheckResponse, DCACheck, DCACheckResponse,
        cliente_nutrizionisti, cliente_coaches, cliente_psicologi, cliente_consulenti,
        ClientCheckReadConfirmation
    )
    from sqlalchemy import select, exists
    from datetime import datetime, timedelta, time

    if not _can_access_member_scoped_data(current_user, user_id):
        return jsonify({
            'success': False,
            'message': 'Non autorizzato a visualizzare i check di questo professionista'
        }), HTTPStatus.FORBIDDEN

    user = User.query.get_or_404(user_id)

    # Parse parameters
    period = request.args.get('period', 'month').strip()
    start_date_str = request.args.get('start_date', '').strip()
    end_date_str = request.args.get('end_date', '').strip()
    check_type = request.args.get('check_type', 'all').strip().lower()
    search_query = request.args.get('q', '').strip().lower()
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 25, type=int), 50)

    # Calculate date range
    today = datetime.now().date()
    if period == 'week':
        start_date = today - timedelta(days=7)
        end_date = today
    elif period == 'month':
        start_date = today - timedelta(days=30)
        end_date = today
    elif period == 'trimester':
        start_date = today - timedelta(days=90)
        end_date = today
    elif period == 'year':
        start_date = today - timedelta(days=365)
        end_date = today
    elif period == 'custom' and start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = today - timedelta(days=30)
            end_date = today
    else:
        start_date = today - timedelta(days=30)
        end_date = today

    # submit_date in DB is DateTime: compare with datetime bounds to avoid adapter issues
    start_dt = datetime.combine(start_date, time.min)
    end_dt = datetime.combine(end_date, time.max)

    # Build exists clauses for many-to-many relationships
    nutri_exists = exists(
        select(cliente_nutrizionisti.c.cliente_id).where(
            cliente_nutrizionisti.c.cliente_id == Cliente.cliente_id,
            cliente_nutrizionisti.c.user_id == user_id
        )
    )

    coach_exists = exists(
        select(cliente_coaches.c.cliente_id).where(
            cliente_coaches.c.cliente_id == Cliente.cliente_id,
            cliente_coaches.c.user_id == user_id
        )
    )

    psico_exists = exists(
        select(cliente_psicologi.c.cliente_id).where(
            cliente_psicologi.c.cliente_id == Cliente.cliente_id,
            cliente_psicologi.c.user_id == user_id
        )
    )

    consulente_exists = exists(
        select(cliente_consulenti.c.cliente_id).where(
            cliente_consulenti.c.cliente_id == Cliente.cliente_id,
            cliente_consulenti.c.user_id == user_id
        )
    )

    # Get all client IDs for this professional
    client_ids_query = Cliente.query.filter(
        or_(
            Cliente.nutrizionista_id == user_id,
            Cliente.coach_id == user_id,
            Cliente.psicologa_id == user_id,
            Cliente.consulente_alimentare_id == user_id,
            Cliente.health_manager_id == user_id,
            nutri_exists,
            coach_exists,
            psico_exists,
            consulente_exists,
        )
    ).with_entities(Cliente.cliente_id)

    client_ids = [c.cliente_id for c in client_ids_query.all()]

    if not client_ids:
        return jsonify({
            'success': True,
            'responses': [],
            'stats': {
                'avg_nutrizionista': None,
                'avg_psicologo': None,
                'avg_coach': None,
                'avg_progresso': None,
                'avg_quality': None,
            },
            'total': 0,
            'page': page,
            'per_page': per_page,
            'total_pages': 0,
        })

    # Get weekly check responses - join through WeeklyCheck to filter by cliente_id
    weekly_responses = WeeklyCheckResponse.query.join(
        WeeklyCheck, WeeklyCheckResponse.weekly_check_id == WeeklyCheck.id
    ).filter(
        WeeklyCheck.cliente_id.in_(client_ids),
        WeeklyCheckResponse.submit_date >= start_dt,
        WeeklyCheckResponse.submit_date <= end_dt
    ).all()

    # Get DCA check responses - join through DCACheck to filter by cliente_id
    dca_responses = DCACheckResponse.query.join(
        DCACheck, DCACheckResponse.dca_check_id == DCACheck.id
    ).filter(
        DCACheck.cliente_id.in_(client_ids),
        DCACheckResponse.submit_date >= start_dt,
        DCACheckResponse.submit_date <= end_dt
    ).all()

    # Helper to get read status for a response
    def get_read_statuses(response, response_type):
        """Get read status for professionals assigned to the client."""
        # Get cliente through assignment relationship
        cliente = response.assignment.cliente if response.assignment else None
        professionals = {
            'nutrizionisti': [],
            'psicologi': [],
            'coaches': [],
        }

        if not cliente:
            return professionals

        # Map response_type to the value stored in ClientCheckReadConfirmation
        db_response_type = 'weekly_check' if response_type == 'weekly' else 'dca_check'

        # Get nutrizionisti
        nutris = list(cliente.nutrizionisti_multipli or [])
        if cliente.nutrizionista_id:
            nutri_user = User.query.get(cliente.nutrizionista_id)
            if nutri_user and nutri_user not in nutris:
                nutris.append(nutri_user)

        for u in nutris:
            # Check read status using ClientCheckReadConfirmation
            read_status = ClientCheckReadConfirmation.query.filter_by(
                response_type=db_response_type,
                response_id=response.id,
                user_id=u.id
            ).first()

            professionals['nutrizionisti'].append({
                'id': u.id,
                'nome': getattr(u, 'full_name', None) or (f'{getattr(u, "first_name", "")} {getattr(u, "last_name", "")}'.strip()) or str(u.id),
                'avatar_path': getattr(u, 'avatar_path', None),
                'has_read': read_status is not None,
            })

        # Get psicologi
        psicos = list(cliente.psicologi_multipli or [])
        if cliente.psicologa_id:
            psico_user = User.query.get(cliente.psicologa_id)
            if psico_user and psico_user not in psicos:
                psicos.append(psico_user)

        for u in psicos:
            read_status = ClientCheckReadConfirmation.query.filter_by(
                response_type=db_response_type,
                response_id=response.id,
                user_id=u.id
            ).first()

            professionals['psicologi'].append({
                'id': u.id,
                'nome': getattr(u, 'full_name', None) or (f'{getattr(u, "first_name", "")} {getattr(u, "last_name", "")}'.strip()) or str(u.id),
                'avatar_path': getattr(u, 'avatar_path', None),
                'has_read': read_status is not None,
            })

        # Get coaches
        coaches = list(cliente.coaches_multipli or [])
        if cliente.coach_id:
            coach_user = User.query.get(cliente.coach_id)
            if coach_user and coach_user not in coaches:
                coaches.append(coach_user)

        for u in coaches:
            read_status = ClientCheckReadConfirmation.query.filter_by(
                response_type=db_response_type,
                response_id=response.id,
                user_id=u.id
            ).first()

            professionals['coaches'].append({
                'id': u.id,
                'nome': getattr(u, 'full_name', None) or (f'{getattr(u, "first_name", "")} {getattr(u, "last_name", "")}'.strip()) or str(u.id),
                'avatar_path': getattr(u, 'avatar_path', None),
                'has_read': read_status is not None,
            })

        return professionals

    # Serialize responses
    all_responses = []

    for r in weekly_responses:
        # Get cliente through assignment
        cliente = r.assignment.cliente if r.assignment else None
        profs = get_read_statuses(r, 'weekly')
        all_responses.append({
            'id': r.id,
            'type': 'weekly',
            'cliente_id': cliente.cliente_id if cliente else None,
            'cliente_nome': cliente.nome_cognome if cliente else 'N/D',
            'submit_date': r.submit_date.strftime('%d/%m/%Y') if r.submit_date else None,
            'submit_date_iso': r.submit_date.isoformat() if r.submit_date else None,
            'nutritionist_rating': r.nutritionist_rating,
            'psychologist_rating': r.psychologist_rating,
            'coach_rating': r.coach_rating,
            'progress_rating': r.progress_rating,
            'nutrizionisti': profs['nutrizionisti'],
            'psicologi': profs['psicologi'],
            'coaches': profs['coaches'],
        })

    for r in dca_responses:
        # Get cliente through assignment
        cliente = r.assignment.cliente if r.assignment else None
        profs = get_read_statuses(r, 'dca')
        all_responses.append({
            'id': r.id,
            'type': 'dca',
            'cliente_id': cliente.cliente_id if cliente else None,
            'cliente_nome': cliente.nome_cognome if cliente else 'N/D',
            'submit_date': r.submit_date.strftime('%d/%m/%Y') if r.submit_date else None,
            'submit_date_iso': r.submit_date.isoformat() if r.submit_date else None,
            'nutritionist_rating': r.nutritionist_rating,
            'psychologist_rating': r.psychologist_rating,
            'coach_rating': r.coach_rating,
            'progress_rating': r.progress_rating,
            'nutrizionisti': profs['nutrizionisti'],
            'psicologi': profs['psicologi'],
            'coaches': profs['coaches'],
        })

    # Filter by type
    if check_type in {'weekly', 'dca'}:
        all_responses = [r for r in all_responses if r.get('type') == check_type]

    # Search by client name
    if search_query:
        all_responses = [
            r for r in all_responses
            if search_query in (r.get('cliente_nome') or '').lower()
        ]

    # Sort by submit date descending using ISO date for correctness
    all_responses.sort(key=lambda x: x.get('submit_date_iso') or '', reverse=True)

    # Calculate stats
    nutri_ratings = [r['nutritionist_rating'] for r in all_responses if r['nutritionist_rating'] is not None]
    psico_ratings = [r['psychologist_rating'] for r in all_responses if r['psychologist_rating'] is not None]
    coach_ratings = [r['coach_rating'] for r in all_responses if r['coach_rating'] is not None]
    progress_ratings = [r['progress_rating'] for r in all_responses if r['progress_rating'] is not None]

    all_ratings = nutri_ratings + psico_ratings + coach_ratings + progress_ratings

    stats = {
        'avg_nutrizionista': round(sum(nutri_ratings) / len(nutri_ratings), 1) if nutri_ratings else None,
        'avg_psicologo': round(sum(psico_ratings) / len(psico_ratings), 1) if psico_ratings else None,
        'avg_coach': round(sum(coach_ratings) / len(coach_ratings), 1) if coach_ratings else None,
        'avg_progresso': round(sum(progress_ratings) / len(progress_ratings), 1) if progress_ratings else None,
        'avg_quality': round(sum(all_ratings) / len(all_ratings), 1) if all_ratings else None,
    }

    # Paginate
    total = len(all_responses)
    total_pages = (total + per_page - 1) // per_page if total > 0 else 0
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_responses = all_responses[start_idx:end_idx]

    # Clean internal sort field before returning
    for response in paginated_responses:
        response.pop('submit_date_iso', None)

    return jsonify({
        'success': True,
        'responses': paginated_responses,
        'stats': stats,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages,
        'has_next': page < total_pages,
        'has_prev': page > 1,
    })
