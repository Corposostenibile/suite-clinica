"""
Feedback routes for displaying TypeForm response data.
"""

from flask import (
    render_template,
    request,
    jsonify,
    flash,
    redirect,
    url_for,
    current_app,
    abort,
)
from flask_login import current_user
from corposostenibile.models import TypeFormResponse, Cliente, WeeklyCheckResponse, DCACheckResponse
from corposostenibile.extensions import db, csrf
from corposostenibile.blueprints.customers.services import _match_cliente
from .helpers import (
    can_access_nutrition_feedback,
    can_access_psychology_feedback,
    can_access_coach_feedback,
)
from sqlalchemy import or_
from . import services
from . import bp
from .forms import get_date_range_for_period, format_period_display, ResponseFilterForm
import hmac
import hashlib
import base64


def verify_typeform_signature(request):
    secret = current_app.config.get("TYPEFORM_WEBHOOK_SECRET")
    signature = request.headers.get("Typeform-Signature", "")
    if not secret or not signature.startswith("sha256="):
        return False
    signature = signature.replace("sha256=", "")
    raw_body = request.get_data()
    computed = hmac.new(secret.encode(), raw_body, hashlib.sha256).digest()
    computed_b64 = base64.b64encode(computed).decode()
    return hmac.compare_digest(signature, computed_b64)


@bp.route("/azienda")
def azienda():
    """Display overall company feedback with all ratings."""
    from .helpers import is_department_head

    # Check admin, user ID 95, or Customer Success head access for company overview
    if not current_user.is_admin and current_user.id != 95 and not is_department_head(['customer success']):
        abort(403)

    period = request.args.get("period", "month")
    offset = int(request.args.get("offset", 0))
    page = int(request.args.get("page", 1))
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    responses, pagination, total_responses, period_display, start_date, end_date = (
        services.get_filtered_responses(period, offset, page, start_date_str=start_date_str, end_date_str=end_date_str)
    )

    # Get ALL responses for the period to calculate correct averages
    all_responses = services.get_all_responses_for_period(period, offset, start_date_str=start_date_str, end_date_str=end_date_str)
    avg_ratings = services.calculate_average_ratings(all_responses)

    # Get chart data
    chart_data = services.get_ratings_chart_data(all_responses, start_date, end_date, period, department=None)

    return render_template(
        "feedback/azienda.html",
        responses=responses,
        pagination=pagination,
        avg_ratings=avg_ratings,
        period=period,
        offset=offset,
        period_display=period_display,
        start_date=start_date,
        end_date=end_date,
        total_responses=total_responses,
        current_route="feedback.azienda",
        other_params={},
        chart_data=chart_data,
    )


@bp.route("/nutrizionista")
def nutrizionista():
    """Display nutritionist department feedback with same style as azienda."""
    from .helpers import can_access_nutrition_feedback, get_user_feedback_filter

    # Check department access
    if not can_access_nutrition_feedback():
        abort(403)

    period = request.args.get("period", "month")
    offset = int(request.args.get("offset", 0))
    page = int(request.args.get("page", 1))
    professional_id = request.args.get("professional_id", type=int)
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    # Get user filter based on role
    user_filter = get_user_feedback_filter()

    # Get department responses with professional filter
    responses, pagination, all_responses, professionals_list, period_display, start_date, end_date = (
        services.get_department_responses("nutrizionista", period, offset, page, professional_id=professional_id, user_filter=user_filter, start_date_str=start_date_str, end_date_str=end_date_str)
    )

    # Calculate average rating for all responses in period
    avg_rating = services.calculate_department_average(all_responses, "nutrizionista")
    avg_quality = services.calculate_quality_average(all_responses, "nutrizionista")

    # Get chart data
    chart_data = services.get_ratings_chart_data(all_responses, start_date, end_date, period, department='nutrizionista')

    return render_template(
        "feedback/nutrizionista.html",
        responses=responses,
        pagination=pagination,
        avg_rating=avg_rating,
        avg_quality=avg_quality,
        professionals_list=professionals_list,
        selected_professional_id=professional_id,
        period=period,
        offset=offset,
        period_display=period_display,
        start_date=start_date,
        end_date=end_date,
        total_responses=len(all_responses),
        current_route="feedback.nutrizionista",
        other_params={'professional_id': professional_id} if professional_id else {},
        department='nutrizionista',
        chart_data=chart_data,
    )


@bp.route("/psicologa")
def psicologa():
    """Display psychologist department feedback with same style as azienda."""
    from .helpers import can_access_psychology_feedback, get_user_feedback_filter

    # Check department access
    if not can_access_psychology_feedback():
        abort(403)

    period = request.args.get("period", "month")
    offset = int(request.args.get("offset", 0))
    page = int(request.args.get("page", 1))
    professional_id = request.args.get("professional_id", type=int)
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    # Get user filter based on role
    user_filter = get_user_feedback_filter()

    # Get department responses with professional filter
    responses, pagination, all_responses, professionals_list, period_display, start_date, end_date = (
        services.get_department_responses("psicologa", period, offset, page, professional_id=professional_id, user_filter=user_filter, start_date_str=start_date_str, end_date_str=end_date_str)
    )

    # Calculate average rating for all responses in period
    avg_rating = services.calculate_department_average(all_responses, "psicologa")
    avg_quality = services.calculate_quality_average(all_responses, "psicologa")

    # Get chart data
    chart_data = services.get_ratings_chart_data(all_responses, start_date, end_date, period, department='psicologa')

    return render_template(
        "feedback/psicologa.html",
        responses=responses,
        pagination=pagination,
        avg_rating=avg_rating,
        avg_quality=avg_quality,
        professionals_list=professionals_list,
        selected_professional_id=professional_id,
        period=period,
        offset=offset,
        period_display=period_display,
        start_date=start_date,
        end_date=end_date,
        total_responses=len(all_responses),
        current_route="feedback.psicologa",
        other_params={'professional_id': professional_id} if professional_id else {},
        department='psicologa',
        chart_data=chart_data,
    )


@bp.route("/coach")
def coach():
    """Display coach department feedback with same style as azienda."""
    from .helpers import can_access_coach_feedback, get_user_feedback_filter

    # Check department access
    if not can_access_coach_feedback():
        abort(403)

    period = request.args.get("period", "month")
    offset = int(request.args.get("offset", 0))
    page = int(request.args.get("page", 1))
    professional_id = request.args.get("professional_id", type=int)
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    # Get user filter based on role
    user_filter = get_user_feedback_filter()

    # Get department responses with professional filter
    responses, pagination, all_responses, professionals_list, period_display, start_date, end_date = (
        services.get_department_responses("coach", period, offset, page, professional_id=professional_id, user_filter=user_filter, start_date_str=start_date_str, end_date_str=end_date_str)
    )

    # Calculate average rating for all responses in period
    avg_rating = services.calculate_department_average(all_responses, "coach")
    avg_quality = services.calculate_quality_average(all_responses, "coach")

    # Get chart data
    chart_data = services.get_ratings_chart_data(all_responses, start_date, end_date, period, department='coach')

    return render_template(
        "feedback/coach.html",
        responses=responses,
        pagination=pagination,
        avg_rating=avg_rating,
        avg_quality=avg_quality,
        professionals_list=professionals_list,
        selected_professional_id=professional_id,
        period=period,
        offset=offset,
        period_display=period_display,
        start_date=start_date,
        end_date=end_date,
        total_responses=len(all_responses),
        current_route="feedback.coach",
        other_params={'professional_id': professional_id} if professional_id else {},
        department='coach',
        chart_data=chart_data,
    )


@bp.route("/health-manager")
def health_manager():
    """Display health manager feedback - shows all professional ratings for clients assigned to health managers."""
    from .helpers import can_access_health_manager_feedback, get_user_feedback_filter

    # Check access
    if not can_access_health_manager_feedback():
        abort(403)

    period = request.args.get("period", "month")
    offset = int(request.args.get("offset", 0))
    page = int(request.args.get("page", 1))
    health_manager_id = request.args.get("health_manager_id", type=int)
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    # Get user filter based on role
    user_filter = get_user_feedback_filter()

    # Get health manager responses
    responses, pagination, all_responses, health_managers_list, period_display, start_date, end_date = (
        services.get_health_manager_responses(period, offset, page, health_manager_id=health_manager_id, user_filter=user_filter, start_date_str=start_date_str, end_date_str=end_date_str)
    )

    # Calculate average ratings (same as azienda page)
    avg_ratings = services.calculate_average_ratings(all_responses)

    return render_template(
        "feedback/health_manager.html",
        responses=responses,
        pagination=pagination,
        avg_ratings=avg_ratings,
        health_managers_list=health_managers_list,
        selected_health_manager_id=health_manager_id,
        period=period,
        offset=offset,
        period_display=period_display,
        start_date=start_date,
        end_date=end_date,
        total_responses=len(all_responses),
        current_route="feedback.health_manager",
        other_params={'health_manager_id': health_manager_id} if health_manager_id else {},
    )


@bp.route("/response/<int:response_id>")
def get_response_details(response_id):
    """Get detailed response information for modal display (TypeForm, WeeklyCheck, DCACheck)."""
    from .helpers import is_in_department, is_department_head

    if (
        not current_user.is_admin
        and current_user.id != 95
        and not can_access_nutrition_feedback()
        and not can_access_psychology_feedback()
        and not can_access_coach_feedback()
    ):
        abort(403)

    try:
        from sqlalchemy.orm import joinedload, selectinload

        # Try to find response in all three tables with eager loading
        response = TypeFormResponse.query.options(
            joinedload(TypeFormResponse.cliente).selectinload(Cliente.nutrizionisti_multipli),
            joinedload(TypeFormResponse.cliente).selectinload(Cliente.psicologi_multipli),
            joinedload(TypeFormResponse.cliente).selectinload(Cliente.coaches_multipli),
            joinedload(TypeFormResponse.cliente).joinedload(Cliente.nutrizionista_user),
            joinedload(TypeFormResponse.cliente).joinedload(Cliente.psicologa_user),
            joinedload(TypeFormResponse.cliente).joinedload(Cliente.coach_user)
        ).filter_by(id=response_id).first()
        response_type = 'typeform'

        if not response:
            from corposostenibile.models import WeeklyCheck
            response = WeeklyCheckResponse.query.options(
                joinedload(WeeklyCheckResponse.assignment).joinedload(WeeklyCheck.cliente).selectinload(Cliente.nutrizionisti_multipli),
                joinedload(WeeklyCheckResponse.assignment).joinedload(WeeklyCheck.cliente).selectinload(Cliente.psicologi_multipli),
                joinedload(WeeklyCheckResponse.assignment).joinedload(WeeklyCheck.cliente).selectinload(Cliente.coaches_multipli),
                joinedload(WeeklyCheckResponse.assignment).joinedload(WeeklyCheck.cliente).joinedload(Cliente.nutrizionista_user),
                joinedload(WeeklyCheckResponse.assignment).joinedload(WeeklyCheck.cliente).joinedload(Cliente.psicologa_user),
                joinedload(WeeklyCheckResponse.assignment).joinedload(WeeklyCheck.cliente).joinedload(Cliente.coach_user)
            ).filter_by(id=response_id).first()
            response_type = 'weekly_check'

        if not response:
            from corposostenibile.models import DCACheck
            response = DCACheckResponse.query.options(
                joinedload(DCACheckResponse.assignment).joinedload(DCACheck.cliente).selectinload(Cliente.nutrizionisti_multipli),
                joinedload(DCACheckResponse.assignment).joinedload(DCACheck.cliente).selectinload(Cliente.psicologi_multipli),
                joinedload(DCACheckResponse.assignment).joinedload(DCACheck.cliente).selectinload(Cliente.coaches_multipli),
                joinedload(DCACheckResponse.assignment).joinedload(DCACheck.cliente).joinedload(Cliente.nutrizionista_user),
                joinedload(DCACheckResponse.assignment).joinedload(DCACheck.cliente).joinedload(Cliente.psicologa_user),
                joinedload(DCACheckResponse.assignment).joinedload(DCACheck.cliente).joinedload(Cliente.coach_user)
            ).filter_by(id=response_id).first()
            response_type = 'dca_check'

        if not response:
            abort(404)

        # Get cliente based on response type
        if response_type == 'typeform':
            cliente = response.cliente
        else:
            # For WeeklyCheck and DCACheck, get cliente through assignment
            cliente = response.assignment.cliente if response.assignment else None
        
        # Determina il tipo di utente e quali valutazioni può vedere
        user_type = None
        can_see_nutrition = False
        can_see_psychology = False
        can_see_coach = False

        if current_user.is_admin or current_user.id == 95:
            user_type = 'admin'
            can_see_nutrition = True
            can_see_psychology = True
            can_see_coach = True
        elif is_in_department(['nutrizion']) or is_department_head(['nutrizion']):
            user_type = 'nutrition'
            can_see_nutrition = True
        elif is_in_department(['psicolog']) or is_department_head(['psicolog']):
            user_type = 'psychology'
            can_see_psychology = True
        elif is_in_department(['coach', 'sport']) or is_department_head(['coach', 'sport']):
            user_type = 'coach'
            can_see_coach = True
        elif is_department_head(['customer success']):
            # Customer Success heads can see all
            user_type = 'customer_success_head'
            can_see_nutrition = True
            can_see_psychology = True
            can_see_coach = True

        # Helper function to get professional info from User objects
        def get_professional_info(cliente, role):
            """Get professional names and avatars from User relationships (not legacy text fields)."""
            professionals = []

            if role == 'nutritionist':
                # Get from many-to-many relationship
                if cliente.nutrizionisti_multipli:
                    professionals.extend(cliente.nutrizionisti_multipli)
                # Add single relationship if not already in list
                if cliente.nutrizionista_user and cliente.nutrizionista_user not in professionals:
                    professionals.append(cliente.nutrizionista_user)
            elif role == 'psychologist':
                if cliente.psicologi_multipli:
                    professionals.extend(cliente.psicologi_multipli)
                if cliente.psicologa_user and cliente.psicologa_user not in professionals:
                    professionals.append(cliente.psicologa_user)
            elif role == 'coach':
                if cliente.coaches_multipli:
                    professionals.extend(cliente.coaches_multipli)
                if cliente.coach_user and cliente.coach_user not in professionals:
                    professionals.append(cliente.coach_user)

            # Format names and include avatar URLs
            formatted = []
            for prof in professionals:
                if prof:
                    name_parts = prof.full_name.split() if prof.full_name else []
                    if len(name_parts) >= 2:
                        formatted_name = f"{name_parts[0]} {name_parts[1][0]}."
                    else:
                        formatted_name = prof.full_name if prof.full_name else "Unknown"

                    formatted.append({
                        'name': formatted_name,
                        'full_name': prof.full_name,
                        'avatar_url': prof.avatar_url
                    })

            return formatted

        # Format the response data
        response_data = {
            "user_type": user_type,
            "can_see_nutrition": can_see_nutrition,
            "can_see_psychology": can_see_psychology,
            "can_see_coach": can_see_coach,
            "id": response.id,
            "response_type": response_type,
            "client_name": cliente.nome_cognome if cliente else None,
            "submit_date": (
                response.submit_date.strftime("%d/%m/%Y %H:%M")
                if response.submit_date
                else None
            ),
            # Associated specialists (names and avatars from User objects)
            "nutritionists": get_professional_info(cliente, 'nutritionist') if cliente else [],
            "psychologists": get_professional_info(cliente, 'psychologist') if cliente else [],
            "coaches": get_professional_info(cliente, 'coach') if cliente else [],
            # Ratings (use getattr for compatibility with DCACheck)
            "nutritionist_rating": getattr(response, 'nutritionist_rating', None),
            "psychologist_rating": getattr(response, 'psychologist_rating', None),
            "coach_rating": getattr(response, 'coach_rating', None),
            "progress_rating": getattr(response, 'progress_rating', None),
            # Coordinator rating and notes
            "coordinator_rating": getattr(response, 'coordinator_rating', None),
            "coordinator_notes": getattr(response, 'coordinator_notes', None),
            # Feedback
            "nutritionist_feedback": getattr(response, 'nutritionist_feedback', None),
            "psychologist_feedback": getattr(response, 'psychologist_feedback', None),
            "coach_feedback": getattr(response, 'coach_feedback', None),
            # Weekly reflections
            "what_worked": getattr(response, 'what_worked', None),
            "what_didnt_work": getattr(response, 'what_didnt_work', None),
            "what_learned": getattr(response, 'what_learned', None),
            "what_focus_next": getattr(response, 'what_focus_next', None),
            "injuries_notes": getattr(response, 'injuries_notes', None),
            # Physical metrics
            "digestion_rating": getattr(response, 'digestion_rating', None),
            "energy_rating": getattr(response, 'energy_rating', None),
            "strength_rating": getattr(response, 'strength_rating', None),
            "hunger_rating": getattr(response, 'hunger_rating', None),
            "sleep_rating": getattr(response, 'sleep_rating', None),
            "mood_rating": getattr(response, 'mood_rating', None),
            "motivation_rating": getattr(response, 'motivation_rating', None),
            "weight": getattr(response, 'weight', None),
            # Program adherence
            "nutrition_program_adherence": getattr(response, 'nutrition_program_adherence', None),
            "training_program_adherence": getattr(response, 'training_program_adherence', None),
            "exercise_modifications": getattr(response, 'exercise_modifications', None),
            "daily_steps": getattr(response, 'daily_steps', None),
            "completed_training_weeks": getattr(response, 'completed_training_weeks', None),
            "planned_training_days": getattr(response, 'planned_training_days', None),
            # Photos
            "photo_front": getattr(response, 'photo_front', None),
            "photo_side": getattr(response, 'photo_side', None),
            "photo_back": getattr(response, 'photo_back', None),
            # Other fields
            "live_session_topics": getattr(response, 'live_session_topics', None),
            "referral": getattr(response, 'referral', None),
            "extra_comments": getattr(response, 'extra_comments', None),
            # DCA Check specific fields (1-5 scale)
            "mood_balance_rating": getattr(response, 'mood_balance_rating', None),
            "food_plan_serenity": getattr(response, 'food_plan_serenity', None),
            "food_weight_worry": getattr(response, 'food_weight_worry', None),
            "emotional_eating": getattr(response, 'emotional_eating', None),
            "body_comfort": getattr(response, 'body_comfort', None),
            "body_respect": getattr(response, 'body_respect', None),
            "exercise_wellness": getattr(response, 'exercise_wellness', None),
            "exercise_guilt": getattr(response, 'exercise_guilt', None),
            "sleep_satisfaction": getattr(response, 'sleep_satisfaction', None),
            "relationship_time": getattr(response, 'relationship_time', None),
            "personal_time": getattr(response, 'personal_time', None),
            "life_interference": getattr(response, 'life_interference', None),
            "unexpected_management": getattr(response, 'unexpected_management', None),
            "self_compassion": getattr(response, 'self_compassion', None),
            "inner_dialogue": getattr(response, 'inner_dialogue', None),
            "long_term_sustainability": getattr(response, 'long_term_sustainability', None),
            "values_alignment": getattr(response, 'values_alignment', None),
            "motivation_level": getattr(response, 'motivation_level', None),
            "meal_organization": getattr(response, 'meal_organization', None),
            "meal_stress": getattr(response, 'meal_stress', None),
            "shopping_awareness": getattr(response, 'shopping_awareness', None),
            "shopping_impact": getattr(response, 'shopping_impact', None),
            "meal_clarity": getattr(response, 'meal_clarity', None),
        }

        return jsonify({"success": True, "response": response_data})

    except Exception as e:
        current_app.logger.error(f"Error loading response details for ID {response_id}: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/responses", methods=["GET"])
def responses_list():
    """Lista risposte TypeForm con filtri e paginazione."""
    from .helpers import is_department_head

    if not current_user.is_admin and current_user.id != 95 and not is_department_head(['customer success']):
        abort(403)

    form = ResponseFilterForm(request.args, meta={"csrf": False})

    # Get filter parameters
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "unmatched")  # Default: show only unmatched
    page = request.args.get("page", 1, type=int)
    per_page = 25

    # Build query
    query = TypeFormResponse.query

    # Apply name filter
    if q:
        query = query.filter(
            or_(
                TypeFormResponse.first_name.ilike(f"%{q}%"),
                TypeFormResponse.last_name.ilike(f"%{q}%"),
            )
        )

    # Apply status filter - default to unmatched
    if status == "matched":
        query = query.filter(TypeFormResponse.cliente_id.isnot(None))
    elif status == "unmatched":
        query = query.filter(TypeFormResponse.cliente_id.is_(None))
    # If status is "all" or empty string, show all (no filter)

    # Order by submit date (newest first)
    query = query.order_by(TypeFormResponse.submit_date.desc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "feedback/responses.html",
        responses=pagination.items,
        pagination=pagination,
        form=form,
        filters_applied=bool(q or status),
        _match_cliente=_match_cliente,
    )


@bp.route("/responses/<int:response_id>/associate", methods=["POST"])
def associate_response(response_id):
    """Associate a TypeForm response with a client"""
    if (
        not current_user.is_admin
        and current_user.id != 95
        and not can_access_nutrition_feedback()
        and not can_access_psychology_feedback()
        and not can_access_coach_feedback()
    ):
        abort(403)

    cliente_id = request.form.get("cliente_id")
    if not cliente_id:
        flash("No client selected", "error")
        return redirect(url_for("feedback.responses_list"))

    success, message = services.manually_associate_response(response_id, cliente_id)

    if success:
        flash(message, "success")
    else:
        flash(message, "error")

    return redirect(url_for("feedback.responses_list"))


@bp.route("/api/search_customers")
def api_search_customers():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])
    results = (
        Cliente.query.filter(Cliente.nome_cognome.ilike(f"%{q}%"))
        .order_by(Cliente.nome_cognome)
        .limit(10)
        .all()
    )
    return jsonify([{"id": c.cliente_id, "name": c.nome_cognome} for c in results])


@csrf.exempt
@bp.route("/webhook", methods=["POST"])
def webhook():
    if not verify_typeform_signature(request):
        return {"error": "Invalid signature"}, 403
    data = request.get_json(force=True)
    if not data or "form_response" not in data:
        return {"error": "Invalid payload"}, 400
    form_response = data["form_response"]
    answers = form_response.get("answers", [])
    field_map = services.TYPEFORM_CONFIG.get("field_mapping", {})
    answer_dict = {}
    for ans in answers:
        field_id = ans.get("field", {}).get("id")
        if not field_id:
            continue
        if "text" in ans:
            answer_dict[field_id] = ans["text"]
        elif "email" in ans:
            answer_dict[field_id] = ans["email"]
        elif "date" in ans:
            answer_dict[field_id] = ans["date"]
        elif "number" in ans:
            answer_dict[field_id] = ans["number"]
        elif "boolean" in ans:
            answer_dict[field_id] = ans["boolean"]
        elif "choice" in ans and "label" in ans["choice"]:
            answer_dict[field_id] = ans["choice"]["label"]

    # Extract name for client matching
    first_name = answer_dict.get(field_map.get("first_name"), "")
    last_name = answer_dict.get(field_map.get("last_name"), "")
    raw_name = f"{first_name} {last_name}".strip()

    # Try to match client automatically
    cliente = None
    if raw_name:
        from scripts.import_typeform_csv import normalize_name, _best_match

        norm_raw_name = normalize_name(raw_name)
        matched_clienti = [
            c
            for c in Cliente.query.all()
            if normalize_name(c.nome_cognome) == norm_raw_name
        ]

        if len(matched_clienti) == 1:
            cliente = matched_clienti[0]

    # Create response with or without client association
    response = TypeFormResponse(
        first_name=first_name,
        last_name=last_name,
        submit_date=form_response.get("submitted_at"),
        raw_response_data=data,  # Save the original webhook data
        cliente_id=cliente.cliente_id if cliente else None,
        is_matched=cliente is not None,
    )

    db.session.add(response)
    db.session.commit()
    return {"status": "ok"}, 200


@bp.route("/api/response/<int:response_id>/coordinator-rating", methods=["POST"])
def save_coordinator_rating(response_id):
    """Save coordinator rating and notes for a response."""
    if not current_user.is_authenticated:
        return jsonify({"error": "Non autorizzato"}), 401

    # Check if user has permission (admins, user ID 95, or department heads)
    from .helpers import is_department_head
    if not current_user.is_admin and current_user.id != 95 and not is_department_head(['customer success']):
        return jsonify({"error": "Non hai i permessi per questa operazione"}), 403

    data = request.get_json()
    rating = data.get("rating")
    notes = data.get("notes", "").strip()

    # Validate rating (1-10)
    if not rating or not isinstance(rating, int) or rating < 1 or rating > 10:
        return jsonify({"error": "Voto non valido. Deve essere tra 1 e 10"}), 400

    # Validate notes (required)
    if not notes:
        return jsonify({"error": "Le note sono obbligatorie"}), 400

    # Try to find response in TypeFormResponse or WeeklyCheckResponse
    response = TypeFormResponse.query.get(response_id)
    if not response:
        response = WeeklyCheckResponse.query.get(response_id)

    if not response:
        return jsonify({"error": "Risposta non trovata"}), 404

    # Update coordinator rating and notes
    response.coordinator_rating = rating
    response.coordinator_notes = notes

    db.session.commit()

    return jsonify({
        "status": "ok",
        "coordinator_rating": rating,
        "coordinator_notes": notes
    }), 200
