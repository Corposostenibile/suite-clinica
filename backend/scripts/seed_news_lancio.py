"""
seed_news_lancio.py
===================
Inserisce l'articolo di lancio della Suite Clinica (2 marzo 2026).

Uso:
    cd backend && poetry run python scripts/seed_news_lancio.py
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import News

app = create_app()

TITLE = "Lancio ufficiale della Suite Clinica!"
SUMMARY = "La Suite Clinica è ufficialmente operativa dal 2 marzo 2026."
CONTENT = """\
<p>Siamo entusiasti di annunciare che la <strong>Suite Clinica</strong> è ufficialmente operativa!</p>

<p>A partire dal <strong>2 marzo 2026</strong>, tutti i professionisti del team avranno accesso alla piattaforma per gestire clienti, check settimanali, task, comunicazioni e molto altro — tutto in un unico posto.</p>

<p>Un ringraziamento speciale va a <strong>Emanuele Mastronardi</strong> e <strong>Samuele Vecchi</strong> del team IT, che hanno lavorato instancabilmente per progettare, sviluppare e testare ogni funzionalità della suite.</p>

<p>A tutti i professionisti: buon lavoro e buon inizio! Siamo certi che questo strumento vi aiuterà a offrire un servizio ancora migliore ai nostri clienti.</p>

<p>— <strong>Matteo Volpara</strong>, CTO Corposostenibile</p>"""

AUTHOR_ID = 1  # Matteo Volpara


with app.app_context():
    # Evita duplicati
    existing = News.query.filter_by(title=TITLE).first()
    if existing:
        print(f"Articolo già presente (id={existing.id}), skip.")
    else:
        news = News(
            title=TITLE,
            summary=SUMMARY,
            content=CONTENT,
            is_published=True,
            is_pinned=True,
            published_at=datetime(2026, 3, 2, 8, 0, 0),
            author_id=AUTHOR_ID,
        )
        db.session.add(news)
        db.session.commit()
        print(f"Articolo creato con successo (id={news.id}).")
