from flask import Blueprint

bp = Blueprint("push_notifications", __name__, url_prefix="/api/push")

from corposostenibile.blueprints.push_notifications import routes  # noqa: E402,F401


def init_app(app):
    app.register_blueprint(bp)
    app.logger.info("[push_notifications] Blueprint initialized")
