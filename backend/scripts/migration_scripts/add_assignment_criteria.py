from corposostenibile import create_app
from corposostenibile.extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        # Verifica se la colonna esiste già
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='assignment_criteria';
        """)
        result = db.session.execute(check_query).fetchone()
        
        if not result:
            print("Adding assignment_criteria column to users table...")
            db.session.execute(text("ALTER TABLE users ADD COLUMN assignment_criteria JSONB DEFAULT '{}'::jsonb"))
            db.session.commit()
            print("Column added successfully.")
        else:
            print("Column assignment_criteria already exists.")
            
    except Exception as e:
        print(f"Error updating database: {e}")
        db.session.rollback()
