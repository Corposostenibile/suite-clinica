#!/usr/bin/env python3
"""
Crea la tabella app_notifications se non esiste.
Utile quando il DB è stato ripristinato da dump o alembic_version è già a head
ma la tabella non è mai stata creata.

Esegui dalla root del progetto con lo stesso .env usato da dev:
  cd backend && FLASK_APP=corposostenibile poetry run python scripts/ensure_app_notifications_table.py
"""
import os
import sys

# backend come cwd per import corposostenibile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    from corposostenibile import create_app
    from corposostenibile.extensions import db
    from sqlalchemy import inspect, text

    app = create_app()
    with app.app_context():
        insp = inspect(db.engine)
        if "app_notifications" in insp.get_table_names():
            print("Tabella app_notifications già presente. Nessuna modifica.")
            return 0

        print("Creazione tabella app_notifications...")
        db.session.execute(text("""
            CREATE TABLE app_notifications (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                kind VARCHAR(50) NOT NULL,
                title VARCHAR(255) NOT NULL,
                body TEXT NOT NULL,
                url VARCHAR(1024) NOT NULL,
                payload JSONB,
                is_read BOOLEAN NOT NULL,
                read_at TIMESTAMP,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """))
        db.session.execute(text("CREATE INDEX ix_app_notifications_user_id ON app_notifications (user_id)"))
        db.session.execute(text("CREATE INDEX ix_app_notifications_kind ON app_notifications (kind)"))
        db.session.execute(text("CREATE INDEX ix_app_notifications_is_read ON app_notifications (is_read)"))
        db.session.commit()
        print("Tabella app_notifications creata con successo.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
