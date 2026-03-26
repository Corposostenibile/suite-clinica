"""
Utilities per setup database test.
"""
from sqlalchemy import text
from corposostenibile.config import TestingConfig
from corposostenibile.extensions import db
from corposostenibile.models import register_enums
from flask import Flask

def setup_test_database(database_url=None):
    """
    Sincronizza schema del database test.
    """
    from corposostenibile.config import TestingConfig
    from corposostenibile.extensions import db
    from corposostenibile.models import register_enums
    
    # Usa l'URL passato o quello di default
    db_url = database_url or TestingConfig.SQLALCHEMY_DATABASE_URI
    
    # Crea un'app minimale (non chiamare create_app per evitare i blueprint)
    from flask import Flask
    app = Flask(__name__)
    app.config.from_object('corposostenibile.config.TestingConfig')
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    
    # Inizializza solo le estensioni necessarie
    db.init_app(app)
    
    with app.app_context():
        # Setup schema...
        from sqlalchemy import event, text
        
        # ... (stesso codice di prima, ma senza registrare blueprint)
        
        # (Aggiunto: configurazione specifica per evitare di triggerare altro)
        def set_search_path(dbapi_conn, connection_record):
            try:
                cursor = dbapi_conn.cursor()
                cursor.execute("SET search_path TO public, pg_catalog")
                cursor.close()
            except:
                pass
        
        event.listen(db.engine, "connect", set_search_path)
        
        # Prima registra ENUM PostgreSQL
        try:
            register_enums()
        except Exception:
            pass
            
        db.session.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
        db.session.commit()
        
        register_enums()
        db.create_all()
        db.session.commit()

        
        register_enums()
        db.create_all()
        db.session.commit()
