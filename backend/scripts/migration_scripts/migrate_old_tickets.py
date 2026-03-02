#!/usr/bin/env python3
"""
migrate_old_tickets.py
======================
Migra i ticket dal vecchio sistema (tabella `tickets`) al nuovo sistema
Kanban Teams (tabella `team_tickets`).

Migra SOLO i ticket NON chiusi (nuovo, in_lavorazione, in_attesa).
I ticket chiusi restano nel vecchio sistema come archivio.
Ogni ticket viene committato singolarmente — un errore non blocca gli altri.
Idempotente: rilancia senza problemi, salta quelli già migrati.

Eseguire nel pod:
    PYTHONPATH=/app python /app/scripts/migration_scripts/migrate_old_tickets.py
"""

from __future__ import annotations

import os
import sys

# Setup Flask app context
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
os.environ.setdefault("FLASK_APP", "corposostenibile")

from corposostenibile import create_app

app = create_app()


def migrate_one_ticket(old, db, STATUS_MAP, PRIORITY_MAP, models):
    """Migra un singolo ticket. Ritorna (new_ticket_number, info_str) o solleva eccezione."""
    TeamTicket = models["TeamTicket"]
    TeamTicketMessage = models["TeamTicketMessage"]
    TeamTicketAttachment = models["TeamTicketAttachment"]
    TeamTicketStatusChange = models["TeamTicketStatusChange"]
    TeamTicketStatusEnum = models["TeamTicketStatusEnum"]
    TeamTicketPriorityEnum = models["TeamTicketPriorityEnum"]
    TeamTicketSourceEnum = models["TeamTicketSourceEnum"]
    team_ticket_assigned_users = models["team_ticket_assigned_users"]
    TicketComment = models["TicketComment"]
    TicketMessage = models["TicketMessage"]
    TicketAttachment = models["TicketAttachment"]
    OldStatusChange = models["OldStatusChange"]
    User = models["User"]

    # Determina creatore
    created_by_id = old.created_by_id
    if not created_by_id and old.requester_email:
        user = User.query.filter_by(email=old.requester_email).first()
        if user:
            created_by_id = user.id

    new_status = STATUS_MAP.get(old.status, TeamTicketStatusEnum.aperto)
    new_priority = PRIORITY_MAP.get(old.urgency, TeamTicketPriorityEnum.media)

    new_ticket = TeamTicket(
        ticket_number=TeamTicket.generate_ticket_number(),
        title=old.title,
        description=(
            f"{old.description}\n\n"
            f"---\n"
            f"[Migrato da {old.ticket_number}]\n"
            f"Richiedente: {old.requester_first_name} {old.requester_last_name} ({old.requester_email})"
        ),
        status=new_status,
        priority=new_priority,
        source=TeamTicketSourceEnum.admin,
        cliente_id=old.cliente_id,
        created_by_id=created_by_id,
        closed_at=old.closed_at,
    )
    new_ticket.created_at = old.created_at
    new_ticket.updated_at = old.updated_at

    db.session.add(new_ticket)
    db.session.flush()

    # Assegnatari
    assignee_ids = set()
    if old.assigned_to_id:
        assignee_ids.add(old.assigned_to_id)
    for u in old.assigned_users:
        assignee_ids.add(u.id)

    for uid in assignee_ids:
        db.session.execute(
            team_ticket_assigned_users.insert().values(
                ticket_id=new_ticket.id, user_id=uid,
            )
        )

    # Commenti → messaggi
    comments = (
        TicketComment.query.filter_by(ticket_id=old.id)
        .order_by(TicketComment.created_at.asc()).all()
    )
    for c in comments:
        msg = TeamTicketMessage(
            ticket_id=new_ticket.id, sender_id=c.author_id,
            content=c.content, source=TeamTicketSourceEnum.admin,
        )
        msg.created_at = c.created_at
        msg.updated_at = c.updated_at
        db.session.add(msg)

    # Messaggi chat
    messages = (
        TicketMessage.query.filter_by(ticket_id=old.id)
        .order_by(TicketMessage.created_at.asc()).all()
    )
    for m in messages:
        msg = TeamTicketMessage(
            ticket_id=new_ticket.id, sender_id=m.sender_id,
            content=m.content, source=TeamTicketSourceEnum.admin,
        )
        msg.created_at = m.created_at
        msg.updated_at = m.updated_at
        db.session.add(msg)

    # Allegato singolo legacy
    if old.attachment_filename and old.attachment_path:
        att = TeamTicketAttachment(
            ticket_id=new_ticket.id, filename=old.attachment_filename,
            file_path=old.attachment_path, file_size=0, mime_type=None,
            uploaded_by_id=created_by_id, source=TeamTicketSourceEnum.admin,
        )
        att.created_at = old.created_at
        db.session.add(att)

    # Allegati multipli
    old_attachments = (
        TicketAttachment.query.filter_by(ticket_id=old.id)
        .order_by(TicketAttachment.created_at.asc()).all()
    )
    for a in old_attachments:
        att = TeamTicketAttachment(
            ticket_id=new_ticket.id, filename=a.filename,
            file_path=a.file_path, file_size=a.file_size or 0,
            mime_type=a.mime_type, uploaded_by_id=a.uploaded_by_id,
            source=TeamTicketSourceEnum.admin,
        )
        att.created_at = a.created_at
        db.session.add(att)

    # Status changes
    old_changes = (
        OldStatusChange.query.filter_by(ticket_id=old.id)
        .order_by(OldStatusChange.created_at.asc()).all()
    )
    for sc in old_changes:
        from_s = STATUS_MAP.get(sc.from_status) if sc.from_status else None
        to_s = STATUS_MAP.get(sc.to_status, TeamTicketStatusEnum.aperto)
        new_sc = TeamTicketStatusChange(
            ticket_id=new_ticket.id, from_status=from_s,
            to_status=to_s, changed_by_id=sc.changed_by_id,
        )
        new_sc.created_at = sc.created_at
        db.session.add(new_sc)

    # COMMIT questo singolo ticket
    db.session.commit()

    n_msg = len(comments) + len(messages)
    n_att = len(old_attachments) + (1 if old.attachment_filename else 0)
    info = (f"[{old.status.value} → {new_status.value}]  "
            f"{len(assignee_ids)} assegnatari, {n_msg} messaggi, {n_att} allegati")
    return new_ticket.ticket_number, info


def migrate():
    from corposostenibile.extensions import db
    from corposostenibile.models import (
        Ticket, TicketStatusEnum, TicketUrgencyEnum,
        TicketComment, TicketMessage, TicketAttachment,
        TicketStatusChange as OldStatusChange,
        TeamTicket, TeamTicketMessage, TeamTicketAttachment,
        TeamTicketStatusChange, TeamTicketStatusEnum,
        TeamTicketPriorityEnum, TeamTicketSourceEnum,
        team_ticket_assigned_users, User,
    )

    models = {
        "TeamTicket": TeamTicket, "TeamTicketMessage": TeamTicketMessage,
        "TeamTicketAttachment": TeamTicketAttachment,
        "TeamTicketStatusChange": TeamTicketStatusChange,
        "TeamTicketStatusEnum": TeamTicketStatusEnum,
        "TeamTicketPriorityEnum": TeamTicketPriorityEnum,
        "TeamTicketSourceEnum": TeamTicketSourceEnum,
        "team_ticket_assigned_users": team_ticket_assigned_users,
        "TicketComment": TicketComment, "TicketMessage": TicketMessage,
        "TicketAttachment": TicketAttachment,
        "OldStatusChange": OldStatusChange, "User": User,
    }

    STATUS_MAP = {
        TicketStatusEnum.nuovo: TeamTicketStatusEnum.aperto,
        TicketStatusEnum.in_lavorazione: TeamTicketStatusEnum.in_lavorazione,
        TicketStatusEnum.in_attesa: TeamTicketStatusEnum.aperto,
        TicketStatusEnum.chiuso: TeamTicketStatusEnum.chiuso,
    }
    PRIORITY_MAP = {
        TicketUrgencyEnum.alta: TeamTicketPriorityEnum.alta,
        TicketUrgencyEnum.media: TeamTicketPriorityEnum.media,
        TicketUrgencyEnum.bassa: TeamTicketPriorityEnum.bassa,
    }

    open_statuses = [
        TicketStatusEnum.nuovo, TicketStatusEnum.in_lavorazione,
        TicketStatusEnum.in_attesa,
    ]
    old_tickets = Ticket.query.filter(Ticket.status.in_(open_statuses)).all()

    print(f"\n{'='*60}")
    print(f"  Migrazione ticket vecchio sistema -> Kanban Teams")
    print(f"{'='*60}")
    print(f"  Ticket aperti trovati: {len(old_tickets)}")

    if not old_tickets:
        print("  Nessun ticket da migrare. Fine.")
        return

    closed_count = Ticket.query.filter(Ticket.status == TicketStatusEnum.chiuso).count()
    print(f"  Ticket chiusi (non migrati): {closed_count}")
    print(f"  Ticket totali nel vecchio sistema: {Ticket.query.count()}")
    print()

    migrated = 0
    skipped = 0
    errors = []

    for i, old in enumerate(old_tickets):
        # Verifica se già migrato
        already = TeamTicket.query.filter(
            TeamTicket.description.contains(f"[Migrato da {old.ticket_number}]")
        ).first()
        if already:
            print(f"  SKIP {old.ticket_number} — già migrato come {already.ticket_number}")
            skipped += 1
            continue

        try:
            new_num, info = migrate_one_ticket(old, db, STATUS_MAP, PRIORITY_MAP, models)
            migrated += 1
            print(f"  OK  {old.ticket_number} → {new_num}  {info}")
        except Exception as e:
            db.session.rollback()
            errors.append((old.ticket_number, str(e)))
            print(f"  ERR {old.ticket_number} — {e}")

    print(f"\n{'='*60}")
    print(f"  RISULTATO")
    print(f"  Migrati:  {migrated}")
    print(f"  Saltati:  {skipped}")
    print(f"  Errori:   {len(errors)}")
    if errors:
        for tn, err in errors:
            print(f"    - {tn}: {err}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    with app.app_context():
        migrate()
