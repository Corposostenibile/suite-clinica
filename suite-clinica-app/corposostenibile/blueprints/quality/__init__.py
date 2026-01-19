"""
Quality Score Blueprint
Dashboard e gestione Quality Score per professionisti.
"""
from flask import Blueprint

bp = Blueprint(
    'quality',
    __name__,
    url_prefix='/quality',
    template_folder='templates'
)

from . import routes
