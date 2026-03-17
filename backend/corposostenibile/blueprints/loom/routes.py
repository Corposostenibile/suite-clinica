from __future__ import annotations

from types import SimpleNamespace

from flask import current_app, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import or_

from corposostenibile.extensions import csrf, db
from corposostenibile.models import Cliente, LoomRecording, Team, UserRoleEnum, team_members

from . import loom_bp


@loom_bp.get("/health")
def health():
    return jsonify({"success": True, "service": "loom", "status": "ok"})


@loom_bp.route("/api/recordings", methods=["POST"])
@csrf.exempt
@login_required
def create_recording():
    """Crea una registrazione Loom del widget supporto."""
    try:
        data = request.get_json() or {}

        loom_link = (data.get("loom_link") or "").strip()
        if not loom_link:
            return jsonify({"success": False, "message": "loom_link richiesto"}), 400

        if "loom.com" not in loom_link:
            return jsonify({"success": False, "message": "URL Loom non valido"}), 400

        cliente_id = data.get("cliente_id")
        cliente = None
        if cliente_id:
            cliente = Cliente.query.filter_by(cliente_id=cliente_id).first()
            if not cliente:
                return jsonify({"success": False, "message": "Cliente non trovato"}), 404
            if not _can_access_cliente(current_user, cliente):
                return jsonify({"success": False, "message": "Non autorizzato per questo cliente"}), 403

        recording = LoomRecording(
            loom_link=loom_link,
            title=(data.get("title") or "").strip() or None,
            note=(data.get("note") or "").strip() or None,
            source="support_widget",
            submitter_user_id=current_user.id,
            cliente_id=cliente.cliente_id if cliente else None,
        )
        db.session.add(recording)
        db.session.commit()

        return jsonify({"success": True, "recording": _serialize_recording(recording)}), 201
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error(f"[Loom] Error creating recording: {exc}")
        return jsonify({"success": False, "message": str(exc)}), 500


@loom_bp.route("/api/recordings", methods=["GET"])
@login_required
def list_recordings():
    """Libreria Loom con scope dipendente da ruolo/team."""
    query = _recordings_scope_query(current_user)

    cliente_id = request.args.get("cliente_id", type=int)
    if cliente_id:
        query = query.filter(LoomRecording.cliente_id == cliente_id)

    only_with_cliente = request.args.get("with_cliente")
    if only_with_cliente == "true":
        query = query.filter(LoomRecording.cliente_id.isnot(None))
    elif only_with_cliente == "false":
        query = query.filter(LoomRecording.cliente_id.is_(None))

    submitter_user_id = request.args.get("submitter_user_id", type=int)
    if submitter_user_id:
        if _can_view_submitter_id(current_user, submitter_user_id):
            query = query.filter(LoomRecording.submitter_user_id == submitter_user_id)
        else:
            return jsonify({"success": False, "message": "Filtro submitter non autorizzato"}), 403

    results = query.order_by(LoomRecording.created_at.desc()).all()
    return jsonify(
        {
            "success": True,
            "count": len(results),
            "recordings": [_serialize_recording(recording) for recording in results],
        }
    )


@loom_bp.route("/api/recordings/<int:recording_id>", methods=["GET"])
@login_required
def get_recording(recording_id: int):
    recording = LoomRecording.query.get_or_404(recording_id)
    if not _can_view_recording(current_user, recording):
        return jsonify({"success": False, "message": "Non autorizzato"}), 403
    return jsonify({"success": True, "recording": _serialize_recording(recording)})


@loom_bp.route("/api/recordings/<int:recording_id>/association", methods=["PUT"])
@csrf.exempt
@login_required
def update_recording_association(recording_id: int):
    """Aggiorna o rimuove l'associazione paziente di una registrazione."""
    recording = LoomRecording.query.get_or_404(recording_id)
    if not _can_manage_recording(current_user, recording):
        return jsonify({"success": False, "message": "Non autorizzato"}), 403

    try:
        data = request.get_json() or {}
        cliente_id = data.get("cliente_id")

        if cliente_id in (None, "", 0):
            recording.cliente_id = None
        else:
            cliente = Cliente.query.filter_by(cliente_id=cliente_id).first()
            if not cliente:
                return jsonify({"success": False, "message": "Cliente non trovato"}), 404
            if not _can_access_cliente(current_user, cliente):
                return jsonify({"success": False, "message": "Non autorizzato per questo cliente"}), 403
            recording.cliente_id = cliente.cliente_id

        db.session.commit()
        return jsonify({"success": True, "recording": _serialize_recording(recording)})
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error(f"[Loom] Error updating association: {exc}")
        return jsonify({"success": False, "message": str(exc)}), 500


@loom_bp.route("/api/patients/search", methods=["GET"])
@login_required
def search_patients():
    """Ricerca pazienti per la select di associazione Loom."""
    query_text = (request.args.get("q") or "").strip()
    limit = min(max(request.args.get("limit", default=20, type=int), 1), 50)

    query = _clienti_scope_query(current_user)
    if query_text:
        query = query.filter(Cliente.nome_cognome.ilike(f"%{query_text}%"))

    rows = query.order_by(Cliente.nome_cognome.asc()).limit(limit).all()
    return jsonify(
        {
            "success": True,
            "items": [{"cliente_id": row.cliente_id, "nome_cognome": row.nome_cognome} for row in rows],
        }
    )


def _serialize_recording(recording: LoomRecording) -> dict:
    return {
        "id": recording.id,
        "loom_link": recording.loom_link,
        "title": recording.title,
        "note": recording.note,
        "source": recording.source,
        "submitter_user_id": recording.submitter_user_id,
        "submitter_user_name": recording.submitter_user.full_name if recording.submitter_user else None,
        "cliente_id": recording.cliente_id,
        "cliente_name": recording.cliente.nome_cognome if recording.cliente else None,
        "created_at": recording.created_at.isoformat() if recording.created_at else None,
    }


def _role_value(user) -> str:
    role = getattr(user, "role", None)
    return role.value if hasattr(role, "value") else str(role or "")


def _is_admin_user(user) -> bool:
    return bool(getattr(user, "is_admin", False) or _role_value(user) == UserRoleEnum.admin.value)


def _is_team_leader_user(user) -> bool:
    return _role_value(user) == UserRoleEnum.team_leader.value


def _is_health_manager_user(user) -> bool:
    return _role_value(user) == UserRoleEnum.health_manager.value


def _team_member_ids_for_leader(leader_id: int) -> set[int]:
    team_ids = db.session.query(Team.id).filter(Team.head_id == leader_id, Team.is_active == True)
    rows = (
        db.session.query(team_members.c.user_id)
        .filter(team_members.c.team_id.in_(team_ids))
        .distinct()
        .all()
    )
    return {int(row[0]) for row in rows}


def _allowed_submitter_ids(user) -> set[int] | None:
    if _is_admin_user(user):
        return None
    if _is_team_leader_user(user):
        ids = _team_member_ids_for_leader(user.id)
        ids.add(user.id)
        return ids
    return {user.id}


def _can_view_submitter_id(user, submitter_user_id: int) -> bool:
    return can_view_submitter_id_for_role(
        SimpleNamespace(id=user.id, is_admin=getattr(user, "is_admin", False), role=_role_value(user)),
        submitter_user_id,
        _allowed_submitter_ids(user),
    )


def _can_view_recording(user, recording: LoomRecording) -> bool:
    if _is_health_manager_user(user):
        return bool(recording.cliente_id and recording.cliente and recording.cliente.health_manager_id == user.id)
    return _can_view_submitter_id(user, recording.submitter_user_id)


def _can_manage_recording(user, recording: LoomRecording) -> bool:
    if _is_admin_user(user):
        return True
    if recording.submitter_user_id == user.id:
        return True
    if _is_team_leader_user(user):
        return recording.submitter_user_id in (_allowed_submitter_ids(user) or set())
    return False


def _recordings_scope_query(user):
    if _is_health_manager_user(user):
        return LoomRecording.query.filter(
            LoomRecording.cliente_id.isnot(None),
            LoomRecording.cliente.has(Cliente.health_manager_id == user.id),
        )
    allowed_ids = _allowed_submitter_ids(user)
    if allowed_ids is None:
        return LoomRecording.query
    return LoomRecording.query.filter(LoomRecording.submitter_user_id.in_(list(allowed_ids)))


def _can_access_cliente(user, cliente: Cliente) -> bool:
    if _is_admin_user(user):
        return True

    assignee_ids = {
        cliente.nutrizionista_id,
        cliente.coach_id,
        cliente.psicologa_id,
        cliente.consulente_alimentare_id,
        cliente.health_manager_id,
    }
    assignee_ids.discard(None)

    if _is_team_leader_user(user):
        allowed = _allowed_submitter_ids(user) or set()
        return any(user_id in allowed for user_id in assignee_ids)

    return user.id in assignee_ids


def _clienti_scope_query(user):
    if _is_admin_user(user):
        return Cliente.query

    if _is_team_leader_user(user):
        allowed_ids = _allowed_submitter_ids(user) or set()
        return Cliente.query.filter(
            or_(
                Cliente.nutrizionista_id.in_(list(allowed_ids)),
                Cliente.coach_id.in_(list(allowed_ids)),
                Cliente.psicologa_id.in_(list(allowed_ids)),
                Cliente.consulente_alimentare_id.in_(list(allowed_ids)),
                Cliente.health_manager_id.in_(list(allowed_ids)),
            )
        )

    return Cliente.query.filter(
        or_(
            Cliente.nutrizionista_id == user.id,
            Cliente.coach_id == user.id,
            Cliente.psicologa_id == user.id,
            Cliente.consulente_alimentare_id == user.id,
            Cliente.health_manager_id == user.id,
        )
    )


def can_view_submitter_id_for_role(user_like, submitter_user_id: int, allowed_ids: set[int] | None) -> bool:
    """Helper puro per verificare lo scope visibilità senza DB."""
    if getattr(user_like, "is_admin", False) or getattr(user_like, "role", "") == UserRoleEnum.admin.value:
        return True
    if allowed_ids is None:
        return False
    return submitter_user_id in allowed_ids
