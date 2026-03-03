from flask import Blueprint

bp = Blueprint("video_calls", __name__, url_prefix="/api/video-calls")

from corposostenibile.blueprints.video_calls import routes  # noqa: E402,F401


def init_app(app):
    app.register_blueprint(bp)
    app.logger.info("[video_calls] Blueprint initialized")
