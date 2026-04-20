"""
GHL Integration Blueprint
=========================

Gestisce l'integrazione con GoHighLevel:
- Webhook receivers per opportunità
- Processing asincrono con Celery
- Creazione automatica clienti
- Assegnazione servizio clienti
"""

from flask import Blueprint

bp = Blueprint(
    'ghl_integration',
    __name__,
    template_folder='templates',
    url_prefix='/ghl'
)

# Import routes after blueprint creation to avoid circular imports
from . import routes, tasks

def init_app(app):
    """Initialize GHL integration with app"""
    app.register_blueprint(bp)

    # Register ACL permissions if available
    if hasattr(app, 'acl'):
        acl = app.acl
        # Admin can manage webhooks
        acl.allow('admin', 'ghl:manage')
        acl.allow('admin', 'ghl:view_logs')
        acl.allow('admin', 'ghl:test_webhooks')
        acl.allow('admin', 'ghl:view_assignments')

        # Finance can view webhook logs
        acl.allow('finance', 'ghl:view_logs')

        # Service clienti can view assignments
        acl.allow('nutrizionista', 'ghl:view_assignments')
        acl.allow('coach', 'ghl:view_assignments')
        acl.allow('psicologa', 'ghl:view_assignments')

    app.logger.info('[GHL Integration] Blueprint registered successfully')