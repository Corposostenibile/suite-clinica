"""
API Routes per Post-it / Promemoria personali.
CRUD completo per la gestione dei post-it dell'utente.
"""

from datetime import datetime
from flask import jsonify, request
from flask_login import login_required, current_user

from corposostenibile.blueprints.postit import bp
from corposostenibile.models import PostIt
from corposostenibile.extensions import db, csrf


@bp.route('/api/list', methods=['GET'])
@login_required
def list_postits():
    """
    GET /postit/api/list
    Restituisce tutti i post-it dell'utente corrente (non cancellati).
    """
    postits = PostIt.query.filter_by(
        user_id=current_user.id,
        deleted_at=None
    ).order_by(PostIt.position, PostIt.created_at.desc()).all()

    return jsonify({
        'success': True,
        'postits': [p.to_dict() for p in postits],
        'count': len(postits)
    })


@bp.route('/api/create', methods=['POST'])
@csrf.exempt
@login_required
def create_postit():
    """
    POST /postit/api/create
    Crea un nuovo post-it.

    Body JSON:
    {
        "content": "Testo del post-it",
        "color": "yellow|green|blue|pink|orange|purple",
        "reminderAt": "2024-01-15T10:00:00" (opzionale)
    }
    """
    try:
        data = request.get_json() or {}

        content = data.get('content', '').strip()
        if not content:
            return jsonify({
                'success': False,
                'error': 'Il contenuto del post-it non può essere vuoto'
            }), 400

        # Colori validi
        valid_colors = ['yellow', 'green', 'blue', 'pink', 'orange', 'purple']
        color = data.get('color', 'yellow')
        if color not in valid_colors:
            color = 'yellow'

        # Reminder opzionale
        reminder_at = None
        if data.get('reminderAt'):
            try:
                reminder_at = datetime.fromisoformat(data['reminderAt'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass

        # Trova la posizione massima per ordinamento
        max_position = db.session.query(db.func.max(PostIt.position)).filter_by(
            user_id=current_user.id,
            deleted_at=None
        ).scalar() or 0

        postit = PostIt(
            user_id=current_user.id,
            content=content,
            color=color,
            reminder_at=reminder_at,
            position=max_position + 1
        )

        db.session.add(postit)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Post-it creato con successo',
            'postit': postit.to_dict()
        }), 201
    except Exception:
        db.session.rollback()
        bp.logger.exception("Errore creazione post-it")
        return jsonify({
            'success': False,
            'error': 'Errore interno durante la creazione del post-it'
        }), 500


@bp.route('/api/<int:postit_id>', methods=['GET'])
@login_required
def get_postit(postit_id):
    """
    GET /postit/api/<id>
    Restituisce un singolo post-it.
    """
    postit = PostIt.query.filter_by(
        id=postit_id,
        user_id=current_user.id,
        deleted_at=None
    ).first()

    if not postit:
        return jsonify({
            'success': False,
            'error': 'Post-it non trovato'
        }), 404

    return jsonify({
        'success': True,
        'postit': postit.to_dict()
    })


@bp.route('/api/<int:postit_id>', methods=['PUT', 'PATCH'])
@csrf.exempt
@login_required
def update_postit(postit_id):
    """
    PUT/PATCH /postit/api/<id>
    Aggiorna un post-it esistente.

    Body JSON (tutti i campi opzionali):
    {
        "content": "Nuovo testo",
        "color": "green",
        "reminderAt": "2024-01-15T10:00:00" | null,
        "position": 5
    }
    """
    postit = PostIt.query.filter_by(
        id=postit_id,
        user_id=current_user.id,
        deleted_at=None
    ).first()

    if not postit:
        return jsonify({
            'success': False,
            'error': 'Post-it non trovato'
        }), 404

    data = request.get_json() or {}

    # Aggiorna content se fornito
    if 'content' in data:
        content = data['content'].strip()
        if not content:
            return jsonify({
                'success': False,
                'error': 'Il contenuto non può essere vuoto'
            }), 400
        postit.content = content

    # Aggiorna color se fornito
    if 'color' in data:
        valid_colors = ['yellow', 'green', 'blue', 'pink', 'orange', 'purple']
        if data['color'] in valid_colors:
            postit.color = data['color']

    # Aggiorna reminder se fornito
    if 'reminderAt' in data:
        if data['reminderAt'] is None:
            postit.reminder_at = None
        else:
            try:
                postit.reminder_at = datetime.fromisoformat(
                    data['reminderAt'].replace('Z', '+00:00')
                )
            except (ValueError, AttributeError):
                pass

    # Aggiorna position se fornito
    if 'position' in data and isinstance(data['position'], int):
        postit.position = data['position']

    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Post-it aggiornato con successo',
        'postit': postit.to_dict()
    })


@bp.route('/api/<int:postit_id>', methods=['DELETE'])
@csrf.exempt
@login_required
def delete_postit(postit_id):
    """
    DELETE /postit/api/<id>
    Elimina un post-it (soft delete).
    """
    postit = PostIt.query.filter_by(
        id=postit_id,
        user_id=current_user.id,
        deleted_at=None
    ).first()

    if not postit:
        return jsonify({
            'success': False,
            'error': 'Post-it non trovato'
        }), 404

    # Soft delete
    postit.deleted_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Post-it eliminato con successo'
    })


@bp.route('/api/reorder', methods=['POST'])
@csrf.exempt
@login_required
def reorder_postits():
    """
    POST /postit/api/reorder
    Riordina i post-it dell'utente.

    Body JSON:
    {
        "order": [3, 1, 5, 2]  // array di postit IDs nell'ordine desiderato
    }
    """
    data = request.get_json() or {}
    order = data.get('order', [])

    if not isinstance(order, list):
        return jsonify({
            'success': False,
            'error': 'Il campo order deve essere un array di ID'
        }), 400

    # Aggiorna le posizioni
    for position, postit_id in enumerate(order):
        postit = PostIt.query.filter_by(
            id=postit_id,
            user_id=current_user.id,
            deleted_at=None
        ).first()
        if postit:
            postit.position = position

    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Ordine aggiornato con successo'
    })
