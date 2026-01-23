"""
Error handlers for Sales Form Blueprint
"""

from flask import render_template, jsonify
from werkzeug.exceptions import HTTPException
from . import sales_form_bp


@sales_form_bp.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    if hasattr(error, 'description'):
        message = error.description
    else:
        message = "La pagina richiesta non è stata trovata"

    # Check if it's an API request
    if '/api/' in str(error):
        return jsonify({'success': False, 'error': message}), 404

    return render_template('sales_form/errors/404.html', message=message), 404


@sales_form_bp.errorhandler(403)
def forbidden_error(error):
    """Handle 403 errors"""
    message = "Non hai i permessi per accedere a questa risorsa"

    # Check if it's an API request
    if '/api/' in str(error):
        return jsonify({'success': False, 'error': message}), 403

    return render_template('sales_form/errors/403.html', message=message), 403


@sales_form_bp.errorhandler(410)
def gone_error(error):
    """Handle 410 errors (resource no longer available)"""
    if hasattr(error, 'description'):
        message = error.description
    else:
        message = "Questa risorsa non è più disponibile"

    # Check if it's an API request
    if '/api/' in str(error):
        return jsonify({'success': False, 'error': message}), 410

    return render_template('sales_form/errors/410.html', message=message), 410


@sales_form_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    message = "Si è verificato un errore interno. Riprova più tardi."

    # Check if it's an API request
    if '/api/' in str(error):
        return jsonify({'success': False, 'error': message}), 500

    return render_template('sales_form/errors/500.html', message=message), 500


@sales_form_bp.errorhandler(429)
def ratelimit_error(error):
    """Handle rate limit errors"""
    message = "Troppe richieste. Attendi qualche minuto prima di riprovare."

    # Check if it's an API request
    if '/api/' in str(error):
        return jsonify({'success': False, 'error': message}), 429

    return render_template('sales_form/errors/429.html', message=message), 429