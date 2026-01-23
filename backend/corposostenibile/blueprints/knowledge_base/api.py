"""
Knowledge Base API
==================
API endpoints per funzionalità AJAX/async della KB.
"""

import os
import json
from pathlib import Path
from flask import jsonify, request, abort, send_file, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from PIL import Image
from functools import wraps
from sqlalchemy import func

from corposostenibile.extensions import db
from corposostenibile.models import (
    KBArticle, KBCategory, KBAttachment, KBDepartmentQuota,
    KBAnalytics, KBActivityLog, KBArticleView,
    KBActionTypeEnum, KBDocumentStatusEnum
)

from . import bp
from .permissions import can_edit_article, can_manage_categories
from .utils import (
    allowed_file, generate_unique_filename, get_kb_upload_path,
    check_storage_quota, update_storage_usage, create_thumbnail,
    log_activity
)



# ═══════════════════════════════════════════════════════════════════════════
#                              UPLOAD API
# ═══════════════════════════════════════════════════════════════════════════

@bp.route('/api/upload/<int:article_id>', methods=['POST'])
@login_required
def api_upload_file(article_id):
    """
    Upload file per articolo.
    Supporta upload multipli e drag&drop.
    """
    article = KBArticle.query.get_or_404(article_id)
    
    # Verifica permessi
    if not can_edit_article(article):
        return jsonify({'error': 'Non autorizzato'}), 403
    
    if 'file' not in request.files:
        return jsonify({'error': 'Nessun file fornito'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Nome file vuoto'}), 400
    
    # Verifica tipo file
    is_allowed, file_type = allowed_file(file.filename)
    if not is_allowed:
        return jsonify({'error': 'Tipo file non permesso'}), 400
    
    # Verifica dimensione
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    max_size = {
        'image': 10 * 1024 * 1024,      # 10 MB
        'document': 50 * 1024 * 1024,    # 50 MB
        'audio': 20 * 1024 * 1024,       # 20 MB
        'video': 100 * 1024 * 1024       # 100 MB
    }.get(file_type, 10 * 1024 * 1024)
    
    if file_size > max_size:
        return jsonify({'error': f'File troppo grande. Max: {max_size/(1024*1024):.1f}MB'}), 400
    
    # Verifica quota storage
    can_upload, message = check_storage_quota(article.department_id, file_size)
    if not can_upload:
        return jsonify({'error': message}), 400
    
    # Genera nome file unico
    original_filename = secure_filename(file.filename)
    unique_filename = generate_unique_filename(original_filename)
    
    # Crea percorso upload
    upload_path = get_kb_upload_path(article.department_id, article_id)
    upload_path.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_path / unique_filename
    
    # Salva file
    file.save(str(file_path))
    
    # Crea thumbnail per immagini
    thumbnail_path = None
    if file_type == 'image':
        thumb_filename = f"thumb_{unique_filename}"
        thumb_path = upload_path / thumb_filename
        if create_thumbnail(file_path, thumb_path):
            thumbnail_path = str(thumb_path)
    
    # Crea record attachment
    attachment = KBAttachment(
        article_id=article_id,
        filename=unique_filename,
        original_filename=original_filename,
        file_path=str(file_path),
        file_size=file_size,
        mime_type=file.content_type,
        attachment_type=file_type,
        thumbnail_path=thumbnail_path,
        uploaded_by_id=current_user.id,
        title=request.form.get('title', original_filename),
        description=request.form.get('description'),
        alt_text=request.form.get('alt_text')
    )
    
    db.session.add(attachment)
    
    # Aggiorna quota storage
    update_storage_usage(article.department_id, file_size)
    
    # Log attività
    log_activity(
        KBActionTypeEnum.upload,
        article.department_id,
        article_id,
        {'filename': original_filename, 'size': file_size, 'type': file_type}
    )
    
    db.session.commit()
    
    # Ritorna info file
    return jsonify({
        'success': True,
        'attachment': {
            'id': attachment.id,
            'filename': attachment.original_filename,
            'size': attachment.size_formatted,
            'type': attachment.attachment_type,
            'url': f'/kb/api/attachment/{attachment.id}/download',
            'thumbnail': f'/kb/api/attachment/{attachment.id}/thumbnail' if thumbnail_path else None
        }
    })


@bp.route('/api/attachment/<int:attachment_id>/download')
@login_required
def api_download_attachment(attachment_id):
    """Download allegato."""
    attachment = KBAttachment.query.get_or_404(attachment_id)
    article = attachment.article
    
    # Verifica permessi
    if not article.can_view(current_user):
        abort(403)
    
    # Incrementa contatore download
    attachment.downloads_count += 1
    if article.analytics:
        article.analytics.downloads_count += 1
    
    # Log attività
    log_activity(
        KBActionTypeEnum.download,
        article.department_id,
        article.id,
        {'attachment_id': attachment_id, 'filename': attachment.original_filename}
    )
    
    db.session.commit()
    
    # Verifica che il file esista
    file_path = Path(attachment.file_path)
    
    # Se il percorso è relativo, prova prima dalla directory corrente del progetto
    if not file_path.is_absolute():
        # Prima prova dalla root del progetto (sopra corposostenibile/)
        project_root = Path(current_app.root_path).parent
        possible_paths = [
            project_root / file_path,  # /home/devops/corposostenibile-suite/uploads/...
            Path(current_app.root_path) / file_path,  # /home/devops/corposostenibile-suite/corposostenibile/uploads/...
            file_path  # percorso relativo corrente
        ]
        
        for p in possible_paths:
            if p.exists():
                file_path = p
                break
    
    if not file_path.exists():
        abort(404, description=f"File not found: {attachment.file_path}")
    
    return send_file(
        str(file_path),
        as_attachment=True,
        download_name=attachment.original_filename
    )


@bp.route('/api/attachment/<int:attachment_id>/thumbnail')
@login_required
def api_attachment_thumbnail(attachment_id):
    """Mostra thumbnail allegato."""
    attachment = KBAttachment.query.get_or_404(attachment_id)
    article = attachment.article
    
    # Verifica permessi
    if not article.can_view(current_user):
        abort(403)
    
    if not attachment.thumbnail_path or not os.path.exists(attachment.thumbnail_path):
        abort(404)
    
    return send_file(attachment.thumbnail_path)


@bp.route('/api/attachment/<int:attachment_id>/delete', methods=['DELETE'])
@login_required
def api_delete_attachment(attachment_id):
    """Elimina allegato."""
    attachment = KBAttachment.query.get_or_404(attachment_id)
    article = attachment.article
    
    # Verifica permessi
    if not can_edit_article(article):
        return jsonify({'error': 'Non autorizzato'}), 403
    
    # Elimina file fisici
    try:
        if os.path.exists(attachment.file_path):
            os.remove(attachment.file_path)
        if attachment.thumbnail_path and os.path.exists(attachment.thumbnail_path):
            os.remove(attachment.thumbnail_path)
    except Exception as e:
        current_app.logger.error(f"Errore eliminazione file: {e}")
    
    # Aggiorna quota storage
    update_storage_usage(article.department_id, -attachment.file_size)
    
    # Log attività
    log_activity(
        KBActionTypeEnum.delete,
        article.department_id,
        article.id,
        {'attachment_id': attachment_id, 'filename': attachment.original_filename}
    )
    
    # Elimina record
    db.session.delete(attachment)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Allegato eliminato'})


# ═══════════════════════════════════════════════════════════════════════════
#                              EDITOR API
# ═══════════════════════════════════════════════════════════════════════════

@bp.route('/api/article/<int:article_id>/autosave', methods=['POST'])
@login_required
def api_autosave(article_id):
    """
    Autosave articolo (ogni 30 secondi).
    Salva solo come bozza.
    """
    article = KBArticle.query.get_or_404(article_id)
    
    # Verifica permessi
    if not can_edit_article(article):
        return jsonify({'error': 'Non autorizzato'}), 403
    
    data = request.get_json()
    
    # Aggiorna solo contenuto (non status)
    article.title = data.get('title', article.title)
    article.summary = data.get('summary', article.summary)
    article.content = data.get('content', article.content)
    article.last_editor_id = current_user.id
    article.updated_at = datetime.utcnow()
    
    # Se era pubblicato, non cambiare status
    if article.status != KBDocumentStatusEnum.published:
        article.status = KBDocumentStatusEnum.draft
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'saved_at': datetime.utcnow().isoformat(),
        'message': 'Salvato automaticamente'
    })


@bp.route('/api/article/<int:article_id>/preview', methods=['POST'])
@login_required
def api_preview(article_id):
    """Preview articolo con contenuto temporaneo."""
    article = KBArticle.query.get_or_404(article_id)
    
    # Verifica permessi
    if not can_edit_article(article):
        return jsonify({'error': 'Non autorizzato'}), 403
    
    data = request.get_json()
    
    # Renderizza preview (senza salvare)
    from flask import render_template_string
    preview_html = render_template_string(
        data.get('content', ''),
        article=article
    )
    
    return jsonify({
        'success': True,
        'preview': preview_html
    })


@bp.route('/api/article/<int:article_id>/track-reading', methods=['POST'])
@login_required
def api_track_reading(article_id):
    """
    Traccia tempo di lettura e scroll depth.
    Chiamato via JS quando l'utente lascia la pagina.
    """
    article = KBArticle.query.get_or_404(article_id)
    
    data = request.get_json()
    time_spent = data.get('time_spent', 0)  # secondi
    scroll_depth = data.get('scroll_depth', 0)  # percentuale
    
    # Crea record view
    from corposostenible.models import KBArticleView
    view = KBArticleView(
        article_id=article_id,
        user_id=current_user.id,
        time_spent_seconds=time_spent,
        scroll_depth=scroll_depth,
        device_type=data.get('device_type', 'unknown'),
        session_id=request.cookies.get('session_id')
    )
    
    db.session.add(view)
    
    # Aggiorna analytics
    if article.analytics:
        article.analytics.avg_read_time = (
            (article.analytics.avg_read_time * article.analytics.views_count + time_spent) /
            (article.analytics.views_count + 1)
        )
        
        if scroll_depth >= 90:
            article.analytics.completion_rate = (
                (article.analytics.completion_rate * article.analytics.views_count + 1) /
                (article.analytics.views_count + 1)
            )
    
    db.session.commit()
    
    return jsonify({'success': True})


# ═══════════════════════════════════════════════════════════════════════════
#                              CATEGORIES API
# ═══════════════════════════════════════════════════════════════════════════

@bp.route('/api/test', methods=['GET', 'POST'])
@login_required
def api_test():
    """Endpoint di test."""
    return jsonify({
        'success': True,
        'message': 'API KB funziona!',
        'method': request.method,
        'user': current_user.email if current_user.is_authenticated else 'Anonymous'
    })

@bp.route('/api/categories', methods=['POST'])
@login_required
def api_create_category():
    """Crea una nuova categoria."""
    try:
        # Debug completo della richiesta
        current_app.logger.info(f"Request method: {request.method}")
        current_app.logger.info(f"Request headers: {dict(request.headers)}")
        current_app.logger.info(f"Request content type: {request.content_type}")
        current_app.logger.info(f"Request data: {request.data}")
        current_app.logger.info(f"Request form: {request.form}")
        current_app.logger.info(f"Current user: {current_user}")
        
        data = request.get_json()
        
        # Debug logging
        current_app.logger.info(f"Ricevuti dati JSON: {data}")
        
        if not data:
            current_app.logger.error("Nessun dato JSON ricevuto")
            return jsonify({'error': 'Nessun dato ricevuto'}), 400
        
        # Verifica permessi
        department_id = data.get('department_id')
        if not department_id:
            return jsonify({'error': 'department_id mancante'}), 400
        
        # Verifica che il dipartimento esista
        from corposostenibile.models import Department
        department = Department.query.get(department_id)
        if not department:
            current_app.logger.error(f"api_create_category: department_id={department_id} non esiste")
            return jsonify({'error': f'Dipartimento con ID {department_id} non trovato'}), 404
            
        if not can_manage_categories(department_id):
            return jsonify({'error': 'Non hai i permessi per gestire le categorie'}), 403
        
        # Validazione
        if not data.get('name'):
            return jsonify({'error': 'Il nome è obbligatorio'}), 400
    
        # Crea categoria
        from .utils import generate_slug
        
        category = KBCategory(
            name=data['name'],
            slug=generate_slug(data['name'], KBCategory),
            description=data.get('description'),
            department_id=department_id,
            parent_id=data.get('parent_id') if data.get('parent_id') else None,
            icon=data.get('icon'),
            color=data.get('color', '#5e72e4'),
            order_index=0
        )
        
        db.session.add(category)
        db.session.commit()
        
        # Log attività
        log_activity(
            KBActionTypeEnum.create,
            department_id,
            None,
            {'category_name': category.name, 'action': 'created_category'}
        )
        
        return jsonify({
            'success': True,
            'message': 'Categoria creata con successo',
            'category': {
                'id': category.id,
                'name': category.name
            }
        })
    
    except Exception as e:
        current_app.logger.error(f"Errore in api_create_category: {e}")
        return jsonify({'error': f'Errore interno: {str(e)}'}), 500


@bp.route('/api/categories/<int:category_id>', methods=['GET', 'PUT'])
@login_required  
def api_update_category(category_id):
    """Recupera o aggiorna una categoria esistente."""
    category = KBCategory.query.get_or_404(category_id)
    
    # Se è una GET, restituisci i dati della categoria
    if request.method == 'GET':
        # Chiunque può vedere le categorie del proprio dipartimento
        if not (current_user.is_authenticated and 
                (current_user.is_admin or 
                 current_user.department_id == category.department_id or
                 current_user.is_head(category.department_id))):
            return jsonify({'error': 'Non autorizzato'}), 403
        
        return jsonify({
            'success': True,
            'category': {
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'icon': category.icon,
                'color': category.color,
                'parent_id': category.parent_id,
                'department_id': category.department_id
            }
        })
    
    # Se è una PUT, verifica permessi di modifica
    if not can_manage_categories(category.department_id):
        return jsonify({'error': 'Non hai i permessi per gestire le categorie'}), 403
    
    data = request.get_json()
    
    # Aggiorna campi
    if 'name' in data:
        category.name = data['name']
    if 'description' in data:
        category.description = data['description']
    if 'icon' in data:
        category.icon = data['icon']
    if 'color' in data:
        category.color = data['color']
    if 'parent_id' in data:
        if data['parent_id'] and data['parent_id'] != category.id:
            category.parent_id = data['parent_id']
        elif not data['parent_id']:
            category.parent_id = None
    
    db.session.commit()
    
    # Log attività
    log_activity(
        KBActionTypeEnum.edit,
        category.department_id,
        None,
        {'category_name': category.name, 'action': 'updated_category'}
    )
    
    return jsonify({
        'success': True,
        'message': 'Categoria aggiornata con successo'
    })


@bp.route('/api/categories/<int:category_id>', methods=['DELETE'])
@login_required
def api_delete_category(category_id):
    """Elimina una categoria."""
    category = KBCategory.query.get_or_404(category_id)
    
    # Verifica permessi  
    if not can_manage_categories(category.department_id):
        return jsonify({'error': 'Non hai i permessi per gestire le categorie'}), 403
    
    # Verifica che non ci siano articoli (conta TUTTI gli articoli, non solo published)
    articles_count = KBArticle.query.filter_by(category_id=category_id).count()
    if articles_count > 0:
        return jsonify({'error': f'Impossibile eliminare: la categoria contiene {articles_count} articoli. Prima sposta o elimina gli articoli.'}), 400
    
    # Verifica che non ci siano sottocategorie
    subcategories_count = KBCategory.query.filter_by(parent_id=category_id).count()
    if subcategories_count > 0:
        return jsonify({'error': f'Impossibile eliminare: la categoria contiene {subcategories_count} sottocategorie'}), 400
    
    name = category.name
    department_id = category.department_id
    
    db.session.delete(category)
    db.session.commit()
    
    # Log attività
    log_activity(
        KBActionTypeEnum.delete,
        department_id,
        None,
        {'category_name': name, 'action': 'deleted_category'}
    )
    
    return jsonify({
        'success': True,
        'message': 'Categoria eliminata con successo'
    })


@bp.route('/api/categories/<int:department_id>/reorder', methods=['POST'])
@login_required
def api_reorder_categories(department_id):
    """Riordina categorie con drag&drop."""
    if not can_manage_categories(department_id):
        return jsonify({'error': 'Non autorizzato'}), 403
    
    data = request.get_json()
    order = data.get('order', [])
    
    for index, category_id in enumerate(order):
        category = KBCategory.query.get(category_id)
        if category and category.department_id == department_id:
            category.order_index = index
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Ordine aggiornato'})


@bp.route('/api/category/<int:category_id>/toggle', methods=['POST'])
@login_required
def api_toggle_category(category_id):
    """Attiva/disattiva categoria."""
    category = KBCategory.query.get_or_404(category_id)
    
    if not can_manage_categories(category.department_id):
        return jsonify({'error': 'Non autorizzato'}), 403
    
    category.is_active = not category.is_active
    db.session.commit()
    
    return jsonify({
        'success': True,
        'is_active': category.is_active,
        'message': 'Categoria ' + ('attivata' if category.is_active else 'disattivata')
    })


# ═══════════════════════════════════════════════════════════════════════════
#                              SEARCH API
# ═══════════════════════════════════════════════════════════════════════════

@bp.route('/api/search/suggestions')
@login_required
def api_search_suggestions():
    """
    Suggerimenti di ricerca in tempo reale.
    """
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify([])
    
    # Cerca nei titoli
    suggestions = KBArticle.query.filter(
        KBArticle.status == KBDocumentStatusEnum.published,
        KBArticle.title.ilike(f'%{query}%')
    ).limit(5).all()
    
    # Filtra per permessi
    suggestions = [s for s in suggestions if s.can_view(current_user)]
    
    results = [
        {
            'id': s.id,
            'title': s.title,
            'department': s.department.name,
            'url': f'/kb/article/{s.id}'
        }
        for s in suggestions
    ]
    
    return jsonify(results)


@bp.route('/api/article/<int:article_id>/feedback', methods=['POST'])
@login_required
def api_article_feedback(article_id):
    """Feedback utente su utilità articolo."""
    article = KBArticle.query.get_or_404(article_id)
    
    if not article.can_view(current_user):
        return jsonify({'error': 'Non autorizzato'}), 403
    
    data = request.get_json()
    helpful = data.get('helpful', True)
    
    # Aggiorna analytics
    if article.analytics:
        if helpful:
            article.analytics.helpful_votes += 1
        else:
            article.analytics.not_helpful_votes += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Grazie per il feedback!'
    })


# ═══════════════════════════════════════════════════════════════════════════
#                              STATS API
# ═══════════════════════════════════════════════════════════════════════════

@bp.route('/api/stats')
@login_required
def api_get_stats():
    """
    Statistiche generali KB per footer.
    """
    from corposostenibile.models import Department, KBCategory
    
    stats = {
        'total_articles': KBArticle.query.filter_by(
            status=KBDocumentStatusEnum.published
        ).count(),
        'total_categories': KBCategory.query.filter_by(is_active=True).count(),
        'departments_count': Department.query.count()
    }
    
    return jsonify(stats)


# ═══════════════════════════════════════════════════════════════════════════
#                              ANALYTICS API
# ═══════════════════════════════════════════════════════════════════════════

@bp.route('/api/analytics/<int:department_id>/chart/<chart_type>')
@login_required
def api_analytics_chart(department_id, chart_type):
    """
    Dati per grafici analytics dashboard.
    """
    from corposostenibile.models import Department
    from .permissions import can_view_analytics
    
    if not can_view_analytics(department_id):
        return jsonify({'error': 'Non autorizzato'}), 403
    
    # Periodo
    days = request.args.get('days', 30, type=int)
    start_date = datetime.utcnow() - timedelta(days=days)
    
    if chart_type == 'views':
        # Visualizzazioni per giorno
        from corposostenibile.models import KBArticleView
        data = db.session.query(
            func.date(KBArticleView.viewed_at).label('date'),
            func.count(KBArticleView.id).label('views')
        ).join(
            KBArticle
        ).filter(
            KBArticle.department_id == department_id,
            KBArticleView.viewed_at >= start_date
        ).group_by(
            func.date(KBArticleView.viewed_at)
        ).all()
        
        return jsonify([
            {'date': str(d.date), 'views': d.views}
            for d in data
        ])
    
    elif chart_type == 'devices':
        # Dispositivi utilizzati
        from corposostenible.models import KBArticleView
        data = db.session.query(
            KBArticleView.device_type,
            func.count(KBArticleView.id).label('count')
        ).join(
            KBArticle
        ).filter(
            KBArticle.department_id == department_id,
            KBArticleView.viewed_at >= start_date
        ).group_by(
            KBArticleView.device_type
        ).all()
        
        return jsonify([
            {'device': d.device_type or 'unknown', 'count': d.count}
            for d in data
        ])
    
    elif chart_type == 'categories':
        # Articoli per categoria
        data = db.session.query(
            KBCategory.name,
            func.count(KBArticle.id).label('count')
        ).join(
            KBArticle, KBCategory.id == KBArticle.category_id
        ).filter(
            KBCategory.department_id == department_id,
            KBArticle.status == KBDocumentStatusEnum.published
        ).group_by(
            KBCategory.id
        ).all()
        
        return jsonify([
            {'category': d.name, 'count': d.count}
            for d in data
        ])
    
    return jsonify({'error': 'Tipo grafico non valido'}), 400


# ═══════════════════════════════════════════════════════════════════════════
#                        ACKNOWLEDGMENT API
# ═══════════════════════════════════════════════════════════════════════════

@bp.route('/api/article/<int:article_id>/acknowledge', methods=['POST'])
@login_required
def api_acknowledge_reading(article_id):
    """
    Registra la conferma di lettura per un articolo.
    """
    from corposostenibile.models import KBAcknowledgment

    article = KBArticle.query.get_or_404(article_id)

    # Verifica se l'utente può vedere l'articolo
    if article.status != KBDocumentStatusEnum.published:
        return jsonify({'error': 'Articolo non pubblicato'}), 403

    # Verifica se ha già confermato
    existing = KBAcknowledgment.query.filter_by(
        article_id=article_id,
        user_id=current_user.id
    ).first()

    if existing:
        return jsonify({'error': 'Hai già confermato la lettura di questo documento'}), 400

    try:
        # Crea conferma
        acknowledgment = KBAcknowledgment(
            article_id=article_id,
            user_id=current_user.id,
            acknowledged_at=datetime.utcnow()
        )
        db.session.add(acknowledgment)
        db.session.commit()

        # Log attività (opzionale - dopo il commit)
        try:
            log_activity(
                user_id=current_user.id,
                article_id=article_id,
                action_type=KBActionTypeEnum.acknowledge,
                details=f"Confermata lettura articolo: {article.title}"
            )
        except Exception as log_error:
            current_app.logger.warning(f"Errore nel log attività: {log_error}")

        return jsonify({
            'success': True,
            'message': 'Conferma di lettura registrata con successo'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore conferma lettura: {e}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({'error': f'Errore nel salvare la conferma: {str(e)}'}), 500