"""
Team API endpoints for React frontend.

This module provides JSON API endpoints for team member CRUD operations.
All endpoints are prefixed with /api/team.
"""

import os
import uuid
from http import HTTPStatus
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_, func
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from corposostenibile.extensions import db, csrf
from corposostenibile.models import User, Department, Team, UserRoleEnum, UserSpecialtyEnum, TeamTypeEnum, team_members


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    """Check if file has allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Create API blueprint with /api/team prefix
team_api_bp = Blueprint(
    "team_api",
    __name__,
    url_prefix="/api/team",
)

# Exempt entire blueprint from CSRF (JSON API)
csrf.exempt(team_api_bp)


# =============================================================================
# Permission Helpers
# =============================================================================

def _require_admin():
    """Check if user is admin."""
    if not (current_user.is_authenticated and current_user.is_admin):
        return jsonify({
            'success': False,
            'message': 'Accesso non autorizzato'
        }), HTTPStatus.FORBIDDEN
    return None


def _get_user_role(user):
    """Get user role from model field."""
    if hasattr(user, 'role') and user.role:
        return user.role.value if hasattr(user.role, 'value') else str(user.role)
    return 'professionista'


def _get_user_specialty(user):
    """Get user specialty from model field."""
    if hasattr(user, 'specialty') and user.specialty:
        return user.specialty.value if hasattr(user.specialty, 'value') else str(user.specialty)
    return None


def _serialize_user(user, include_details=False):
    """Serialize user object to JSON-safe dict."""
    data = {
        'id': user.id,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'full_name': user.full_name,
        'avatar_path': user.avatar_path,
        'is_admin': user.is_admin,
        'is_active': user.is_active,
        'is_external': getattr(user, 'is_external', False),
        'role': _get_user_role(user),
        'specialty': _get_user_specialty(user),
        'teams_led': [
            {'id': t.id, 'name': t.name}
            for t in (user.teams_led or [])
        ] if hasattr(user, 'teams_led') else [],
    }

    if include_details:
        data.update({
            'last_login_at': user.last_login_at.isoformat() if user.last_login_at else None,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'is_trial': user.is_trial,
            'trial_stage': user.trial_stage,
            'assignment_ai_notes': user.assignment_ai_notes or {},
        })

    return data


# =============================================================================
# API Endpoints
# =============================================================================

@team_api_bp.route("/members", methods=["GET"])
@login_required
def get_members():
    """
    Get paginated list of team members.

    Query params:
        - page: Page number (default 1)
        - per_page: Items per page (default 25, max 100)
        - q: Search query (searches name, email)
        - role: Filter by role (admin, team_leader, professionista, team_esterno)
        - specialty: Filter by specialty
        - active: Filter by active status ('1' or '0')
        - department_id: Filter by department
    """
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 25, type=int), 100)
    search_query = request.args.get('q', '').strip()
    role_filter = request.args.get('role', '').strip()
    specialty_filter = request.args.get('specialty', '').strip()
    active_filter = request.args.get('active', '').strip()
    department_id = request.args.get('department_id', type=int)

    # Base query
    query = User.query

    # Search filter
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            or_(
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
                User.email.ilike(search_term),
                func.concat(User.first_name, ' ', User.last_name).ilike(search_term)
            )
        )

    # Active filter
    if active_filter == '1':
        query = query.filter(User.is_active == True)
    elif active_filter == '0':
        query = query.filter(User.is_active == False)

    # Department filter
    if department_id:
        query = query.filter(User.department_id == department_id)

    # Role filter - use new role field directly
    if role_filter:
        if role_filter in [e.value for e in UserRoleEnum]:
            query = query.filter(User.role == UserRoleEnum(role_filter))
        elif role_filter == 'admin':
            # Fallback for old API calls
            query = query.filter(User.is_admin == True)

    # Specialty filter - use new specialty field directly
    # Supports comma-separated values (e.g., "nutrizione,nutrizionista")
    if specialty_filter:
        specialty_values = [s.strip() for s in specialty_filter.split(',')]
        valid_specialties = []
        for sv in specialty_values:
            if sv in [e.value for e in UserSpecialtyEnum]:
                valid_specialties.append(UserSpecialtyEnum(sv))
        if valid_specialties:
            query = query.filter(User.specialty.in_(valid_specialties))

    # Order by name
    query = query.order_by(User.first_name, User.last_name)

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Serialize results
    members = [_serialize_user(user) for user in pagination.items]

    return jsonify({
        'success': True,
        'members': members,
        'total': pagination.total,
        'page': pagination.page,
        'per_page': pagination.per_page,
        'total_pages': pagination.pages,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev,
    })


@team_api_bp.route("/members/<int:user_id>", methods=["GET"])
@login_required
def get_member(user_id):
    """Get single team member details."""
    user = User.query.get_or_404(user_id)

    return jsonify({
        'success': True,
        **_serialize_user(user, include_details=True)
    })


@team_api_bp.route("/members", methods=["POST"])
@login_required
def create_member():
    """Create new team member."""
    # Check admin permission
    perm_error = _require_admin()
    if perm_error:
        return perm_error

    data = request.get_json()
    if not data:
        return jsonify({
            'success': False,
            'message': 'Dati non validi'
        }), HTTPStatus.BAD_REQUEST

    # Validate required fields
    required_fields = ['email', 'password', 'first_name', 'last_name']
    for field in required_fields:
        if not data.get(field):
            return jsonify({
                'success': False,
                'message': f'Campo obbligatorio mancante: {field}'
            }), HTTPStatus.BAD_REQUEST

    # Check email uniqueness
    if User.query.filter_by(email=data['email'].lower()).first():
        return jsonify({
            'success': False,
            'message': 'Email già registrata'
        }), HTTPStatus.BAD_REQUEST

    try:
        # Determine role and flags from input
        role_str = data.get('role', 'professionista')
        is_admin = data.get('is_admin', False) or role_str == 'admin'
        is_external = data.get('is_external', False) or role_str == 'team_esterno'

        # Map role string to enum
        role_enum = UserRoleEnum.professionista  # default
        if role_str in [e.value for e in UserRoleEnum]:
            role_enum = UserRoleEnum(role_str)

        # Map specialty string to enum (if provided)
        specialty_enum = None
        specialty_str = data.get('specialty')
        if specialty_str and specialty_str in [e.value for e in UserSpecialtyEnum]:
            specialty_enum = UserSpecialtyEnum(specialty_str)

        # Create user
        user = User(
            email=data['email'].lower(),
            first_name=data['first_name'],
            last_name=data['last_name'],
            is_admin=is_admin,
            is_active=True,
            role=role_enum,
            specialty=specialty_enum,
            is_external=is_external,
        )

        # Set password
        user.set_password(data['password'])

        db.session.add(user)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Membro creato con successo',
            'id': user.id,
            **_serialize_user(user)
        }), HTTPStatus.CREATED

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating team member: {e}")
        return jsonify({
            'success': False,
            'message': f'Errore durante la creazione: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@team_api_bp.route("/members/<int:user_id>", methods=["PUT"])
@login_required
def update_member(user_id):
    """Update team member."""
    # Check admin permission
    perm_error = _require_admin()
    if perm_error:
        return perm_error

    user = User.query.get_or_404(user_id)
    data = request.get_json()

    if not data:
        return jsonify({
            'success': False,
            'message': 'Dati non validi'
        }), HTTPStatus.BAD_REQUEST

    try:
        # Update allowed fields
        updatable_fields = ['first_name', 'last_name', 'is_admin', 'is_external']

        for field in updatable_fields:
            if field in data:
                setattr(user, field, data[field])

        # Update role (enum field)
        if 'role' in data:
            role_str = data['role']
            if role_str in [e.value for e in UserRoleEnum]:
                user.role = UserRoleEnum(role_str)
                # Sync is_admin and is_external flags
                user.is_admin = role_str == 'admin'
                user.is_external = role_str == 'team_esterno'

        # Update specialty (enum field)
        if 'specialty' in data:
            specialty_str = data['specialty']
            if specialty_str and specialty_str in [e.value for e in UserSpecialtyEnum]:
                user.specialty = UserSpecialtyEnum(specialty_str)
            elif not specialty_str:
                user.specialty = None

        # Update email (check uniqueness)
        if 'email' in data and data['email'].lower() != user.email:
            if User.query.filter_by(email=data['email'].lower()).first():
                return jsonify({
                    'success': False,
                    'message': 'Email già registrata'
                }), HTTPStatus.BAD_REQUEST
            user.email = data['email'].lower()

        # Update password if provided
        if data.get('password'):
            user.set_password(data['password'])

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Membro aggiornato con successo',
            **_serialize_user(user, include_details=True)
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating team member: {e}")
        return jsonify({
            'success': False,
            'message': f'Errore durante l\'aggiornamento: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@team_api_bp.route("/members/<int:user_id>", methods=["DELETE"])
@login_required
def delete_member(user_id):
    """Delete team member (soft delete by deactivating)."""
    # Check admin permission
    perm_error = _require_admin()
    if perm_error:
        return perm_error

    user = User.query.get_or_404(user_id)

    # Prevent self-deletion
    if user.id == current_user.id:
        return jsonify({
            'success': False,
            'message': 'Non puoi eliminare il tuo account'
        }), HTTPStatus.BAD_REQUEST

    try:
        # Soft delete - just deactivate
        user.is_active = False
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Membro disattivato con successo'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting team member: {e}")
        return jsonify({
            'success': False,
            'message': f'Errore durante l\'eliminazione: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@team_api_bp.route("/members/<int:user_id>/toggle", methods=["POST"])
@login_required
def toggle_member_status(user_id):
    """Toggle team member active status."""
    # Check admin permission
    perm_error = _require_admin()
    if perm_error:
        return perm_error

    user = User.query.get_or_404(user_id)

    # Prevent toggling own status
    if user.id == current_user.id:
        return jsonify({
            'success': False,
            'message': 'Non puoi disattivare il tuo account'
        }), HTTPStatus.BAD_REQUEST

    try:
        user.is_active = not user.is_active
        db.session.commit()

        status = 'attivato' if user.is_active else 'disattivato'
        return jsonify({
            'success': True,
            'message': f'Account {status} con successo',
            'is_active': user.is_active
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling team member status: {e}")
        return jsonify({
            'success': False,
            'message': f'Errore: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@team_api_bp.route("/members/<int:user_id>/avatar", methods=["POST"])
@login_required
def upload_avatar(user_id):
    """Upload avatar for team member."""
    # Check admin permission or self
    if not (current_user.is_admin or current_user.id == user_id):
        return jsonify({
            'success': False,
            'message': 'Accesso non autorizzato'
        }), HTTPStatus.FORBIDDEN

    user = User.query.get_or_404(user_id)

    if 'avatar' not in request.files:
        return jsonify({
            'success': False,
            'message': 'Nessun file caricato'
        }), HTTPStatus.BAD_REQUEST

    file = request.files['avatar']
    if file.filename == '':
        return jsonify({
            'success': False,
            'message': 'Nessun file selezionato'
        }), HTTPStatus.BAD_REQUEST

    if not allowed_file(file.filename):
        return jsonify({
            'success': False,
            'message': 'Tipo di file non consentito. Usa PNG, JPG, JPEG, GIF o WEBP'
        }), HTTPStatus.BAD_REQUEST

    try:
        # Generate unique filename
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"

        # Use configured UPLOAD_FOLDER
        base_upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        upload_folder = os.path.join(base_upload_folder, 'avatars')
        os.makedirs(upload_folder, exist_ok=True)

        # Delete old avatar if exists
        if user.avatar_path and user.avatar_path.startswith('/uploads/'):
            old_filename = user.avatar_path.replace('/uploads/avatars/', '')
            old_path = os.path.join(upload_folder, old_filename)
            if os.path.exists(old_path):
                os.remove(old_path)

        # Save new file
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)

        # Update user avatar_path - matches /uploads/<path:filename> route
        user.avatar_path = f"/uploads/avatars/{filename}"
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Avatar caricato con successo',
            'avatar_path': user.avatar_path
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error uploading avatar: {e}")
        return jsonify({
            'success': False,
            'message': f'Errore durante il caricamento: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@team_api_bp.route("/departments", methods=["GET"])
@login_required
def get_departments():
    """Get list of departments."""
    departments = Department.query.order_by(Department.name).all()

    return jsonify({
        'success': True,
        'departments': [
            {
                'id': dept.id,
                'name': dept.name,
                'head_id': dept.head_id,
                'member_count': len(dept.members) if hasattr(dept, 'members') else 0
            }
            for dept in departments
        ]
    })


@team_api_bp.route("/stats", methods=["GET"])
@login_required
def get_team_stats():
    """Get team statistics."""
    # Total counts
    total_members = User.query.count()  # All members
    total_active = User.query.filter_by(is_active=True).count()  # Active only
    total_admins = User.query.filter_by(is_admin=True, is_active=True).count()
    total_trial = User.query.filter_by(is_trial=True, is_active=True).count()

    # Count by role
    total_team_leaders = User.query.filter(
        User.is_active == True,
        User.role == UserRoleEnum.team_leader
    ).count()
    total_professionisti = User.query.filter(
        User.is_active == True,
        User.role == UserRoleEnum.professionista
    ).count()
    total_external = User.query.filter(
        User.is_active == True,
        User.is_external == True
    ).count()

    return jsonify({
        'success': True,
        'total_members': total_members,
        'total_active': total_active,
        'total_admins': total_admins,
        'total_trial': total_trial,
        'total_team_leaders': total_team_leaders,
        'total_professionisti': total_professionisti,
        'total_external': total_external
    })


# =============================================================================
# Team Entity Management - Gestione Team per Specializzazione
# =============================================================================

# Mapping team_type -> specialties compatibili per Team Leader
TEAM_TYPE_LEADER_SPECIALTIES = {
    'nutrizione': [UserSpecialtyEnum.nutrizione],
    'coach': [UserSpecialtyEnum.coach],
    'psicologia': [UserSpecialtyEnum.psicologia],
}

# Mapping team_type -> specialties compatibili per Professionisti
TEAM_TYPE_PROFESSIONAL_SPECIALTIES = {
    'nutrizione': [UserSpecialtyEnum.nutrizione, UserSpecialtyEnum.nutrizionista],
    'coach': [UserSpecialtyEnum.coach],
    'psicologia': [UserSpecialtyEnum.psicologia, UserSpecialtyEnum.psicologo],
}


def _serialize_team(team, include_members=False):
    """Serialize team object to JSON-safe dict."""
    data = {
        'id': team.id,
        'name': team.name,
        'description': team.description,
        'team_type': team.team_type.value if team.team_type else None,
        'is_active': team.is_active,
        'head_id': team.head_id,
        'head': _serialize_user(team.head) if team.head else None,
        'member_count': team.member_count,
        'created_at': team.created_at.isoformat() if team.created_at else None,
        'updated_at': team.updated_at.isoformat() if team.updated_at else None,
    }

    if include_members:
        data['members'] = [_serialize_user(m) for m in (team.members or [])]

    return data


@team_api_bp.route("/teams", methods=["GET"])
@login_required
def get_teams():
    """
    Get list of teams.

    Query params:
        - team_type: Filter by team type (nutrizione, coach, psicologia)
        - active: Filter by active status ('1' or '0')
        - q: Search query (searches team name)
    """
    team_type_filter = request.args.get('team_type', '').strip()
    active_filter = request.args.get('active', '').strip()
    search_query = request.args.get('q', '').strip()

    # Base query
    query = Team.query

    # Filter by team_type
    if team_type_filter and team_type_filter in [e.value for e in TeamTypeEnum]:
        query = query.filter(Team.team_type == TeamTypeEnum(team_type_filter))

    # Filter by active
    if active_filter == '1':
        query = query.filter(Team.is_active == True)
    elif active_filter == '0':
        query = query.filter(Team.is_active == False)

    # Search filter
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(Team.name.ilike(search_term))

    # Order by team_type, then name
    query = query.order_by(Team.team_type, Team.name)

    teams = query.all()

    return jsonify({
        'success': True,
        'teams': [_serialize_team(t) for t in teams],
        'total': len(teams)
    })


@team_api_bp.route("/teams/<int:team_id>", methods=["GET"])
@login_required
def get_team(team_id):
    """Get single team details with members."""
    team = Team.query.get_or_404(team_id)

    return jsonify({
        'success': True,
        **_serialize_team(team, include_members=True)
    })


@team_api_bp.route("/teams", methods=["POST"])
@login_required
def create_team():
    """Create new team."""
    # Check admin permission
    perm_error = _require_admin()
    if perm_error:
        return perm_error

    data = request.get_json()
    if not data:
        return jsonify({
            'success': False,
            'message': 'Dati non validi'
        }), HTTPStatus.BAD_REQUEST

    # Validate required fields
    if not data.get('name'):
        return jsonify({
            'success': False,
            'message': 'Nome team obbligatorio'
        }), HTTPStatus.BAD_REQUEST

    if not data.get('team_type'):
        return jsonify({
            'success': False,
            'message': 'Tipo team obbligatorio'
        }), HTTPStatus.BAD_REQUEST

    team_type_str = data['team_type']
    if team_type_str not in [e.value for e in TeamTypeEnum]:
        return jsonify({
            'success': False,
            'message': 'Tipo team non valido'
        }), HTTPStatus.BAD_REQUEST

    # Check unique name per type
    existing = Team.query.filter_by(
        team_type=TeamTypeEnum(team_type_str),
        name=data['name']
    ).first()
    if existing:
        return jsonify({
            'success': False,
            'message': 'Esiste già un team con questo nome per questo tipo'
        }), HTTPStatus.BAD_REQUEST

    try:
        team = Team(
            name=data['name'],
            description=data.get('description'),
            team_type=TeamTypeEnum(team_type_str),
            head_id=data.get('head_id'),
            is_active=True
        )

        # Add initial members if provided
        member_ids = data.get('member_ids', [])
        if member_ids:
            members = User.query.filter(User.id.in_(member_ids)).all()
            team.members = members

        db.session.add(team)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Team creato con successo',
            **_serialize_team(team, include_members=True)
        }), HTTPStatus.CREATED

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating team: {e}")
        return jsonify({
            'success': False,
            'message': f'Errore durante la creazione: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@team_api_bp.route("/teams/<int:team_id>", methods=["PUT"])
@login_required
def update_team(team_id):
    """Update team."""
    # Check admin permission
    perm_error = _require_admin()
    if perm_error:
        return perm_error

    team = Team.query.get_or_404(team_id)
    data = request.get_json()

    if not data:
        return jsonify({
            'success': False,
            'message': 'Dati non validi'
        }), HTTPStatus.BAD_REQUEST

    try:
        # Update name
        if 'name' in data:
            # Check uniqueness if changing name
            if data['name'] != team.name:
                existing = Team.query.filter_by(
                    team_type=team.team_type,
                    name=data['name']
                ).first()
                if existing:
                    return jsonify({
                        'success': False,
                        'message': 'Esiste già un team con questo nome per questo tipo'
                    }), HTTPStatus.BAD_REQUEST
            team.name = data['name']

        # Update description
        if 'description' in data:
            team.description = data['description']

        # Update head_id
        if 'head_id' in data:
            team.head_id = data['head_id'] if data['head_id'] else None

        # Update is_active
        if 'is_active' in data:
            team.is_active = data['is_active']

        # Update members if provided
        if 'member_ids' in data:
            members = User.query.filter(User.id.in_(data['member_ids'])).all()
            team.members = members

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Team aggiornato con successo',
            **_serialize_team(team, include_members=True)
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating team: {e}")
        return jsonify({
            'success': False,
            'message': f'Errore durante l\'aggiornamento: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@team_api_bp.route("/teams/<int:team_id>", methods=["DELETE"])
@login_required
def delete_team(team_id):
    """Delete team (soft delete by deactivating)."""
    # Check admin permission
    perm_error = _require_admin()
    if perm_error:
        return perm_error

    team = Team.query.get_or_404(team_id)

    try:
        # Soft delete - just deactivate
        team.is_active = False
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Team disattivato con successo'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting team: {e}")
        return jsonify({
            'success': False,
            'message': f'Errore durante l\'eliminazione: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@team_api_bp.route("/teams/<int:team_id>/members", methods=["POST"])
@login_required
def add_team_member(team_id):
    """Add member to team."""
    # Check admin permission
    perm_error = _require_admin()
    if perm_error:
        return perm_error

    team = Team.query.get_or_404(team_id)
    data = request.get_json()

    if not data or not data.get('user_id'):
        return jsonify({
            'success': False,
            'message': 'user_id obbligatorio'
        }), HTTPStatus.BAD_REQUEST

    user = User.query.get_or_404(data['user_id'])

    # Check if already member
    if user in team.members:
        return jsonify({
            'success': False,
            'message': 'L\'utente è già membro del team'
        }), HTTPStatus.BAD_REQUEST

    try:
        team.members.append(user)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Membro aggiunto con successo',
            **_serialize_team(team, include_members=True)
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding team member: {e}")
        return jsonify({
            'success': False,
            'message': f'Errore: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@team_api_bp.route("/teams/<int:team_id>/members/<int:user_id>", methods=["DELETE"])
@login_required
def remove_team_member(team_id, user_id):
    """Remove member from team."""
    # Check admin permission
    perm_error = _require_admin()
    if perm_error:
        return perm_error

    team = Team.query.get_or_404(team_id)
    user = User.query.get_or_404(user_id)

    # Check if actually member
    if user not in team.members:
        return jsonify({
            'success': False,
            'message': 'L\'utente non è membro del team'
        }), HTTPStatus.BAD_REQUEST

    try:
        team.members.remove(user)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Membro rimosso con successo',
            **_serialize_team(team, include_members=True)
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error removing team member: {e}")
        return jsonify({
            'success': False,
            'message': f'Errore: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@team_api_bp.route("/available-leaders/<team_type>", methods=["GET"])
@login_required
def get_available_leaders(team_type):
    """
    Get available team leaders for a specific team type.

    Team leaders must have:
    - role = team_leader
    - specialty compatible with team_type
    """
    if team_type not in [e.value for e in TeamTypeEnum]:
        return jsonify({
            'success': False,
            'message': 'Tipo team non valido'
        }), HTTPStatus.BAD_REQUEST

    # Get compatible specialties
    compatible_specialties = TEAM_TYPE_LEADER_SPECIALTIES.get(team_type, [])

    # Query users with team_leader role and compatible specialty
    query = User.query.filter(
        User.is_active == True,
        User.role == UserRoleEnum.team_leader,
        User.specialty.in_(compatible_specialties)
    ).order_by(User.first_name, User.last_name)

    leaders = query.all()

    return jsonify({
        'success': True,
        'leaders': [_serialize_user(u) for u in leaders],
        'total': len(leaders)
    })


@team_api_bp.route("/available-professionals/<team_type>", methods=["GET"])
@login_required
def get_available_professionals(team_type):
    """
    Get available professionals for a specific team type.

    Professionals must have:
    - role = professionista
    - specialty compatible with team_type
    """
    if team_type not in [e.value for e in TeamTypeEnum]:
        return jsonify({
            'success': False,
            'message': 'Tipo team non valido'
        }), HTTPStatus.BAD_REQUEST

    # Get compatible specialties
    compatible_specialties = TEAM_TYPE_PROFESSIONAL_SPECIALTIES.get(team_type, [])

    # Query users with professionista role and compatible specialty
    query = User.query.filter(
        User.is_active == True,
        User.role == UserRoleEnum.professionista,
        User.specialty.in_(compatible_specialties)
    ).order_by(User.first_name, User.last_name)

    professionals = query.all()

    return jsonify({
        'success': True,
        'professionals': [_serialize_user(u) for u in professionals],
        'total': len(professionals)
    })


# =============================================================================
# Professional's Clients Endpoint
# =============================================================================

@team_api_bp.route("/members/<int:user_id>/clients", methods=["GET"])
@login_required
def get_member_clients(user_id):
    """
    Get paginated list of clients associated with a professional.

    Query params:
        - page: Page number (default 1)
        - per_page: Items per page (default 5, max 50)
        - q: Search query (searches client name)
        - stato: Filter by stato_cliente

    Returns clients where the professional is assigned via:
    - Single FK (nutrizionista_id, coach_id, psicologa_id)
    - Many-to-many relationships (nutrizionisti_multipli, coaches_multipli, psicologi_multipli)
    """
    from corposostenibile.models import Cliente, cliente_nutrizionisti, cliente_coaches, cliente_psicologi
    from sqlalchemy import select, exists

    user = User.query.get_or_404(user_id)

    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 5, type=int), 50)
    search_query = request.args.get('q', '').strip()
    stato_filter = request.args.get('stato', '').strip()

    # Build exists clauses for many-to-many relationships
    nutri_exists = exists(
        select(cliente_nutrizionisti.c.cliente_id).where(
            cliente_nutrizionisti.c.cliente_id == Cliente.cliente_id,
            cliente_nutrizionisti.c.user_id == user_id
        )
    )

    coach_exists = exists(
        select(cliente_coaches.c.cliente_id).where(
            cliente_coaches.c.cliente_id == Cliente.cliente_id,
            cliente_coaches.c.user_id == user_id
        )
    )

    psico_exists = exists(
        select(cliente_psicologi.c.cliente_id).where(
            cliente_psicologi.c.cliente_id == Cliente.cliente_id,
            cliente_psicologi.c.user_id == user_id
        )
    )

    # Base query: find clients where this user is assigned
    query = Cliente.query.filter(
        or_(
            # Single FK relationships
            Cliente.nutrizionista_id == user_id,
            Cliente.coach_id == user_id,
            Cliente.psicologa_id == user_id,
            Cliente.consulente_alimentare_id == user_id,
            Cliente.health_manager_id == user_id,
            # Many-to-many relationships
            nutri_exists,
            coach_exists,
            psico_exists,
        )
    )

    # Search filter
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            or_(
                Cliente.nome.ilike(search_term),
                Cliente.cognome.ilike(search_term),
                func.concat(Cliente.nome, ' ', Cliente.cognome).ilike(search_term)
            )
        )

    # Stato filter
    if stato_filter:
        query = query.filter(Cliente.stato_cliente == stato_filter)

    # Order by cognome, nome
    query = query.order_by(Cliente.cognome, Cliente.nome)

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Serialize clients - simplified to avoid lazy loading issues
    def serialize_client(c):
        # Check roles
        is_nutri = c.nutrizionista_id == user_id
        is_coach = c.coach_id == user_id
        is_psico = c.psicologa_id == user_id

        # Also check many-to-many (already loaded via selectin)
        if not is_nutri and c.nutrizionisti_multipli:
            is_nutri = any(u.id == user_id for u in c.nutrizionisti_multipli)
        if not is_coach and c.coaches_multipli:
            is_coach = any(u.id == user_id for u in c.coaches_multipli)
        if not is_psico and c.psicologi_multipli:
            is_psico = any(u.id == user_id for u in c.psicologi_multipli)

        return {
            'id': c.cliente_id,
            'nome': c.nome,
            'cognome': c.cognome,
            'full_name': f"{c.nome} {c.cognome}" if c.nome and c.cognome else (c.nome or c.cognome or '-'),
            'email': c.email,
            'telefono': c.telefono,
            'stato_cliente': c.stato_cliente.value if c.stato_cliente else None,
            'tipologia_cliente': c.tipologia_cliente.value if c.tipologia_cliente else None,
            'data_inizio': c.data_inizio.isoformat() if c.data_inizio else None,
            'foto_profilo': c.foto_profilo,
            'is_nutrizionista': is_nutri,
            'is_coach': is_coach,
            'is_psicologo': is_psico,
        }

    clients = [serialize_client(c) for c in pagination.items]

    return jsonify({
        'success': True,
        'clients': clients,
        'total': pagination.total,
        'page': pagination.page,
        'per_page': pagination.per_page,
        'total_pages': pagination.pages,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev,
    })
