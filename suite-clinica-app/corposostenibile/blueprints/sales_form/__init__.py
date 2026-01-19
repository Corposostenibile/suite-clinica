"""
Sales Form Blueprint
====================

Sistema completo di gestione lead dal form alla conversione in cliente.

Features:
- Form builder dinamico per admin
- Link univoci per ogni sales
- Gestione lead con workflow completo
- Sistema pagamenti (acconto/saldo)
- Pannello Finance per approvazioni
- Pannello Health Manager per assegnazioni
- Conversione automatica lead → cliente
"""

from flask import Blueprint
from flask_login import login_required

sales_form_bp = Blueprint(
    'sales_form',
    __name__,
    url_prefix='/sales-form',
    template_folder='templates',
    static_folder='static',
    static_url_path='/static/sales_form'
)

# Import routes
from . import views
from . import api
from . import admin
from . import public

# Register error handlers
from . import errors

__all__ = ['sales_form_bp']