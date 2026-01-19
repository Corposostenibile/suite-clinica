"""
welcome.routes
==============

Route per la pagina di benvenuto personalizzata con dashboard OKR.
"""

from __future__ import annotations

from datetime import date, datetime
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import and_, or_
from sqlalchemy.orm import Query

from corposostenibile.models import (
    Objective, 
    KeyResult,
    DepartmentObjective,
    DepartmentKeyResult, 
    OKRStatusEnum,
    OKRPeriodEnum,
    Communication,
    CommunicationRead,
    Review,
    ReviewAcknowledgment,
    ReviewMessage,
    ReviewRequest,
    Department,
    db
)

welcome_bp = Blueprint(
    "welcome",
    __name__,
    template_folder="templates",
    static_folder="static",
)

@welcome_bp.get("/maintenance")
@login_required
def maintenance():
    """Pagina di manutenzione per sezioni temporaneamente non disponibili."""
    return render_template("maintenance.html")


@welcome_bp.get("/")
@login_required
def index():
    """Landing page di benvenuto personalizzata con OKR dashboard."""
    
    # ═══════════════════════════════════════════════════════════════
    #  COMUNICAZIONI NON LETTE
    # ═══════════════════════════════════════════════════════════════
    
    # Query per comunicazioni accessibili all'utente
    communications_query = db.session.query(Communication)
    
    # Filtra per comunicazioni destinate all'utente
    if current_user.department:
        # Comunicazioni per tutti O per il dipartimento dell'utente
        communications_query = communications_query.filter(
            or_(
                Communication.is_for_all_departments == True,
                Communication.departments.contains(current_user.department)
            )
        )
    else:
        # Solo comunicazioni per tutti se l'utente non ha dipartimento
        communications_query = communications_query.filter(
            Communication.is_for_all_departments == True
        )
    
    # Escludi comunicazioni inviate dall'utente stesso
    communications_query = communications_query.filter(
        Communication.author_id != current_user.id
    )
    
    # Ottieni tutti gli ID delle comunicazioni accessibili
    accessible_comm_ids = [c.id for c in communications_query.all()]
    
    # Trova quali sono state lette
    read_comm_ids = db.session.query(CommunicationRead.communication_id).filter(
        and_(
            CommunicationRead.user_id == current_user.id,
            CommunicationRead.communication_id.in_(accessible_comm_ids)
        )
    ).all()
    read_comm_ids = [r[0] for r in read_comm_ids]
    
    # Calcola comunicazioni non lette
    unread_comm_ids = set(accessible_comm_ids) - set(read_comm_ids)
    
    # Recupera le comunicazioni non lette (ultime 5, più recenti)
    unread_communications = []
    if unread_comm_ids:
        unread_communications = Communication.query.filter(
            Communication.id.in_(unread_comm_ids)
        ).order_by(Communication.created_at.desc()).limit(5).all()
    
    unread_count = len(unread_comm_ids)
    
    # ═══════════════════════════════════════════════════════════════
    #  REVIEW NON LETTE
    # ═══════════════════════════════════════════════════════════════
    
    # Conta le review non ancora confermate dall'utente
    # ESCLUDI le review private (non visibili al destinatario)
    unread_reviews_count = Review.query.filter(
        Review.reviewee_id == current_user.id,
        Review.is_draft == False,
        Review.is_private == False,  # Escludi review private
        Review.deleted_at == None
    ).outerjoin(
        ReviewAcknowledgment,
        ReviewAcknowledgment.review_id == Review.id
    ).filter(
        ReviewAcknowledgment.id == None
    ).count()
    
    # ═══════════════════════════════════════════════════════════════
    #  MESSAGGI REVIEW NON LETTI
    # ═══════════════════════════════════════════════════════════════
    
    # Trova tutte le review dove l'utente è reviewer o reviewee
    user_reviews = Review.query.filter(
        or_(
            Review.reviewer_id == current_user.id,
            Review.reviewee_id == current_user.id
        ),
        Review.deleted_at == None
    ).all()
    
    review_ids = [r.id for r in user_reviews]
    
    # Conta i messaggi non letti in queste review
    unread_messages_count = 0
    if review_ids:
        unread_messages_count = ReviewMessage.query.filter(
            ReviewMessage.review_id.in_(review_ids),
            ReviewMessage.is_read == False,
            ReviewMessage.sender_id != current_user.id,
            ReviewMessage.deleted_at == None
        ).count()
    
    # ═══════════════════════════════════════════════════════════════
    #  RICHIESTE TRAINING PENDING (per responsabili)
    # ═══════════════════════════════════════════════════════════════
    
    pending_requests_count = 0
    pending_requests = []
    
    # Verifica se l'utente è un responsabile
    if current_user.is_admin:
        # Admin vede tutte le richieste pending indirizzate a lui
        pending_requests_count = ReviewRequest.query.filter_by(
            requested_to_id=current_user.id,
            status='pending'
        ).count()
        
        # Prendi le ultime 3 richieste pending per la dashboard
        pending_requests = ReviewRequest.query.filter_by(
            requested_to_id=current_user.id,
            status='pending'
        ).order_by(ReviewRequest.created_at.desc()).limit(3).all()
    else:
        # Verifica se è head di un dipartimento
        is_head = Department.query.filter_by(head_id=current_user.id).first()
        if is_head:
            pending_requests_count = ReviewRequest.query.filter_by(
                requested_to_id=current_user.id,
                status='pending'
            ).count()
            
            # Prendi le ultime 3 richieste pending per la dashboard
            pending_requests = ReviewRequest.query.filter_by(
                requested_to_id=current_user.id,
                status='pending'
            ).order_by(ReviewRequest.created_at.desc()).limit(3).all()
    
    # Totale notifiche non lette (review + messaggi + richieste pending)
    total_unread_training = unread_reviews_count + unread_messages_count + pending_requests_count
    
    # ═══════════════════════════════════════════════════════════════
    #  OKR PERSONALI
    # ═══════════════════════════════════════════════════════════════
    
    # Obiettivi personali attivi dell'anno corrente
    current_year = date.today().year
    current_month = date.today().month
    
    # Determina il trimestre corrente
    if current_month <= 3:
        current_quarter = 'q1'
    elif current_month <= 6:
        current_quarter = 'q2'
    elif current_month <= 9:
        current_quarter = 'q3'
    else:
        current_quarter = 'q4'
    
    # Use a proper SQLAlchemy query instead of accessing the relationship directly
    # Ora period contiene i trimestri come stringa es. "q1,q2,q3"
    personal_objectives = db.session.query(Objective).filter(
        and_(
            Objective.user_id == current_user.id,
            Objective.status == OKRStatusEnum.active,
            Objective.period.contains(current_quarter)  # Cerca il trimestre corrente nella stringa
        )
    ).order_by(Objective.order_index).limit(3).all()
    
    # Statistiche personali
    personal_stats = {
        'total_objectives': len(personal_objectives),
        'avg_progress': 0,
        'total_key_results': 0,
        'completed_kr': 0
    }
    
    if personal_objectives:
        # Progress rimosso dal modello semplificato
        personal_stats['avg_progress'] = 0
        
        # Conta key results
        for obj in personal_objectives:
            personal_stats['total_key_results'] += len(obj.key_results)
            # Progress rimosso - contiamo solo i KR totali
            personal_stats['completed_kr'] = 0
    
    # ═══════════════════════════════════════════════════════════════
    #  OKR DIPARTIMENTO
    # ═══════════════════════════════════════════════════════════════
    
    dept_objectives = []
    dept_stats = {
        'total_objectives': 0,
        'avg_progress': 0,
        'my_key_results': 0,
        'my_completed_kr': 0
    }
    
    if current_user.department:
        # Obiettivi del dipartimento del trimestre corrente
        dept_objectives = db.session.query(DepartmentObjective).filter(
            and_(
                DepartmentObjective.department_id == current_user.department.id,
                DepartmentObjective.status == OKRStatusEnum.active,
                DepartmentObjective.period.like(f'%{current_quarter}%')
            )
        ).order_by(DepartmentObjective.order_index).limit(3).all()
        
        dept_stats['total_objectives'] = len(dept_objectives)
    
    # ═══════════════════════════════════════════════════════════════
    #  PROSSIME SCADENZE - Disabilitato senza date
    # ═══════════════════════════════════════════════════════════════
    
    upcoming_deadlines = []  # Lista vuota, non abbiamo più date/scadenze
    
    # ═══════════════════════════════════════════════════════════════
    #  KEY RESULTS IN FOCUS (i miei KR con progress < 100%)
    # ═══════════════════════════════════════════════════════════════
    
    focus_krs = []
    
    # KR personali - progress rimosso dal modello semplificato
    for obj in personal_objectives:
        for kr in obj.key_results[:2]:  # Max 2 per obiettivo
            focus_krs.append({
                'title': kr.title,
                'progress': 0,  # Progress rimosso
                'display_value': kr.title,  # Solo il titolo ora
                'objective_title': obj.title,
                'type': 'personal',
                'kr_id': kr.id
            })
    
    # KR dipartimento - non più assegnabili nel modello semplificato
    # Rimosso perché non abbiamo più assignee_id
        # Rimosso il loop - non ci sono più KR assegnabili
    
    # Limita a 6 KR totali per non sovraccaricare
    focus_krs = focus_krs[:6]
    
    return render_template(
        "welcome/index.html",
        personal_objectives=personal_objectives,
        personal_stats=personal_stats,
        dept_objectives=dept_objectives,
        dept_stats=dept_stats,
        upcoming_deadlines=upcoming_deadlines,
        focus_krs=focus_krs,
        current_year=current_year,
        current_quarter=current_quarter.upper(),
        unread_communications=unread_communications,
        unread_count=unread_count,
        unread_reviews_count=unread_reviews_count,
        unread_messages_count=unread_messages_count,
        total_unread_training=total_unread_training,
        pending_requests_count=pending_requests_count,
        pending_requests=pending_requests
    )