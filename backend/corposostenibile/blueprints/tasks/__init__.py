from .routes import bp
# Import events explicitly to ensure listeners are registered
from . import events

def init_app(app):
    """
    Registra il blueprint tasks.
    Chiamato da ``corposostenibile/__init__.py``.
    """
    app.register_blueprint(bp)
    
    # Se ci fossero ACL specifiche per i task:
    if hasattr(app, "acl"):
        # Esempio: chi può gestire i task globalmente
        if not app.acl.permitted("admin", "task:manage_all"):
            app.acl.allow("admin", "task:manage_all")
            
    app.logger.info("[tasks] Blueprint initialized")
