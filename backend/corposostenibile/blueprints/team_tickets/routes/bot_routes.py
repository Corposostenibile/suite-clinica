"""
bot_routes.py
=============
Webhook endpoint per il Bot Framework (Microsoft Teams).
CSRF exempt (registrato nel __init__.py del blueprint).
"""

from __future__ import annotations

import asyncio
import logging

from flask import jsonify, request

from corposostenibile.blueprints.team_tickets import teams_bot_bp

logger = logging.getLogger(__name__)


@teams_bot_bp.route("/messages", methods=["POST"])
def teams_messages():
    """
    Riceve tutte le activity dal Bot Framework.
    Endpoint: POST /api/teams-bot/messages

    Per invoke activities (Data.Query typeahead), ritorna l'invoke response
    come body HTTP affinché Teams possa mostrare i risultati.
    """
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Invalid request body"}), 400

    auth_header = request.headers.get("Authorization", "")

    try:
        from corposostenibile.blueprints.team_tickets.services.teams_bot_service import process_activity

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(process_activity(body, auth_header))
        finally:
            loop.close()

        # Se c'è un invoke response (Data.Query typeahead), ritornalo come HTTP response
        if result is not None:
            logger.info("Invoke result type: %s, value type: %s", type(result).__name__, type(getattr(result, 'value', None)).__name__)
            # result è un Activity con type="invokeResponse" e value=InvokeResponse
            invoke_resp = getattr(result, "value", None)
            if invoke_resp and hasattr(invoke_resp, "body"):
                logger.info("Returning invoke response: status=%s, body keys=%s", invoke_resp.status, list((invoke_resp.body or {}).keys()))
                return jsonify(invoke_resp.body or {}), invoke_resp.status
            # Fallback: potrebbe essere un InvokeResponse diretto
            if hasattr(result, "body") and hasattr(result, "status"):
                logger.info("Returning direct invoke response: status=%s", result.status)
                return jsonify(result.body or {}), result.status
            logger.warning("Invoke result not recognized: %r", result)
        else:
            # Log per capire se l'invoke non ritorna nulla
            activity_type = body.get("type", "")
            if activity_type == "invoke":
                logger.warning("Invoke activity processed but result is None!")

        return jsonify({}), 200

    except ImportError:
        logger.warning("botbuilder-core non installato, Teams bot webhook ignora richiesta")
        return jsonify({"status": "bot_not_configured"}), 200
    except Exception:
        logger.exception("Errore nel processing dell'activity Teams")
        return jsonify({"error": "Internal error"}), 500
