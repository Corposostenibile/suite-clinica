"""Routes per il blueprint sales_ghl_assignments.

Espone la vista lista delle SalesLead provenienti da GHL sotto
`/api/ghl-assignments`.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime

from flask import abort, current_app, g, jsonify, request
from sqlalchemy import func, or_

from corposostenibile.extensions import db
from corposostenibile.models import LeadStatusEnum, SalesLead, User, UserSpecialtyEnum

from corposostenibile.blueprints.team.ai_matching_service import AIMatchingService
from corposostenibile.blueprints.sales_form.services import ConversionService

from . import bp
from .services import serialize_sales_lead
from .sso import (
    build_sales_session_user,
    create_sales_jwt,
    get_active_sales_user,
    resolve_sales_user_by_email,
    sales_assignments_auth_required,
)


@bp.route("/sso/exchange", methods=["POST"])
def sso_exchange():
    """Scambia l'email del sales con un JWT firmato dal backend.

    Payload atteso:
    - user_email / email
    - user_name / name (opzionale)
    """
    payload = request.get_json(silent=True) or {}
    email = (
        payload.get("user_email")
        or payload.get("email")
        or payload.get("sales_user_email")
        or ""
    ).strip()

    if not email:
        abort(422, description="user_email richiesto")

    sales_user = resolve_sales_user_by_email(email)
    if not sales_user:
        abort(401, description="Utente sales non trovato")

    token = create_sales_jwt(sales_user)
    session_user = build_sales_session_user(sales_user)

    return jsonify(
        {
            "success": True,
            "scope": "sales",
            "token": token,
            "sales_user": session_user.to_dict(),
        }
    )


def _lead_query_with_scope():
    query = SalesLead.query.filter(
        SalesLead.source_system == "ghl",
        SalesLead.archived_at.is_(None),
    )

    # Scoping: via JWT sales si vede solo la propria coda.
    active_user = get_active_sales_user()
    if getattr(g, "sales_auth_mode", None) == "jwt" and active_user:
        query = query.filter(SalesLead.sales_user_id == active_user.id)

    return query


def _ensure_lead_scope(lead: SalesLead):
    active_user = get_active_sales_user()
    if getattr(g, "sales_auth_mode", None) == "jwt" and active_user and lead.sales_user_id and lead.sales_user_id != active_user.id:
        abort(403, description="Lead non disponibile per questo sales")


def _serialize_professional(user: User) -> dict:
    specialty = getattr(user, "specialty", None)
    specialty_value = specialty.value if hasattr(specialty, "value") else specialty
    role = getattr(user, "role", None)
    role_value = role.value if hasattr(role, "value") else role
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "specialty": specialty_value,
        "role": role_value,
        "is_active": bool(user.is_active),
    }


@bp.route("", methods=["GET"], strict_slashes=False)
@bp.route("/", methods=["GET"], strict_slashes=False)
@sales_assignments_auth_required()
def api_assignments():
    """Lista le SalesLead GHL.

    Query params supportati:
    - `status`: filtro stato (`all` per tutti)
    - `q`: ricerca su nome/email/telefono/unique_code
    - `limit`: massimo record restituiti (default 100, max 300)
    """
    status = (request.args.get("status") or "all").strip()
    search = (request.args.get("q") or request.args.get("search") or "").strip()
    limit = request.args.get("limit", type=int) or 100
    limit = max(1, min(limit, 300))

    query = _lead_query_with_scope()

    if status.lower() != "all":
        query = query.filter(SalesLead.status == status.upper())

    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                SalesLead.first_name.ilike(like),
                SalesLead.last_name.ilike(like),
                SalesLead.email.ilike(like),
                SalesLead.phone.ilike(like),
                SalesLead.unique_code.ilike(like),
            )
        )

    leads = query.order_by(SalesLead.created_at.desc()).limit(limit).all()
    active_user = get_active_sales_user()

    return jsonify(
        {
            "assignments": [serialize_sales_lead(lead) for lead in leads],
            "total": len(leads),
            "status": status,
            "search": search,
            "limit": limit,
            "current_user_id": active_user.id if active_user else None,
            "auth_mode": getattr(g, "sales_auth_mode", None),
        }
    )


@bp.route("/professionals/<string:team_type>", methods=["GET"])
@sales_assignments_auth_required()
def api_available_professionals(team_type: str):
    """Ritorna i professionisti attivi per team/specialty."""
    normalized = (team_type or "").strip().lower()
    aliases = {
        "nutrizione": [UserSpecialtyEnum.nutrizione, UserSpecialtyEnum.nutrizionista],
        "coach": [UserSpecialtyEnum.coach],
        "psicologia": [UserSpecialtyEnum.psicologia, UserSpecialtyEnum.psicologo],
    }
    specialties = aliases.get(normalized, [])

    query = User.query.filter(User.is_active == True)  # noqa: E712
    if specialties:
        query = query.filter(User.specialty.in_(specialties))

    professionals = query.order_by(User.first_name, User.last_name).all()
    return jsonify(
        {
            "success": True,
            "professionals": [_serialize_professional(user) for user in professionals],
            "total": len(professionals),
            "team_type": normalized,
        }
    )


@bp.route("/<int:lead_id>", methods=["GET"])
@sales_assignments_auth_required()
def api_lead_detail(lead_id: int):
    lead = _lead_query_with_scope().filter(SalesLead.id == lead_id).first_or_404()
    return jsonify({"success": True, "lead": serialize_sales_lead(lead)})


@bp.route("/<int:lead_id>/story", methods=["PATCH"])
@sales_assignments_auth_required()
def api_update_story(lead_id: int):
    lead = _lead_query_with_scope().filter(SalesLead.id == lead_id).first_or_404()
    _ensure_lead_scope(lead)

    payload = request.get_json(silent=True) or {}
    story = (payload.get("client_story") or payload.get("story") or "").strip()
    lead.client_story = story
    lead.ai_analysis_snapshot = lead.ai_analysis_snapshot or None
    db.session.commit()
    return jsonify({"success": True, "lead": serialize_sales_lead(lead)})


@bp.route("/<int:lead_id>/analyze-lead", methods=["POST"])
@sales_assignments_auth_required()
def api_analyze_lead(lead_id: int):
    lead = _lead_query_with_scope().filter(SalesLead.id == lead_id).first_or_404()
    _ensure_lead_scope(lead)

    payload = request.get_json(silent=True) or {}
    story = (payload.get("story") or lead.client_story or "").strip()
    target_role = (payload.get("target_role") or "").strip() or None
    analysis = AIMatchingService.extract_lead_criteria(story, target_role=target_role)

    lead.ai_analysis = analysis
    lead.ai_analyzed_at = datetime.utcnow()
    lead.ai_analysis_snapshot = deepcopy(analysis)
    db.session.commit()

    return jsonify({"success": True, "analysis": analysis, "lead": serialize_sales_lead(lead)})


@bp.route("/<int:lead_id>/match", methods=["POST"])
@sales_assignments_auth_required()
def api_match_lead_professionals(lead_id: int):
    lead = _lead_query_with_scope().filter(SalesLead.id == lead_id).first_or_404()
    _ensure_lead_scope(lead)

    payload = request.get_json(silent=True) or {}
    criteria = payload.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        analysis = lead.ai_analysis or lead.ai_analysis_snapshot or {}
        criteria = analysis.get("criteria") if isinstance(analysis, dict) else []
    if not criteria:
        story = (payload.get("story") or lead.client_story or "").strip()
        analysis = AIMatchingService.extract_lead_criteria(story)
        criteria = analysis.get("criteria") if isinstance(analysis, dict) else []

    matches = AIMatchingService.match_professionals(criteria)
    return jsonify({"success": True, "matches": matches, "criteria": criteria})


@bp.route("/<int:lead_id>/confirm", methods=["POST"])
@sales_assignments_auth_required()
def api_confirm_assignment(lead_id: int):
    lead = _lead_query_with_scope().filter(SalesLead.id == lead_id).first_or_404()
    _ensure_lead_scope(lead)

    payload = request.get_json(silent=True) or {}
    nutritionist_id = payload.get("nutritionist_id")
    coach_id = payload.get("coach_id")
    psychologist_id = payload.get("psychologist_id")

    lead.assigned_nutritionist_id = int(nutritionist_id) if nutritionist_id else None
    lead.assigned_coach_id = int(coach_id) if coach_id else None
    lead.assigned_psychologist_id = int(psychologist_id) if psychologist_id else None
    lead.assigned_by = get_active_sales_user().id if get_active_sales_user() else lead.assigned_by
    lead.assigned_at = datetime.utcnow()
    lead.assignment_notes = payload.get("notes") or lead.assignment_notes
    lead.ai_analysis_snapshot = deepcopy(payload.get("ai_analysis") or lead.ai_analysis_snapshot or lead.ai_analysis or {})
    lead.status = LeadStatusEnum.ASSIGNED

    db.session.commit()

    try:
        ConversionService.convert_lead_to_client(
            lead.id,
            get_active_sales_user().id if get_active_sales_user() else lead.assigned_by or lead.sales_user_id,
            note_onboarding=payload.get("note_onboarding"),
            data_call_iniziale_nutrizionista=payload.get("data_call_iniziale_nutrizionista"),
            data_call_iniziale_coach=payload.get("data_call_iniziale_coach"),
            data_call_iniziale_psicologia=payload.get("data_call_iniziale_psicologia"),
        )
    except Exception as exc:  # noqa: BLE001
        current_app.logger.warning("[sales_ghl_assignments] conversione lead %s fallita: %s", lead.id, exc)

    db.session.refresh(lead)
    return jsonify({"success": True, "message": "Assegnazione salvata", "lead": serialize_sales_lead(lead)})
