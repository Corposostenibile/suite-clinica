from flask import jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import or_, desc, exists, select
from sqlalchemy.orm import aliased
from datetime import datetime

from corposostenibile.models import (
    Cliente, WeeklyCheckResponse, WeeklyCheck, User, 
    UserRoleEnum, Team, Review, ReviewMessage,
    cliente_nutrizionisti, cliente_coaches, cliente_psicologi, cliente_consulenti
)
from corposostenibile.extensions import db
from corposostenibile.blueprints.search import bp

@bp.route('/global', methods=['GET'])
def global_search():
    """
    Global search endpoint across multiple entities.
    Query params:
        q: search query string
        category: optional filter (paziente, check, professional, training)
    """
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    if not q or len(q) < 2:
        return jsonify({
            'results': [],
            'counts': {'all': 0, 'paziente': 0, 'check': 0, 'professional': 0, 'training': 0},
            'pagination': {'page': page, 'per_page': per_page, 'total': 0, 'pages': 0}
        })
        
    results = []
    counts = {'all': 0, 'paziente': 0, 'check': 0, 'professional': 0, 'training': 0}
    pagination_meta = {'page': page, 'per_page': per_page, 'total': 0, 'pages': 0}
    
    # helper for role-based cliente filtering
    def get_clienti_query_filtered(query):
        if current_user.role == UserRoleEnum.admin or current_user.role == UserRoleEnum.health_manager:
            return query
        elif current_user.role == UserRoleEnum.team_leader:
            # Separare i team per tipo per applicare il filtro corretto
            hm_team_member_ids = {current_user.id}
            prof_team_member_ids = {current_user.id}
            
            for team in (current_user.teams_led or []):
                team_type = getattr(getattr(team, 'team_type', None), 'value', getattr(team, 'team_type', None))
                team_type_str = str(team_type or '').strip().lower()
                
                if team_type_str == 'health_manager':
                    for member in (team.members or []):
                        hm_team_member_ids.add(member.id)
                else:
                    for member in (team.members or []):
                        prof_team_member_ids.add(member.id)
            
            filters = []
            
            # Filtro per team HM
            if len(hm_team_member_ids) > 1:
                hm_ids = list(hm_team_member_ids)
                filters.append(Cliente.health_manager_id.in_(hm_ids))
            
            # Filtro per team altre specialità
            if len(prof_team_member_ids) > 1:
                prof_ids = list(prof_team_member_ids)
                filters.extend([
                    Cliente.nutrizionista_id.in_(prof_ids),
                    Cliente.coach_id.in_(prof_ids),
                    Cliente.psicologa_id.in_(prof_ids),
                    Cliente.consulente_alimentare_id.in_(prof_ids),
                    exists().where(cliente_nutrizionisti.c.cliente_id == Cliente.cliente_id).where(cliente_nutrizionisti.c.user_id.in_(prof_ids)),
                    exists().where(cliente_coaches.c.cliente_id == Cliente.cliente_id).where(cliente_coaches.c.user_id.in_(prof_ids)),
                    exists().where(cliente_psicologi.c.cliente_id == Cliente.cliente_id).where(cliente_psicologi.c.user_id.in_(prof_ids)),
                    exists().where(cliente_consulenti.c.cliente_id == Cliente.cliente_id).where(cliente_consulenti.c.user_id.in_(prof_ids))
                ])
            
            if filters:
                return query.filter(or_(*filters))
            return query.filter(False)
        else: # professionista
            u_id = current_user.id
            return query.filter(
                or_(
                    # Assegnazione tramite FK singola
                    Cliente.nutrizionista_id == u_id,
                    Cliente.coach_id == u_id,
                    Cliente.psicologa_id == u_id,
                    Cliente.consulente_alimentare_id == u_id,
                    # Assegnazione Health Manager (FK)
                    Cliente.health_manager_id == u_id,
                    # Assegnazione tramite M2M
                    exists().where(cliente_nutrizionisti.c.cliente_id == Cliente.cliente_id).where(cliente_nutrizionisti.c.user_id == u_id),
                    exists().where(cliente_coaches.c.cliente_id == Cliente.cliente_id).where(cliente_coaches.c.user_id == u_id),
                    exists().where(cliente_psicologi.c.cliente_id == Cliente.cliente_id).where(cliente_psicologi.c.user_id == u_id),
                    exists().where(cliente_consulenti.c.cliente_id == Cliente.cliente_id).where(cliente_consulenti.c.user_id == u_id)
                )
            )

    # --- SEARCH CLIENTI (PAZIENTI) ---
    pazienti_base_query = get_clienti_query_filtered(
        Cliente.query.filter(
            or_(
                Cliente.nome_cognome.ilike(f'%{q}%'),
                Cliente.mail.ilike(f'%{q}%'),
                Cliente.numero_telefono.ilike(f'%{q}%')
            )
        )
    )
    counts['paziente'] = pazienti_base_query.count()
    
    if not category or category == 'paziente':
        # If 'all', only take 10. If specific category, use pagination.
        limit = 10 if not category else per_page
        offset = 0 if not category else (page - 1) * per_page
        
        clienti_results = pazienti_base_query.offset(offset).limit(limit).all()
        
        if category == 'paziente':
            pagination_meta['total'] = counts['paziente']
            pagination_meta['pages'] = (counts['paziente'] + per_page - 1) // per_page

        for c in clienti_results:
            results.append({
                'type': 'paziente',
                'category': 'paziente',
                'id': c.cliente_id,
                'title': c.nome_cognome,
                'subtitle': c.mail or c.numero_telefono or 'Nessun contatto',
                'avatar': None,
                'link': f'/clienti-dettaglio/{c.cliente_id}',
                'metadata': {
                    'tipologia': c.tipologia_cliente.value if c.tipologia_cliente else None,
                    'stato': c.stato_cliente.value if c.stato_cliente else None
                }
            })
    
    # --- SEARCH CHECK RESPONSES (WeeklyCheckResponse) ---
    check_base_query = WeeklyCheckResponse.query \
        .join(WeeklyCheck, WeeklyCheckResponse.weekly_check_id == WeeklyCheck.id) \
        .join(Cliente, WeeklyCheck.cliente_id == Cliente.cliente_id) \
        .filter(
            or_(
                Cliente.nome_cognome.ilike(f'%{q}%'),
                Cliente.mail.ilike(f'%{q}%')
            )
        )
    
    # Apply role filtering (re-using patient filter logic but on the joined Cliente)
    if current_user.role == UserRoleEnum.admin or current_user.role == UserRoleEnum.health_manager:
        pass
    elif current_user.role == UserRoleEnum.team_leader:
        # Separare i team per tipo per applicare il filtro corretto
        hm_team_member_ids = {current_user.id}
        prof_team_member_ids = {current_user.id}
        
        for team in (current_user.teams_led or []):
            team_type = getattr(getattr(team, 'team_type', None), 'value', getattr(team, 'team_type', None))
            team_type_str = str(team_type or '').strip().lower()
            
            if team_type_str == 'health_manager':
                for member in (team.members or []):
                    hm_team_member_ids.add(member.id)
            else:
                for member in (team.members or []):
                    prof_team_member_ids.add(member.id)
        
        filters = []
        
        # Filtro per team HM
        if len(hm_team_member_ids) > 1:
            hm_ids = list(hm_team_member_ids)
            filters.append(Cliente.health_manager_id.in_(hm_ids))
        
        # Filtro per team altre specialità
        if len(prof_team_member_ids) > 1:
            prof_ids = list(prof_team_member_ids)
            filters.extend([
                Cliente.nutrizionista_id.in_(prof_ids),
                Cliente.coach_id.in_(prof_ids),
                Cliente.psicologa_id.in_(prof_ids),
                Cliente.consulente_alimentare_id.in_(prof_ids),
                exists().where(cliente_nutrizionisti.c.cliente_id == Cliente.cliente_id).where(cliente_nutrizionisti.c.user_id.in_(prof_ids)),
                exists().where(cliente_coaches.c.cliente_id == Cliente.cliente_id).where(cliente_coaches.c.user_id.in_(prof_ids)),
                exists().where(cliente_psicologi.c.cliente_id == Cliente.cliente_id).where(cliente_psicologi.c.user_id.in_(prof_ids)),
                exists().where(cliente_consulenti.c.cliente_id == Cliente.cliente_id).where(cliente_consulenti.c.user_id.in_(prof_ids))
            ])
        
        if filters:
            check_base_query = check_base_query.filter(or_(*filters))
        else:
            check_base_query = check_base_query.filter(False)
    else: # professionista
        u_id = current_user.id
        check_base_query = check_base_query.filter(
            or_(
                # Assegnazione tramite FK singola
                Cliente.nutrizionista_id == u_id,
                Cliente.coach_id == u_id,
                Cliente.psicologa_id == u_id,
                Cliente.consulente_alimentare_id == u_id,
                # Assegnazione Health Manager (FK)
                Cliente.health_manager_id == u_id,
                # Assegnazione tramite M2M
                exists().where(cliente_nutrizionisti.c.cliente_id == Cliente.cliente_id).where(cliente_nutrizionisti.c.user_id == u_id),
                exists().where(cliente_coaches.c.cliente_id == Cliente.cliente_id).where(cliente_coaches.c.user_id == u_id),
                exists().where(cliente_psicologi.c.cliente_id == Cliente.cliente_id).where(cliente_psicologi.c.user_id == u_id),
                exists().where(cliente_consulenti.c.cliente_id == Cliente.cliente_id).where(cliente_consulenti.c.user_id == u_id)
            )
        )

    counts['check'] = check_base_query.count()

    if not category or category == 'check':
        limit = 10 if not category else per_page
        offset = 0 if not category else (page - 1) * per_page
        
        check_results = check_base_query.order_by(desc(WeeklyCheckResponse.submit_date)).offset(offset).limit(limit).all()
        
        if category == 'check':
            pagination_meta['total'] = counts['check']
            pagination_meta['pages'] = (counts['check'] + per_page - 1) // per_page
        
        for check in check_results:
            assignment = check.assignment
            cliente = assignment.cliente if assignment else None
            date_str = check.submit_date.strftime('%d/%m/%Y') if check.submit_date else 'N/A'
            ratings = [check.nutritionist_rating, check.psychologist_rating, check.coach_rating, check.progress_rating]
            valid_ratings = [r for r in ratings if r is not None]
            avg_rating = round(sum(valid_ratings) / len(valid_ratings), 1) if valid_ratings else None
            subtitle_parts = [date_str]
            if avg_rating: subtitle_parts.append(f'Voto: {avg_rating}')
            patient_name = cliente.nome_cognome if cliente else "Paziente"
            
            results.append({
                'type': 'check',
                'category': 'check',
                'id': check.id,
                'title': f'Check di {patient_name}',
                'subtitle': ' - '.join(subtitle_parts),
                'avatar': None,
                'link': f'/check-azienda?highlight={check.id}',
                'metadata': {
                    'patient_id': cliente.cliente_id if cliente else None,
                    'patient_name': patient_name,
                    'date': date_str,
                    'avg_rating': avg_rating
                }
            })
    
    # --- SEARCH PROFESSIONALS (USERS) ---
    users_base_query = User.query.filter(
        User.is_active == True,
        User.is_trial == False,
        or_(
            User.first_name.ilike(f'%{q}%'),
            User.last_name.ilike(f'%{q}%'),
            User.email.ilike(f'%{q}%')
        )
    )
    if current_user.role != UserRoleEnum.admin:
        my_team_ids = [t.id for t in current_user.teams]
        if my_team_ids:
            users_base_query = users_base_query.join(User.teams).filter(Team.id.in_(my_team_ids))
        else:
            users_base_query = users_base_query.filter(User.id == current_user.id)

    counts['professional'] = users_base_query.count()

    if not category or category == 'professional':
        limit = 10 if not category else per_page
        offset = 0 if not category else (page - 1) * per_page
        
        user_results = users_base_query.offset(offset).limit(limit).all()
        
        if category == 'professional':
            pagination_meta['total'] = counts['professional']
            pagination_meta['pages'] = (counts['professional'] + per_page - 1) // per_page
        
        for user in user_results:
            full_name = f"{user.first_name} {user.last_name}".strip()
            specialty_label = None
            if user.specialty:
                specialty_map = {'nutrizione': 'Nutrizionista', 'psicologia': 'Psicologo/a', 'coach': 'Coach', 'consulente': 'Consulente'}
                try: val = user.specialty.value; specialty_label = specialty_map.get(val, val.title())
                except: specialty_label = str(user.specialty)
            
            subtitle_parts = [user.email]
            if specialty_label: subtitle_parts.insert(0, specialty_label)
            
            results.append({
                'type': 'professional',
                'category': 'professional',
                'id': user.id,
                'title': full_name,
                'subtitle': ' - '.join(subtitle_parts),
                'avatar': user.avatar_path,
                'link': f'/team-dettaglio/{user.id}',
                'metadata': {
                    'email': user.email,
                    'specialty': user.specialty.value if user.specialty and hasattr(user.specialty, 'value') else str(user.specialty) if user.specialty else None,
                    'role': user.role.value if user.role and hasattr(user.role, 'value') else str(user.role) if user.role else None,
                    'is_admin': user.is_admin
                }
            })

    # --- SEARCH TRAININGS (REVIEWS + CHAT MESSAGES) ---
    message_sender = aliased(User)
    reviewer_user = aliased(User)
    reviewee_user = aliased(User)

    message_match_exists = db.session.query(ReviewMessage.id) \
        .join(message_sender, ReviewMessage.sender_id == message_sender.id) \
        .filter(
            ReviewMessage.review_id == Review.id,
            ReviewMessage.deleted_at.is_(None),
            or_(
                ReviewMessage.content.ilike(f'%{q}%'),
                message_sender.first_name.ilike(f'%{q}%'),
                message_sender.last_name.ilike(f'%{q}%'),
                message_sender.email.ilike(f'%{q}%')
            )
        ).exists()

    training_base_query = Review.query \
        .join(reviewer_user, Review.reviewer_id == reviewer_user.id) \
        .join(reviewee_user, Review.reviewee_id == reviewee_user.id) \
        .filter(
            Review.deleted_at.is_(None),
            Review.is_draft.is_(False),
            or_(
                Review.title.ilike(f'%{q}%'),
                Review.content.ilike(f'%{q}%'),
                message_match_exists
            )
        )

    # Le review private restano visibili solo ad admin e reviewer
    if current_user.role != UserRoleEnum.admin:
        training_base_query = training_base_query.filter(
            or_(
                Review.is_private.is_(False),
                Review.reviewer_id == current_user.id
            )
        )

    # Permessi per ruolo
    if current_user.role == UserRoleEnum.admin:
        pass
    elif current_user.role == UserRoleEnum.team_leader:
        team_member_ids = set()
        for team in (current_user.teams_led or []):
            for member in (team.members or []):
                team_member_ids.add(member.id)
        team_member_ids.add(current_user.id)
        training_base_query = training_base_query.filter(
            or_(
                Review.reviewer_id.in_(list(team_member_ids)),
                Review.reviewee_id.in_(list(team_member_ids))
            )
        )
    else:
        training_base_query = training_base_query.filter(
            or_(
                Review.reviewer_id == current_user.id,
                Review.reviewee_id == current_user.id
            )
        )

    counts['training'] = training_base_query.count()

    if not category or category == 'training':
        limit = 10 if not category else per_page
        offset = 0 if not category else (page - 1) * per_page

        training_results = training_base_query.order_by(desc(Review.updated_at)).offset(offset).limit(limit).all()

        if category == 'training':
            pagination_meta['total'] = counts['training']
            pagination_meta['pages'] = (counts['training'] + per_page - 1) // per_page

        for review in training_results:
            reviewer_name = f"{review.reviewer.first_name or ''} {review.reviewer.last_name or ''}".strip() if review.reviewer else "N/A"
            reviewee_name = f"{review.reviewee.first_name or ''} {review.reviewee.last_name or ''}".strip() if review.reviewee else "N/A"
            date_str = review.updated_at.strftime('%d/%m/%Y') if review.updated_at else 'N/A'
            training_tab = 'trainings'
            if review.reviewer_id == current_user.id and review.reviewee_id != current_user.id:
                training_tab = 'given'

            results.append({
                'type': 'training',
                'category': 'training',
                'id': review.id,
                'title': review.title or f"Training #{review.id}",
                'subtitle': f'Da {reviewer_name} a {reviewee_name} - {date_str}',
                'avatar': None,
                'link': f'/formazione?trainingId={review.id}&trainingTab={training_tab}',
                'metadata': {
                    'review_type': review.review_type,
                    'reviewer_id': review.reviewer_id,
                    'reviewee_id': review.reviewee_id,
                    'is_private': review.is_private
                }
            })
    
    counts['all'] = counts['paziente'] + counts['check'] + counts['professional'] + counts['training']
    
    return jsonify({
        'results': results,
        'counts': counts,
        'pagination': pagination_meta
    })
