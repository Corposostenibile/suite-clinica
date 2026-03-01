from flask import Blueprint, Flask

sop_chatbot_bp = Blueprint(
    'sop_chatbot', __name__,
    url_prefix='/api/sop'
)

from .routes import register_routes
register_routes(sop_chatbot_bp)


def init_app(app: Flask) -> None:
    """Registra il blueprint sop_chatbot nell'applicazione Flask."""
    app.register_blueprint(sop_chatbot_bp)
