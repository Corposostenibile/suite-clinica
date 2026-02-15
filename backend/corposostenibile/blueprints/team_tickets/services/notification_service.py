"""
notification_service.py
=======================
Notifiche bidirezionali: admin → Teams e Teams → admin.
"""

from __future__ import annotations

import logging

from flask import current_app

from corposostenibile.models import User, TeamTicket

logger = logging.getLogger(__name__)


async def notify_teams_user(user: User, card: dict) -> bool:
    """
    Invia un messaggio proattivo a un utente Teams.
    Richiede che il user abbia teams_conversation_ref salvato.
    """
    if not user.teams_conversation_ref:
        logger.debug("User %s non ha conversation ref Teams", user.id)
        return False

    try:
        from botbuilder.core import (
            BotFrameworkAdapter,
            BotFrameworkAdapterSettings,
            TurnContext,
            CardFactory,
        )
        from botbuilder.schema import (
            Activity,
            ActivityTypes,
            ConversationReference,
            ConversationAccount,
            ChannelAccount,
        )
    except ImportError:
        logger.warning("botbuilder-core non installato")
        return False

    cfg = {
        "app_id": current_app.config.get("TEAMS_BOT_APP_ID", ""),
        "app_password": current_app.config.get("TEAMS_BOT_APP_PASSWORD", ""),
        "tenant_id": current_app.config.get("TEAMS_BOT_TENANT_ID", ""),
    }
    if not cfg["app_id"]:
        return False

    settings = BotFrameworkAdapterSettings(
        app_id=cfg["app_id"],
        app_password=cfg["app_password"],
        channel_auth_tenant=cfg["tenant_id"] or None,
    )
    adapter = BotFrameworkAdapter(settings)

    ref_data = user.teams_conversation_ref
    conv_ref = ConversationReference(
        conversation=ConversationAccount(
            id=ref_data["conversation"]["id"],
            tenant_id=ref_data["conversation"].get("tenant_id"),
        ),
        service_url=ref_data["service_url"],
        channel_id=ref_data.get("channel_id", "msteams"),
        bot=ChannelAccount(
            id=ref_data["bot"]["id"],
            name=ref_data["bot"].get("name"),
        ),
    )

    async def send_card(turn_context: TurnContext):
        activity = Activity(
            type=ActivityTypes.message,
            attachments=[CardFactory.adaptive_card(card)],
        )
        await turn_context.send_activity(activity)

    try:
        await adapter.continue_conversation(conv_ref, send_card, cfg["app_id"])
        return True
    except Exception:
        logger.exception("Errore invio messaggio proattivo Teams a user %s", user.id)
        return False


async def notify_ticket_assignees_teams(ticket: TeamTicket, card: dict):
    """Invia notifica Teams a tutti gli assegnatari del ticket."""
    for user in ticket.assigned_users:
        await notify_teams_user(user, card)
