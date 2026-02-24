"""
planner_sync_service.py
=======================
Two-way sync between TeamTicket and Microsoft Planner.

Outbound: ticket changes → Planner task CRUD
Inbound:  Planner webhook notifications → ticket changes

Uses synchronous ``requests`` (not aiohttp) for Graph API calls,
reusing the same Azure AD app registration as the Teams bot.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime

import requests
from flask import current_app

from corposostenibile.extensions import db
from corposostenibile.models import (
    PlannerSyncState,
    TeamTicket,
    TeamTicketMessage,
    TeamTicketSourceEnum,
    TeamTicketStatusEnum,
    TeamTicketPriorityEnum,
    TeamTicketStatusChange,
    User,
)

logger = logging.getLogger(__name__)

# ─────────────────────── Loop prevention (thread-local) ─────────────────── #
_sync_ctx = threading.local()


def is_syncing_from_planner() -> bool:
    return getattr(_sync_ctx, "syncing", False)


def set_syncing_from_planner(value: bool):
    _sync_ctx.syncing = value


# ─────────────────────── Config helpers ──────────────────────────────────── #

def _get_planner_config() -> dict:
    return {
        "enabled": current_app.config.get("PLANNER_SYNC_ENABLED", False),
        "plan_id": current_app.config.get("PLANNER_PLAN_ID", ""),
        "group_id": current_app.config.get("PLANNER_GROUP_ID", ""),
        "webhook_url": current_app.config.get("PLANNER_WEBHOOK_URL", ""),
        "webhook_secret": current_app.config.get("PLANNER_WEBHOOK_SECRET", "planner-sync-secret"),
        "app_id": current_app.config.get("TEAMS_BOT_APP_ID", ""),
        "app_password": current_app.config.get("TEAMS_BOT_APP_PASSWORD", ""),
        "tenant_id": current_app.config.get("TEAMS_BOT_TENANT_ID", ""),
    }


def _is_enabled() -> bool:
    cfg = _get_planner_config()
    return cfg["enabled"] and cfg["plan_id"] and cfg["app_id"]


# ─────────────────────── Graph token (sync) ──────────────────────────────── #

_token_cache: dict[str, str] = {}


def _get_graph_token_sync() -> str | None:
    """Obtain a Graph API token using client credentials (synchronous)."""
    if "access_token" in _token_cache:
        return _token_cache["access_token"]

    cfg = _get_planner_config()
    tenant_id = cfg["tenant_id"]
    if not tenant_id or not cfg["app_id"] or not cfg["app_password"]:
        return None

    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    try:
        resp = requests.post(token_url, data={
            "client_id": cfg["app_id"],
            "client_secret": cfg["app_password"],
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        }, timeout=15)
        if resp.status_code == 200:
            token = resp.json().get("access_token")
            _token_cache["access_token"] = token
            return token
        else:
            logger.warning("Graph token request failed: %s %s", resp.status_code, resp.text[:200])
    except Exception:
        logger.exception("Error obtaining Graph token")
    return None


def _graph_headers() -> dict:
    token = _get_graph_token_sync()
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"} if token else {}


# ─────────────────────── Bucket cache ────────────────────────────────────── #

STATUS_BUCKET_NAMES = {
    TeamTicketStatusEnum.aperto: "Aperto",
    TeamTicketStatusEnum.in_lavorazione: "In Lavorazione",
    TeamTicketStatusEnum.risolto: "Risolto",
    TeamTicketStatusEnum.chiuso: "Chiuso",
}

BUCKET_NAME_TO_STATUS = {v: k for k, v in STATUS_BUCKET_NAMES.items()}

_bucket_cache: dict[str, str] = {}  # status.value → bucket_id


def _ensure_buckets() -> dict[str, str]:
    """Ensure the 4 buckets exist in the Planner plan. Returns status→bucket_id map."""
    if _bucket_cache:
        return _bucket_cache

    cfg = _get_planner_config()
    plan_id = cfg["plan_id"]
    headers = _graph_headers()
    if not headers:
        return {}

    # Fetch existing buckets
    url = f"https://graph.microsoft.com/v1.0/planner/plans/{plan_id}/buckets"
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            logger.warning("Failed to fetch buckets: %s %s", resp.status_code, resp.text[:200])
            return {}
        existing = {b["name"]: b["id"] for b in resp.json().get("value", [])}
    except Exception:
        logger.exception("Error fetching Planner buckets")
        return {}

    # Create missing buckets
    for status_enum, bucket_name in STATUS_BUCKET_NAMES.items():
        if bucket_name in existing:
            _bucket_cache[status_enum.value] = existing[bucket_name]
        else:
            try:
                create_resp = requests.post(
                    "https://graph.microsoft.com/v1.0/planner/buckets",
                    headers=headers,
                    json={"name": bucket_name, "planId": plan_id},
                    timeout=15,
                )
                if create_resp.status_code in (200, 201):
                    _bucket_cache[status_enum.value] = create_resp.json()["id"]
                    logger.info("Created Planner bucket: %s", bucket_name)
                else:
                    logger.warning("Failed to create bucket %s: %s", bucket_name, create_resp.text[:200])
            except Exception:
                logger.exception("Error creating bucket %s", bucket_name)

    return _bucket_cache


def _bucket_id_to_status(bucket_id: str) -> TeamTicketStatusEnum | None:
    """Reverse-lookup: bucket_id → status enum."""
    buckets = _ensure_buckets()
    for status_val, bid in buckets.items():
        if bid == bucket_id:
            return TeamTicketStatusEnum(status_val)
    return None


# ─────────────────────── Priority mapping ────────────────────────────────── #

PRIORITY_TO_PLANNER = {
    TeamTicketPriorityEnum.alta: 1,
    TeamTicketPriorityEnum.media: 5,
    TeamTicketPriorityEnum.bassa: 9,
}

PLANNER_TO_PRIORITY = {v: k for k, v in PRIORITY_TO_PLANNER.items()}


# ═══════════════════════════════════════════════════════════════════════════ #
#                          OUTBOUND (Ticket → Planner)                       #
# ═══════════════════════════════════════════════════════════════════════════ #

def sync_ticket_to_planner(ticket: TeamTicket) -> str | None:
    """Create a Planner task for a new ticket. Returns planner_task_id or None."""
    if not _is_enabled() or is_syncing_from_planner():
        return None

    cfg = _get_planner_config()
    headers = _graph_headers()
    if not headers:
        return None

    buckets = _ensure_buckets()
    bucket_id = buckets.get(ticket.status.value)

    # Build title with prefix for loop detection
    title = f"[{ticket.ticket_number}] {ticket.title or ticket.description[:80]}"

    # Build assignments from ticket's assigned_users (need AAD IDs)
    assignments = {}
    for user in ticket.assigned_users:
        if user.teams_aad_object_id:
            assignments[user.teams_aad_object_id] = {"@odata.type": "#microsoft.graph.plannerAssignment", "orderHint": " !"}

    body = {
        "planId": cfg["plan_id"],
        "title": title,
        "priority": PRIORITY_TO_PLANNER.get(ticket.priority, 5),
        "assignments": assignments,
    }
    if bucket_id:
        body["bucketId"] = bucket_id

    try:
        resp = requests.post(
            "https://graph.microsoft.com/v1.0/planner/tasks",
            headers=headers,
            json=body,
            timeout=15,
        )
        if resp.status_code in (200, 201):
            task_data = resp.json()
            planner_task_id = task_data["id"]
            logger.info("Created Planner task %s for ticket %s", planner_task_id, ticket.ticket_number)

            # Set description via task details
            _update_task_description(planner_task_id, ticket)

            return planner_task_id
        else:
            logger.warning("Failed to create Planner task: %s %s", resp.status_code, resp.text[:300])
    except Exception:
        logger.exception("Error creating Planner task for ticket %s", ticket.ticket_number)
    return None


def _update_task_description(planner_task_id: str, ticket: TeamTicket):
    """Update task details with ticket description + conversation."""
    headers = _graph_headers()
    if not headers:
        return

    # Fetch current etag
    detail_url = f"https://graph.microsoft.com/v1.0/planner/tasks/{planner_task_id}/details"
    try:
        get_resp = requests.get(detail_url, headers=headers, timeout=15)
        if get_resp.status_code != 200:
            logger.warning("Failed to get task details: %s", get_resp.status_code)
            return
        etag = get_resp.json().get("@odata.etag", "")
    except Exception:
        logger.exception("Error fetching task details for %s", planner_task_id)
        return

    description = _build_description(ticket)

    patch_headers = {**headers, "If-Match": etag}
    try:
        resp = requests.patch(
            detail_url,
            headers=patch_headers,
            json={"description": description},
            timeout=15,
        )
        if resp.status_code not in (200, 204):
            logger.warning("Failed to update task description: %s %s", resp.status_code, resp.text[:200])
    except Exception:
        logger.exception("Error updating task description for %s", planner_task_id)


def _build_description(ticket: TeamTicket) -> str:
    """Build the full description field for a Planner task."""
    lines = [
        f"Ticket: {ticket.ticket_number}  |  Priorita: {ticket.priority.value}  |  Status: {ticket.status.value}",
    ]
    if ticket.cliente:
        lines.append(f"Paziente: {ticket.cliente.nome_cognome}")
    lines.append("")
    lines.append("--- Descrizione ---")
    lines.append(ticket.description or "")

    # Last 20 messages
    messages = (
        TeamTicketMessage.query
        .filter_by(ticket_id=ticket.id)
        .order_by(TeamTicketMessage.created_at.asc())
        .limit(20)
        .all()
    )
    if messages:
        lines.append("")
        lines.append("--- Conversazione ---")
        for msg in messages:
            ts = msg.created_at.strftime("%d/%m %H:%M") if msg.created_at else "?"
            sender = msg.sender.full_name if msg.sender else (msg.teams_sender_name or "?")
            lines.append(f"[{ts}] {sender}: {msg.content}")

    return "\n".join(lines)[:25000]  # Planner limit ~25KB


def sync_ticket_status_to_planner(ticket: TeamTicket):
    """Update the Planner task bucket and percent complete based on ticket status."""
    if not _is_enabled() or is_syncing_from_planner() or not ticket.planner_task_id:
        return

    headers = _graph_headers()
    if not headers:
        return

    buckets = _ensure_buckets()
    bucket_id = buckets.get(ticket.status.value)
    if not bucket_id:
        return

    # Get current etag
    task_url = f"https://graph.microsoft.com/v1.0/planner/tasks/{ticket.planner_task_id}"
    try:
        get_resp = requests.get(task_url, headers=headers, timeout=15)
        if get_resp.status_code != 200:
            logger.warning("Failed to get Planner task: %s", get_resp.status_code)
            return
        etag = get_resp.json().get("@odata.etag", "")
    except Exception:
        logger.exception("Error fetching Planner task %s", ticket.planner_task_id)
        return

    body: dict = {"bucketId": bucket_id}
    if ticket.status in (TeamTicketStatusEnum.chiuso, TeamTicketStatusEnum.risolto):
        body["percentComplete"] = 100
    else:
        body["percentComplete"] = 50 if ticket.status == TeamTicketStatusEnum.in_lavorazione else 0

    patch_headers = {**headers, "If-Match": etag}
    try:
        resp = requests.patch(task_url, headers=patch_headers, json=body, timeout=15)
        if resp.status_code not in (200, 204):
            logger.warning("Failed to update task status: %s %s", resp.status_code, resp.text[:200])
        else:
            logger.info("Synced status %s to Planner task %s", ticket.status.value, ticket.planner_task_id)
    except Exception:
        logger.exception("Error syncing status for task %s", ticket.planner_task_id)


def sync_ticket_priority_to_planner(ticket: TeamTicket):
    """Update the Planner task priority."""
    if not _is_enabled() or is_syncing_from_planner() or not ticket.planner_task_id:
        return

    headers = _graph_headers()
    if not headers:
        return

    task_url = f"https://graph.microsoft.com/v1.0/planner/tasks/{ticket.planner_task_id}"
    try:
        get_resp = requests.get(task_url, headers=headers, timeout=15)
        if get_resp.status_code != 200:
            return
        etag = get_resp.json().get("@odata.etag", "")
    except Exception:
        logger.exception("Error fetching Planner task %s", ticket.planner_task_id)
        return

    planner_priority = PRIORITY_TO_PLANNER.get(ticket.priority, 5)
    patch_headers = {**headers, "If-Match": etag}
    try:
        resp = requests.patch(task_url, headers=patch_headers, json={"priority": planner_priority}, timeout=15)
        if resp.status_code not in (200, 204):
            logger.warning("Failed to update task priority: %s %s", resp.status_code, resp.text[:200])
    except Exception:
        logger.exception("Error syncing priority for task %s", ticket.planner_task_id)


def sync_ticket_assignees_to_planner(ticket: TeamTicket):
    """Sync ticket assignees to Planner task assignments."""
    if not _is_enabled() or is_syncing_from_planner() or not ticket.planner_task_id:
        return

    headers = _graph_headers()
    if not headers:
        return

    task_url = f"https://graph.microsoft.com/v1.0/planner/tasks/{ticket.planner_task_id}"
    try:
        get_resp = requests.get(task_url, headers=headers, timeout=15)
        if get_resp.status_code != 200:
            return
        task_data = get_resp.json()
        etag = task_data.get("@odata.etag", "")
        current_assignments = task_data.get("assignments", {})
    except Exception:
        logger.exception("Error fetching Planner task %s", ticket.planner_task_id)
        return

    # Build desired assignments
    desired_aad_ids = {u.teams_aad_object_id for u in ticket.assigned_users if u.teams_aad_object_id}
    current_aad_ids = set(current_assignments.keys())

    if desired_aad_ids == current_aad_ids:
        return  # no change

    # Build diff: add new, remove old
    assignments_patch = {}
    for aad_id in desired_aad_ids - current_aad_ids:
        assignments_patch[aad_id] = {"@odata.type": "#microsoft.graph.plannerAssignment", "orderHint": " !"}
    for aad_id in current_aad_ids - desired_aad_ids:
        assignments_patch[aad_id] = None  # remove

    patch_headers = {**headers, "If-Match": etag}
    try:
        resp = requests.patch(task_url, headers=patch_headers, json={"assignments": assignments_patch}, timeout=15)
        if resp.status_code not in (200, 204):
            logger.warning("Failed to update task assignees: %s %s", resp.status_code, resp.text[:200])
    except Exception:
        logger.exception("Error syncing assignees for task %s", ticket.planner_task_id)


def sync_message_to_planner(ticket: TeamTicket, message: TeamTicketMessage):
    """Rebuild and update task description with the latest conversation."""
    if not _is_enabled() or is_syncing_from_planner() or not ticket.planner_task_id:
        return

    _update_task_description(ticket.planner_task_id, ticket)


def sync_ticket_delete_to_planner(planner_task_id: str):
    """Delete a Planner task when the ticket is deleted."""
    if not _is_enabled() or is_syncing_from_planner() or not planner_task_id:
        return

    headers = _graph_headers()
    if not headers:
        return

    task_url = f"https://graph.microsoft.com/v1.0/planner/tasks/{planner_task_id}"
    try:
        # Get etag first
        get_resp = requests.get(task_url, headers=headers, timeout=15)
        if get_resp.status_code != 200:
            return
        etag = get_resp.json().get("@odata.etag", "")

        delete_headers = {**headers, "If-Match": etag}
        resp = requests.delete(task_url, headers=delete_headers, timeout=15)
        if resp.status_code not in (200, 204):
            logger.warning("Failed to delete Planner task %s: %s", planner_task_id, resp.status_code)
        else:
            logger.info("Deleted Planner task %s", planner_task_id)
    except Exception:
        logger.exception("Error deleting Planner task %s", planner_task_id)


# ═══════════════════════════════════════════════════════════════════════════ #
#                          INBOUND (Planner → Ticket)                        #
# ═══════════════════════════════════════════════════════════════════════════ #

def handle_planner_change(resource_url: str, change_type: str):
    """Dispatcher for Planner webhook notifications."""
    if not _is_enabled():
        return

    # Extract task ID from resource URL, e.g. "planner/tasks/{id}"
    parts = resource_url.rstrip("/").split("/")
    if len(parts) < 2 or "tasks" not in parts:
        logger.warning("Unexpected Planner resource URL: %s", resource_url)
        return

    task_idx = parts.index("tasks")
    if task_idx + 1 >= len(parts):
        logger.warning("No task ID in resource URL: %s", resource_url)
        return
    planner_task_id = parts[task_idx + 1]

    set_syncing_from_planner(True)
    try:
        if change_type == "deleted":
            _handle_task_deleted(planner_task_id)
        else:
            # Fetch the task data from Graph
            headers = _graph_headers()
            if not headers:
                return
            task_url = f"https://graph.microsoft.com/v1.0/planner/tasks/{planner_task_id}"
            try:
                resp = requests.get(task_url, headers=headers, timeout=15)
                if resp.status_code != 200:
                    logger.warning("Failed to fetch task %s: %s", planner_task_id, resp.status_code)
                    return
                task_data = resp.json()
            except Exception:
                logger.exception("Error fetching Planner task %s", planner_task_id)
                return

            if change_type == "created":
                _handle_task_created(planner_task_id, task_data)
            elif change_type == "updated":
                _handle_task_updated(planner_task_id, task_data)
    finally:
        set_syncing_from_planner(False)


def _handle_task_created(planner_task_id: str, task_data: dict):
    """Handle a task created directly in Planner → create a ticket."""
    title = task_data.get("title", "")

    # Skip tasks created by us (title starts with [TT-)
    if title.startswith("[TT-"):
        return

    # Check if already linked
    existing = TeamTicket.query.filter_by(planner_task_id=planner_task_id).first()
    if existing:
        return

    cfg = _get_planner_config()
    # Only process tasks from our plan
    if task_data.get("planId") != cfg["plan_id"]:
        return

    # Determine status from bucket
    bucket_id = task_data.get("bucketId")
    status = _bucket_id_to_status(bucket_id) if bucket_id else TeamTicketStatusEnum.aperto

    # Determine priority
    planner_priority = task_data.get("priority", 5)
    priority = PLANNER_TO_PRIORITY.get(planner_priority, TeamTicketPriorityEnum.media)

    # Determine assignees from AAD IDs
    assignments = task_data.get("assignments", {})
    assignee_users = []
    for aad_id in assignments.keys():
        user = User.query.filter_by(teams_aad_object_id=aad_id).first()
        if user:
            assignee_users.append(user)

    ticket = TeamTicket(
        ticket_number=TeamTicket.generate_ticket_number(),
        title=title[:200] if title else None,
        description=title or "Task da Planner",
        status=status or TeamTicketStatusEnum.aperto,
        priority=priority,
        source=TeamTicketSourceEnum.planner,
        planner_task_id=planner_task_id,
    )
    db.session.add(ticket)
    db.session.flush()

    if assignee_users:
        ticket.assigned_users = assignee_users

    sc = TeamTicketStatusChange(
        ticket_id=ticket.id,
        from_status=None,
        to_status=ticket.status,
        changed_by_id=None,
        message="Ticket creato da Planner",
        source=TeamTicketSourceEnum.planner,
    )
    db.session.add(sc)
    db.session.commit()
    logger.info("Created ticket %s from Planner task %s", ticket.ticket_number, planner_task_id)


def _handle_task_updated(planner_task_id: str, task_data: dict):
    """Handle a task updated in Planner → sync changes to ticket."""
    ticket = TeamTicket.query.filter_by(planner_task_id=planner_task_id).first()
    if not ticket:
        return

    changed = False

    # Status from bucket
    bucket_id = task_data.get("bucketId")
    if bucket_id:
        new_status = _bucket_id_to_status(bucket_id)
        if new_status and new_status != ticket.status:
            old_status = ticket.status
            ticket.status = new_status

            if new_status == TeamTicketStatusEnum.risolto:
                ticket.resolved_at = datetime.utcnow()
            elif new_status == TeamTicketStatusEnum.chiuso:
                ticket.closed_at = datetime.utcnow()

            sc = TeamTicketStatusChange(
                ticket_id=ticket.id,
                from_status=old_status,
                to_status=new_status,
                changed_by_id=None,
                message="Status aggiornato da Planner",
                source=TeamTicketSourceEnum.planner,
            )
            db.session.add(sc)
            changed = True

    # Priority
    planner_priority = task_data.get("priority")
    if planner_priority is not None:
        new_priority = PLANNER_TO_PRIORITY.get(planner_priority)
        if new_priority and new_priority != ticket.priority:
            ticket.priority = new_priority
            changed = True

    # Percent complete → if 100%, mark as resolved/closed
    percent = task_data.get("percentComplete")
    if percent == 100 and ticket.status not in (TeamTicketStatusEnum.risolto, TeamTicketStatusEnum.chiuso):
        old_status = ticket.status
        ticket.status = TeamTicketStatusEnum.risolto
        ticket.resolved_at = datetime.utcnow()
        sc = TeamTicketStatusChange(
            ticket_id=ticket.id,
            from_status=old_status,
            to_status=TeamTicketStatusEnum.risolto,
            changed_by_id=None,
            message="Task completato in Planner",
            source=TeamTicketSourceEnum.planner,
        )
        db.session.add(sc)
        changed = True

    # Assignees
    assignments = task_data.get("assignments", {})
    planner_aad_ids = set(assignments.keys())
    current_aad_ids = {u.teams_aad_object_id for u in ticket.assigned_users if u.teams_aad_object_id}

    if planner_aad_ids != current_aad_ids:
        new_users = []
        for aad_id in planner_aad_ids:
            user = User.query.filter_by(teams_aad_object_id=aad_id).first()
            if user:
                new_users.append(user)
        if set(u.id for u in new_users) != set(u.id for u in ticket.assigned_users):
            ticket.assigned_users = new_users
            changed = True

    if changed:
        db.session.commit()
        logger.info("Updated ticket %s from Planner task %s", ticket.ticket_number, planner_task_id)


def _handle_task_deleted(planner_task_id: str):
    """Handle a task deleted in Planner → close the ticket."""
    ticket = TeamTicket.query.filter_by(planner_task_id=planner_task_id).first()
    if not ticket:
        return

    if ticket.status not in (TeamTicketStatusEnum.chiuso,):
        old_status = ticket.status
        ticket.status = TeamTicketStatusEnum.chiuso
        ticket.closed_at = datetime.utcnow()

        sc = TeamTicketStatusChange(
            ticket_id=ticket.id,
            from_status=old_status,
            to_status=TeamTicketStatusEnum.chiuso,
            changed_by_id=None,
            message="Task eliminato da Planner",
            source=TeamTicketSourceEnum.planner,
        )
        db.session.add(sc)
        db.session.commit()
        logger.info("Closed ticket %s (Planner task %s deleted)", ticket.ticket_number, planner_task_id)


# ═══════════════════════════════════════════════════════════════════════════ #
#                       SUBSCRIPTION MANAGEMENT                              #
# ═══════════════════════════════════════════════════════════════════════════ #

def create_planner_subscription() -> str | None:
    """Create a Graph subscription for Planner task changes. Returns subscription_id."""
    cfg = _get_planner_config()
    headers = _graph_headers()
    if not headers:
        return None

    from datetime import timedelta, timezone
    expiration = datetime.now(timezone.utc) + timedelta(days=2, hours=23)

    body = {
        "changeType": "created,updated,deleted",
        "notificationUrl": cfg["webhook_url"],
        "resource": f"/planner/plans/{cfg['plan_id']}/tasks",
        "expirationDateTime": expiration.isoformat(),
        "clientState": cfg["webhook_secret"],
    }

    try:
        resp = requests.post(
            "https://graph.microsoft.com/v1.0/subscriptions",
            headers=headers,
            json=body,
            timeout=30,
        )
        if resp.status_code in (200, 201):
            sub_data = resp.json()
            subscription_id = sub_data["id"]
            logger.info("Created Planner subscription: %s", subscription_id)

            # Persist to DB
            state = PlannerSyncState.query.first()
            if not state:
                state = PlannerSyncState(plan_id=cfg["plan_id"])
                db.session.add(state)
            state.subscription_id = subscription_id
            state.last_renewed_at = datetime.utcnow()
            db.session.commit()

            # Also cache in Redis if available
            try:
                from corposostenibile.extensions import redis_client
                if redis_client:
                    redis_client.setex("planner:subscription_id", 72 * 3600, subscription_id)
            except Exception:
                pass

            return subscription_id
        else:
            logger.warning("Failed to create subscription: %s %s", resp.status_code, resp.text[:300])
    except Exception:
        logger.exception("Error creating Planner subscription")
    return None


def renew_planner_subscription(subscription_id: str) -> bool:
    """Renew an existing Graph subscription. Returns True on success."""
    headers = _graph_headers()
    if not headers:
        return False

    from datetime import timedelta, timezone
    expiration = datetime.now(timezone.utc) + timedelta(days=2, hours=23)

    try:
        resp = requests.patch(
            f"https://graph.microsoft.com/v1.0/subscriptions/{subscription_id}",
            headers=headers,
            json={"expirationDateTime": expiration.isoformat()},
            timeout=15,
        )
        if resp.status_code in (200, 204):
            logger.info("Renewed Planner subscription: %s", subscription_id)

            state = PlannerSyncState.query.first()
            if state:
                state.last_renewed_at = datetime.utcnow()
                db.session.commit()
            return True
        else:
            logger.warning("Failed to renew subscription %s: %s %s", subscription_id, resp.status_code, resp.text[:200])
    except Exception:
        logger.exception("Error renewing Planner subscription %s", subscription_id)
    return False
