"""
Routes for automatic assignment dashboard
"""

from flask import render_template, jsonify, request
from flask_login import login_required, current_user
from . import bp
from corposostenibile.extensions import db
from corposostenibile.models import RespondIOAssignmentLog
from datetime import datetime, timedelta
import pytz

@bp.route('/assignment/realtime')
@login_required
def assignment_realtime_dashboard():
    """Real-time assignment dashboard"""
    return render_template('respond_io/assignment_realtime.html')

@bp.route('/assignment/stats')
def get_assignment_stats():
    """Get current assignment statistics"""
    from flask import current_app
    service = current_app.auto_assignment_service
    stats = service.get_assignment_statistics()
    
    # Calculate next check time
    now = datetime.now(pytz.timezone('Europe/Rome'))
    minutes_since_hour = now.minute % 10
    seconds_to_next = (10 - minutes_since_hour) * 60 - now.second
    
    return jsonify({
        'statistics': stats,
        'next_check_seconds': seconds_to_next,
        'last_check': service.last_check_time.isoformat() if service.last_check_time else None
    })

@bp.route('/assignment/logs')
@login_required
def get_assignment_logs():
    """Get assignment logs with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    # Get date filter
    date_str = request.args.get('date')
    if date_str:
        try:
            filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            filter_date = datetime.now().date()
    else:
        filter_date = datetime.now().date()
    
    # Query logs
    logs_query = RespondIOAssignmentLog.query.filter(
        db.func.date(RespondIOAssignmentLog.created_at) == filter_date
    ).order_by(RespondIOAssignmentLog.created_at.desc())
    
    pagination = logs_query.paginate(page=page, per_page=per_page, error_out=False)
    
    logs = []
    for log in pagination.items:
        logs.append({
            'id': log.id,
            'action': log.action,
            'reason': log.reason,
            'details': log.details,
            'user_id': log.user_id,
            'contact_id': log.contact_id,
            'created_at': log.created_at.isoformat()
        })
    
    return jsonify({
        'logs': logs,
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages,
        'per_page': per_page
    })

@bp.route('/assignment/force-check', methods=['POST'])
@login_required
def force_assignment_check():
    """Force an immediate assignment check"""
    from flask import current_app
    service = current_app.auto_assignment_service
    
    try:
        result = service.run_assignment_check()
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bp.route('/assignment/toggle-auto', methods=['POST'])
@login_required
def toggle_auto_assignment():
    """Toggle automatic assignment on/off"""
    from flask import current_app
    enabled = request.json.get('enabled', True)
    
    # Store state in app config or database
    current_app.config['RESPOND_IO_AUTO_ASSIGNMENT_ENABLED'] = enabled
    
    return jsonify({
        'success': True,
        'enabled': enabled
    })