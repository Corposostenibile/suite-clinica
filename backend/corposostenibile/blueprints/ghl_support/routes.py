"""
Routes API per blueprint ghl_support.

Endpoints (tutti /api/ghl-support/*):

Autenticazione:
- POST /sso/exchange                           → scambia placeholder GHL con JWT
- GET  /session/me                             → info sessione corrente

Ticketing (protetti da @ghl_session_required):
- POST /tickets                                → crea ticket (title, description)
- GET  /tickets/mine                           → lista ticket dell'utente GHL
- GET  /tickets/<id>                           → dettaglio
- POST /tickets/<id>/comments                  → aggiungi commento
- POST /tickets/<id>/attachments               → upload allegato
- GET  /attachments/<id>/download              → download allegato
"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Tuple

from flask import abort, current_app, g, jsonify, request, send_file
from werkzeug.utils import secure_filename

from corposostenibile.extensions import db
from corposostenibile.models import (
    GHLSupportTicket,
    GHLSupportTicketAttachment,
)

from . import ghl_support_bp
from .services import GHLSupportTicketService
from .sso import (
    build_user_from_query_params,
    create_session_token,
    ghl_session_required,
)

logger = logging.getLogger(__name__)


# ─── Helpers ───────────────────────────────────────────────────────────────

ALLOWED_EXTENSIONS = {
    "png", "jpg", "jpeg", "gif", "webp", "bmp",
    "pdf",
    "mp4", "mov", "webm",
    "txt", "log", "json", "csv",
    "zip",
}
MAX_ATTACHMENT_MB = 10


def _parse_user_agent(ua: str) -> Tuple[str, str]:
    """Estrae (browser, os) dallo user-agent (parser leggero)."""
    if not ua:
        return "", ""
    ua_lower = ua.lower()
    if "firefox/" in ua_lower:
        browser = "Firefox"
    elif "edg/" in ua_lower or "edge/" in ua_lower:
        browser = "Edge"
    elif "chrome/" in ua_lower and "safari/" in ua_lower:
        browser = "Chrome"
    elif "safari/" in ua_lower and "version/" in ua_lower:
        browser = "Safari"
    elif "opera/" in ua_lower or " opr/" in ua_lower:
        browser = "Opera"
    else:
        browser = "Sconosciuto"

    if "windows nt" in ua_lower:
        os_name = "Windows"
    elif "mac os x" in ua_lower or "macintosh" in ua_lower:
        os_name = "macOS"
    elif "iphone" in ua_lower or "ipad" in ua_lower:
        os_name = "iOS"
    elif "android" in ua_lower:
        os_name = "Android"
    elif "linux" in ua_lower:
        os_name = "Linux"
    else:
        os_name = "Sconosciuto"

    return browser, os_name


def _attachment_dir() -> Path:
    base = Path(current_app.config.get("UPLOAD_FOLDER", "./uploads"))
    if not base.is_absolute():
        base = Path(current_app.root_path).parent / base
    folder = base / "ghl_support"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


# ─── SSO endpoints ─────────────────────────────────────────────────────────


@ghl_support_bp.route("/sso/exchange", methods=["POST"])
def sso_exchange():
    """
    Scambia i placeholder GHL ricevuti dal Custom Menu Link con un JWT di
    sessione. Chiamato dal React embed page al primo mount.

    Body JSON atteso:
      {
        "user_id": "...",        # obbligatorio
        "user_email": "...",
        "user_name": "...",
        "role": "...",
        "location_id": "...",
        "location_name": "..."
      }
    """
    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    ghl_user = build_user_from_query_params(payload)
    token = create_session_token(ghl_user)
    return jsonify(
        {
            "session_token": token,
            "user": ghl_user.to_dict(),
        }
    )


@ghl_support_bp.route("/session/me", methods=["GET"])
@ghl_session_required
def session_me():
    """Ritorna l'utente GHL della sessione corrente."""
    return jsonify(g.ghl_user.to_dict())


# ─── Tickets ───────────────────────────────────────────────────────────────


@ghl_support_bp.route("/tickets", methods=["POST"])
@ghl_session_required
def create_ticket():
    """Crea un nuovo ticket. Form minimo: title, description."""
    payload: Dict[str, Any] = request.get_json(silent=True) or {}

    title = (payload.get("title") or "").strip()
    description = (payload.get("description") or "").strip()
    if not title:
        abort(422, description="Il titolo è obbligatorio")
    if not description:
        abort(422, description="La descrizione è obbligatoria")

    # Metadati tecnici dal client (fallback a headers)
    client_ua = (
        payload.get("user_agent")
        or request.headers.get("User-Agent")
        or ""
    ).strip()
    browser = (payload.get("browser") or "").strip()
    os_name = (payload.get("os") or "").strip()
    if not browser or not os_name:
        parsed_browser, parsed_os = _parse_user_agent(client_ua)
        browser = browser or parsed_browser
        os_name = os_name or parsed_os

    ticket = GHLSupportTicketService.create_ticket(
        ghl_user_id=g.ghl_user.user_id,
        ghl_user_email=g.ghl_user.email,
        ghl_user_name=g.ghl_user.name,
        ghl_user_role=g.ghl_user.role,
        ghl_location_id=g.ghl_user.location_id,
        ghl_location_name=g.ghl_user.location_name,
        title=title,
        description=description,
        pagina_origine=(payload.get("pagina_origine") or "").strip() or None,
        browser=browser or None,
        os=os_name or None,
        user_agent_raw=client_ua[:2000] or None,
    )

    return jsonify(ticket.to_dict()), 201


@ghl_support_bp.route("/tickets/mine", methods=["GET"])
@ghl_session_required
def list_my_tickets():
    status = request.args.get("status")
    limit = min(int(request.args.get("limit", 100)), 500)
    tickets = GHLSupportTicketService.get_user_tickets(
        ghl_user_id=g.ghl_user.user_id,
        status=status,
        limit=limit,
    )
    return jsonify([t.to_dict() for t in tickets])


@ghl_support_bp.route("/tickets/<int:ticket_id>", methods=["GET"])
@ghl_session_required
def get_ticket(ticket_id: int):
    ticket = GHLSupportTicketService.get_by_id_for_ghl_user(
        ticket_id,
        ghl_user_id=g.ghl_user.user_id,
    )
    if not ticket:
        abort(404, description="Ticket non trovato")
    return jsonify(ticket.to_dict(include_comments=True, include_attachments=True))


@ghl_support_bp.route("/tickets/<int:ticket_id>/comments", methods=["POST"])
@ghl_session_required
def add_comment(ticket_id: int):
    ticket = GHLSupportTicketService.get_by_id_for_ghl_user(
        ticket_id,
        ghl_user_id=g.ghl_user.user_id,
    )
    if not ticket:
        abort(404, description="Ticket non trovato")

    content = (request.get_json(silent=True) or {}).get("content", "").strip()
    if not content:
        abort(422, description="Il commento non può essere vuoto")
    if len(content) > 10000:
        abort(422, description="Commento troppo lungo (max 10000 caratteri)")

    comment = GHLSupportTicketService.add_comment_from_ghl_user(
        ticket=ticket,
        ghl_user_id=g.ghl_user.user_id,
        ghl_user_name=g.ghl_user.name,
        content=content,
    )
    return jsonify(comment.to_dict()), 201


@ghl_support_bp.route("/tickets/<int:ticket_id>/attachments", methods=["POST"])
@ghl_session_required
def upload_attachment(ticket_id: int):
    ticket = GHLSupportTicketService.get_by_id_for_ghl_user(
        ticket_id,
        ghl_user_id=g.ghl_user.user_id,
    )
    if not ticket:
        abort(404, description="Ticket non trovato")

    if "file" not in request.files:
        abort(422, description="Nessun file ricevuto (campo atteso: 'file')")

    file_storage = request.files["file"]
    if not file_storage or not file_storage.filename:
        abort(422, description="File vuoto")

    original_name = secure_filename(file_storage.filename)
    ext = (original_name.rsplit(".", 1)[-1] or "").lower()
    if ext not in ALLOWED_EXTENSIONS:
        abort(422, description=f"Estensione '.{ext}' non permessa")

    file_storage.seek(0, os.SEEK_END)
    size = file_storage.tell()
    file_storage.seek(0)
    max_bytes = MAX_ATTACHMENT_MB * 1024 * 1024
    if size > max_bytes:
        abort(422, description=f"File troppo grande (max {MAX_ATTACHMENT_MB}MB)")

    unique_name = f"{ticket.id}_{uuid.uuid4().hex}_{original_name}"
    dest = _attachment_dir() / unique_name
    file_storage.save(str(dest))

    attachment = GHLSupportTicketAttachment(
        ticket_id=ticket.id,
        filename=original_name,
        file_path=str(dest),
        file_size=size,
        mime_type=file_storage.mimetype or None,
        uploaded_by_ghl_user_id=g.ghl_user.user_id,
        uploaded_by_ghl_user_name=g.ghl_user.name,
    )
    db.session.add(attachment)
    db.session.commit()

    # Push su ClickUp (async) se il task esiste già
    if (
        current_app.config.get("CLICKUP_GHL_INTEGRATION_ENABLED", False)
        and ticket.clickup_task_id
    ):
        from .tasks import push_attachment_to_clickup_ghl
        push_attachment_to_clickup_ghl.delay(attachment.id)

    return jsonify(attachment.to_dict()), 201


@ghl_support_bp.route("/attachments/<int:attachment_id>/download", methods=["GET"])
@ghl_session_required
def download_attachment(attachment_id: int):
    attachment = GHLSupportTicketAttachment.query.get(attachment_id)
    if not attachment:
        abort(404)

    ticket = GHLSupportTicket.query.get(attachment.ticket_id)
    if not ticket or ticket.ghl_user_id != g.ghl_user.user_id:
        abort(403)

    path = Path(attachment.file_path)
    if not path.exists():
        abort(404, description="File non trovato su disco")

    return send_file(
        str(path),
        as_attachment=True,
        download_name=attachment.filename,
        mimetype=attachment.mime_type or "application/octet-stream",
    )
