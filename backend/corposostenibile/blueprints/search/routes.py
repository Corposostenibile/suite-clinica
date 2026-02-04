from flask import jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import or_, desc, exists, select
from datetime import datetime

from corposostenibile.models import (
    Cliente, WeeklyCheckResponse, WeeklyCheck, User, 
    UserRoleEnum, Team,
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
        category: optional filter (paziente, check, professional)
    """
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    
    if not q or len(q) < 2:
        return jsonify([])
        
    results = []
    
    # --- SEARCH CLIENTI (PAZIENTI) ---
    if not category or category == 'paziente':
        clienti_query = Cliente.query.filter(
            or_(
                Cliente.nome_cognome.ilike(f'%{q}%'),
                Cliente.mail.ilike(f'%{q}%'),
                Cliente.numero_telefono.ilike(f'%{q}%')
            )
        )

        # ROLE-BASED FILTERING
        if current_user.role == UserRoleEnum.admin:
            pass
        elif current_user.role == UserRoleEnum.team_leader:
            team_member_ids = set()
            for team in (current_user.teams_led or []):
                for member in (team.members or []):
                    team_member_ids.add(member.id)
            
            if team_member_ids:
                m_ids = list(team_member_ids)
                clienti_query = clienti_query.filter(
                    or_(
                        exists().where(cliente_nutrizionisti.c.cliente_id == Cliente.cliente_id).where(cliente_nutrizionisti.c.user_id.in_(m_ids)),
                        exists().where(cliente_coaches.c.cliente_id == Cliente.cliente_id).where(cliente_coaches.c.user_id.in_(m_ids)),
                        exists().where(cliente_psicologi.c.cliente_id == Cliente.cliente_id).where(cliente_psicologi.c.user_id.in_(m_ids)),
                        exists().where(cliente_consulenti.c.cliente_id == Cliente.cliente_id).where(cliente_consulenti.c.user_id.in_(m_ids))
                    )
                )
            else:
                clienti_query = clienti_query.filter(False)
        else: # professionista
            u_id = current_user.id
            clienti_query = clienti_query.filter(
                or_(
                    exists().where(cliente_nutrizionisti.c.cliente_id == Cliente.cliente_id).where(cliente_nutrizionisti.c.user_id == u_id),
                    exists().where(cliente_coaches.c.cliente_id == Cliente.cliente_id).where(cliente_coaches.c.user_id == u_id),
                    exists().where(cliente_psicologi.c.cliente_id == Cliente.cliente_id).where(cliente_psicologi.c.user_id == u_id),
                    exists().where(cliente_consulenti.c.cliente_id == Cliente.cliente_id).where(cliente_consulenti.c.user_id == u_id)
                )
            )

        clienti_results = clienti_query.limit(10).all()
        
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
    if not category or category == 'check':
        # Search by patient name in WEEKLY check responses
        # Join: WeeklyCheckResponse -> WeeklyCheck -> Cliente
        check_query = WeeklyCheckResponse.query \
            .join(WeeklyCheck, WeeklyCheckResponse.weekly_check_id == WeeklyCheck.id) \
            .join(Cliente, WeeklyCheck.cliente_id == Cliente.cliente_id) \
            .filter(
                or_(
                    Cliente.nome_cognome.ilike(f'%{q}%'),
                    Cliente.mail.ilike(f'%{q}%')
                )
            )

        # ROLE-BASED FILTERING
        if current_user.role == UserRoleEnum.admin:
            pass
        elif current_user.role == UserRoleEnum.team_leader:
            team_member_ids = set()
            for team in (current_user.teams_led or []):
                for member in (team.members or []):
                    team_member_ids.add(member.id)
            
            if team_member_ids:
                m_ids = list(team_member_ids)
                check_query = check_query.filter(
                    or_(
                        exists().where(cliente_nutrizionisti.c.cliente_id == Cliente.cliente_id).where(cliente_nutrizionisti.c.user_id.in_(m_ids)),
                        exists().where(cliente_coaches.c.cliente_id == Cliente.cliente_id).where(cliente_coaches.c.user_id.in_(m_ids)),
                        exists().where(cliente_psicologi.c.cliente_id == Cliente.cliente_id).where(cliente_psicologi.c.user_id.in_(m_ids)),
                        exists().where(cliente_consulenti.c.cliente_id == Cliente.cliente_id).where(cliente_consulenti.c.user_id.in_(m_ids))
                    )
                )
            else:
                check_query = check_query.filter(False)
        else: # professionista
            u_id = current_user.id
            check_query = check_query.filter(
                or_(
                    exists().where(cliente_nutrizionisti.c.cliente_id == Cliente.cliente_id).where(cliente_nutrizionisti.c.user_id == u_id),
                    exists().where(cliente_coaches.c.cliente_id == Cliente.cliente_id).where(cliente_coaches.c.user_id == u_id),
                    exists().where(cliente_psicologi.c.cliente_id == Cliente.cliente_id).where(cliente_psicologi.c.user_id == u_id),
                    exists().where(cliente_consulenti.c.cliente_id == Cliente.cliente_id).where(cliente_consulenti.c.user_id == u_id)
                )
            )

        check_results = check_query.order_by(desc(WeeklyCheckResponse.submit_date)).limit(10).all()
        
        for check in check_results:
            # check.assignment is the WeeklyCheck object
            # check.assignment.cliente is the Cliente
            assignment = check.assignment
            cliente = assignment.cliente if assignment else None
            
            # Format date
            date_str = check.submit_date.strftime('%d/%m/%Y') if check.submit_date else 'N/A'
            
            # Calculate average rating
            ratings = [
                check.nutritionist_rating,
                check.psychologist_rating,
                check.coach_rating,
                check.progress_rating
            ]
            valid_ratings = [r for r in ratings if r is not None]
            avg_rating = round(sum(valid_ratings) / len(valid_ratings), 1) if valid_ratings else None
            
            subtitle_parts = [date_str]
            if avg_rating:
                subtitle_parts.append(f'Voto: {avg_rating}')
            
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
    if not category or category == 'professional':
        # Search in first_name, last_name, email
        # Exclude trial users and inactive users
        users_query = User.query.filter(
            User.is_active == True,
            User.is_trial == False,
            or_(
                User.first_name.ilike(f'%{q}%'),
                User.last_name.ilike(f'%{q}%'),
                User.email.ilike(f'%{q}%')
            )
        )

        # ROLE-BASED FILTERING
        if current_user.role == UserRoleEnum.admin:
            pass
        else:
            # TL and Professionista see users in their same team(s)
            my_team_ids = [t.id for t in current_user.teams]
            if my_team_ids:
                users_query = users_query.join(User.teams).filter(Team.id.in_(my_team_ids))
            else:
                users_query = users_query.filter(User.id == current_user.id)

        user_results = users_query.limit(10).all()
        
        for user in user_results:
            full_name = f"{user.first_name} {user.last_name}".strip()
            
            # Determine specialty label
            specialty_label = None
            if user.specialty:
                specialty_map = {
                    'nutrizione': 'Nutrizionista',
                    'psicologia': 'Psicologo/a',
                    'coach': 'Coach',
                    'consulente': 'Consulente'
                }
                # Handle Enum value access safely
                try:
                    val = user.specialty.value
                    specialty_label = specialty_map.get(val, val.title())
                except:
                    specialty_label = str(user.specialty)
            
            subtitle_parts = [user.email]
            if specialty_label:
                subtitle_parts.insert(0, specialty_label)
            
            results.append({
                'type': 'professional',
                'category': 'professional',
                'id': user.id,
                'title': full_name,
                'subtitle': ' - '.join(subtitle_parts),
                'avatar': user.avatar_path,
                'link': f'/profilo-professionista/{user.id}',
                'metadata': {
                    'email': user.email,
                    'specialty': user.specialty.value if user.specialty and hasattr(user.specialty, 'value') else str(user.specialty) if user.specialty else None,
                    'role': user.role.value if user.role and hasattr(user.role, 'value') else str(user.role) if user.role else None,
                    'is_admin': user.is_admin
                }
            })
        
    return jsonify(results)
