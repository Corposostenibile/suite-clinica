"""
Route per il sistema di Review
"""

from flask import render_template, redirect, url_for, flash, request, abort, current_app
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
    User, Department, Review, ReviewAcknowledgment, ReviewMessage, ReviewRequest
)
from corposostenibile.extensions import db


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

    # Team Leader Nutrizione può vedere membri del proprio team
    if member.department_id == 2 and member.team_id:
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

    # Team Leader Nutrizione può scrivere a membri del proprio team
    if member.department_id == 2 and member.team_id:
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

    Logica speciale per dipartimenti 2 (Nutrizione), 3 (Coach), 4 (Psicologia), 13 (Customer Success):
    - Membri: possono scegliere tra il proprio head/team leader e il head CCO (23)
    - Head/Team Leader: richiedono al CCO

    Per Nutrizione (dept 2) con team:
    - Membri con team: scelgono tra Team Leader e Head CCO
    - Membri senza team: scelgono tra Head Nutrizione e Head CCO
    - Team Leader: richiedono a Head CCO
    """
    from corposostenibile.models import Team

    # Trova i possibili destinatari della richiesta
    possible_recipients = []

    # Helper per aggiungere Head CCO come opzione
    def add_cco_option():
        dept_cco = Department.query.filter_by(id=23).first()
        if dept_cco and dept_cco.head and dept_cco.head.id != current_user.id:
            possible_recipients.append({
                'user': dept_cco.head,
                'label': f"{dept_cco.head.first_name} {dept_cco.head.last_name} (Head CCO)"
            })
            return True
        return False

    # Verifica se l'utente è un team leader (nel dipartimento Nutrizione)
    is_team_leader = Team.query.filter_by(head_id=current_user.id).first() is not None
    user_team = None
    if current_user.team_id:
        user_team = Team.query.get(current_user.team_id)

    # CASO 1: Membri del dipartimento Nutrizione (2) con struttura a team
    if current_user.department_id == 2:
        if is_team_leader:
            # Team Leader Nutrizione → richiedono al CCO
            add_cco_option()
            current_app.logger.info(f'Nutrizione Team Leader {current_user.id} can request training from CCO head')
        elif user_team and user_team.head and user_team.head.id != current_user.id:
            # Membro con team → sceglie tra Team Leader e CCO
            possible_recipients.append({
                'user': user_team.head,
                'label': f"{user_team.head.first_name} {user_team.head.last_name} (Team Leader {user_team.name})"
            })
            add_cco_option()
            current_app.logger.info(f'Nutrizione member {current_user.id} (team {user_team.id}) can request training from team leader and CCO head')
        else:
            # Membro senza team → sceglie tra Head Nutrizione e CCO
            if current_user.department and current_user.department.head:
                if current_user.department.head.id != current_user.id:
                    possible_recipients.append({
                        'user': current_user.department.head,
                        'label': f"{current_user.department.head.first_name} {current_user.department.head.last_name} (Head {current_user.department.name})"
                    })
            add_cco_option()
            current_app.logger.info(f'Nutrizione member {current_user.id} (no team) can request training from dept head and CCO head')

    # CASO 2: Membri dei dipartimenti 3, 4, 13 → scelgono tra proprio head e CCO
    elif current_user.department_id in [3, 4, 13]:
        # Aggiungi il proprio head di dipartimento
        if current_user.department and current_user.department.head:
            if current_user.department.head.id != current_user.id:  # Non se stesso
                possible_recipients.append({
                    'user': current_user.department.head,
                    'label': f"{current_user.department.head.first_name} {current_user.department.head.last_name} (Head {current_user.department.name})"
                })

        # Aggiungi anche il head del dipartimento CCO (23)
        add_cco_option()
        current_app.logger.info(f'Dept {current_user.department_id} member {current_user.id} can request training from own head and CCO head')

    # CASO 3: Head di dipartimento
    elif is_department_head(current_user):
        # Head dei dipartimenti 2, 3, 4, 13 richiedono al CCO
        user_dept = Department.query.filter_by(head_id=current_user.id).first()
        if user_dept and user_dept.id in [2, 3, 4, 13]:
            dept_cco = Department.query.filter_by(id=23).first()
            if dept_cco and dept_cco.head and dept_cco.head.id != current_user.id:
                recipient = dept_cco.head
            else:
                recipient = None
        else:
            # Altri head richiedono al CEO
            ceo_dept = Department.query.filter_by(name='CEO').first()
            if ceo_dept and ceo_dept.head:
                recipient = ceo_dept.head
            else:
                # Fallback: cerca utente con job_title CEO o admin con id più basso
                ceo_user = User.query.filter_by(job_title='CEO').first()
                if ceo_user:
                    recipient = ceo_user
                else:
                    # Cerca prima un admin, poi fallback su HR
                    recipient = User.query.filter_by(is_admin=True).order_by(User.id).first()
                    if not recipient:
                        # Se non c'è admin, prova con HR (department_id 17)
                        recipient = User.query.filter_by(department_id=17).order_by(User.id).first()

        # Evita che qualcuno richieda training a se stesso
        if recipient and recipient.id != current_user.id:
            possible_recipients.append({
                'user': recipient,
                'label': f"{recipient.first_name} {recipient.last_name} (Head CCO)" if user_dept and user_dept.id in [2, 3, 4, 13] else f"{recipient.first_name} {recipient.last_name}"
            })

    # CASO 4: Utente normale di altri dipartimenti
    elif current_user.department and current_user.department.head:
        # L'utente normale richiede al suo head di dipartimento
        if current_user.department.head.id != current_user.id:
            possible_recipients.append({
                'user': current_user.department.head,
                'label': f"{current_user.department.head.first_name} {current_user.department.head.last_name}"
            })

    if not possible_recipients:
        flash('Non è possibile inviare richieste di training al momento. Nessun responsabile configurato.', 'warning')
        return redirect(url_for('review.index'))

    form = ReviewRequestForm()

    # Se ci sono più destinatari possibili, aggiungiamo un campo di selezione
    if len(possible_recipients) > 1:
        # Aggiungi le choices al form dinamicamente
        choices = [(str(r['user'].id), r['label']) for r in possible_recipients]
        form.recipient_id.choices = choices
    else:
        # Un solo destinatario, lo impostiamo direttamente
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
            send_review_request_response_notification(training_request)
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
            send_review_notification(review)
        send_review_request_response_notification(training_request)
        
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