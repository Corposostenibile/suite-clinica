"""
Route per dashboard Respond.io - versione semplificata solo metriche
"""

from datetime import datetime, date, timedelta
from collections import defaultdict
from flask import request, jsonify, flash, redirect, url_for, current_app, session
from flask_login import login_required
from sqlalchemy import func, and_, or_
from corposostenibile.extensions import db
from corposostenibile.models import (
    RESPOND_IO_CHANNELS,
    RespondIOFollowupQueue,
    RespondIOFollowupConfig,
    RespondIOLifecycleChange,
    FOLLOWUP_ENABLED_LIFECYCLES
)
from . import bp
from .services import FunnelAnalyticsService


@bp.route('/test-api')
@login_required
def test_api():
    """Route di test per verificare la connessione API"""
    try:
        from .client import RespondIOClient
        import requests
        
        # Test manuale diretto con requests
        api_token = current_app.config.get('RESPOND_IO_API_TOKEN')
        
        # Facciamo una chiamata diretta per debug
        url = "https://api.respond.io/v2/contact/list?limit=1"
        headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        body = {
            "search": "",
            "filter": {
                "$and": []
            },
            "timezone": "Europe/Rome"  # RICHIESTO!
        }
        
        response = requests.post(url, json=body, headers=headers)
        
        return jsonify({
            'success': response.status_code == 200,
            'status_code': response.status_code,
            'response_text': response.text,
            'response_headers': dict(response.headers),
            'request_body': body,
            'request_url': url
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


# API routes temporaneamente disabilitate - saranno ricostruite
# Le route per follow-up rimangono intatte sotto


# ========================= FOLLOW-UP SYSTEM ROUTES =========================

@bp.route('/api/followup/config', methods=['GET', 'POST'])
@login_required
def api_followup_config():
    """API per gestire configurazioni follow-up"""
    
    if request.method == 'GET':
        configs = RespondIOFollowupConfig.query.all()
        return jsonify([{
            'id': c.id,
            'lifecycle': c.lifecycle,
            'enabled': c.enabled,
            'delay_hours': c.delay_hours,
            'message_text': c.message_text,
            'template_name': c.template_name,
            'tag_waiting': c.tag_waiting,
            'tag_sent': c.tag_sent,
            'total_scheduled': c.total_scheduled,
            'total_sent': c.total_sent,
            'total_cancelled': c.total_cancelled
        } for c in configs])
    
    elif request.method == 'POST':
        data = request.get_json()
        lifecycle = data.get('lifecycle')
        
        if lifecycle not in FOLLOWUP_ENABLED_LIFECYCLES:
            return jsonify({'error': 'Invalid lifecycle'}), 400
        
        config = RespondIOFollowupConfig.query.filter_by(lifecycle=lifecycle).first()
        if not config:
            config = RespondIOFollowupConfig(lifecycle=lifecycle)
            db.session.add(config)
        
        # Aggiorna configurazione
        config.enabled = data.get('enabled', config.enabled)
        config.delay_hours = data.get('delay_hours', config.delay_hours)
        config.message_text = data.get('message_text', config.message_text)
        config.template_name = data.get('template_name', config.template_name)
        config.tag_waiting = data.get('tag_waiting', config.tag_waiting)
        config.tag_sent = data.get('tag_sent', config.tag_sent)
        
        db.session.commit()
        
        return jsonify({'status': 'success', 'id': config.id})


@bp.route('/api/followup/queue/<int:queue_id>', methods=['DELETE'])
@login_required
def api_cancel_followup(queue_id):
    """Cancella un follow-up pending"""
    
    followup = RespondIOFollowupQueue.query.get_or_404(queue_id)
    
    if followup.status != 'pending':
        return jsonify({'error': 'Can only cancel pending follow-ups'}), 400
    
    followup.status = 'cancelled'
    followup.cancelled_at = datetime.utcnow()
    followup.error_message = 'Manually cancelled from dashboard'
    
    db.session.commit()
    
    flash(f'Follow-up per contatto {followup.contact_id} cancellato', 'success')
    return jsonify({'status': 'success'})


@bp.route('/api/followup/stats')
@login_required
def api_followup_stats():
    """Statistiche follow-up per grafici"""
    
    days = request.args.get('days', 7, type=int)
    start_date = date.today() - timedelta(days=days)
    
    # Query statistiche giornaliere
    from sqlalchemy import func
    
    daily_stats = db.session.query(
        func.date(RespondIOFollowupQueue.created_at).label('date'),
        RespondIOFollowupQueue.status,
        func.count(RespondIOFollowupQueue.id).label('count')
    ).filter(
        RespondIOFollowupQueue.created_at >= start_date
    ).group_by(
        'date',
        RespondIOFollowupQueue.status
    ).all()
    
    # Organizza per data
    stats_by_date = {}
    current = start_date
    while current <= date.today():
        stats_by_date[current.isoformat()] = {
            'pending': 0,
            'sent': 0,
            'cancelled': 0,
            'failed': 0
        }
        current += timedelta(days=1)
    
    for date_val, status, count in daily_stats:
        if date_val:
            date_str = date_val.isoformat()
            if date_str in stats_by_date:
                stats_by_date[date_str][status] = count
    
    return jsonify({
        'dates': list(stats_by_date.keys()),
        'data': stats_by_date
    })


@bp.route('/api/followup/duplicates')
@login_required
def api_followup_duplicates():
    """API per rilevare duplicati nel sistema follow-up"""
    
    from sqlalchemy import func
    
    # Duplicati già inviati (stesso contact, stesso giorno, multiple volte)
    sent_duplicates = db.session.query(
        RespondIOFollowupQueue.contact_id,
        func.date(RespondIOFollowupQueue.sent_at).label('date'),
        func.count(RespondIOFollowupQueue.id).label('count')
    ).filter(
        RespondIOFollowupQueue.status == 'sent',
        RespondIOFollowupQueue.sent_at.isnot(None)
    ).group_by(
        RespondIOFollowupQueue.contact_id,
        func.date(RespondIOFollowupQueue.sent_at)
    ).having(
        func.count(RespondIOFollowupQueue.id) > 1
    ).all()
    
    # Duplicati pending/processing (potenziali futuri duplicati)
    pending_duplicates = db.session.query(
        RespondIOFollowupQueue.contact_id,
        RespondIOFollowupQueue.lifecycle,
        func.count(RespondIOFollowupQueue.id).label('count')
    ).filter(
        RespondIOFollowupQueue.status.in_(['pending', 'processing'])
    ).group_by(
        RespondIOFollowupQueue.contact_id,
        RespondIOFollowupQueue.lifecycle
    ).having(
        func.count(RespondIOFollowupQueue.id) > 1
    ).all()
    
    # Dettagli per duplicati inviati
    sent_details = []
    for contact_id, date, count in sent_duplicates:
        details = RespondIOFollowupQueue.query.filter(
            RespondIOFollowupQueue.contact_id == contact_id,
            func.date(RespondIOFollowupQueue.sent_at) == date,
            RespondIOFollowupQueue.status == 'sent'
        ).order_by(RespondIOFollowupQueue.sent_at).all()
        
        sent_details.append({
            'contact_id': contact_id,
            'date': date.isoformat() if date else None,
            'count': count,
            'messages': [{
                'id': d.id,
                'sent_at': d.sent_at.isoformat() if d.sent_at else None,
                'message_type': d.message_type
            } for d in details]
        })
    
    # Dettagli per duplicati pending
    pending_details = []
    for contact_id, lifecycle, count in pending_duplicates:
        details = RespondIOFollowupQueue.query.filter(
            RespondIOFollowupQueue.contact_id == contact_id,
            RespondIOFollowupQueue.lifecycle == lifecycle,
            RespondIOFollowupQueue.status.in_(['pending', 'processing'])
        ).order_by(RespondIOFollowupQueue.scheduled_at).all()
        
        pending_details.append({
            'contact_id': contact_id,
            'lifecycle': lifecycle,
            'count': count,
            'followups': [{
                'id': d.id,
                'scheduled_at': d.scheduled_at.isoformat() if d.scheduled_at else None,
                'status': d.status
            } for d in details]
        })
    
    return jsonify({
        'sent_duplicates': sent_details,
        'pending_duplicates': pending_details,
        'has_duplicates': len(sent_details) > 0 or len(pending_details) > 0,
        'total_sent_duplicates': len(sent_details),
        'total_pending_duplicates': len(pending_details)
    })


@bp.route('/api/followup/cleanup-duplicates', methods=['POST'])
@login_required
def api_cleanup_duplicates():
    """Rimuove follow-up duplicati mantenendo solo il primo per contatto"""
    
    from sqlalchemy import func
    
    removed_count = 0
    
    try:
        # IMPORTANTE: Un contatto dovrebbe avere SOLO UN follow-up attivo alla volta
        # indipendentemente dal lifecycle (perché può cambiare rapidamente)
        
        # Trova tutti i contatti con più di un follow-up pending/processing
        contacts_with_duplicates = db.session.query(
            RespondIOFollowupQueue.contact_id,
            func.count(RespondIOFollowupQueue.id).label('count')
        ).filter(
            RespondIOFollowupQueue.status.in_(['pending', 'processing'])
        ).group_by(
            RespondIOFollowupQueue.contact_id
        ).having(
            func.count(RespondIOFollowupQueue.id) > 1
        ).all()
        
        # Per ogni contatto con duplicati
        for contact_id, count in contacts_with_duplicates:
            # Prendi TUTTI i follow-up per questo contatto (indipendentemente dal lifecycle)
            followups = RespondIOFollowupQueue.query.filter(
                RespondIOFollowupQueue.contact_id == contact_id,
                RespondIOFollowupQueue.status.in_(['pending', 'processing'])
            ).order_by(
                RespondIOFollowupQueue.scheduled_at  # Mantieni quello schedulato prima
            ).all()
            
            # Log per debug
            current_app.logger.info(f"Contact {contact_id} has {len(followups)} pending follow-ups")
            
            # Mantieni solo il PRIMO (quello schedulato prima)
            # Cancella TUTTI gli altri
            for followup in followups[1:]:
                # Revoca il task Celery se esiste
                if followup.celery_task_id:
                    try:
                        from corposostenibile.celery_app import celery
                        celery.control.revoke(followup.celery_task_id, terminate=True)
                        current_app.logger.info(f"Revoked Celery task {followup.celery_task_id}")
                    except Exception as e:
                        current_app.logger.error(f"Error revoking task: {e}")
                
                # Marca come cancellato
                followup.status = 'cancelled'
                followup.cancelled_at = datetime.utcnow()
                followup.error_message = f'Duplicate removed - keeping only first followup for contact'
                removed_count += 1
                
                current_app.logger.info(f"Cancelled follow-up {followup.id} for contact {contact_id} (lifecycle: {followup.lifecycle})")
        
        db.session.commit()
        
        flash(f'Rimossi {removed_count} follow-up duplicati', 'success')
        current_app.logger.info(f"Cleanup completed: removed {removed_count} duplicate follow-ups")
        
        return jsonify({'status': 'success', 'removed': removed_count})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'error': str(e)}), 500


@bp.route('/api/followup/test', methods=['POST'])
@login_required
def api_test_followup():
    """Test invio follow-up manuale (solo per testing)"""
    
    data = request.get_json()
    contact_id = data.get('contact_id')
    lifecycle = data.get('lifecycle', 'Link Inviato')
    use_template = data.get('use_template', False)
    
    if not contact_id:
        return jsonify({'error': 'contact_id required'}), 400
    
    try:
        from .client import RespondIOClient
        from flask import current_app
        
        client = RespondIOClient(current_app.config)
        
        # Ottieni canale
        from corposostenibile.models import RespondIOContactChannel
        channel_name, channel_source = RespondIOContactChannel.get_channel(contact_id)
        
        if not channel_name:
            return jsonify({'error': 'Channel not found for contact'}), 404
        
        # Invia messaggio di test
        if use_template:
            result = client.send_template_message(
                contact_id,
                'followup_generico1',
                language='it'
            )
            message_type = 'template'
        else:
            result = client.send_message(
                contact_id,
                "Ciao 💪 Stai bene?"
            )
            message_type = 'text'
        
        return jsonify({
            'status': 'success',
            'message_type': message_type,
            'result': result
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500