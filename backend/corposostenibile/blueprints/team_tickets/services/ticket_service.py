"""
ticket_service.py
=================
CRUD e business logic per i Team Ticket.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from flask import current_app
from sqlalchemy import or_, func, case, text
from werkzeug.utils import secure_filename

from corposostenibile.extensions import db
from corposostenibile.models import (
    TeamTicket,
    TeamTicketMessage,
    TeamTicketAttachment,
    TeamTicketStatusChange,
    TeamTicketStatusEnum,
    TeamTicketPriorityEnum,
    TeamTicketSourceEnum,
    User,
    Cliente,
    team_ticket_assigned_users,
)


UPLOAD_SUBDIR = "team_tickets"


def _upload_dir() -> Path:
    base = current_app.config.get("UPLOAD_FOLDER", str(Path(current_app.root_path).parent / "uploads"))
    p = Path(base) / UPLOAD_SUBDIR
    p.mkdir(parents=True, exist_ok=True)
    return p


# ─────────────────────────────── CREATE ──────────────────────────────── #

def create_ticket(
    description: str,
    created_by_id: int | None,
    priority: str = "media",
    source: str = "admin",
    assignee_ids: list[int] | None = None,
    cliente_id: int | None = None,
    files: list | None = None,
    title: str | None = None,
) -> TeamTicket:
    """Crea un nuovo team ticket."""
    ticket = TeamTicket(
        ticket_number=TeamTicket.generate_ticket_number(),
        title=title,
        description=description,
        status=TeamTicketStatusEnum.aperto,
        priority=TeamTicketPriorityEnum(priority),
        source=TeamTicketSourceEnum(source),
        cliente_id=cliente_id,
        created_by_id=created_by_id,
    )
    db.session.add(ticket)
    db.session.flush()  # per avere ticket.id

    # Assegnatari
    if assignee_ids:
        users = User.query.filter(User.id.in_(assignee_ids), User.is_active.is_(True)).all()
        ticket.assigned_users = users

    # Status change iniziale
    sc = TeamTicketStatusChange(
        ticket_id=ticket.id,
        from_status=None,
        to_status=TeamTicketStatusEnum.aperto,
        changed_by_id=created_by_id,
        message="Ticket creato",
        source=TeamTicketSourceEnum(source),
    )
    db.session.add(sc)

    # Allegati
    if files:
        for f in files:
            _save_attachment(ticket, f, created_by_id, source)

    db.session.commit()

    # ── Planner sync (outbound) ──
    try:
        from corposostenibile.blueprints.team_tickets.services.planner_sync_service import (
            sync_ticket_to_planner, is_syncing_from_planner,
        )
        if not is_syncing_from_planner():
            planner_task_id = sync_ticket_to_planner(ticket)
            if planner_task_id:
                ticket.planner_task_id = planner_task_id
                db.session.commit()
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Planner sync failed for new ticket %s", ticket.ticket_number)

    return ticket


# ─────────────────────────────── READ ────────────────────────────────── #

def get_ticket(ticket_id: int) -> TeamTicket | None:
    return TeamTicket.query.get(ticket_id)


def list_tickets(
    page: int = 1,
    per_page: int = 20,
    status: str | None = None,
    priority: str | None = None,
    assignee_id: int | None = None,
    cliente_id: int | None = None,
    search: str | None = None,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
):
    """Lista ticket paginata con filtri."""
    q = TeamTicket.query

    if status:
        q = q.filter(TeamTicket.status == TeamTicketStatusEnum(status))
    if priority:
        q = q.filter(TeamTicket.priority == TeamTicketPriorityEnum(priority))
    if assignee_id:
        q = q.filter(TeamTicket.assigned_users.any(User.id == assignee_id))
    if cliente_id:
        q = q.filter(TeamTicket.cliente_id == cliente_id)
    if search:
        pattern = f"%{search}%"
        q = q.filter(
            or_(
                TeamTicket.ticket_number.ilike(pattern),
                TeamTicket.title.ilike(pattern),
                TeamTicket.description.ilike(pattern),
            )
        )

    # Ordinamento
    col = getattr(TeamTicket, sort_by, TeamTicket.created_at)
    q = q.order_by(col.desc() if sort_dir == "desc" else col.asc())

    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    return pagination


# ─────────────────────────────── UPDATE ──────────────────────────────── #

def update_ticket(
    ticket_id: int,
    changed_by_id: int | None,
    status: str | None = None,
    priority: str | None = None,
    assignee_ids: list[int] | None = None,
    description: str | None = None,
) -> TeamTicket:
    """Aggiorna un team ticket."""
    ticket = TeamTicket.query.get_or_404(ticket_id)

    if description is not None:
        ticket.description = description

    if priority is not None:
        ticket.priority = TeamTicketPriorityEnum(priority)

    if status is not None:
        new_status = TeamTicketStatusEnum(status)
        if new_status != ticket.status:
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
                changed_by_id=changed_by_id,
                source=TeamTicketSourceEnum.admin,
            )
            db.session.add(sc)

    if assignee_ids is not None:
        users = User.query.filter(User.id.in_(assignee_ids), User.is_active.is_(True)).all()
        ticket.assigned_users = users
        _assignees_changed = True
    else:
        _assignees_changed = False

    db.session.commit()

    # ── Planner sync (outbound) ──
    try:
        from corposostenibile.blueprints.team_tickets.services.planner_sync_service import (
            sync_ticket_status_to_planner,
            sync_ticket_priority_to_planner,
            sync_ticket_assignees_to_planner,
            is_syncing_from_planner,
        )
        if not is_syncing_from_planner():
            if status is not None:
                sync_ticket_status_to_planner(ticket)
            if priority is not None:
                sync_ticket_priority_to_planner(ticket)
            if _assignees_changed:
                sync_ticket_assignees_to_planner(ticket)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Planner sync failed for ticket update %s", ticket.ticket_number)

    return ticket


# ─────────────────────────────── DELETE ──────────────────────────────── #

def delete_ticket(ticket_id: int) -> bool:
    ticket = TeamTicket.query.get_or_404(ticket_id)
    planner_task_id = ticket.planner_task_id
    db.session.delete(ticket)
    db.session.commit()

    # ── Planner sync (outbound) ──
    if planner_task_id:
        try:
            from corposostenibile.blueprints.team_tickets.services.planner_sync_service import (
                sync_ticket_delete_to_planner, is_syncing_from_planner,
            )
            if not is_syncing_from_planner():
                sync_ticket_delete_to_planner(planner_task_id)
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Planner sync failed for ticket delete %s", planner_task_id)

    return True


# ─────────────────────────── MESSAGES ────────────────────────────────── #

def add_message(
    ticket_id: int,
    sender_id: int | None,
    content: str,
    source: str = "admin",
) -> TeamTicketMessage:
    msg = TeamTicketMessage(
        ticket_id=ticket_id,
        sender_id=sender_id,
        content=content,
        source=TeamTicketSourceEnum(source),
    )
    db.session.add(msg)
    db.session.commit()

    # ── Planner sync (outbound) ──
    try:
        from corposostenibile.blueprints.team_tickets.services.planner_sync_service import (
            sync_message_to_planner, is_syncing_from_planner,
        )
        if not is_syncing_from_planner():
            ticket = TeamTicket.query.get(ticket_id)
            if ticket:
                sync_message_to_planner(ticket, msg)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Planner sync failed for message on ticket %s", ticket_id)

    return msg


def get_messages(ticket_id: int) -> list[TeamTicketMessage]:
    return (
        TeamTicketMessage.query
        .filter_by(ticket_id=ticket_id)
        .order_by(TeamTicketMessage.created_at.asc())
        .all()
    )


# ─────────────────────────── ATTACHMENTS ─────────────────────────────── #

def add_attachment(ticket_id: int, file, uploaded_by_id: int | None, source: str = "admin") -> TeamTicketAttachment:
    ticket = TeamTicket.query.get_or_404(ticket_id)
    att = _save_attachment(ticket, file, uploaded_by_id, source)
    db.session.commit()
    return att


def get_attachment(attachment_id: int) -> TeamTicketAttachment | None:
    return TeamTicketAttachment.query.get(attachment_id)


def _save_attachment(ticket: TeamTicket, file, uploaded_by_id: int | None, source: str) -> TeamTicketAttachment:
    """Salva un file allegato al ticket."""
    filename = secure_filename(file.filename)
    ticket_dir = _upload_dir() / str(ticket.id)
    ticket_dir.mkdir(parents=True, exist_ok=True)

    # Previeni collisioni di nomi
    dest = ticket_dir / filename
    counter = 1
    while dest.exists():
        stem, ext = os.path.splitext(filename)
        dest = ticket_dir / f"{stem}_{counter}{ext}"
        counter += 1

    file.save(str(dest))

    att = TeamTicketAttachment(
        ticket_id=ticket.id,
        filename=filename,
        file_path=str(dest.relative_to(_upload_dir().parent)),
        file_size=dest.stat().st_size,
        mime_type=file.content_type,
        uploaded_by_id=uploaded_by_id,
        source=TeamTicketSourceEnum(source),
    )
    db.session.add(att)
    return att


# ─────────────────────────── STATS ───────────────────────────────────── #

def get_stats() -> dict:
    """Statistiche per la dashboard."""
    total = TeamTicket.query.count()
    aperti = TeamTicket.query.filter_by(status=TeamTicketStatusEnum.aperto).count()
    in_lavorazione = TeamTicket.query.filter_by(status=TeamTicketStatusEnum.in_lavorazione).count()
    risolti = TeamTicket.query.filter_by(status=TeamTicketStatusEnum.risolto).count()
    chiusi = TeamTicket.query.filter_by(status=TeamTicketStatusEnum.chiuso).count()

    return {
        "total": total,
        "aperti": aperti,
        "in_lavorazione": in_lavorazione,
        "risolti": risolti,
        "chiusi": chiusi,
    }


# ─────────────────────────── ANALYTICS ─────────────────────────────── #

def get_analytics(days: int = 30) -> dict:
    """Statistiche avanzate per la pagina analytics."""
    cutoff = datetime.utcnow() - timedelta(days=days)

    # ── Tickets by day (trend) ──
    day_col = func.date_trunc("day", TeamTicket.created_at).label("day")
    tickets_created = (
        db.session.query(
            day_col,
            func.count(TeamTicket.id).label("created"),
        )
        .filter(TeamTicket.created_at >= cutoff)
        .group_by(day_col)
        .all()
    )

    resolved_day_col = func.date_trunc("day", TeamTicket.resolved_at).label("day")
    tickets_resolved = (
        db.session.query(
            resolved_day_col,
            func.count(TeamTicket.id).label("resolved"),
        )
        .filter(TeamTicket.resolved_at >= cutoff)
        .group_by(resolved_day_col)
        .all()
    )

    # Merge into a single list
    day_map: dict = {}
    for row in tickets_created:
        d = row.day.strftime("%Y-%m-%d") if row.day else None
        if d:
            day_map.setdefault(d, {"date": d, "created": 0, "resolved": 0})
            day_map[d]["created"] = row.created
    for row in tickets_resolved:
        d = row.day.strftime("%Y-%m-%d") if row.day else None
        if d:
            day_map.setdefault(d, {"date": d, "created": 0, "resolved": 0})
            day_map[d]["resolved"] = row.resolved

    tickets_by_day = sorted(day_map.values(), key=lambda x: x["date"])

    # ── Tickets by priority ──
    tickets_by_priority = [
        {"priority": row.priority.value, "count": row.cnt}
        for row in (
            db.session.query(
                TeamTicket.priority,
                func.count(TeamTicket.id).label("cnt"),
            )
            .filter(TeamTicket.created_at >= cutoff)
            .group_by(TeamTicket.priority)
            .all()
        )
    ]

    # ── Tickets by source ──
    tickets_by_source = [
        {"source": row.source.value, "count": row.cnt}
        for row in (
            db.session.query(
                TeamTicket.source,
                func.count(TeamTicket.id).label("cnt"),
            )
            .filter(TeamTicket.created_at >= cutoff)
            .group_by(TeamTicket.source)
            .all()
        )
    ]

    # ── Tickets by status (current snapshot, all tickets) ──
    tickets_by_status = [
        {"status": row.status.value, "count": row.cnt}
        for row in (
            db.session.query(
                TeamTicket.status,
                func.count(TeamTicket.id).label("cnt"),
            )
            .group_by(TeamTicket.status)
            .all()
        )
    ]

    # ── Average resolution hours ──
    avg_res = (
        db.session.query(
            func.avg(
                func.extract("epoch", TeamTicket.resolved_at - TeamTicket.created_at) / 3600
            )
        )
        .filter(TeamTicket.resolved_at.isnot(None))
        .filter(TeamTicket.created_at >= cutoff)
        .scalar()
    )
    avg_resolution_hours = round(float(avg_res), 1) if avg_res else 0

    # ── Average resolution by priority ──
    avg_resolution_by_priority = [
        {
            "priority": row.priority.value,
            "avg_hours": round(float(row.avg_h), 1) if row.avg_h else 0,
            "count": row.cnt,
        }
        for row in (
            db.session.query(
                TeamTicket.priority,
                func.avg(
                    func.extract("epoch", TeamTicket.resolved_at - TeamTicket.created_at) / 3600
                ).label("avg_h"),
                func.count(TeamTicket.id).label("cnt"),
            )
            .filter(TeamTicket.resolved_at.isnot(None))
            .filter(TeamTicket.created_at >= cutoff)
            .group_by(TeamTicket.priority)
            .all()
        )
    ]

    # ── Top assignees ──
    assignee_rows = (
        db.session.query(
            User.id,
            User.first_name,
            User.last_name,
            func.count(TeamTicket.id).label("total"),
            func.sum(
                case(
                    (TeamTicket.status.in_([
                        TeamTicketStatusEnum.aperto,
                        TeamTicketStatusEnum.in_lavorazione,
                    ]), 1),
                    else_=0,
                )
            ).label("open_count"),
            func.sum(
                case(
                    (TeamTicket.status.in_([
                        TeamTicketStatusEnum.risolto,
                        TeamTicketStatusEnum.chiuso,
                    ]), 1),
                    else_=0,
                )
            ).label("resolved_count"),
            func.avg(
                case(
                    (TeamTicket.resolved_at.isnot(None),
                     func.extract("epoch", TeamTicket.resolved_at - TeamTicket.created_at) / 3600),
                    else_=None,
                )
            ).label("avg_h"),
        )
        .join(team_ticket_assigned_users, team_ticket_assigned_users.c.user_id == User.id)
        .join(TeamTicket, TeamTicket.id == team_ticket_assigned_users.c.ticket_id)
        .filter(TeamTicket.created_at >= cutoff)
        .group_by(User.id, User.first_name, User.last_name)
        .order_by(func.count(TeamTicket.id).desc())
        .limit(10)
        .all()
    )

    top_assignees = [
        {
            "name": f"{r.first_name or ''} {r.last_name or ''}".strip(),
            "total": r.total,
            "open": r.open_count,
            "resolved": r.resolved_count,
            "avg_resolution_hours": round(float(r.avg_h), 1) if r.avg_h else None,
        }
        for r in assignee_rows
    ]

    # ── Recent activity (messages last 24h) ──
    recent_activity = (
        db.session.query(func.count(TeamTicketMessage.id))
        .filter(TeamTicketMessage.created_at >= datetime.utcnow() - timedelta(hours=24))
        .scalar()
    ) or 0

    # ── Total attachments ──
    total_attachments = (
        db.session.query(func.count(TeamTicketAttachment.id))
        .join(TeamTicket, TeamTicket.id == TeamTicketAttachment.ticket_id)
        .filter(TeamTicket.created_at >= cutoff)
        .scalar()
    ) or 0

    # ── Busiest day of week ──
    dow_rows = (
        db.session.query(
            func.extract("dow", TeamTicket.created_at).label("dow"),
            func.count(TeamTicket.id).label("cnt"),
        )
        .filter(TeamTicket.created_at >= cutoff)
        .group_by(text("1"))
        .order_by(func.count(TeamTicket.id).desc())
        .limit(1)
        .all()
    )

    day_names = {0: "Domenica", 1: "Lunedì", 2: "Martedì", 3: "Mercoledì",
                 4: "Giovedì", 5: "Venerdì", 6: "Sabato"}

    if dow_rows:
        dow_val = int(dow_rows[0].dow)
        busiest_day_of_week = {
            "day_name": day_names.get(dow_val, str(dow_val)),
            "count": dow_rows[0].cnt,
        }
    else:
        busiest_day_of_week = {"day_name": "-", "count": 0}

    return {
        "tickets_by_day": tickets_by_day,
        "tickets_by_priority": tickets_by_priority,
        "tickets_by_source": tickets_by_source,
        "tickets_by_status": tickets_by_status,
        "avg_resolution_hours": avg_resolution_hours,
        "avg_resolution_by_priority": avg_resolution_by_priority,
        "top_assignees": top_assignees,
        "recent_activity": recent_activity,
        "total_attachments": total_attachments,
        "busiest_day_of_week": busiest_day_of_week,
    }


# ─────────────────────────── USERS ───────────────────────────────────── #

def get_assignable_users() -> list[dict]:
    """Ritorna lista utenti attivi assegnabili ai ticket."""
    users = User.query.filter_by(is_active=True).order_by(User.first_name).all()
    return [
        {"id": u.id, "name": u.full_name, "avatar": u.avatar_path}
        for u in users
    ]


# ─────────────────────────── PATIENTS SEARCH ─────────────────────────── #

def search_patients(query: str, limit: int = 15) -> list[dict]:
    """Cerca pazienti per nome, email o telefono."""
    if not query or len(query) < 2:
        return []

    pattern = f"%{query}%"
    clienti = (
        Cliente.query
        .filter(
            or_(
                Cliente.nome_cognome.ilike(pattern),
                Cliente.mail.ilike(pattern),
                Cliente.numero_telefono.ilike(pattern),
            )
        )
        .limit(limit)
        .all()
    )
    return [
        {
            "id": c.cliente_id,
            "nome": c.nome_cognome,
            "email": c.mail,
            "telefono": c.numero_telefono,
        }
        for c in clienti
    ]
