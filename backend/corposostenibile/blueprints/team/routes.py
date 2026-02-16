"""
team.routes
===========

API routes for team blueprint - React frontend only.
All HTML template routes have been removed as the frontend is now React-based.
"""

from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
from typing import Any
import os
import json

from flask import (
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    request,
    url_for,
)
from flask_login import current_user, login_required
from corposostenibile.extensions import csrf
from sqlalchemy import func
from datetime import datetime

from corposostenibile.extensions import db
from corposostenibile.models import User
from . import team_bp


# ════════════════════════════════════════════════════════════════════════
#  ACL helper
# ════════════════════════════════════════════════════════════════════════

def _require_admin() -> None:
    is_hr = current_user.department and current_user.department.id == 17
    if not (current_user.is_authenticated and (current_user.is_admin or is_hr)):
        abort(HTTPStatus.FORBIDDEN)


def _require_assignment_permission() -> None:
    """
    Verifica permessi per gestione assegnazioni AI.
    Permette: Admin, CCO, Head dipartimento Coach/Psicologia, Head e Team Leader dipartimento Nutrizione,
    Utente ID 35 per Psicologia
    """
    if not current_user.is_authenticated:
        abort(HTTPStatus.FORBIDDEN)

    if current_user.is_admin:
        return

    # Utente specifico con accesso gestione Psicologia (ID 35)
    if current_user.id == 35:
        return

    if current_user.department:
        # CCO ha accesso completo
        if current_user.department.name == 'CCO':
            return

        # Head dei dipartimenti Coach, Psicologia
        if current_user.department.name in ['Coach', 'Psicologia']:
            if current_user.department.head_id == current_user.id:
                return

        # Per Nutrizione: Head dipartimento + Team Leader
        if current_user.department.name in ['Nutrizione', 'Nutrizione 2']:
            # Head dipartimento
            if current_user.department.head_id == current_user.id:
                return
            # Team Leader (head di un team nel dipartimento Nutrizione)
            from corposostenibile.models import Team
            is_team_leader = Team.query.filter_by(head_id=current_user.id).first() is not None
            if is_team_leader:
                return

    abort(HTTPStatus.FORBIDDEN)


# ════════════════════════════════════════════════════════════════════════════ #
#  PAGINA ASSEGNAZIONI AI - API ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════ #

@team_bp.route("/api/assegnazioni/<int:user_id>", methods=["GET"])
@login_required
def api_get_assignment_notes(user_id: int):
    """API per ottenere le note di assegnazione AI di un utente."""
    _require_assignment_permission()

    user = User.query.get_or_404(user_id)

    ai_notes = user.assignment_ai_notes or {}
    if isinstance(ai_notes, str):
        try:
            ai_notes = json.loads(ai_notes)
        except json.JSONDecodeError:
            ai_notes = {}

    return jsonify({
        'success': True,
        'user_id': user_id,
        'full_name': user.full_name,
        'department': user.department.name if user.department else None,
        'assignment_ai_notes': {
            'disponibile_assegnazioni': ai_notes.get('disponibile_assegnazioni', True),
            'specializzazione': ai_notes.get('specializzazione', ''),
            'target_ideale': ai_notes.get('target_ideale', ''),
            'problematiche_efficaci': ai_notes.get('problematiche_efficaci', ''),
            'target_non_ideale': ai_notes.get('target_non_ideale', ''),
            'link_calendario': ai_notes.get('link_calendario', ''),
            'link_call_bonus': ai_notes.get('link_call_bonus', ''),
            'note_aggiuntive': ai_notes.get('note_aggiuntive', '')
        }
    })


@team_bp.route("/api/assegnazioni/<int:user_id>", methods=["POST"])
@login_required
@csrf.exempt
def api_update_assignment_notes(user_id: int):
    """API per aggiornare le note di assegnazione AI di un utente."""
    _require_assignment_permission()

    user = User.query.get_or_404(user_id)
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'message': 'Dati non validi'}), 400

    # Recupera note esistenti o inizializza
    ai_notes = user.assignment_ai_notes or {}
    if isinstance(ai_notes, str):
        try:
            ai_notes = json.loads(ai_notes)
        except json.JSONDecodeError:
            ai_notes = {}

    # Aggiorna i campi
    if 'disponibile_assegnazioni' in data:
        ai_notes['disponibile_assegnazioni'] = bool(data['disponibile_assegnazioni'])
    if 'specializzazione' in data:
        ai_notes['specializzazione'] = data['specializzazione'].strip() if data['specializzazione'] else ''
    if 'target_ideale' in data:
        ai_notes['target_ideale'] = data['target_ideale'].strip() if data['target_ideale'] else ''
    if 'problematiche_efficaci' in data:
        ai_notes['problematiche_efficaci'] = data['problematiche_efficaci'].strip() if data['problematiche_efficaci'] else ''
    if 'target_non_ideale' in data:
        ai_notes['target_non_ideale'] = data['target_non_ideale'].strip() if data['target_non_ideale'] else ''
    if 'link_calendario' in data:
        ai_notes['link_calendario'] = data['link_calendario'].strip() if data['link_calendario'] else ''
    if 'link_call_bonus' in data:
        ai_notes['link_call_bonus'] = data['link_call_bonus'].strip() if data['link_call_bonus'] else ''
    if 'note_aggiuntive' in data:
        ai_notes['note_aggiuntive'] = data['note_aggiuntive'].strip() if data['note_aggiuntive'] else ''

    # Salva
    user.assignment_ai_notes = ai_notes

    # Flag modified per SQLAlchemy
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(user, 'assignment_ai_notes')

    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Impostazioni assegnazione per {user.full_name} aggiornate'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore aggiornamento assignment_ai_notes: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@team_bp.route("/api/assegnazioni/<int:user_id>/toggle-disponibile", methods=["POST"])
@login_required
@csrf.exempt
def api_toggle_assignment_available(user_id: int):
    """API per toggle rapido disponibilità assegnazioni."""
    _require_assignment_permission()

    user = User.query.get_or_404(user_id)

    # Recupera note esistenti o inizializza
    ai_notes = user.assignment_ai_notes or {}
    if isinstance(ai_notes, str):
        try:
            ai_notes = json.loads(ai_notes)
        except json.JSONDecodeError:
            ai_notes = {}

    # Toggle disponibilità (default True se non definito)
    current_value = ai_notes.get('disponibile_assegnazioni', True)
    ai_notes['disponibile_assegnazioni'] = not current_value

    user.assignment_ai_notes = ai_notes

    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(user, 'assignment_ai_notes')

    try:
        db.session.commit()
        new_status = "disponibile" if ai_notes['disponibile_assegnazioni'] else "non disponibile"
        return jsonify({
            'success': True,
            'disponibile': ai_notes['disponibile_assegnazioni'],
            'message': f'{user.full_name} ora è {new_status} per nuove assegnazioni'
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore toggle disponibilità: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
