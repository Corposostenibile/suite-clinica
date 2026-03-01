"""
API routes per il blueprint communications.
"""

from flask import jsonify, request, url_for
from flask_login import login_required, current_user
from http import HTTPStatus

from corposostenibile.models import Communication
from . import communications_bp
from .services import CommunicationService
from .permissions import can_see_statistics


@communications_bp.route('/api/<int:communication_id>/stats')
@login_required
def api_get_stats(communication_id):
    """API per ottenere le statistiche di una comunicazione."""
    communication = Communication.query.get_or_404(communication_id)
    
    # Verifica permessi
    if not can_see_statistics(current_user, communication):
        return jsonify({'error': 'Non autorizzato'}), HTTPStatus.FORBIDDEN
    
    # Ottieni statistiche
    stats = CommunicationService.get_communication_stats(communication)
    
    return jsonify(stats)


@communications_bp.route('/api/<int:communication_id>/unread-users')
@login_required
def api_get_unread_users(communication_id):
    """API per ottenere la lista degli utenti che non hanno letto."""
    communication = Communication.query.get_or_404(communication_id)
    
    # Verifica permessi
    if not can_see_statistics(current_user, communication):
        return jsonify({'error': 'Non autorizzato'}), HTTPStatus.FORBIDDEN
    
    # Ottieni utenti che non hanno letto
    unread_users = communication.get_unread_users()
    
    # Formatta per JSON
    users_data = []
    for user in unread_users:
        users_data.append({
            'id': user.id,
            'full_name': user.full_name,
            'email': user.email,
            'department': user.department.name if user.department else 'N/A',
            'avatar_url': user.avatar_url if user.avatar_path else None
        })
    
    return jsonify({
        'total': len(users_data),
        'users': users_data
    })
