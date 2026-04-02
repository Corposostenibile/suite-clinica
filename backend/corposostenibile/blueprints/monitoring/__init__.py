from flask import Blueprint

bp = Blueprint("monitoring", __name__, url_prefix="/api/monitoring")

from corposostenibile.blueprints.monitoring import routes  # noqa: E402,F401


def init_app(app):
    app.register_blueprint(bp)
    app.logger.info("[monitoring] Blueprint initialized")
