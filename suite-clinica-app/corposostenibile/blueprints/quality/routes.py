"""
Quality Score Routes
Routes per gestione Quality Score (ADMIN ONLY).
"""
from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import date, datetime, timedelta
from sqlalchemy import desc, func
from corposostenibile.extensions import db
from corposostenibile.models import (
    User,
    Cliente,
    QualityWeeklyScore,
    QualityClientScore,
    TrustpilotReview,
    EleggibilitaSettimanale,
)
from corposostenibile.services.quality import (
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
            flash('Accesso negato. Solo amministratori.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# DASHBOARD PRINCIPALE
# ============================================================================

@bp.route('/')
@login_required
@admin_required
def dashboard():
    """Dashboard principale Quality Score."""
    # Settimana da parametro query string o corrente
    week_param = request.args.get('week')
    if week_param:
        try:
            target_date = datetime.strptime(week_param, '%Y-%m-%d').date()
        except:
            target_date = date.today()
    else:
        target_date = date.today()

    week_start, week_end = EligibilityService.get_week_bounds(target_date)

    # Statistiche generali settimana corrente
    weekly_scores = db.session.query(QualityWeeklyScore).filter_by(
        week_start_date=week_start
    ).all()

    # Top professionisti settimana
    top_week = db.session.query(QualityWeeklyScore).filter(
        QualityWeeklyScore.week_start_date == week_start,
        QualityWeeklyScore.quality_final.isnot(None)
    ).order_by(desc(QualityWeeklyScore.quality_final)).limit(10).all()

    # Top professionisti trimestre
    top_quarter = db.session.query(QualityWeeklyScore).filter(
        QualityWeeklyScore.week_start_date == week_start,
        QualityWeeklyScore.quality_trim.isnot(None)
    ).order_by(desc(QualityWeeklyScore.quality_trim)).limit(10).all()

    # Statistiche aggregate
    stats = {
        'total_professionisti': len(weekly_scores),
        'avg_quality_week': round(sum(s.quality_final for s in weekly_scores if s.quality_final) / len(weekly_scores), 2) if weekly_scores else 0,
        'total_clients_eligible': sum(s.n_clients_eligible for s in weekly_scores),
        'total_checks_done': sum(s.n_checks_done for s in weekly_scores),
        'avg_miss_rate': round(sum(s.miss_rate for s in weekly_scores) / len(weekly_scores), 4) if weekly_scores else 0,
    }

    return render_template(
        'quality/dashboard.html',
        week_start=week_start,
        week_end=week_end,
        stats=stats,
        top_week=top_week,
        top_quarter=top_quarter,
        timedelta=timedelta,
    )


# ============================================================================
# DETTAGLIO PROFESSIONISTA
# ============================================================================

@bp.route('/professionista/<int:user_id>')
@login_required
@admin_required
def professionista_detail(user_id):
    """Dettaglio Quality Score di un professionista."""
    professionista = db.session.get(User, user_id)
    if not professionista:
        flash('Professionista non trovato', 'error')
        return redirect(url_for('quality.dashboard'))

    # Ultime 12 settimane
    scores = db.session.query(QualityWeeklyScore).filter_by(
        professionista_id=user_id
    ).order_by(desc(QualityWeeklyScore.week_start_date)).limit(12).all()

    # Settimana da parametro query string o corrente
    week_param = request.args.get('week')
    if week_param:
        try:
            target_date = datetime.strptime(week_param, '%Y-%m-%d').date()
        except:
            target_date = date.today()
    else:
        target_date = date.today()

    week_start, week_end = EligibilityService.get_week_bounds(target_date)
    current_week_score = db.session.query(QualityWeeklyScore).filter_by(
        professionista_id=user_id,
        week_start_date=week_start
    ).first()

    # Clienti eleggibili settimana corrente
    eligible_clients = db.session.query(EleggibilitaSettimanale).filter_by(
        professionista_id=user_id,
        week_start_date=week_start,
        eleggibile=True
    ).all()

    # Score clienti settimana corrente
    client_scores = db.session.query(QualityClientScore).filter_by(
        professionista_id=user_id,
        week_start_date=week_start
    ).all()

    # Recensioni trimestre corrente
    quarter_string = ReviewService.get_quarter_string()
    reviews = ReviewService.get_reviews_for_quarter(quarter_string, user_id)

    return render_template(
        'quality/professionista_detail.html',
        professionista=professionista,
        scores=scores,
        current_week_score=current_week_score,
        eligible_clients=eligible_clients,
        client_scores=client_scores,
        reviews=reviews,
        week_start=week_start,
        week_end=week_end,
        timedelta=timedelta,
    )


# ============================================================================
# CALCOLO MANUALE
# ============================================================================

@bp.route('/calcola', methods=['GET', 'POST'])
@login_required
@admin_required
def calcola():
    """Form per calcolo manuale Quality Score - OTTIMIZZATO."""
    if request.method == 'POST':
        # Leggi parametri
        week_start_str = request.form.get('week_start')
        professionista_id = request.form.get('professionista_id')

        # Parse data
        try:
            week_start = datetime.strptime(week_start_str, '%Y-%m-%d').date()
        except:
            flash('Data non valida', 'error')
            return redirect(url_for('quality.calcola'))

        # Converti professionista_id
        prof_id = int(professionista_id) if professionista_id and professionista_id != 'all' else None

        # OTTIMIZZAZIONE: Calcolo con timeout esteso (300s = 5 min)
        # Su produzione con 2361 clienti e 70 prof, il calcolo ottimizzato dovrebbe
        # completarsi in 30-60 secondi grazie a bulk operations
        import time
        start_time = time.time()

        try:
            # Esegui calcolo (ora ottimizzato)
            result = QualityScoreCalculator.calculate_full_week(
                week_start=week_start,
                professionista_id=prof_id,
                calculated_by_user_id=current_user.id
            )

            elapsed = time.time() - start_time

            flash(
                f"✅ Calcolo completato in {elapsed:.1f}s! "
                f"Processati {result['eligibility']['total_processed']} clienti, "
                f"{len(result['weekly_scores'])} professionisti.",
                'success'
            )

            return redirect(url_for('quality.dashboard', week=week_start.strftime('%Y-%m-%d')))

        except Exception as e:
            elapsed = time.time() - start_time
            import traceback
            error_detail = traceback.format_exc()

            flash(
                f'❌ Errore dopo {elapsed:.1f}s: {str(e)}',
                'error'
            )

            # Log dettagliato per debug
            print(f"[QUALITY CALC ERROR] {error_detail}")

            return redirect(url_for('quality.calcola'))

    # GET - mostra form
    # OTTIMIZZAZIONE: Query solo campi necessari
    professionisti = db.session.query(
        User.id, User.first_name, User.last_name, User.department_id
    ).filter(
        User.is_active == True,
        User.department_id.in_([1, 2, 3])  # Nutrizionisti, Coach, Psicologi
    ).order_by(User.last_name).all()

    # Settimana corrente di default
    week_start, _ = EligibilityService.get_week_bounds()

    return render_template(
        'quality/calcola.html',
        professionisti=professionisti,
        week_start=week_start
    )


# ============================================================================
# ELEGGIBILITÀ
# ============================================================================

@bp.route('/eleggibilita/<week_start>')
@login_required
@admin_required
def eleggibilita_week(week_start):
    """Visualizza eleggibilità clienti per una settimana."""
    try:
        week_date = datetime.strptime(week_start, '%Y-%m-%d').date()
    except:
        flash('Data non valida', 'error')
        return redirect(url_for('quality.dashboard'))

    week_start, week_end = EligibilityService.get_week_bounds(week_date)

    # Tutti i record eleggibilità
    eleggibilita = db.session.query(EleggibilitaSettimanale).filter_by(
        week_start_date=week_start
    ).order_by(
        EleggibilitaSettimanale.professionista_id,
        EleggibilitaSettimanale.eleggibile.desc()
    ).all()

    # Group by professionista
    by_prof = {}
    for e in eleggibilita:
        if e.professionista_id not in by_prof:
            by_prof[e.professionista_id] = {
                'professionista': db.session.get(User, e.professionista_id),
                'eligible': [],
                'not_eligible': []
            }

        if e.eleggibile:
            by_prof[e.professionista_id]['eligible'].append(e)
        else:
            by_prof[e.professionista_id]['not_eligible'].append(e)

    return render_template(
        'quality/eleggibilita.html',
        week_start=week_start,
        week_end=week_end,
        by_prof=by_prof,
        timedelta=timedelta
    )


# ============================================================================
# RECENSIONI
# ============================================================================

@bp.route('/recensioni')
@login_required
@admin_required
def recensioni():
    """Lista recensioni Trustpilot."""
    quarter = request.args.get('quarter', ReviewService.get_quarter_string())

    reviews = db.session.query(TrustpilotReview).filter_by(
        applied_to_quarter=quarter
    ).order_by(desc(TrustpilotReview.data_pubblicazione)).all()

    return render_template(
        'quality/recensioni.html',
        reviews=reviews,
        quarter=quarter
    )


@bp.route('/recensioni/conferma/<int:review_id>', methods=['POST'])
@login_required
@admin_required
def conferma_recensione(review_id):
    """Conferma pubblicazione recensione."""
    review = db.session.get(TrustpilotReview, review_id)
    if not review:
        return jsonify({'error': 'Recensione non trovata'}), 404

    # Leggi dati
    stelle = int(request.form.get('stelle'))
    testo = request.form.get('testo')
    data_pubblicazione_str = request.form.get('data_pubblicazione')
    week_start_str = request.form.get('week_start')

    try:
        data_pub = datetime.strptime(data_pubblicazione_str, '%Y-%m-%d')
        week_start = datetime.strptime(week_start_str, '%Y-%m-%d').date()

        # Conferma
        ReviewService.confirm_review_published(
            review_id=review_id,
            stelle=stelle,
            testo_recensione=testo,
            data_pubblicazione=data_pub,
            applied_to_week_start=week_start,
            confermata_da_hm_id=current_user.id
        )

        flash('Recensione confermata con successo!', 'success')
        return redirect(url_for('quality.recensioni'))

    except Exception as e:
        flash(f'Errore: {str(e)}', 'error')
        return redirect(url_for('quality.recensioni'))


# ============================================================================
# API JSON (per grafici/datatables)
# ============================================================================

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
        'miss_rate': [s.miss_rate * 100 for s in scores],  # Percentuale
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
        if s.bonus_band:
            bands_count[s.bonus_band.value] += 1

    data = {
        'total_professionisti': len(weekly_scores),
        'bands_distribution': bands_count,
        'avg_quality': round(sum(s.quality_final for s in weekly_scores if s.quality_final) / len(weekly_scores), 2) if weekly_scores else 0,
    }

    return jsonify(data)


# ============================================================================
# DASHBOARD DIPARTIMENTALI
# ============================================================================

DEPT_CONFIG = {
    'nutrizione': {'id': 2, 'name': 'Nutrizione', 'icon': 'fa-apple-alt'},
    'coach': {'id': 3, 'name': 'Coach', 'icon': 'fa-dumbbell'},
    'psicologia': {'id': 4, 'name': 'Psicologia', 'icon': 'fa-brain'},
}


def get_week_navigation(week_start):
    """Calcola settimane precedente e successiva."""
    prev_week = week_start - timedelta(days=7)
    next_week = week_start + timedelta(days=7)
    # Non permettere navigazione nel futuro oltre la settimana corrente
    current_week_start, _ = EligibilityService.get_week_bounds()
    if next_week > current_week_start:
        next_week = None
    return prev_week, next_week


def get_month_weeks(year, month):
    """Restituisce tutte le settimane (lunedì) di un mese."""
    from calendar import monthrange
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])

    weeks = []
    # Trova il primo lunedì
    current = first_day
    while current.weekday() != 0:  # 0 = Monday
        current += timedelta(days=1)

    while current <= last_day:
        weeks.append(current)
        current += timedelta(days=7)

    return weeks


def get_quarter_weeks(year, quarter):
    """Restituisce tutte le settimane di un trimestre."""
    start_month = (quarter - 1) * 3 + 1
    end_month = start_month + 2

    weeks = []
    for month in range(start_month, end_month + 1):
        weeks.extend(get_month_weeks(year, month))

    return weeks


@bp.route('/nutrizione')
@login_required
@admin_required
def dashboard_nutrizione():
    """Dashboard Quality Score - Dipartimento Nutrizione."""
    return _render_department_dashboard('nutrizione')


@bp.route('/coach')
@login_required
@admin_required
def dashboard_coach():
    """Dashboard Quality Score - Dipartimento Coach."""
    return _render_department_dashboard('coach')


@bp.route('/psicologia')
@login_required
@admin_required
def dashboard_psicologia():
    """Dashboard Quality Score - Dipartimento Psicologia."""
    return _render_department_dashboard('psicologia')


def _render_department_dashboard(dept_key):
    """Render dashboard per un dipartimento specifico."""
    config = DEPT_CONFIG[dept_key]
    dept_id = config['id']

    # Parametri da query string
    week_param = request.args.get('week')
    view_mode = request.args.get('view', 'week')  # week, month, quarter
    year_param = request.args.get('year', str(date.today().year))
    month_param = request.args.get('month')
    quarter_param = request.args.get('quarter')

    # Determina settimana target
    if week_param:
        try:
            target_date = datetime.strptime(week_param, '%Y-%m-%d').date()
        except:
            target_date = date.today()
    else:
        target_date = date.today()

    week_start, week_end = EligibilityService.get_week_bounds(target_date)
    prev_week, next_week = get_week_navigation(week_start)

    # Anno corrente per selettori
    current_year = int(year_param)

    # Professionisti del dipartimento
    professionisti = db.session.query(User).filter(
        User.is_active == True,
        User.department_id == dept_id
    ).order_by(User.last_name).all()

    # Score settimanali per la settimana selezionata
    weekly_scores = {}
    for prof in professionisti:
        score = db.session.query(QualityWeeklyScore).filter_by(
            professionista_id=prof.id,
            week_start_date=week_start
        ).first()
        weekly_scores[prof.id] = score

    # Calcola aggregati per mese/trimestre se richiesto
    period_data = None
    if view_mode == 'month' and month_param:
        month = int(month_param)
        weeks = get_month_weeks(current_year, month)
        period_data = _aggregate_period_scores(professionisti, weeks)
    elif view_mode == 'quarter' and quarter_param:
        quarter = int(quarter_param)
        weeks = get_quarter_weeks(current_year, quarter)
        period_data = _aggregate_period_scores(professionisti, weeks)

    # Statistiche aggregate settimana
    valid_scores = [s for s in weekly_scores.values() if s and s.quality_final]
    stats = {
        'total_professionisti': len(professionisti),
        'with_score': len(valid_scores),
        'avg_quality': round(sum(s.quality_final for s in valid_scores) / len(valid_scores), 2) if valid_scores else None,
        'total_eligible': sum(s.n_clients_eligible for s in valid_scores) if valid_scores else 0,
        'total_checks': sum(s.n_checks_done for s in valid_scores) if valid_scores else 0,
        'avg_miss_rate': round(sum(s.miss_rate for s in valid_scores) / len(valid_scores) * 100, 1) if valid_scores else None,
    }

    return render_template(
        f'quality/dashboard_{dept_key}.html',
        dept_key=dept_key,
        dept_config=config,
        professionisti=professionisti,
        weekly_scores=weekly_scores,
        week_start=week_start,
        week_end=week_end,
        prev_week=prev_week,
        next_week=next_week,
        stats=stats,
        view_mode=view_mode,
        current_year=current_year,
        current_month=int(month_param) if month_param else date.today().month,
        current_quarter=int(quarter_param) if quarter_param else (date.today().month - 1) // 3 + 1,
        period_data=period_data,
        timedelta=timedelta,
    )


def _aggregate_period_scores(professionisti, weeks):
    """Aggrega score per un periodo (mese/trimestre)."""
    period_data = {}

    for prof in professionisti:
        scores = db.session.query(QualityWeeklyScore).filter(
            QualityWeeklyScore.professionista_id == prof.id,
            QualityWeeklyScore.week_start_date.in_(weeks)
        ).all()

        if scores:
            valid = [s for s in scores if s.quality_final]
            period_data[prof.id] = {
                'weeks_count': len(valid),
                'avg_quality': round(sum(s.quality_final for s in valid) / len(valid), 2) if valid else None,
                'total_eligible': sum(s.n_clients_eligible for s in valid),
                'total_checks': sum(s.n_checks_done for s in valid),
                'avg_miss_rate': round(sum(s.miss_rate for s in valid) / len(valid) * 100, 1) if valid else None,
            }
        else:
            period_data[prof.id] = None

    return period_data


# ============================================================================
# API CALCOLO DIPARTIMENTALE
# ============================================================================

@bp.route('/api/calcola/<dept_key>', methods=['POST'])
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
        # (calculate_eligibility_for_week fa già commit interno)
        for prof in professionisti:
            EligibilityService.calculate_eligibility_for_week(
                week_start=week_start,
                professionista_id=prof.id
            )

        # 2. Processa check responses per collegare i voti ai clienti eleggibili
        # IMPORTANTE: questo deve avvenire DOPO l'eleggibilità e PRIMA del calcolo score
        check_stats = QualityScoreCalculator.process_check_responses_for_week(
            week_start=week_start
        )
        # Commit per persistere i check_effettuato prima di calculate_weekly_score
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

        # Commit finale per i weekly scores
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
    from corposostenibile.models import WeeklyCheck, WeeklyCheckResponse, DCACheck, DCACheckResponse

    week_start_str = request.args.get('week')
    dept = request.args.get('dept', 'nutrizione')

    try:
        week_start = datetime.strptime(week_start_str, '%Y-%m-%d').date()
    except:
        week_start, _ = EligibilityService.get_week_bounds()

    week_start, week_end = EligibilityService.get_week_bounds(week_start)
    week_end_dt = datetime.combine(week_end, datetime.max.time())
    week_start_dt = datetime.combine(week_start, datetime.min.time())

    # Recupera eleggibilità con check effettuato
    eligibilities = db.session.query(EleggibilitaSettimanale).filter_by(
        professionista_id=prof_id,
        week_start_date=week_start,
        eleggibile=True,
        check_effettuato=True
    ).all()

    # Costruisci lista risposte
    responses_list = []
    for elig in eligibilities:
        cliente = elig.cliente
        if not cliente:
            continue

        # Cerca WeeklyCheckResponse nella settimana
        for wc in cliente.weekly_checks.all():
            for resp in wc.responses.filter(
                WeeklyCheckResponse.submit_date >= week_start_dt,
                WeeklyCheckResponse.submit_date <= week_end_dt
            ).all():
                responses_list.append({
                    'type': 'weekly',
                    'id': resp.id,
                    'cliente_id': cliente.cliente_id,
                    'cliente_nome': cliente.nome_cognome,
                    'submit_date': resp.submit_date.strftime('%d/%m/%Y %H:%M') if resp.submit_date else None,
                    'weight': resp.weight,
                    'digestion': resp.digestion_rating,
                    'energy': resp.energy_rating,
                    'strength': resp.strength_rating,
                    'hunger': resp.hunger_rating,
                    'sleep': resp.sleep_rating,
                    'mood': resp.mood_rating,
                    'motivation': resp.motivation_rating,
                    'what_worked': resp.what_worked,
                    'what_didnt_work': resp.what_didnt_work,
                    'what_learned': resp.what_learned,
                    'what_focus_next': resp.what_focus_next,
                    'nutrition_adherence': resp.nutrition_program_adherence,
                    'training_adherence': resp.training_program_adherence,
                    'exercise_modifications': resp.exercise_modifications,
                    'daily_steps': resp.daily_steps,
                    'injuries_notes': resp.injuries_notes,
                    'extra_comments': resp.extra_comments,
                    'nutritionist_rating': resp.nutritionist_rating,
                    'psychologist_rating': resp.psychologist_rating,
                    'coach_rating': resp.coach_rating,
                    'progress_rating': resp.progress_rating,
                    'photo_front': resp.photo_front,
                    'photo_side': resp.photo_side,
                    'photo_back': resp.photo_back,
                })

        # Cerca DCACheckResponse nella settimana
        if hasattr(cliente, 'dca_checks'):
            for dca in cliente.dca_checks.all():
                for resp in dca.responses.filter(
                    DCACheckResponse.submit_date >= week_start_dt,
                    DCACheckResponse.submit_date <= week_end_dt
                ).all():
                    responses_list.append({
                        'type': 'dca',
                        'id': resp.id,
                        'cliente_id': cliente.cliente_id,
                        'cliente_nome': cliente.nome_cognome,
                        'submit_date': resp.submit_date.strftime('%d/%m/%Y %H:%M') if resp.submit_date else None,
                        'mood_balance': resp.mood_balance_rating,
                        'food_plan_serenity': resp.food_plan_serenity,
                        'food_weight_worry': resp.food_weight_worry,
                        'emotional_eating': resp.emotional_eating,
                        'body_comfort': resp.body_comfort,
                        'body_respect': resp.body_respect,
                        'exercise_wellness': resp.exercise_wellness,
                        'exercise_guilt': resp.exercise_guilt,
                        'sleep_satisfaction': resp.sleep_satisfaction,
                        'relationship_time': resp.relationship_time,
                        'personal_time': resp.personal_time,
                        'life_interference': resp.life_interference,
                        'unexpected_management': resp.unexpected_management,
                        'self_compassion': resp.self_compassion,
                        'inner_dialogue': resp.inner_dialogue,
                        'long_term_sustainability': resp.long_term_sustainability,
                        'values_alignment': resp.values_alignment,
                        'motivation_level': resp.motivation_level,
                        'meal_organization': resp.meal_organization,
                        'meal_stress': resp.meal_stress,
                        'shopping_awareness': resp.shopping_awareness,
                        'shopping_impact': resp.shopping_impact,
                        'meal_clarity': resp.meal_clarity,
                        'digestion': resp.digestion,
                        'energy': resp.energy,
                        'strength': resp.strength,
                        'hunger': resp.hunger,
                        'sleep': resp.sleep,
                        'mood': resp.mood,
                        'motivation': resp.motivation,
                        'referral': resp.referral,
                        'extra_comments': resp.extra_comments,
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
