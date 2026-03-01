"""
teams_bot_service.py
====================
Bot Framework adapter e gestione messaggi per Microsoft Teams.
Tutti gli utenti Teams possono interagire, anche senza account nel DB.
"""

from __future__ import annotations

import logging
from pathlib import Path

import aiohttp
from flask import current_app

logger = logging.getLogger(__name__)

# Stato in-memory per il flusso "aggiungi allegato" (conv_id → ticket_id)
_pending_attachments: dict[str, int] = {}

# Cache token Graph API (evita richieste ripetute)
_graph_token_cache: dict[str, str] = {}


def _get_bot_config() -> dict:
    return {
        "app_id": current_app.config.get("TEAMS_BOT_APP_ID", ""),
        "app_password": current_app.config.get("TEAMS_BOT_APP_PASSWORD", ""),
        "tenant_id": current_app.config.get("TEAMS_BOT_TENANT_ID", ""),
    }


async def process_activity(body: dict, auth_header: str):
    """Processa un'activity in arrivo dal Bot Framework.

    Ritorna l'invoke response (per Data.Query typeahead) oppure None.
    """
    try:
        from botbuilder.core import (
            BotFrameworkAdapter,
            BotFrameworkAdapterSettings,
            TurnContext,
        )
        from botbuilder.schema import Activity
    except ImportError:
        logger.warning("botbuilder-core non installato, Teams bot disabilitato")
        return None

    cfg = _get_bot_config()
    if not cfg["app_id"]:
        logger.warning("Teams bot non configurato (TEAMS_BOT_APP_ID mancante)")
        return None

    settings = BotFrameworkAdapterSettings(
        app_id=cfg["app_id"],
        app_password=cfg["app_password"],
        channel_auth_tenant=cfg["tenant_id"] or None,
    )
    adapter = BotFrameworkAdapter(settings)

    activity = Activity().deserialize(body)

    async def on_turn(turn_context: TurnContext):
        await _handle_turn(turn_context)

    # adapter.process_activity returns InvokeResponse for invoke activities
    result = await adapter.process_activity(activity, auth_header, on_turn)
    return result


# ─────────────────────── Helper: invia Adaptive Card ─────────────────────── #

async def _send_card(turn_context, card: dict):
    """Invia una Adaptive Card correttamente formattata."""
    from botbuilder.schema import Attachment
    from botbuilder.core import MessageFactory
    attachment = Attachment(
        content_type="application/vnd.microsoft.card.adaptive",
        content=card,
    )
    await turn_context.send_activity(MessageFactory.attachment(attachment))


# ─────────────────────── Helper: info utente Teams ─────────────────────── #

def _get_teams_user_info(turn_context) -> dict:
    """Estrae nome e AAD ID dell'utente Teams dall'activity."""
    from_prop = turn_context.activity.from_property
    return {
        "name": from_prop.name if from_prop else "Utente Teams",
        "aad_id": from_prop.aad_object_id if from_prop else None,
    }


# ─────────────────── Microsoft Graph API: cerca utenti tenant ─────────── #

async def _get_graph_token() -> str | None:
    """Ottiene un token per Microsoft Graph API via client credentials."""
    cfg = _get_bot_config()
    tenant_id = cfg["tenant_id"]
    if not tenant_id or not cfg["app_id"] or not cfg["app_password"]:
        return None

    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data={
                "client_id": cfg["app_id"],
                "client_secret": cfg["app_password"],
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
            }) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("access_token")
                else:
                    body = await resp.text()
                    logger.warning("Graph token request failed: %s %s", resp.status, body[:200])
    except Exception:
        logger.exception("Errore ottenimento Graph token")
    return None


async def _search_graph_users(query: str, limit: int = 15) -> list[dict]:
    """Cerca utenti nel tenant Azure AD via Microsoft Graph API."""
    token = await _get_graph_token()
    if not token:
        return []

    # Usa $filter con startswith su displayName per cercare
    # Nota: richiede permesso Application "User.Read.All" nell'app registration
    safe_query = query.replace("'", "''")
    url = (
        f"https://graph.microsoft.com/v1.0/users"
        f"?$filter=startswith(displayName,'{safe_query}')"
        f"&$top={limit}"
        f"&$select=id,displayName,mail"
    )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={"Authorization": f"Bearer {token}"}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [
                        {
                            "aad_id": u["id"],
                            "name": u.get("displayName", ""),
                            "email": u.get("mail", ""),
                        }
                        for u in data.get("value", [])
                        if u.get("displayName")
                    ]
                else:
                    body = await resp.text()
                    logger.warning("Graph users search failed: %s %s", resp.status, body[:200])
    except Exception:
        logger.exception("Errore ricerca utenti Graph")
    return []


# ─────────────────── Riepilogo ticket utente ─────────────────── #

def _get_user_ticket_summary(turn_context) -> dict:
    """Recupera i ticket aperti dell'utente per il riepilogo nella welcome card."""
    from corposostenibile.models import TeamTicket, TeamTicketStatusEnum, User
    from sqlalchemy import or_

    teams_user = _get_teams_user_info(turn_context)
    aad_id = teams_user.get("aad_id")
    conv_id = turn_context.activity.conversation.id if turn_context.activity.conversation else None

    open_statuses = [TeamTicketStatusEnum.aperto, TeamTicketStatusEnum.in_lavorazione]
    user = _find_user_by_aad(aad_id) if aad_id else None

    # Ticket assegnati a me (aperti)
    assigned = []
    if user:
        assigned = (
            TeamTicket.query
            .filter(
                TeamTicket.assigned_users.any(User.id == user.id),
                TeamTicket.status.in_(open_statuses),
            )
            .order_by(TeamTicket.created_at.desc())
            .limit(10)
            .all()
        )

    # Ticket che ho aperto (ancora aperti)
    my_open = []
    creator_filters = []
    if user:
        creator_filters.append(TeamTicket.created_by_id == user.id)
    if conv_id:
        creator_filters.append(TeamTicket.teams_conversation_id == conv_id)

    if creator_filters:
        my_open = (
            TeamTicket.query
            .filter(
                or_(*creator_filters),
                TeamTicket.status.in_(open_statuses),
            )
            .order_by(TeamTicket.created_at.desc())
            .limit(10)
            .all()
        )

    # Deduplicazione: rimuovi da my_open quelli gia' in assigned
    assigned_ids = {t.id for t in assigned}
    my_open = [t for t in my_open if t.id not in assigned_ids]

    return {
        "assigned_tickets": [t.to_dict() for t in assigned] if assigned else None,
        "my_open_tickets": [t.to_dict() for t in my_open] if my_open else None,
    }


# ─────────────────────── Handle Turn ─────────────────────── #

async def _handle_turn(turn_context) -> None:
    """Gestisce il turno di conversazione."""
    from botbuilder.schema import ActivityTypes
    from corposostenibile.blueprints.team_tickets.adaptive_cards.templates import welcome_card

    activity = turn_context.activity

    # ── Invoke: typeahead search (Data.Query) ──
    if activity.type == "invoke" and activity.name == "application/search":
        await _handle_search_invoke(turn_context)
        return

    if activity.type == ActivityTypes.message:
        # Submit da Adaptive Card
        if activity.value:
            await _handle_card_submit(turn_context, activity.value)
            return

        # Controlla se ci sono allegati FILE reali (non metadata inline di Teams)
        real_files = _get_real_file_attachments(activity.attachments)
        if real_files:
            await _handle_file_attachments(turn_context, real_files)
            return

        # Messaggio di testo: mostra welcome card con riepilogo
        summary = _get_user_ticket_summary(turn_context)
        await _send_card(turn_context, welcome_card(**summary))
        return

    elif activity.type == ActivityTypes.conversation_update:
        if activity.members_added:
            for member in activity.members_added:
                if member.id != activity.recipient.id:
                    summary = _get_user_ticket_summary(turn_context)
                    await _send_card(turn_context, welcome_card(**summary))


# ─────────────────────── Handle Search Invoke (Data.Query) ─────────────── #

async def _handle_search_invoke(turn_context) -> None:
    """Gestisce le richieste typeahead search da Data.Query."""
    from botbuilder.schema import InvokeResponse, Activity as BFActivity

    value = turn_context.activity.value or {}
    query_text = value.get("queryText", "").strip()
    dataset = value.get("dataset", "")

    logger.info("Data.Query invoke: dataset=%s, query=%r", dataset, query_text)

    results = []

    if dataset == "patients" and len(query_text) >= 2:
        from corposostenibile.blueprints.team_tickets.services.ticket_service import search_patients
        patients = search_patients(query_text, limit=15)
        results = [
            {
                "title": f"{p['nome']} ({p.get('email') or p.get('telefono') or ''})",
                "value": str(p["id"]),
            }
            for p in patients
        ]

    elif dataset == "users" and len(query_text) >= 2:
        # Cerca utenti nel tenant via Graph API
        graph_users = await _search_graph_users(query_text, limit=15)
        if graph_users:
            results = [
                {
                    "title": f"{u['name']}" + (f" ({u['email']})" if u.get("email") else ""),
                    "value": f"aad:{u['aad_id']}:{u['name']}",
                }
                for u in graph_users
            ]
        else:
            # Fallback: cerca tra gli utenti DB
            from corposostenibile.blueprints.team_tickets.services.ticket_service import get_assignable_users
            db_users = get_assignable_users()
            query_lower = query_text.lower()
            results = [
                {"title": u["name"], "value": f"db:{u['id']}:{u['name']}"}
                for u in db_users
                if query_lower in u["name"].lower()
            ][:15]

    logger.info("Data.Query results: dataset=%s, count=%d", dataset, len(results))

    # Invia l'invoke response tramite il turn context
    invoke_response = InvokeResponse(
        status=200,
        body={
            "type": "application/vnd.microsoft.search.searchResponse",
            "value": {"results": results},
        },
    )
    await turn_context.send_activity(
        BFActivity(type="invokeResponse", value=invoke_response)
    )


# ─────────────────────── Helper: filtra allegati reali ─────────────────── #

_SKIP_CONTENT_TYPES = {
    "text/html",
    "application/vnd.microsoft.card.adaptive",
    "application/vnd.microsoft.card.hero",
    "application/vnd.microsoft.card.thumbnail",
}


def _get_real_file_attachments(attachments) -> list:
    """Filtra gli allegati, tenendo solo file reali (non metadata Teams)."""
    if not attachments:
        return []
    real = []
    for att in attachments:
        ct = (att.content_type or "").lower()
        if ct in _SKIP_CONTENT_TYPES:
            continue
        if "download.info" in ct or att.content_url or (
            att.content and isinstance(att.content, dict) and att.content.get("downloadUrl")
        ):
            real.append(att)
    return real


# ─────────────────────── Handle File Attachments ─────────────────────── #

async def _handle_file_attachments(turn_context, real_files: list) -> None:
    """Gestisce file inviati dall'utente in chat (associa al ticket pending)."""
    conv_id = turn_context.activity.conversation.id if turn_context.activity.conversation else None
    ticket_id = _pending_attachments.pop(conv_id, None) if conv_id else None

    if not ticket_id:
        await turn_context.send_activity(
            "Per allegare un file, prima crea un ticket o clicca 'Aggiungi Allegato' "
            "su un ticket esistente."
        )
        return

    from corposostenibile.models import TeamTicket
    ticket = TeamTicket.query.get(ticket_id)
    if not ticket:
        await turn_context.send_activity("Ticket non trovato.")
        return

    saved_count = 0
    for att in real_files:
        download_url = None
        filename = att.name or "allegato"

        if att.content and isinstance(att.content, dict):
            download_url = att.content.get("downloadUrl")
        if not download_url and att.content_url:
            download_url = att.content_url

        if not download_url:
            continue

        try:
            file_data = await _download_file(download_url)
            if file_data:
                _save_teams_attachment(ticket, filename, file_data, att.content_type)
                saved_count += 1
        except Exception:
            logger.exception("Errore download allegato Teams per ticket %s", ticket_id)

    if saved_count > 0:
        from corposostenibile.extensions import db
        db.session.commit()
        await turn_context.send_activity(
            f"{saved_count} allegato/i aggiunto/i al ticket {ticket.ticket_number}!"
        )
    else:
        await turn_context.send_activity("Non sono riuscito a scaricare gli allegati.")


async def _download_file(url: str) -> bytes | None:
    """Scarica un file da un URL."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
    except Exception:
        logger.exception("Errore download file da %s", url)
    return None


def _save_teams_attachment(ticket, filename: str, file_data: bytes, content_type: str | None):
    """Salva un allegato scaricato da Teams nel filesystem e nel DB."""
    from werkzeug.utils import secure_filename as sf
    from corposostenibile.models import TeamTicketAttachment, TeamTicketSourceEnum
    from corposostenibile.extensions import db

    base = current_app.config.get(
        "UPLOAD_FOLDER",
        str(Path(current_app.root_path).parent / "uploads"),
    )
    ticket_dir = Path(base) / "team_tickets" / str(ticket.id)
    ticket_dir.mkdir(parents=True, exist_ok=True)

    safe_name = sf(filename) or "allegato"
    dest = ticket_dir / safe_name
    counter = 1
    while dest.exists():
        stem = dest.stem
        suffix = dest.suffix
        dest = ticket_dir / f"{stem}_{counter}{suffix}"
        counter += 1

    dest.write_bytes(file_data)

    att = TeamTicketAttachment(
        ticket_id=ticket.id,
        filename=safe_name,
        file_path=str(dest.relative_to(Path(base).parent)),
        file_size=len(file_data),
        mime_type=content_type or "application/octet-stream",
        uploaded_by_id=None,
        source=TeamTicketSourceEnum.teams,
    )
    db.session.add(att)


# ─────────────────────── Handle Card Submit ─────────────────────── #

async def _handle_card_submit(turn_context, value: dict) -> None:
    """Gestisce i submit delle Adaptive Cards."""
    from corposostenibile.blueprints.team_tickets.adaptive_cards.templates import (
        create_ticket_form,
        ticket_confirmation_card,
        ticket_list_card,
        ticket_detail_card,
        reply_form_card,
    )
    from corposostenibile.blueprints.team_tickets.services.ticket_service import (
        create_ticket,
        add_message,
    )
    from corposostenibile.models import (
        TeamTicket, TeamTicketStatusEnum, TeamTicketMessage, User,
    )
    from corposostenibile.extensions import db
    from sqlalchemy import or_

    action = value.get("action", "")
    teams_user = _get_teams_user_info(turn_context)
    conv_id = turn_context.activity.conversation.id if turn_context.activity.conversation else None
    aad_id = teams_user.get("aad_id")

    if action == "new_ticket":
        await _send_card(turn_context, create_ticket_form())

    elif action == "submit_ticket":
        title = value.get("title", "").strip()
        description = value.get("description", "").strip()
        priority = value.get("priority", "media")
        assignee_raw = value.get("assignee_id", "").strip()
        cliente_id_str = value.get("cliente_id", "").strip()

        if not description:
            await turn_context.send_activity("Descrizione obbligatoria. Riprova.")
            return

        # Parse cliente_id from Data.Query selection
        cliente_id = None
        if cliente_id_str and cliente_id_str.isdigit():
            cliente_id = int(cliente_id_str)

        # Parse assignee from Data.Query: "aad:{aad_id}:{name}" o "db:{id}:{name}"
        assignee_ids = []
        assignee_name = None
        if assignee_raw:
            assignee_ids, assignee_name = _parse_assignee_value(assignee_raw)

        # Trova o crea l'utente DB per il creatore Teams
        creator_id = _resolve_teams_user_id(aad_id, teams_user.get("name"))

        ticket = create_ticket(
            description=description,
            created_by_id=creator_id,
            priority=priority,
            source="teams",
            assignee_ids=assignee_ids or None,
            cliente_id=cliente_id,
            title=title or None,
        )

        # Salva info Teams sul ticket
        ticket.teams_conversation_id = conv_id
        ticket.teams_activity_id = turn_context.activity.id

        db.session.commit()

        await _send_card(turn_context, ticket_confirmation_card(ticket.to_dict()))

    # ── Ticket Assegnati a Me ──
    elif action == "tickets_assigned_to_me":
        user = _find_user_by_aad(aad_id) if aad_id else None
        if user:
            tickets = (
                TeamTicket.query
                .filter(TeamTicket.assigned_users.any(User.id == user.id))
                .order_by(TeamTicket.created_at.desc())
                .limit(10)
                .all()
            )
        else:
            tickets = []
        await _send_card(
            turn_context,
            ticket_list_card([t.to_dict() for t in tickets], "Ticket Assegnati a Me"),
        )

    # ── Ticket Miei Aperti (creati da me, ancora aperti) ──
    elif action == "tickets_my_open":
        user = _find_user_by_aad(aad_id) if aad_id else None
        filters = [
            TeamTicket.status.in_([TeamTicketStatusEnum.aperto, TeamTicketStatusEnum.in_lavorazione]),
        ]
        # Cerca per created_by_id o per conversation_id
        creator_filters = []
        if user:
            creator_filters.append(TeamTicket.created_by_id == user.id)
        if conv_id:
            creator_filters.append(TeamTicket.teams_conversation_id == conv_id)
        if creator_filters:
            filters.append(or_(*creator_filters))
        else:
            filters.append(db.false())

        tickets = (
            TeamTicket.query
            .filter(*filters)
            .order_by(TeamTicket.created_at.desc())
            .limit(10)
            .all()
        )
        await _send_card(
            turn_context,
            ticket_list_card([t.to_dict() for t in tickets], "Ticket Miei Aperti"),
        )

    # ── Ticket Che Ho Aperto (tutti quelli creati da me) ──
    elif action == "tickets_i_opened":
        user = _find_user_by_aad(aad_id) if aad_id else None
        creator_filters = []
        if user:
            creator_filters.append(TeamTicket.created_by_id == user.id)
        if conv_id:
            creator_filters.append(TeamTicket.teams_conversation_id == conv_id)

        if creator_filters:
            tickets = (
                TeamTicket.query
                .filter(or_(*creator_filters))
                .order_by(TeamTicket.created_at.desc())
                .limit(15)
                .all()
            )
        else:
            tickets = []
        await _send_card(
            turn_context,
            ticket_list_card([t.to_dict() for t in tickets], "Ticket Che Ho Aperto"),
        )

    # ── Ticket Che Ho Gestito (assegnati a me + dove ho scritto messaggi) ──
    elif action == "tickets_i_managed":
        user = _find_user_by_aad(aad_id) if aad_id else None
        ticket_ids = set()

        if user:
            # Ticket assegnati a me
            assigned = (
                TeamTicket.query
                .filter(TeamTicket.assigned_users.any(User.id == user.id))
                .with_entities(TeamTicket.id)
                .all()
            )
            ticket_ids.update(t.id for t in assigned)

        if aad_id:
            # Ticket dove ho scritto messaggi (via aad_id)
            msg_tickets = (
                TeamTicketMessage.query
                .filter_by(teams_sender_aad_id=aad_id)
                .with_entities(TeamTicketMessage.ticket_id)
                .distinct()
                .all()
            )
            ticket_ids.update(t.ticket_id for t in msg_tickets)

        if conv_id:
            # Ticket creati dalla mia conversazione
            conv_tickets = (
                TeamTicket.query
                .filter_by(teams_conversation_id=conv_id)
                .with_entities(TeamTicket.id)
                .all()
            )
            ticket_ids.update(t.id for t in conv_tickets)

        if ticket_ids:
            tickets = (
                TeamTicket.query
                .filter(TeamTicket.id.in_(ticket_ids))
                .order_by(TeamTicket.updated_at.desc())
                .limit(15)
                .all()
            )
        else:
            tickets = []
        await _send_card(
            turn_context,
            ticket_list_card([t.to_dict() for t in tickets], "Ticket Che Ho Gestito"),
        )

    # ── Visualizza dettaglio ticket ──
    elif action == "view_ticket":
        ticket_id = value.get("ticket_id")
        ticket = TeamTicket.query.get(ticket_id) if ticket_id else None
        if ticket:
            await _send_card(
                turn_context,
                ticket_detail_card(ticket.to_dict(include_messages=True, include_attachments=True)),
            )
        else:
            await turn_context.send_activity("Ticket non trovato.")

    elif action == "reply_ticket":
        ticket_id = value.get("ticket_id")
        ticket = TeamTicket.query.get(ticket_id)
        if ticket:
            await _send_card(turn_context, reply_form_card(ticket.id, ticket.ticket_number))

    elif action == "submit_reply":
        ticket_id = value.get("ticket_id")
        content = value.get("reply_content", "").strip()
        if ticket_id and content:
            msg = add_message(
                ticket_id=ticket_id,
                sender_id=None,
                content=content,
                source="teams",
            )
            msg.teams_sender_name = teams_user["name"]
            msg.teams_sender_aad_id = teams_user["aad_id"]
            db.session.commit()
            await turn_context.send_activity("Risposta inviata al ticket!")

    elif action == "close_ticket":
        ticket_id = value.get("ticket_id")
        if ticket_id:
            from corposostenibile.blueprints.team_tickets.services.ticket_service import update_ticket
            update_ticket(
                ticket_id=ticket_id,
                changed_by_id=None,
                status="chiuso",
            )
            await turn_context.send_activity("Ticket chiuso.")

    elif action == "add_attachment":
        ticket_id = value.get("ticket_id")
        if ticket_id and conv_id:
            _pending_attachments[conv_id] = ticket_id
            ticket = TeamTicket.query.get(ticket_id)
            ticket_num = ticket.ticket_number if ticket else f"#{ticket_id}"
            await turn_context.send_activity(
                f"Invia i file come messaggio in questa chat. "
                f"Li associo al ticket {ticket_num}."
            )

    # ── Knowledge Base ──
    elif action == "kb_chat":
        from corposostenibile.blueprints.team_tickets.adaptive_cards.templates import kb_chat_card
        doc_count, chunks_count = _get_kb_stats()
        await _send_card(turn_context, kb_chat_card(doc_count, chunks_count))

    elif action == "kb_ask":
        from corposostenibile.blueprints.team_tickets.adaptive_cards.templates import kb_response_card, kb_chat_card
        question = value.get("kb_question", "").strip()
        if not question:
            await turn_context.send_activity("Scrivi una domanda prima di cercare.")
            return
        session_id = f"teams_kb_{conv_id}" if conv_id else "teams_kb_default"
        try:
            from corposostenibile.blueprints.sop_chatbot.services.chat_service import ChatService
            result = ChatService.ask(question, session_id)
            await _send_card(
                turn_context,
                kb_response_card(result["response"], result.get("sources", []), question),
            )
        except Exception as e:
            logger.exception("Errore Knowledge Base: %s", e)
            await turn_context.send_activity(
                "Errore nella ricerca Knowledge Base. "
                "Verifica che Qdrant e Google API siano configurati correttamente."
            )

    elif action == "kb_new_session":
        from corposostenibile.blueprints.team_tickets.adaptive_cards.templates import kb_chat_card
        session_id = f"teams_kb_{conv_id}" if conv_id else "teams_kb_default"
        try:
            from corposostenibile.blueprints.sop_chatbot.services.chat_service import ChatService
            ChatService.clear_session(session_id)
        except Exception:
            pass
        doc_count, chunks_count = _get_kb_stats()
        await _send_card(turn_context, kb_chat_card(doc_count, chunks_count))


def _get_kb_stats() -> tuple[int, int]:
    """Recupera stats Knowledge Base: (doc_count, chunks_count)."""
    try:
        from corposostenibile.models import SOPDocument, SOPDocumentStatus
        doc_count = SOPDocument.query.filter_by(status=SOPDocumentStatus.ready).count()
    except Exception:
        doc_count = 0
    try:
        from corposostenibile.blueprints.sop_chatbot.services.qdrant_service import QdrantService
        chunks_count = QdrantService.get_total_chunks()
    except Exception:
        chunks_count = 0
    return doc_count, chunks_count


def _find_user_by_aad(aad_id: str):
    """Trova un User nel DB per AAD object ID."""
    from corposostenibile.models import User
    if not aad_id:
        return None
    return User.query.filter_by(teams_aad_object_id=aad_id).first()


def _resolve_teams_user_id(aad_id: str | None, name: str | None) -> int | None:
    """Trova o crea un User per il Teams user, ritorna user.id."""
    if not aad_id:
        return None
    user = _find_user_by_aad(aad_id)
    if user:
        return user.id
    # Auto-crea
    try:
        from werkzeug.security import generate_password_hash
        import secrets
        from corposostenibile.models import User
        from corposostenibile.extensions import db

        name = name or "Teams User"
        name_parts = name.strip().split(" ", 1)
        user = User(
            email=f"teams_{aad_id[:8]}@teams.internal",
            first_name=name_parts[0],
            last_name=name_parts[1] if len(name_parts) > 1 else "",
            teams_aad_object_id=aad_id,
            is_active=True,
            password_hash=generate_password_hash(secrets.token_hex(32)),
        )
        db.session.add(user)
        db.session.flush()
        logger.info("Auto-creato utente per Teams creator %s (%s)", aad_id, name)
        return user.id
    except Exception:
        db.session.rollback()
        logger.exception("Impossibile auto-creare utente Teams %s", aad_id)
        return None


def _parse_assignee_value(raw: str) -> tuple[list[int], str | None]:
    """Parse il valore dell'assegnatario da Data.Query.

    Formato: "aad:{aad_id}:{name}" o "db:{id}:{name}"
    Ritorna: (lista di user_id DB per la M2M, nome assegnatario)
    """
    parts = raw.split(":", 2)
    if len(parts) < 3:
        return [], raw

    source, identifier, name = parts

    if source == "db":
        try:
            return [int(identifier)], name
        except ValueError:
            return [], name

    elif source == "aad":
        user_id = _resolve_teams_user_id(identifier, name)
        if user_id:
            return [user_id], name
        return [], name

    return [], raw
