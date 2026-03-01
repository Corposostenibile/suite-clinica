"""
corposostenibile.blueprints.client_checks
=========================================

Blueprint "client_checks" – Sistema Check Iniziali e Settimanali per Clienti

* Rotte principali:
  • **/client-checks/**                    – Lista form creati (admin/responsabili)
  • **/client-checks/builder**             – Form builder per creazione
  • **/client-checks/builder/<id>**        – Form builder per modifica
  • **/client-checks/assign/<cliente_id>** – Assegnazione form a cliente
  • **/client-checks/public/<token>**      – Form pubblico per compilazione
  • **/client-checks/responses/<cliente_id>** – Visualizzazione risposte

* Funzionalità:
  • Form builder drag&drop per admin e responsabili dipartimento
  • Creazione check iniziali e settimanali personalizzati
  • Assegnazione form ai clienti con link univoci
  • Compilazione pubblica senza autenticazione
  • Sistema notifiche automatiche ai professionisti
  • Visualizzazione storico risposte nel dettaglio cliente
"""

from __future__ import annotations

from flask import Blueprint

# Definizione del blueprint
client_checks_bp = Blueprint(
    'client_checks',
    __name__,
    url_prefix='/client-checks',
    template_folder='templates',
    static_folder='static'
)


def init_app(app):
    """Inizializza il blueprint client_checks con l'app Flask."""
    app.register_blueprint(client_checks_bp)
    
    # Register API blueprint (defined in routes)
    from .routes import api_bp
    app.register_blueprint(api_bp)


# Import delle route alla fine per evitare circular imports
from . import routes  # noqa: E402