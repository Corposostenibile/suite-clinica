"""
Main routes for SuiteMind blueprint.
Handles page rendering and static assets.
"""

import os
from flask import render_template, send_from_directory
from flask_login import login_required, current_user
from functools import wraps


def admin_required(f):
    """Decorator per richiedere permessi admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            from flask import abort
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def register_main_routes(bp):
    """Registra le route principali del blueprint."""

    @bp.route('/')
    @login_required
    def index():
        """Interfaccia principale del chatbot."""
        return render_template('index.html')

    @bp.route('/casi-pazienti')
    @login_required
    @admin_required
    def casi_pazienti():
        """Pagina per analizzare casi di successo dei pazienti."""
        return render_template('suitemind/casi_pazienti.html')

    @bp.route('/assets/<path:filename>')
    def assets(filename):
        """Serve i file statici dalla directory assets."""
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets')
        return send_from_directory(assets_dir, filename)