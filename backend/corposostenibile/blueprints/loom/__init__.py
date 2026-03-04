from flask import Blueprint

loom_bp = Blueprint(
    'loom',
    __name__,
    template_folder='templates',
    static_folder='static'
)

from . import routes  # noqa: E402,F401
