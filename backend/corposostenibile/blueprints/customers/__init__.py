"""
corposostenibile.blueprints.customers
====================================

Bootstrap del feature-package **customers**.

Responsabilità
--------------
• Esporre il blueprint pubblico ``customers_bp``.  
• Offrire ``init_app(app)`` che integra in un solo punto:  
    – blueprint HTML + API (registrati da ``routes.register_routes``)  
    – comandi Flask-CLI del dominio  
    – layer ACL di base (se l’app host espone ``app.acl``)  
    – filtri Jinja custom (basename, avg_or_dash)  
    – voci di menu per la navigazione principale  
• Offrire ``init_celery(celery)`` per registrare i task Celery.
"""

from __future__ import annotations

import os.path
from importlib import import_module
from typing import Callable

from flask import Blueprint, Flask
from markupsafe import Markup
from flask_babel import lazy_gettext as _

# --------------------------------------------------------------------------- #
# Public symbols                                                              #
# --------------------------------------------------------------------------- #
__all__ = [
    "customers_bp",
    "init_app",
    "init_celery",
    "MENU_LABEL",
    "MENU_ITEMS",
]

# --------------------------------------------------------------------------- #
# Blueprint scheletro                                                         #
# --------------------------------------------------------------------------- #
customers_bp: Blueprint = Blueprint(
    "customers",
    __name__,
    static_folder="static",
    url_prefix="/customers",  # ⇨ tutte le route /customers/*
    cli_group="customers",    # abilita  `flask customers …`
)

# --------------------------------------------------------------------------- #
# Jinja helpers                                                               #
# --------------------------------------------------------------------------- #
def _avg_or_dash(value) -> str | Markup:  # noqa: ANN001
    """
    Ritorna «—» se *value* è *None* **altrimenti** il numero formattato a 1 decimale.

    Usato nei template KPI/feedback:
        {{ avg|avg_or_dash }}
    """
    if value is None:
        return "—"
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):  # pragma: no cover
        return str(value)


# --------------------------------------------------------------------------- #
# 1) Integrazione principale                                                  #
# --------------------------------------------------------------------------- #
def init_app(app: Flask) -> None:  # noqa: D401
    """
    Collega blueprint, CLI, ACL, menu e filtri Jinja all’istanza *app*.

    La funzione è **idempotente** – può essere richiamata più volte
    senza effetti collaterali.
    """

    # ── ACL minimale (opzionale) ──────────────────────────────────────────
    if hasattr(app, "acl"):
        from . import permissions as _permissions  # lazy import evita cicli
        with app.app_context():
            _permissions.register_acl(app.acl)  # type: ignore[arg-type]

    # ── CLI commands ─────────────────────────────────────────────────────
    from . import cli as _cli                   # side-effect: registra il gruppo
    _cli.register_cli(app)

    # ── Blueprint & routes (HTML + API) ──────────────────────────────────
    from . import routes as _routes             # side-effect: definisce blueprint
    _routes.register_routes(app)

    # ── Listener webhook stato globale cliente (pausa/ghost) ──────────────
    from .global_status_webhooks import register_global_status_webhook_listeners
    register_global_status_webhook_listeners(app)

    # ── Jinja filters ----------------------------------------------------
    # basename: "/foo/bar/file.pdf" → "file.pdf"
    if "basename" not in app.jinja_env.filters:
        app.jinja_env.filters["basename"] = lambda v: os.path.basename(v or "")

    if "avg_or_dash" not in app.jinja_env.filters:
        app.jinja_env.filters["avg_or_dash"] = _avg_or_dash
    
    # Registra i filtri personalizzati per enum e giorni
    from .template_filters import register_filters
    register_filters(app)

    # ── Menu integration -------------------------------------------------
    # L’app host può leggere `app.menu_items` (lista) per costruire la sidebar.
    # Qui aggiungiamo/estendiamo la voce «Clients» + la nuova «Feedback».
    menu_items: list[dict] = getattr(app, "menu_items", [])
    menu_items.extend(MENU_ITEMS)
    app.menu_items = menu_items  # type: ignore[attr-defined]


# --------------------------------------------------------------------------- #
# 2) Integrazione Celery (facoltativa)                                        #
# --------------------------------------------------------------------------- #
def init_celery(celery) -> None:  # pragma: no cover
    """
    Importa *tasks.py* così che i task vengano registrati nel worker.
    """
    import_module("corposostenibile.blueprints.customers.tasks")  # side-effects
    celery.autodiscover_tasks(
        ["corposostenibile.blueprints.customers"],
        related_name="tasks",
        force=True,
    )


# --------------------------------------------------------------------------- #
# Menu – etichetta principale + voci secondarie                               #
# --------------------------------------------------------------------------- #
MENU_LABEL: str = _("Clients")

# Ogni voce è un dizionario “compatibile” con la sidebar dell’application-shell.
# * icon  : icona (classe RemixIcon / FontAwesome ecc.)
# * label : testo traducibile
# * endpoint : endpoint Flask (stringa)
# * perm  : permesso richiesto (nascondi se l’utente non lo possiede)
MENU_ITEMS: list[dict[str, str]] = [
    {
        "section": MENU_LABEL,
        "icon": "ri-user-3-line",
        "label": _("All clients"),
        "endpoint": "customers.list_view",
        "perm": "customers:view",
    },
    {
        "section": MENU_LABEL,
        "icon": "ri-ghost-2-line",
        "label": _("Ghost Recovery"),
        "endpoint": "customers.recupero_ghost_view",
        "perm": "customers:view",
    },
    {
        "section": MENU_LABEL,
        "icon": "ri-phone-line",
        "label": _("Call Bonus Accettate"),
        "endpoint": "customers.call_bonus_accettate_view",
        "perm": "admin",  # Solo per admin
    },
]
