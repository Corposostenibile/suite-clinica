#!/usr/bin/env python3
"""
Applica le colonne nutritionist_user_id, psychologist_user_id, coach_user_id
a weekly_check_responses se mancanti (stesso effetto della migrazione e2f3a4b5c6d7).
Eseguire da backend/ con: poetry run python scripts/dev_data_scripts/apply_weekly_check_user_columns.py
"""
import sys
import os

# backend/scripts/dev_data_scripts/ -> backend/
_scripts_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(os.path.dirname(_scripts_dir))
sys.path.insert(0, _backend_dir)
os.chdir(_backend_dir)

def main():
    from corposostenibile import create_app
    from corposostenibile.extensions import db
    from sqlalchemy import text

    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            for col in ("nutritionist_user_id", "psychologist_user_id", "coach_user_id"):
                r = conn.execute(text("""
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'weekly_check_responses' AND column_name = :col
                """), {"col": col})
                if r.scalar() is None:
                    conn.execute(text(f'ALTER TABLE weekly_check_responses ADD COLUMN "{col}" INTEGER REFERENCES users(id)'))
                    print(f"Colonna {col} aggiunta.")
    print("Ok.")

if __name__ == "__main__":
    main()
