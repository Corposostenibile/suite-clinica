"""
Route per il sistema di Review
"""

from flask import render_template, redirect, url_for, flash, request, abort, current_app, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import or_, and_, desc

from corposostenibile.blueprints.review import bp
from corposostenibile.blueprints.review.forms import (
    ReviewForm, AcknowledgmentForm, ReviewFilterForm, ReviewMessageForm,
    ReviewRequestForm, ReviewRequestResponseForm
)
from corposostenibile.blueprints.review.email_service import (
    send_review_notification, send_message_notification, 
    send_review_request_notification, send_review_request_response_notification
)
from corposostenibile.models import (
    User, Department, Review, ReviewAcknowledgment, ReviewMessage, ReviewRequest,
    UserRoleEnum,
)
from corposostenibile.extensions import db


def _is_cco_user(user) -> bool:
    specialty = getattr(user, 'specialty', None)
    if hasattr(specialty, 'value'):
        specialty = specialty.value
    return str(specialty).strip().lower() == 'cco' if specialty else False


def _is_admin_hr_or_cco(user) -> bool:
    return bool(
        user.is_admin
        or (hasattr(user, 'department_id') and user.department_id == 17)
        or _is_cco_user(user)
    )


def _get_led_team_member_ids(user):
    """Restituisce gli ID membri dei team guidati dall'utente (many-to-many), includendo sé stesso."""
    visible_ids = set()
    if not getattr(user, 'is_authenticated', False):
        return visible_ids

    visible_ids.add(user.id)
    for team in (getattr(user, 'teams_led', None) or []):
        for member in (getattr(team, 'members', None) or []):
            if getattr(member, 'id', None):
                visible_ids.add(member.id)
    return visible_ids


def can_view_member_reviews(user, member):
    """
    Verifica se un utente può vedere le review di un membro.
    - Admin: può vedere tutto
    - HR (department_id 17): può vedere tutto
    - Head: può vedere i membri del suo dipartimento
    - Head CCO (dept 23): può vedere membri di dept 2, 3, 4, 13
    - Team Leader Nutrizione: può vedere membri del proprio team
    - Membro: può vedere solo le proprie review
    - Eccezione speciale: User #2 può vedere review di User #64
    """
    from corposostenibile.models import Team

    # Admin o HR (department_id 17) possono vedere tutto
    if user.is_admin or (hasattr(user, 'department_id') and user.department_id == 17):
        return True

    # Se è il membro stesso
    if user.id == member.id:
        return True

    # Se è il capo del dipartimento del membro
    if member.department and member.department.head_id == user.id:
        return True

    # Head CCO (dept 23) può vedere membri dei dipartimenti 2, 3, 4, 13
    if member.department_id in [2, 3, 4, 13]:
        dept_cco = Department.query.filter_by(id=23).first()
        if dept_cco and dept_cco.head_id == user.id:
            return True

    # Team Leader: può vedere membri dei propri team (many-to-many)
    led_member_ids = _get_led_team_member_ids(user)
    if member.id in led_member_ids:
        return True

    # Fallback legacy (team_id diretto)
    if member.department_id == 2 and getattr(member, 'team_id', None):
        team = Team.query.get(member.team_id)
        if team and team.head_id == user.id:
            return True

    # Eccezione speciale: User #2 può vedere review di User #64
    if user.id == 2 and member.id == 64:
        return True

    # Eccezione speciale: User #79 e #64 possono vedersi reciprocamente
    if (user.id == 79 and member.id == 64) or (user.id == 64 and member.id == 79):
        return True

    return False


def can_write_review(user, member):
    """
    Verifica se un utente può scrivere una review a un membro.
    - Admin: può scrivere a tutti
    - HR (department_id 17): può scrivere a tutti
    - Head: può scrivere ai membri del suo dipartimento
    - Head CCO (dept 23): può scrivere a membri di dept 2, 3, 4, 13
    - Team Leader Nutrizione: può scrivere a membri del proprio team
    - Eccezione speciale: User #2 può scrivere review a User #64
    """
    from corposostenibile.models import Team

    # Admin o HR (department_id 17) possono scrivere a tutti
    if user.is_admin or (hasattr(user, 'department_id') and user.department_id == 17):
        return True

    # Se è il capo del dipartimento del membro
    if member.department and member.department.head_id == user.id:
        return True

    # Head CCO (dept 23) può scrivere a membri dei dipartimenti 2, 3, 4, 13
    if member.department_id in [2, 3, 4, 13]:
        dept_cco = Department.query.filter_by(id=23).first()
        if dept_cco and dept_cco.head_id == user.id:
            return True

    # Team Leader: può scrivere ai membri dei propri team (many-to-many)
    led_member_ids = _get_led_team_member_ids(user)
    if member.id in led_member_ids and member.id != user.id:
        return True

    # Fallback legacy (team_id diretto)
    if member.department_id == 2 and getattr(member, 'team_id', None):
        team = Team.query.get(member.team_id)
        if team and team.head_id == user.id:
            return True

    # Eccezione speciale: User #2 può scrivere review a User #64
    if user.id == 2 and member.id == 64:
        return True

    # Eccezione speciale: User #79 e #64 possono scriversi reciprocamente
    if (user.id == 79 and member.id == 64) or (user.id == 64 and member.id == 79):
        return True

    return False


def is_department_head(user):
    """Verifica se l'utente è capo di un dipartimento."""
    # Admin o HR (department_id 17) sono considerati come head
    if user.is_admin or (hasattr(user, 'department_id') and user.department_id == 17):
        return True
    
    department = Department.query.filter_by(head_id=user.id).first()
    return department is not None


@bp.route('/')
@login_required
def index():
    """
    Pagina principale delle review.
    - Admin: vede tutti i membri
    - Head: vede i membri del suo dipartimento
    - Membro: redirect al proprio detail
    """
    
    # Se non è admin, HR né head, mostra solo le proprie review
    if not (current_user.is_admin or current_user.department_id == 17) and not is_department_head(current_user):
        return redirect(url_for('review.detail', user_id=current_user.id))
    
    # Query base per i membri
    query = User.query.filter_by(is_active=True)
    
    # Filtro per dipartimento (solo per admin)
    selected_department_id = request.args.get('department_id', type=int)
    departments = []
    
    # Admin o HR possono filtrare per dipartimento
    if current_user.is_admin or current_user.department_id == 17:
        # Admin e HR possono filtrare per dipartimento
        departments = Department.query.order_by(Department.name).all()
        if selected_department_id:
            query = query.filter_by(department_id=selected_department_id)
    else:
        # Head vede solo il suo dipartimento
        department = Department.query.filter_by(head_id=current_user.id).first()
        if department:
            query = query.filter_by(department_id=department.id)
        else:
            # Non è head di nessun dipartimento, mostra solo se stesso
            return redirect(url_for('review.detail', user_id=current_user.id))
    
    # Ordina per nome
    members = query.order_by(User.first_name, User.last_name).all()
    
    # Conta le review per ogni membro
    members_data = []
    for member in members:
        total_reviews = Review.query.filter_by(
            reviewee_id=member.id,
            deleted_at=None,
            is_draft=False
        ).count()
        
        unread_reviews = Review.query.filter_by(
            reviewee_id=member.id,
            deleted_at=None,
            is_draft=False
        ).outerjoin(ReviewAcknowledgment).filter(
            ReviewAcknowledgment.id == None
        ).count()
        
        # Conta i messaggi non letti nelle review dove current_user è coinvolto con questo membro
        unread_messages = 0
        
        # Trova review dove current_user e member sono entrambi coinvolti
        relevant_reviews = Review.query.filter(
            or_(
                # Review scritte da current_user per member
                and_(Review.reviewer_id == current_user.id, Review.reviewee_id == member.id),
                # Review scritte da member per current_user  
                and_(Review.reviewer_id == member.id, Review.reviewee_id == current_user.id),
                # Se current_user è admin o HR, vede anche le review tra member e altri
                and_(or_(current_user.is_admin, current_user.department_id == 17),
                     or_(Review.reviewer_id == member.id, Review.reviewee_id == member.id))
            ),
            Review.deleted_at == None
        ).all()
        
        review_ids = [r.id for r in relevant_reviews]
        
        if review_ids:
            # Conta messaggi non letti in queste review (non inviati da current_user)
            unread_messages = ReviewMessage.query.filter(
                ReviewMessage.review_id.in_(review_ids),
                ReviewMessage.is_read == False,
                ReviewMessage.sender_id != current_user.id,
                ReviewMessage.deleted_at == None
            ).count()
        
        members_data.append({
            'member': member,
            'total_reviews': total_reviews,
            'unread_reviews': unread_reviews,
            'unread_messages': unread_messages
        })
    
    return render_template(
        'review/index.html',
        members_data=members_data,
        is_admin=(current_user.is_admin or current_user.department_id == 17),
        is_head=is_department_head(current_user),
        departments=departments,
        selected_department_id=selected_department_id
    )


@bp.route('/member/<int:user_id>')
@login_required
def detail(user_id):
    """
    Mostra il dettaglio delle review di un membro con paginazione.
    """
    
    member = User.query.get_or_404(user_id)
    
    # Verifica permessi
    if not can_view_member_reviews(current_user, member):
        flash('Non hai i permessi per visualizzare questi training.', 'danger')
        abort(403)
    
    # Form per filtri
    filter_form = ReviewFilterForm()
    
    # Query base per le review
    query = Review.query.filter_by(
        reviewee_id=member.id,
        deleted_at=None
    )
    
    # Se non è admin/HR e non è il reviewer, non mostra le bozze
    if not (current_user.is_admin or current_user.department_id == 17):
        query = query.filter(
            or_(
                Review.is_draft == False,
                Review.reviewer_id == current_user.id
            )
        )
    
    # Le review private sono visibili SOLO al reviewer e agli admin
    # NON al destinatario (reviewee)
    if not (current_user.is_admin or current_user.department_id == 17):
        query = query.filter(
            or_(
                Review.is_private == False,
                Review.reviewer_id == current_user.id
            )
        )
    
    # Applica filtri dal form
    if request.args.get('review_type') and request.args.get('review_type') != 'all':
        query = query.filter_by(review_type=request.args.get('review_type'))
    
    if request.args.get('status'):
        status = request.args.get('status')
        if status == 'acknowledged':
            query = query.join(ReviewAcknowledgment)
        elif status == 'pending':
            query = query.outerjoin(ReviewAcknowledgment).filter(ReviewAcknowledgment.id == None)
        elif status == 'draft':
            query = query.filter_by(is_draft=True)
    
    if request.args.get('period'):
        period = request.args.get('period')
        now = datetime.utcnow()
        if period == 'today':
            start_date = now.date()
        elif period == 'week':
            start_date = now - timedelta(days=7)
        elif period == 'month':
            start_date = now - timedelta(days=30)
        elif period == 'quarter':
            start_date = now - timedelta(days=90)
        elif period == 'year':
            start_date = now - timedelta(days=365)
        else:
            start_date = None
        
        if start_date:
            query = query.filter(Review.created_at >= start_date)
    
    # Ordina per data decrescente
    query = query.order_by(desc(Review.created_at))
    
    # Paginazione - 5 training per pagina
    page = request.args.get('page', 1, type=int)
    per_page = 5
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    reviews = pagination.items
    
    # Verifica se l'utente può scrivere review
    can_write = can_write_review(current_user, member)
    
    # Se è il membro stesso, crea il form di acknowledgment (escludi review private)
    ack_forms = {}
    if current_user.id == member.id:
        for review in reviews:
            if not review.is_acknowledged and not review.is_draft and not review.is_private:
                ack_forms[review.id] = AcknowledgmentForm()
    
    # Crea form per i messaggi per ogni review (se l'utente può partecipare alla chat)
    message_forms = {}
    messages_by_review = {}
    unread_counts = {}
    
    for review in reviews:
        # L'utente può chattare se è il reviewer, il reviewee o admin
        can_chat = (
            current_user.is_admin or
            current_user.department_id == 17 or
            current_user.id == review.reviewer_id or
            current_user.id == review.reviewee_id
        )
        
        if can_chat and not review.is_draft:
            message_forms[review.id] = ReviewMessageForm()
            
            # Carica i messaggi per questa review
            messages = ReviewMessage.query.filter_by(
                review_id=review.id,
                deleted_at=None
            ).order_by(ReviewMessage.created_at).all()
            messages_by_review[review.id] = messages
            
            # Conta messaggi non letti per questa review
            unread_count = ReviewMessage.query.filter_by(
                review_id=review.id,
                is_read=False,
                deleted_at=None
            ).filter(
                ReviewMessage.sender_id != current_user.id  # Non contare i propri messaggi
            ).count()
            unread_counts[review.id] = unread_count
    
    # Ottieni le richieste attive se è il profilo dell'utente corrente
    active_requests = []
    if current_user.id == member.id:
        active_requests = ReviewRequest.query.filter(
            ReviewRequest.requester_id == current_user.id,
            ReviewRequest.status.in_(['pending', 'accepted'])
        ).order_by(desc(ReviewRequest.created_at)).limit(3).all()
    
    return render_template(
        'review/detail.html',
        member=member,
        reviews=reviews,
        pagination=pagination,
        filter_form=filter_form,
        can_write=can_write,
        ack_forms=ack_forms,
        message_forms=message_forms,
        messages_by_review=messages_by_review,
        unread_counts=unread_counts,
        is_own_profile=(current_user.id == member.id),
        active_requests=active_requests
    )


@bp.route('/create/<int:user_id>', methods=['GET', 'POST'])
@login_required
def create(user_id):
    """
    Crea una nuova review per un membro.
    """
    
    member = User.query.get_or_404(user_id)
    
    # Verifica permessi
    if not can_write_review(current_user, member):
        flash('Non hai i permessi per scrivere training a questo utente.', 'danger')
        abort(403)
    
    # Non si può scrivere review a se stessi
    if current_user.id == member.id:
        flash('Non puoi scrivere un training a te stesso.', 'warning')
        return redirect(url_for('review.detail', user_id=user_id))
    
    form = ReviewForm()
    
    if form.validate_on_submit():
        review = Review(
            reviewer_id=current_user.id,
            reviewee_id=member.id,
            title=form.title.data,
            review_type=form.review_type.data,
            content=form.content.data,
            period_start=form.period_start.data,
            period_end=form.period_end.data,
            strengths=form.strengths.data,
            improvements=form.improvements.data,
            goals=form.goals.data,
            is_draft=False,  # Sempre pubblicata
            is_private=form.is_private.data
        )
        
        db.session.add(review)
        db.session.commit()
        
        # Invia notifica email al destinatario (solo se non è privata)
        if review.is_private:
            flash('Training privato creato con successo!', 'success')
        elif send_review_notification(review):
            flash('Training creato con successo! Una notifica è stata inviata al destinatario.', 'success')
        else:
            flash('Training creato con successo!', 'success')
        
        return redirect(url_for('review.detail', user_id=member.id))
    
    return render_template(
        'review/create.html',
        form=form,
        member=member
    )


@bp.route('/edit/<int:review_id>', methods=['GET', 'POST'])
@login_required
def edit(review_id):
    """
    Modifica una review esistente.
    """
    
    review = Review.query.get_or_404(review_id)
    
    # Solo admin, HR o il reviewer possono modificare
    if not (current_user.is_admin or current_user.department_id == 17) and review.reviewer_id != current_user.id:
        flash('Non hai i permessi per modificare questo training.', 'danger')
        abort(403)
    
    # Non si può modificare una review già confermata
    if review.is_acknowledged:
        flash('Non puoi modificare un training già confermato.', 'warning')
        return redirect(url_for('review.detail', user_id=review.reviewee_id))
    
    form = ReviewForm(obj=review)
    
    if form.validate_on_submit():
        review.title = form.title.data
        review.review_type = form.review_type.data
        review.content = form.content.data
        review.period_start = form.period_start.data
        review.period_end = form.period_end.data
        review.strengths = form.strengths.data
        review.improvements = form.improvements.data
        review.goals = form.goals.data
        review.is_private = form.is_private.data
        review.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash('Training aggiornato con successo!', 'success')
        return redirect(url_for('review.detail', user_id=review.reviewee_id))
    
    return render_template(
        'review/edit.html',
        form=form,
        review=review,
        member=review.reviewee
    )


@bp.route('/acknowledge/<int:review_id>', methods=['POST'])
@login_required
def acknowledge(review_id):
    """
    Conferma la lettura di una review.
    """
    
    review = Review.query.get_or_404(review_id)
    
    # Solo il destinatario può confermare
    if review.reviewee_id != current_user.id:
        flash('Non puoi confermare questo training.', 'danger')
        abort(403)
    
    # Verifica se già confermata
    if review.is_acknowledged:
        flash('Hai già confermato questo training.', 'info')
        return redirect(url_for('review.detail', user_id=current_user.id))
    
    form = AcknowledgmentForm()
    
    if form.validate_on_submit():
        acknowledgment = ReviewAcknowledgment(
            review_id=review.id,
            acknowledged_by=current_user.id,
            notes=form.notes.data,
            ip_address=request.remote_addr
        )
        
        db.session.add(acknowledgment)
        db.session.commit()
        
        flash('Lettura del training confermata!', 'success')
    
    return redirect(url_for('review.detail', user_id=current_user.id))


@bp.route('/delete/<int:review_id>', methods=['POST'])
@login_required
def delete(review_id):
    """
    Elimina una review (soft delete).
    """
    
    review = Review.query.get_or_404(review_id)
    
    # Solo admin, HR o il reviewer possono eliminare
    if not (current_user.is_admin or current_user.department_id == 17) and review.reviewer_id != current_user.id:
        flash('Non hai i permessi per eliminare questo training.', 'danger')
        abort(403)
    
    # Non si può eliminare una review già confermata (a meno di non essere admin o HR)
    if review.is_acknowledged and not (current_user.is_admin or current_user.department_id == 17):
        flash('Non puoi eliminare un training già confermato.', 'warning')
        return redirect(url_for('review.detail', user_id=review.reviewee_id))
    
    # Soft delete
    review.deleted_at = datetime.utcnow()
    db.session.commit()
    
    flash('Training eliminato con successo!', 'success')
    return redirect(url_for('review.detail', user_id=review.reviewee_id))


@bp.route('/message/<int:review_id>', methods=['POST'])
@login_required
def send_message(review_id):
    """
    Invia un messaggio nella chat di una review.
    """
    
    review = Review.query.get_or_404(review_id)
    
    # Verifica permessi: solo reviewer, reviewee, admin o HR possono inviare messaggi
    if not (current_user.is_admin or
            current_user.department_id == 17 or
            current_user.id == review.reviewer_id or
            current_user.id == review.reviewee_id):
        flash('Non hai i permessi per inviare messaggi in questo training.', 'danger')
        abort(403)
    
    # Non si può inviare messaggi in review cancellate
    if review.deleted_at:
        flash('Non puoi inviare messaggi in un training eliminato.', 'warning')
        return redirect(url_for('review.detail', user_id=review.reviewee_id))
    
    form = ReviewMessageForm()
    
    if form.validate_on_submit():
        message = ReviewMessage(
            review_id=review.id,
            sender_id=current_user.id,
            content=form.content.data,
            ip_address=request.remote_addr
        )
        
        db.session.add(message)
        db.session.commit()
        
        # Determina il destinatario per la notifica email
        if current_user.id == review.reviewer_id:
            recipient = review.reviewee
        else:
            recipient = review.reviewer
        
        # Invia notifica email
        if send_message_notification(message, recipient):
            flash('Messaggio inviato con successo!', 'success')
        else:
            flash('Messaggio inviato (email di notifica non disponibile).', 'info')
    else:
        flash('Errore nell\'invio del messaggio. Riprova.', 'danger')
    
    return redirect(url_for('review.detail', user_id=review.reviewee_id, _anchor=f'review-{review_id}-chat'))


@bp.route('/message/<int:message_id>/read', methods=['POST'])
@login_required
def mark_message_read(message_id):
    """
    Marca un messaggio come letto.
    """
    
    message = ReviewMessage.query.get_or_404(message_id)
    review = message.review
    
    # Solo il destinatario del messaggio può marcarlo come letto
    # Il destinatario è chi NON ha inviato il messaggio e può essere reviewer o reviewee
    can_mark_read = False
    
    if message.sender_id != current_user.id:  # Non è il mittente
        if current_user.id == review.reviewer_id or current_user.id == review.reviewee_id:
            can_mark_read = True
        elif current_user.is_admin or current_user.department_id == 17:
            can_mark_read = True
    
    if not can_mark_read:
        flash('Non puoi marcare questo messaggio come letto.', 'danger')
        abort(403)
    
    # Marca come letto
    if message.mark_as_read(current_user.id):
        db.session.commit()
        flash('Messaggio marcato come letto.', 'success')
    else:
        flash('Il messaggio è già stato letto.', 'info')
    
    return redirect(url_for('review.detail', user_id=review.reviewee_id, _anchor=f'review-{review.id}-chat'))


@bp.route('/messages/mark-all-read/<int:review_id>', methods=['POST'])
@login_required
def mark_all_messages_read(review_id):
    """
    Marca tutti i messaggi di una review come letti.
    """
    
    review = Review.query.get_or_404(review_id)
    
    # Verifica permessi
    if not (current_user.is_admin or
            current_user.department_id == 17 or
            current_user.id == review.reviewer_id or
            current_user.id == review.reviewee_id):
        flash('Non hai i permessi per questa azione.', 'danger')
        abort(403)
    
    # Marca tutti i messaggi non letti (non inviati dall'utente corrente) come letti
    messages = ReviewMessage.query.filter_by(
        review_id=review.id,
        is_read=False,
        deleted_at=None
    ).filter(
        ReviewMessage.sender_id != current_user.id
    ).all()
    
    count = 0
    for message in messages:
        if message.mark_as_read(current_user.id):
            count += 1
    
    if count > 0:
        db.session.commit()
        flash(f'{count} messaggi marcati come letti.', 'success')
    else:
        flash('Nessun nuovo messaggio da leggere.', 'info')
    
    return redirect(url_for('review.detail', user_id=review.reviewee_id, _anchor=f'review-{review_id}-chat'))


@bp.route('/stats')
@login_required
def stats():
    """
    Mostra statistiche sulle review (solo per admin).
    """
    
    # Solo admin o HR possono accedere
    if not (current_user.is_admin or current_user.department_id == 17):
        abort(403)
    
    # Statistiche generali
    total_reviews = Review.query.filter_by(deleted_at=None, is_draft=False).count()
    total_acknowledged = ReviewAcknowledgment.query.count()
    
    # Review per tipo
    reviews_by_type = db.session.query(
        Review.review_type,
        db.func.count(Review.id)
    ).filter_by(deleted_at=None, is_draft=False).group_by(Review.review_type).all()
    
    # Top reviewers
    top_reviewers = db.session.query(
        User,
        db.func.count(Review.id).label('count')
    ).join(Review, Review.reviewer_id == User.id).filter(
        Review.deleted_at == None,
        Review.is_draft == False
    ).group_by(User.id).order_by(desc('count')).limit(10).all()
    
    # Membri con più review
    top_reviewees = db.session.query(
        User,
        db.func.count(Review.id).label('count')
    ).join(Review, Review.reviewee_id == User.id).filter(
        Review.deleted_at == None,
        Review.is_draft == False
    ).group_by(User.id).order_by(desc('count')).limit(10).all()
    
    return render_template(
        'review/stats.html',
        total_reviews=total_reviews,
        total_acknowledged=total_acknowledged,
        reviews_by_type=reviews_by_type,
        top_reviewers=top_reviewers,
        top_reviewees=top_reviewees
    )


# ===================== ROUTES PER RICHIESTE TRAINING =====================

@bp.route('/request', methods=['GET', 'POST'])
@login_required
def request_training():
    """
    Permette agli utenti di richiedere un training al loro responsabile.

    Regole:
    - Professionista → SOLO il team leader del proprio team
    - Team leader → SOLO CCO (head dept 23)
    - Admin → tutti gli utenti attivi
    """
    # Usa helper centralizzato per i destinatari
    api_recipients = _get_training_recipients(current_user)

    # Converti formato API (id/name/role) → formato Jinja (user/label)
    possible_recipients = []
    for r in api_recipients:
        user_obj = User.query.get(r['id'])
        if user_obj:
            possible_recipients.append({
                'user': user_obj,
                'label': f"{r['name']} ({r['role']})" if r.get('role') else r['name']
            })

    if not possible_recipients:
        flash('Non è possibile inviare richieste di training al momento. Nessun responsabile configurato.', 'warning')
        return redirect(url_for('review.index'))

    form = ReviewRequestForm()

    # Se ci sono più destinatari possibili, aggiungiamo un campo di selezione
    if len(possible_recipients) > 1:
        choices = [(str(r['user'].id), r['label']) for r in possible_recipients]
        form.recipient_id.choices = choices
    else:
        form.recipient_id.choices = [(str(possible_recipients[0]['user'].id), possible_recipients[0]['label'])]
        form.recipient_id.data = str(possible_recipients[0]['user'].id)

    if form.validate_on_submit():
        # Determina il destinatario in base alla selezione o al default
        if len(possible_recipients) > 1:
            recipient_id = int(form.recipient_id.data)
        else:
            recipient_id = possible_recipients[0]['user'].id

        request = ReviewRequest(
            requester_id=current_user.id,
            requested_to_id=recipient_id,
            subject=form.subject.data,
            description=form.description.data,
            priority=form.priority.data,
            status='pending'
        )

        db.session.add(request)
        db.session.commit()

        # Trova il nome del destinatario per il messaggio flash
        recipient = User.query.get(recipient_id)

        # Invia notifica email
        if send_review_request_notification(request):
            flash(f'Richiesta di training inviata a {recipient.first_name} {recipient.last_name}!', 'success')
        else:
            flash('Richiesta inviata (notifica email non disponibile).', 'info')

        return redirect(url_for('review.my_requests'))

    return render_template(
        'review/request_training.html',
        form=form,
        possible_recipients=possible_recipients,
        multiple_recipients=(len(possible_recipients) > 1)
    )


@bp.route('/requests/my')
@login_required
def my_requests():
    """
    Mostra le richieste di training inviate dall'utente corrente.
    """
    
    requests = ReviewRequest.query.filter_by(
        requester_id=current_user.id
    ).order_by(desc(ReviewRequest.created_at)).all()
    
    return render_template(
        'review/my_requests.html',
        requests=requests
    )


@bp.route('/requests/received')
@login_required
def received_requests():
    """
    Mostra le richieste di training ricevute (per responsabili) con paginazione.
    """
    
    # Solo head, admin e HR possono vedere richieste ricevute
    if not (current_user.is_admin or current_user.department_id == 17) and not is_department_head(current_user):
        flash('Non hai i permessi per visualizzare questa pagina.', 'danger')
        abort(403)
    
    # Query base
    query = ReviewRequest.query.filter_by(requested_to_id=current_user.id)
    
    # Filtro per stato
    status_filter = request.args.get('status', 'pending')
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    # Ordina per data e priorità
    query = query.order_by(
        ReviewRequest.priority.desc(),  # Urgenti prima
        desc(ReviewRequest.created_at)
    )
    
    # Paginazione - 5 richieste per pagina
    page = request.args.get('page', 1, type=int)
    per_page = 5
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    requests = pagination.items
    
    # Conta richieste per stato (per i badge)
    pending_count = ReviewRequest.query.filter_by(
        requested_to_id=current_user.id,
        status='pending'
    ).count()
    
    accepted_count = ReviewRequest.query.filter_by(
        requested_to_id=current_user.id,
        status='accepted'
    ).count()
    
    completed_count = ReviewRequest.query.filter_by(
        requested_to_id=current_user.id,
        status='completed'
    ).count()
    
    rejected_count = ReviewRequest.query.filter_by(
        requested_to_id=current_user.id,
        status='rejected'
    ).count()
    
    total_count = pending_count + accepted_count + completed_count + rejected_count
    
    return render_template(
        'review/received_requests.html',
        requests=requests,
        pagination=pagination,
        status_filter=status_filter,
        pending_count=pending_count,
        accepted_count=accepted_count,
        completed_count=completed_count,
        rejected_count=rejected_count,
        total_count=total_count,
        timedelta=timedelta
    )


@bp.route('/request/<int:request_id>/respond', methods=['GET', 'POST'])
@login_required
def respond_request(request_id):
    """
    Permette al responsabile di rispondere a una richiesta di training.
    """
    
    training_request = ReviewRequest.query.get_or_404(request_id)
    
    # Verifica permessi
    if training_request.requested_to_id != current_user.id and not (current_user.is_admin or current_user.department_id == 17):
        flash('Non hai i permessi per rispondere a questa richiesta.', 'danger')
        abort(403)
    
    # Non si può rispondere a richieste già gestite
    if training_request.status != 'pending':
        flash('Questa richiesta è già stata gestita.', 'info')
        return redirect(url_for('review.received_requests'))
    
    form = ReviewRequestResponseForm()
    
    if form.validate_on_submit():
        action = form.action.data
        training_request.response_notes = form.response_notes.data
        training_request.responded_at = datetime.utcnow()
        
        if action == 'accept':
            training_request.status = 'accepted'
            db.session.commit()
            
            # Reindirizza alla creazione del training
            flash('Richiesta accettata! Ora puoi scrivere il training.', 'success')
            return redirect(url_for(
                'review.create_from_request',
                request_id=training_request.id
            ))
        else:  # reject
            training_request.status = 'rejected'
            db.session.commit()
            
            # Invia notifica di rifiuto
            try:
                send_review_request_response_notification(training_request)
            except Exception as e:
                current_app.logger.warning(f"Failed to send request response notification: {e}")
            flash('Richiesta rifiutata.', 'info')
            return redirect(url_for('review.received_requests'))
    
    return render_template(
        'review/respond_request.html',
        form=form,
        request=training_request
    )


@bp.route('/request/<int:request_id>/create-training', methods=['GET', 'POST'])
@login_required
def create_from_request(request_id):
    """
    Crea un training da una richiesta accettata.
    """
    
    training_request = ReviewRequest.query.get_or_404(request_id)
    
    # Verifica permessi e stato
    if training_request.requested_to_id != current_user.id and not (current_user.is_admin or current_user.department_id == 17):
        flash('Non hai i permessi per creare questo training.', 'danger')
        abort(403)
    
    if training_request.status != 'accepted':
        flash('Puoi creare un training solo da richieste accettate.', 'warning')
        return redirect(url_for('review.received_requests'))
    
    # Pre-popola il form con i dati della richiesta
    form = ReviewForm()
    
    if request.method == 'GET':
        form.title.data = f"Training: {training_request.subject}"
        form.review_type.data = 'progetto'  # Default
    
    if form.validate_on_submit():
        review = Review(
            reviewer_id=current_user.id,
            reviewee_id=training_request.requester_id,
            title=form.title.data,
            review_type=form.review_type.data,
            content=form.content.data,
            period_start=form.period_start.data,
            period_end=form.period_end.data,
            strengths=form.strengths.data,
            improvements=form.improvements.data,
            goals=form.goals.data,
            is_draft=False,
            is_private=form.is_private.data
        )
        
        db.session.add(review)
        db.session.flush()  # Per ottenere l'ID
        
        # Collega la review alla richiesta
        training_request.review_id = review.id
        training_request.status = 'completed'
        
        db.session.commit()
        
        # Invia notifiche
        if not review.is_private:
            try:
                send_review_notification(review)
            except Exception as e:
                current_app.logger.warning(f"Failed to send review notification: {e}")
        try:
            send_review_request_response_notification(training_request)
        except Exception as e:
            current_app.logger.warning(f"Failed to send request response notification: {e}")
        
        flash('Training creato con successo dalla richiesta!', 'success')
        return redirect(url_for('review.detail', user_id=training_request.requester_id))
    
    return render_template(
        'review/create_from_request.html',
        form=form,
        request=training_request,
        member=training_request.requester
    )


@bp.route('/request/<int:request_id>/cancel', methods=['POST'])
@login_required
def cancel_request(request_id):
    """
    Permette di cancellare una richiesta pending.
    """
    
    training_request = ReviewRequest.query.get_or_404(request_id)
    
    # Solo il richiedente può cancellare
    if training_request.requester_id != current_user.id:
        flash('Non puoi cancellare questa richiesta.', 'danger')
        abort(403)
    
    # Solo richieste pending possono essere cancellate
    if training_request.status != 'pending':
        flash('Puoi cancellare solo richieste in attesa.', 'warning')
        return redirect(url_for('review.my_requests'))
    
    db.session.delete(training_request)
    db.session.commit()

    flash('Richiesta cancellata.', 'success')
    return redirect(url_for('review.my_requests'))


# ===================== API JSON PER REACT FRONTEND =====================

from corposostenibile.extensions import csrf

@bp.route('/api/my-trainings')
@login_required
def api_my_trainings():
    """
    API JSON: Ottiene i training ricevuti dall'utente corrente.
    OTTIMIZZATO: eager loading + paginazione per performance.
    """
    from sqlalchemy.orm import joinedload, subqueryload
    from sqlalchemy import func

    # Paginazione opzionale (default: ultimi 50 training)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    per_page = min(per_page, 100)  # Max 100 per pagina

    # Query base con EAGER LOADING per evitare N+1
    query = Review.query.options(
        joinedload(Review.reviewer),
        joinedload(Review.acknowledgment),
    ).filter_by(
        reviewee_id=current_user.id,
        deleted_at=None
    )

    # Escludi bozze (a meno che non sia il reviewer)
    query = query.filter(
        or_(
            Review.is_draft == False,
            Review.reviewer_id == current_user.id
        )
    )

    # Escludi review private
    query = query.filter(
        or_(
            Review.is_private == False,
            Review.reviewer_id == current_user.id
        )
    )

    # Conta totale per statistiche (query leggera)
    total_count = query.count()

    # Query paginata ordinata per data
    reviews = query.order_by(desc(Review.created_at)).offset((page - 1) * per_page).limit(per_page).all()

    # Ottieni tutti i review_ids per query batch
    review_ids = [r.id for r in reviews]

    # Query batch per messaggi (evita N+1)
    messages_by_review = {}
    unread_by_review = {}
    if review_ids:
        # Carica tutti i messaggi in una sola query
        all_messages = ReviewMessage.query.options(
            joinedload(ReviewMessage.sender)
        ).filter(
            ReviewMessage.review_id.in_(review_ids),
            ReviewMessage.deleted_at == None
        ).order_by(ReviewMessage.review_id, ReviewMessage.created_at).all()

        for msg in all_messages:
            if msg.review_id not in messages_by_review:
                messages_by_review[msg.review_id] = []
                unread_by_review[msg.review_id] = 0
            messages_by_review[msg.review_id].append(msg)
            if not msg.is_read and msg.sender_id != current_user.id:
                unread_by_review[msg.review_id] += 1

    # Formatta i dati
    trainings_data = []
    total_unread = 0
    unacknowledged_count = 0

    for review in reviews:
        messages = messages_by_review.get(review.id, [])
        unread_count = unread_by_review.get(review.id, 0)
        total_unread += unread_count

        is_ack = review.acknowledgment is not None
        if not is_ack and not review.is_draft:
            unacknowledged_count += 1

        messages_data = [{
            'id': msg.id,
            'senderId': msg.sender_id,
            'senderName': f"{msg.sender.first_name} {msg.sender.last_name}" if msg.sender else 'Utente',
            'content': msg.content,
            'createdAt': msg.created_at.isoformat() if msg.created_at else None,
            'isRead': msg.is_read,
            'isOwn': msg.sender_id == current_user.id,
        } for msg in messages]

        trainings_data.append({
            'id': review.id,
            'title': review.title,
            'content': review.content,
            'reviewer': {
                'id': review.reviewer_id,
                'firstName': review.reviewer.first_name if review.reviewer else '',
                'lastName': review.reviewer.last_name if review.reviewer else '',
                'jobTitle': getattr(review.reviewer, 'role_display', '') if review.reviewer else '',
            },
            'reviewType': review.review_type,
            'createdAt': review.created_at.isoformat() if review.created_at else None,
            'periodStart': review.period_start.isoformat() if review.period_start else None,
            'periodEnd': review.period_end.isoformat() if review.period_end else None,
            'strengths': review.strengths,
            'improvements': review.improvements,
            'goals': review.goals,
            'isAcknowledged': is_ack,
            'acknowledgedAt': review.acknowledgment.acknowledged_at.isoformat() if review.acknowledgment else None,
            'acknowledgmentNotes': review.acknowledgment.notes if review.acknowledgment else None,
            'isDraft': review.is_draft,
            'isPrivate': review.is_private,
            'messages': messages_data,
            'unreadCount': unread_count,
        })

    # Statistiche
    stats = {
        'totalTrainings': total_count,
        'unacknowledged': unacknowledged_count,
        'unreadMessages': total_unread,
    }

    return jsonify({
        'success': True,
        'trainings': trainings_data,
        'stats': stats,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total_count,
            'pages': (total_count + per_page - 1) // per_page
        }
    })


@bp.route('/api/my-requests')
@login_required
def api_my_requests():
    """
    API JSON: Ottiene le richieste di training inviate dall'utente corrente.
    OTTIMIZZATO: eager loading + paginazione.
    """
    from sqlalchemy.orm import joinedload

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    per_page = min(per_page, 100)

    # Query con eager loading
    query = ReviewRequest.query.options(
        joinedload(ReviewRequest.requested_to)
    ).filter_by(requester_id=current_user.id)

    total_count = query.count()
    requests_list = query.order_by(desc(ReviewRequest.created_at)).offset((page - 1) * per_page).limit(per_page).all()

    requests_data = []
    stats = {'pending': 0, 'accepted': 0, 'completed': 0, 'rejected': 0}

    for req in requests_list:
        status = req.status or 'pending'
        if status in stats:
            stats[status] += 1

        requests_data.append({
            'id': req.id,
            'subject': req.subject,
            'description': req.description,
            'requestedTo': {
                'id': req.requested_to_id,
                'firstName': req.requested_to.first_name if req.requested_to else '',
                'lastName': req.requested_to.last_name if req.requested_to else '',
            },
            'priority': req.priority,
            'status': status,
            'createdAt': req.created_at.isoformat() if req.created_at else None,
            'respondedAt': req.responded_at.isoformat() if req.responded_at else None,
            'responseNotes': req.response_notes,
            'reviewId': req.review_id,
        })

    return jsonify({
        'success': True,
        'requests': requests_data,
        'stats': stats,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total_count,
            'pages': (total_count + per_page - 1) // per_page
        }
    })


@bp.route('/api/received-requests')
@login_required
def api_received_requests():
    """
    API JSON: Ottiene le richieste di training ricevute dall'utente corrente.
    OTTIMIZZATO: eager loading + paginazione.
    """
    from sqlalchemy.orm import joinedload

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    per_page = min(per_page, 100)

    query = ReviewRequest.query.options(
        joinedload(ReviewRequest.requester)
    ).filter_by(requested_to_id=current_user.id)

    total_count = query.count()
    requests_list = query.order_by(desc(ReviewRequest.created_at)).offset((page - 1) * per_page).limit(per_page).all()

    requests_data = []
    stats = {'pending': 0, 'accepted': 0, 'completed': 0, 'rejected': 0}

    for req in requests_list:
        status = req.status or 'pending'
        if status in stats:
            stats[status] += 1

        requests_data.append({
            'id': req.id,
            'subject': req.subject,
            'description': req.description,
            'requester': {
                'id': req.requester_id,
                'firstName': req.requester.first_name if req.requester else '',
                'lastName': req.requester.last_name if req.requester else '',
            },
            'priority': req.priority,
            'status': status,
            'createdAt': req.created_at.isoformat() if req.created_at else None,
            'respondedAt': req.responded_at.isoformat() if req.responded_at else None,
            'responseNotes': req.response_notes,
            'reviewId': req.review_id,
        })

    return jsonify({
        'success': True,
        'requests': requests_data,
        'stats': stats,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total_count,
            'pages': (total_count + per_page - 1) // per_page
        }
    })


@bp.route('/api/given-trainings')
@login_required
def api_given_trainings():
    """
    API JSON: Ottiene i training erogati dall'utente corrente (dove sono il reviewer).
    OTTIMIZZATO: eager loading + paginazione per performance.
    """
    from sqlalchemy.orm import joinedload

    # Paginazione opzionale
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    per_page = min(per_page, 100)

    # Query base con EAGER LOADING
    query = Review.query.options(
        joinedload(Review.reviewee),
        joinedload(Review.acknowledgment),
    ).filter_by(
        reviewer_id=current_user.id,
        deleted_at=None
    )

    # Conta totale
    total_count = query.count()

    # Query paginata
    reviews = query.order_by(desc(Review.created_at)).offset((page - 1) * per_page).limit(per_page).all()

    # Ottieni IDs per batch query
    review_ids = [r.id for r in reviews]

    # Carica messaggi in batch
    messages_by_review = {}
    unread_by_review = {}
    if review_ids:
        all_messages = ReviewMessage.query.options(
            joinedload(ReviewMessage.sender)
        ).filter(
            ReviewMessage.review_id.in_(review_ids)
        ).order_by(ReviewMessage.review_id, ReviewMessage.created_at).all()

        for msg in all_messages:
            if msg.review_id not in messages_by_review:
                messages_by_review[msg.review_id] = []
                unread_by_review[msg.review_id] = 0
            messages_by_review[msg.review_id].append(msg)
            if msg.read_at is None and msg.sender_id != current_user.id:
                unread_by_review[msg.review_id] += 1

    trainings_data = []
    drafts_count = 0
    ack_count = 0
    pending_count = 0

    for review in reviews:
        messages = messages_by_review.get(review.id, [])
        unread_count = unread_by_review.get(review.id, 0)
        ack = review.acknowledgment

        if review.is_draft:
            drafts_count += 1
        elif ack is not None:
            ack_count += 1
        else:
            pending_count += 1

        trainings_data.append({
            'id': review.id,
            'title': review.title or f"Training {review.review_type}",
            'content': review.content,
            'reviewType': review.review_type,
            'periodStart': review.period_start.isoformat() if review.period_start else None,
            'periodEnd': review.period_end.isoformat() if review.period_end else None,
            'strengths': review.strengths,
            'improvements': review.improvements,
            'goals': review.goals,
            'isDraft': review.is_draft,
            'reviewee': {
                'id': review.reviewee_id,
                'firstName': review.reviewee.first_name if review.reviewee else '',
                'lastName': review.reviewee.last_name if review.reviewee else '',
            },
            'isAcknowledged': ack is not None,
            'acknowledgedAt': ack.acknowledged_at.isoformat() if ack and ack.acknowledged_at else None,
            'acknowledgmentNotes': ack.notes if ack else None,
            'unreadCount': unread_count,
            'createdAt': review.created_at.isoformat() if review.created_at else None,
            'messages': [{
                'id': msg.id,
                'content': msg.content,
                'senderId': msg.sender_id,
                'senderName': f"{msg.sender.first_name} {msg.sender.last_name}" if msg.sender else '',
                'createdAt': msg.created_at.isoformat() if msg.created_at else None,
                'isOwn': msg.sender_id == current_user.id,
            } for msg in messages],
        })

    stats = {
        'total': total_count,
        'drafts': drafts_count,
        'acknowledged': ack_count,
        'pending': pending_count,
    }

    return jsonify({
        'success': True,
        'trainings': trainings_data,
        'stats': stats,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total_count,
            'pages': (total_count + per_page - 1) // per_page
        }
    })


def _get_training_recipients(user):
    """
    Ritorna la lista di destinatari autorizzati per richieste di training.

    Regole:
    - Admin: tutti gli utenti attivi (escluso se stesso)
    - Team leader (user.teams_led non vuoto): solo head CCO (dept 23)
    - Professionista con team: solo i team.head dei propri team
    - Professionista senza team: head del proprio dipartimento
    """
    from corposostenibile.models import Team
    from sqlalchemy.orm import joinedload

    recipients = []

    if user.is_admin:
        # Admin: tutti gli utenti attivi
        all_users = User.query.options(
            joinedload(User.teams_led),
            joinedload(User.departments_led)
        ).filter(
            User.is_active == True,
            User.id != user.id
        ).order_by(User.last_name, User.first_name).all()

        for u in all_users:
            role_info = []
            if u.is_admin:
                role_info.append('Admin')
            if u.teams_led:
                role_info.append(f"Team Leader {', '.join([t.name for t in u.teams_led])}")
            if u.departments_led:
                role_info.append(f"Head {', '.join([d.name for d in u.departments_led])}")

            specialty_name = u.specialty_display if hasattr(u, 'specialty_display') else str(u.specialty.value) if u.specialty else None
            display_role = ' | '.join(role_info) if role_info else (u.role_display if hasattr(u, 'role_display') else 'Professionista')

            recipients.append({
                'id': u.id,
                'name': f"{u.first_name} {u.last_name}",
                'role': display_role,
                'department': specialty_name
            })

    elif user.teams_led:
        # Team leader → solo head CCO (dept 23)
        dept_cco = Department.query.filter_by(id=23).first()
        if dept_cco and dept_cco.head and dept_cco.head.id != user.id:
            recipients.append({
                'id': dept_cco.head.id,
                'name': f"{dept_cco.head.first_name} {dept_cco.head.last_name}",
                'role': f"Head {dept_cco.name}",
                'department': dept_cco.head.specialty_display if hasattr(dept_cco.head, 'specialty_display') else None,
            })

    else:
        # Professionista: team heads dei propri team
        if user.teams:
            for user_team in user.teams:
                if user_team.head and user_team.head.id != user.id:
                    if not any(r['id'] == user_team.head.id for r in recipients):
                        recipients.append({
                            'id': user_team.head.id,
                            'name': f"{user_team.head.first_name} {user_team.head.last_name}",
                            'role': f"Team Leader {user_team.name}",
                            'department': user_team.head.specialty_display if hasattr(user_team.head, 'specialty_display') else None,
                        })

        # Fallback: se senza team, head del proprio dipartimento
        if not recipients and user.department and user.department.head and user.department.head.id != user.id:
            recipients.append({
                'id': user.department.head.id,
                'name': f"{user.department.head.first_name} {user.department.head.last_name}",
                'role': f"Head {user.department.name}",
                'department': user.department.head.specialty_display if hasattr(user.department.head, 'specialty_display') else None,
            })

    return recipients


@bp.route('/api/request-recipients')
@login_required
def api_request_recipients():
    """
    API JSON: Ottiene i possibili destinatari per una richiesta di training.
    Usa _get_training_recipients per logica centralizzata per ruolo.
    """
    import traceback

    try:
        possible_recipients = _get_training_recipients(current_user)

        return jsonify({
            'success': True,
            'recipients': possible_recipients,
        })
    except Exception as e:
        current_app.logger.error(f"Error in api_request_recipients: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/api/request', methods=['POST'])
@csrf.exempt
@login_required
def api_create_request():
    """
    API JSON: Crea una nuova richiesta di training.
    """
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'message': 'Dati non forniti'}), 400

    subject = data.get('subject')
    description = data.get('description', '')
    priority = data.get('priority', 'normal')
    recipient_id = data.get('recipient_id')

    if not subject:
        return jsonify({'success': False, 'message': 'Oggetto richiesto'}), 400

    if not recipient_id:
        return jsonify({'success': False, 'message': 'Destinatario richiesto'}), 400

    recipient = User.query.get(recipient_id)
    if not recipient:
        return jsonify({'success': False, 'message': 'Destinatario non trovato'}), 404

    # Validazione server-side: il destinatario deve essere tra quelli autorizzati
    if not current_user.is_admin:
        allowed = _get_training_recipients(current_user)
        if int(recipient_id) not in {r['id'] for r in allowed}:
            return jsonify({'success': False, 'message': 'Destinatario non autorizzato'}), 403

    training_request = ReviewRequest(
        requester_id=current_user.id,
        requested_to_id=recipient_id,
        subject=subject,
        description=description,
        priority=priority,
        status='pending'
    )

    db.session.add(training_request)
    db.session.commit()

    # Invia notifica email
    try:
        send_review_request_notification(training_request)
    except Exception as e:
        current_app.logger.warning(f"Failed to send request notification: {e}")

    return jsonify({
        'success': True,
        'request_id': training_request.id,
        'message': f'Richiesta inviata a {recipient.first_name} {recipient.last_name}'
    })


@bp.route('/api/request/<int:request_id>/cancel', methods=['POST'])
@csrf.exempt
@login_required
def api_cancel_request(request_id):
    """
    API JSON: Cancella una richiesta pending.
    """
    training_request = ReviewRequest.query.get_or_404(request_id)

    if training_request.requester_id != current_user.id:
        return jsonify({'success': False, 'message': 'Non autorizzato'}), 403

    if training_request.status != 'pending':
        return jsonify({'success': False, 'message': 'Puoi cancellare solo richieste in attesa'}), 400

    db.session.delete(training_request)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Richiesta cancellata'})


@bp.route('/api/request/<int:request_id>/respond', methods=['POST'])
@csrf.exempt
@login_required
def api_respond_request(request_id):
    """
    API JSON: Risponde a una richiesta di training ricevuta (accetta/rifiuta).
    """
    training_request = ReviewRequest.query.get_or_404(request_id)

    is_cco = bool(getattr(current_user, 'department_id', None) == 17)
    if training_request.requested_to_id != current_user.id and not (current_user.is_admin or is_cco):
        return jsonify({'success': False, 'message': 'Non autorizzato'}), 403

    if training_request.status != 'pending':
        return jsonify({'success': False, 'message': 'Questa richiesta è già stata gestita'}), 400

    data = request.get_json() or {}
    action = (data.get('action') or '').strip().lower()
    response_notes = (data.get('response_notes') or '').strip()

    if action not in {'accept', 'reject'}:
        return jsonify({'success': False, 'message': 'Azione non valida'}), 400

    training_request.response_notes = response_notes
    training_request.responded_at = datetime.utcnow()
    training_request.status = 'accepted' if action == 'accept' else 'rejected'

    db.session.commit()

    if action == 'reject':
        try:
            send_review_request_response_notification(training_request)
        except Exception as e:
            current_app.logger.warning(f"Failed to send request response notification: {e}")

    return jsonify({
        'success': True,
        'message': 'Richiesta accettata' if action == 'accept' else 'Richiesta rifiutata',
        'request': {
            'id': training_request.id,
            'status': training_request.status,
            'respondedAt': training_request.responded_at.isoformat() if training_request.responded_at else None,
            'responseNotes': training_request.response_notes,
            'reviewId': training_request.review_id,
        }
    })


@bp.route('/api/<int:review_id>/acknowledge', methods=['POST'])
@csrf.exempt
@login_required
def api_acknowledge(review_id):
    """
    API JSON: Conferma la lettura di un training.
    """
    review = Review.query.get_or_404(review_id)

    if review.reviewee_id != current_user.id:
        return jsonify({'success': False, 'message': 'Non autorizzato'}), 403

    if review.is_acknowledged:
        return jsonify({'success': False, 'message': 'Già confermato'}), 400

    data = request.get_json() or {}
    notes = data.get('notes', '')

    acknowledgment = ReviewAcknowledgment(
        review_id=review.id,
        acknowledged_by=current_user.id,
        notes=notes,
        ip_address=request.remote_addr
    )

    db.session.add(acknowledgment)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Lettura confermata',
        'acknowledgedAt': acknowledgment.acknowledged_at.isoformat()
    })


@bp.route('/api/<int:review_id>/message', methods=['POST'])
@csrf.exempt
@login_required
def api_send_message(review_id):
    """
    API JSON: Invia un messaggio nella chat di un training.
    """
    review = Review.query.get_or_404(review_id)

    # Verifica permessi
    if not (current_user.is_admin or
            current_user.department_id == 17 or
            current_user.id == review.reviewer_id or
            current_user.id == review.reviewee_id):
        return jsonify({'success': False, 'message': 'Non autorizzato'}), 403

    if review.deleted_at:
        return jsonify({'success': False, 'message': 'Training eliminato'}), 400

    data = request.get_json()
    if not data or not data.get('content'):
        return jsonify({'success': False, 'message': 'Messaggio vuoto'}), 400

    message = ReviewMessage(
        review_id=review.id,
        sender_id=current_user.id,
        content=data.get('content'),
        ip_address=request.remote_addr
    )

    db.session.add(message)
    db.session.commit()

    # Notifica email
    try:
        if current_user.id == review.reviewer_id:
            recipient = review.reviewee
        else:
            recipient = review.reviewer
        send_message_notification(message, recipient)
    except Exception as e:
        current_app.logger.warning(f"Failed to send message notification: {e}")

    return jsonify({
        'success': True,
        'message': {
            'id': message.id,
            'senderId': message.sender_id,
            'senderName': f"{current_user.first_name} {current_user.last_name}",
            'content': message.content,
            'createdAt': message.created_at.isoformat(),
            'isRead': True,
            'isOwn': True,
        }
    })


@bp.route('/api/<int:review_id>/mark-all-read', methods=['POST'])
@csrf.exempt
@login_required
def api_mark_all_read(review_id):
    """
    API JSON: Marca tutti i messaggi di un training come letti.
    """
    review = Review.query.get_or_404(review_id)

    if not (current_user.is_admin or
            current_user.department_id == 17 or
            current_user.id == review.reviewer_id or
            current_user.id == review.reviewee_id):
        return jsonify({'success': False, 'message': 'Non autorizzato'}), 403

    messages = ReviewMessage.query.filter_by(
        review_id=review.id,
        is_read=False,
        deleted_at=None
    ).filter(
        ReviewMessage.sender_id != current_user.id
    ).all()

    count = 0
    for message in messages:
        if message.mark_as_read(current_user.id):
            count += 1

    if count > 0:
        db.session.commit()

    return jsonify({'success': True, 'count': count})


# ===================== ADMIN API ENDPOINTS =====================

@bp.route('/api/admin/professionals')
@login_required
def api_admin_professionals():
    """
    API JSON: Lista tutti i professionisti attivi (solo per admin/HR).
    """
    # Verifica permessi admin/HR/CCO o Team Leader (scope team)
    is_team_leader = getattr(current_user, 'role', None) == UserRoleEnum.team_leader
    if not (_is_admin_hr_or_cco(current_user) or is_team_leader):
        return jsonify({'success': False, 'error': 'Non autorizzato'}), 403

    # Query per utenti attivi
    query = User.query.filter_by(is_active=True)
    if not _is_admin_hr_or_cco(current_user):
        visible_ids = _get_led_team_member_ids(current_user)
        visible_ids.discard(current_user.id)
        if not visible_ids:
            return jsonify({'success': True, 'professionals': []})
        query = query.filter(User.id.in_(list(visible_ids)))

    users = query.order_by(
        User.last_name, User.first_name
    ).all()

    professionals = []
    for user in users:
        # Conta i training ricevuti
        training_count = Review.query.filter_by(
            reviewee_id=user.id,
            deleted_at=None,
            is_draft=False
        ).count()

        # Conta training non confermati
        unacknowledged_count = Review.query.filter_by(
            reviewee_id=user.id,
            deleted_at=None,
            is_draft=False
        ).filter(
            ~Review.id.in_(
                db.session.query(ReviewAcknowledgment.review_id)
            )
        ).count()

        professionals.append({
            'id': user.id,
            'firstName': user.first_name,
            'lastName': user.last_name,
            'email': user.email,
            'jobTitle': getattr(user, 'job_title', None),
            'department': None,
            'departmentId': None,
            'trainingCount': training_count,
            'unacknowledgedCount': unacknowledged_count,
        })

    return jsonify({
        'success': True,
        'professionals': professionals,
    })


@bp.route('/api/admin/trainings/<int:user_id>')
@login_required
def api_admin_user_trainings(user_id):
    """
    API JSON: Ottiene i training di un utente specifico (solo per admin/HR).
    """
    # Verifica che l'utente esista
    target_user = User.query.get_or_404(user_id)

    # Verifica permessi (admin/HR/CCO oppure Team Leader nel proprio scope)
    if not (_is_admin_hr_or_cco(current_user) or can_view_member_reviews(current_user, target_user)):
        return jsonify({'success': False, 'error': 'Non autorizzato'}), 403

    # Query per i training dell'utente target
    reviews = Review.query.filter_by(
        reviewee_id=user_id,
        deleted_at=None
    ).order_by(desc(Review.created_at)).all()

    trainings_data = []
    for review in reviews:
        # Ottieni i messaggi
        messages = ReviewMessage.query.filter_by(
            review_id=review.id,
            deleted_at=None
        ).order_by(ReviewMessage.created_at).all()

        messages_data = [{
            'id': msg.id,
            'senderId': msg.sender_id,
            'senderName': f"{msg.sender.first_name} {msg.sender.last_name}" if msg.sender else 'Utente',
            'content': msg.content,
            'createdAt': msg.created_at.isoformat() if msg.created_at else None,
            'isRead': msg.is_read,
            'isOwn': msg.sender_id == current_user.id,
        } for msg in messages]

        trainings_data.append({
            'id': review.id,
            'title': review.title,
            'content': review.content,
            'reviewer': {
                'id': review.reviewer_id,
                'firstName': review.reviewer.first_name if review.reviewer else '',
                'lastName': review.reviewer.last_name if review.reviewer else '',
                'jobTitle': getattr(review.reviewer, 'job_title', '') if review.reviewer else '',
            },
            'reviewee': {
                'id': target_user.id,
                'firstName': target_user.first_name,
                'lastName': target_user.last_name,
            },
            'reviewType': review.review_type,
            'createdAt': review.created_at.isoformat() if review.created_at else None,
            'periodStart': review.period_start.isoformat() if review.period_start else None,
            'periodEnd': review.period_end.isoformat() if review.period_end else None,
            'strengths': review.strengths,
            'improvements': review.improvements,
            'goals': review.goals,
            'isAcknowledged': review.is_acknowledged,
            'acknowledgedAt': review.acknowledgment.acknowledged_at.isoformat() if review.acknowledgment else None,
            'acknowledgmentNotes': review.acknowledgment.notes if review.acknowledgment else None,
            'isDraft': review.is_draft,
            'isPrivate': review.is_private,
            'messages': messages_data,
            'unreadCount': 0,  # Admin non ha messaggi non letti
        })

    # Query per i training EROGATI dall'utente (dove è il reviewer)
    given_reviews = Review.query.filter_by(
        reviewer_id=user_id,
        deleted_at=None
    ).order_by(desc(Review.created_at)).all()

    given_trainings_data = []
    for review in given_reviews:
        given_trainings_data.append({
            'id': review.id,
            'title': review.title,
            'content': review.content,
            'reviewee': {
                'id': review.reviewee_id,
                'firstName': review.reviewee.first_name if review.reviewee else '',
                'lastName': review.reviewee.last_name if review.reviewee else '',
            },
            'reviewType': review.review_type,
            'createdAt': review.created_at.isoformat() if review.created_at else None,
            'periodStart': review.period_start.isoformat() if review.period_start else None,
            'periodEnd': review.period_end.isoformat() if review.period_end else None,
            'isAcknowledged': review.is_acknowledged,
            'isDraft': review.is_draft,
        })

    # Statistiche
    stats = {
        'totalTrainings': len(trainings_data),
        'totalGiven': len(given_trainings_data),
        'unacknowledged': len([t for t in trainings_data if not t['isAcknowledged'] and not t['isDraft']]),
        'drafts': len([t for t in trainings_data if t['isDraft']]),
    }

    return jsonify({
        'success': True,
        'user': {
            'id': target_user.id,
            'firstName': target_user.first_name,
            'lastName': target_user.last_name,
            'email': target_user.email,
            'jobTitle': getattr(target_user, 'job_title', None),
            'department': None,
        },
        'trainings': trainings_data,
        'givenTrainings': given_trainings_data,
        'stats': stats,
    })


@bp.route('/api/admin/trainings/<int:user_id>', methods=['POST'])
@login_required
def api_admin_create_training(user_id):
    """
    API JSON: Crea un nuovo training per un utente specifico (solo per admin/HR o chi ha permessi).
    """
    from flask import jsonify

    # Verifica che l'utente target esista
    target_user = User.query.get_or_404(user_id)

    # Verifica permessi di scrittura
    if not can_write_review(current_user, target_user):
        return jsonify({'success': False, 'error': 'Non autorizzato a scrivere training a questo utente'}), 403

    # Non si può scrivere training a se stessi
    if current_user.id == target_user.id:
        return jsonify({'success': False, 'error': 'Non puoi scrivere un training a te stesso'}), 400

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Dati mancanti'}), 400

    # Valida campi obbligatori
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()

    if not title:
        return jsonify({'success': False, 'error': 'Il titolo è obbligatorio'}), 400
    if not content:
        return jsonify({'success': False, 'error': 'Il contenuto è obbligatorio'}), 400

    # Crea il training
    review = Review(
        reviewer_id=current_user.id,
        reviewee_id=target_user.id,
        title=title,
        review_type=data.get('review_type', 'general'),
        content=content,
        period_start=datetime.strptime(data['period_start'], '%Y-%m-%d').date() if data.get('period_start') else None,
        period_end=datetime.strptime(data['period_end'], '%Y-%m-%d').date() if data.get('period_end') else None,
        strengths=data.get('strengths', '').strip() or None,
        improvements=data.get('improvements', '').strip() or None,
        goals=data.get('goals', '').strip() or None,
        is_draft=False,
        is_private=data.get('is_private', False)
    )

    db.session.add(review)
    db.session.commit()

    # Invia notifica email al destinatario (solo se non è privata)
    if not review.is_private:
        send_review_notification(review)

    return jsonify({
        'success': True,
        'message': 'Training creato con successo',
        'training': {
            'id': review.id,
            'title': review.title,
            'createdAt': review.created_at.isoformat() if review.created_at else None,
        }
    })


def _review_dashboard_visible_user_ids():
    """
    User IDs that count for training dashboard (reviewer or reviewee).
    - Admin / dept 17: None (all)
    - Team Leader: members of teams they lead + self
    - Professionista: only self
    """
    if not current_user.is_authenticated:
        return []
    if current_user.is_admin or (hasattr(current_user, 'department_id') and current_user.department_id == 17):
        return None
    if getattr(current_user, 'role', None) == UserRoleEnum.team_leader and getattr(current_user, 'teams_led', None):
        visible = {current_user.id}
        for team in current_user.teams_led:
            if getattr(team, 'members', None):
                for m in team.members:
                    visible.add(m.id)
        return list(visible)
    return [current_user.id]


@bp.route('/api/admin/dashboard-stats')
@login_required
def api_admin_dashboard_stats():
    """
    API JSON: Statistiche training per la dashboard.
    Dati filtrati per ruolo (admin/dept17=all, TL=team, professionista=own).
    """
    from sqlalchemy import func, extract
    from calendar import monthrange

    now = datetime.utcnow()
    visible_ids = _review_dashboard_visible_user_ids()

    # Base filter: non-draft, not deleted; then restrict by role
    base_filter = Review.query.filter_by(deleted_at=None, is_draft=False)
    if visible_ids is not None:
        base_filter = base_filter.filter(
            or_(Review.reviewer_id.in_(visible_ids), Review.reviewee_id.in_(visible_ids))
        )

    total_trainings = base_filter.count()
    total_acknowledged = base_filter.join(Review.acknowledgment).count()
    total_pending = total_trainings - total_acknowledged
    drafts_q = Review.query.filter_by(deleted_at=None, is_draft=True)
    if visible_ids is not None:
        drafts_q = drafts_q.filter(Review.reviewer_id.in_(visible_ids))
    total_drafts = drafts_q.count()

    # Questo mese
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    this_month = base_filter.filter(Review.created_at >= month_start).count()

    # Mese scorso
    prev_month_end = month_start - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)
    last_month = base_filter.filter(
        Review.created_at >= prev_month_start,
        Review.created_at < month_start
    ).count()

    # Tasso conferma
    ack_rate = round((total_acknowledged / total_trainings * 100), 1) if total_trainings > 0 else 0

    # --- Richieste training ---
    total_requests = ReviewRequest.query.filter_by(deleted_at=None).count() if hasattr(ReviewRequest, 'deleted_at') else ReviewRequest.query.count()
    pending_requests = ReviewRequest.query.filter_by(status='pending').count()

    # --- Breakdown per tipo ---
    by_type_q = db.session.query(Review.review_type, func.count(Review.id)).filter(
        Review.deleted_at == None,
        Review.is_draft == False
    )
    if visible_ids is not None:
        by_type_q = by_type_q.filter(
            or_(Review.reviewer_id.in_(visible_ids), Review.reviewee_id.in_(visible_ids))
        )
    by_type_raw = by_type_q.group_by(Review.review_type).all()

    type_labels = {
        'settimanale': 'Settimanale',
        'mensile': 'Mensile',
        'progetto': 'Progetto',
        'miglioramento': 'Miglioramento',
    }
    by_type = [{'type': t, 'label': type_labels.get(t, t.capitalize() if t else 'Altro'), 'count': c} for t, c in by_type_raw]

    # --- Trend mensile (ultimi 6 mesi) ---
    monthly_trend = []
    for i in range(5, -1, -1):
        # Calcola mese
        m_date = now - timedelta(days=i * 30)
        m_year = m_date.year
        m_month = m_date.month
        m_start = datetime(m_year, m_month, 1)
        m_days = monthrange(m_year, m_month)[1]
        m_end = datetime(m_year, m_month, m_days, 23, 59, 59)

        count = base_filter.filter(
            Review.created_at >= m_start,
            Review.created_at <= m_end
        ).count()

        ack_count = base_filter.join(Review.acknowledgment).filter(
            Review.created_at >= m_start,
            Review.created_at <= m_end
        ).count()

        month_names = ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu',
                       'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic']
        monthly_trend.append({
            'month': month_names[m_month - 1],
            'year': m_year,
            'total': count,
            'acknowledged': ack_count,
        })

    # --- Top 10 formatori (chi ha erogato più training) ---
    top_reviewers_q = db.session.query(
        User.id,
        User.first_name,
        User.last_name,
        User.email,
        func.count(Review.id).label('count')
    ).join(Review, Review.reviewer_id == User.id).filter(
        Review.deleted_at == None,
        Review.is_draft == False
    )
    if visible_ids is not None:
        top_reviewers_q = top_reviewers_q.filter(
            or_(Review.reviewer_id.in_(visible_ids), Review.reviewee_id.in_(visible_ids))
        )
    top_reviewers_raw = top_reviewers_q.group_by(User.id, User.first_name, User.last_name, User.email).order_by(desc('count')).limit(10).all()
    top_reviewers = [{
        'id': r.id,
        'name': f"{r.first_name} {r.last_name}",
        'email': r.email,
        'count': r.count
    } for r in top_reviewers_raw]

    # --- Top 10 destinatari (chi ha ricevuto più training) ---
    top_reviewees_q = db.session.query(
        User.id,
        User.first_name,
        User.last_name,
        User.email,
        func.count(Review.id).label('count')
    ).join(Review, Review.reviewee_id == User.id).filter(
        Review.deleted_at == None,
        Review.is_draft == False
    )
    if visible_ids is not None:
        top_reviewees_q = top_reviewees_q.filter(
            or_(Review.reviewer_id.in_(visible_ids), Review.reviewee_id.in_(visible_ids))
        )
    top_reviewees_raw = top_reviewees_q.group_by(User.id, User.first_name, User.last_name, User.email).order_by(desc('count')).limit(10).all()

    top_reviewees = [{
        'id': r.id,
        'name': f"{r.first_name} {r.last_name}",
        'email': r.email,
        'count': r.count
    } for r in top_reviewees_raw]

    # --- Ultimi 10 training ---
    recent_raw = base_filter.order_by(desc(Review.created_at)).limit(10).all()
    recent_trainings = [{
        'id': r.id,
        'title': r.title,
        'reviewType': r.review_type,
        'createdAt': r.created_at.isoformat() if r.created_at else None,
        'reviewer': f"{r.reviewer.first_name} {r.reviewer.last_name}" if r.reviewer else 'N/D',
        'reviewee': f"{r.reviewee.first_name} {r.reviewee.last_name}" if r.reviewee else 'N/D',
        'isAcknowledged': r.is_acknowledged,
    } for r in recent_raw]

    return jsonify({
        'success': True,
        'kpi': {
            'totalTrainings': total_trainings,
            'totalAcknowledged': total_acknowledged,
            'totalPending': total_pending,
            'totalDrafts': total_drafts,
            'thisMonth': this_month,
            'lastMonth': last_month,
            'ackRate': ack_rate,
            'totalRequests': total_requests,
            'pendingRequests': pending_requests,
        },
        'byType': by_type,
        'monthlyTrend': monthly_trend,
        'topReviewers': top_reviewers,
        'topReviewees': top_reviewees,
        'recentTrainings': recent_trainings,
    })
