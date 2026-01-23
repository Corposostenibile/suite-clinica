"""
Blueprint Nutrition per Corposostenibile
========================================

Gestione piani alimentari, ricette e profili nutrizionali clienti.
"""

from flask import Blueprint

bp = Blueprint(
    'nutrition',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/nutrition/static'
)

# Import views e API dopo la creazione del blueprint per evitare circular imports
from . import views, api

def init_app(app):
    """Registra il blueprint nutrition nell'app Flask."""
    app.register_blueprint(bp, url_prefix='/nutrition')
    
    # Registra filtri Jinja specifici per nutrition
    @app.template_filter('format_calories')
    def format_calories(value):
        """Formatta le calorie con suffisso kcal."""
        if value is None:
            return "0 kcal"
        return f"{int(value)} kcal"
    
    @app.template_filter('format_macros')
    def format_macros(value):
        """Formatta i macronutrienti con 1 decimale."""
        if value is None:
            return "0.0"
        return f"{value:.1f}"
    
    app.logger.info("[nutrition] Blueprint registrato con successo")