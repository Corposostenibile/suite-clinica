import sys
import random
from pathlib import Path

# Add backend directory to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import User, UserRoleEnum
from corposostenibile.blueprints.team.criteria_service import CriteriaService

def seed_dev_criteria():
    app = create_app()
    with app.app_context():
        print("--- Seeding Mock Criteria for Dev ---")
        
        users = User.query.filter_by(role=UserRoleEnum.professionista).all()
        print(f"Found {len(users)} professionals.")
        
        for user in users:
            # Determine schema based on user specialty or team
            # If specialty is not set, guess or assign random
            role_key = 'coach' # Default
            if user.is_nutritionist:
                role_key = 'nutrizione'
            elif user.specialty and 'psico' in str(user.specialty).lower():
                role_key = 'psicologia'
            
            schema = CriteriaService.get_criteria_for_role(role_key)
            criteria = {}
            
            # Randomly assign True/False (bias towards True for testing)
            for key in schema:
                criteria[key] = random.choice([True, False, True]) # 66% True
            
            user.assignment_criteria = criteria
            print(f"Updated {user.email} with {len(schema)} criteria ({role_key}).")
            
        db.session.commit()
        print("Done.")

if __name__ == "__main__":
    seed_dev_criteria()
