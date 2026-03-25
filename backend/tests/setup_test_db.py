#!/usr/bin/env python3
"""
Script per configurare automaticamente il database di test PostgreSQL.

Esegui: poetry run python tests/setup_test_db.py

Questo script:
1. Verifica se PostgreSQL è disponibile
2. Crea il database se non esiste
3. Configura i permessi sullo schema public
4. Verifica che tutto funzioni
"""

import os
import sys
from urllib.parse import urlparse
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError

# Configurazione
DB_NAME = "corposostenibile_test"
DB_USER = "corposostenibile"
DB_PASSWORD = os.getenv("PGPASSWORD", "password")
DB_HOST = os.getenv("PGHOST", "localhost")
DB_PORT = os.getenv("PGPORT", "5432")

# URL per connessione
ADMIN_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/postgres"
TEST_DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def print_step(msg):
    """Stampa un messaggio di step."""
    print(f"🔧 {msg}")


def print_success(msg):
    """Stampa un messaggio di successo."""
    print(f"✅ {msg}")


def print_error(msg):
    """Stampa un messaggio di errore."""
    print(f"❌ {msg}", file=sys.stderr)


def print_warning(msg):
    """Stampa un messaggio di warning."""
    print(f"⚠️  {msg}")


def check_postgres_connection():
    """Verifica che PostgreSQL sia raggiungibile."""
    print_step("Verifico connessione a PostgreSQL...")
    try:
        engine = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print_success(f"PostgreSQL raggiungibile: {version.split(',')[0]}")
            return True
    except Exception as e:
        print_error(f"Impossibile connettersi a PostgreSQL: {e}")
        print_warning("Assicurati che PostgreSQL sia in esecuzione")
        return False


def create_database_if_not_exists():
    """Crea il database se non esiste."""
    print_step(f"Verifico se il database '{DB_NAME}' esiste...")
    
    try:
        admin_engine = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
        with admin_engine.connect() as conn:
            # Verifica se esiste
            result = conn.execute(
                text(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")
            )
            exists = result.fetchone() is not None
            
            if exists:
                print_success(f"Database '{DB_NAME}' già esistente")
                return True
            
            # Prova a crearlo
            print_step(f"Creo il database '{DB_NAME}'...")
            try:
                conn.execute(text(f'CREATE DATABASE "{DB_NAME}" OWNER {DB_USER}'))
                print_success(f"Database '{DB_NAME}' creato")
                return True
            except ProgrammingError as e:
                if "permission denied" in str(e).lower():
                    print_error("Permessi insufficienti per creare database")
                    print_warning("Esegui manualmente come superuser:")
                    print_warning(f"  sudo -u postgres createdb {DB_NAME}")
                    return False
                raise
        
    except Exception as e:
        print_error(f"Errore durante creazione database: {e}")
        return False


def setup_schema_permissions():
    """Configura i permessi sullo schema public."""
    print_step("Configuro permessi sullo schema public...")
    
    try:
        test_engine = create_engine(TEST_DB_URL, isolation_level="AUTOCOMMIT")
        with test_engine.connect() as conn:
            # Prova prima a dare i permessi (senza ricreare lo schema)
            # Questo funziona se abbiamo già i permessi base
            try:
                conn.execute(text("""
                    GRANT ALL ON SCHEMA public TO corposostenibile;
                    GRANT CREATE ON SCHEMA public TO corposostenibile;
                """))
                
                # Imposta permessi di default
                conn.execute(text("""
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public 
                    GRANT ALL ON TABLES TO corposostenibile;
                    
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public 
                    GRANT ALL ON SEQUENCES TO corposostenibile;
                    
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public 
                    GRANT ALL ON FUNCTIONS TO corposostenibile;
                """))
                
                print_success("Permessi schema public configurati")
                return True
                
            except ProgrammingError as e:
                if "permission denied" in str(e).lower() or "must be owner" in str(e).lower():
                    print_warning("Permessi insufficienti per configurare lo schema")
                    print_warning("Esegui questo comando come superuser PostgreSQL:")
                    print()
                    print(f"  sudo -u postgres psql -d {DB_NAME} <<'EOF'")
                    print("  ALTER SCHEMA public OWNER TO corposostenibile;")
                    print("  GRANT ALL ON SCHEMA public TO corposostenibile;")
                    print("  GRANT CREATE ON SCHEMA public TO corposostenibile;")
                    print("  EOF")
                    print()
                    print("Oppure usa lo script SQL:")
                    print(f"  sudo -u postgres psql -d {DB_NAME} -f tests/setup_test_db.sql")
                    return False
                raise
            
    except Exception as e:
        print_error(f"Errore durante configurazione permessi: {e}")
        return False


def verify_setup():
    """Verifica che il setup sia corretto."""
    print_step("Verifico che il setup sia corretto...")
    
    try:
        test_engine = create_engine(TEST_DB_URL, isolation_level="AUTOCOMMIT")
        with test_engine.connect() as conn:
            # Verifica permessi schema
            result = conn.execute(text("""
                SELECT schema_owner 
                FROM information_schema.schemata 
                WHERE schema_name = 'public'
            """))
            owner = result.fetchone()[0]
            
            # Verifica che possiamo creare una tabella di test
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS _test_permissions_check (
                    id SERIAL PRIMARY KEY
                )
            """))
            conn.execute(text("DROP TABLE IF EXISTS _test_permissions_check"))
            
            print_success("Setup verificato correttamente!")
            return True
            
    except Exception as e:
        print_error(f"Verifica fallita: {e}")
        return False


def main():
    """Esegue il setup completo."""
    print("=" * 60)
    print("🔧 Setup Database di Test - Corposostenibile Suite")
    print("=" * 60)
    print()
    
    # Step 1: Verifica connessione
    if not check_postgres_connection():
        sys.exit(1)
    
    # Step 2: Crea database
    if not create_database_if_not_exists():
        sys.exit(1)
    
    # Step 3: Configura permessi
    if not setup_schema_permissions():
        sys.exit(1)
    
    # Step 4: Verifica
    if not verify_setup():
        sys.exit(1)
    
    print()
    print("=" * 60)
    print_success("Setup completato con successo!")
    print("=" * 60)
    print()
    print("Ora puoi eseguire i test con:")
    print("  poetry run pytest tests/")
    print()


if __name__ == "__main__":
    main()

