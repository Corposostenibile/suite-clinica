"""
blueprints/ticket/public_routes.py
==================================

Route pubbliche per apertura ticket senza autenticazione.
"""

from __future__ import annotations

from flask import (
    flash,
    redirect,
    request,
    session,
    url_for,
)
from sqlalchemy.exc import SQLAlchemyError

from corposostenibile.extensions import db
from corposostenibile.models import (
    Department,
    Ticket,
    TicketUrgencyEnum,
)

from . import public_ticket_bp
from .services import TicketService


# ────────────────────────────────────────────────────────────────────
#  Form Pubblico
# ────────────────────────────────────────────────────────────────────

# HTML form deleted - use API instead


# ────────────────────────────────────────────────────────────────────
#  Pagina Conferma
# ────────────────────────────────────────────────────────────────────

# HTML page deleted - use API instead


# ────────────────────────────────────────────────────────────────────
#  Tracking Pubblico
# ────────────────────────────────────────────────────────────────────

# HTML form deleted - use API instead


# ────────────────────────────────────────────────────────────────────
#  Info/FAQ
# ────────────────────────────────────────────────────────────────────

# HTML page deleted - use API instead