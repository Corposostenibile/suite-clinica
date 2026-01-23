"""
Knowledge Base Blueprint
========================
Sistema completo di gestione documentazione aziendale.
"""

from flask import Blueprint

# Crea il blueprint
bp = Blueprint(
    'kb',
    __name__,
    template_folder='templates',
    static_folder='static',
    url_prefix='/kb'
)

def init_app(app):
    """Inizializza il blueprint Knowledge Base con l'app Flask."""
    from . import routes
    from . import api
    
    app.register_blueprint(bp)
    
    # Registra template globals
    @app.template_global('kb')
    def kb_global():
        """Helper globale per template KB."""
        return {
            'name': 'Knowledge Base',
            'version': '1.0.0'
        }
    
    # Context processor per KB
    @app.context_processor
    def kb_context_processor():
        """Aggiunge variabili di contesto per i template KB."""
        from flask_login import current_user
        from corposostenibile.models import Department, KBCategory
        
        def get_kb_departments():
            """Ritorna tutti i dipartimenti con documenti KB."""
            return Department.query.filter(
                Department.kb_articles.any()
            ).order_by(Department.name).all()
        
        def get_kb_stats():
            """Statistiche generali KB."""
            from corposostenibile.models import KBArticle, KBCategory
            return {
                'total_articles': KBArticle.query.filter_by(
                    status='published'
                ).count(),
                'total_categories': KBCategory.query.filter_by(
                    is_active=True
                ).count(),
                'departments_count': Department.query.filter(
                    Department.kb_articles.any()
                ).count()
            }
        
        return dict(
            get_kb_departments=get_kb_departments,
            get_kb_stats=get_kb_stats
        )