"""
Blueprint per la gestione dei Post-it / Promemoria personali.
"""

from flask import Blueprint

bp = Blueprint('postit', __name__, url_prefix='/postit')

from corposostenibile.blueprints.postit import routes  # noqa
