from flask import Blueprint, send_from_directory, redirect, abort, current_app, request, jsonify
import os
import yaml
from flask_login import login_required, current_user

documentation_bp = Blueprint('documentation', __name__)

# Percorso assoluto alla directory static
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
MKDOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
MKDOCS_YML = os.path.join(MKDOCS_DIR, 'mkdocs.yml')

ALLOWED_SPECIALTY_KEYS = {'nutrizione', 'coaching', 'psicologia'}

# Sezioni riservate ad admin/cco
ADMIN_ONLY_SECTIONS = {'infrastruttura', 'sviluppo'}

def scalar_value(val):
    if val is None:
        return ""
    return str(getattr(val, 'value', val))

def is_admin_or_cco_user(user):
    return bool(
        getattr(user, 'is_admin', False)
        or scalar_value(getattr(user, 'role', '')).lower() == 'admin'
        or scalar_value(getattr(user, 'specialty', '')).lower() == 'cco'
    )

def normalize_specialty_key(specialty):
    normalized = scalar_value(specialty).lower()
    if normalized in {'nutrizione', 'nutrizionista'}:
        return 'nutrizione'
    if normalized in {'psicologia', 'psicologo', 'psicologa'}:
        return 'psicologia'
    if normalized in {'coach', 'coaching'}:
        return 'coaching'
    return None

def can_view_audience(audience):
    """
    Verifica se l'utente corrente può vedere la documentazione per una specifica audience.
    """
    if not current_user.is_authenticated:
        return False
    
    # Admin e CCO possono vedere tutto
    if is_admin_or_cco_user(current_user):
        return True
    
    if audience == 'team_leader':
        return scalar_value(getattr(current_user, 'role', '')).lower() == 'team_leader'
    
    # Tutti gli altri utenti autenticati possono vedere la documentazione 'professionista'
    return True

# Helper per gestire il check dell'audience nel percorso del file
def check_path_permission(path):
    if not current_user.is_authenticated:
        return False

    # Admin/CCO hanno accesso completo
    if is_admin_or_cco_user(current_user):
        return True

    # Estrai la prima componente del percorso
    parts = [part for part in String(path).split('/') if part]
    if not parts:
        return True

    first_section = parts[0]

    # Controllo sezione admin-only (nega accesso a non-admin)
    if first_section in ADMIN_ONLY_SECTIONS:
        return False

    # Controllo team_leader nei path
    if 'team_leader' in path:
        return can_view_audience('team_leader')

    # Sezioni standard con controllo specialty
    if first_section not in {'pazienti', 'professionisti', 'azienda', 'guide-ruoli', 'team', 'clienti-core', 'strumenti', 'comunicazione', 'panoramica'}:
        return True

    # Se abbiamo un secondo livello, controlla la specialty
    if len(parts) < 2:
        return True

    doc_slug = parts[1]
    requested_specialty = next((specialty for specialty in ALLOWED_SPECIALTY_KEYS if f'_{specialty}' in doc_slug), None)
    if not requested_specialty:
        return True

    user_specialty = normalize_specialty_key(getattr(current_user, 'specialty', ''))
    return user_specialty == requested_specialty

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
    return scalar_value(val)

# ─────────────────────────────────────────────────────────────────────────────
# API: Configurazione navigazione da mkdocs.yml
# ─────────────────────────────────────────────────────────────────────────────

def _load_mkdocs_nav():
    """Carica e processa la navigazione da mkdocs.yml."""
    if not os.path.exists(MKDOCS_YML):
        return []
    
    with open(MKDOCS_YML, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config.get('nav', []) if config else []

def _is_admin_only_section(section_key):
    """Check se una sezione e admin-only."""
    admin_section_keys = {'infrastruttura', 'sviluppo'}
    return section_key in admin_section_keys

def _extract_key_from_title(title):
    """Estrae una chiave URL-safe da un titolo."""
    # Rimuovi caratteri speciali, spaazi con underscore
    import re
    key = re.sub(r'[^\w\s-]', '', title.lower())
    key = re.sub(r'[\s]+', '-', key)
    return key

def _normalize_nav_item(item, parent_key=None):
    """
    Normalizza un item della navigazione mkdocs.
    Restituisce dict strutturato per il frontend.
    """
    if isinstance(item, str):
        # Item semplice: "Title: path.md"
        if ':' in item:
            title, path = item.split(':', 1)
            title = title.strip()
            path = path.strip().replace('.md', '/')  # path.md -> path/
            section_key = parent_key or _extract_key_from_title(title)
            return {
                'key': _extract_key_from_title(title),
                'label': title,
                'path': path,
                'section': section_key,
                'isStatic': True,
            }
        return None
    
    if isinstance(item, dict):
        for title, children in item.items():
            section_key = _extract_key_from_title(title)
            
            # Determina se la sezione e admin-only
            is_admin_section = _is_admin_only_section(section_key)
            
            if children is None:
                # Sezione senza figli (path diretto)
                return {
                    'key': section_key,
                    'label': title,
                    'path': None,
                    'section': section_key,
                    'isAdminOnly': is_admin_section,
                    'isStatic': True,
                }
            
            # Sezione con figli
            processed_children = []
            for child in children:
                processed = _normalize_nav_item(child, section_key)
                if processed:
                    processed_children.append(processed)
            
            return {
                'key': section_key,
                'label': title,
                'section': section_key,
                'isAdminOnly': is_admin_section,
                'items': processed_children,
                'isGroup': len(processed_children) > 1,
            }
    
    return None

@documentation_bp.route('/api/nav')
@login_required
def get_navigation():
    """
    REST endpoint che restituisce la configurazione della navigazione
    derivata da mkdocs.yml, strutturata per il frontend.
    
    Filtra le sezioni admin-only per utenti non-admin.
    """
    nav = _load_mkdocs_nav()
    
    # Processa la navigazione
    processed_nav = []
    for item in nav:
        processed = _normalize_nav_item(item)
        if processed:
            # Filtra sezioni admin-only per non-admin
            if processed.get('isAdminOnly') and not is_admin_or_cco_user(current_user):
                continue
            processed_nav.append(processed)
    
    return jsonify({
        'success': True,
        'data': processed_nav,
        'isAdmin': is_admin_or_cco_user(current_user),
    })
