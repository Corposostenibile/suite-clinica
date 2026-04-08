"""
Feedback services for processing TypeForm response data.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
from collections import defaultdict
from sqlalchemy import func, and_, desc, or_
from sqlalchemy.exc import ProgrammingError
from flask import current_app

from corposostenibile.extensions import db
from corposostenibile.models import TypeFormResponse, Cliente, User, Department, WeeklyCheckResponse, DCACheckResponse

# --------------------------------------------------------------------------- #
#  Config Typeform (override-able in instance/config.py)                      #
# --------------------------------------------------------------------------- #
TYPEFORM_CONFIG: Dict[str, Any] = {
    "form_id": "NMA7wAUZ",
    "field_mapping": {
        "first_name":   "xUZ7AHHvXcDc",
        "last_name":    "j00YnBJPzweV",
        "satisfaction": "T6qaQ7Kun42s",
    },
}
try:
    # se l'app espone una config custom la fondiamo
    TYPEFORM_CONFIG.update(current_app.config["TYPEFORM_CUSTOMER_SATISFACTION"])  # type: ignore[index]
except Exception:       # pragma: no cover
    pass


# --------------------------------------------------------------------------- #
#  Helper Functions for Professional Assignment                               #
# --------------------------------------------------------------------------- #

def _client_has_professional(cliente, department: str, professional_id: int) -> bool:
    """
    Check if a client has a specific professional assigned.
    Handles both many-to-many and FK relationships.
    """
    if not cliente:
        return False

    if department == 'nutrizionista':
        # Check many-to-many first
        if hasattr(cliente, 'nutrizionisti_multipli') and cliente.nutrizionisti_multipli:
            return any(n.id == professional_id for n in cliente.nutrizionisti_multipli)
        # Check FK fallback
        if hasattr(cliente, 'nutrizionista_user') and cliente.nutrizionista_user:
            return cliente.nutrizionista_user.id == professional_id

    elif department == 'psicologa':
        # Check many-to-many first
        if hasattr(cliente, 'psicologi_multipli') and cliente.psicologi_multipli:
            return any(p.id == professional_id for p in cliente.psicologi_multipli)
        # Check FK fallback
        if hasattr(cliente, 'psicologa_user') and cliente.psicologa_user:
            return cliente.psicologa_user.id == professional_id

    elif department == 'coach':
        # Check many-to-many first
        if hasattr(cliente, 'coaches_multipli') and cliente.coaches_multipli:
            return any(c.id == professional_id for c in cliente.coaches_multipli)
        # Check FK fallback
        if hasattr(cliente, 'coach_user') and cliente.coach_user:
            return cliente.coach_user.id == professional_id

    return False


def _get_client_professional_ids(cliente, department: str) -> set:
    """
    Get all professional IDs for a client in a specific department.
    Returns a set of user IDs.
    """
    ids = set()
    if not cliente:
        return ids

    if department == 'nutrizionista':
        if hasattr(cliente, 'nutrizionisti_multipli') and cliente.nutrizionisti_multipli:
            ids.update(n.id for n in cliente.nutrizionisti_multipli)
        if hasattr(cliente, 'nutrizionista_user') and cliente.nutrizionista_user:
            ids.add(cliente.nutrizionista_user.id)

    elif department == 'psicologa':
        if hasattr(cliente, 'psicologi_multipli') and cliente.psicologi_multipli:
            ids.update(p.id for p in cliente.psicologi_multipli)
        if hasattr(cliente, 'psicologa_user') and cliente.psicologa_user:
            ids.add(cliente.psicologa_user.id)

    elif department == 'coach':
        if hasattr(cliente, 'coaches_multipli') and cliente.coaches_multipli:
            ids.update(c.id for c in cliente.coaches_multipli)
        if hasattr(cliente, 'coach_user') and cliente.coach_user:
            ids.add(cliente.coach_user.id)

    return ids


# --------------------------------------------------------------------------- #
#  Data Retrieval and Filtering                                               #
# --------------------------------------------------------------------------- #

def get_all_check_responses(start_date, end_date):
    """
    Get all check responses (TypeForm, WeeklyCheck, DCACheck) in date range.
    Returns unified list of response objects with read confirmations loaded.
    """
    from sqlalchemy.orm import joinedload, selectinload, lazyload
    from corposostenibile.models import ClientCheckReadConfirmation
    from datetime import date

    today = date.today()
    all_responses = []

    # 1. TypeForm responses (old system - no read confirmations)
    typeform_responses = TypeFormResponse.query.options(
        joinedload(TypeFormResponse.cliente).selectinload(Cliente.nutrizionisti_multipli).options(lazyload("*")),
        joinedload(TypeFormResponse.cliente).selectinload(Cliente.psicologi_multipli).options(lazyload("*")),
        joinedload(TypeFormResponse.cliente).selectinload(Cliente.coaches_multipli).options(lazyload("*")),
        joinedload(TypeFormResponse.cliente).joinedload(Cliente.nutrizionista_user).options(lazyload("*")),
        joinedload(TypeFormResponse.cliente).joinedload(Cliente.psicologa_user).options(lazyload("*")),
        joinedload(TypeFormResponse.cliente).joinedload(Cliente.coach_user).options(lazyload("*"))
    ).filter(
        and_(
            TypeFormResponse.submit_date >= start_date,
            TypeFormResponse.submit_date <= end_date
        )
    ).all()
    all_responses.extend(typeform_responses)

    # 2. WeeklyCheck responses
    from corposostenibile.models import WeeklyCheck
    weekly_check_responses = db.session.query(WeeklyCheckResponse).join(
        WeeklyCheck, WeeklyCheckResponse.weekly_check_id == WeeklyCheck.id
    ).join(
        Cliente, WeeklyCheck.cliente_id == Cliente.cliente_id
    ).options(
        joinedload(WeeklyCheckResponse.assignment).joinedload(WeeklyCheck.cliente).selectinload(Cliente.nutrizionisti_multipli).options(lazyload("*")),
        joinedload(WeeklyCheckResponse.assignment).joinedload(WeeklyCheck.cliente).selectinload(Cliente.psicologi_multipli).options(lazyload("*")),
        joinedload(WeeklyCheckResponse.assignment).joinedload(WeeklyCheck.cliente).selectinload(Cliente.coaches_multipli).options(lazyload("*")),
        joinedload(WeeklyCheckResponse.assignment).joinedload(WeeklyCheck.cliente).joinedload(Cliente.nutrizionista_user).options(lazyload("*")),
        joinedload(WeeklyCheckResponse.assignment).joinedload(WeeklyCheck.cliente).joinedload(Cliente.psicologa_user).options(lazyload("*")),
        joinedload(WeeklyCheckResponse.assignment).joinedload(WeeklyCheck.cliente).joinedload(Cliente.coach_user).options(lazyload("*"))
    ).filter(
        and_(
            WeeklyCheckResponse.submit_date >= start_date,
            WeeklyCheckResponse.submit_date <= end_date
        )
    ).all()

    # Add cliente reference and professional user IDs
    for resp in weekly_check_responses:
        if resp.assignment:
            resp.cliente = resp.assignment.cliente
            # Add professional user_id fields for filtering
            if resp.cliente:
                resp.nutritionist_user_id = resp.cliente.nutrizionisti_multipli[0].id if resp.cliente.nutrizionisti_multipli else (resp.cliente.nutrizionista_user.id if resp.cliente.nutrizionista_user else None)
                resp.psychologist_user_id = resp.cliente.psicologi_multipli[0].id if resp.cliente.psicologi_multipli else (resp.cliente.psicologa_user.id if resp.cliente.psicologa_user else None)
                resp.coach_user_id = resp.cliente.coaches_multipli[0].id if resp.cliente.coaches_multipli else (resp.cliente.coach_user.id if resp.cliente.coach_user else None)
    all_responses.extend(weekly_check_responses)

    # 3. DCACheck responses
    from corposostenibile.models import DCACheck
    dca_check_responses = db.session.query(DCACheckResponse).join(
        DCACheck, DCACheckResponse.dca_check_id == DCACheck.id
    ).join(
        Cliente, DCACheck.cliente_id == Cliente.cliente_id
    ).options(
        joinedload(DCACheckResponse.assignment).joinedload(DCACheck.cliente).selectinload(Cliente.nutrizionisti_multipli).options(lazyload("*")),
        joinedload(DCACheckResponse.assignment).joinedload(DCACheck.cliente).selectinload(Cliente.psicologi_multipli).options(lazyload("*")),
        joinedload(DCACheckResponse.assignment).joinedload(DCACheck.cliente).selectinload(Cliente.coaches_multipli).options(lazyload("*")),
        joinedload(DCACheckResponse.assignment).joinedload(DCACheck.cliente).joinedload(Cliente.nutrizionista_user).options(lazyload("*")),
        joinedload(DCACheckResponse.assignment).joinedload(DCACheck.cliente).joinedload(Cliente.psicologa_user).options(lazyload("*")),
        joinedload(DCACheckResponse.assignment).joinedload(DCACheck.cliente).joinedload(Cliente.coach_user).options(lazyload("*"))
    ).filter(
        and_(
            DCACheckResponse.submit_date >= start_date,
            DCACheckResponse.submit_date <= end_date
        )
    ).all()

    # Add cliente reference and professional user IDs for easier access
    for resp in dca_check_responses:
        if resp.assignment:
            resp.cliente = resp.assignment.cliente
            # Add professional user_id fields for filtering
            if resp.cliente:
                resp.nutritionist_user_id = resp.cliente.nutrizionisti_multipli[0].id if resp.cliente.nutrizionisti_multipli else (resp.cliente.nutrizionista_user.id if resp.cliente.nutrizionista_user else None)
                resp.psychologist_user_id = resp.cliente.psicologi_multipli[0].id if resp.cliente.psicologi_multipli else (resp.cliente.psicologa_user.id if resp.cliente.psicologa_user else None)
                resp.coach_user_id = resp.cliente.coaches_multipli[0].id if resp.cliente.coaches_multipli else (resp.cliente.coach_user.id if resp.cliente.coach_user else None)
    all_responses.extend(dca_check_responses)

    # Load read confirmations for all Weekly and DCA checks
    weekly_ids = [r.id for r in weekly_check_responses]
    dca_ids = [r.id for r in dca_check_responses]

    # Load all read confirmations for these responses
    read_confirmations = {}
    if weekly_ids:
        weekly_confirmations = ClientCheckReadConfirmation.query.filter(
            ClientCheckReadConfirmation.response_type == 'weekly_check',
            ClientCheckReadConfirmation.response_id.in_(weekly_ids)
        ).options(joinedload(ClientCheckReadConfirmation.user)).all()
        for conf in weekly_confirmations:
            key = ('weekly_check', conf.response_id)
            if key not in read_confirmations:
                read_confirmations[key] = []
            read_confirmations[key].append(conf)

    if dca_ids:
        dca_confirmations = ClientCheckReadConfirmation.query.filter(
            ClientCheckReadConfirmation.response_type == 'dca_check',
            ClientCheckReadConfirmation.response_id.in_(dca_ids)
        ).options(joinedload(ClientCheckReadConfirmation.user)).all()
        for conf in dca_confirmations:
            key = ('dca_check', conf.response_id)
            if key not in read_confirmations:
                read_confirmations[key] = []
            read_confirmations[key].append(conf)

    # Attach read_confirmations to response objects
    for resp in all_responses:
        if resp.__class__.__name__ == 'WeeklyCheckResponse':
            key = ('weekly_check', resp.id)
            resp.read_confirmations = read_confirmations.get(key, [])
        elif resp.__class__.__name__ == 'DCACheckResponse':
            key = ('dca_check', resp.id)
            resp.read_confirmations = read_confirmations.get(key, [])
        else:
            resp.read_confirmations = []

    # Sort by submit_date (most recent first)
    all_responses.sort(key=lambda x: x.submit_date if x.submit_date else datetime.min, reverse=True)

    return all_responses

def manually_associate_response(response_id: int, cliente_id: int) -> Tuple[bool, str]:
    """
    Manually associate a TypeForm response with a client

    Args:
        response_id: ID of the TypeFormResponse
        cliente_id: ID of the Cliente

    Returns:
        Tuple of (success, message)
    """
    try:
        response = TypeFormResponse.query.get(response_id)
        if not response:
            return False, "Response not found"

        cliente = Cliente.query.filter_by(cliente_id=cliente_id).first()
        if not cliente:
            return False, "Client not found"

        response.cliente_id = cliente.cliente_id
        response.is_matched = False
        db.session.commit()

        return True, "Response successfully associated with client"
    except Exception as e:
        db.session.rollback()
        return False, f"Error associating response: {str(e)}"

def calculate_average_ratings(responses):
    """Calculate average ratings for all responses, following specialist assignment rules."""
    nutritionist_ratings = []
    psychologist_ratings = []
    coach_ratings = []
    progress_ratings = []
    quality_scores = []

    for response in responses:
        # Progress rating: include all responses (even unassociated ones)
        # Use getattr for DCACheckResponse compatibility (doesn't have progress_rating)
        progress = getattr(response, 'progress_rating', None)
        if progress is not None:
            progress_ratings.append(progress)

        # Coordinator rating: if present, use it instead of progress for Quality calculation
        coordinator = getattr(response, 'coordinator_rating', None)

        # Specialist ratings: only include if client has specialists assigned
        # Use helper function for consistent logic
        if response.cliente:
            # Nutritionist rating
            nutritionist_rating = getattr(response, 'nutritionist_rating', None)
            if nutritionist_rating is not None:
                if _get_client_professional_ids(response.cliente, 'nutrizionista'):
                    nutritionist_ratings.append(nutritionist_rating)
                    # Calculate Quality for nutritionist: (nutritionist + coordinator OR progress) / 2
                    rating_to_use = coordinator if coordinator is not None else progress
                    if rating_to_use is not None:
                        quality_scores.append((nutritionist_rating + rating_to_use) / 2)

            # Psychologist rating
            psychologist_rating = getattr(response, 'psychologist_rating', None)
            if psychologist_rating is not None:
                if _get_client_professional_ids(response.cliente, 'psicologa'):
                    psychologist_ratings.append(psychologist_rating)
                    # Calculate Quality for psychologist: (psychologist + coordinator OR progress) / 2
                    rating_to_use = coordinator if coordinator is not None else progress
                    if rating_to_use is not None:
                        quality_scores.append((psychologist_rating + rating_to_use) / 2)

            # Coach rating
            coach_rating = getattr(response, 'coach_rating', None)
            if coach_rating is not None:
                if _get_client_professional_ids(response.cliente, 'coach'):
                    coach_ratings.append(coach_rating)
                    # Calculate Quality for coach: (coach + coordinator OR progress) / 2
                    rating_to_use = coordinator if coordinator is not None else progress
                    if rating_to_use is not None:
                        quality_scores.append((coach_rating + rating_to_use) / 2)

    return {
        'nutritionist': round(sum(nutritionist_ratings) / len(nutritionist_ratings), 1) if nutritionist_ratings else 0,
        'psychologist': round(sum(psychologist_ratings) / len(psychologist_ratings), 1) if psychologist_ratings else 0,
        'coach': round(sum(coach_ratings) / len(coach_ratings), 1) if coach_ratings else 0,
        'progress': round(sum(progress_ratings) / len(progress_ratings), 1) if progress_ratings else 0,
        'quality': round(sum(quality_scores) / len(quality_scores), 1) if quality_scores else 0
    }

def get_filtered_responses(period: str, offset: int, page: int = 1, per_page: int = 20, start_date_str: str = None, end_date_str: str = None):
    """Get filtered and paginated responses (includes TypeForm, WeeklyCheck, DCACheck)."""
    from .forms import get_date_range_for_period, format_period_display

    start_date, end_date = get_date_range_for_period(period, offset, start_date_str=start_date_str, end_date_str=end_date_str)

    # Get ALL responses (TypeForm + WeeklyCheck + DCACheck)
    all_responses = get_all_check_responses(start_date, end_date)

    # Manual pagination
    total = len(all_responses)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_responses = all_responses[start:end]

    # Create a simple pagination object
    class SimplePagination:
        def __init__(self, items, page, per_page, total):
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = total
            self.pages = (total + per_page - 1) // per_page if per_page > 0 else 0
            self.has_prev = page > 1
            self.has_next = page < self.pages
            self.prev_num = page - 1 if self.has_prev else None
            self.next_num = page + 1 if self.has_next else None

        def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
            """Generate page numbers for pagination display."""
            last = 0
            for num in range(1, self.pages + 1):
                if num <= left_edge or \
                   (num > self.page - left_current - 1 and num < self.page + right_current) or \
                   num > self.pages - right_edge:
                    if last + 1 != num:
                        yield None
                    yield num
                    last = num

    pagination = SimplePagination(paginated_responses, page, per_page, total)
    period_display = format_period_display(start_date, end_date, period)

    return (
        paginated_responses,
        pagination,
        total,
        period_display,
        start_date,
        end_date
    )

def get_all_responses_for_period(period: str, offset: int, start_date_str: str = None, end_date_str: str = None):
    """Get all responses for a period (without pagination) for calculations."""
    from .forms import get_date_range_for_period

    start_date, end_date = get_date_range_for_period(period, offset, start_date_str=start_date_str, end_date_str=end_date_str)

    # Get ALL responses (TypeForm + WeeklyCheck + DCACheck)
    return get_all_check_responses(start_date, end_date)

def calculate_department_average(responses, department: str):
    """Calculate average rating for a specific department - ONLY for clients with professional assigned."""
    rating_field_map = {
        'nutrizionista': 'nutritionist_rating',
        'psicologa': 'psychologist_rating',
        'coach': 'coach_rating'
    }

    rating_field = rating_field_map[department]

    ratings = []
    for r in responses:
        # Only count if rating exists AND client has professional assigned
        # Use helper function for consistent logic
        if getattr(r, rating_field) is not None and r.cliente:
            if _get_client_professional_ids(r.cliente, department):
                ratings.append(getattr(r, rating_field))

    return round(sum(ratings) / len(ratings), 1) if ratings else 0


def calculate_quality_average(responses, department: str):
    """Calculate average Quality score: (Professional Rating + Progress Rating) / 2 - ONLY for clients with professional assigned."""
    rating_field_map = {
        'nutrizionista': 'nutritionist_rating',
        'psicologa': 'psychologist_rating',
        'coach': 'coach_rating'
    }

    rating_field = rating_field_map[department]

    quality_scores = []
    for r in responses:
        # Only count if BOTH ratings exist AND client has professional assigned
        professional_rating = getattr(r, rating_field)
        progress_rating = getattr(r, 'progress_rating')

        if professional_rating is not None and progress_rating is not None and r.cliente:
            if _get_client_professional_ids(r.cliente, department):
                # Calculate Quality: (Professional + Progress) / 2
                quality = (professional_rating + progress_rating) / 2
                quality_scores.append(quality)

    return round(sum(quality_scores) / len(quality_scores), 1) if quality_scores else 0


def get_department_responses(department: str, period: str, offset: int, page: int = 1, per_page: int = 20, professional_id: int = None, user_filter=None, start_date_str: str = None, end_date_str: str = None):
    """
    Get responses for a specific department (nutrizionista, psicologa, coach).

    Args:
        department: 'nutrizionista', 'psicologa', or 'coach'
        period: time period
        offset: period offset
        page: page number
        per_page: items per page
        professional_id: filter by specific professional (optional)
        user_filter: user access filter
        start_date_str: start date string for custom period (optional)
        end_date_str: end date string for custom period (optional)
    """
    from .forms import get_date_range_for_period, format_period_display
    from corposostenibile.models import User

    start_date, end_date = get_date_range_for_period(period, offset, start_date_str=start_date_str, end_date_str=end_date_str)

    # Map department to rating field
    rating_field_map = {
        'nutrizionista': 'nutritionist_rating',
        'psicologa': 'psychologist_rating',
        'coach': 'coach_rating'
    }

    rating_field = rating_field_map[department]

    # Get ALL responses (TypeForm + WeeklyCheck + DCACheck)
    all_responses_raw = get_all_check_responses(start_date, end_date)

    # Filter responses: only those with rating for this department
    filtered_responses = []
    professional_ids = set()

    for resp in all_responses_raw:
        # Check if rating exists
        rating = getattr(resp, rating_field, None)
        if rating is None:
            continue

        # Check if client exists
        if not resp.cliente:
            continue

        # Get all professional IDs for this client in this department
        client_prof_ids = _get_client_professional_ids(resp.cliente, department)

        # Apply professional filter
        if professional_id:
            # Include response only if client has this specific professional
            if not _client_has_professional(resp.cliente, department, professional_id):
                continue

        # Apply user filter (for members who see only their own)
        if user_filter and user_filter['type'] == 'personal':
            if user_filter['user_id'] not in client_prof_ids:
                continue

        # Apply team filter (for team leaders who see their team's feedback)
        if user_filter and user_filter['type'] == 'team':
            team_member_ids = user_filter.get('team_member_ids', [])
            # Check if any of the client's professionals are in the team
            if not any(prof_id in team_member_ids for prof_id in client_prof_ids):
                continue

        # Only include if client has at least one professional assigned
        if not client_prof_ids:
            continue

        filtered_responses.append(resp)
        professional_ids.update(client_prof_ids)

    # Manual pagination
    total = len(filtered_responses)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_responses = filtered_responses[start_idx:end_idx]

    # Create pagination object
    class SimplePagination:
        def __init__(self, items, page, per_page, total):
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = total
            self.pages = (total + per_page - 1) // per_page if per_page > 0 else 0
            self.has_prev = page > 1
            self.has_next = page < self.pages
            self.prev_num = page - 1 if self.has_prev else None
            self.next_num = page + 1 if self.has_next else None

        def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
            """Generate page numbers for pagination display."""
            last = 0
            for num in range(1, self.pages + 1):
                if num <= left_edge or \
                   (num > self.page - left_current - 1 and num < self.page + right_current) or \
                   num > self.pages - right_edge:
                    if last + 1 != num:
                        yield None
                    yield num
                    last = num

    pagination = SimplePagination(paginated_responses, page, per_page, total)

    # Get list of professionals for dropdown
    professionals_query = User.query.filter(
        User.id.in_(list(professional_ids))
    ).order_by(User.first_name, User.last_name).all() if professional_ids else []

    period_display = format_period_display(start_date, end_date, period)

    return (
        paginated_responses,
        pagination,
        filtered_responses,  # all_responses for KPI calculation
        professionals_query,
        period_display,
        start_date,
        end_date
    )


def get_health_manager_responses(period: str, offset: int, page: int = 1, per_page: int = 20, health_manager_id: int = None, user_filter=None, start_date_str: str = None, end_date_str: str = None):
    """
    Get responses filtered by Health Manager assignment.

    Args:
        period: time period
        offset: period offset
        page: page number
        per_page: items per page
        health_manager_id: filter by specific health manager (optional)
        user_filter: user access filter
        start_date_str: start date string for custom period (optional)
        end_date_str: end date string for custom period (optional)
    """
    from .forms import get_date_range_for_period, format_period_display
    from corposostenibile.models import User

    start_date, end_date = get_date_range_for_period(period, offset, start_date_str=start_date_str, end_date_str=end_date_str)

    # Get ALL responses (TypeForm + WeeklyCheck + DCACheck)
    all_responses_raw = get_all_check_responses(start_date, end_date)

    # Filter responses: only those with health manager assigned
    filtered_responses = []
    health_manager_ids = set()

    for resp in all_responses_raw:
        # Check if client exists
        if not resp.cliente:
            continue

        # Check if client has health manager
        if not resp.cliente.health_manager_id:
            continue

        # Apply health manager filter
        if health_manager_id:
            # Include response only if client has this specific health manager
            if resp.cliente.health_manager_id != health_manager_id:
                continue

        # Apply user filter (for members who see only their own)
        if user_filter and user_filter['type'] == 'personal':
            if resp.cliente.health_manager_id != user_filter['user_id']:
                continue

        filtered_responses.append(resp)
        health_manager_ids.add(resp.cliente.health_manager_id)

    # Manual pagination
    total = len(filtered_responses)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_responses = filtered_responses[start_idx:end_idx]

    # Create pagination object
    class SimplePagination:
        def __init__(self, items, page, per_page, total):
            self.items = items
            self.page = page
            self.per_page = per_page
            self.total = total
            self.pages = (total + per_page - 1) // per_page if per_page > 0 else 0
            self.has_prev = page > 1
            self.has_next = page < self.pages
            self.prev_num = page - 1 if self.has_prev else None
            self.next_num = page + 1 if self.has_next else None

        def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
            """Generate page numbers for pagination display."""
            last = 0
            for num in range(1, self.pages + 1):
                if num <= left_edge or \
                   (num > self.page - left_current - 1 and num < self.page + right_current) or \
                   num > self.pages - right_edge:
                    if last + 1 != num:
                        yield None
                    yield num
                    last = num

    pagination = SimplePagination(paginated_responses, page, per_page, total)

    # Get list of health managers for dropdown
    health_managers_query = User.query.filter(
        User.id.in_(list(health_manager_ids))
    ).order_by(User.first_name, User.last_name).all() if health_manager_ids else []

    period_display = format_period_display(start_date, end_date, period)

    return (
        paginated_responses,
        pagination,
        filtered_responses,  # all_responses for KPI calculation
        health_managers_query,
        period_display,
        start_date,
        end_date
    )


def get_professional_ratings(professional_type, period, offset, user_filter=None):
    """Get individual professional ratings and responses (includes TypeForm, WeeklyCheck, DCACheck)."""
    from .forms import get_date_range_for_period

    start_date, end_date = get_date_range_for_period(period, offset)

    # Get ALL responses (TypeForm + WeeklyCheck + DCACheck)
    all_responses = get_all_check_responses(start_date, end_date)

    # Apply user filter if provided
    if user_filter:
        if user_filter['type'] == 'personal':
            # Filter by specific user ID - member sees only their own feedback
            filtered_responses = []
            for resp in all_responses:
                if professional_type == 'coach' and getattr(resp, 'coach_user_id', None) == user_filter['user_id']:
                    filtered_responses.append(resp)
                elif professional_type == 'nutrizionista' and getattr(resp, 'nutritionist_user_id', None) == user_filter['user_id']:
                    filtered_responses.append(resp)
                elif professional_type == 'psicologa' and getattr(resp, 'psychologist_user_id', None) == user_filter['user_id']:
                    filtered_responses.append(resp)
            all_responses = filtered_responses
        elif user_filter['type'] == 'team':
            # Filter by team members - team leader sees their team's feedback
            team_member_ids = user_filter.get('team_member_ids', [])
            filtered_responses = []
            for resp in all_responses:
                if professional_type == 'nutrizionista' and getattr(resp, 'nutritionist_user_id', None) in team_member_ids:
                    filtered_responses.append(resp)
                elif professional_type == 'psicologa' and getattr(resp, 'psychologist_user_id', None) in team_member_ids:
                    filtered_responses.append(resp)
            all_responses = filtered_responses
        elif user_filter['type'] == 'none':
            # No access - return empty
            return []

    if professional_type == 'coach':
        return _generate_coach_data(all_responses, user_filter)
    elif professional_type == 'nutrizionista':
        return _generate_nutritionist_data(all_responses, user_filter)
    elif professional_type == 'psicologa':
        return _generate_psychologist_data(all_responses, user_filter)

    return []

def _format_professional_name(name):
    """Format professional name from snake_case to Title Case."""
    if not name:
        return name
    name_parts = name.replace('_', ' ').title().split()
    if len(name_parts) >= 2:
        return f"{name_parts[0]} {name_parts[1][0]}."
    return name.replace('_', ' ').title()

def _generate_coach_data(responses, user_filter=None):
    """Generate coach-specific data from responses."""
    
    # Se è un department head, ottieni la lista degli user del dipartimento
    department_user_ids = None
    if user_filter and user_filter['type'] == 'department':
        # Trova tutti gli user del dipartimento Coach/Sport
        dept_coach = Department.query.filter(
            db.or_(
                Department.name.ilike('%coach%'),
                Department.name.ilike('%sport%')
            )
        ).first()
        if dept_coach:
            department_user_ids = [u.id for u in dept_coach.members]
    
    coaches = {}

    for response in responses:
        # Use getattr for DCACheckResponse compatibility
        coach_rating = getattr(response, 'coach_rating', None)
        if coach_rating is not None:
            coach_name = None
            coach_key = None
            coach_user_id = None

            # Priorità 1: Use User association if available
            resp_coach_user_id = getattr(response, 'coach_user_id', None)
            resp_coach_user = getattr(response, 'coach_user', None)
            if resp_coach_user_id and resp_coach_user:
                coach_user = resp_coach_user
                coach_key = f"user_{coach_user.id}"
                coach_name = f"{coach_user.first_name} {coach_user.last_name}"
                coach_user_id = coach_user.id
            # Priorità 2: Se non c'è associazione diretta ma c'è un cliente, usa i suoi professionisti
            elif response.cliente and response.cliente.coaches_multipli:
                # Prendi il primo coach dalla relazione many-to-many
                coach_user = response.cliente.coaches_multipli[0]
                coach_key = f"user_{coach_user.id}"
                coach_name = f"{coach_user.first_name} {coach_user.last_name}"
                coach_user_id = coach_user.id
            # Priorità 3: Usa il campo testuale se disponibile
            elif response.cliente and response.cliente.coach:
                coach_name = _format_professional_name(response.cliente.coach)
                coach_key = f"text_{response.cliente.coach}"
            # Fallback: Non specificato
            else:
                coach_name = "Coach Non Specificato"
                coach_key = "unknown"

            # Se è un department head, filtra solo i coach del dipartimento
            if department_user_ids is not None and coach_user_id:
                if coach_user_id not in department_user_ids:
                    continue  # Salta questo feedback se il coach non è del dipartimento

            if coach_key and coach_name:
                if coach_key not in coaches:
                    coaches[coach_key] = {
                        'name': coach_name,
                        'display_name': coach_name,
                        'user_id': coach_user_id,
                        'responses': [],
                        'ratings': []
                    }

                coaches[coach_key]['ratings'].append(coach_rating)
                coaches[coach_key]['responses'].append({
                    'id': response.id,
                    'rating': coach_rating,
                    'feedback': getattr(response, 'coach_feedback', None),
                    'client_name': response.cliente.nome_cognome if response.cliente else f"{getattr(response, 'first_name', '')} {getattr(response, 'last_name', '')}".strip() or "Cliente Sconosciuto",
                    'submit_date': response.submit_date
                })
    
    # Calculate averages and format results
    result = []
    for coach_data in coaches.values():
        if coach_data['ratings']:
            coach_data['average_rating'] = round(sum(coach_data['ratings']) / len(coach_data['ratings']), 1)
            coach_data['total_responses'] = len(coach_data['responses'])
            # Ordina le risposte per data (più recenti prima)
            coach_data['responses'] = sorted(
                coach_data['responses'], 
                key=lambda x: x['submit_date'] if x['submit_date'] else datetime.min, 
                reverse=True
            )
            result.append(coach_data)
    
    return sorted(result, key=lambda x: x['average_rating'], reverse=True)

def _generate_nutritionist_data(responses, user_filter=None):
    """Generate nutritionist-specific data from responses."""

    # Ottieni la lista degli user in base al tipo di filtro
    allowed_user_ids = None
    if user_filter:
        if user_filter['type'] == 'department':
            # Department head: vede tutti gli user del dipartimento Nutrizione
            dept_nutri = Department.query.filter(
                Department.name.ilike('%nutrizion%')
            ).first()
            if dept_nutri:
                allowed_user_ids = [u.id for u in dept_nutri.members]
        elif user_filter['type'] == 'team':
            # Team leader: vede solo i membri del proprio team
            allowed_user_ids = user_filter.get('team_member_ids', [])

    nutritionists = {}

    for response in responses:
        # Use getattr for DCACheckResponse compatibility
        nutritionist_rating = getattr(response, 'nutritionist_rating', None)
        if nutritionist_rating is not None:
            nutritionist_name = None
            nutritionist_key = None
            nutritionist_user_id = None

            # Priorità 1: Use User association if available
            resp_nutritionist_user_id = getattr(response, 'nutritionist_user_id', None)
            resp_nutritionist_user = getattr(response, 'nutritionist_user', None)
            if resp_nutritionist_user_id and resp_nutritionist_user:
                nutritionist_user = resp_nutritionist_user
                nutritionist_key = f"user_{nutritionist_user.id}"
                nutritionist_name = f"{nutritionist_user.first_name} {nutritionist_user.last_name}"
                nutritionist_user_id = nutritionist_user.id
            # Priorità 2: Se non c'è associazione diretta ma c'è un cliente, usa i suoi professionisti
            elif response.cliente and response.cliente.nutrizionisti_multipli:
                # Prendi il primo nutrizionista dalla relazione many-to-many
                nutritionist_user = response.cliente.nutrizionisti_multipli[0]
                nutritionist_key = f"user_{nutritionist_user.id}"
                nutritionist_name = f"{nutritionist_user.first_name} {nutritionist_user.last_name}"
                nutritionist_user_id = nutritionist_user.id
            # Priorità 3: Usa il campo testuale se disponibile
            elif response.cliente and response.cliente.nutrizionista:
                nutritionist_name = _format_professional_name(response.cliente.nutrizionista)
                nutritionist_key = f"text_{response.cliente.nutrizionista}"
            # Fallback: Non specificato
            else:
                nutritionist_name = "Nutrizionista Non Specificato"
                nutritionist_key = "unknown"

            # Filtra in base al tipo di accesso (department head o team leader)
            if allowed_user_ids is not None and nutritionist_user_id:
                if nutritionist_user_id not in allowed_user_ids:
                    continue  # Salta questo feedback se il nutrizionista non è autorizzato

            if nutritionist_key and nutritionist_name:
                if nutritionist_key not in nutritionists:
                    nutritionists[nutritionist_key] = {
                        'name': nutritionist_name,
                        'display_name': nutritionist_name,
                        'user_id': nutritionist_user_id,
                        'responses': [],
                        'ratings': []
                    }

                nutritionists[nutritionist_key]['ratings'].append(nutritionist_rating)
                nutritionists[nutritionist_key]['responses'].append({
                    'id': response.id,
                    'rating': nutritionist_rating,
                    'feedback': getattr(response, 'nutritionist_feedback', None),
                    'client_name': response.cliente.nome_cognome if response.cliente else f"{getattr(response, 'first_name', '')} {getattr(response, 'last_name', '')}".strip() or "Cliente Sconosciuto",
                    'submit_date': response.submit_date
                })
    
    # Calculate averages and format results
    result = []
    for nutritionist_data in nutritionists.values():
        if nutritionist_data['ratings']:
            nutritionist_data['average_rating'] = round(sum(nutritionist_data['ratings']) / len(nutritionist_data['ratings']), 1)
            nutritionist_data['total_responses'] = len(nutritionist_data['responses'])
            # Ordina le risposte per data (più recenti prima)
            nutritionist_data['responses'] = sorted(
                nutritionist_data['responses'], 
                key=lambda x: x['submit_date'] if x['submit_date'] else datetime.min, 
                reverse=True
            )
            result.append(nutritionist_data)
    
    return sorted(result, key=lambda x: x['average_rating'], reverse=True)

def _generate_psychologist_data(responses, user_filter=None):
    """Generate psychologist-specific data from responses."""

    # Ottieni la lista degli user in base al tipo di filtro
    allowed_user_ids = None
    if user_filter:
        if user_filter['type'] == 'department':
            # Department head: vede tutti gli user del dipartimento Psicologia
            dept_psico = Department.query.filter(
                Department.name.ilike('%psicolog%')
            ).first()
            if dept_psico:
                allowed_user_ids = [u.id for u in dept_psico.members]
        elif user_filter['type'] == 'team':
            # Team leader: vede solo i membri del proprio team
            allowed_user_ids = user_filter.get('team_member_ids', [])

    psychologists = {}

    for response in responses:
        # Use getattr for DCACheckResponse compatibility
        psychologist_rating = getattr(response, 'psychologist_rating', None)
        if psychologist_rating is not None:
            psychologist_name = None
            psychologist_key = None
            psychologist_user_id = None

            # Priorità 1: Use User association if available
            resp_psychologist_user_id = getattr(response, 'psychologist_user_id', None)
            resp_psychologist_user = getattr(response, 'psychologist_user', None)
            if resp_psychologist_user_id and resp_psychologist_user:
                psychologist_user = resp_psychologist_user
                psychologist_key = f"user_{psychologist_user.id}"
                psychologist_name = f"{psychologist_user.first_name} {psychologist_user.last_name}"
                psychologist_user_id = psychologist_user.id
            # Priorità 2: Se non c'è associazione diretta ma c'è un cliente, usa i suoi professionisti
            elif response.cliente and response.cliente.psicologi_multipli:
                # Prendi il primo psicologo dalla relazione many-to-many
                psychologist_user = response.cliente.psicologi_multipli[0]
                psychologist_key = f"user_{psychologist_user.id}"
                psychologist_name = f"{psychologist_user.first_name} {psychologist_user.last_name}"
                psychologist_user_id = psychologist_user.id
            # Priorità 3: Usa il campo testuale se disponibile
            elif response.cliente and response.cliente.psicologa:
                psychologist_name = _format_professional_name(response.cliente.psicologa)
                psychologist_key = f"text_{response.cliente.psicologa}"
            # Fallback: Non specificato
            else:
                psychologist_name = "Psicologo Non Specificato"
                psychologist_key = "unknown"

            # Filtra in base al tipo di accesso (department head o team leader)
            if allowed_user_ids is not None and psychologist_user_id:
                if psychologist_user_id not in allowed_user_ids:
                    continue  # Salta questo feedback se lo psicologo non è autorizzato

            if psychologist_key and psychologist_name:
                if psychologist_key not in psychologists:
                    psychologists[psychologist_key] = {
                        'name': psychologist_name,
                        'display_name': psychologist_name,
                        'user_id': psychologist_user_id,
                        'responses': [],
                        'ratings': []
                    }

                psychologists[psychologist_key]['ratings'].append(psychologist_rating)
                psychologists[psychologist_key]['responses'].append({
                    'id': response.id,
                    'rating': psychologist_rating,
                    'feedback': getattr(response, 'psychologist_feedback', None),
                    'client_name': response.cliente.nome_cognome if response.cliente else f"{getattr(response, 'first_name', '')} {getattr(response, 'last_name', '')}".strip() or "Cliente Sconosciuto",
                    'submit_date': response.submit_date
                })
    
    # Calculate averages and format results
    result = []
    for psychologist_data in psychologists.values():
        if psychologist_data['ratings']:
            psychologist_data['average_rating'] = round(sum(psychologist_data['ratings']) / len(psychologist_data['ratings']), 1)
            psychologist_data['total_responses'] = len(psychologist_data['responses'])
            # Ordina le risposte per data (più recenti prima)
            psychologist_data['responses'] = sorted(
                psychologist_data['responses'], 
                key=lambda x: x['submit_date'] if x['submit_date'] else datetime.min, 
                reverse=True
            )
            result.append(psychologist_data)

    return sorted(result, key=lambda x: x['average_rating'], reverse=True)


# --------------------------------------------------------------------------- #
#  Chart Data Aggregation                                                     #
# --------------------------------------------------------------------------- #

def get_ratings_chart_data(responses, start_date, end_date, period: str, department: str = None):
    """
    Aggregate ratings data for chart visualization.

    Args:
        responses: List of response objects
        start_date: Period start date
        end_date: Period end date
        period: Period type ('week', 'month', 'trimester', 'year', 'custom')
        department: Specific department ('nutrizionista', 'psicologa', 'coach') or None for all

    Returns:
        Dict with labels and datasets for Chart.js
    """
    # Determine granularity based on period
    duration_days = (end_date - start_date).days

    if period == 'week' or duration_days <= 7:
        granularity = 'day'
        date_format = '%d/%m'
    elif period == 'month' or duration_days <= 31:
        granularity = 'day'
        date_format = '%d/%m'
    elif period == 'trimester' or duration_days <= 100:
        granularity = 'week'
        date_format = 'W%W'
    elif period == 'year' or duration_days > 100:
        granularity = 'month'
        date_format = '%b %Y'
    else:
        # Custom period
        if duration_days <= 14:
            granularity = 'day'
            date_format = '%d/%m'
        elif duration_days <= 90:
            granularity = 'week'
            date_format = 'W%W %Y'
        else:
            granularity = 'month'
            date_format = '%b %Y'

    # Generate time intervals
    intervals = []
    current = start_date

    if granularity == 'day':
        while current <= end_date:
            intervals.append({
                'start': current,
                'end': current.replace(hour=23, minute=59, second=59),
                'label': current.strftime(date_format)
            })
            current += timedelta(days=1)
    elif granularity == 'week':
        # Start from Monday of the first week
        while current.weekday() != 0:
            current -= timedelta(days=1)
        while current <= end_date:
            week_end = current + timedelta(days=6)
            intervals.append({
                'start': current,
                'end': min(week_end, end_date),
                'label': f"{current.strftime('%d/%m')} - {min(week_end, end_date).strftime('%d/%m')}"
            })
            current += timedelta(days=7)
    else:  # month
        while current <= end_date:
            # Last day of month
            if current.month == 12:
                month_end = current.replace(year=current.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = current.replace(month=current.month + 1, day=1) - timedelta(days=1)
            intervals.append({
                'start': current,
                'end': min(month_end.replace(hour=23, minute=59, second=59), end_date),
                'label': current.strftime(date_format)
            })
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

    # Aggregate ratings by interval
    if department:
        # Single department view
        rating_field_map = {
            'nutrizionista': 'nutritionist_rating',
            'psicologa': 'psychologist_rating',
            'coach': 'coach_rating'
        }
        rating_field = rating_field_map[department]

        data = []
        response_counts = []  # Track number of responses per interval
        for interval in intervals:
            ratings = []
            for resp in responses:
                if not resp.submit_date:
                    continue
                if interval['start'] <= resp.submit_date <= interval['end']:
                    rating = getattr(resp, rating_field, None)
                    # Note: responses are already filtered by get_department_responses
                    # No need to re-verify professional assignment
                    if rating is not None:
                        ratings.append(rating)

            # Calculate average or None if no data
            avg = round(sum(ratings) / len(ratings), 1) if ratings else None
            data.append(avg)
            response_counts.append(len(ratings))

        return {
            'labels': [interval['label'] for interval in intervals],
            'datasets': [{
                'label': f'Rating {department.title()}',
                'data': data,
                'response_counts': response_counts,  # Include counts for tooltip
                'borderColor': _get_color_for_department(department),
                'backgroundColor': _get_color_for_department(department, alpha=0.1),
                'tension': 0.4,
                'fill': True,
                'pointRadius': 4,
                'pointHoverRadius': 6
            }]
        }
    else:
        # Company view - all departments
        nutritionist_data = []
        psychologist_data = []
        coach_data = []
        progress_data = []
        nutritionist_counts = []
        psychologist_counts = []
        coach_counts = []
        progress_counts = []

        for interval in intervals:
            nutritionist_ratings = []
            psychologist_ratings = []
            coach_ratings = []
            progress_ratings = []

            for resp in responses:
                if not resp.submit_date:
                    continue
                if interval['start'] <= resp.submit_date <= interval['end']:
                    # Note: For company view, responses come from get_all_responses_for_period
                    # which includes all responses, so we need to verify professional assignment

                    # Nutritionist - verify client has nutritionist assigned
                    if hasattr(resp, 'nutritionist_rating') and resp.nutritionist_rating is not None:
                        if resp.cliente and _get_client_professional_ids(resp.cliente, 'nutrizionista'):
                            nutritionist_ratings.append(resp.nutritionist_rating)

                    # Psychologist - verify client has psychologist assigned
                    if hasattr(resp, 'psychologist_rating') and resp.psychologist_rating is not None:
                        if resp.cliente and _get_client_professional_ids(resp.cliente, 'psicologa'):
                            psychologist_ratings.append(resp.psychologist_rating)

                    # Coach - verify client has coach assigned
                    if hasattr(resp, 'coach_rating') and resp.coach_rating is not None:
                        if resp.cliente and _get_client_professional_ids(resp.cliente, 'coach'):
                            coach_ratings.append(resp.coach_rating)

                    # Progress - include all responses (even without assigned professionals)
                    if hasattr(resp, 'progress_rating') and resp.progress_rating is not None:
                        progress_ratings.append(resp.progress_rating)

            nutritionist_data.append(round(sum(nutritionist_ratings) / len(nutritionist_ratings), 1) if nutritionist_ratings else None)
            psychologist_data.append(round(sum(psychologist_ratings) / len(psychologist_ratings), 1) if psychologist_ratings else None)
            coach_data.append(round(sum(coach_ratings) / len(coach_ratings), 1) if coach_ratings else None)
            progress_data.append(round(sum(progress_ratings) / len(progress_ratings), 1) if progress_ratings else None)

            nutritionist_counts.append(len(nutritionist_ratings))
            psychologist_counts.append(len(psychologist_ratings))
            coach_counts.append(len(coach_ratings))
            progress_counts.append(len(progress_ratings))

        return {
            'labels': [interval['label'] for interval in intervals],
            'datasets': [
                {
                    'label': 'Nutrizionista',
                    'data': nutritionist_data,
                    'response_counts': nutritionist_counts,
                    'borderColor': '#22c55e',
                    'backgroundColor': 'rgba(34, 197, 94, 0.1)',
                    'tension': 0.4,
                    'fill': True,
                    'pointRadius': 4,
                    'pointHoverRadius': 6
                },
                {
                    'label': 'Psicologa',
                    'data': psychologist_data,
                    'response_counts': psychologist_counts,
                    'borderColor': '#8b5cf6',
                    'backgroundColor': 'rgba(139, 92, 246, 0.1)',
                    'tension': 0.4,
                    'fill': True,
                    'pointRadius': 4,
                    'pointHoverRadius': 6
                },
                {
                    'label': 'Coach',
                    'data': coach_data,
                    'response_counts': coach_counts,
                    'borderColor': '#f59e0b',
                    'backgroundColor': 'rgba(245, 158, 11, 0.1)',
                    'tension': 0.4,
                    'fill': True,
                    'pointRadius': 4,
                    'pointHoverRadius': 6
                },
                {
                    'label': 'Progresso',
                    'data': progress_data,
                    'response_counts': progress_counts,
                    'borderColor': '#3b82f6',
                    'backgroundColor': 'rgba(59, 130, 246, 0.1)',
                    'tension': 0.4,
                    'fill': True,
                    'pointRadius': 4,
                    'pointHoverRadius': 6
                }
            ]
        }


def _get_color_for_department(department: str, alpha: float = 1.0) -> str:
    """Get color for department chart line."""
    colors = {
        'nutrizionista': '#22c55e',  # Green
        'psicologa': '#8b5cf6',      # Purple
        'coach': '#f59e0b'           # Orange
    }

    if alpha < 1.0:
        # Convert hex to rgba
        hex_color = colors.get(department, '#3b82f6')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (1, 3, 5))
        return f'rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {alpha})'

    return colors.get(department, '#3b82f6') 