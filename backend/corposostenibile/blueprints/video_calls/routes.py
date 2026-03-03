"""
Video Calls API routes.

Manages video call sessions between professionals and clients using dTelecom.
Token generation is delegated to the Node.js token service (localhost:3100).
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime

import requests
from flask import request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from corposostenibile.extensions import csrf, db
from corposostenibile.models import VideoCallSession, Cliente, ServiceClienteAssignment

from . import bp

# ── Internal token service URL ────────────────────────────────────────────────
TOKEN_SERVICE = "http://localhost:3100"


def _token_service_url():
    return current_app.config.get("VIDEOCALL_TOKEN_SERVICE_URL", TOKEN_SERVICE)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _can_call_client(user, cliente_id):
    """Check if user is assigned to this client or is admin."""
    if user.role == 'admin':
        return True
    return ServiceClienteAssignment.query.filter_by(
        professionista_id=user.id,
        cliente_id=cliente_id,
        attivo=True,
    ).first() is not None


def _generate_room_name(prof_id, cliente_id=None):
    """Generate a unique room name."""
    suffix = secrets.token_hex(4)
    if cliente_id:
        return f"call-{prof_id}-{cliente_id}-{suffix}"
    return f"call-{prof_id}-{suffix}"


# ── Create a new video call session ──────────────────────────────────────────
@bp.route("/create", methods=["POST"])
@login_required
def create_call():
    """
    Create a new video call session and get tokens for the professional.

    Body: { "cliente_id": int (optional), "scheduled_at": ISO string (optional), "notes": str (optional) }
    Returns: { session, token, wsUrl, publicLink }

    If scheduled_at is provided, creates a scheduled call (no token generated yet).
    """
    data = request.get_json(silent=True) or {}
    cliente_id = data.get("cliente_id")
    scheduled_at_str = data.get("scheduled_at")
    notes = data.get("notes")

    # Validate client access if specified
    if cliente_id:
        cliente = db.session.get(Cliente, cliente_id)
        if not cliente:
            return jsonify(error="Cliente non trovato"), 404
        if not _can_call_client(current_user, cliente_id):
            return jsonify(error="Non hai accesso a questo cliente"), 403

    # Parse scheduled_at
    scheduled_at = None
    if scheduled_at_str:
        try:
            scheduled_at = datetime.fromisoformat(scheduled_at_str.replace("Z", "+00:00")).replace(tzinfo=None)
        except (ValueError, AttributeError):
            return jsonify(error="Formato data non valido"), 400

    # Create session record
    room_name = _generate_room_name(current_user.id, cliente_id)
    session_token = secrets.token_urlsafe(32)

    status = "scheduled" if scheduled_at else "waiting"

    session = VideoCallSession(
        room_name=room_name,
        session_token=session_token,
        professionista_id=current_user.id,
        cliente_id=cliente_id,
        status=status,
        scheduled_at=scheduled_at,
        notes=notes,
    )
    db.session.add(session)
    db.session.commit()

    # Scheduled calls don't need a token yet
    if scheduled_at:
        return jsonify(
            session=session.to_dict(),
            publicLink=f"/video-call/join/{session_token}",
        )

    # Get token from dTelecom token service
    try:
        resp = requests.post(f"{_token_service_url()}/token", json={
            "roomName": room_name,
            "identity": f"prof-{current_user.id}",
            "name": current_user.full_name,
            "clientIp": request.remote_addr,
            "grants": {
                "canPublish": True,
                "canSubscribe": True,
                "canPublishData": True,
                "roomAdmin": True,
            },
        }, timeout=10)
        resp.raise_for_status()
        token_data = resp.json()
    except Exception as e:
        current_app.logger.error(f"[video_calls] Token service error: {e}")
        # Clean up the session on failure
        db.session.delete(session)
        db.session.commit()
        return jsonify(error="Servizio video non disponibile", detail=str(e)), 503

    return jsonify(
        session=session.to_dict(),
        token=token_data["token"],
        wsUrl=token_data["wsUrl"],
        publicLink=f"/video-call/join/{session_token}",
    )


# ── Public join (for clients, no auth required) ─────────────────────────────
@bp.route("/public/join/<session_token>", methods=["POST"])
@csrf.exempt
def public_join(session_token):
    """
    Client joins a video call via public link.

    Body: { "name": "Client Name" }
    Returns: { token, wsUrl, session }
    """
    session = VideoCallSession.query.filter_by(
        session_token=session_token,
    ).first()

    if not session:
        return jsonify(error="Sessione non trovata"), 404
    if session.status == "ended":
        return jsonify(error="La videochiamata è già terminata"), 410
    if session.status == "cancelled":
        return jsonify(error="La videochiamata è stata annullata"), 410

    data = request.get_json(silent=True) or {}
    client_name = data.get("name", "Cliente")

    # Get token from dTelecom token service
    try:
        identity = f"client-{session.cliente_id}" if session.cliente_id else f"guest-{secrets.token_hex(4)}"
        resp = requests.post(f"{_token_service_url()}/token", json={
            "roomName": session.room_name,
            "identity": identity,
            "name": client_name,
            "clientIp": request.remote_addr,
            "grants": {
                "canPublish": True,
                "canSubscribe": True,
                "canPublishData": True,
            },
        }, timeout=10)
        resp.raise_for_status()
        token_data = resp.json()
    except Exception as e:
        current_app.logger.error(f"[video_calls] Token service error: {e}")
        return jsonify(error="Servizio video non disponibile"), 503

    # Mark session as active
    if session.status in ("waiting", "scheduled"):
        session.status = "active"
        session.started_at = datetime.utcnow()
        db.session.commit()

    return jsonify(
        token=token_data["token"],
        wsUrl=token_data["wsUrl"],
        session=session.to_dict(),
    )


# ── Get session info (public, for pre-join screen) ──────────────────────────
@bp.route("/public/info/<session_token>", methods=["GET"])
def public_info(session_token):
    """Get basic info about a video call session (for the public join page)."""
    session = VideoCallSession.query.filter_by(
        session_token=session_token,
    ).first()

    if not session:
        return jsonify(error="Sessione non trovata"), 404

    return jsonify(
        status=session.status,
        professionista_name=session.professionista.full_name if session.professionista else None,
        professionista_avatar=session.professionista.avatar_url if session.professionista else None,
        cliente_name=session.cliente.nome_cognome if session.cliente else None,
        created_at=session.created_at.isoformat() if session.created_at else None,
    )


# ── End a video call ─────────────────────────────────────────────────────────
@bp.route("/<int:session_id>/end", methods=["POST"])
@login_required
def end_call(session_id):
    """End a video call session."""
    session = db.session.get(VideoCallSession, session_id)
    if not session:
        return jsonify(error="Sessione non trovata"), 404

    if session.professionista_id != current_user.id and current_user.role != 'admin':
        return jsonify(error="Non autorizzato"), 403

    session.status = "ended"
    session.ended_at = datetime.utcnow()
    if session.started_at:
        session.duration_seconds = int((session.ended_at - session.started_at).total_seconds())

    data = request.get_json(silent=True) or {}
    if data.get("notes"):
        session.notes = data["notes"]

    db.session.commit()
    return jsonify(session=session.to_dict())


# ── Call history ──────────────────────────────────────────────────────────────
@bp.route("/history", methods=["GET"])
@login_required
def call_history():
    """Get video call history for the current user."""
    cliente_id = request.args.get("cliente_id", type=int)

    query = VideoCallSession.query.filter_by(professionista_id=current_user.id)
    if cliente_id:
        query = query.filter_by(cliente_id=cliente_id)

    sessions = query.order_by(VideoCallSession.created_at.desc()).limit(50).all()
    return jsonify(sessions=[s.to_dict() for s in sessions])


# ── Client video calls (for Appuntamenti tab) ────────────────────────────────
@bp.route("/client/<int:cliente_id>", methods=["GET"])
@login_required
def client_calls(cliente_id):
    """Get all video call sessions for a specific client."""
    if not _can_call_client(current_user, cliente_id):
        return jsonify(error="Non hai accesso a questo cliente"), 403

    sessions = (
        VideoCallSession.query
        .filter_by(cliente_id=cliente_id)
        .order_by(VideoCallSession.scheduled_at.desc().nulls_last(),
                  VideoCallSession.created_at.desc())
        .all()
    )
    return jsonify(sessions=[s.to_dict() for s in sessions])


# ── Join a scheduled call (professional gets token) ──────────────────────────
@bp.route("/<int:session_id>/join", methods=["POST"])
@login_required
def join_call(session_id):
    """
    Professional joins a scheduled/waiting call. Generates a dTelecom token.
    Transitions status from 'scheduled' → 'waiting'.
    """
    session = db.session.get(VideoCallSession, session_id)
    if not session:
        return jsonify(error="Sessione non trovata"), 404

    if session.status in ("ended", "cancelled"):
        return jsonify(error="La videochiamata è già terminata"), 410

    # Only the assigned professional or admin can join
    if session.professionista_id != current_user.id and current_user.role != 'admin':
        return jsonify(error="Non autorizzato"), 403

    # Get token from dTelecom token service
    try:
        resp = requests.post(f"{_token_service_url()}/token", json={
            "roomName": session.room_name,
            "identity": f"prof-{current_user.id}",
            "name": current_user.full_name,
            "clientIp": request.remote_addr,
            "grants": {
                "canPublish": True,
                "canSubscribe": True,
                "canPublishData": True,
                "roomAdmin": True,
            },
        }, timeout=10)
        resp.raise_for_status()
        token_data = resp.json()
    except Exception as e:
        current_app.logger.error(f"[video_calls] Token service error: {e}")
        return jsonify(error="Servizio video non disponibile", detail=str(e)), 503

    # Transition scheduled → waiting
    if session.status == "scheduled":
        session.status = "waiting"
        db.session.commit()

    return jsonify(
        session=session.to_dict(),
        token=token_data["token"],
        wsUrl=token_data["wsUrl"],
        publicLink=f"/video-call/join/{session.session_token}",
    )


# ── Upload recording ──────────────────────────────────────────────────────────
@bp.route("/<int:session_id>/upload-recording", methods=["POST"])
@login_required
@csrf.exempt
def upload_recording(session_id):
    """Upload a call recording (webm blob from MediaRecorder)."""
    session = db.session.get(VideoCallSession, session_id)
    if not session:
        return jsonify(error="Sessione non trovata"), 404

    if session.professionista_id != current_user.id and current_user.role != 'admin':
        return jsonify(error="Non autorizzato"), 403

    if 'recording' not in request.files:
        return jsonify(error="Nessun file inviato"), 400

    file = request.files['recording']
    if not file or not file.filename:
        return jsonify(error="File non valido"), 400

    ts = int(datetime.utcnow().timestamp())
    filename = secure_filename(f"{session_id}_{ts}.webm")

    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    rec_folder = os.path.join(upload_folder, 'recordings')
    os.makedirs(rec_folder, exist_ok=True)

    file.save(os.path.join(rec_folder, filename))

    session.recording_path = f"recordings/{filename}"
    db.session.commit()

    return jsonify(session=session.to_dict())


# ── Replay data ──────────────────────────────────────────────────────────────
@bp.route("/<int:session_id>/replay", methods=["GET"])
@login_required
def replay_data(session_id):
    """Return session data for the replay page."""
    session = db.session.get(VideoCallSession, session_id)
    if not session:
        return jsonify(error="Sessione non trovata"), 404

    if session.professionista_id != current_user.id and current_user.role != 'admin':
        return jsonify(error="Non autorizzato"), 403

    return jsonify(session=session.to_dict())


# ── Webhook from dTelecom ─────────────────────────────────────────────────────
@bp.route("/webhook", methods=["POST"])
@csrf.exempt
def dtelecom_webhook():
    """
    Receive webhook events from dTelecom SFU nodes.
    Events: room_started, room_finished, participant_joined, participant_left
    """
    data = request.get_json(silent=True) or {}
    event = data.get("event")
    room_name = data.get("room", {}).get("name", "")

    current_app.logger.info(f"[video_calls] Webhook: {event} for room {room_name}")

    if event == "room_finished":
        session = VideoCallSession.query.filter_by(room_name=room_name).first()
        if session and session.status != "ended":
            session.status = "ended"
            session.ended_at = datetime.utcnow()
            if session.started_at:
                session.duration_seconds = int(
                    (session.ended_at - session.started_at).total_seconds()
                )
            db.session.commit()

    return jsonify(ok=True)
