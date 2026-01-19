"""
WebSocket routes for real-time assignment updates
"""

from flask import request, current_app
from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
from corposostenibile.extensions import socketio
from datetime import datetime, timedelta
import pytz

@socketio.on('connect', namespace='/respond-io')
def handle_connect():
    """Handle WebSocket connection"""
    if not current_user.is_authenticated:
        return False
    
    join_room('assignment_dashboard')
    emit('connected', {'message': 'Connected to assignment dashboard'})
    
    # Send initial stats
    send_dashboard_update()

@socketio.on('disconnect', namespace='/respond-io')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    leave_room('assignment_dashboard')

@socketio.on('request_update', namespace='/respond-io')
def handle_request_update():
    """Handle manual update request"""
    send_dashboard_update()

@socketio.on('force_assignment_check', namespace='/respond-io')
def handle_force_check():
    """Handle forced assignment check"""
    if not current_user.is_authenticated:
        emit('error', {'message': 'Unauthorized'})
        return
    
    # Run assignment check immediately
    result = current_app.auto_assignment_service.run_assignment_check()
    
    # Send update to all connected clients
    socketio.emit('assignment_complete', result, namespace='/respond-io', room='assignment_dashboard')
    send_dashboard_update()

def send_dashboard_update():
    """Send dashboard update to all connected clients"""
    try:
        service = current_app.auto_assignment_service
        
        # Get current statistics with timeout
        stats = service.get_assignment_statistics()
        
        # Calculate time to next check (every 10 minutes)
        now = datetime.now(pytz.timezone('Europe/Rome'))
        minutes_since_hour = now.minute % 10
        seconds_to_next = (10 - minutes_since_hour) * 60 - now.second
        
        # Get today's logs
        logs = service.get_today_logs()
        
        # Get users on duty
        users_on_duty_list = []
        try:
            from .assignment_service import ContactAssignmentService
            assignment_service = ContactAssignmentService(current_app.respond_io_client)
            users_on_duty = assignment_service.get_users_on_duty()
            
            for user in users_on_duty:
                # Handle both dict and object formats
                if isinstance(user, dict):
                    users_on_duty_list.append({
                        'id': user.get('id'),
                        'name': user.get('name', 'Unknown'),
                        'email': user.get('email', 'Unknown'),
                        'on_break': user.get('is_on_break', False)
                    })
                else:
                    users_on_duty_list.append({
                        'id': getattr(user, 'id', None),
                        'name': getattr(user, 'name', 'Unknown'),
                        'email': getattr(user, 'email', 'Unknown'),
                        'on_break': getattr(user, 'is_on_break', False)
                    })
        except Exception as e:
            current_app.logger.error(f"Error getting users on duty: {str(e)}")
        
        update_data = {
            'statistics': stats,
            'users_on_duty': users_on_duty_list,
            'next_check_seconds': seconds_to_next,
            'last_check': service.last_check_time.isoformat() if service.last_check_time else None,
            'logs': logs,
            'timestamp': datetime.now().isoformat()
        }
        
        socketio.emit('dashboard_update', update_data, namespace='/respond-io', room='assignment_dashboard')
    except Exception as e:
        current_app.logger.error(f"Error sending dashboard update: {str(e)}")
        # Send minimal update
        socketio.emit('dashboard_update', {
            'statistics': {'total_contacts': 0, 'unassigned_contacts': 0, 'by_user': {}, 'by_lifecycle': {}},
            'users_on_duty': [],
            'next_check_seconds': 600,
            'logs': [],
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }, namespace='/respond-io', room='assignment_dashboard')

@socketio.on('assignment_progress', namespace='/respond-io')
def send_assignment_progress(data):
    """Send assignment progress updates"""
    socketio.emit('assignment_progress', data, namespace='/respond-io', room='assignment_dashboard')