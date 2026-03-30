"""
blueprints/ticket/routes.py
===========================

Route principali per la gestione dei ticket (richiede autenticazione).
"""

from __future__ import annotations

from datetime import datetime
from http import HTTPStatus
import json

from flask import (
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import and_, or_

from corposostenibile.extensions import db
from corposostenibile.models import (
    Department,
    Ticket,
    TicketComment,
    TicketStatusChange,
    TicketStatusEnum,
    TicketUrgencyEnum,
    TicketCategoryEnum,
    User,
)
from .timezone_utils import get_utc_now

from . import ticket_bp
from .forms import (
    AuthenticatedTicketForm,
    TicketAssignUsersForm,
    TicketCommentForm,
    TicketFilterForm,
    TicketShareForm,
    TicketStatusChangeForm,
)
from .permissions import (
    can_edit_ticket,
    can_share_ticket,
    can_view_ticket,
    can_delete_ticket,
    get_user_accessible_tickets_query,
)
from .services import TicketService, TicketKPIService
from .api_routes import apply_dashboard_filters


# ────────────────────────────────────────────────────────────────────
#  Crea nuovo ticket
# ────────────────────────────────────────────────────────────────────

@ticket_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    """Create route - HTML form deleted"""
    # This route has been removed - use API instead
    abort(404)


# ────────────────────────────────────────────────────────────────────
#  I miei ticket
# ────────────────────────────────────────────────────────────────────

@ticket_bp.route("/my-tickets")
@login_required
def my_tickets():
    """HTML form deleted"""
    abort(404)# ────────────────────────────────────────────────────────────────────
#  Dashboard
# ────────────────────────────────────────────────────────────────────

@ticket_bp.route("/")
@ticket_bp.route("/dashboard")
@login_required
def dashboard():
    """HTML form deleted"""
    abort(404)# ────────────────────────────────────────────────────────────────────
#  Dettaglio Ticket
# ────────────────────────────────────────────────────────────────────

@ticket_bp.route("/<int:ticket_id>")
@login_required
def detail():
    """HTML form deleted"""
    abort(404)# ────────────────────────────────────────────────────────────────────
#  Serve Allegato
# ────────────────────────────────────────────────────────────────────

@ticket_bp.route("/<int:ticket_id>/attachment")
@login_required
def serve_attachment(ticket_id: int):
    """Serve l'allegato del ticket in modo sicuro."""
    
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Verifica permessi di visualizzazione
    if not can_view_ticket(current_user, ticket):
        abort(HTTPStatus.FORBIDDEN)
    
    # Verifica che il ticket abbia un allegato
    if not ticket.has_attachment:
        abort(HTTPStatus.NOT_FOUND)
    
    try:
        import os
        from flask import send_from_directory, send_file
        
        # Ottieni il percorso base del progetto (corposostenibile-suite)
        # current_app.root_path è /home/devops/corposostenibile-suite/corposostenibile
        # quindi il parent è /home/devops/corposostenibile-suite
        project_root = os.path.dirname(current_app.root_path)
        
        # Costruisci il percorso completo della cartella uploads
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        
        # Se upload_folder è relativo, costruisci il path assoluto dal project root
        if not os.path.isabs(upload_folder):
            upload_folder = os.path.join(project_root, upload_folder.rstrip('/'))
        
        # Il path salvato è già relativo (es: "tickets/20250111-0001_documento.pdf")
        if ticket.attachment_path:
            full_path = os.path.join(upload_folder, ticket.attachment_path)
        else:
            # Fallback: usa solo attachment_filename
            full_path = os.path.join(upload_folder, 'tickets', ticket.attachment_filename)
        
        current_app.logger.info(f"Tentativo di servire file: {full_path}")
        current_app.logger.info(f"File esiste? {os.path.exists(full_path)}")
        
        if not os.path.exists(full_path):
            current_app.logger.error(f"File non trovato: {full_path}")
            current_app.logger.error(f"Upload folder: {upload_folder}")
            current_app.logger.error(f"Attachment path: {ticket.attachment_path}")
            current_app.logger.error(f"Attachment filename: {ticket.attachment_filename}")
            abort(HTTPStatus.NOT_FOUND)
        
        # Invia il file
        return send_file(
            full_path,
            as_attachment=False,  # False per permettere preview nel browser
            download_name=ticket.attachment_filename,
            mimetype=None  # Lascia che Flask determini il mimetype
        )
        
    except FileNotFoundError:
        current_app.logger.error(f"Allegato non trovato per ticket {ticket_id}: {ticket.attachment_path}")
        abort(HTTPStatus.NOT_FOUND)
    except Exception as e:
        current_app.logger.error(f"Errore nel servire allegato per ticket {ticket_id}: {str(e)}")
        abort(HTTPStatus.INTERNAL_SERVER_ERROR)


# ────────────────────────────────────────────────────────────────────
#  Cambio Stato
# ────────────────────────────────────────────────────────────────────

@ticket_bp.route("/attachment/<int:attachment_id>")
@login_required
def serve_attachment_new(attachment_id: int):
    """Serve un allegato del nuovo sistema multi-allegati."""
    from corposostenibile.models import TicketAttachment
    
    attachment = TicketAttachment.query.get_or_404(attachment_id)
    
    # Verifica permessi di visualizzazione tramite il ticket
    if not can_view_ticket(current_user, attachment.ticket):
        abort(HTTPStatus.FORBIDDEN)
    
    try:
        import os
        from flask import send_file
        
        # Ottieni il percorso base del progetto
        project_root = os.path.dirname(current_app.root_path)
        
        # Costruisci il percorso completo del file
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        
        if os.path.isabs(upload_folder):
            full_path = os.path.join(upload_folder, attachment.file_path)
        else:
            full_path = os.path.join(project_root, upload_folder, attachment.file_path)
        
        # Verifica che il file esista
        if not os.path.exists(full_path):
            current_app.logger.error(f"File non trovato: {full_path}")
            abort(HTTPStatus.NOT_FOUND)
        
        # Invia il file
        return send_file(
            full_path,
            as_attachment=False,  # False per permettere preview nel browser
            download_name=attachment.filename,
            mimetype=attachment.mime_type or None
        )
        
    except FileNotFoundError:
        current_app.logger.error(f"Allegato non trovato: {attachment.file_path}")
        abort(HTTPStatus.NOT_FOUND)
    except Exception as e:
        current_app.logger.error(f"Errore nel servire allegato {attachment_id}: {str(e)}")
        abort(HTTPStatus.INTERNAL_SERVER_ERROR)


@ticket_bp.route("/<int:ticket_id>/status", methods=["POST"])
@login_required
def change_status(ticket_id: int):
    """Cambia stato del ticket."""
    
    ticket = Ticket.query.get_or_404(ticket_id)
    
    if not can_edit_ticket(current_user, ticket):
        abort(HTTPStatus.FORBIDDEN)
    
    form = TicketStatusChangeForm(current_status=ticket.status)
    
    if form.validate_on_submit():
        try:
            # Usa il service per cambiare stato
            service = TicketService()
            service.change_status(
                ticket=ticket,
                new_status=TicketStatusEnum(form.new_status.data),
                changed_by=current_user,
                message=form.message.data,
                notify_requester=form.notify_requester.data
            )
            
            flash(f"Stato ticket cambiato in {form.new_status.data}", "success")
            
        except Exception as e:
            db.session.rollback()
            flash(f"Errore nel cambio stato: {str(e)}", "danger")
    
    return redirect(url_for("ticket.detail", ticket_id=ticket_id))


# ────────────────────────────────────────────────────────────────────
#  Assegnazione Utenti
# ────────────────────────────────────────────────────────────────────

@ticket_bp.route("/<int:ticket_id>/assign", methods=["POST"])
@login_required
def assign_users(ticket_id: int):
    """Assegna utenti al ticket (solo head e admin)."""
    
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Verifica permessi - solo admin o head del dipartimento
    from .permissions import is_department_head, get_assignable_users_for_ticket
    
    if not (current_user.is_admin or is_department_head(current_user, ticket.department)):
        abort(HTTPStatus.FORBIDDEN)
    
    # Ottieni utenti assegnabili
    assignable_users = get_assignable_users_for_ticket(current_user, ticket)
    
    form = TicketAssignUsersForm(
        assignable_users=assignable_users,
        current_assigned=ticket.assigned_users
    )
    
    if form.validate_on_submit():
        try:
            # Aggiorna utenti assegnati
            new_assigned_ids = form.assigned_users.data
            new_assigned_users = User.query.filter(User.id.in_(new_assigned_ids)).all() if new_assigned_ids else []
            
            # Traccia chi è stato aggiunto/rimosso
            old_ids = {u.id for u in ticket.assigned_users}
            new_ids = set(new_assigned_ids)
            added_ids = new_ids - old_ids
            removed_ids = old_ids - new_ids
            
            # Aggiorna assegnazioni
            ticket.assigned_users = new_assigned_users
            
            # Log nel commento
            changes = []
            if added_ids:
                added_users = User.query.filter(User.id.in_(added_ids)).all()
                added_names = [u.full_name for u in added_users]
                changes.append(f"Assegnato a: {', '.join(added_names)}")
            
            if removed_ids:
                removed_users = User.query.filter(User.id.in_(removed_ids)).all()
                removed_names = [u.full_name for u in removed_users]
                changes.append(f"Rimosso da: {', '.join(removed_names)}")
            
            if changes:
                comment = TicketComment(
                    ticket_id=ticket.id,
                    author_id=current_user.id,
                    content='\n'.join(changes),
                    is_internal=True
                )
                db.session.add(comment)
            
            db.session.commit()
            
            # Invia email di notifica agli utenti assegnati
            if added_ids:
                try:
                    service = TicketService()
                    added_users_objects = User.query.filter(User.id.in_(added_ids)).all()
                    service.send_assignment_notifications(
                        ticket=ticket,
                        assigned_users=new_assigned_users,
                        assigned_by=current_user,
                        added_users=added_users_objects
                    )
                except Exception as e:
                    current_app.logger.error(f"Errore invio notifiche assegnazione: {str(e)}")
            
            flash("Assegnazioni aggiornate con successo", "success")
            
        except Exception as e:
            db.session.rollback()
            flash(f"Errore nell'assegnazione: {str(e)}", "danger")
    
    return redirect(url_for("ticket.detail", ticket_id=ticket_id))


# ────────────────────────────────────────────────────────────────────
#  Condivisione
# ────────────────────────────────────────────────────────────────────

@ticket_bp.route("/<int:ticket_id>/share", methods=["POST"])
@login_required
def share(ticket_id: int):
    """Condividi ticket con altri dipartimenti."""
    
    ticket = Ticket.query.get_or_404(ticket_id)
    
    if not can_share_ticket(current_user, ticket):
        abort(HTTPStatus.FORBIDDEN)
    
    form = TicketShareForm(ticket=ticket)
    
    if form.validate_on_submit():
        try:
            # Usa il service per condividere
            service = TicketService()
            departments = Department.query.filter(
                Department.id.in_(form.department_ids.data)
            ).all()
            
            service.share_with_departments(
                ticket=ticket,
                departments=departments,
                shared_by=current_user,
                message=form.message.data
            )
            
            dept_names = ", ".join([d.name for d in departments])
            flash(f"Ticket condiviso con: {dept_names}", "success")
            
        except Exception as e:
            db.session.rollback()
            flash(f"Errore nella condivisione: {str(e)}", "danger")
    
    return redirect(url_for("ticket.detail", ticket_id=ticket_id))


@ticket_bp.route("/<int:ticket_id>/share-member", methods=["POST"])
@login_required
def share_member(ticket_id: int):
    """Condividi ticket con un membro specifico di un dipartimento."""
    
    ticket = Ticket.query.get_or_404(ticket_id)
    
    if not can_share_ticket(current_user, ticket):
        abort(HTTPStatus.FORBIDDEN)
    
    department_id = request.form.get('department_id', type=int)
    member_id = request.form.get('member_id', type=int)
    message = request.form.get('message', '')
    
    if not department_id or not member_id:
        flash("Devi selezionare sia il dipartimento che il membro", "danger")
        return redirect(url_for("ticket.detail", ticket_id=ticket_id))
    
    try:
        # Verifica che il dipartimento esista
        department = Department.query.get_or_404(department_id)
        
        # Verifica che il membro appartenga al dipartimento
        member = User.query.filter_by(
            id=member_id,
            department_id=department_id,
            is_active=True
        ).first()
        
        if not member:
            flash("Membro non valido per il dipartimento selezionato", "danger")
            return redirect(url_for("ticket.detail", ticket_id=ticket_id))
        
        # Condividi con il dipartimento se non già condiviso
        if department not in ticket.shared_departments and department.id != ticket.department_id:
            ticket.shared_departments.append(department)
        
        # Assegna al membro se non già assegnato
        if member not in ticket.assigned_users:
            ticket.assigned_users.append(member)
        
        db.session.commit()
        
        # Invia notifica email al membro
        try:
            service = TicketService()
            service.send_assignment_notifications(
                ticket=ticket,
                assigned_users=[member],
                assigned_by=current_user,
                added_users=[member]
            )
            
            # Notifica anche via email di condivisione con messaggio personalizzato
            if message:
                # TODO: Implementare email con messaggio personalizzato
                pass
                
        except Exception as e:
            current_app.logger.error(f"Errore invio notifiche: {str(e)}")
        
        flash(f"Ticket condiviso con {member.full_name} ({department.name})", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Errore nella condivisione: {str(e)}", "danger")
    
    return redirect(url_for("ticket.detail", ticket_id=ticket_id))


# ────────────────────────────────────────────────────────────────────
#  Commenti
# ────────────────────────────────────────────────────────────────────

@ticket_bp.route("/<int:ticket_id>/comment", methods=["POST"])
@login_required
def add_comment(ticket_id: int):
    """Aggiungi commento al ticket."""
    
    ticket = Ticket.query.get_or_404(ticket_id)
    
    if not can_view_ticket(current_user, ticket):
        abort(HTTPStatus.FORBIDDEN)
    
    form = TicketCommentForm()
    
    if form.validate_on_submit():
        comment = TicketComment(
            ticket_id=ticket_id,
            author_id=current_user.id,
            content=form.content.data,
            is_internal=True  # Sempre interno
        )
        
        db.session.add(comment)
        db.session.commit()
        
        # Invia notifiche email
        try:
            service = TicketService()
            service.send_comment_notifications(
                ticket=ticket,
                comment=comment,
                author=current_user
            )
        except Exception as e:
            current_app.logger.error(f"Errore invio notifiche commento: {str(e)}")
        
        flash("Nota aggiunta", "success")
    
    return redirect(url_for("ticket.detail", ticket_id=ticket_id))


# ────────────────────────────────────────────────────────────────────
#  Assegnazione
# ────────────────────────────────────────────────────────────────────

@ticket_bp.route("/<int:ticket_id>/assign", methods=["POST"])
@login_required
def assign(ticket_id: int):
    """Assegna ticket a un utente del dipartimento."""
    
    ticket = Ticket.query.get_or_404(ticket_id)
    
    if not can_edit_ticket(current_user, ticket):
        abort(HTTPStatus.FORBIDDEN)
    
    user_id = request.form.get('user_id', type=int)
    
    if user_id:
        # Verifica che l'utente sia del dipartimento giusto
        user = User.query.get_or_404(user_id)
        
        valid_departments = [ticket.department_id]
        valid_departments.extend([d.id for d in ticket.shared_departments])
        
        if user.department_id not in valid_departments:
            flash("L'utente deve appartenere a uno dei dipartimenti coinvolti", "danger")
            return redirect(url_for("ticket.detail", ticket_id=ticket_id))
        
        ticket.assigned_to_id = user_id
        
        # Se il ticket è nuovo, passalo automaticamente in lavorazione
        if ticket.status == TicketStatusEnum.nuovo:
            service = TicketService()
            service.change_status(
                ticket=ticket,
                new_status=TicketStatusEnum.in_lavorazione,
                changed_by=current_user,
                message=f"Ticket preso in carico da {user.full_name}",
                notify_requester=True
            )
    else:
        # Rimuovi assegnazione
        ticket.assigned_to_id = None
    
    db.session.commit()
    
    if user_id:
        flash(f"Ticket assegnato a {user.full_name}", "success")
    else:
        flash("Assegnazione rimossa", "info")
    
    return redirect(url_for("ticket.detail", ticket_id=ticket_id))


# ────────────────────────────────────────────────────────────────────
#  Eliminazione Ticket
# ────────────────────────────────────────────────────────────────────

@ticket_bp.route("/<int:ticket_id>/delete", methods=["POST"])
@login_required
def delete(ticket_id: int):
    """Elimina un ticket."""
    
    ticket = Ticket.query.get_or_404(ticket_id)
    
    if not can_delete_ticket(current_user, ticket):
        abort(HTTPStatus.FORBIDDEN)
    
    # Salva info per il messaggio
    ticket_number = ticket.ticket_number
    
    try:
        # Elimina tutti i record correlati (comments, status_changes, etc.)
        # grazie alle cascade definite nel modello
        db.session.delete(ticket)
        db.session.commit()
        
        flash(f"Ticket #{ticket_number} eliminato con successo", "success")
        return redirect(url_for("ticket.dashboard"))
        
    except Exception as e:
        db.session.rollback()
        flash(f"Errore durante l'eliminazione: {str(e)}", "danger")
        return redirect(url_for("ticket.detail", ticket_id=ticket_id))


# ────────────────────────────────────────────────────────────────────
#  KPI Dashboard
# ────────────────────────────────────────────────────────────────────

@ticket_bp.route("/kpi")
@login_required
def kpi_dashboard():
    """HTML form deleted"""
    abort(404)# ────────────────────────────────────────────────────────────────────
#  Report / Export
# ────────────────────────────────────────────────────────────────────

@ticket_bp.route("/debug-assignment")
@login_required
def debug_assignment():
    """DEBUG: Verifica assegnazioni ticket per l'utente corrente."""
    
    # Query diretta per i ticket assegnati
    assigned_tickets = Ticket.query.filter(
        Ticket.assigned_users.any(User.id == current_user.id)
    ).all()
    
    # Query diretta SQL per verificare la tabella di associazione
    from corposostenibile.extensions import db
    from sqlalchemy import text
    
    sql_result = db.session.execute(
        text("""
        SELECT t.id, t.ticket_number, t.title, t.status
        FROM tickets t
        JOIN ticket_assigned_users tau ON t.id = tau.ticket_id
        WHERE tau.user_id = :user_id
        """),
        {"user_id": current_user.id}
    ).fetchall()
    
    # Query tramite permissions
    from .permissions import get_user_accessible_tickets_query
    accessible_tickets = get_user_accessible_tickets_query(current_user).all()
    
    # Verifica se è head
    departments_led = Department.query.filter_by(head_id=current_user.id).all()
    
    # Prepara info debug
    debug_info = {
        'user': {
            'id': current_user.id,
            'email': current_user.email,
            'name': current_user.full_name,
            'is_admin': current_user.is_admin,
            'department': current_user.department.name if current_user.department else None,
            'department_id': current_user.department_id,
            'is_head': len(departments_led) > 0,
            'head_of_departments': [d.name for d in departments_led]
        },
        'assigned_tickets_orm': [
            {
                'id': t.id,
                'number': t.ticket_number,
                'title': t.title,
                'status': t.status.value,
                'assigned_users': [u.full_name for u in t.assigned_users]
            }
            for t in assigned_tickets
        ],
        'assigned_tickets_sql': [
            {
                'id': row[0],
                'number': row[1],
                'title': row[2],
                'status': row[3]
            }
            for row in sql_result
        ],
        'accessible_tickets': [
            {
                'id': t.id,
                'number': t.ticket_number,
                'title': t.title,
                'status': t.status.value,
                'department': t.department.name if t.department else None
            }
            for t in accessible_tickets
        ],
        'total_counts': {
            'assigned_via_orm': len(assigned_tickets),
            'assigned_via_sql': len(sql_result),
            'accessible': len(accessible_tickets)
        }
    }
    
    return f"""
    <html>
    <head><title>Debug Ticket Assignment</title></head>
    <body style="font-family: monospace; padding: 20px;">
        <h2>Debug Ticket Assignment for {current_user.email}</h2>
        <pre>{json.dumps(debug_info, indent=2)}</pre>
        <hr>
        <a href="/tickets/dashboard">Back to Dashboard</a>
    </body>
    </html>
    """


@ticket_bp.route("/stats-json")
@login_required
def stats_json():
    """Ritorna le stats in JSON per verificare i valori esatti."""
    base_query = get_user_accessible_tickets_query(current_user)
    
    # Usa lo stesso approccio del modello per calcolare overdue
    import pytz
    rome_tz = pytz.timezone('Europe/Rome')
    now_rome = datetime.now(rome_tz)
    # Converti in UTC per il confronto con il database (senza timezone info)
    now_utc = now_rome.astimezone(pytz.utc).replace(tzinfo=None)
    
    # Query per ticket aperti
    open_query = base_query.filter(Ticket.status != TicketStatusEnum.chiuso)
    
    # Conta ticket aperti
    open_tickets = open_query.count()
    
    # Conta ticket scaduti (solo tra quelli aperti E con due_date valida)
    overdue_tickets = open_query.filter(
        Ticket.due_date.isnot(None),
        Ticket.due_date < now_utc
    ).count()
    
    return jsonify({
        'timestamp': now_utc.isoformat(),
        'stats': {
            'open': open_tickets,
            'overdue': overdue_tickets
        },
        'message': f'Dovrebbe mostrare {open_tickets} aperti e {overdue_tickets} scaduti'
    })


@ticket_bp.route("/stats-check")
@login_required
def stats_check():
    """Verifica rapida delle statistiche con esempi."""
    
    # Query base
    base_query = get_user_accessible_tickets_query(current_user)
    now = get_utc_now()
    
    # Query per ticket aperti
    open_query = base_query.filter(Ticket.status != TicketStatusEnum.chiuso)
    
    # Calcoli
    total = base_query.count()
    open_tickets = open_query.count()
    closed_tickets = base_query.filter(Ticket.status == TicketStatusEnum.chiuso).count()
    
    # Overdue solo per ticket aperti e con due_date valida
    overdue_query = open_query.filter(
        Ticket.due_date < now,
        Ticket.due_date.isnot(None)
    )
    overdue = overdue_query.count()
    
    # Non scaduti
    not_overdue_query = open_query.filter(
        Ticket.due_date >= now
    )
    not_overdue = not_overdue_query.count()
    
    # Senza due_date  
    no_due_date_open = open_query.filter(
        Ticket.due_date.is_(None)
    ).count()
    
    # Prendi alcuni esempi
    overdue_examples = overdue_query.limit(3).all()
    not_overdue_examples = not_overdue_query.limit(3).all()
    
    html = f"""
    <html>
    <head><title>Stats Check</title></head>
    <body style="font-family: monospace; padding: 20px;">
        <h2>Verifica Statistiche Ticket</h2>
        <table border="1" cellpadding="10">
            <tr><td><b>Totale Ticket:</b></td><td>{total}</td></tr>
            <tr><td><b>Ticket Aperti:</b></td><td>{open_tickets}</td></tr>
            <tr><td><b>Ticket Chiusi:</b></td><td>{closed_tickets}</td></tr>
            <tr style="background: #fee2e2;"><td><b>Ticket Aperti Scaduti:</b></td><td>{overdue}</td></tr>
            <tr style="background: #d1fae5;"><td><b>Ticket Aperti Non Scaduti:</b></td><td>{not_overdue}</td></tr>
            <tr><td><b>Ticket Aperti Senza Scadenza:</b></td><td>{no_due_date_open}</td></tr>
            <tr><td><b>Data/Ora Attuale:</b></td><td>{now.strftime('%Y-%m-%d %H:%M:%S')} UTC</td></tr>
        </table>
        <br>
        <p><b>Verifica:</b> {open_tickets} (aperti) = {overdue} (scaduti) + {not_overdue} (non scaduti) + {no_due_date_open} (senza scadenza)</p>
        <p><b>Somma:</b> {overdue} + {not_overdue} + {no_due_date_open} = {overdue + not_overdue + no_due_date_open}</p>
        
        <h3>Esempi Ticket Scaduti:</h3>
        <table border="1" cellpadding="5">
            <tr><th>Numero</th><th>Titolo</th><th>Scadenza</th><th>Creato</th></tr>
    """
    
    for t in overdue_examples:
        html += f"""
            <tr>
                <td>#{t.ticket_number}</td>
                <td>{t.title[:30]}</td>
                <td style="color: red;">{t.due_date.strftime('%Y-%m-%d %H:%M') if t.due_date else 'N/A'}</td>
                <td>{t.created_at.strftime('%Y-%m-%d %H:%M')}</td>
            </tr>
        """
    
    html += """
        </table>
        
        <h3>Esempi Ticket Non Scaduti:</h3>
        <table border="1" cellpadding="5">
            <tr><th>Numero</th><th>Titolo</th><th>Scadenza</th><th>Creato</th></tr>
    """
    
    for t in not_overdue_examples:
        html += f"""
            <tr>
                <td>#{t.ticket_number}</td>
                <td>{t.title[:30]}</td>
                <td style="color: green;">{t.due_date.strftime('%Y-%m-%d %H:%M') if t.due_date else 'N/A'}</td>
                <td>{t.created_at.strftime('%Y-%m-%d %H:%M')}</td>
            </tr>
        """
    
    html += """
        </table>
        <hr>
        <a href="/tickets/dashboard">Torna alla Dashboard</a>
    </body>
    </html>
    """
    
    return html


@ticket_bp.route("/debug-stats")
@login_required
def debug_stats():
    """Debug statistiche ticket."""
    if not current_user.is_admin:
        abort(HTTPStatus.FORBIDDEN)
    
    from sqlalchemy import func
    
    # Query base
    base_query = get_user_accessible_tickets_query(current_user)
    
    # Analisi dettagliata
    total_tickets = base_query.count()
    
    # Tickets per stato
    tickets_by_status = db.session.query(
        Ticket.status,
        func.count(Ticket.id)
    ).filter(
        Ticket.id.in_(base_query.with_entities(Ticket.id))
    ).group_by(Ticket.status).all()
    
    # Tickets per urgenza  
    tickets_by_urgency = db.session.query(
        Ticket.urgency,
        func.count(Ticket.id)
    ).filter(
        Ticket.id.in_(base_query.with_entities(Ticket.id))
    ).group_by(Ticket.urgency).all()
    
    # Analisi scadenze
    now = get_utc_now()
    
    # Tickets con due_date NULL
    tickets_no_due_date = base_query.filter(
        Ticket.due_date.is_(None)
    ).count()
    
    # Tickets aperti
    open_tickets_query = base_query.filter(
        Ticket.status != TicketStatusEnum.chiuso
    )
    open_tickets = open_tickets_query.count()
    
    # Tickets aperti e scaduti
    overdue_open_tickets = open_tickets_query.filter(
        Ticket.due_date < now
    ).count()
    
    # Tickets aperti non ancora scaduti
    not_overdue_tickets = open_tickets_query.filter(
        Ticket.due_date >= now
    ).count()
    
    # Sample di ticket scaduti
    sample_overdue = open_tickets_query.filter(
        Ticket.due_date < now
    ).limit(5).all()
    
    # Sample di ticket non scaduti
    sample_not_overdue = open_tickets_query.filter(
        Ticket.due_date >= now
    ).limit(5).all()
    
    debug_info = {
        'summary': {
            'total_tickets': total_tickets,
            'open_tickets': open_tickets,
            'overdue_open_tickets': overdue_open_tickets,
            'not_overdue_tickets': not_overdue_tickets,
            'tickets_no_due_date': tickets_no_due_date,
            'current_time': now.isoformat()
        },
        'by_status': [
            {'status': status.value, 'count': count}
            for status, count in tickets_by_status
        ],
        'by_urgency': [
            {'urgency': urgency.value, 'count': count}
            for urgency, count in tickets_by_urgency
        ],
        'sample_overdue': [
            {
                'number': t.ticket_number,
                'title': t.title,
                'status': t.status.value,
                'urgency': t.urgency.value,
                'created_at': t.created_at.isoformat(),
                'due_date': t.due_date.isoformat() if t.due_date else None,
                'is_overdue': t.is_overdue
            }
            for t in sample_overdue
        ],
        'sample_not_overdue': [
            {
                'number': t.ticket_number,
                'title': t.title,
                'status': t.status.value,
                'urgency': t.urgency.value,
                'created_at': t.created_at.isoformat(),
                'due_date': t.due_date.isoformat() if t.due_date else None,
                'is_overdue': t.is_overdue
            }
            for t in sample_not_overdue
        ]
    }
    
    return jsonify(debug_info)


@ticket_bp.route("/report")
@login_required
def report():
    """HTML form deleted"""
    abort(404)
@ticket_bp.route('/message/<int:ticket_id>', methods=['POST'])
@login_required
def send_message(ticket_id):
    """
    Invia un messaggio nella chat di un ticket.
    """
    from corposostenibile.models import TicketMessage
    from corposostenibile.blueprints.ticket.forms import TicketMessageForm
    
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Verifica permessi: richiedente, assegnatario, membri dipartimenti coinvolti, admin
    can_send = False
    
    if current_user.is_admin:
        can_send = True
    elif ticket.created_by_id and ticket.created_by_id == current_user.id:
        can_send = True
    elif ticket.assigned_to_id and ticket.assigned_to_id == current_user.id:
        can_send = True
    elif current_user.department in ticket.all_involved_departments:
        can_send = True
    
    if not can_send:
        flash('Non hai i permessi per inviare messaggi in questo ticket.', 'danger')
        abort(403)
    
    # Non si può inviare messaggi in ticket chiusi
    if ticket.status == TicketStatusEnum.chiuso:
        flash('Non puoi inviare messaggi in un ticket chiuso.', 'warning')
        return redirect(url_for('ticket.detail', ticket_id=ticket.id))
    
    form = TicketMessageForm()
    
    if form.validate_on_submit():
        message = TicketMessage(
            ticket_id=ticket.id,
            sender_id=current_user.id,
            content=form.content.data,
            is_read=False
        )
        
        db.session.add(message)
        db.session.commit()
        
        # Invia notifica email a tutti i partecipanti (tranne il mittente)
        recipients = set()
        
        # Aggiungi il creatore del ticket (se è un utente interno)
        if ticket.created_by_id and ticket.created_by_id != current_user.id:
            if ticket.created_by and ticket.created_by.email:
                recipients.add(ticket.created_by)
                current_app.logger.info(f"Aggiungo creatore ticket alle notifiche: {ticket.created_by.email}")
        
        # Aggiungi tutti gli utenti assegnati (relazione many-to-many)
        for assigned_user in ticket.assigned_users:
            if assigned_user.id != current_user.id and assigned_user.email:
                recipients.add(assigned_user)
                current_app.logger.info(f"Aggiungo assegnatario ticket alle notifiche: {assigned_user.email}")
        
        # Invia email a tutti i destinatari
        from corposostenibile.blueprints.ticket.services import TicketEmailService
        email_service = TicketEmailService()
        
        current_app.logger.info(f"Invio notifiche a {len(recipients)} destinatari per messaggio nel ticket #{ticket.ticket_number}")
        
        for recipient in recipients:
            if recipient and recipient.email:
                try:
                    current_app.logger.info(f"Invio notifica email a: {recipient.email} per ticket #{ticket.ticket_number}")
                    success = email_service.send_message_notification(ticket, message, recipient)
                    if success:
                        current_app.logger.info(f"Email inviata con successo a {recipient.email}")
                    else:
                        current_app.logger.warning(f"Invio email fallito per {recipient.email}")
                except Exception as e:
                    current_app.logger.error(f"Errore invio email messaggio ticket a {recipient.email}: {e}")
            else:
                current_app.logger.warning(f"Destinatario senza email valida: {recipient}")
        
        if not recipients:
            current_app.logger.info(f"Nessun destinatario per le notifiche del ticket #{ticket.ticket_number} (mittente: {current_user.email})")
        
        flash('Messaggio inviato con successo!', 'success')
    else:
        flash('Errore nell\'invio del messaggio.', 'danger')
    
    return redirect(url_for('ticket.detail', ticket_id=ticket.id))


@ticket_bp.route('/message/<int:message_id>/read', methods=['POST'])
@login_required
def mark_message_read(message_id):
    """
    Marca un messaggio come letto.
    """
    from corposostenibile.models import TicketMessage
    
    message = TicketMessage.query.get_or_404(message_id)
    ticket = message.ticket
    
    # Verifica permessi
    can_mark = False
    
    if message.sender_id != current_user.id:  # Non è il mittente
        if current_user.is_admin:
            can_mark = True
        elif ticket.created_by_id and ticket.created_by_id == current_user.id:
            can_mark = True
        elif any(u.id == current_user.id for u in ticket.assigned_users):
            can_mark = True
        elif current_user.department in ticket.all_involved_departments:
            can_mark = True
    
    if not can_mark:
        flash('Non puoi marcare questo messaggio come letto.', 'danger')
        abort(403)
    
    # Marca come letto
    message.mark_as_read(current_user.id)
    flash('Messaggio marcato come letto.', 'success')
    
    return redirect(url_for('ticket.detail', ticket_id=ticket.id))


@ticket_bp.route('/messages/mark-all-read/<int:ticket_id>', methods=['POST'])
@login_required
def mark_all_messages_read(ticket_id):
    """
    Marca tutti i messaggi di un ticket come letti.
    """
    from corposostenibile.models import TicketMessage
    
    ticket = Ticket.query.get_or_404(ticket_id)
    
    # Verifica permessi
    can_mark = False
    
    if current_user.is_admin:
        can_mark = True
    elif ticket.created_by_id and ticket.created_by_id == current_user.id:
        can_mark = True
    elif any(u.id == current_user.id for u in ticket.assigned_users):
        can_mark = True
    elif current_user.department in ticket.all_involved_departments:
        can_mark = True
    
    if not can_mark:
        flash('Non hai i permessi per questa azione.', 'danger')
        abort(403)
    
    # Marca tutti i messaggi non letti (non inviati dall'utente corrente) come letti
    messages = TicketMessage.query.filter_by(
        ticket_id=ticket.id
    ).filter(
        TicketMessage.sender_id != current_user.id,
        ~TicketMessage.read_by.contains([current_user.id])
    ).all()
    
    count = 0
    for message in messages:
        message.mark_as_read(current_user.id)
        count += 1
    
    if count > 0:
        db.session.commit()
        flash(f'{count} messaggi marcati come letti.', 'success')
    else:
        flash('Nessun messaggio da marcare come letto.', 'info')
    
    return redirect(url_for('ticket.detail', ticket_id=ticket.id))