"""
Knowledge Base Utils
====================
Funzioni di utilità per la gestione della Knowledge Base.
"""

import os
import re
import secrets
import hashlib
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image
import mimetypes
from flask import current_app, url_for
from flask_login import current_user
from werkzeug.utils import secure_filename
from sqlalchemy import func, and_, or_
from bs4 import BeautifulSoup

from corposostenibile.extensions import db
from corposostenibile.models import (
    KBArticle, KBCategory, KBAttachment, KBDepartmentQuota,
    KBAnalytics, KBActivityLog, KBDepartmentAlert,
    KBActionTypeEnum, KBAlertTypeEnum, Department
)


# ═══════════════════════════════════════════════════════════════════════════
#                              FILE HANDLING
# ═══════════════════════════════════════════════════════════════════════════

ALLOWED_EXTENSIONS = {
    'image': {'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'},
    'document': {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'odt'},
    'audio': {'mp3', 'wav', 'ogg', 'm4a'},
    'video': {'mp4', 'webm', 'avi', 'mov'}
}

MAX_FILE_SIZE = {
    'image': 10 * 1024 * 1024,      # 10 MB
    'document': 50 * 1024 * 1024,    # 50 MB
    'audio': 20 * 1024 * 1024,       # 20 MB
    'video': 100 * 1024 * 1024       # 100 MB
}


def get_kb_upload_path(department_id: int, article_id: int = None) -> Path:
    """
    Genera il percorso di upload per i file KB.
    """
    # Usa percorso assoluto basato su root_path dell'app
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    if not Path(upload_folder).is_absolute():
        upload_folder = Path(current_app.root_path) / upload_folder
    else:
        upload_folder = Path(upload_folder)
    
    base_path = upload_folder / 'knowledge_base'
    dept_path = base_path / f'dept_{department_id}'
    
    if article_id:
        return dept_path / f'article_{article_id}'
    
    return dept_path


def allowed_file(filename: str) -> Tuple[bool, Optional[str]]:
    """
    Verifica se il file è permesso e ritorna il tipo.
    """
    if '.' not in filename:
        return False, None
    
    ext = filename.rsplit('.', 1)[1].lower()
    
    for file_type, extensions in ALLOWED_EXTENSIONS.items():
        if ext in extensions:
            return True, file_type
    
    return False, None


def generate_unique_filename(original_filename: str) -> str:
    """
    Genera un nome file unico mantenendo l'estensione.
    """
    name, ext = os.path.splitext(secure_filename(original_filename))
    unique_id = secrets.token_hex(8)
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    return f"{timestamp}_{unique_id}_{name}{ext}"


def create_thumbnail(image_path: Path, thumb_path: Path, size: Tuple[int, int] = (300, 300)):
    """
    Crea una thumbnail per un'immagine.
    """
    try:
        with Image.open(image_path) as img:
            # Converti RGBA in RGB se necessario
            if img.mode in ('RGBA', 'LA', 'P'):
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = rgb_img
            
            img.thumbnail(size, Image.Resampling.LANCZOS)
            img.save(thumb_path, 'JPEG', quality=85, optimize=True)
            return True
    except Exception as e:
        current_app.logger.error(f"Errore creazione thumbnail: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════
#                              STORAGE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

def check_storage_quota(department_id: int, file_size: int) -> Tuple[bool, str]:
    """
    Verifica se c'è spazio disponibile per l'upload.
    """
    quota = KBDepartmentQuota.query.filter_by(department_id=department_id).first()
    
    if not quota:
        # Crea quota default se non esiste
        quota = KBDepartmentQuota(
            department_id=department_id,
            quota_bytes=2 * 1024 * 1024 * 1024  # 2GB default
        )
        db.session.add(quota)
        db.session.commit()
    
    if not quota.can_upload(file_size):
        available_mb = quota.available_bytes / (1024 * 1024)
        needed_mb = file_size / (1024 * 1024)
        return False, f"Spazio insufficiente. Disponibili: {available_mb:.2f}MB, Richiesti: {needed_mb:.2f}MB"
    
    return True, "OK"


def update_storage_usage(department_id: int, delta_bytes: int):
    """
    Aggiorna l'utilizzo dello storage del dipartimento.
    """
    quota = KBDepartmentQuota.query.filter_by(department_id=department_id).first()
    if quota:
        quota.update_usage(delta_bytes)
        
        # Genera alert se necessario
        if quota.is_critical and not quota.is_warning:
            create_storage_alert(department_id, 'critical', quota.usage_percentage)
        elif quota.is_warning:
            create_storage_alert(department_id, 'warning', quota.usage_percentage)
        
        db.session.commit()


def create_storage_alert(department_id: int, severity: str, usage_percentage: float):
    """
    Crea un alert per problemi di storage.
    """
    # Verifica se esiste già un alert simile non risolto
    existing = KBDepartmentAlert.query.filter_by(
        department_id=department_id,
        alert_type=KBAlertTypeEnum.storage_limit,
        is_resolved=False
    ).first()
    
    if existing:
        return
    
    alert = KBDepartmentAlert(
        department_id=department_id,
        alert_type=KBAlertTypeEnum.storage_limit,
        title=f"Limite storage {severity.upper()}",
        message=f"Lo storage del dipartimento è al {usage_percentage:.1f}% della capacità.",
        severity=severity,
        metadata={'usage_percentage': usage_percentage},
        action_url=url_for('kb.department_storage', department_id=department_id),
        auto_dismiss_at=datetime.utcnow() + timedelta(days=7)
    )
    db.session.add(alert)


# ═══════════════════════════════════════════════════════════════════════════
#                              SLUGS & URLS
# ═══════════════════════════════════════════════════════════════════════════

def generate_slug(title: str, model_class=None, exclude_id: int = None) -> str:
    """
    Genera uno slug univoco da un titolo.
    """
    import re
    from unidecode import unidecode
    
    # Converti in ASCII e lowercase
    slug = unidecode(title).lower()
    
    # Rimuovi caratteri non alfanumerici
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    
    # Sostituisci spazi con trattini
    slug = re.sub(r'[\s-]+', '-', slug)
    
    # Rimuovi trattini iniziali/finali
    slug = slug.strip('-')
    
    # Limita lunghezza
    slug = slug[:200]
    
    # Assicura unicità se model_class è fornito
    if model_class:
        original_slug = slug
        counter = 1
        
        while True:
            query = model_class.query.filter_by(slug=slug)
            if exclude_id:
                query = query.filter(model_class.id != exclude_id)
            
            if not query.first():
                break
            
            slug = f"{original_slug}-{counter}"
            counter += 1
    
    return slug


# ═══════════════════════════════════════════════════════════════════════════
#                              SEARCH & FILTERS
# ═══════════════════════════════════════════════════════════════════════════

def search_articles(query: str, department_id: int = None, limit: int = 20) -> List[KBArticle]:
    """
    Ricerca full-text negli articoli.
    """
    from corposostenibile.models import KBDocumentStatusEnum
    
    # Log della ricerca
    log_search(query, department_id)
    
    # Query base
    articles_query = KBArticle.query.filter(
        KBArticle.status == KBDocumentStatusEnum.published
    )
    
    # Filtra per dipartimento se specificato
    if department_id:
        articles_query = articles_query.filter_by(department_id=department_id)
    
    # Ricerca full-text
    if query:
        # Usa PostgreSQL full-text search
        articles_query = articles_query.filter(
            func.to_tsvector('italian', KBArticle.title + ' ' + KBArticle.content).match(query)
        )
    
    # Ordina per rilevanza e limita
    results = articles_query.order_by(
        KBArticle.is_pinned.desc(),
        KBArticle.views_count.desc()
    ).limit(limit).all()
    
    # Filtra per permessi utente
    filtered_results = [
        article for article in results 
        if article.can_view(current_user)
    ]
    
    return filtered_results


def get_popular_articles(department_id: int = None, limit: int = 10) -> List[KBArticle]:
    """
    Ottiene gli articoli più popolari.
    """
    from corposostenibile.models import KBDocumentStatusEnum
    
    query = KBArticle.query.filter(
        KBArticle.status == KBDocumentStatusEnum.published
    )
    
    if department_id:
        query = query.filter_by(department_id=department_id)
    
    return query.order_by(
        KBArticle.views_count.desc()
    ).limit(limit).all()


def get_recent_articles(department_id: int = None, limit: int = 10) -> List[KBArticle]:
    """
    Ottiene gli articoli più recenti.
    """
    from corposostenibile.models import KBDocumentStatusEnum
    
    query = KBArticle.query.filter(
        KBArticle.status == KBDocumentStatusEnum.published
    )
    
    if department_id:
        query = query.filter_by(department_id=department_id)
    
    return query.order_by(
        KBArticle.published_at.desc()
    ).limit(limit).all()


# ═══════════════════════════════════════════════════════════════════════════
#                              ANALYTICS & LOGGING
# ═══════════════════════════════════════════════════════════════════════════

def log_activity(
    action: KBActionTypeEnum,
    department_id: int,
    article_id: int = None,
    details: Dict[str, Any] = None,
    search_query: str = None
):
    """
    Registra un'attività nel log.
    """
    from flask import request
    
    # Validazione robusta del department_id
    if department_id is None:
        current_app.logger.warning(f"log_activity chiamata con department_id=None, usando department_id=0 (default)")
        department_id = 0
    
    # Verifica che il dipartimento esista
    department_exists = db.session.query(
        db.session.query(Department).filter_by(id=department_id).exists()
    ).scalar()
    
    if not department_exists:
        current_app.logger.error(f"log_activity: department_id={department_id} non esiste, usando department_id=0 (default)")
        department_id = 0
    
    try:
        log = KBActivityLog(
            department_id=department_id,
            user_id=current_user.id if current_user.is_authenticated else None,
            article_id=article_id,
            action=action,
            details=details or {},
            search_query=search_query,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string[:500] if request.user_agent else None,
            referrer=request.referrer[:500] if request.referrer else None,
            session_id=request.cookies.get('session_id')
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Errore durante log_activity: {str(e)}")
        db.session.rollback()
        # Non rilanciare l'eccezione per non interrompere il flusso principale


def log_article_view(article: KBArticle, time_spent: int = None, scroll_depth: int = None):
    """
    Registra la visualizzazione di un articolo.
    """
    from flask import request
    from corposostenibile.models import KBArticleView
    
    # Aggiorna contatori (gestisce valori None)
    if article.views_count is None:
        article.views_count = 0
    article.views_count += 1
    
    # Aggiorna analytics
    if not article.analytics:
        article.analytics = KBAnalytics(
            article_id=article.id,
            department_id=article.department_id
        )
    
    # Gestisce valori None anche per analytics
    if article.analytics.views_count is None:
        article.analytics.views_count = 0
    article.analytics.views_count += 1
    
    # Registra view dettagliata
    view = KBArticleView(
        article_id=article.id,
        user_id=current_user.id if current_user.is_authenticated else None,
        time_spent_seconds=time_spent,
        scroll_depth=scroll_depth,
        referrer_type=get_referrer_type(request.referrer),
        device_type=get_device_type(request.user_agent),
        browser=get_browser(request.user_agent),
        session_id=request.cookies.get('session_id')
    )
    
    db.session.add(view)
    db.session.commit()
    
    # Log activity
    log_activity(
        KBActionTypeEnum.view,
        article.department_id,
        article.id,
        {'time_spent': time_spent, 'scroll_depth': scroll_depth}
    )


def log_search(query: str, department_id: int = None):
    """
    Registra una ricerca.
    """
    from corposostenibile.models import KBSearchLog
    
    log = KBSearchLog(
        query=query,
        department_id=department_id,
        user_id=current_user.id if current_user.is_authenticated else None
    )
    db.session.add(log)
    db.session.commit()


def get_referrer_type(referrer: str) -> str:
    """
    Determina il tipo di referrer.
    """
    if not referrer:
        return 'direct'
    
    # Assicuriamoci che referrer sia una stringa
    referrer_str = str(referrer) if referrer else ''
    
    if 'google' in referrer_str or 'bing' in referrer_str:
        return 'search'
    
    server_name = current_app.config.get('SERVER_NAME')
    if server_name and server_name in referrer_str:
        return 'internal'
    
    return 'external'


def get_device_type(user_agent) -> str:
    """
    Determina il tipo di dispositivo.
    """
    if not user_agent:
        return 'unknown'
    
    # Assicuriamoci che user_agent sia una stringa
    ua_string = str(user_agent).lower() if user_agent else ''
    
    if 'mobile' in ua_string or 'android' in ua_string:
        return 'mobile'
    elif 'tablet' in ua_string or 'ipad' in ua_string:
        return 'tablet'
    
    return 'desktop'


def get_browser(user_agent) -> str:
    """
    Determina il browser.
    """
    if not user_agent:
        return 'unknown'
    
    # Assicuriamoci che user_agent sia una stringa
    ua_string = str(user_agent).lower() if user_agent else ''
    
    browsers = {
        'chrome': 'Chrome',
        'firefox': 'Firefox',
        'safari': 'Safari',
        'edge': 'Edge',
        'opera': 'Opera'
    }
    
    for key, name in browsers.items():
        if key in ua_string:
            return name
    
    return 'other'


# ═══════════════════════════════════════════════════════════════════════════
#                              ALERTS & NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════

def check_outdated_articles(department_id: int):
    """
    Verifica articoli obsoleti e genera alert.
    """
    from corposostenibile.models import KBDocumentStatusEnum
    
    # Trova articoli non aggiornati da oltre 6 mesi
    six_months_ago = datetime.utcnow() - timedelta(days=180)
    
    outdated = KBArticle.query.filter(
        KBArticle.department_id == department_id,
        KBArticle.status == KBDocumentStatusEnum.published,
        KBArticle.updated_at < six_months_ago
    ).count()
    
    if outdated > 0:
        alert = KBDepartmentAlert(
            department_id=department_id,
            alert_type=KBAlertTypeEnum.outdated_docs,
            title=f"{outdated} documenti obsoleti",
            message=f"Ci sono {outdated} documenti che non vengono aggiornati da oltre 6 mesi.",
            severity='warning',
            metadata={'count': outdated},
            action_url=url_for('kb.department_outdated', department_id=department_id),
            auto_dismiss_at=datetime.utcnow() + timedelta(days=30)
        )
        db.session.add(alert)
        db.session.commit()


def get_department_stats(department_id: int) -> Dict[str, Any]:
    """
    Ottiene statistiche complete del dipartimento per dashboard.
    """
    from corposostenibile.models import KBDocumentStatusEnum
    from sqlalchemy import extract
    
    # Articoli
    total_articles = KBArticle.query.filter_by(department_id=department_id).count()
    published_articles = KBArticle.query.filter_by(
        department_id=department_id,
        status=KBDocumentStatusEnum.published
    ).count()
    
    # Views totali
    total_views = db.session.query(func.sum(KBArticle.views_count)).filter_by(
        department_id=department_id
    ).scalar() or 0
    
    # Storage
    quota = KBDepartmentQuota.query.filter_by(department_id=department_id).first()
    
    # Attività ultimi 30 giorni
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_activity = KBActivityLog.query.filter(
        KBActivityLog.department_id == department_id,
        KBActivityLog.created_at > thirty_days_ago
    ).count()
    
    # Top contributors
    top_contributors = db.session.query(
        KBArticle.author_id,
        func.count(KBArticle.id).label('article_count')
    ).filter_by(
        department_id=department_id
    ).group_by(
        KBArticle.author_id
    ).order_by(
        func.count(KBArticle.id).desc()
    ).limit(5).all()
    
    return {
        'total_articles': total_articles,
        'published_articles': published_articles,
        'draft_articles': total_articles - published_articles,
        'total_views': total_views,
        'storage_used_gb': quota.used_gb if quota else 0,
        'storage_total_gb': quota.quota_gb if quota else 2,
        'storage_percentage': quota.usage_percentage if quota else 0,
        'recent_activity': recent_activity,
        'top_contributors': top_contributors
    }


def generate_toc_from_html(html_content: str) -> List[Dict[str, Any]]:
    """
    Genera automaticamente un Table of Contents (TOC) dal contenuto HTML.
    
    Args:
        html_content (str): Contenuto HTML dell'articolo
        
    Returns:
        List[Dict]: Lista di elementi TOC con struttura gerarchica
        
    Example:
        [
            {
                'id': 'heading-1',
                'text': 'Introduzione',
                'level': 1,
                'children': [
                    {
                        'id': 'heading-1-1',
                        'text': 'Sottosezione',
                        'level': 2,
                        'children': []
                    }
                ]
            }
        ]
    """
    if not html_content:
        return []
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        if not headings:
            return []
        
        toc_items = []
        heading_counter = {}
        
        for heading in headings:
            # Estrai il testo pulito
            text = heading.get_text().strip()
            if not text:
                continue
            
            # Determina il livello (h1=1, h2=2, etc.)
            level = int(heading.name[1])
            
            # Genera ID unico se non presente
            if not heading.get('id'):
                # Crea slug dal testo
                slug = re.sub(r'[^\w\s-]', '', text.lower())
                slug = re.sub(r'[-\s]+', '-', slug).strip('-')
                
                # Gestisci duplicati
                if slug in heading_counter:
                    heading_counter[slug] += 1
                    heading_id = f"{slug}-{heading_counter[slug]}"
                else:
                    heading_counter[slug] = 0
                    heading_id = slug
                
                # Assegna l'ID al heading nell'HTML
                heading['id'] = heading_id
            else:
                heading_id = heading.get('id')
            
            toc_item = {
                'id': heading_id,
                'text': text,
                'level': level,
                'children': []
            }
            
            toc_items.append(toc_item)
        
        # Costruisci struttura gerarchica
        hierarchical_toc = _build_toc_hierarchy(toc_items)
        
        return hierarchical_toc
        
    except Exception as e:
        current_app.logger.error(f"Errore nella generazione TOC: {str(e)}")
        return []


def _build_toc_hierarchy(flat_toc: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Costruisce una struttura gerarchica dal TOC piatto.
    
    Args:
        flat_toc (List[Dict]): Lista piatta di elementi TOC
        
    Returns:
        List[Dict]: Struttura gerarchica del TOC
    """
    if not flat_toc:
        return []
    
    result = []
    stack = []
    
    for item in flat_toc:
        current_level = item['level']
        
        # Rimuovi elementi dallo stack con livello >= corrente
        while stack and stack[-1]['level'] >= current_level:
            stack.pop()
        
        if not stack:
            # Elemento di primo livello
            result.append(item)
        else:
            # Aggiungi come figlio dell'ultimo elemento nello stack
            stack[-1]['children'].append(item)
        
        # Aggiungi l'elemento corrente allo stack
        stack.append(item)
    
    return result


def update_article_html_with_toc_ids(article: KBArticle) -> str:
    """
    Aggiorna il contenuto HTML dell'articolo aggiungendo ID ai heading per il TOC.
    
    Args:
        article (KBArticle): Articolo da aggiornare
        
    Returns:
        str: HTML aggiornato con ID sui heading
    """
    if not article.content:
        return ""
    
    try:
        soup = BeautifulSoup(article.content, 'html.parser')
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        heading_counter = {}
        
        for heading in headings:
            if not heading.get('id'):
                text = heading.get_text().strip()
                if text:
                    # Crea slug dal testo
                    slug = re.sub(r'[^\w\s-]', '', text.lower())
                    slug = re.sub(r'[-\s]+', '-', slug).strip('-')
                    
                    # Gestisci duplicati
                    if slug in heading_counter:
                        heading_counter[slug] += 1
                        heading_id = f"{slug}-{heading_counter[slug]}"
                    else:
                        heading_counter[slug] = 0
                        heading_id = slug
                    
                    heading['id'] = heading_id
        
        return str(soup)
        
    except Exception as e:
        current_app.logger.error(f"Errore nell'aggiornamento HTML con TOC IDs: {str(e)}")
        return article.content


def get_toc_for_article(article: KBArticle) -> List[Dict[str, Any]]:
    """
    Ottiene il TOC per un articolo specifico.
    
    Args:
        article (KBArticle): Articolo per cui generare il TOC
        
    Returns:
        List[Dict]: Struttura TOC dell'articolo
    """
    if not article or not article.content:
        return []
    
    # Aggiorna il contenuto con ID se necessario
    updated_content = update_article_html_with_toc_ids(article)
    
    # Genera il TOC
    toc = generate_toc_from_html(updated_content)
    
    # Aggiorna il contenuto dell'articolo se è stato modificato
    if updated_content != article.content:
        try:
            article.content = updated_content
            db.session.commit()
        except Exception as e:
            current_app.logger.error(f"Errore nell'aggiornamento contenuto articolo: {str(e)}")
            db.session.rollback()
    
    return toc