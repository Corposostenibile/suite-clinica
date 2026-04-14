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

# Sezioni riservate ad admin/cco (tutto il contenuto)
ADMIN_ONLY_SECTIONS = {'infrastruttura', 'sviluppo', 'SYSTEM_DOCUMENTATION'}

# Sezioni accessibili ad admin + team leader (non professionisti)
ADMIN_AND_TL_SECTIONS = {'team', 'strumenti', 'comunicazione'}

# Sezioni con controllo specialty per guide ruolo
# Costruisce mapping: slug parziale -> specialty richiesta
GUIDE_RUOLI_SPECIALTY_MAP = {
    'guida-team-leader': None,  # tutti i team leader
    'guida-coach': 'coach',
    'guida-nutrizionista': 'nutrizione',
    'guida-psicologo': 'psicologia',
    'guida-health-manager': None,  # hm hanno proprio ruolo
}

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

def is_team_leader_user(user):
    """Check se utente ha ruolo team_leader."""
    return scalar_value(getattr(user, 'role', '')).lower() == 'team_leader'

def is_health_manager_user(user):
    """Check se utente e health manager."""
    specialty = normalize_specialty_key(scalar_value(getattr(user, 'specialty', '')))
    role = scalar_value(getattr(user, 'role', '')).lower()
    return specialty == 'health_manager' or role == 'health_manager'

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

    # Estrai componenti del percorso
    parts = [part for part in String(path).split('/') if part]
    if not parts:
        return True

    first_section = parts[0]

    # ── Regola 1: sezioni admin-only ──
    if first_section in ADMIN_ONLY_SECTIONS:
        return False

    # ── Regola 2: guide ruolo (accesso per specialty/ruolo) ──
    if first_section == 'guide-ruoli' and len(parts) >= 2:
        guide_slug = parts[1]
        return _check_guide_ruoli_access(guide_slug)

    # ── Regola 3: team (solo admin + team leader) ──
    if first_section == 'team':
        return is_team_leader_user(current_user)

    # ── Regola 4: strumenti/quality-score (solo TL) ──
    if first_section == 'strumenti' and len(parts) >= 2:
        if parts[1] == 'quality-score' or parts[1] == 'quality_score':
            return is_team_leader_user(current_user)
        return True  # altri strumenti accessibili

    # ── Regola 5: comunicazione/ (limitata per alcune sezioni) ──
    if first_section == 'comunicazione':
        return True  # accesso generico, controlli granulari a livello app

    # ── Regola 6: guide con varianti (pazienti, professionisti, azienda) ──
    if first_section in {'pazienti', 'professionisti', 'azienda'}:
        # Controllo team_leader nei path
        if 'team_leader' in path:
            return can_view_audience('team_leader')
        # Controllo specialty
        if len(parts) >= 2:
            doc_slug = parts[1]
            requested_specialty = next(
                (s for s in ALLOWED_SPECIALTY_KEYS if f'_{s}' in doc_slug),
                None
            )
            if requested_specialty:
                user_specialty = normalize_specialty_key(getattr(current_user, 'specialty', ''))
                return user_specialty == requested_specialty
        return True

    # ── Regola 7: tutto il resto (panoramica, clienti-core, etc.) ──
    return True


def _check_guide_ruoli_access(guide_slug):
    """
    Verifica accesso alle guide ruolo.
    - guida-team-leader: solo team leader
    - guida-coach: solo specialty coaching
    - guida-nutrizionista: solo specialty nutrizione
    - guida-psicologo: solo specialty psicologia
    - guida-health-manager: solo health manager
    - overview: tutti
    """
    # Mappa slug -> check function
    guide_access = {
        'guida-team-leader': lambda: is_team_leader_user(current_user),
        'guida-coach': lambda: normalize_specialty_key(scalar_value(
            getattr(current_user, 'specialty', ''))) in ('coaching', 'coach'),
        'guida-nutrizionista': lambda: normalize_specialty_key(scalar_value(
            getattr(current_user, 'specialty', ''))) in ('nutrizione', 'nutrizionista'),
        'guida-psicologo': lambda: normalize_specialty_key(scalar_value(
            getattr(current_user, 'specialty', ''))) in ('psicologia', 'psicologo'),
        'guida-health-manager': lambda: is_health_manager_user(current_user),
        'overview': lambda: True,  # overview accessibile a tutti
    }
    
    check_fn = guide_access.get(guide_slug)
    if check_fn:
        return check_fn()
    
    # Slug non riconosciuto: nega per sicurezza
    return False

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
        config = yaml.load(f, Loader=yaml.FullLoader)
    
    return config.get('nav', []) if config else []

def _is_admin_only_section(section_key):
    """Check se una sezione e admin-only."""
    admin_section_keys = {'infrastruttura', 'sviluppo', 'amministrazione-e-it', 'system-documentation'}
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
            
            # children puo essere:
            # - None: sezione senza path proprio
            # - str: path diretto (es. "index.md")
            # - list: lista di figli (altri items o dicts)
            
            if children is None:
                # Sezione senza path proprio (solo header)
                return {
                    'key': section_key,
                    'label': title,
                    'path': None,
                    'section': section_key,
                    'isAdminOnly': is_admin_section,
                    'isGroup': True,
                    'isStatic': True,
                }
            
            if isinstance(children, str):
                # Path diretto - questa sezione ha un file proprio
                path = children.strip().replace('.md', '/')
                return {
                    'key': section_key,
                    'label': title,
                    'path': path,
                    'section': section_key,
                    'isAdminOnly': is_admin_section,
                    'isStatic': True,
                }
            
            # Lista di figli
            processed_children = []
            for child in children:
                processed = _normalize_nav_item(child, section_key)
                if processed:
                    processed_children.append(processed)
            
            # Il path del primo child con path serve per rendere l'header cliccabile
            first_child_path = None
            for c in processed_children:
                if c.get('path'):
                    first_child_path = c['path']
                    break
            
            return {
                'key': section_key,
                'label': title,
                'section': section_key,
                'path': first_child_path,  # header cliccabile se ha un child con path
                'isAdminOnly': is_admin_section,
                'items': processed_children,
                'isGroup': len(processed_children) > 0,
            }
    
    return None

@documentation_bp.route('/nav')
@login_required
def get_navigation():
    """
    REST endpoint che restituisce la configurazione della navigazione
    derivata da mkdocs.yml, strutturata per il frontend.
    
    Filtra sezioni per permessi utente:
    - admin/cco: accesso completo
    - team leader: area clinica + strumenti + comunicazione + team
    - professionista: area clinica + strumenti + comunicazione base
    - guida ruolo: solo la propria guida
    """
    nav = _load_mkdocs_nav()
    user = current_user
    user_is_admin = is_admin_or_cco_user(user)
    user_is_tl = is_team_leader_user(user)
    user_specialty = normalize_specialty_key(scalar_value(
        getattr(user, 'specialty', '')))
    
    processed_nav = []
    for item in nav:
        processed = _normalize_nav_item(item)
        if not processed:
            continue
        
        section_key = processed.get('key', '')
        
        # ── Admin-only sections ──
        if processed.get('isAdminOnly') and not user_is_admin:
            continue
        
        # ── Team section: solo admin + team leader ──
        if section_key == 'team' and not user_is_admin and not user_is_tl:
            continue
        
        # ── Guide Ruolo: filtra items per specialty ──
        if section_key == 'guide-per-ruolo' and not user_is_admin:
            processed = _filter_guide_ruoli_for_user(processed, user_is_tl, user_specialty)
            if not processed or not processed.get('items'):
                continue
        
        # ── Strumenti: quality-score solo per admin + TL ──
        if section_key == 'strumenti' and not user_is_admin:
            items = processed.get('items', [])
            filtered_items = [
                i for i in items
                if not _is_tl_only_item(i)
            ]
            processed['items'] = filtered_items
        
        processed_nav.append(processed)
    
    return jsonify({
        'success': True,
        'data': processed_nav,
        'isAdmin': user_is_admin,
    })


def _is_tl_only_item(item):
    """Check se un item e accessibile solo a team leader."""
    slug = item.get('key', '')
    tl_only = {'quality-score', 'quality_score'}
    return slug in tl_only


def _filter_guide_ruoli_for_user(group, user_is_tl, user_specialty):
    """
    Filtra gli items di guide-ruoli in base al ruolo/specialty dell'utente.
    """
    if not group.get('items'):
        return group
    
    filtered = []
    for item in group['items']:
        slug = item.get('key', '')
        
        # overview accessibile a tutti
        if slug == 'overview':
            filtered.append(item)
            continue
        
        # Guida team leader: solo TL
        if 'team-leader' in slug or 'team_leader' in slug:
            if user_is_tl:
                filtered.append(item)
            continue
        
        # Guida coach: solo specialty coaching
        if 'coach' in slug:
            if user_specialty in ('coaching', 'coach'):
                filtered.append(item)
            continue
        
        # Guida nutrizionista: solo specialty nutrizione
        if 'nutrizionista' in slug or 'nutrizione' in slug:
            if user_specialty in ('nutrizione', 'nutrizionista'):
                filtered.append(item)
            continue
        
        # Guida psicologo: solo specialty psicologia
        if 'psicologo' in slug or 'psicologia' in slug:
            if user_specialty in ('psicologia', 'psicologo', 'psicologa'):
                filtered.append(item)
            continue
        
        # Guida health manager: solo HM
        if 'health-manager' in slug or 'health_manager' in slug:
            hm_role = scalar_value(getattr(current_user, 'role', '')).lower()
            hm_spec = scalar_value(getattr(current_user, 'specialty', '')).lower()
            if hm_role == 'health_manager' or 'health_manager' in hm_spec:
                filtered.append(item)
            continue
        
        # Default: mostra
        filtered.append(item)
    
    group['items'] = filtered
    return group
