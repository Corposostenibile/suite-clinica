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
from sqlalchemy.orm import joinedload, selectinload
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from corposostenibile.extensions import db, csrf
from corposostenibile.models import User, Department, Team, UserRoleEnum, UserSpecialtyEnum, TeamTypeEnum, team_members, Origine


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


def _serialize_user(user, include_details=False, include_teams_led=True):
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
    }

    # Only load teams_led when explicitly requested (causes N+1 queries)
    if include_teams_led and hasattr(user, 'teams_led'):
        data['teams_led'] = [
            {'id': t.id, 'name': t.name}
            for t in (user.teams_led or [])
        ]
    else:
        data['teams_led'] = []

    if include_details:
        data.update({
            'last_login_at': user.last_login_at.isoformat() if user.last_login_at else None,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'is_trial': user.is_trial,
            'trial_stage': user.trial_stage,
            'assignment_ai_notes': user.assignment_ai_notes or {},
        })

    return data

def _serialize_origins(user):
    """Serialize user origins (for influencers)."""
    if hasattr(user, 'influencer_origins'):
        # Handle dynamic relationship
        origins = user.influencer_origins.all() if hasattr(user.influencer_origins, 'all') else user.influencer_origins
        return [{'id': o.id, 'name': o.name} for o in origins]
    return []


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
        - per_page: Items per page (default 25, max 10000)
        - q: Search query (searches name, email)
        - role: Filter by role (admin, team_leader, professionista, team_esterno)
        - specialty: Filter by specialty
        - active: Filter by active status ('1' or '0')
        - department_id: Filter by department
    """
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 25, type=int), 10000)
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
        **_serialize_user(user, include_details=True),
        'influencer_origins': _serialize_origins(user)
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

        # Handle Origin assignment for Influencers
        if role_enum == UserRoleEnum.influencer and 'origin_ids' in data:
            origin_ids = data['origin_ids']
            if isinstance(origin_ids, list):
                # Retrieve Origin objects
                origins = Origine.query.filter(Origine.id.in_(origin_ids)).all()
                for origin in origins:
                    user.influencer_origins.append(origin)

        db.session.add(user)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Membro creato con successo',
            'id': user.id,
            **_serialize_user(user),
            'influencer_origins': _serialize_origins(user)
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


        # Update Origin assignment for Influencers
        if 'origin_ids' in data:
            # Check if user is influencer (either currently or being updated to)
            current_role = user.role
            new_role_str = data.get('role')
            new_role = UserRoleEnum(new_role_str) if new_role_str in [e.value for e in UserRoleEnum] else current_role
            
            if new_role == UserRoleEnum.influencer:
                origin_ids = data['origin_ids']
                if isinstance(origin_ids, list):
                    # Clear current origins (safe for dynamic relationship)
                    current_origins = user.influencer_origins.all() if hasattr(user.influencer_origins, 'all') else list(user.influencer_origins)
                    for o in current_origins:
                        user.influencer_origins.remove(o)
                    
                    # Add new origins
                    new_origins = Origine.query.filter(Origine.id.in_(origin_ids)).all()
                    for o in new_origins:
                        user.influencer_origins.append(o)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Membro aggiornato con successo',
            **_serialize_user(user, include_details=True),
            'influencer_origins': _serialize_origins(user)
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


@team_api_bp.route("/admin-dashboard-stats", methods=["GET"])
@login_required
def get_admin_dashboard_stats():
    """
    Get comprehensive admin dashboard statistics for professionals.
    Returns KPIs, specialty distribution, quality scores, trial users, top performers.
    """
    from corposostenibile.models import QualityWeeklyScore, Cliente, StatoClienteEnum
    from corposostenibile.models import cliente_nutrizionisti, cliente_coaches, cliente_psicologi
    from datetime import datetime, timedelta
    from sqlalchemy import select, case, literal_column

    # Check admin permission
    perm_error = _require_admin()
    if perm_error:
        return perm_error

    try:
        today = datetime.now().date()

        # ─── KPI: Counts ───
        total_all = User.query.count()
        total_active = User.query.filter_by(is_active=True).count()
        total_inactive = total_all - total_active
        total_admins = User.query.filter_by(is_admin=True, is_active=True).count()
        total_trial = User.query.filter_by(is_trial=True, is_active=True).count()
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

        # ─── Specialty Distribution ───
        specialty_counts = db.session.query(
            User.specialty, func.count(User.id)
        ).filter(
            User.is_active == True,
            User.specialty.isnot(None)
        ).group_by(User.specialty).all()

        specialty_distribution = {}
        specialty_labels = {
            'nutrizione': 'Nutrizione (TL)',
            'nutrizionista': 'Nutrizionisti',
            'psicologia': 'Psicologia (TL)',
            'psicologo': 'Psicologi',
            'coach': 'Coach',
            'amministrazione': 'Amministrazione',
            'cco': 'CCO',
        }
        for spec, count in specialty_counts:
            key = spec.value if hasattr(spec, 'value') else str(spec)
            specialty_distribution[key] = {
                'count': count,
                'label': specialty_labels.get(key, key.capitalize())
            }

        # ─── Role Distribution ───
        role_counts = db.session.query(
            User.role, func.count(User.id)
        ).filter(
            User.is_active == True,
            User.role.isnot(None)
        ).group_by(User.role).all()

        role_distribution = {}
        role_labels = {
            'admin': 'Admin',
            'team_leader': 'Team Leader',
            'professionista': 'Professionista',
            'team_esterno': 'Team Esterno',
        }
        for role, count in role_counts:
            key = role.value if hasattr(role, 'value') else str(role)
            role_distribution[key] = {
                'count': count,
                'label': role_labels.get(key, key.capitalize())
            }

        # ─── Quality Scores (latest week) ───
        latest_week = db.session.query(
            func.max(QualityWeeklyScore.week_start_date)
        ).scalar()

        quality_summary = {
            'avgQuality': None,
            'avgMonth': None,
            'avgTrim': None,
            'bonusBands': {'100%': 0, '60%': 0, '30%': 0, '0%': 0},
            'trendUp': 0,
            'trendDown': 0,
            'trendStable': 0,
        }

        if latest_week:
            latest_scores = QualityWeeklyScore.query.filter_by(
                week_start_date=latest_week,
                calculation_status='completed'
            ).all()

            if latest_scores:
                finals = [s.quality_final for s in latest_scores if s.quality_final is not None]
                months = [s.quality_month for s in latest_scores if s.quality_month is not None]
                trims = [s.quality_trim for s in latest_scores if s.quality_trim is not None]

                quality_summary['avgQuality'] = round(sum(finals) / len(finals), 2) if finals else None
                quality_summary['avgMonth'] = round(sum(months) / len(months), 2) if months else None
                quality_summary['avgTrim'] = round(sum(trims) / len(trims), 2) if trims else None

                for s in latest_scores:
                    band = s.bonus_band or '0%'
                    if band in quality_summary['bonusBands']:
                        quality_summary['bonusBands'][band] += 1

                    trend = s.trend_indicator
                    if trend == 'up':
                        quality_summary['trendUp'] += 1
                    elif trend == 'down':
                        quality_summary['trendDown'] += 1
                    else:
                        quality_summary['trendStable'] += 1

        # ─── Top Performers (by quality_final, latest week) ───
        top_performers = []
        if latest_week:
            top_scores = QualityWeeklyScore.query.filter_by(
                week_start_date=latest_week,
                calculation_status='completed'
            ).filter(
                QualityWeeklyScore.quality_final.isnot(None)
            ).order_by(
                QualityWeeklyScore.quality_final.desc()
            ).limit(10).all()

            for s in top_scores:
                prof = s.professionista
                if prof:
                    top_performers.append({
                        'id': prof.id,
                        'name': prof.full_name,
                        'specialty': _get_user_specialty(prof),
                        'quality_final': round(s.quality_final, 2) if s.quality_final else None,
                        'quality_month': round(s.quality_month, 2) if s.quality_month else None,
                        'bonus_band': s.bonus_band,
                        'trend': s.trend_indicator,
                        'avatar_path': prof.avatar_path,
                    })

        # ─── Trial Users ───
        trial_users = User.query.filter_by(
            is_trial=True, is_active=True
        ).order_by(User.created_at.desc()).limit(10).all()

        trial_list = []
        for u in trial_users:
            trial_list.append({
                'id': u.id,
                'name': u.full_name,
                'specialty': _get_user_specialty(u),
                'trial_stage': u.trial_stage,
                'avatar_path': u.avatar_path,
                'created_at': u.created_at.isoformat() if u.created_at else None,
            })

        # ─── Quality Weekly Trend (last 8 weeks) ───
        quality_trend = []
        if latest_week:
            eight_weeks_ago = latest_week - timedelta(weeks=8)
            weekly_avgs = db.session.query(
                QualityWeeklyScore.week_start_date,
                func.avg(QualityWeeklyScore.quality_final),
                func.count(QualityWeeklyScore.id)
            ).filter(
                QualityWeeklyScore.week_start_date >= eight_weeks_ago,
                QualityWeeklyScore.calculation_status == 'completed',
                QualityWeeklyScore.quality_final.isnot(None)
            ).group_by(
                QualityWeeklyScore.week_start_date
            ).order_by(
                QualityWeeklyScore.week_start_date
            ).all()

            for week_date, avg_quality, count in weekly_avgs:
                quality_trend.append({
                    'week': week_date.isoformat(),
                    'avgQuality': round(float(avg_quality), 2),
                    'count': count
                })

        # ─── Teams Summary ───
        teams = Team.query.filter_by(is_active=True).all()
        teams_summary = []
        for team in teams:
            member_count = len(team.members) if team.members else 0
            teams_summary.append({
                'id': team.id,
                'name': team.name,
                'team_type': team.team_type.value if team.team_type else None,
                'head_name': team.head.full_name if team.head else None,
                'member_count': member_count,
            })

        # ─── Client Load per Specialty ───
        # Count active clients per specialty group
        nutri_clients = db.session.query(func.count(Cliente.cliente_id)).filter(
            Cliente.stato_cliente.in_([StatoClienteEnum.attivo, StatoClienteEnum.pausa]),
            or_(
                Cliente.nutrizionista_id.isnot(None),
                Cliente.cliente_id.in_(
                    select(cliente_nutrizionisti.c.cliente_id)
                )
            )
        ).scalar() or 0

        coach_clients = db.session.query(func.count(Cliente.cliente_id)).filter(
            Cliente.stato_cliente.in_([StatoClienteEnum.attivo, StatoClienteEnum.pausa]),
            or_(
                Cliente.coach_id.isnot(None),
                Cliente.cliente_id.in_(
                    select(cliente_coaches.c.cliente_id)
                )
            )
        ).scalar() or 0

        psico_clients = db.session.query(func.count(Cliente.cliente_id)).filter(
            Cliente.stato_cliente.in_([StatoClienteEnum.attivo, StatoClienteEnum.pausa]),
            or_(
                Cliente.psicologa_id.isnot(None),
                Cliente.cliente_id.in_(
                    select(cliente_psicologi.c.cliente_id)
                )
            )
        ).scalar() or 0

        # Professionals count per clinical specialty
        nutri_profs = User.query.filter(
            User.is_active == True,
            User.specialty.in_([UserSpecialtyEnum.nutrizione, UserSpecialtyEnum.nutrizionista])
        ).count()
        coach_profs = User.query.filter(
            User.is_active == True,
            User.specialty == UserSpecialtyEnum.coach
        ).count()
        psico_profs = User.query.filter(
            User.is_active == True,
            User.specialty.in_([UserSpecialtyEnum.psicologia, UserSpecialtyEnum.psicologo])
        ).count()

        client_load = {
            'nutrizione': {
                'clients': nutri_clients,
                'professionals': nutri_profs,
                'avgLoad': round(nutri_clients / nutri_profs, 1) if nutri_profs > 0 else 0
            },
            'coach': {
                'clients': coach_clients,
                'professionals': coach_profs,
                'avgLoad': round(coach_clients / coach_profs, 1) if coach_profs > 0 else 0
            },
            'psicologia': {
                'clients': psico_clients,
                'professionals': psico_profs,
                'avgLoad': round(psico_clients / psico_profs, 1) if psico_profs > 0 else 0
            },
        }

        return jsonify({
            'success': True,
            'kpi': {
                'totalAll': total_all,
                'totalActive': total_active,
                'totalInactive': total_inactive,
                'totalAdmins': total_admins,
                'totalTrial': total_trial,
                'totalTeamLeaders': total_team_leaders,
                'totalProfessionisti': total_professionisti,
                'totalExternal': total_external,
            },
            'specialtyDistribution': specialty_distribution,
            'roleDistribution': role_distribution,
            'qualitySummary': quality_summary,
            'topPerformers': top_performers,
            'trialUsers': trial_list,
            'qualityTrend': quality_trend,
            'teamsSummary': teams_summary,
            'clientLoad': client_load,
        })

    except Exception as e:
        current_app.logger.error(f"Error in admin-dashboard-stats: {e}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'Errore nel calcolo statistiche: {str(e)}'
        }), HTTPStatus.INTERNAL_SERVER_ERROR


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
        'head': _serialize_user(team.head, include_teams_led=False) if team.head else None,
        'created_at': team.created_at.isoformat() if team.created_at else None,
        'updated_at': team.updated_at.isoformat() if team.updated_at else None,
    }

    # Only load members when explicitly requested (expensive)
    if include_members:
        data['members'] = [_serialize_user(m, include_teams_led=False) for m in (team.members or [])]
        data['member_count'] = len(team.members) if team.members else 0

    return data


@team_api_bp.route("/teams", methods=["GET"])
@login_required
def get_teams():
    """
    Get list of teams with server-side pagination.

    Query params:
        - page: Page number (default 1)
        - per_page: Items per page (default 12, max 100)
        - team_type: Filter by team type (nutrizione, coach, psicologia)
        - active: Filter by active status ('1' or '0')
        - q: Search query (searches team name)
        - include_members: Include team members in response ('1' to include)
    """
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 12, type=int), 100)
    team_type_filter = request.args.get('team_type', '').strip()
    active_filter = request.args.get('active', '').strip()
    search_query = request.args.get('q', '').strip()
    include_members = request.args.get('include_members', '').strip() == '1'

    # Base query with eager loading for head only (fast)
    query = Team.query.options(
        joinedload(Team.head)  # Eager load team head only
    )

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

    # Server-side pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'success': True,
        'teams': [_serialize_team(t, include_members=include_members) for t in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'per_page': pagination.per_page,
        'total_pages': pagination.pages
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
    # Relationships already have lazy="selectin" in the model, so no need for explicit loading
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
        query = query.filter(Cliente.nome_cognome.ilike(search_term))

    # Stato filter
    if stato_filter:
        query = query.filter(Cliente.stato_cliente == stato_filter)

    # Order by nome_cognome
    query = query.order_by(Cliente.nome_cognome)

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Serialize clients - include all fields needed for table display
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

        # Serialize team member helper
        def serialize_team_member(u):
            if not u:
                return None
            return {
                'id': u.id,
                'first_name': u.first_name or '',
                'last_name': u.last_name or '',
                'full_name': f"{u.first_name or ''} {u.last_name or ''}".strip(),
                'avatar_path': u.avatar_path,
            }

        # Build result
        result = {
            'id': c.cliente_id,
            'cliente_id': c.cliente_id,
            'nome_cognome': c.nome_cognome or '-',
            'full_name': c.nome_cognome or '-',
            'email': c.mail,
            'telefono': c.numero_telefono,
            'stato_cliente': c.stato_cliente.value if c.stato_cliente else None,
            'tipologia_cliente': c.tipologia_cliente.value if c.tipologia_cliente else None,
            'data_inizio_abbonamento': c.data_inizio_abbonamento.isoformat() if c.data_inizio_abbonamento else None,
            'data_rinnovo': c.data_rinnovo.isoformat() if c.data_rinnovo else None,
            'programma_attuale': c.programma_attuale,
            'storico_programma': c.storico_programma,
            'is_nutrizionista': is_nutri,
            'is_coach': is_coach,
            'is_psicologo': is_psico,
            # Team members
            'health_manager_user': serialize_team_member(c.health_manager_user) if c.health_manager_user else None,
            'nutrizionisti_multipli': [serialize_team_member(u) for u in (c.nutrizionisti_multipli or [])],
            'coaches_multipli': [serialize_team_member(u) for u in (c.coaches_multipli or [])],
            'psicologi_multipli': [serialize_team_member(u) for u in (c.psicologi_multipli or [])],
            'consulenti_multipli': [serialize_team_member(u) for u in (c.consulenti_multipli or [])],
        }
        return result

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


# =============================================================================
# Professional's Client Checks Endpoint
# =============================================================================

@team_api_bp.route("/members/<int:user_id>/checks", methods=["GET"])
@login_required
def get_member_client_checks(user_id):
    """
    Get check responses for clients associated with a professional.

    Query params:
        - period: 'week', 'month', 'trimester', 'year', or 'custom' (default 'month')
        - start_date: Start date for custom period (YYYY-MM-DD)
        - end_date: End date for custom period (YYYY-MM-DD)
        - page: Page number (default 1)
        - per_page: Items per page (default 25, max 50)

    Returns check responses from clients where the professional is assigned.
    """
    from corposostenibile.models import (
        Cliente, WeeklyCheck, WeeklyCheckResponse, DCACheck, DCACheckResponse,
        cliente_nutrizionisti, cliente_coaches, cliente_psicologi,
        ClientCheckReadConfirmation
    )
    from sqlalchemy import select, exists
    from datetime import datetime, timedelta

    user = User.query.get_or_404(user_id)

    # Parse parameters
    period = request.args.get('period', 'month').strip()
    start_date_str = request.args.get('start_date', '').strip()
    end_date_str = request.args.get('end_date', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 25, type=int), 50)

    # Calculate date range
    today = datetime.now().date()
    if period == 'week':
        start_date = today - timedelta(days=7)
        end_date = today
    elif period == 'month':
        start_date = today - timedelta(days=30)
        end_date = today
    elif period == 'trimester':
        start_date = today - timedelta(days=90)
        end_date = today
    elif period == 'year':
        start_date = today - timedelta(days=365)
        end_date = today
    elif period == 'custom' and start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = today - timedelta(days=30)
            end_date = today
    else:
        start_date = today - timedelta(days=30)
        end_date = today

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

    # Get all client IDs for this professional
    client_ids_query = Cliente.query.filter(
        or_(
            Cliente.nutrizionista_id == user_id,
            Cliente.coach_id == user_id,
            Cliente.psicologa_id == user_id,
            Cliente.consulente_alimentare_id == user_id,
            Cliente.health_manager_id == user_id,
            nutri_exists,
            coach_exists,
            psico_exists,
        )
    ).with_entities(Cliente.cliente_id)

    client_ids = [c.cliente_id for c in client_ids_query.all()]

    if not client_ids:
        return jsonify({
            'success': True,
            'responses': [],
            'stats': {
                'avg_nutrizionista': None,
                'avg_psicologo': None,
                'avg_coach': None,
                'avg_progresso': None,
                'avg_quality': None,
            },
            'total': 0,
            'page': page,
            'per_page': per_page,
            'total_pages': 0,
        })

    # Get weekly check responses - join through WeeklyCheck to filter by cliente_id
    weekly_responses = WeeklyCheckResponse.query.join(
        WeeklyCheck, WeeklyCheckResponse.weekly_check_id == WeeklyCheck.id
    ).filter(
        WeeklyCheck.cliente_id.in_(client_ids),
        WeeklyCheckResponse.submit_date >= start_date,
        WeeklyCheckResponse.submit_date <= end_date
    ).all()

    # Get DCA check responses - join through DCACheck to filter by cliente_id
    dca_responses = DCACheckResponse.query.join(
        DCACheck, DCACheckResponse.dca_check_id == DCACheck.id
    ).filter(
        DCACheck.cliente_id.in_(client_ids),
        DCACheckResponse.submit_date >= start_date,
        DCACheckResponse.submit_date <= end_date
    ).all()

    # Helper to get read status for a response
    def get_read_statuses(response, response_type):
        """Get read status for professionals assigned to the client."""
        # Get cliente through assignment relationship
        cliente = response.assignment.cliente if response.assignment else None
        professionals = {
            'nutrizionisti': [],
            'psicologi': [],
            'coaches': [],
        }

        if not cliente:
            return professionals

        # Map response_type to the value stored in ClientCheckReadConfirmation
        db_response_type = 'weekly_check' if response_type == 'weekly' else 'dca_check'

        # Get nutrizionisti
        nutris = list(cliente.nutrizionisti_multipli or [])
        if cliente.nutrizionista_id:
            nutri_user = User.query.get(cliente.nutrizionista_id)
            if nutri_user and nutri_user not in nutris:
                nutris.append(nutri_user)

        for u in nutris:
            # Check read status using ClientCheckReadConfirmation
            read_status = ClientCheckReadConfirmation.query.filter_by(
                response_type=db_response_type,
                response_id=response.id,
                user_id=u.id
            ).first()

            professionals['nutrizionisti'].append({
                'id': u.id,
                'nome': u.full_name,
                'avatar_path': u.avatar_path,
                'has_read': read_status is not None,
            })

        # Get psicologi
        psicos = list(cliente.psicologi_multipli or [])
        if cliente.psicologa_id:
            psico_user = User.query.get(cliente.psicologa_id)
            if psico_user and psico_user not in psicos:
                psicos.append(psico_user)

        for u in psicos:
            read_status = ClientCheckReadConfirmation.query.filter_by(
                response_type=db_response_type,
                response_id=response.id,
                user_id=u.id
            ).first()

            professionals['psicologi'].append({
                'id': u.id,
                'nome': u.full_name,
                'avatar_path': u.avatar_path,
                'has_read': read_status is not None,
            })

        # Get coaches
        coaches = list(cliente.coaches_multipli or [])
        if cliente.coach_id:
            coach_user = User.query.get(cliente.coach_id)
            if coach_user and coach_user not in coaches:
                coaches.append(coach_user)

        for u in coaches:
            read_status = ClientCheckReadConfirmation.query.filter_by(
                response_type=db_response_type,
                response_id=response.id,
                user_id=u.id
            ).first()

            professionals['coaches'].append({
                'id': u.id,
                'nome': u.full_name,
                'avatar_path': u.avatar_path,
                'has_read': read_status is not None,
            })

        return professionals

    # Serialize responses
    all_responses = []

    for r in weekly_responses:
        # Get cliente through assignment
        cliente = r.assignment.cliente if r.assignment else None
        profs = get_read_statuses(r, 'weekly')
        all_responses.append({
            'id': r.id,
            'type': 'weekly',
            'cliente_id': cliente.cliente_id if cliente else None,
            'cliente_nome': cliente.nome_cognome if cliente else 'N/D',
            'submit_date': r.submit_date.strftime('%d/%m/%Y') if r.submit_date else None,
            'nutritionist_rating': r.nutritionist_rating,
            'psychologist_rating': r.psychologist_rating,
            'coach_rating': r.coach_rating,
            'progress_rating': r.progress_rating,
            'nutrizionisti': profs['nutrizionisti'],
            'psicologi': profs['psicologi'],
            'coaches': profs['coaches'],
        })

    for r in dca_responses:
        # Get cliente through assignment
        cliente = r.assignment.cliente if r.assignment else None
        profs = get_read_statuses(r, 'dca')
        all_responses.append({
            'id': r.id,
            'type': 'dca',
            'cliente_id': cliente.cliente_id if cliente else None,
            'cliente_nome': cliente.nome_cognome if cliente else 'N/D',
            'submit_date': r.submit_date.strftime('%d/%m/%Y') if r.submit_date else None,
            'nutritionist_rating': r.nutritionist_rating,
            'psychologist_rating': r.psychologist_rating,
            'coach_rating': r.coach_rating,
            'progress_rating': r.progress_rating,
            'nutrizionisti': profs['nutrizionisti'],
            'psicologi': profs['psicologi'],
            'coaches': profs['coaches'],
        })

    # Sort by submit_date descending
    all_responses.sort(key=lambda x: x['submit_date'] or '', reverse=True)

    # Calculate stats
    nutri_ratings = [r['nutritionist_rating'] for r in all_responses if r['nutritionist_rating'] is not None]
    psico_ratings = [r['psychologist_rating'] for r in all_responses if r['psychologist_rating'] is not None]
    coach_ratings = [r['coach_rating'] for r in all_responses if r['coach_rating'] is not None]
    progress_ratings = [r['progress_rating'] for r in all_responses if r['progress_rating'] is not None]

    all_ratings = nutri_ratings + psico_ratings + coach_ratings + progress_ratings

    stats = {
        'avg_nutrizionista': round(sum(nutri_ratings) / len(nutri_ratings), 1) if nutri_ratings else None,
        'avg_psicologo': round(sum(psico_ratings) / len(psico_ratings), 1) if psico_ratings else None,
        'avg_coach': round(sum(coach_ratings) / len(coach_ratings), 1) if coach_ratings else None,
        'avg_progresso': round(sum(progress_ratings) / len(progress_ratings), 1) if progress_ratings else None,
        'avg_quality': round(sum(all_ratings) / len(all_ratings), 1) if all_ratings else None,
    }

    # Paginate
    total = len(all_responses)
    total_pages = (total + per_page - 1) // per_page if total > 0 else 0
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_responses = all_responses[start_idx:end_idx]

    return jsonify({
        'success': True,
        'responses': paginated_responses,
        'stats': stats,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages,
    })
