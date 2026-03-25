"""
Utilities per setup database test.

Gestisce sincronizzazione schema PostgreSQL senza necessità di CREATE DATABASE.
"""

from urllib.parse import urlparse, urlunparse
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError, OperationalError


def setup_test_database():
    """
    Sincronizza schema del database test.
    
    IMPORTANTE: Si assume che il database esista già.
    Non tenta di creare un nuovo database, usa quello configurato in TEST_DATABASE_URL.
    
    Il database URL è definito in corposostenibile/config.py → TestingConfig.SQLALCHEMY_DATABASE_URI
    Default: postgresql://suite_clinica:password@localhost/suite_clinica_dev_manu_prodclone
    """
    from corposostenibile.config import TestingConfig
    from corposostenibile.extensions import db
    from corposostenibile.models import register_enums
    import os
    
    # Estrai DATABASE_URL dalla configurazione (senza creare app)
    database_url = TestingConfig.SQLALCHEMY_DATABASE_URI
    
    # Parse URL per estrarre nome database
    parsed = urlparse(database_url)
    database_name = parsed.path.lstrip('/')
    database_user = parsed.username or 'suite_clinica'
    
    print(f"✓ Database test '{database_name}' configurato (assicurati che esista)")
    print(f"  Connessione: {parsed.scheme}://{parsed.username}@{parsed.netloc}/{database_name}")
    
    # Ora crea app temporanea per sincronizzare schema (il database deve esistere già)
    from corposostenibile import create_app
    
    # Crea app SENZA chiamare register_enums() durante la creazione
    # Temporaneamente disabilita register_enums durante la creazione app
    original_alembic = os.environ.get("ALEMBIC_RUNNING")
    os.environ["ALEMBIC_RUNNING"] = "1"  # Disabilita register_enums in create_app
    
    try:
        app = create_app('testing')
    finally:
        if original_alembic:
            os.environ["ALEMBIC_RUNNING"] = original_alembic
        else:
            os.environ.pop("ALEMBIC_RUNNING", None)
    
    with app.app_context():
        # Per i test, ricrea completamente lo schema usando db.create_all()
        # Questo è più semplice che usare Alembic e non richiede permessi speciali
        
        # Configura connessioni per impostare search_path
        from sqlalchemy import event
        
        def set_search_path(dbapi_conn, connection_record):
            try:
                cursor = dbapi_conn.cursor()
                cursor.execute("SET search_path TO public, pg_catalog")
                cursor.close()
            except:
                pass
        
        # Registra il listener per impostare search_path su ogni connessione
        event.listen(db.engine, "connect", set_search_path)
        
        # Prima registra ENUM PostgreSQL (necessario per db.create_all())
        enums_registered = False
        try:
            register_enums()
            print("✓ ENUM PostgreSQL registrati")
            enums_registered = True
        except Exception as e:
            error_msg = str(e).lower()
            if "permission" in error_msg or "privilege" in error_msg:
                print(f"⚠️  Permessi insufficienti per creare ENUM: {e}")
                print("   Continuo comunque (gli ENUM potrebbero esistere già)")
            else:
                print(f"⚠️  Errore registrazione ENUM: {e}")
                print("   Continuo comunque...")
        
        # Ricrea completamente lo schema
        # Usa DROP SCHEMA CASCADE per gestire tutte le dipendenze
        try:
            db.session.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
            db.session.commit()
            print("✓ Schema public ricreato (DROP CASCADE)")
            
            # Riesegui register_enums perché DROP SCHEMA ha rimosso anche i tipi ENUM
            try:
                register_enums()
                print("✓ ENUM PostgreSQL registrati nuovamente")
            except Exception as e:
                print(f"⚠️  Errore registrazione ENUM dopo DROP: {e}")
            
            # Crea tutte le tabelle usando db.create_all()
            db.create_all()
            print("✓ Schema database sincronizzato con db.create_all()")
        except Exception as e:
            error_msg = str(e).lower()
            if "permission" in error_msg or "privilege" in error_msg:
                print(f"✗ Errore permessi creazione schema: {e}")
                print("")
                print("⚠️  PERMESSI INSUFFICIENTI!")
                print("   L'utente database deve avere permessi su public schema")
                raise
            else:
                print(f"✗ Errore creazione schema: {e}")
                raise
    
    # L'app viene creata e distrutta qui, ma il database è pronto
    print(f"✓ Database test '{database_name}' è pronto per i test!")

