"""
seed_test_users.py
==================
Crea (o aggiorna) utenti di test per lo sviluppo locale:
  - 1 Health Manager
  - 1 Nutrizionista
  - 1 Coach
  - 1 Psicologa

Tutti con password: test123

Uso:
    cd backend
    FLASK_APP=wsgi.py python scripts/seed_test_users.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from wsgi import app
from corposostenibile.extensions import db
from corposostenibile.models import User, UserRoleEnum, UserSpecialtyEnum
from werkzeug.security import generate_password_hash

PASSWORD = "test123"

TEST_USERS = [
    {
        "email": "hm.test@suiteclinica.com",
        "first_name": "Maria",
        "last_name": "Rossi HM",
        "role": UserRoleEnum.health_manager,
        "specialty": None,
        "is_admin": False,
    },
    {
        "email": "nutrizionista.test@suiteclinica.com",
        "first_name": "Luca",
        "last_name": "Bianchi Nutri",
        "role": UserRoleEnum.professionista,
        "specialty": UserSpecialtyEnum.nutrizionista,
        "is_admin": False,
    },
    {
        "email": "coach.test@suiteclinica.com",
        "first_name": "Sara",
        "last_name": "Verdi Coach",
        "role": UserRoleEnum.professionista,
        "specialty": UserSpecialtyEnum.coach,
        "is_admin": False,
    },
    {
        "email": "psicologa.test@suiteclinica.com",
        "first_name": "Anna",
        "last_name": "Neri Psi",
        "role": UserRoleEnum.professionista,
        "specialty": UserSpecialtyEnum.psicologo,
        "is_admin": False,
    },
]


def seed():
    pwd_hash = generate_password_hash(PASSWORD)

    with app.app_context():
        for data in TEST_USERS:
            user = User.query.filter_by(email=data["email"]).first()

            if user:
                # Aggiorna password + campi
                user.password_hash = pwd_hash
                user.first_name = data["first_name"]
                user.last_name = data["last_name"]
                user.role = data["role"]
                user.specialty = data["specialty"]
                user.is_active = True
                action = "AGGIORNATO"
            else:
                # Crea nuovo
                user = User(
                    email=data["email"],
                    password_hash=pwd_hash,
                    first_name=data["first_name"],
                    last_name=data["last_name"],
                    role=data["role"],
                    specialty=data["specialty"],
                    is_admin=data["is_admin"],
                    is_active=True,
                )
                db.session.add(user)
                action = "CREATO"

            db.session.flush()
            role_label = f"{data['role'].value}"
            spec_label = f" / {data['specialty'].value}" if data["specialty"] else ""
            print(f"  {action:<12} id={user.id:<5} {data['email']:<42} [{role_label}{spec_label}]")

        db.session.commit()
        print(f"\nPassword per tutti: {PASSWORD}")
        print("Done!")


if __name__ == "__main__":
    seed()
