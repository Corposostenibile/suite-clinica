import sys
import os
sys.path.append('/app')

from corposostenibile.app import create_app
from corposostenibile.models import User, UserSpecialtyEnum
from sqlalchemy import func

app = create_app()
with app.app_context():
    print("=== Simulazione Query API ===")
    target_specialties_strings = [
        'nutrizionista', 'nutrizione',
        'coach',
        'psicologo', 'psicologia'
    ]
    
    # Query con stringhe (vecchia versione)
    profs_strings = User.query.filter(
        User.specialty.in_(target_specialties_strings),
        User.is_active == True
    ).all()
    print(f"Query con stringhe: trovati {len(profs_strings)} professionisti")
    
    # Query con Enum objects (nuova versione)
    target_specialties_enums = [
        UserSpecialtyEnum.nutrizionista, UserSpecialtyEnum.nutrizione,
        UserSpecialtyEnum.coach,
        UserSpecialtyEnum.psicologo, UserSpecialtyEnum.psicologia
    ]
    profs_enums = User.query.filter(
        User.specialty.in_(target_specialties_enums),
        User.is_active == True
    ).all()
    print(f"Query con Enum: trovati {len(profs_enums)} professionisti")

    if len(profs_enums) > 0:
        p = profs_enums[0]
        print(f"Esempio: {p.full_name} | Specialty: {p.specialty} | Type: {type(p.specialty)}")