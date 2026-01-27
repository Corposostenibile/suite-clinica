"""
Quality Score API Routes
API routes for Quality Score management (ADMIN ONLY).
All routes return JSON for React frontend consumption.
"""
from flask import request, jsonify
from flask_login import login_required, current_user
from datetime import date, datetime, timedelta
from sqlalchemy import desc, func
from corposostenibile.extensions import db, csrf
from corposostenibile.models import (
    User,
    Cliente,
    QualityWeeklyScore,
    QualityClientScore,
    TrustpilotReview,
    EleggibilitaSettimanale,
    WeeklyCheck,
    WeeklyCheckResponse,
    TypeFormResponse,
    DCACheckResponse,
    UserSpecialtyEnum,
)
from .services import (
    EligibilityService,
    ReviewService,
    QualityScoreCalculator,
)
from . import bp


def admin_required(f):
    """Decorator per verificare accesso admin."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({'success': False, 'error': 'Accesso negato. Solo amministratori.'}), 403
        return f(*args, **kwargs)
    return decorated_function


# Specialty configuration
DEPT_CONFIG = {
    'nutrizione': {'id': 2, 'name': 'Nutrizione'},
    'coach': {'id': 3, 'name': 'Coach'},
    'psicologia': {'id': 4, 'name': 'Psicologia'},
}

# Specialty to DB enum mapping
SPECIALTY_FILTER_MAP = {
    'nutrizione': ['nutrizione', 'nutrizionista'],
    'nutrizionista': ['nutrizione', 'nutrizionista'],
    'coach': ['coach'],
    'psicologia': ['psicologia', 'psicologo'],
    'psicologo': ['psicologia', 'psicologo'],
}


# ============================================================================
# API CORE - WEEKLY SCORES
# ============================================================================

@bp.route('/api/weekly-scores')
@login_required
def api_weekly_scores():
    """
    API: Restituisce Quality Score settimanali per tutti i professionisti di una specialità.

    Query params:
        - specialty: 'nutrizione', 'coach', 'psicologia' (required)
        - week: YYYY-MM-DD (optional, default: current week)
        - team_id: filter by team (optional)

    Returns JSON con lista di score per professionista.
    """
    specialty = request.args.get('specialty', 'nutrizione')
    week_param = request.args.get('week')
    team_id = request.args.get('team_id', type=int)

    specialty_values = SPECIALTY_FILTER_MAP.get(specialty.lower())
    if not specialty_values:
        return jsonify({'error': 'Invalid specialty'}), 400

    # Parse week date
    if week_param:
        try:
            target_date = datetime.strptime(week_param, '%Y-%m-%d').date()
        except:
            target_date = date.today()
    else:
        target_date = date.today()

    week_start, week_end = EligibilityService.get_week_bounds(target_date)

    # Get professionals by specialty
    specialty_enums = [UserSpecialtyEnum(v) for v in specialty_values if v in [e.value for e in UserSpecialtyEnum]]

    prof_query = db.session.query(User).filter(
        User.is_active == True,
        User.specialty.in_(specialty_enums)
    )

    if team_id:
        prof_query = prof_query.filter(User.team_id == team_id)

    professionisti = prof_query.order_by(User.last_name).all()

    # Get weekly scores for these professionals
    prof_ids = [p.id for p in professionisti]
    scores = {}
    if prof_ids:
        score_records = db.session.query(QualityWeeklyScore).filter(
            QualityWeeklyScore.professionista_id.in_(prof_ids),
            QualityWeeklyScore.week_start_date == week_start
        ).all()
        scores = {s.professionista_id: s for s in score_records}

    # Build response with professionals and their scores
    result = []
    total_eligible = 0
    total_checks = 0
    total_quality = 0
    quality_count = 0
    total_miss_rate = 0
    miss_rate_count = 0

    for prof in professionisti:
        score = scores.get(prof.id)
        prof_data = {
            'id': prof.id,
            'first_name': prof.first_name,
            'last_name': prof.last_name,
            'email': prof.email,
            'specialty': prof.specialty.value if prof.specialty else None,
            'team_id': prof.team_id,
            'avatar_url': prof.avatar_url if hasattr(prof, 'avatar_url') else None,
            'quality': None
        }

        if score:
            prof_data['quality'] = {
                'n_clients_eligible': score.n_clients_eligible,
                'n_checks_done': score.n_checks_done,
                'miss_rate': score.miss_rate,
                'quality_raw': score.quality_raw,
                'quality_final': score.quality_final,
                'quality_month': score.quality_month,
                'quality_trim': score.quality_trim,
                'bonus_band': score.bonus_band,
                'trend_indicator': score.trend_indicator,
                'delta_vs_last_week': score.delta_vs_last_week,
                # New KPI fields
                'rinnovo_adj_percentage': score.rinnovo_adj_percentage,
                'rinnovo_adj_bonus_band': score.rinnovo_adj_bonus_band,
                'quality_bonus_band': score.quality_bonus_band,
                'final_bonus_percentage': score.final_bonus_percentage,
                'super_malus_applied': score.super_malus_applied,
                'super_malus_percentage': score.super_malus_percentage,
                'final_bonus_after_malus': score.final_bonus_after_malus,
            }
            # Aggregate stats
            total_eligible += score.n_clients_eligible or 0
            total_checks += score.n_checks_done or 0
            if score.quality_final is not None:
                total_quality += score.quality_final
                quality_count += 1
            if score.miss_rate is not None:
                total_miss_rate += score.miss_rate
                miss_rate_count += 1

        result.append(prof_data)

    # Calculate aggregated stats
    stats = {
        'total_professionisti': len(professionisti),
        'with_score': quality_count,
        'total_eligible': total_eligible,
        'total_checks': total_checks,
        'avg_quality': round(total_quality / quality_count, 2) if quality_count > 0 else None,
        'avg_miss_rate': round(total_miss_rate / miss_rate_count, 4) if miss_rate_count > 0 else None,
    }

    return jsonify({
        'success': True,
        'week_start': week_start.strftime('%Y-%m-%d'),
        'week_end': week_end.strftime('%Y-%m-%d'),
        'specialty': specialty,
        'professionals': result,
        'stats': stats,
    })


@bp.route('/api/professionista/<int:user_id>/trend')
@login_required
@admin_required
def api_professionista_trend(user_id):
    """API: trend Quality Score professionista (ultime 12 settimane)."""
    scores = db.session.query(QualityWeeklyScore).filter_by(
        professionista_id=user_id
    ).order_by(QualityWeeklyScore.week_start_date).limit(12).all()

    data = {
        'labels': [s.week_start_date.strftime('%d/%m') for s in scores],
        'quality_final': [s.quality_final for s in scores],
        'quality_month': [s.quality_month for s in scores],
        'quality_trim': [s.quality_trim for s in scores],
        'miss_rate': [s.miss_rate * 100 for s in scores if s.miss_rate],
    }

    return jsonify(data)


@bp.route('/api/dashboard/stats')
@login_required
@admin_required
def api_dashboard_stats():
    """API: statistiche generali dashboard."""
    week_start, _ = EligibilityService.get_week_bounds()

    weekly_scores = db.session.query(QualityWeeklyScore).filter_by(
        week_start_date=week_start
    ).all()

    # Distribuzione bonus bands
    bands_count = {
        '100%': 0,
        '60%': 0,
        '30%': 0,
        '0%': 0,
    }

    for s in weekly_scores:
        if s.bonus_band and s.bonus_band in bands_count:
            bands_count[s.bonus_band] += 1

    data = {
        'total_professionisti': len(weekly_scores),
        'bands_distribution': bands_count,
        'avg_quality': round(sum(s.quality_final for s in weekly_scores if s.quality_final) / len(weekly_scores), 2) if weekly_scores else 0,
    }

    return jsonify(data)


# ============================================================================
# API CALCOLO
# ============================================================================

@bp.route('/api/calculate', methods=['POST'])
@csrf.exempt
@login_required
@admin_required
def api_calculate_quality():
    """
    API: Calcola Quality Score per una specialità e settimana.

    JSON body:
        - specialty: 'nutrizione', 'coach', 'psicologia' (required)
        - week: YYYY-MM-DD (required)
        - team_id: filter by team (optional)

    Returns JSON con risultati del calcolo.
    """
    data = request.get_json() or {}
    specialty = data.get('specialty', 'nutrizione')
    week_str = data.get('week')
    team_id = data.get('team_id')

    if not week_str:
        return jsonify({'success': False, 'error': 'week is required'}), 400

    try:
        week_start = datetime.strptime(week_str, '%Y-%m-%d').date()
    except:
        return jsonify({'success': False, 'error': 'Invalid week format'}), 400

    week_start, week_end = EligibilityService.get_week_bounds(week_start)

    # Get department config
    if specialty not in DEPT_CONFIG:
        return jsonify({'success': False, 'error': 'Invalid specialty'}), 400

    dept_id = DEPT_CONFIG[specialty]['id']

    # Find professionals
    prof_query = db.session.query(User).filter(
        User.is_active == True,
        User.department_id == dept_id
    )
    if team_id:
        prof_query = prof_query.filter(User.team_id == team_id)

    professionisti = prof_query.all()

    import time
    start_time = time.time()

    results = {
        'total_professionisti': len(professionisti),
        'processed': 0,
        'eligible_total': 0,
        'checks_total': 0,
        'scores': []
    }

    try:
        # 1. Calculate eligibility
        for prof in professionisti:
            EligibilityService.calculate_eligibility_for_week(
                week_start=week_start,
                professionista_id=prof.id
            )

        # 2. Process check responses
        check_stats = QualityScoreCalculator.process_check_responses_for_week(
            week_start=week_start
        )
        db.session.commit()

        # 3. Calculate weekly scores
        for prof in professionisti:
            weekly_score = QualityScoreCalculator.calculate_weekly_score(
                professionista_id=prof.id,
                week_start=week_start,
                calculated_by_user_id=current_user.id
            )

            results['processed'] += 1
            if weekly_score:
                results['eligible_total'] += weekly_score.n_clients_eligible or 0
                results['checks_total'] += weekly_score.n_checks_done or 0
                results['scores'].append({
                    'professionista_id': prof.id,
                    'professionista_name': f"{prof.first_name} {prof.last_name}",
                    'quality_final': weekly_score.quality_final,
                    'n_clients': weekly_score.n_clients_eligible,
                    'n_checks': weekly_score.n_checks_done,
                    'miss_rate': round(weekly_score.miss_rate * 100, 1) if weekly_score.miss_rate else None,
                })

        db.session.commit()

        elapsed = time.time() - start_time
        results['elapsed_seconds'] = round(elapsed, 1)
        results['success'] = True
        results['check_processing'] = check_stats

        return jsonify(results)

    except Exception as e:
        db.session.rollback()
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/api/calcola/<dept_key>', methods=['POST'])
@csrf.exempt
@login_required
@admin_required
def api_calcola_dipartimento(dept_key):
    """API: Calcola Quality Score per un dipartimento specifico."""
    if dept_key not in DEPT_CONFIG:
        return jsonify({'success': False, 'error': 'Dipartimento non valido'}), 400

    config = DEPT_CONFIG[dept_key]
    dept_id = config['id']

    # Parametri
    week_start_str = request.form.get('week_start') or request.json.get('week_start')

    try:
        week_start = datetime.strptime(week_start_str, '%Y-%m-%d').date()
    except:
        week_start, _ = EligibilityService.get_week_bounds()

    week_start, week_end = EligibilityService.get_week_bounds(week_start)

    # Trova professionisti del dipartimento
    professionisti = db.session.query(User).filter(
        User.is_active == True,
        User.department_id == dept_id
    ).all()

    import time
    start_time = time.time()

    results = {
        'total_professionisti': len(professionisti),
        'processed': 0,
        'eligible_total': 0,
        'checks_total': 0,
        'scores': []
    }

    try:
        # 1. Calcola eleggibilità per ogni professionista
        for prof in professionisti:
            EligibilityService.calculate_eligibility_for_week(
                week_start=week_start,
                professionista_id=prof.id
            )

        # 2. Processa check responses
        check_stats = QualityScoreCalculator.process_check_responses_for_week(
            week_start=week_start
        )
        db.session.commit()

        # 3. Calcola weekly scores
        for prof in professionisti:
            weekly_score = QualityScoreCalculator.calculate_weekly_score(
                professionista_id=prof.id,
                week_start=week_start,
                calculated_by_user_id=current_user.id
            )

            results['processed'] += 1
            if weekly_score:
                results['eligible_total'] += weekly_score.n_clients_eligible or 0
                results['checks_total'] += weekly_score.n_checks_done or 0
                results['scores'].append({
                    'professionista_id': prof.id,
                    'professionista_name': f"{prof.first_name} {prof.last_name}",
                    'quality_final': weekly_score.quality_final,
                    'n_clients': weekly_score.n_clients_eligible,
                    'n_checks': weekly_score.n_checks_done,
                    'miss_rate': round(weekly_score.miss_rate * 100, 1) if weekly_score.miss_rate else None,
                })

        db.session.commit()

        elapsed = time.time() - start_time
        results['elapsed_seconds'] = round(elapsed, 1)
        results['success'] = True
        results['check_processing'] = check_stats

        return jsonify(results)

    except Exception as e:
        db.session.rollback()
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


# ============================================================================
# API CLIENTI ED ELEGGIBILITÀ
# ============================================================================

@bp.route('/api/clienti-eleggibili/<int:prof_id>')
@login_required
@admin_required
def api_clienti_eleggibili(prof_id):
    """API: Recupera clienti eleggibili per un professionista in una settimana."""
    week_start_str = request.args.get('week')

    try:
        week_start = datetime.strptime(week_start_str, '%Y-%m-%d').date()
    except:
        week_start, _ = EligibilityService.get_week_bounds()

    week_start, week_end = EligibilityService.get_week_bounds(week_start)

    # Recupera eleggibilità
    eligibilities = db.session.query(EleggibilitaSettimanale).filter_by(
        professionista_id=prof_id,
        week_start_date=week_start,
        eleggibile=True
    ).all()

    # Costruisci lista clienti
    clienti = []
    for elig in eligibilities:
        cliente = elig.cliente
        if cliente:
            clienti.append({
                'id': cliente.cliente_id,
                'nome': cliente.nome_cognome,
                'email': cliente.email,
                'check_effettuato': elig.check_effettuato,
                'stato_nutrizione': cliente.stato_nutrizione,
                'stato_coach': cliente.stato_coach,
                'stato_psicologia': cliente.stato_psicologia,
                'data_inizio': cliente.data_inizio_abbonamento.strftime('%d/%m/%Y') if cliente.data_inizio_abbonamento else None,
            })

    # Ordina: prima chi non ha fatto il check, poi per nome
    clienti.sort(key=lambda x: (x['check_effettuato'], x['nome']))

    return jsonify({
        'success': True,
        'week_start': week_start.strftime('%d/%m/%Y'),
        'week_end': week_end.strftime('%d/%m/%Y'),
        'total': len(clienti),
        'check_done': sum(1 for c in clienti if c['check_effettuato']),
        'clienti': clienti
    })


@bp.route('/api/check-responses/<int:prof_id>')
@login_required
@admin_required
def api_check_responses(prof_id):
    """API: Recupera le risposte ai check settimanali per un professionista in una settimana."""
    week_start_str = request.args.get('week')
    dept = request.args.get('dept', 'nutrizione')

    try:
        week_start = datetime.strptime(week_start_str, '%Y-%m-%d').date()
    except:
        week_start, _ = EligibilityService.get_week_bounds()

    week_start, week_end = EligibilityService.get_week_bounds(week_start)
    week_start_dt = datetime.combine(week_start, datetime.min.time())
    week_end_dt = datetime.combine(week_end, datetime.max.time())

    # Trova clienti eleggibili
    eligibilities = db.session.query(EleggibilitaSettimanale).filter_by(
        professionista_id=prof_id,
        week_start_date=week_start,
        eleggibile=True
    ).all()

    cliente_ids = [e.cliente_id for e in eligibilities]
    clienti = db.session.query(Cliente).filter(Cliente.cliente_id.in_(cliente_ids)).all() if cliente_ids else []

    responses_list = []

    for cliente in clienti:
        # Cerca WeeklyCheckResponse nella settimana
        weekly_checks = db.session.query(WeeklyCheck).filter_by(
            cliente_id=cliente.cliente_id,
            is_active=True
        ).all()

        for wc in weekly_checks:
            responses = db.session.query(WeeklyCheckResponse).filter(
                WeeklyCheckResponse.weekly_check_id == wc.id,
                WeeklyCheckResponse.submit_date >= week_start_dt,
                WeeklyCheckResponse.submit_date <= week_end_dt
            ).all()

            for resp in responses:
                responses_list.append({
                    'type': 'weekly_check',
                    'id': resp.id,
                    'cliente_id': cliente.cliente_id,
                    'cliente_nome': cliente.nome_cognome,
                    'submit_date': resp.submit_date.strftime('%d/%m/%Y %H:%M') if resp.submit_date else None,
                    'nutritionist_rating': resp.nutritionist_rating,
                    'coach_rating': resp.coach_rating,
                    'psychologist_rating': resp.psychologist_rating,
                    'coordinator_rating': resp.coordinator_rating,
                    'progress_rating': resp.progress_rating,
                })

    # Ordina per data discendente
    responses_list.sort(key=lambda x: x['submit_date'] or '', reverse=True)

    return jsonify({
        'success': True,
        'week_start': week_start.strftime('%d/%m/%Y'),
        'week_end': week_end.strftime('%d/%m/%Y'),
        'total': len(responses_list),
        'responses': responses_list
    })


# ============================================================================
# API CALCOLO TRIMESTRALE CON SUPER MALUS
# ============================================================================

@bp.route('/api/calcola-trimestrale', methods=['POST'])
@csrf.exempt
@login_required
@admin_required
def api_calcola_trimestrale():
    """
    API: Calcola KPI composito trimestrale con Super Malus per tutti i professionisti.

    POST body:
        - quarter: trimestre (es. "2025-Q4", opzionale, default: trimestre corrente)

    Returns:
        JSON con statistiche calcolo e risultati per professionista
    """
    from .services import SuperMalusService

    data = request.get_json() or {}
    quarter = data.get('quarter') or ReviewService.get_quarter_string()

    import time
    start_time = time.time()

    try:
        result = QualityScoreCalculator.calculate_quarterly_scores(
            quarter=quarter,
            calculated_by_user_id=current_user.id
        )

        elapsed = time.time() - start_time
        result['elapsed_seconds'] = round(elapsed, 1)
        result['success'] = True

        return jsonify(result)

    except Exception as e:
        db.session.rollback()
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@bp.route('/api/quarterly-summary')
@login_required
@admin_required
def api_quarterly_summary():
    """
    API: Riassunto trimestrale con KPI compositi e Super Malus.

    Query params:
        - quarter: trimestre (es. "2025-Q4", opzionale)

    Returns:
        JSON con statistiche aggregate e lista professionisti con Super Malus
    """
    quarter = request.args.get('quarter') or ReviewService.get_quarter_string()

    # Trova tutti gli score del trimestre (ultima settimana per professionista)
    subquery = db.session.query(
        QualityWeeklyScore.professionista_id,
        func.max(QualityWeeklyScore.week_start_date).label('max_week')
    ).filter(
        QualityWeeklyScore.quarter == quarter
    ).group_by(QualityWeeklyScore.professionista_id).subquery()

    scores = db.session.query(QualityWeeklyScore).join(
        subquery,
        (QualityWeeklyScore.professionista_id == subquery.c.professionista_id) &
        (QualityWeeklyScore.week_start_date == subquery.c.max_week)
    ).all()

    # Statistiche aggregate
    total_profs = len(scores)
    with_malus = [s for s in scores if s.super_malus_applied]
    total_bonus_before = sum(s.final_bonus_percentage or 0 for s in scores)
    total_bonus_after = sum(s.final_bonus_after_malus or 0 for s in scores)

    # Lista professionisti con Super Malus
    malus_details = []
    for s in with_malus:
        prof = db.session.get(User, s.professionista_id)
        malus_details.append({
            'professionista_id': s.professionista_id,
            'professionista_name': f"{prof.first_name} {prof.last_name}" if prof else 'N/A',
            'specialty': prof.specialty.value if prof and prof.specialty else 'N/A',
            'quality_trim': s.quality_trim,
            'rinnovo_adj_percentage': s.rinnovo_adj_percentage,
            'final_bonus_percentage': s.final_bonus_percentage,
            'super_malus_percentage': s.super_malus_percentage,
            'final_bonus_after_malus': s.final_bonus_after_malus,
            'is_primary_for_malus': s.is_primary_for_malus,
            'has_negative_review': s.has_negative_review,
            'has_refund': s.has_refund,
            'super_malus_reason': s.super_malus_reason,
        })

    return jsonify({
        'success': True,
        'quarter': quarter,
        'total_professionisti': total_profs,
        'professionisti_con_malus': len(with_malus),
        'total_bonus_before_malus': round(total_bonus_before, 2),
        'total_bonus_after_malus': round(total_bonus_after, 2),
        'bonus_reduction_total': round(total_bonus_before - total_bonus_after, 2),
        'malus_details': malus_details
    })


@bp.route('/api/professionista/<int:user_id>/kpi-breakdown')
@login_required
@admin_required
def api_professionista_kpi_breakdown(user_id):
    """
    API: Dettaglio KPI composito per professionista nel trimestre.

    Path params:
        - user_id: ID professionista

    Query params:
        - quarter: trimestre (es. "2025-Q4", opzionale)

    Returns:
        JSON con breakdown KPI1, KPI2, bonus pesato e Super Malus
    """
    quarter = request.args.get('quarter') or ReviewService.get_quarter_string()

    professionista = db.session.get(User, user_id)
    if not professionista:
        return jsonify({'success': False, 'error': 'Professionista non trovato'}), 404

    # Trova ultimo score del trimestre
    score = db.session.query(QualityWeeklyScore).filter(
        QualityWeeklyScore.professionista_id == user_id,
        QualityWeeklyScore.quarter == quarter
    ).order_by(desc(QualityWeeklyScore.week_start_date)).first()

    if not score:
        return jsonify({
            'success': True,
            'professionista_id': user_id,
            'professionista_name': f"{professionista.first_name} {professionista.last_name}",
            'quarter': quarter,
            'message': 'Nessun dato disponibile per questo trimestre'
        })

    return jsonify({
        'success': True,
        'professionista_id': user_id,
        'professionista_name': f"{professionista.first_name} {professionista.last_name}",
        'quarter': quarter,
        'week_start_date': score.week_start_date.strftime('%Y-%m-%d'),

        # KPI Quality (40%)
        'kpi_quality': {
            'value': score.quality_trim,
            'bonus_band': score.quality_bonus_band or score.bonus_band,
            'weight': 40
        },

        # KPI Rinnovo Adj (60%)
        'kpi_rinnovo_adj': {
            'value': score.rinnovo_adj_percentage,
            'bonus_band': score.rinnovo_adj_bonus_band,
            'weight': 60
        },

        # Bonus composito
        'final_bonus_percentage': score.final_bonus_percentage,

        # Super Malus
        'super_malus': {
            'applied': score.super_malus_applied,
            'percentage': score.super_malus_percentage,
            'is_primary': score.is_primary_for_malus,
            'has_negative_review': score.has_negative_review,
            'has_refund': score.has_refund,
            'reason': score.super_malus_reason,
        },

        # Bonus finale (dopo malus)
        'final_bonus_after_malus': score.final_bonus_after_malus
    })
