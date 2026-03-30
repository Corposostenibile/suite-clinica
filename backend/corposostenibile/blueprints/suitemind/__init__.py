from flask import Blueprint

suitemind_bp = Blueprint('suitemind', __name__, 
                      template_folder='templates',
                      static_folder='static',
                      url_prefix='/suitemind')

# Import and register routes
from .routes import register_api_routes

# Register API routes
register_api_routes(suitemind_bp)

from flask import Flask

def init_app(app: Flask) -> None:
    """
    Registra il blueprint suitemind nell'applicazione Flask.
    
    Args:
        app: L'istanza Flask dell'applicazione
    """
    app.register_blueprint(suitemind_bp)
