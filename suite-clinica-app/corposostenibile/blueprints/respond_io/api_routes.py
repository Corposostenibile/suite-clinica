"""
API routes per integrazione respond.io
"""

from flask import jsonify, request
from flask_login import login_required
from datetime import datetime, timedelta
from . import bp
from .client import RespondIOClient
from .services import FunnelAnalyticsService
from corposostenibile.models import RespondIOLifecycleChange




@bp.route('/api/send-message', methods=['POST'])
@login_required
def api_send_message():
    """Invia un messaggio tramite Respond.io"""
    
    data = request.get_json()
    contact_id = data.get('contact_id')
    message = data.get('message')
    
    if not contact_id or not message:
        return jsonify({'error': 'contact_id e message sono richiesti'}), 400
    
    try:
        from flask import current_app
        client = current_app.respond_io_client
        
        result = client.send_message(contact_id, message)
        
        return jsonify({
            'success': True,
            'message_id': result.get('id')
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/update-lifecycle', methods=['PUT'])
@login_required 
def api_update_lifecycle():
    """Aggiorna il lifecycle di un contatto"""
    
    data = request.get_json()
    contact_id = data.get('contact_id')
    new_lifecycle = data.get('lifecycle')
    
    if not contact_id or not new_lifecycle:
        return jsonify({'error': 'contact_id e lifecycle sono richiesti'}), 400
    
    try:
        from flask import current_app
        client = current_app.respond_io_client
        
        result = client.update_contact_lifecycle(contact_id, new_lifecycle)
        
        return jsonify({
            'success': True,
            'contact_id': contact_id,
            'new_lifecycle': new_lifecycle
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/funnel-summary', methods=['GET'])
@login_required
def api_funnel_summary():
    """
    Ottiene un riepilogo rapido del funnel per widget/dashboard
    """
    
    # Default: ultimi 7 giorni
    from datetime import date
    
    days = request.args.get('days', 7, type=int)
    channel = request.args.get('channel')
    
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    metrics = FunnelAnalyticsService.calculate_funnel_metrics(
        start_date, end_date, channel
    )
    
    # Prepara summary compatto
    summary = {
        'period_days': days,
        'total_new_leads': metrics['totals']['new_leads'],
        'total_converted': metrics['totals']['conversions'].get('link_inviato_to_prenotato', 0),
        'conversion_rate': 0,
        'top_channel': None,
        'channels_summary': []
    }
    
    # Calcola conversion rate totale
    if summary['total_new_leads'] > 0:
        summary['conversion_rate'] = round(
            (summary['total_converted'] / summary['total_new_leads']) * 100, 1
        )
    
    # Trova canale migliore
    best_channel = None
    best_conversions = 0
    
    for channel_name, channel_data in metrics['channels'].items():
        conversions = channel_data['conversions'].get('link_inviato_to_prenotato', 0)
        
        summary['channels_summary'].append({
            'name': channel_name,
            'new_leads': channel_data['new_leads'],
            'conversions': conversions
        })
        
        if conversions > best_conversions:
            best_conversions = conversions
            best_channel = channel_name
    
    summary['top_channel'] = best_channel
    
    return jsonify(summary)


@bp.route('/api/lifecycle-distribution', methods=['GET'])
@login_required
def api_lifecycle_distribution():
    """
    Ottiene la distribuzione dei lifecycle changes nel periodo
    """
    
    from sqlalchemy import func
    from corposostenibile.extensions import db
    from datetime import date, timedelta
    
    # Ultimi 30 giorni di default
    days = request.args.get('days', 30, type=int)
    start_date = date.today() - timedelta(days=days)
    
    distribution = db.session.query(
        RespondIOLifecycleChange.to_lifecycle,
        func.count(RespondIOLifecycleChange.id).label('count')
    ).filter(
        RespondIOLifecycleChange.changed_at >= start_date
    ).group_by(RespondIOLifecycleChange.to_lifecycle).all()
    
    result = {
        'period_days': days,
        'distribution': [
            {'lifecycle': item[0], 'count': item[1]}
            for item in distribution
        ],
        'total': sum(item[1] for item in distribution)
    }
    
    return jsonify(result)