"""
teams_bot_service.py
====================
Bot Framework adapter e gestione messaggi per Microsoft Teams.
Tutti gli utenti Teams possono interagire, anche senza account nel DB.
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path

import aiohttp
from flask import current_app

logger = logging.getLogger(__name__)

# Cache token Graph API con TTL
_graph_token_cache: dict[str, object] = {}  # {"token": str, "expires_at": float}


def _get_bot_config() -> dict:
    return {
        "app_id": current_app.config.get("TEAMS_BOT_APP_ID", ""),
        "app_password": current_app.config.get("TEAMS_BOT_APP_PASSWORD", ""),
        "tenant_id": current_app.config.get("TEAMS_BOT_TENANT_ID", ""),
    }


# ─────────────────────── Pending attachments via Redis ─────────────────── #

def _get_pending_attachment(conv_id: str) -> int | None:
    """Recupera ticket_id pendente per allegati dalla cache Redis."""
    if not conv_id:
        return None
    try:
        from corposostenibile.extensions import redis_client
        if redis_client:
            val = redis_client.get(f"teams_bot:pending:{conv_id}")
            return int(val) if val else None
    except Exception:
        logger.debug("Redis non disponibile per pending attachments")
    return None


def _set_pending_attachment(conv_id: str, ticket_id: int) -> None:
    """Salva ticket_id pendente per allegati in Redis con TTL 5 min."""
    if not conv_id:
        return
    try:
        from corposostenibile.extensions import redis_client
        if redis_client:
            redis_client.setex(f"teams_bot:pending:{conv_id}", 300, str(ticket_id))
            return
    except Exception:
        logger.debug("Redis non disponibile per pending attachments")


def _pop_pending_attachment(conv_id: str) -> int | None:
    """Recupera e rimuove ticket_id pendente."""
    if not conv_id:
        return None
    try:
        from corposostenibile.extensions import redis_client
        if redis_client:
            key = f"teams_bot:pending:{conv_id}"
            val = redis_client.get(key)
            if val:
                redis_client.delete(key)
                return int(val)
            return None
    except Exception:
        logger.debug("Redis non disponibile per pending attachments")
    return None


# ─────────────────────── Process Activity ─────────────────────── #

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


# ─────────────────── RBAC: controllo accesso ticket ─────────────────── #

def _user_can_access_ticket(user, ticket) -> bool:
    """True se l'utente e' creatore, assegnatario, o ha messaggi nel ticket."""
    if not user:
        return False
    # Creatore
    if ticket.created_by_id == user.id:
        return True
    # Assegnatario
    if any(u.id == user.id for u in ticket.assigned_users):
        return True
    # Ha messaggi nel ticket
    from corposostenibile.models import TeamTicketMessage
    has_msg = (
        TeamTicketMessage.query
        .filter_by(ticket_id=ticket.id, sender_id=user.id)
        .first()
    )
    if has_msg:
        return True
    # Ha messaggi via AAD
    if user.teams_aad_object_id:
        has_teams_msg = (
            TeamTicketMessage.query
            .filter_by(ticket_id=ticket.id, teams_sender_aad_id=user.teams_aad_object_id)
            .first()
        )
        if has_teams_msg:
            return True
    return False


# ─────────────────── Microsoft Graph API: cerca utenti tenant ─────────── #

async def _get_graph_token() -> str | None:
    """Ottiene un token per Microsoft Graph API via client credentials (con cache)."""
    global _graph_token_cache

    # Check cache
    cached = _graph_token_cache.get("data")
    if cached and time.time() < cached.get("expires_at", 0):
        return cached["token"]

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
                    token = data.get("access_token")
                    if token:
                        # Cache per 55 minuti (token dura 60 min)
                        _graph_token_cache["data"] = {
                            "token": token,
                            "expires_at": time.time() + 55 * 60,
                        }
                    return token
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


# ─────────────────── Salva conversation ref per notifiche proattive ──── #

def _save_conversation_ref(turn_context, user) -> None:
    """Salva la conversation reference sull'utente per messaggi proattivi."""
    if not user:
        return
    try:
        from botbuilder.core import TurnContext as TC
        ref = TC.get_conversation_reference(turn_context.activity)
        ref_data = {
            "conversation": {
                "id": ref.conversation.id if ref.conversation else None,
                "tenant_id": getattr(ref.conversation, "tenant_id", None),
            },
            "service_url": ref.service_url,
            "channel_id": ref.channel_id,
            "bot": {
                "id": ref.bot.id if ref.bot else None,
                "name": ref.bot.name if ref.bot else None,
            },
        }
        # Scrivi solo se cambiata
        if user.teams_conversation_ref != ref_data:
            from corposostenibile.extensions import db
            user.teams_conversation_ref = ref_data
            db.session.commit()
            logger.debug("Aggiornata conversation ref per user %s", user.id)
    except Exception:
        logger.exception("Errore salvataggio conversation ref")


# ─────────────────── Riepilogo ticket utente ─────────────────── #

def _get_user_ticket_summary(turn_context) -> dict:
    """Recupera i ticket aperti dell'utente e le stats per la welcome card."""
    from corposostenibile.models import TeamTicket, TeamTicketStatusEnum, User
    from corposostenibile.blueprints.team_tickets.services.ticket_service import get_stats
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

    # Deduplicazione
    assigned_ids = {t.id for t in assigned}
    my_open = [t for t in my_open if t.id not in assigned_ids]

    # Stats
    stats = get_stats()

    return {
        "assigned_tickets": [t.to_dict() for t in assigned] if assigned else None,
        "my_open_tickets": [t.to_dict() for t in my_open] if my_open else None,
        "user_name": teams_user.get("name"),
        "stats": stats,
    }


# ─────────────────────── Handle Turn ─────────────────────── #

async def _handle_turn(turn_context) -> None:
    """Gestisce il turno di conversazione."""
    from botbuilder.schema import ActivityTypes
    from corposostenibile.blueprints.team_tickets.adaptive_cards.templates import (
        welcome_card,
        error_card,
    )

    activity = turn_context.activity

    # ── Salva conversation ref per notifiche proattive ──
    teams_user = _get_teams_user_info(turn_context)
    aad_id = teams_user.get("aad_id")
    user = _find_user_by_aad(aad_id) if aad_id else None
    if user:
        _save_conversation_ref(turn_context, user)

    # ── Invoke: typeahead search (Data.Query) ──
    if activity.type == "invoke" and activity.name == "application/search":
        await _handle_search_invoke(turn_context)
        return

    if activity.type == ActivityTypes.message:
        # Submit da Adaptive Card
        if activity.value:
            await _handle_card_submit(turn_context, activity.value)
            return

        # Controlla se ci sono allegati FILE reali
        real_files = _get_real_file_attachments(activity.attachments)
        if real_files:
            await _handle_file_attachments(turn_context, real_files)
            return

        # Messaggio di testo
        text = (activity.text or "").strip()
        if text:
            # Cerca match TT-XXXXXX per mostrare dettaglio diretto
            ticket_match = re.search(r"TT-\d{8}-\d{4}", text, re.IGNORECASE)
            if ticket_match:
                await _handle_ticket_search_by_number(turn_context, ticket_match.group(0))
                return

            # Ricerca generica
            if len(text) >= 3:
                await _handle_text_search(turn_context, text)
                return

        # Default: mostra welcome card con riepilogo
        summary = _get_user_ticket_summary(turn_context)
        await _send_card(turn_context, welcome_card(**summary))
        return

    elif activity.type == ActivityTypes.conversation_update:
        if activity.members_added:
            for member in activity.members_added:
                if member.id != activity.recipient.id:
                    summary = _get_user_ticket_summary(turn_context)
                    await _send_card(turn_context, welcome_card(**summary))


# ─────────────────────── Search helpers ─────────────────────── #

async def _handle_ticket_search_by_number(turn_context, ticket_number: str) -> None:
    """Mostra dettaglio ticket cercato per numero."""
    from corposostenibile.models import TeamTicket
    from corposostenibile.blueprints.team_tickets.adaptive_cards.templates import (
        ticket_detail_card,
        error_card,
    )

    ticket = TeamTicket.query.filter(
        TeamTicket.ticket_number.ilike(ticket_number)
    ).first()

    if ticket:
        await _send_card(
            turn_context,
            ticket_detail_card(ticket.to_dict(include_messages=True, include_attachments=True)),
        )
    else:
        await _send_card(turn_context, error_card(
            "Ticket non trovato",
            f"Nessun ticket con numero {ticket_number}",
        ))


async def _handle_text_search(turn_context, text: str) -> None:
    """Cerca ticket per testo e mostra risultati."""
    from corposostenibile.blueprints.team_tickets.services.ticket_service import list_tickets
    from corposostenibile.blueprints.team_tickets.adaptive_cards.templates import (
        ticket_list_card,
        welcome_card,
    )

    pagination = list_tickets(page=1, per_page=10, search=text)
    tickets = pagination.items

    if tickets:
        await _send_card(
            turn_context,
            ticket_list_card(
                [t.to_dict() for t in tickets],
                f"Risultati per \"{text[:30]}\"",
            ),
        )
    else:
        # Nessun risultato: mostra welcome
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
            from corposostenibile.blueprints.team_tickets.services.ticket_service import get_assignable_users
            db_users = get_assignable_users()
            query_lower = query_text.lower()
            results = [
                {"title": u["name"], "value": f"db:{u['id']}:{u['name']}"}
                for u in db_users
                if query_lower in u["name"].lower()
            ][:15]

    logger.info("Data.Query results: dataset=%s, count=%d", dataset, len(results))

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
    from corposostenibile.blueprints.team_tickets.adaptive_cards.templates import (
        error_card,
        success_card,
        ticket_detail_card,
    )

    conv_id = turn_context.activity.conversation.id if turn_context.activity.conversation else None
    ticket_id = _pop_pending_attachment(conv_id) if conv_id else None

    if not ticket_id:
        await _send_card(turn_context, error_card(
            "Nessun ticket selezionato",
            "Per allegare un file, prima crea un ticket o clicca 'Aggiungi Allegato' su un ticket esistente.",
        ))
        return

    from corposostenibile.models import TeamTicket
    ticket = TeamTicket.query.get(ticket_id)
    if not ticket:
        await _send_card(turn_context, error_card("Ticket non trovato", "Il ticket non esiste piu'."))
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
        # Mostra dettaglio ticket aggiornato
        await _send_card(
            turn_context,
            ticket_detail_card(ticket.to_dict(include_messages=True, include_attachments=True)),
        )
    else:
        await _send_card(turn_context, error_card(
            "Upload fallito",
            "Non sono riuscito a scaricare gli allegati.",
        ))


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


# ─────────────────────── WebSocket notification helper ─────────────────── #

def _emit_ticket_event(event: str, ticket) -> None:
    """Emette un evento WebSocket per notificare l'admin dashboard."""
    try:
        from corposostenibile.extensions import socketio
        socketio.emit(
            event,
            {"ticket": ticket.to_dict(), "timestamp": __import__("datetime").datetime.utcnow().isoformat()},
            namespace="/team-tickets",
            room="team_tickets_dashboard",
        )
    except Exception:
        logger.debug("WebSocket emit fallito per %s", event)


# ─────────────────────── Handle Card Submit ─────────────────────── #

async def _handle_card_submit(turn_context, value: dict) -> None:
    """Gestisce i submit delle Adaptive Cards."""
    from corposostenibile.blueprints.team_tickets.adaptive_cards.templates import (
        create_ticket_form,
        ticket_confirmation_card,
        ticket_list_card,
        ticket_detail_card,
        reply_form_card,
        close_confirmation_card,
        welcome_card,
        error_card,
        success_card,
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
    page = value.get("page", 1)

    # ── Home ──
    if action == "home":
        summary = _get_user_ticket_summary(turn_context)
        await _send_card(turn_context, welcome_card(**summary))

    elif action == "new_ticket":
        await _send_card(turn_context, create_ticket_form())

    elif action == "submit_ticket":
        title = value.get("title", "").strip()
        description = value.get("description", "").strip()
        priority = value.get("priority", "media")
        assignee_raw = value.get("assignee_id", "").strip()
        cliente_id_str = value.get("cliente_id", "").strip()

        if not description:
            await _send_card(turn_context, error_card(
                "Dati mancanti",
                "Descrizione obbligatoria. Riprova.",
            ))
            return

        cliente_id = None
        if cliente_id_str and cliente_id_str.isdigit():
            cliente_id = int(cliente_id_str)

        assignee_ids = []
        assignee_name = None
        if assignee_raw:
            assignee_ids, assignee_name = _parse_assignee_value(assignee_raw)

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

        ticket.teams_conversation_id = conv_id
        ticket.teams_activity_id = turn_context.activity.id
        db.session.commit()

        _emit_ticket_event("ticket_created", ticket)
        await _send_card(turn_context, ticket_confirmation_card(ticket.to_dict()))

    # ── Ticket Assegnati a Me (paginato) ──
    elif action == "tickets_assigned_to_me":
        user = _find_user_by_aad(aad_id) if aad_id else None
        if user:
            per_page = 10
            query = (
                TeamTicket.query
                .filter(TeamTicket.assigned_users.any(User.id == user.id))
                .order_by(TeamTicket.created_at.desc())
            )
            total = query.count()
            tickets = query.offset((page - 1) * per_page).limit(per_page + 1).all()
            has_next = len(tickets) > per_page
            tickets = tickets[:per_page]
        else:
            tickets = []
            has_next = False
        await _send_card(
            turn_context,
            ticket_list_card(
                [t.to_dict() for t in tickets],
                "Ticket Assegnati a Me",
                page=page,
                has_next=has_next,
                list_action="tickets_assigned_to_me",
            ),
        )

    # ── I Miei Ticket (merge di aperti + creati + gestiti, paginato) ──
    elif action == "tickets_mine":
        user = _find_user_by_aad(aad_id) if aad_id else None
        ticket_ids = set()

        if user:
            # Assegnati a me
            assigned = (
                TeamTicket.query
                .filter(TeamTicket.assigned_users.any(User.id == user.id))
                .with_entities(TeamTicket.id)
                .all()
            )
            ticket_ids.update(t.id for t in assigned)

            # Creati da me
            created = (
                TeamTicket.query
                .filter(TeamTicket.created_by_id == user.id)
                .with_entities(TeamTicket.id)
                .all()
            )
            ticket_ids.update(t.id for t in created)

        if aad_id:
            # Ticket dove ho scritto messaggi
            msg_tickets = (
                TeamTicketMessage.query
                .filter_by(teams_sender_aad_id=aad_id)
                .with_entities(TeamTicketMessage.ticket_id)
                .distinct()
                .all()
            )
            ticket_ids.update(t.ticket_id for t in msg_tickets)

        if conv_id:
            conv_tickets = (
                TeamTicket.query
                .filter_by(teams_conversation_id=conv_id)
                .with_entities(TeamTicket.id)
                .all()
            )
            ticket_ids.update(t.id for t in conv_tickets)

        per_page = 10
        if ticket_ids:
            query = (
                TeamTicket.query
                .filter(TeamTicket.id.in_(ticket_ids))
                .order_by(TeamTicket.updated_at.desc())
            )
            tickets = query.offset((page - 1) * per_page).limit(per_page + 1).all()
            has_next = len(tickets) > per_page
            tickets = tickets[:per_page]
        else:
            tickets = []
            has_next = False

        await _send_card(
            turn_context,
            ticket_list_card(
                [t.to_dict() for t in tickets],
                "I Miei Ticket",
                page=page,
                has_next=has_next,
                list_action="tickets_mine",
            ),
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
            await _send_card(turn_context, error_card("Ticket non trovato", "Il ticket richiesto non esiste."))

    elif action == "reply_ticket":
        ticket_id = value.get("ticket_id")
        ticket = TeamTicket.query.get(ticket_id)
        if ticket:
            ticket_data = ticket.to_dict(include_messages=True)
            await _send_card(turn_context, reply_form_card(
                ticket.id,
                ticket.ticket_number,
                title=ticket.title,
                last_messages=ticket_data.get("messages", [])[-3:],
            ))

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

            # Mostra dettaglio aggiornato invece di testo semplice
            ticket = TeamTicket.query.get(ticket_id)
            if ticket:
                _emit_ticket_event("ticket_updated", ticket)
                await _send_card(
                    turn_context,
                    ticket_detail_card(ticket.to_dict(include_messages=True, include_attachments=True)),
                )

    # ── Chiudi ticket (con conferma) ──
    elif action == "close_ticket":
        ticket_id = value.get("ticket_id")
        ticket = TeamTicket.query.get(ticket_id)
        if ticket:
            await _send_card(turn_context, close_confirmation_card(
                ticket.id,
                ticket.ticket_number,
                ticket.title or ticket.description[:80],
            ))

    elif action == "confirm_close_ticket":
        ticket_id = value.get("ticket_id")
        if ticket_id:
            from corposostenibile.blueprints.team_tickets.services.ticket_service import update_ticket
            user = _find_user_by_aad(aad_id) if aad_id else None
            ticket = update_ticket(
                ticket_id=ticket_id,
                changed_by_id=user.id if user else None,
                status="chiuso",
                source="teams",
            )
            _emit_ticket_event("ticket_status_changed", ticket)
            await _send_card(
                turn_context,
                ticket_detail_card(ticket.to_dict(include_messages=True, include_attachments=True)),
            )

    # ── Prendi in Carico ──
    elif action == "take_ticket":
        ticket_id = value.get("ticket_id")
        if ticket_id:
            user = _find_user_by_aad(aad_id) if aad_id else None
            creator_id = _resolve_teams_user_id(aad_id, teams_user.get("name"))
            ticket = TeamTicket.query.get(ticket_id)
            if ticket:
                from corposostenibile.blueprints.team_tickets.services.ticket_service import update_ticket
                # Auto-assegna l'utente e cambia stato
                current_assignee_ids = [u.id for u in ticket.assigned_users]
                if creator_id and creator_id not in current_assignee_ids:
                    current_assignee_ids.append(creator_id)
                ticket = update_ticket(
                    ticket_id=ticket_id,
                    changed_by_id=creator_id,
                    status="in_lavorazione",
                    assignee_ids=current_assignee_ids,
                    source="teams",
                )
                _emit_ticket_event("ticket_status_changed", ticket)
                await _send_card(
                    turn_context,
                    ticket_detail_card(ticket.to_dict(include_messages=True, include_attachments=True)),
                )

    # ── Segna Risolto ──
    elif action == "resolve_ticket":
        ticket_id = value.get("ticket_id")
        if ticket_id:
            from corposostenibile.blueprints.team_tickets.services.ticket_service import update_ticket
            user = _find_user_by_aad(aad_id) if aad_id else None
            ticket = update_ticket(
                ticket_id=ticket_id,
                changed_by_id=user.id if user else None,
                status="risolto",
                source="teams",
            )
            _emit_ticket_event("ticket_status_changed", ticket)
            await _send_card(
                turn_context,
                ticket_detail_card(ticket.to_dict(include_messages=True, include_attachments=True)),
            )

    # ── Riapri ──
    elif action == "reopen_ticket":
        ticket_id = value.get("ticket_id")
        if ticket_id:
            from corposostenibile.blueprints.team_tickets.services.ticket_service import update_ticket
            user = _find_user_by_aad(aad_id) if aad_id else None
            ticket = TeamTicket.query.get(ticket_id)
            # Risolto → in_lavorazione, Chiuso → aperto
            new_status = "in_lavorazione" if ticket and ticket.status.value == "risolto" else "aperto"
            ticket = update_ticket(
                ticket_id=ticket_id,
                changed_by_id=user.id if user else None,
                status=new_status,
                source="teams",
            )
            _emit_ticket_event("ticket_status_changed", ticket)
            await _send_card(
                turn_context,
                ticket_detail_card(ticket.to_dict(include_messages=True, include_attachments=True)),
            )

    elif action == "add_attachment":
        ticket_id = value.get("ticket_id")
        if ticket_id and conv_id:
            _set_pending_attachment(conv_id, ticket_id)
            ticket = TeamTicket.query.get(ticket_id)
            ticket_num = ticket.ticket_number if ticket else f"#{ticket_id}"
            await _send_card(turn_context, success_card(
                "Pronto per allegati",
                f"Invia i file come messaggio in questa chat. Li associo al ticket {ticket_num}.",
            ))

    # ── Knowledge Base ──
    elif action == "kb_chat":
        from corposostenibile.blueprints.team_tickets.adaptive_cards.templates import kb_chat_card
        doc_count, chunks_count = _get_kb_stats()
        await _send_card(turn_context, kb_chat_card(doc_count, chunks_count))

    elif action == "kb_ask":
        from corposostenibile.blueprints.team_tickets.adaptive_cards.templates import kb_response_card, kb_chat_card
        question = value.get("kb_question", "").strip()
        if not question:
            await _send_card(turn_context, error_card(
                "Domanda vuota",
                "Scrivi una domanda prima di cercare.",
            ))
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
            await _send_card(turn_context, error_card(
                "Errore Knowledge Base",
                "Verifica che Qdrant e Google API siano configurati correttamente.",
            ))

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
