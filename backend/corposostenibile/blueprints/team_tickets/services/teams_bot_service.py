"""
teams_bot_service.py
====================
Bot Framework adapter per Microsoft Teams.
Il bot e' solo per:
1. Salutare e spiegare come usare la Kanban Board (tab)
2. Notifiche proattive per ticket propri/assegnati
Tutta la gestione ticket avviene nella tab Kanban.
"""

from __future__ import annotations

import logging

from flask import current_app

logger = logging.getLogger(__name__)


def _get_bot_config() -> dict:
    return {
        "app_id": current_app.config.get("TEAMS_BOT_APP_ID", ""),
        "app_password": current_app.config.get("TEAMS_BOT_APP_PASSWORD", ""),
        "tenant_id": current_app.config.get("TEAMS_BOT_TENANT_ID", ""),
    }


# ─────────────────────── Process Activity ─────────────────────── #

async def process_activity(body: dict, auth_header: str):
    """Processa un'activity in arrivo dal Bot Framework."""
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


# ─────────────────────── Handle Turn ─────────────────────── #

async def _handle_turn(turn_context) -> None:
    """Gestisce il turno di conversazione.

    Il bot risponde SOLO con la card di benvenuto che spiega
    come usare la Kanban Board nella tab Teams.
    """
    from botbuilder.schema import ActivityTypes
    from corposostenibile.blueprints.team_tickets.adaptive_cards.templates import (
        welcome_card,
    )

    activity = turn_context.activity

    # ── Salva conversation ref per notifiche proattive ──
    teams_user = _get_teams_user_info(turn_context)
    aad_id = teams_user.get("aad_id")
    user = _find_user_by_aad(aad_id) if aad_id else None
    if user:
        _save_conversation_ref(turn_context, user)

    if activity.type == ActivityTypes.message:
        # Qualsiasi messaggio → mostra guida Kanban Board
        user_name = teams_user.get("name")
        await _send_card(turn_context, welcome_card(user_name=user_name))
        return

    elif activity.type == ActivityTypes.conversation_update:
        if activity.members_added:
            for member in activity.members_added:
                if member.id != activity.recipient.id:
                    user_name = teams_user.get("name")
                    await _send_card(turn_context, welcome_card(user_name=user_name))


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


# ─────────────────────── User helpers ─────────────────────── #

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
