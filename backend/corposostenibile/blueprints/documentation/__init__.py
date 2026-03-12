from flask import Blueprint, send_from_directory, redirect, abort, current_app, request
import os
from flask_login import login_required, current_user

documentation_bp = Blueprint('documentation', __name__)

# Percorso assoluto alla directory static
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

def can_view_audience(audience):
    """
    Verifica se l'utente corrente può vedere la documentazione per una specifica audience.
    """
    if not current_user.is_authenticated:
        return False
    
    # Admin e CCO possono vedere tutto
    if current_user.is_admin or getattr(current_user, 'role', '') == 'admin' or \
       String(getattr(current_user, 'specialty', '')).lower() == 'cco':
        return True
    
    if audience == 'team_leader':
        return getattr(current_user, 'role', '') == 'team_leader'
    
    # Tutti gli altri utenti autenticati possono vedere la documentazione 'professionista'
    return True

# Helper per gestire il check dell'audience nel percorso del file
def check_path_permission(path):
    if 'team_leader' in path:
        return can_view_audience('team_leader')
    return True

@documentation_bp.route('/')
@login_required
def index_root():
    return redirect('/documentation/static/')

@documentation_bp.route('/static/')
@documentation_bp.route('/static/<path:path>')
@login_required
def serve_docs(path=''):
    """
    Serve files and handle directory indexes (index.html) with role check
    """
    # Rimuove lo slash iniziale se presente
    path = path.lstrip('/')
    
    # Controllo permessi sul percorso richiesto
    if not check_path_permission(path):
        current_app.logger.warning(f"[Docs] Unauthorized access attempt by user {current_user.id} to path: {path}")
        abort(403) # Forbidden
    
    full_path = os.path.join(STATIC_DIR, path)
    
    # Debug logging
    current_app.logger.info(f"[Docs] Requested path: {path}")
    
    # Se è una directory (con o senza slash finale), cerchiamo index.html
    if os.path.isdir(full_path):
        index_file = os.path.join(full_path, 'index.html')
        if os.path.exists(index_file):
            return send_from_directory(full_path, 'index.html')
        abort(404)
        
    # Se è un file, lo serviamo
    if os.path.isfile(full_path):
        directory = os.path.dirname(full_path)
        filename = os.path.basename(full_path)
        return send_from_directory(directory, filename)

    # Fallback per directory senza trailing slash se non rilevate da isdir
    if os.path.exists(full_path) and os.path.isdir(full_path):
        return send_from_directory(full_path, 'index.html')

    abort(404)

# Utility function since we don't have JavaScript's String() or cco check exactly the same
def String(val):
    return str(val) if val is not None else ""
