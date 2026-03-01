"""
API routes JSON per le Novità — consumate dai frontend React.
Blueprint separato registrato sotto /api/news.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime

from corposostenibile.extensions import db
from corposostenibile.models import News, NewsRead
from .permissions import admin_only

news_api_bp = Blueprint('news_api', __name__, url_prefix='/api/news')


# ─── LIST ───────────────────────────────────────────────────────────

@news_api_bp.route('/list')
@login_required
def api_list():
    """Lista news pubblicate (paginata, pinned first)."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    query = News.query.filter(
        News.is_published == True,
        News.published_at <= datetime.utcnow()
    ).order_by(
        News.is_pinned.desc(),
        News.published_at.desc()
    )

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    items = []
    for n in pagination.items:
        items.append({
            'id': n.id,
            'title': n.title,
            'summary': n.summary,
            'content': n.content,
            'author': n.author.full_name if n.author else None,
            'published_at': n.published_at.isoformat() if n.published_at else None,
            'is_pinned': n.is_pinned,
            'is_read': n.is_read_by(current_user.id),
            'total_views': n.total_views,
            'cover_image_url': n.cover_image_url,
        })

    return jsonify({
        'success': True,
        'news': items,
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev,
        }
    })


# ─── LIST ALL (admin) ───────────────────────────────────────────────

@news_api_bp.route('/list-all')
@login_required
@admin_only
def api_list_all():
    """Lista TUTTE le news (anche bozze) — per admin CRUD."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    query = News.query.order_by(
        News.is_pinned.desc(),
        News.published_at.desc()
    )

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    items = []
    for n in pagination.items:
        items.append({
            'id': n.id,
            'title': n.title,
            'summary': n.summary,
            'content': n.content,
            'author': n.author.full_name if n.author else None,
            'published_at': n.published_at.isoformat() if n.published_at else None,
            'is_published': n.is_published,
            'is_pinned': n.is_pinned,
            'total_views': n.total_views,
            'cover_image_url': n.cover_image_url,
        })

    return jsonify({
        'success': True,
        'news': items,
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev,
        }
    })


# ─── DETAIL + mark-as-read ─────────────────────────────────────────

@news_api_bp.route('/<int:news_id>')
@login_required
def api_detail(news_id):
    """Dettaglio singola news + segna come letta."""
    news = News.query.get_or_404(news_id)

    if not news.is_visible and not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Not found'}), 404

    # Mark as read
    news.mark_as_read(current_user.id)
    db.session.commit()

    return jsonify({
        'success': True,
        'news': {
            'id': news.id,
            'title': news.title,
            'summary': news.summary,
            'content': news.content,
            'author': news.author.nome_cognome if news.author else None,
            'published_at': news.published_at.isoformat() if news.published_at else None,
            'is_published': news.is_published,
            'is_pinned': news.is_pinned,
            'is_read': True,
            'total_views': news.total_views,
            'cover_image_url': news.cover_image_url,
        }
    })


# ─── CREATE (admin) ────────────────────────────────────────────────

@news_api_bp.route('/create', methods=['POST'])
@login_required
@admin_only
def api_create():
    """Crea una nuova news."""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Dati mancanti'}), 400

    title = (data.get('title') or '').strip()
    content = (data.get('content') or '').strip()

    if not title or not content:
        return jsonify({'success': False, 'error': 'Titolo e contenuto sono obbligatori'}), 400

    published_at_str = data.get('published_at')
    if published_at_str:
        try:
            published_at = datetime.fromisoformat(published_at_str)
        except ValueError:
            published_at = datetime.utcnow()
    else:
        published_at = datetime.utcnow()

    news = News(
        title=title,
        summary=(data.get('summary') or '').strip() or None,
        content=content,
        is_published=data.get('is_published', True),
        is_pinned=data.get('is_pinned', False),
        published_at=published_at,
        author_id=current_user.id,
    )

    db.session.add(news)
    db.session.commit()

    return jsonify({
        'success': True,
        'news': {
            'id': news.id,
            'title': news.title,
        }
    }), 201


# ─── UPDATE (admin) ────────────────────────────────────────────────

@news_api_bp.route('/<int:news_id>', methods=['PUT'])
@login_required
@admin_only
def api_update(news_id):
    """Modifica una news esistente."""
    news = News.query.get_or_404(news_id)
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Dati mancanti'}), 400

    if 'title' in data:
        news.title = (data['title'] or '').strip()
    if 'summary' in data:
        news.summary = (data['summary'] or '').strip() or None
    if 'content' in data:
        news.content = (data['content'] or '').strip()
    if 'is_published' in data:
        news.is_published = bool(data['is_published'])
    if 'is_pinned' in data:
        news.is_pinned = bool(data['is_pinned'])
    if 'published_at' in data and data['published_at']:
        try:
            news.published_at = datetime.fromisoformat(data['published_at'])
        except ValueError:
            pass

    db.session.commit()

    return jsonify({
        'success': True,
        'news': {
            'id': news.id,
            'title': news.title,
        }
    })


# ─── DELETE (admin) ─────────────────────────────────────────────────

@news_api_bp.route('/<int:news_id>', methods=['DELETE'])
@login_required
@admin_only
def api_delete(news_id):
    """Elimina una news."""
    news = News.query.get_or_404(news_id)

    db.session.delete(news)
    db.session.commit()

    return jsonify({'success': True})
