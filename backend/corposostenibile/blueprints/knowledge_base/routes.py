"""
Knowledge Base Routes
=====================
Routes principali per la gestione della documentazione aziendale.
"""

from flask import render_template, request, redirect, url_for, flash, jsonify, abort, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
from sqlalchemy import or_, and_, func

from corposostenibile.extensions import db
from corposostenibile.models import (
    Department, User,
    KBArticle, KBCategory, KBAttachment, KBDepartmentQuota,
    KBAnalytics, KBActivityLog, KBDepartmentAlert, KBBookmark, KBComment,
    KBDocumentStatusEnum, KBVisibilityEnum, KBActionTypeEnum
)

from . import bp
from .permissions import (
    kb_admin_required, department_head_required,
    article_edit_permission_required, article_view_permission_required,
    can_create_article, can_edit_article, can_view_article,
    can_manage_categories, can_view_analytics
)
from .utils import (
    generate_slug, search_articles, get_popular_articles,
    get_recent_articles, log_activity, log_article_view,
    get_department_stats, check_storage_quota, update_storage_usage,
    allowed_file, generate_unique_filename, get_kb_upload_path,
    get_toc_for_article
)
from .forms import ArticleForm, CategoryForm, SearchForm


# ═══════════════════════════════════════════════════════════════════════════
#                              MAIN VIEWS
# ═══════════════════════════════════════════════════════════════════════════

@bp.route('/test-modal')
@login_required
def test_modal():
    """Test modal functionality."""
    return render_template('kb/test_modal.html')

@bp.route('/')
@login_required
def index():
    """Dashboard principale Knowledge Base."""
    # Ottieni TUTTI i dipartimenti (con o senza articoli)
    departments = Department.query.order_by(Department.name).all()
    
    # Aggiungi conteggi per ogni dipartimento
    for dept in departments:
        dept.articles_count = KBArticle.query.filter_by(
            department_id=dept.id,
            status=KBDocumentStatusEnum.published
        ).count()
        dept.categories_count = KBCategory.query.filter_by(
            department_id=dept.id,
            is_active=True
        ).count()
    
    # Statistiche generali
    stats = {
        'total_articles': KBArticle.query.filter_by(
            status=KBDocumentStatusEnum.published
        ).count(),
        'total_categories': KBCategory.query.filter_by(is_active=True).count(),
        'departments_count': len(departments),
        'recent_articles': get_recent_articles(limit=5),
        'popular_articles': get_popular_articles(limit=5)
    }
    
    # Articoli in evidenza
    featured_articles = KBArticle.query.filter_by(
        status=KBDocumentStatusEnum.published,
        is_featured=True
    ).order_by(KBArticle.updated_at.desc()).limit(6).all()
    
    # Filtra articoli per permessi utente
    featured_articles = [a for a in featured_articles if a.can_view(current_user)]
    
    # I miei bookmark
    my_bookmarks = []
    if current_user.is_authenticated:
        my_bookmarks = KBBookmark.query.filter_by(
            user_id=current_user.id
        ).join(KBArticle).order_by(
            KBBookmark.created_at.desc()
        ).limit(5).all()
    
    # Log attività
    log_activity(
        KBActionTypeEnum.view,
        current_user.department_id if current_user.department_id else 0,
        details={'page': 'index'}
    )
    
    return render_template(
        'kb/index.html',
        departments=departments,
        stats=stats,
        featured_articles=featured_articles,
        my_bookmarks=my_bookmarks
    )


@bp.route('/department/<int:department_id>')
@login_required
def department_view(department_id):
    """Vista documenti di un dipartimento."""
    department = Department.query.get_or_404(department_id)
    
    # Categorie del dipartimento (tutte, incluse sottocategorie)
    categories = KBCategory.query.filter_by(
        department_id=department_id,
        is_active=True
    ).order_by(KBCategory.order_index, KBCategory.name).all()
    
    # Filtri
    category_id = request.args.get('category', type=int)
    visibility = request.args.get('visibility')
    status = request.args.get('status')
    search_query = request.args.get('q')
    
    # Query articoli
    articles_query = KBArticle.query.filter_by(department_id=department_id)
    
    # Applica filtri
    if category_id:
        articles_query = articles_query.filter_by(category_id=category_id)
    
    if visibility:
        articles_query = articles_query.filter_by(visibility=visibility)
    
    # Filtro status (solo HEAD/admin vedono bozze)
    if status and can_manage_categories(department_id):
        # Se è specificato uno status, filtra per quello
        articles_query = articles_query.filter_by(status=status)
    elif can_manage_categories(department_id):
        # Admin/Head vedono TUTTI gli articoli (published + draft)
        pass  # Non applica filtro status
    else:
        # Utenti normali vedono solo published
        articles_query = articles_query.filter_by(
            status=KBDocumentStatusEnum.published
        )
    
    # Ricerca
    if search_query:
        articles_query = articles_query.filter(
            or_(
                KBArticle.title.ilike(f'%{search_query}%'),
                KBArticle.summary.ilike(f'%{search_query}%'),
                KBArticle.content.ilike(f'%{search_query}%')
            )
        )
    
    # Paginazione
    page = request.args.get('page', 1, type=int)
    per_page = 20
    articles = articles_query.order_by(
        KBArticle.is_pinned.desc(),
        KBArticle.published_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    # Filtra per permessi
    articles.items = [a for a in articles.items if a.can_view(current_user)]
    
    # Statistiche dipartimento (solo per HEAD)
    dept_stats = None
    alerts = []
    if can_view_analytics(department_id):
        dept_stats = get_department_stats(department_id)
        # Alert non letti
        alerts = KBDepartmentAlert.query.filter_by(
            department_id=department_id,
            is_read=False,
            is_resolved=False
        ).order_by(KBDepartmentAlert.created_at.desc()).limit(5).all()
    
    # Quota storage
    quota = KBDepartmentQuota.query.filter_by(department_id=department_id).first()
    
    # Log attività
    log_activity(
        KBActionTypeEnum.view,
        department_id,
        details={'page': 'department', 'filters': request.args.to_dict()}
    )
    
    # Conta articoli per categoria
    category_articles_count = {}
    for cat in categories:
        if can_manage_categories(department_id):
            # Admin/Head vedono il count di TUTTI gli articoli
            count = KBArticle.query.filter_by(category_id=cat.id).count()
        else:
            # Utenti normali vedono solo published
            count = KBArticle.query.filter_by(
                category_id=cat.id,
                status=KBDocumentStatusEnum.published
            ).count()
        category_articles_count[cat.id] = count
    
    # Statistiche base
    stats = {
        'total_articles': KBArticle.query.filter_by(
            department_id=department_id,
            status=KBDocumentStatusEnum.published
        ).count(),
        'total_categories': len(categories),
        'total_views': db.session.query(db.func.sum(KBArticle.views_count)).filter_by(
            department_id=department_id
        ).scalar() or 0,
        'storage_used_mb': int((quota.used_bytes / (1024 * 1024)) if quota else 0)
    }
    
    # Ottieni la categoria corrente se specificata
    current_category = None
    if category_id:
        current_category = KBCategory.query.get(category_id)
    
    return render_template(
        'kb/department.html',
        department=department,
        categories=categories,
        articles=articles,
        current_category=current_category,
        category_articles_count=category_articles_count,
        stats=stats,
        dept_stats=dept_stats,
        alerts=alerts,
        quota=quota,
        can_create=can_create_article(department_id),
        can_manage=can_manage_categories(department_id)
    )


@bp.route('/article/<int:article_id>')
@login_required
@article_view_permission_required
def article_view(article_id, article=None):
    """Vista dettagliata articolo."""
    # article viene passato dal decoratore
    
    # Incrementa view count
    log_article_view(article)
    
    # Genera TOC automaticamente dal contenuto
    toc_items = get_toc_for_article(article)
    
    # Articoli correlati (stessa categoria)
    related_articles = []
    if article.category:
        related_articles = KBArticle.query.filter(
            KBArticle.category_id == article.category_id,
            KBArticle.id != article.id,
            KBArticle.status == KBDocumentStatusEnum.published
        ).order_by(func.random()).limit(4).all()
        related_articles = [a for a in related_articles if a.can_view(current_user)]
    
    # Verifica se è nei bookmark
    is_bookmarked = False
    if current_user.is_authenticated:
        is_bookmarked = KBBookmark.query.filter_by(
            user_id=current_user.id,
            article_id=article_id
        ).first() is not None
    
    # Breadcrumb
    breadcrumb = []
    if article.category:
        cat = article.category
        while cat:
            breadcrumb.insert(0, cat)
            cat = cat.parent
    
    return render_template(
        'kb/article.html',
        article=article,
        related_articles=related_articles,
        is_bookmarked=is_bookmarked,
        breadcrumb=breadcrumb,
        can_edit=can_edit_article(article),
        toc_items=toc_items
    )


# ═══════════════════════════════════════════════════════════════════════════
#                              EDITOR VIEWS
# ═══════════════════════════════════════════════════════════════════════════

@bp.route('/editor')
@login_required
def editor():
    """Route generale per l'editor - reindirizza al dipartimento dell'utente."""
    if current_user.department_id:
        # Se l'utente ha un dipartimento, reindirizza all'editor per quel dipartimento
        return redirect(url_for('kb.article_create', department_id=current_user.department_id))
    else:
        # Se non ha un dipartimento, mostra la lista dei dipartimenti disponibili
        departments = Department.query.order_by(Department.name).all()
        # Filtra solo i dipartimenti dove l'utente può creare articoli
        available_departments = [dept for dept in departments if can_create_article(dept.id)]
        
        if len(available_departments) == 1:
            # Se c'è solo un dipartimento disponibile, reindirizza direttamente
            return redirect(url_for('kb.article_create', department_id=available_departments[0].id))
        elif len(available_departments) == 0:
            # Se non può creare articoli in nessun dipartimento
            flash('Non hai i permessi per creare articoli in nessun dipartimento.', 'warning')
            return redirect(url_for('kb.index'))
        else:
            # Mostra la selezione del dipartimento
            return render_template('kb/editor_select_department.html', 
                                 departments=available_departments)

@bp.route('/editor/new/<int:department_id>', methods=['GET', 'POST'])
@login_required
def article_create(department_id):
    """Crea nuovo articolo."""
    department = Department.query.get_or_404(department_id)
    
    # Verifica permessi
    if not can_create_article(department_id):
        flash('Non hai i permessi per creare articoli in questo dipartimento.', 'danger')
        return redirect(url_for('kb.department_view', department_id=department_id))
    
    form = ArticleForm()
    
    # Popola categorie
    form.category_id.choices = [('', '-- Nessuna categoria --')] + [
        (c.id, c.full_path) for c in KBCategory.query.filter_by(
            department_id=department_id,
            is_active=True
        ).order_by(KBCategory.name).all()
    ]
    
    # Debug: Log form data and validation errors
    if request.method == 'POST':
        print(f"DEBUG: Form data received: {request.form}")
        print(f"DEBUG: Form validation result: {form.validate()}")
        print(f"DEBUG: Form errors: {form.errors}")
        
    if form.validate_on_submit():
        # Crea articolo
        article = KBArticle(
            department_id=department_id,
            author_id=current_user.id,
            title=form.title.data,
            slug=generate_slug(form.title.data, KBArticle),
            summary=form.summary.data,
            content=form.content.data,
            category_id=form.category_id.data if form.category_id.data else None,
            status=form.status.data,
            visibility=form.visibility.data,
            meta_keywords=form.meta_keywords.data,
            tags=form.tags.data.split(',') if form.tags.data else [],
            is_featured=form.is_featured.data,
            is_pinned=form.is_pinned.data,
            allow_comments=form.allow_comments.data,
            require_acknowledgment=form.require_acknowledgment.data,
            template_type=form.template_type.data
        )
        
        # Se pubblicato, imposta data
        if article.status == KBDocumentStatusEnum.published:
            article.published_at = datetime.utcnow()
        
        db.session.add(article)
        db.session.flush()  # Per ottenere l'ID
        
        # Crea analytics
        analytics = KBAnalytics(
            article_id=article.id,
            department_id=department_id
        )
        db.session.add(analytics)
        
        # Log attività
        log_activity(
            KBActionTypeEnum.create,
            department_id,
            article.id,
            {'title': article.title, 'status': article.status}
        )
        
        db.session.commit()
        
        # Gestione upload allegati
        if 'attachments' in request.files:
            files = request.files.getlist('attachments')
            for file in files:
                if file and file.filename:
                    # Verifica tipo file
                    is_allowed, file_type = allowed_file(file.filename)
                    if is_allowed:
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
                        
                        if file_size <= max_size:
                            # Verifica quota storage
                            can_upload, message = check_storage_quota(department_id, file_size)
                            if can_upload:
                                # Genera nome file unico
                                original_filename = secure_filename(file.filename)
                                unique_filename = generate_unique_filename(original_filename)
                                
                                # Crea percorso upload
                                upload_path = get_kb_upload_path(department_id, article.id)
                                upload_path.mkdir(parents=True, exist_ok=True)
                                
                                file_path = upload_path / unique_filename
                                
                                # Salva file
                                file.save(str(file_path))
                                
                                # Crea record attachment
                                attachment = KBAttachment(
                                    article_id=article.id,
                                    filename=unique_filename,
                                    original_filename=original_filename,
                                    file_path=str(file_path),
                                    file_size=file_size,
                                    mime_type=file.content_type,
                                    attachment_type=file_type,
                                    uploaded_by_id=current_user.id
                                )
                                
                                db.session.add(attachment)
                                
                                # Aggiorna quota storage
                                update_storage_usage(department_id, file_size)
            
            db.session.commit()
        
        flash('Articolo creato con successo!', 'success')
        
        # Redirect alla visualizzazione dell'articolo
        return redirect(url_for('kb.article_view', article_id=article.id))
    
    return render_template(
        'kb/editor.html',
        form=form,
        department=department,
        is_new=True
    )


@bp.route('/editor/<int:article_id>', methods=['GET', 'POST'])
@login_required
@article_edit_permission_required
def article_edit(article_id, article=None):
    """Modifica articolo esistente."""
    form = ArticleForm(obj=article)
    
    # Popola categorie
    form.category_id.choices = [('', '-- Nessuna categoria --')] + [
        (c.id, c.full_path) for c in KBCategory.query.filter_by(
            department_id=article.department_id,
            is_active=True
        ).order_by(KBCategory.name).all()
    ]
    
    if form.validate_on_submit():
        # Aggiorna articolo
        article.title = form.title.data
        article.slug = generate_slug(form.title.data, KBArticle, article.id)
        article.summary = form.summary.data
        article.content = form.content.data
        article.category_id = form.category_id.data if form.category_id.data else None
        article.status = form.status.data
        article.visibility = form.visibility.data
        article.meta_keywords = form.meta_keywords.data
        article.tags = form.tags.data.split(',') if form.tags.data else []
        article.is_featured = form.is_featured.data
        article.is_pinned = form.is_pinned.data
        article.allow_comments = form.allow_comments.data
        article.require_acknowledgment = form.require_acknowledgment.data
        article.template_type = form.template_type.data
        article.last_editor_id = current_user.id
        article.updated_at = datetime.utcnow()
        
        # Se pubblicato per la prima volta
        if article.status == KBDocumentStatusEnum.published and not article.published_at:
            article.published_at = datetime.utcnow()
        
        # Log attività
        log_activity(
            KBActionTypeEnum.edit,
            article.department_id,
            article.id,
            {'title': article.title, 'status': article.status}
        )
        
        db.session.commit()
        
        # Gestione upload allegati
        if 'attachments' in request.files:
            files = request.files.getlist('attachments')
            for file in files:
                if file and file.filename:
                    # Verifica tipo file
                    is_allowed, file_type = allowed_file(file.filename)
                    if is_allowed:
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
                        
                        if file_size <= max_size:
                            # Verifica quota storage
                            can_upload, message = check_storage_quota(article.department_id, file_size)
                            if can_upload:
                                # Genera nome file unico
                                original_filename = secure_filename(file.filename)
                                unique_filename = generate_unique_filename(original_filename)
                                
                                # Crea percorso upload
                                upload_path = get_kb_upload_path(article.department_id, article.id)
                                upload_path.mkdir(parents=True, exist_ok=True)
                                
                                file_path = upload_path / unique_filename
                                
                                # Salva file
                                file.save(str(file_path))
                                
                                # Crea record attachment
                                attachment = KBAttachment(
                                    article_id=article.id,
                                    filename=unique_filename,
                                    original_filename=original_filename,
                                    file_path=str(file_path),
                                    file_size=file_size,
                                    mime_type=file.content_type,
                                    attachment_type=file_type,
                                    uploaded_by_id=current_user.id
                                )
                                
                                db.session.add(attachment)
                                
                                # Aggiorna quota storage
                                update_storage_usage(article.department_id, file_size)
            
            db.session.commit()
        
        flash('Articolo aggiornato con successo!', 'success')
        return redirect(url_for('kb.article_view', article_id=article.id))
    
    # Pre-popola tags
    if article.tags:
        form.tags.data = ', '.join(article.tags)
    
    return render_template(
        'kb/editor.html',
        form=form,
        article=article,
        department=article.department,
        is_new=False
    )


@bp.route('/article/<int:article_id>/delete', methods=['POST'])
@login_required
@article_edit_permission_required
def article_delete(article_id, article=None):
    """Elimina articolo."""
    # Log attività
    log_activity(
        KBActionTypeEnum.delete,
        article.department_id,
        article.id,
        {'title': article.title}
    )
    
    department_id = article.department_id
    
    # Elimina file allegati dal filesystem
    for attachment in article.attachments:
        try:
            if os.path.exists(attachment.file_path):
                os.remove(attachment.file_path)
            if attachment.thumbnail_path and os.path.exists(attachment.thumbnail_path):
                os.remove(attachment.thumbnail_path)
        except:
            pass
    
    # Aggiorna quota storage
    total_size = sum(a.file_size for a in article.attachments)
    if total_size > 0:
        update_storage_usage(department_id, -total_size)

    # Elimina manualmente i bookmarks (per evitare constraint violation)
    from corposostenibile.models import KBBookmark
    KBBookmark.query.filter_by(article_id=article.id).delete()

    # Elimina articolo (cascade elimina attachments, analytics, etc)
    db.session.delete(article)
    db.session.commit()
    
    flash('Articolo eliminato con successo.', 'success')
    return redirect(url_for('kb.department_view', department_id=department_id))


# ═══════════════════════════════════════════════════════════════════════════
#                              SEARCH & FILTERS
# ═══════════════════════════════════════════════════════════════════════════

@bp.route('/search')
@login_required
def search():
    """Ricerca globale nella KB."""
    query = request.args.get('q', '')
    department_id = request.args.get('department', type=int)
    category_id = request.args.get('category', type=int)
    
    results = []
    if query:
        # Ricerca articoli
        results = search_articles(query, department_id, limit=50)
        
        # Log ricerca
        from corposostenibile.models import KBSearchLog
        search_log = KBSearchLog(
            query=query,
            results_count=len(results),
            department_id=department_id,
            user_id=current_user.id
        )
        db.session.add(search_log)
        db.session.commit()
    
    # Suggerimenti di ricerca (query frequenti)
    from corposostenibile.models import KBSearchLog
    popular_searches = db.session.query(
        KBSearchLog.query,
        func.count(KBSearchLog.id).label('count')
    ).group_by(
        KBSearchLog.query
    ).order_by(
        func.count(KBSearchLog.id).desc()
    ).limit(10).all()
    
    return render_template(
        'kb/search.html',
        query=query,
        results=results,
        department_id=department_id,
        category_id=category_id,
        popular_searches=popular_searches
    )


# ═══════════════════════════════════════════════════════════════════════════
#                              CATEGORIES MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

@bp.route('/department/<int:department_id>/categories')
@login_required
@department_head_required
def categories_manage(department_id):
    """Gestione categorie dipartimento."""
    department = Department.query.get_or_404(department_id)
    
    # Tutte le categorie (per mostrare anche le sottocategorie)
    categories = KBCategory.query.filter_by(
        department_id=department_id
    ).order_by(KBCategory.order_index, KBCategory.name).all()
    
    # Quota storage
    quota = KBDepartmentQuota.query.filter_by(department_id=department_id).first()
    
    # Statistiche
    stats = {
        'total_articles': KBArticle.query.filter_by(
            department_id=department_id,
            status=KBDocumentStatusEnum.published
        ).count()
    }
    
    return render_template(
        'kb/categories.html',
        department=department,
        categories=categories,
        quota=quota,
        stats=stats
    )


@bp.route('/department/<int:department_id>/category/new', methods=['GET', 'POST'])
@login_required
@department_head_required
def category_create(department_id):
    """Crea nuova categoria."""
    department = Department.query.get_or_404(department_id)
    form = CategoryForm()
    
    # Popola parent categories
    form.parent_id.choices = [('', '-- Categoria principale --')] + [
        (c.id, c.full_path) for c in KBCategory.query.filter_by(
            department_id=department_id,
            is_active=True
        ).order_by(KBCategory.name).all()
    ]
    
    if form.validate_on_submit():
        category = KBCategory(
            department_id=department_id,
            parent_id=form.parent_id.data if form.parent_id.data else None,
            name=form.name.data,
            slug=generate_slug(form.name.data, KBCategory),
            description=form.description.data,
            icon=form.icon.data,
            color=form.color.data,
            order_index=form.order_index.data,
            is_active=form.is_active.data
        )
        
        db.session.add(category)
        db.session.commit()
        
        flash('Categoria creata con successo!', 'success')
        return redirect(url_for('kb.categories_manage', department_id=department_id))
    
    return render_template(
        'kb/category_form.html',
        form=form,
        department=department,
        is_new=True
    )


# ═══════════════════════════════════════════════════════════════════════════
#                              ANALYTICS DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════

@bp.route('/department/<int:department_id>/analytics')
@login_required
@department_head_required
def analytics_dashboard(department_id):
    """Dashboard analytics per HEAD dipartimento."""
    department = Department.query.get_or_404(department_id)
    
    # Periodo di analisi
    period = request.args.get('period', '30')  # giorni
    if period == '7':
        start_date = datetime.utcnow() - timedelta(days=7)
    elif period == '30':
        start_date = datetime.utcnow() - timedelta(days=30)
    elif period == '90':
        start_date = datetime.utcnow() - timedelta(days=90)
    else:
        start_date = datetime.utcnow() - timedelta(days=30)
    
    # Statistiche generali
    stats = get_department_stats(department_id)
    
    # Top articoli per views
    from corposostenible.models import KBArticleView
    top_articles = db.session.query(
        KBArticle,
        func.count(KBArticleView.id).label('view_count')
    ).join(
        KBArticleView, KBArticle.id == KBArticleView.article_id
    ).filter(
        KBArticle.department_id == department_id,
        KBArticleView.viewed_at >= start_date
    ).group_by(
        KBArticle.id
    ).order_by(
        func.count(KBArticleView.id).desc()
    ).limit(10).all()
    
    # Ricerche più frequenti
    from corposostenible.models import KBSearchLog
    top_searches = db.session.query(
        KBSearchLog.query,
        func.count(KBSearchLog.id).label('count')
    ).filter(
        KBSearchLog.department_id == department_id,
        KBSearchLog.created_at >= start_date
    ).group_by(
        KBSearchLog.query
    ).order_by(
        func.count(KBSearchLog.id).desc()
    ).limit(20).all()
    
    # Attività per giorno
    daily_activity = db.session.query(
        func.date(KBActivityLog.created_at).label('date'),
        func.count(KBActivityLog.id).label('count')
    ).filter(
        KBActivityLog.department_id == department_id,
        KBActivityLog.created_at >= start_date
    ).group_by(
        func.date(KBActivityLog.created_at)
    ).order_by(
        func.date(KBActivityLog.created_at)
    ).all()
    
    # Alert attivi
    alerts = KBDepartmentAlert.query.filter_by(
        department_id=department_id,
        is_resolved=False
    ).order_by(
        KBDepartmentAlert.severity.desc(),
        KBDepartmentAlert.created_at.desc()
    ).all()
    
    # Quota storage
    quota = KBDepartmentQuota.query.filter_by(department_id=department_id).first()
    
    # Articoli che necessitano revisione
    outdated_articles = KBArticle.query.filter(
        KBArticle.department_id == department_id,
        KBArticle.status == KBDocumentStatusEnum.published,
        KBArticle.updated_at < (datetime.utcnow() - timedelta(days=180))
    ).order_by(KBArticle.updated_at).limit(10).all()
    
    return render_template(
        'kb/analytics.html',
        department=department,
        stats=stats,
        top_articles=top_articles,
        top_searches=top_searches,
        daily_activity=daily_activity,
        alerts=alerts,
        quota=quota,
        outdated_articles=outdated_articles,
        period=period
    )


# ═══════════════════════════════════════════════════════════════════════════
#                              BOOKMARKS
# ═══════════════════════════════════════════════════════════════════════════

@bp.route('/bookmarks')
@login_required
def my_bookmarks():
    """I miei segnalibri."""
    bookmarks = KBBookmark.query.filter_by(
        user_id=current_user.id
    ).join(KBArticle).order_by(
        KBBookmark.created_at.desc()
    ).all()
    
    return render_template(
        'kb/bookmarks.html',
        bookmarks=bookmarks
    )


@bp.route('/article/<int:article_id>/bookmark', methods=['POST'])
@login_required
def toggle_bookmark(article_id):
    """Aggiungi/rimuovi bookmark."""
    article = KBArticle.query.get_or_404(article_id)
    
    if not article.can_view(current_user):
        return jsonify({'error': 'Non autorizzato'}), 403
    
    bookmark = KBBookmark.query.filter_by(
        user_id=current_user.id,
        article_id=article_id
    ).first()
    
    if bookmark:
        db.session.delete(bookmark)
        db.session.commit()
        return jsonify({'bookmarked': False, 'message': 'Rimosso dai preferiti'})
    else:
        bookmark = KBBookmark(
            user_id=current_user.id,
            article_id=article_id
        )
        db.session.add(bookmark)
        
        # Aggiorna analytics
        if article.analytics:
            article.analytics.bookmarks_count += 1
        
        log_activity(
            KBActionTypeEnum.bookmark,
            article.department_id,
            article_id
        )
        
        db.session.commit()
        return jsonify({'bookmarked': True, 'message': 'Aggiunto ai preferiti'})


# ═══════════════════════════════════════════════════════════════════════════
#                              COMMENTS
# ═══════════════════════════════════════════════════════════════════════════

@bp.route('/article/<int:article_id>/comment', methods=['POST'])
@login_required
@article_view_permission_required
def add_comment(article_id, article=None):
    """Aggiungi commento a un articolo."""
    # Verifica che i commenti siano abilitati
    if not article.allow_comments:
        flash('I commenti non sono abilitati per questo articolo.', 'warning')
        return redirect(url_for('kb.article_view', article_id=article_id))
    
    content = request.form.get('content', '').strip()
    if not content:
        flash('Il commento non può essere vuoto.', 'danger')
        return redirect(url_for('kb.article_view', article_id=article_id))
    
    # Crea il commento
    comment = KBComment(
        article_id=article_id,
        author_id=current_user.id,
        content=content
    )
    
    db.session.add(comment)
    
    # Aggiorna contatore commenti nell'analytics
    if article.analytics:
        article.analytics.comments_count += 1
    
    # Log attività
    log_activity(
        KBActionTypeEnum.comment,
        article.department_id,
        article_id,
        {'comment_length': len(content)}
    )
    
    db.session.commit()
    
    flash('Commento aggiunto con successo!', 'success')
    return redirect(url_for('kb.article_view', article_id=article_id) + '#comments')

