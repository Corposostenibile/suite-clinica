"""
Routes API per blueprint it_support.

Endpoints:
- POST   /api/it-support/tickets              → crea ticket
- GET    /api/it-support/tickets/mine         → lista ticket utente corrente
- GET    /api/it-support/tickets/<id>         → dettaglio ticket (con commenti)
- POST   /api/it-support/tickets/<id>/comments → aggiungi commento
- POST   /api/it-support/tickets/<id>/attachments → upload allegato
- GET    /api/it-support/attachments/<id>/download → download allegato
- GET    /api/it-support/enums                → mappa enum (per il form FE)
"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Tuple

from flask import abort, current_app, jsonify, request, send_file
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from corposostenibile.extensions import db
from corposostenibile.models import (
    ITSupportTicket,
    ITSupportTicketAttachment,
    ITSupportTicketCriticitaEnum,
    ITSupportTicketModuloEnum,
    ITSupportTicketTipoEnum,
)

from . import it_support_bp
from .services import ITSupportTicketService

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


def _is_admin_user() -> bool:
    return bool(getattr(current_user, "is_admin", False))


def _parse_enum(enum_cls, raw: Any, field_name: str):
    if raw is None or raw == "":
        abort(422, description=f"Campo '{field_name}' obbligatorio")
    if isinstance(raw, enum_cls):
        return raw
    try:
        return enum_cls(str(raw).strip().lower())
    except ValueError:
        valid = [m.value for m in enum_cls]
        abort(
            422,
            description=f"Valore '{raw}' non valido per '{field_name}'. Validi: {valid}",
        )


def _parse_user_agent(ua: str) -> Tuple[str, str]:
    """Estrae (browser, os) in modo leggero dallo user-agent."""
    if not ua:
        return "", ""
    ua_lower = ua.lower()
    browser = ""
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
    folder = base / "it_support"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


# ─── Endpoints ─────────────────────────────────────────────────────────────


@it_support_bp.route("/enums", methods=["GET"])
@login_required
def get_enums():
    """Ritorna la lista di valori validi per i select del form."""
    return jsonify(
        {
            "tipo": [
                {"value": m.value, "label": m.value.replace("_", " ").capitalize()}
                for m in ITSupportTicketTipoEnum
            ],
            "modulo": [
                {"value": m.value, "label": m.value.capitalize()}
                for m in ITSupportTicketModuloEnum
            ],
            "criticita": [
                {"value": m.value, "label": m.value.replace("_", " ").capitalize()}
                for m in ITSupportTicketCriticitaEnum
            ],
        }
    )


@it_support_bp.route("/tickets", methods=["POST"])
@login_required
def create_ticket():
    payload: Dict[str, Any] = request.get_json(silent=True) or {}

    title = (payload.get("title") or "").strip()
    description = (payload.get("description") or "").strip()
    if not title:
        abort(422, description="Il titolo è obbligatorio")
    if not description:
        abort(422, description="La descrizione è obbligatoria")

    tipo = _parse_enum(ITSupportTicketTipoEnum, payload.get("tipo"), "tipo")
    modulo = _parse_enum(ITSupportTicketModuloEnum, payload.get("modulo"), "modulo")
    criticita = _parse_enum(
        ITSupportTicketCriticitaEnum, payload.get("criticita"), "criticita"
    )

    # Client-side auto fields (fallback a header se mancanti)
    client_ua = (payload.get("user_agent") or request.headers.get("User-Agent") or "").strip()
    browser = (payload.get("browser") or "").strip()
    os_name = (payload.get("os") or "").strip()
    if not browser or not os_name:
        parsed_browser, parsed_os = _parse_user_agent(client_ua)
        browser = browser or parsed_browser
        os_name = os_name or parsed_os

    ticket = ITSupportTicketService.create_ticket(
        user=current_user,
        title=title,
        description=description,
        tipo=tipo,
        modulo=modulo,
        criticita=criticita,
        cliente_coinvolto=(payload.get("cliente_coinvolto") or "").strip() or None,
        link_registrazione=(payload.get("link_registrazione") or "").strip() or None,
        pagina_origine=(payload.get("pagina_origine") or "").strip() or None,
        browser=browser or None,
        os=os_name or None,
        versione_app=(payload.get("versione_app") or "").strip() or None,
        commit_sha=(payload.get("commit_sha") or "").strip() or None,
        user_agent_raw=client_ua[:2000] or None,
    )

    return jsonify(ticket.to_dict()), 201


@it_support_bp.route("/tickets/mine", methods=["GET"])
@login_required
def list_my_tickets():
    status = request.args.get("status")
    limit = min(int(request.args.get("limit", 100)), 500)
    tickets = ITSupportTicketService.get_user_tickets(
        user_id=current_user.id,
        status=status,
        limit=limit,
    )
    return jsonify([t.to_dict() for t in tickets])


@it_support_bp.route("/tickets/<int:ticket_id>", methods=["GET"])
@login_required
def get_ticket(ticket_id: int):
    ticket = ITSupportTicketService.get_by_id_for_user(
        ticket_id,
        user_id=current_user.id,
        is_admin=_is_admin_user(),
    )
    if not ticket:
        abort(404, description="Ticket non trovato")
    return jsonify(ticket.to_dict(include_comments=True, include_attachments=True))


@it_support_bp.route("/tickets/<int:ticket_id>/comments", methods=["POST"])
@login_required
def add_comment(ticket_id: int):
    ticket = ITSupportTicketService.get_by_id_for_user(
        ticket_id,
        user_id=current_user.id,
        is_admin=_is_admin_user(),
    )
    if not ticket:
        abort(404, description="Ticket non trovato")

    content = (request.get_json(silent=True) or {}).get("content", "").strip()
    if not content:
        abort(422, description="Il commento non può essere vuoto")
    if len(content) > 10000:
        abort(422, description="Commento troppo lungo (max 10000 caratteri)")

    comment = ITSupportTicketService.add_comment_from_user(
        ticket=ticket,
        author=current_user,
        content=content,
    )
    return jsonify(comment.to_dict()), 201


@it_support_bp.route("/tickets/<int:ticket_id>/attachments", methods=["POST"])
@login_required
def upload_attachment(ticket_id: int):
    ticket = ITSupportTicketService.get_by_id_for_user(
        ticket_id,
        user_id=current_user.id,
        is_admin=_is_admin_user(),
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

    # Leggi dimensione
    file_storage.seek(0, os.SEEK_END)
    size = file_storage.tell()
    file_storage.seek(0)
    max_bytes = MAX_ATTACHMENT_MB * 1024 * 1024
    if size > max_bytes:
        abort(422, description=f"File troppo grande (max {MAX_ATTACHMENT_MB}MB)")

    # Salva su disco
    unique_name = f"{ticket.id}_{uuid.uuid4().hex}_{original_name}"
    dest = _attachment_dir() / unique_name
    file_storage.save(str(dest))

    attachment = ITSupportTicketAttachment(
        ticket_id=ticket.id,
        filename=original_name,
        file_path=str(dest),
        file_size=size,
        mime_type=file_storage.mimetype or None,
        uploaded_by_id=current_user.id,
    )
    db.session.add(attachment)
    db.session.commit()

    # Push su ClickUp (async)
    if (
        current_app.config.get("CLICKUP_INTEGRATION_ENABLED", False)
        and ticket.clickup_task_id
    ):
        from .tasks import push_attachment_to_clickup
        push_attachment_to_clickup.delay(attachment.id)

    return jsonify(attachment.to_dict()), 201


@it_support_bp.route("/attachments/<int:attachment_id>/download", methods=["GET"])
@login_required
def download_attachment(attachment_id: int):
    attachment = ITSupportTicketAttachment.query.get(attachment_id)
    if not attachment:
        abort(404)

    ticket = ITSupportTicket.query.get(attachment.ticket_id)
    if not ticket or (not _is_admin_user() and ticket.user_id != current_user.id):
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
