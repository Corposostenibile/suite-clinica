"""
Routes per la gestione delle Novità/Aggiornamenti.
"""

from flask import render_template, redirect, url_for, flash, abort, request, current_app
from flask_login import login_required, current_user
from datetime import datetime
from werkzeug.utils import secure_filename
import os

from corposostenibile.extensions import db
from corposostenibile.models import News, NewsRead, NewsComment, NewsLike, NewsCategory
from . import news_bp
from .forms import NewsForm
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
    # Get page number
    page = request.args.get('page', 1, type=int)
    per_page = 10

    # Query news - mostra solo quelle pubblicate e con data <= oggi
    query = News.query.filter(
        News.is_published == True,
        News.published_at <= datetime.utcnow()
    ).order_by(
        News.is_pinned.desc(),  # Prima quelle in evidenza
        News.published_at.desc()  # Poi le più recenti
    )

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    news_list = pagination.items

    # Conta quante non lette
    unread_count = 0
    for news in news_list:
        if not news.is_read_by(current_user.id):
            unread_count += 1

    return render_template(
        'news/index.html',
        news_list=news_list,
        pagination=pagination,
        unread_count=unread_count
    )


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

    return render_template('news/detail.html', news=news)


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
    form = NewsForm()

    # Popola le scelte delle categorie dal database
    categories = NewsCategory.query.filter_by(is_active=True).order_by(NewsCategory.display_order).all()
    form.categories.choices = [(c.id, c.name) for c in categories]

    # Inizializza data come lista vuota se None (GET request)
    if not form.categories.data:
        form.categories.data = []

    if form.validate_on_submit():
        # Gestione upload immagine
        cover_image_url = None
        if form.cover_image.data:
            cover_image_url = save_cover_image(form.cover_image.data)

        news = News(
            title=form.title.data,
            summary=form.summary.data,
            content=form.content.data,
            cover_image_url=cover_image_url,
            is_published=form.is_published.data,
            is_pinned=False,
            published_at=datetime.utcnow(),
            author_id=current_user.id
        )

        # Aggiungi le categorie selezionate
        if form.categories.data:
            selected_categories = NewsCategory.query.filter(NewsCategory.id.in_(form.categories.data)).all()
            news.categories = selected_categories

        db.session.add(news)
        db.session.commit()

        flash(f'✅ Novità "{news.title}" creata con successo!', 'success')
        return redirect(url_for('news.detail', news_id=news.id))

    return render_template('news/form.html', form=form, title='Nuova Novità')


@news_bp.route('/<int:news_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(news_id):
    """Modifica una novità esistente (admin + autore se creator speciale)."""
    news = News.query.get_or_404(news_id)

    # Verifica permessi
    if not can_edit_news(news):
        flash('❌ Non hai i permessi per modificare questa novità.', 'danger')
        abort(403)

    form = NewsForm(obj=news)

    # Popola le scelte delle categorie dal database
    categories = NewsCategory.query.filter_by(is_active=True).order_by(NewsCategory.display_order).all()
    form.categories.choices = [(c.id, c.name) for c in categories]

    if form.validate_on_submit():
        news.title = form.title.data
        news.summary = form.summary.data
        news.content = form.content.data

        # Gestione upload nuova immagine
        if form.cover_image.data:
            news.cover_image_url = save_cover_image(form.cover_image.data)

        news.is_published = form.is_published.data
        # is_pinned e published_at non vengono più modificati dall'utente

        # Aggiorna le categorie selezionate
        if form.categories.data:
            selected_categories = NewsCategory.query.filter(NewsCategory.id.in_(form.categories.data)).all()
            news.categories = selected_categories
        else:
            news.categories = []

        db.session.commit()

        flash(f'✅ Novità "{news.title}" aggiornata con successo!', 'success')
        return redirect(url_for('news.detail', news_id=news.id))

    # Pre-popola le categorie selezionate
    if not form.categories.data:
        form.categories.data = [c.id for c in news.categories]

    return render_template('news/form.html', form=form, news=news, title='Modifica Novità')


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
