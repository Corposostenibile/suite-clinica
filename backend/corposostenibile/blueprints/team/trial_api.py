"""
API JSON per la gestione degli User in prova (Trial Users)
Per il frontend React.
"""
from flask import jsonify, request, abort
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import text, func
from sqlalchemy.orm import joinedload

from corposostenibile.extensions import db, csrf
from corposostenibile.models import User, Cliente, Department, Team, trial_user_clients, team_members, UserRoleEnum, UserSpecialtyEnum
from . import team_bp
from .api import team_api_bp


def _is_admin_user(user):
    """Riconosce admin sia da flag booleano sia da ruolo enum/stringa."""
    if getattr(user, "is_admin", False):
        return True
    role = getattr(user, "role", None)
    role_value = role.value if hasattr(role, "value") else role
    return role_value == "admin"


def _get_user_department(user):
    """Ottieni il dipartimento di un utente attraverso il suo team"""
    # Prima controlla se è head di un dipartimento
    if user.departments_led:
        return user.departments_led[0]
    # Altrimenti prendi il dipartimento dal primo team
    if user.teams:
        for team in user.teams:
            if team.department:
                return team.department
    return None


def _check_trial_permission():
    """Verifica permessi per gestione trial users"""
    if not current_user.is_authenticated:
        return False, 401

    if _is_admin_user(current_user):
        return True, None

    # Check se è head di un dipartimento
    if current_user.departments_led:
        return True, None

    # Check se è supervisor di qualche trial user
    supervised = User.query.filter_by(
        trial_supervisor_id=current_user.id,
        is_trial=True
    ).count()

    if supervised > 0:
        return True, None

    return False, 403


def _can_manage_trial_user(user):
    """Verifica se current_user può gestire uno specifico trial user"""
    if _is_admin_user(current_user):
        return True

    # Head di un dipartimento
    if current_user.departments_led:
        return True

    # Supervisor diretto
    return user.trial_supervisor_id == current_user.id


def _serialize_trial_user(user, include_clients=False):
    """Serializza un trial user per JSON response"""
    # Ottieni department via team
    dept = _get_user_department(user)
    # Ottieni specialty come stringa
    specialty_val = None
    if user.specialty:
        specialty_val = user.specialty.value if hasattr(user.specialty, 'value') else str(user.specialty)

    data = {
        'id': user.id,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'full_name': user.full_name,
        'specialty': specialty_val,
        'avatar_path': user.avatar_path,
        'is_active': user.is_active,
        'is_trial': user.is_trial,
        'trial_stage': user.trial_stage,
        'trial_stage_description': user.trial_stage_description,
        'trial_started_at': user.trial_started_at.isoformat() if user.trial_started_at else None,
        'trial_promoted_at': user.trial_promoted_at.isoformat() if user.trial_promoted_at else None,
        'department': {
            'id': dept.id,
            'name': dept.name
        } if dept else None,
        'team': {
            'id': user.teams[0].id,
            'name': user.teams[0].name
        } if user.teams and len(user.teams) > 0 else None,
        'supervisor': {
            'id': user.trial_supervisor.id,
            'full_name': user.trial_supervisor.full_name,
            'avatar_path': user.trial_supervisor.avatar_path
        } if user.trial_supervisor else None,
        'assigned_clients_count': len(user.trial_assigned_clients) if user.trial_assigned_clients else 0
    }

    if include_clients:
        # Carica clienti con dettagli
        assigned = db.session.query(
            Cliente,
            trial_user_clients.c.assigned_at,
            trial_user_clients.c.notes,
            User.first_name.label('assigned_by_first'),
            User.last_name.label('assigned_by_last')
        ).join(
            trial_user_clients,
            Cliente.cliente_id == trial_user_clients.c.cliente_id
        ).outerjoin(
            User,
            User.id == trial_user_clients.c.assigned_by
        ).filter(
            trial_user_clients.c.user_id == user.id
        ).order_by(
            trial_user_clients.c.assigned_at.desc()
        ).all()

        data['assigned_clients'] = [{
            'cliente_id': c.Cliente.cliente_id,
            'nome_cognome': c.Cliente.nome_cognome,
            'tipologia_cliente': c.Cliente.tipologia_cliente.value if c.Cliente.tipologia_cliente else None,
            'stato': c.Cliente.stato_cliente.value if c.Cliente.stato_cliente else None,
            'assigned_at': c.assigned_at.isoformat() if c.assigned_at else None,
            'assigned_by': f"{c.assigned_by_first} {c.assigned_by_last}" if c.assigned_by_first else None,
            'notes': c.notes
        } for c in assigned]

    return data


# ==================== API ENDPOINTS ====================

@team_bp.route('/api/trial-users', methods=['GET'])
@team_api_bp.route('/trial-users', methods=['GET'])
@login_required
def api_trial_users_list():
    """
    GET /team/api/trial-users
    Lista tutti i trial users (filtrati per permessi)
    """
    allowed, error_code = _check_trial_permission()
    if not allowed:
        return jsonify({'success': False, 'error': 'Non autorizzato'}), error_code

    try:
        # Check se è head di un dipartimento
        is_dept_head = bool(current_user.departments_led)

        # Query base
        query = User.query.filter_by(is_trial=True)

        # Se non admin/head, filtra per supervised
        if not _is_admin_user(current_user) and not is_dept_head:
            query = query.filter_by(trial_supervisor_id=current_user.id)

        users = query.order_by(User.trial_stage, User.first_name).all()

        # Statistiche
        stats = {
            'total': len(users),
            'stage_1': sum(1 for u in users if u.trial_stage == 1),
            'stage_2': sum(1 for u in users if u.trial_stage == 2),
            'stage_3': sum(1 for u in users if u.trial_stage == 3)
        }

        return jsonify({
            'success': True,
            'trial_users': [_serialize_trial_user(u) for u in users],
            'stats': stats
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@team_bp.route('/api/trial-users/<int:user_id>', methods=['GET'])
@team_api_bp.route('/trial-users/<int:user_id>', methods=['GET'])
@login_required
def api_trial_user_detail(user_id):
    """
    GET /team/api/trial-users/<id>
    Dettaglio singolo trial user con clienti assegnati
    """
    allowed, error_code = _check_trial_permission()
    if not allowed:
        return jsonify({'success': False, 'error': 'Non autorizzato'}), error_code

    try:
        user = User.query.get(user_id)

        if not user:
            return jsonify({'success': False, 'error': 'Utente non trovato'}), 404

        if not _can_manage_trial_user(user):
            return jsonify({'success': False, 'error': 'Non autorizzato'}), 403

        return jsonify({
            'success': True,
            'trial_user': _serialize_trial_user(user, include_clients=True)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@team_bp.route('/api/trial-users', methods=['POST'])
@team_api_bp.route('/trial-users', methods=['POST'])
@csrf.exempt
@login_required
def api_trial_user_create():
    """
    POST /team/api/trial-users
    Crea nuovo trial user

    Body: {
        email, first_name, last_name, password,
        job_title?, specialty?, department_id?,
        trial_stage?, trial_supervisor_id?
    }
    """
    allowed, error_code = _check_trial_permission()
    if not allowed:
        return jsonify({'success': False, 'error': 'Non autorizzato'}), error_code

    try:
        data = request.get_json() or {}

        # Validazione campi obbligatori
        required = ['email', 'first_name', 'last_name', 'password']
        for field in required:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'Campo {field} obbligatorio'}), 400

        # Check email univoca
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'success': False, 'error': 'Email già registrata'}), 400

        # Gestisci specialty come enum
        specialty_val = data.get('specialty')
        if specialty_val:
            from corposostenibile.models import UserSpecialtyEnum
            try:
                specialty_val = UserSpecialtyEnum(specialty_val)
            except (ValueError, KeyError):
                specialty_val = None

        user = User(
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            specialty=specialty_val,
            is_trial=True,
            trial_stage=data.get('trial_stage', 1),
            trial_started_at=datetime.utcnow(),
            trial_supervisor_id=data.get('trial_supervisor_id') or current_user.id,
            is_active=True
        )

        user.set_password(data['password'])

        db.session.add(user)
        db.session.flush()  # Get the user.id

        # Assegna team se specificato
        team_id = data.get('team_id')
        if team_id:
            db.session.execute(
                text("INSERT INTO team_members (team_id, user_id, joined_at) VALUES (:tid, :uid, :now)"),
                {"tid": team_id, "uid": user.id, "now": datetime.utcnow()}
            )

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f"Trial user '{user.full_name}' creato con successo",
            'trial_user': _serialize_trial_user(user)
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@team_bp.route('/api/trial-users/<int:user_id>', methods=['PUT'])
@team_api_bp.route('/trial-users/<int:user_id>', methods=['PUT'])
@csrf.exempt
@login_required
def api_trial_user_update(user_id):
    """
    PUT /team/api/trial-users/<id>
    Aggiorna trial user
    """
    allowed, error_code = _check_trial_permission()
    if not allowed:
        return jsonify({'success': False, 'error': 'Non autorizzato'}), error_code

    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'Utente non trovato'}), 404

        if not _can_manage_trial_user(user):
            return jsonify({'success': False, 'error': 'Non autorizzato'}), 403

        data = request.get_json() or {}

        # Aggiorna campi
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'email' in data:
            # Check univocità
            existing = User.query.filter(User.email == data['email'], User.id != user_id).first()
            if existing:
                return jsonify({'success': False, 'error': 'Email già registrata'}), 400
            user.email = data['email']
        if 'specialty' in data:
            from corposostenibile.models import UserSpecialtyEnum
            specialty_val = data['specialty']
            if specialty_val:
                try:
                    user.specialty = UserSpecialtyEnum(specialty_val)
                except (ValueError, KeyError):
                    user.specialty = None
            else:
                user.specialty = None
        if 'team_id' in data:
            # Rimuovi dal team corrente e aggiungi al nuovo
            db.session.execute(
                text("DELETE FROM team_members WHERE user_id = :uid"),
                {"uid": user_id}
            )
            if data['team_id']:
                db.session.execute(
                    text("INSERT INTO team_members (team_id, user_id, joined_at) VALUES (:tid, :uid, :now)"),
                    {"tid": data['team_id'], "uid": user_id, "now": datetime.utcnow()}
                )
        if 'trial_supervisor_id' in data:
            user.trial_supervisor_id = data['trial_supervisor_id'] if data['trial_supervisor_id'] else None
        if 'password' in data and data['password']:
            user.set_password(data['password'])
        if 'is_active' in data:
            user.is_active = data['is_active']

        # Gestione cambio stage
        if 'trial_stage' in data:
            new_stage = data['trial_stage']
            if new_stage == 3:
                # Promozione a user ufficiale
                user.is_trial = False
                user.trial_stage = 3
                user.trial_promoted_at = datetime.utcnow()
            else:
                user.trial_stage = new_stage

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f"Trial user '{user.full_name}' aggiornato",
            'trial_user': _serialize_trial_user(user)
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@team_bp.route('/api/trial-users/<int:user_id>/promote', methods=['POST'])
@team_api_bp.route('/trial-users/<int:user_id>/promote', methods=['POST'])
@csrf.exempt
@login_required
def api_trial_user_promote(user_id):
    """
    POST /team/api/trial-users/<id>/promote
    Promuovi trial user allo stage successivo
    """
    allowed, error_code = _check_trial_permission()
    if not allowed:
        return jsonify({'success': False, 'error': 'Non autorizzato'}), error_code

    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'Utente non trovato'}), 404

        if not _can_manage_trial_user(user):
            return jsonify({'success': False, 'error': 'Non autorizzato'}), 403

        if not user.is_trial:
            return jsonify({'success': False, 'error': 'Non è un trial user'}), 400

        old_stage = user.trial_stage

        if user.promote_to_next_stage():
            return jsonify({
                'success': True,
                'message': f"Promosso da Stage {old_stage} a {user.trial_stage_description}",
                'trial_user': _serialize_trial_user(user)
            })
        else:
            return jsonify({'success': False, 'error': 'Impossibile promuovere'}), 400

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@team_bp.route('/api/trial-users/<int:user_id>/assign-clients', methods=['POST'])
@team_api_bp.route('/trial-users/<int:user_id>/assign-clients', methods=['POST'])
@csrf.exempt
@login_required
def api_trial_user_assign_clients(user_id):
    """
    POST /team/api/trial-users/<id>/assign-clients
    Assegna clienti a trial user

    Body: { cliente_ids: [1, 2, 3], notes?: "..." }
    """
    allowed, error_code = _check_trial_permission()
    if not allowed:
        return jsonify({'success': False, 'error': 'Non autorizzato'}), error_code

    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'Utente non trovato'}), 404

        if not _can_manage_trial_user(user):
            return jsonify({'success': False, 'error': 'Non autorizzato'}), 403

        if not user.is_trial or user.trial_stage < 2:
            return jsonify({'success': False, 'error': 'User deve essere in Stage 2+'}), 400

        data = request.get_json() or {}
        cliente_ids = data.get('cliente_ids', [])
        notes = data.get('notes', '')

        if not cliente_ids:
            return jsonify({'success': False, 'error': 'Nessun cliente selezionato'}), 400

        assigned_count = 0
        for cliente_id in cliente_ids:
            # Check non già assegnato
            existing = db.session.execute(
                text("SELECT 1 FROM trial_user_clients WHERE user_id = :uid AND cliente_id = :cid"),
                {"uid": user_id, "cid": cliente_id}
            ).first()

            if not existing:
                db.session.execute(
                    text("""
                        INSERT INTO trial_user_clients (user_id, cliente_id, assigned_at, assigned_by, notes)
                        VALUES (:uid, :cid, :at, :by, :notes)
                    """),
                    {
                        "uid": user_id,
                        "cid": cliente_id,
                        "at": datetime.utcnow(),
                        "by": current_user.id,
                        "notes": notes
                    }
                )
                assigned_count += 1

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f"{assigned_count} clienti assegnati",
            'assigned_count': assigned_count
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@team_bp.route('/api/trial-users/<int:user_id>/remove-client/<int:cliente_id>', methods=['DELETE'])
@team_api_bp.route('/trial-users/<int:user_id>/remove-client/<int:cliente_id>', methods=['DELETE'])
@csrf.exempt
@login_required
def api_trial_user_remove_client(user_id, cliente_id):
    """
    DELETE /team/api/trial-users/<id>/remove-client/<cliente_id>
    Rimuovi cliente da trial user
    """
    allowed, error_code = _check_trial_permission()
    if not allowed:
        return jsonify({'success': False, 'error': 'Non autorizzato'}), error_code

    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'Utente non trovato'}), 404

        if not _can_manage_trial_user(user):
            return jsonify({'success': False, 'error': 'Non autorizzato'}), 403

        db.session.execute(
            text("DELETE FROM trial_user_clients WHERE user_id = :uid AND cliente_id = :cid"),
            {"uid": user_id, "cid": cliente_id}
        )
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Cliente rimosso'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@team_bp.route('/api/trial-users/<int:user_id>', methods=['DELETE'])
@team_api_bp.route('/trial-users/<int:user_id>', methods=['DELETE'])
@csrf.exempt
@login_required
def api_trial_user_delete(user_id):
    """
    DELETE /team/api/trial-users/<id>
    Elimina trial user
    """
    allowed, error_code = _check_trial_permission()
    if not allowed:
        return jsonify({'success': False, 'error': 'Non autorizzato'}), error_code

    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'Utente non trovato'}), 404

        if not user.is_trial:
            return jsonify({'success': False, 'error': 'Non è un trial user'}), 400

        if not _can_manage_trial_user(user):
            return jsonify({'success': False, 'error': 'Non autorizzato'}), 403

        name = user.full_name

        # Rimuovi clienti assegnati (svuota relazione ORM)
        user.trial_assigned_clients = []
        db.session.flush()

        # Elimina user
        db.session.delete(user)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f"Trial user '{name}' eliminato"
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@team_bp.route('/api/trial-users/available-clients', methods=['GET'])
@team_api_bp.route('/trial-users/available-clients', methods=['GET'])
@login_required
def api_trial_users_available_clients():
    """
    GET /team/api/trial-users/available-clients?user_id=X
    Lista clienti disponibili per assegnazione (non ancora assegnati)
    """
    allowed, error_code = _check_trial_permission()
    if not allowed:
        return jsonify({'success': False, 'error': 'Non autorizzato'}), error_code

    try:
        user_id = request.args.get('user_id', type=int)
        search = request.args.get('search', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)

        # Query clienti attivi
        from corposostenibile.models import StatoClienteEnum
        query = Cliente.query.filter(
            Cliente.stato_cliente == StatoClienteEnum.attivo
        )

        # Escludi già assegnati se user_id specificato
        if user_id:
            assigned_subq = db.session.query(trial_user_clients.c.cliente_id).filter(
                trial_user_clients.c.user_id == user_id
            ).subquery()
            query = query.filter(~Cliente.cliente_id.in_(db.session.query(assigned_subq)))

        # Ricerca per nome
        if search:
            query = query.filter(Cliente.nome_cognome.ilike(f'%{search}%'))

        # Paginazione
        total = query.count()
        clients = query.order_by(Cliente.nome_cognome).offset((page - 1) * per_page).limit(per_page).all()

        return jsonify({
            'success': True,
            'clients': [{
                'id': c.cliente_id,
                'nome': c.nome_cognome.split(' ')[0] if c.nome_cognome else '',
                'cognome': ' '.join(c.nome_cognome.split(' ')[1:]) if c.nome_cognome and ' ' in c.nome_cognome else '',
                'nome_cognome': c.nome_cognome,
                'email': c.mail,
                'pacchetto': c.programma_attuale,
                'tipologia_cliente': c.tipologia_cliente.value if c.tipologia_cliente else None,
            } for c in clients],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@team_bp.route('/api/trial-users/supervisors', methods=['GET'])
@team_api_bp.route('/trial-users/supervisors', methods=['GET'])
@login_required
def api_trial_users_supervisors():
    """
    GET /team/api/trial-users/supervisors?specialty=nutrizione
    Lista potenziali supervisori (admin e team_leader) filtrabili per specialty
    """
    allowed, error_code = _check_trial_permission()
    if not allowed:
        return jsonify({'success': False, 'error': 'Non autorizzato'}), error_code

    try:
        specialty_filter = request.args.get('specialty', '').strip()

        # Admin e team_leader
        supervisors = User.query.filter(
            User.is_active == True,
            db.or_(
                User.is_admin == True,
                User.role == UserRoleEnum.team_leader
            )
        ).order_by(User.first_name, User.last_name).all()

        # Filtra per specialty se specificato
        if specialty_filter:
            filtered = []
            for u in supervisors:
                if u.is_admin:
                    # Admin: mostra se ha la specialty richiesta o se non ne ha una specifica
                    spec_val = u.specialty.value if hasattr(u.specialty, 'value') else str(u.specialty) if u.specialty else None
                    if not spec_val or spec_val == specialty_filter or spec_val in ('amministrazione', 'cco'):
                        filtered.append(u)
                else:
                    # Team leader: mostra solo se ha la specialty richiesta
                    spec_val = u.specialty.value if hasattr(u.specialty, 'value') else str(u.specialty) if u.specialty else None
                    if spec_val == specialty_filter:
                        filtered.append(u)
            supervisors = filtered

        return jsonify({
            'success': True,
            'supervisors': [{
                'id': u.id,
                'full_name': u.full_name,
                'avatar_path': u.avatar_path,
                'is_admin': u.is_admin,
                'role': u.role.value if hasattr(u.role, 'value') else str(u.role),
                'specialty': u.specialty.value if hasattr(u.specialty, 'value') else str(u.specialty) if u.specialty else None,
                'department': _get_user_department(u).name if _get_user_department(u) else None
            } for u in supervisors]
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
