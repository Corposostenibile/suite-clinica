from flask import Blueprint, send_from_directory, redirect, abort, current_app
import os

documentation_bp = Blueprint('documentation', __name__)

# Percorso assoluto alla directory static
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

@documentation_bp.route('/')
def index_root():
    return redirect('/documentation/static/')

@documentation_bp.route('/static/')
@documentation_bp.route('/static/<path:path>')
def serve_docs(path=''):
    """
    Serve files and handle directory indexes (index.html)
    """
    # Rimuove lo slash iniziale se presente
    path = path.lstrip('/')
    
    full_path = os.path.join(STATIC_DIR, path)
    
    # Debug logging
    current_app.logger.info(f"[Docs] Requested path: {path}")
    current_app.logger.info(f"[Docs] Full path: {full_path}")
    
    # Se è una directory (con o senza slash finale), cerchiamo index.html
    if os.path.isdir(full_path):
        index_file = os.path.join(full_path, 'index.html')
        current_app.logger.info(f"[Docs] Path is directory. Checking: {index_file}")
        if os.path.exists(index_file):
            return send_from_directory(full_path, 'index.html')
        current_app.logger.error(f"[Docs] Directory index not found: {index_file}")
        abort(404)
        
    # Se è un file, lo serviamo
    if os.path.isfile(full_path):
        directory = os.path.dirname(full_path)
        filename = os.path.basename(full_path)
        return send_from_directory(directory, filename)

    # Fallback per directory senza trailing slash se non rilevate da isdir
    if os.path.exists(full_path) and os.path.isdir(full_path):
        return send_from_directory(full_path, 'index.html')

    current_app.logger.error(f"[Docs] Path not found: {full_path}")
    abort(404)
