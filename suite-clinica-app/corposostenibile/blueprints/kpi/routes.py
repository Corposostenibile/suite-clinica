"""
KPI Routes - API e pagine per il sistema KPI
=============================================
"""

from datetime import date, datetime, timedelta
from flask import render_template, request, jsonify
from flask_login import login_required, current_user

from . import kpi_bp
from .services import KPIService, ARRService, KPIDashboardService


def admin_required(f):
    """Decorator per richiedere accesso admin."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({'success': False, 'message': 'Accesso non autorizzato'}), 403
        return f(*args, **kwargs)
    return decorated_function


# ==================== PAGINE ====================

@kpi_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Dashboard KPI principale."""
    # Default: ultimo mese
    oggi = date.today()
    primo_mese = oggi.replace(day=1)
    ultimo_mese_prec = primo_mese - timedelta(days=1)
    inizio_mese_prec = ultimo_mese_prec.replace(day=1)

    return render_template(
        'kpi/dashboard.html',
        periodo_default={
            'inizio': inizio_mese_prec.isoformat(),
            'fine': ultimo_mese_prec.isoformat()
        },
        oggi=oggi.isoformat()
    )


# ==================== API KPI AZIENDALI ====================

@kpi_bp.route('/api/calcola', methods=['POST'])
@login_required
@admin_required
def api_calcola_kpi():
    """
    Calcola i KPI per il periodo specificato.

    Body JSON:
    {
        "periodo_inizio": "2025-01-01",
        "periodo_fine": "2025-01-31",
        "save_snapshot": true
    }
    """
    try:
        data = request.get_json()
        periodo_inizio = datetime.strptime(data['periodo_inizio'], '%Y-%m-%d').date()
        periodo_fine = datetime.strptime(data['periodo_fine'], '%Y-%m-%d').date()
        save_snapshot = data.get('save_snapshot', False)

        # Calcola KPI
        dashboard_data = KPIDashboardService.get_dashboard_data(periodo_inizio, periodo_fine)

        # Salva snapshot se richiesto
        if save_snapshot:
            KPIService.calcola_tasso_rinnovi(
                periodo_inizio, periodo_fine,
                save_snapshot=True,
                user_id=current_user.id
            )
            KPIService.calcola_tasso_referral(
                periodo_inizio, periodo_fine,
                save_snapshot=True,
                user_id=current_user.id
            )
            ARRService.calcola_arr_tutti_professionisti(
                periodo_inizio, periodo_fine,
                save_snapshot=True
            )

        return jsonify({
            'success': True,
            'data': dashboard_data
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


@kpi_bp.route('/api/tasso-rinnovi')
@login_required
@admin_required
def api_tasso_rinnovi():
    """
    API per ottenere il tasso rinnovi.

    Query params:
    - periodo_inizio: YYYY-MM-DD
    - periodo_fine: YYYY-MM-DD
    """
    try:
        periodo_inizio = datetime.strptime(
            request.args.get('periodo_inizio'),
            '%Y-%m-%d'
        ).date()
        periodo_fine = datetime.strptime(
            request.args.get('periodo_fine'),
            '%Y-%m-%d'
        ).date()

        result = KPIService.calcola_tasso_rinnovi(
            periodo_inizio, periodo_fine, save_snapshot=False
        )

        return jsonify({
            'success': True,
            'data': result
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


@kpi_bp.route('/api/tasso-referral')
@login_required
@admin_required
def api_tasso_referral():
    """
    API per ottenere il tasso referral.

    Query params:
    - periodo_inizio: YYYY-MM-DD
    - periodo_fine: YYYY-MM-DD
    """
    try:
        periodo_inizio = datetime.strptime(
            request.args.get('periodo_inizio'),
            '%Y-%m-%d'
        ).date()
        periodo_fine = datetime.strptime(
            request.args.get('periodo_fine'),
            '%Y-%m-%d'
        ).date()

        result = KPIService.calcola_tasso_referral(
            periodo_inizio, periodo_fine, save_snapshot=False
        )

        return jsonify({
            'success': True,
            'data': result
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


# ==================== API ARR ====================

@kpi_bp.route('/api/arr/professionisti')
@login_required
@admin_required
def api_arr_professionisti():
    """
    API per ottenere l'ARR di tutti i professionisti.

    Query params:
    - periodo_inizio: YYYY-MM-DD
    - periodo_fine: YYYY-MM-DD
    """
    try:
        periodo_inizio = datetime.strptime(
            request.args.get('periodo_inizio'),
            '%Y-%m-%d'
        ).date()
        periodo_fine = datetime.strptime(
            request.args.get('periodo_fine'),
            '%Y-%m-%d'
        ).date()

        risultati = ARRService.calcola_arr_tutti_professionisti(
            periodo_inizio, periodo_fine, save_snapshot=False
        )

        return jsonify({
            'success': True,
            'data': risultati
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


@kpi_bp.route('/api/arr/professionista/<int:user_id>')
@login_required
@admin_required
def api_arr_singolo_professionista(user_id: int):
    """
    API per ottenere l'ARR di un singolo professionista.

    Query params:
    - periodo_inizio: YYYY-MM-DD
    - periodo_fine: YYYY-MM-DD
    """
    try:
        periodo_inizio = datetime.strptime(
            request.args.get('periodo_inizio'),
            '%Y-%m-%d'
        ).date()
        periodo_fine = datetime.strptime(
            request.args.get('periodo_fine'),
            '%Y-%m-%d'
        ).date()

        result = ARRService.calcola_arr_professionista(
            user_id, periodo_inizio, periodo_fine, save_snapshot=False
        )

        return jsonify({
            'success': True,
            'data': result
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


# ==================== API STORICO ====================

@kpi_bp.route('/api/storico/kpi/<kpi_type>')
@login_required
@admin_required
def api_storico_kpi(kpi_type: str):
    """
    API per ottenere lo storico di un KPI.

    Path params:
    - kpi_type: tasso_rinnovi | tasso_referral

    Query params:
    - limit: numero massimo di record (default 12)
    """
    try:
        limit = int(request.args.get('limit', 12))
        storico = KPIDashboardService.get_storico_kpi(kpi_type, limit)

        return jsonify({
            'success': True,
            'data': storico
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


@kpi_bp.route('/api/storico/arr/<int:user_id>')
@login_required
@admin_required
def api_storico_arr_professionista(user_id: int):
    """
    API per ottenere lo storico ARR di un professionista.

    Path params:
    - user_id: ID del professionista

    Query params:
    - limit: numero massimo di record (default 12)
    """
    try:
        limit = int(request.args.get('limit', 12))
        storico = KPIDashboardService.get_storico_arr_professionista(user_id, limit)

        return jsonify({
            'success': True,
            'data': storico
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400


# ==================== API SALVA SNAPSHOT ====================

@kpi_bp.route('/api/snapshot/salva', methods=['POST'])
@login_required
@admin_required
def api_salva_snapshot():
    """
    Salva gli snapshot KPI e ARR per il periodo specificato.

    Body JSON:
    {
        "periodo_inizio": "2025-01-01",
        "periodo_fine": "2025-01-31"
    }
    """
    try:
        data = request.get_json()
        periodo_inizio = datetime.strptime(data['periodo_inizio'], '%Y-%m-%d').date()
        periodo_fine = datetime.strptime(data['periodo_fine'], '%Y-%m-%d').date()

        # Salva KPI aziendali
        tasso_rinnovi = KPIService.calcola_tasso_rinnovi(
            periodo_inizio, periodo_fine,
            save_snapshot=True,
            user_id=current_user.id
        )
        tasso_referral = KPIService.calcola_tasso_referral(
            periodo_inizio, periodo_fine,
            save_snapshot=True,
            user_id=current_user.id
        )

        # Salva ARR professionisti
        arr_results = ARRService.calcola_arr_tutti_professionisti(
            periodo_inizio, periodo_fine,
            save_snapshot=True
        )

        return jsonify({
            'success': True,
            'message': 'Snapshot salvati con successo',
            'data': {
                'tasso_rinnovi': tasso_rinnovi,
                'tasso_referral': tasso_referral,
                'arr_professionisti_count': len(arr_results)
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
