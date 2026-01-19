"""
Routes per il blueprint communications.
"""

from datetime import date
from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from sqlalchemy import desc

from corposostenibile.extensions import db
from corposostenibile.models import Communication, Department
from . import communications_bp
from .forms import CommunicationForm
from .services import CommunicationService
from .permissions import (
    can_create_communication,
    can_view_communication,
    can_view_all_communications,
    can_see_statistics,
    get_user_accessible_communications
)


@communications_bp.route('/')
@login_required
def index():
    """Lista delle comunicazioni ricevute dall'utente."""
    # Paginazione
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Query base per comunicazioni accessibili
    query = get_user_accessible_communications(current_user)
    
    # Escludi le comunicazioni inviate dall'utente stesso
    query = query.filter(Communication.author_id != current_user.id)
    
    # Ordina per data decrescente
    query = query.order_by(desc(Communication.created_at))
    
    # Paginazione
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    return render_template(
        'communications/index.html',
        communications=pagination.items,
        pagination=pagination,
        today=date.today()
    )


@communications_bp.route('/sent')
@login_required
def sent():
    """Lista delle comunicazioni inviate (per admin e head)."""
    # Solo admin e head possono vedere questa pagina
    if not can_create_communication(current_user):
        abort(403)
    
    # Paginazione
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Query base
    if current_user.is_admin:
        # Admin vedono tutte le comunicazioni
        query = Communication.query
    else:
        # Head vedono solo le proprie
        query = Communication.query.filter_by(author_id=current_user.id)
    
    # Ordina per data decrescente
    query = query.order_by(desc(Communication.created_at))
    
    # Paginazione
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    return render_template(
        'communications/sent.html',
        communications=pagination.items,
        pagination=pagination
    )


@communications_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Crea una nuova comunicazione."""
    # Verifica permessi
    if not can_create_communication(current_user):
        flash('Non hai i permessi per creare comunicazioni.', 'error')
        return redirect(url_for('communications.index'))
    
    form = CommunicationForm()
    
    if form.validate_on_submit():
        try:
            # Determina i dipartimenti destinatari
            is_for_all = hasattr(form, 'send_to_all') and form.send_to_all.data
            departments = []
            
            if not is_for_all:
                # Ottieni i dipartimenti selezionati
                dept_ids = form.departments.data
                departments = Department.query.filter(Department.id.in_(dept_ids)).all()
            
            # Crea la comunicazione
            communication = CommunicationService.create_communication(
                title=form.title.data,
                content=form.content.data,
                author=current_user,
                departments=departments,
                is_for_all=is_for_all
            )
            
            flash('Comunicazione inviata con successo!', 'success')
            return redirect(url_for('communications.sent'))
            
        except Exception as e:
            flash(f'Errore durante l\'invio: {str(e)}', 'error')
            db.session.rollback()
    
    return render_template(
        'communications/create.html',
        form=form
    )


@communications_bp.route('/<int:communication_id>')
@login_required
def detail(communication_id):
    """Visualizza il dettaglio di una comunicazione."""
    communication = Communication.query.get_or_404(communication_id)
    
    # Verifica permessi
    if not can_view_communication(current_user, communication):
        abort(403)
    
    # Verifica se l'utente ha già letto
    has_read = communication.has_read(current_user)
    
    # Mostra statistiche solo se autorizzato
    show_stats = can_see_statistics(current_user, communication)
    stats = None
    if show_stats:
        stats = CommunicationService.get_communication_stats(communication)
    
    return render_template(
        'communications/detail.html',
        communication=communication,
        has_read=has_read,
        show_stats=show_stats,
        stats=stats
    )


@communications_bp.route('/<int:communication_id>/mark-read', methods=['POST'])
@login_required
def mark_read(communication_id):
    """Marca una comunicazione come letta."""
    communication = Communication.query.get_or_404(communication_id)
    
    # Verifica permessi
    if not can_view_communication(current_user, communication):
        abort(403)
    
    # Marca come letta
    success = CommunicationService.mark_as_read(communication, current_user)
    
    if success:
        flash('Lettura confermata con successo.', 'success')
    else:
        flash('Hai già confermato la lettura di questa comunicazione.', 'info')
    
    return redirect(url_for('communications.detail', communication_id=communication_id))


@communications_bp.route('/<int:communication_id>/delete', methods=['POST'])
@login_required
def delete(communication_id):
    """Elimina una comunicazione."""
    communication = Communication.query.get_or_404(communication_id)
    
    # Solo l'autore o un admin possono eliminare
    if communication.author_id != current_user.id and not current_user.is_admin:
        flash('Non hai i permessi per eliminare questa comunicazione.', 'error')
        abort(403)
    
    try:
        db.session.delete(communication)
        db.session.commit()
        flash('Comunicazione eliminata con successo.', 'success')
        return redirect(url_for('communications.sent'))
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante l\'eliminazione: {str(e)}', 'error')
        return redirect(url_for('communications.detail', communication_id=communication_id))