"""
Routes per la gestione delle Novità/Aggiornamenti.
"""

from flask import redirect, url_for, flash, abort, request, current_app
from flask_login import login_required, current_user
from datetime import datetime
from werkzeug.utils import secure_filename
import os

from corposostenibile.extensions import db
from corposostenibile.models import News, NewsRead, NewsComment, NewsLike, NewsCategory
from . import news_bp
from .permissions import (
    can_create_news,
    can_edit_news,
    can_delete_news,
    can_pin_news,
    can_publish_news,
    create_news_required,
    admin_only
)


@news_bp.route('/')
@login_required
def index():
    """Lista di tutte le novità pubblicate."""
    # Redirect to API or admin panel
    abort(404)


@news_bp.route('/<int:news_id>')
@login_required
def detail(news_id):
    """Dettaglio di una novità."""
    news = News.query.get_or_404(news_id)

    # Verifica che sia visibile (pubblicata e data <= oggi)
    if not news.is_visible and not current_user.is_admin:
        abort(404)

    # Segna come letta
    news.mark_as_read(current_user.id)
    db.session.commit()

    # Return JSON instead of HTML
    abort(404)


def save_cover_image(file):
    """Salva l'immagine di copertina e ritorna il percorso."""
    if not file:
        return None

    # Crea directory se non esiste
    upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'news')
    os.makedirs(upload_folder, exist_ok=True)

    # Nome file sicuro con timestamp
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    name, ext = os.path.splitext(filename)
    unique_filename = f"{timestamp}_{name}{ext}"

    # Salva file
    filepath = os.path.join(upload_folder, unique_filename)
    file.save(filepath)

    # Ritorna percorso relativo per URL
    return f'/static/uploads/news/{unique_filename}'


@news_bp.route('/new', methods=['GET', 'POST'])
@login_required
@create_news_required
def create():
    """Crea una nuova novità (admin + creator speciali)."""
    # API-only - removed HTML form
    abort(404)


@news_bp.route('/<int:news_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(news_id):
    """Modifica una novità esistente (admin + autore se creator speciale)."""
    # API-only - removed HTML form
    abort(404)


@news_bp.route('/<int:news_id>/delete', methods=['POST'])
@login_required
def delete(news_id):
    """Elimina una novità (admin + autore se creator speciale)."""
    news = News.query.get_or_404(news_id)

    # Verifica permessi
    if not can_delete_news(news):
        flash('❌ Non hai i permessi per eliminare questa novità.', 'danger')
        abort(403)

    title = news.title

    db.session.delete(news)
    db.session.commit()

    flash(f'🗑️ Novità "{title}" eliminata con successo.', 'success')
    return redirect(url_for('news.index'))


@news_bp.route('/<int:news_id>/toggle-pin', methods=['POST'])
@login_required
@admin_only
def toggle_pin(news_id):
    """Metti/togli in evidenza una novità (solo admin)."""
    news = News.query.get_or_404(news_id)
    news.is_pinned = not news.is_pinned

    db.session.commit()

    status = "messa in evidenza" if news.is_pinned else "rimossa dall'evidenza"
    flash(f'📌 Novità "{news.title}" {status}.', 'success')

    return redirect(url_for('news.detail', news_id=news.id))


@news_bp.route('/<int:news_id>/toggle-publish', methods=['POST'])
@login_required
@admin_only
def toggle_publish(news_id):
    """Pubblica/nascondi una novità (solo admin)."""
    news = News.query.get_or_404(news_id)
    news.is_published = not news.is_published

    db.session.commit()

    status = "pubblicata" if news.is_published else "nascosta"
    flash(f'👁️ Novità "{news.title}" {status}.', 'success')

    return redirect(url_for('news.detail', news_id=news.id))


@news_bp.route('/<int:news_id>/comment', methods=['POST'])
@login_required
def add_comment(news_id):
    """Aggiungi un commento a una novità."""
    news = News.query.get_or_404(news_id)

    # Verifica che sia visibile
    if not news.is_visible and not current_user.is_admin:
        abort(404)

    content = request.form.get('content', '').strip()

    if not content:
        flash('Il commento non può essere vuoto.', 'warning')
        return redirect(url_for('news.detail', news_id=news_id))

    comment = NewsComment(
        news_id=news_id,
        user_id=current_user.id,
        content=content
    )

    db.session.add(comment)
    db.session.commit()

    flash('💬 Commento aggiunto con successo!', 'success')
    return redirect(url_for('news.detail', news_id=news_id))


@news_bp.route('/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    """Elimina un commento (solo autore o admin)."""
    comment = NewsComment.query.get_or_404(comment_id)

    # Solo l'autore del commento o un admin possono eliminarlo
    if comment.user_id != current_user.id and not current_user.is_admin:
        abort(403)

    news_id = comment.news_id
    db.session.delete(comment)
    db.session.commit()

    flash('🗑️ Commento eliminato.', 'success')
    return redirect(url_for('news.detail', news_id=news_id))


@news_bp.route('/<int:news_id>/like', methods=['POST'])
@login_required
def toggle_like(news_id):
    """Metti/togli like a una novità."""
    news = News.query.get_or_404(news_id)

    # Verifica che sia visibile
    if not news.is_visible and not current_user.is_admin:
        abort(404)

    # Controlla se l'utente ha già messo like
    existing_like = NewsLike.query.filter_by(
        news_id=news_id,
        user_id=current_user.id
    ).first()

    if existing_like:
        # Rimuovi like
        db.session.delete(existing_like)
        db.session.commit()
        return {'liked': False, 'total_likes': news.likes.count()}
    else:
        # Aggiungi like
        new_like = NewsLike(news_id=news_id, user_id=current_user.id)
        db.session.add(new_like)
        db.session.commit()
        return {'liked': True, 'total_likes': news.likes.count()}
