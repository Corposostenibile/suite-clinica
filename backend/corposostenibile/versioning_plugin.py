"""
Plugin per SQLAlchemy-Continuum per tracciare l'utente nelle modifiche.
"""
from flask_login import current_user
from sqlalchemy_continuum import Plugin


class FlaskLoginPlugin(Plugin):
    """Plugin per tracciare l'utente corrente con Flask-Login."""
    
    def before_create_tx(self, uow, session):
        """Prima di creare una transazione, imposta l'user_id se la colonna esiste."""
        try:
            # Check if user_id column exists in transaction model
            if hasattr(uow.current_transaction.__class__, 'user_id'):
                if hasattr(current_user, 'id') and current_user.is_authenticated:
                    uow.current_transaction.user_id = current_user.id
                else:
                    uow.current_transaction.user_id = None
        except Exception:
            # Column doesn't exist, skip user tracking
            pass