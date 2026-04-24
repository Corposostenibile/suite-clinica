"""Seed dev database with admin user, marketing user and fake clienti.

Run via:
    docker compose -f docker-compose.dev.yml exec backend python scripts/seed_marketing_demo.py
"""
from datetime import datetime, date
from werkzeug.security import generate_password_hash

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import Cliente, Origine, User, UserRoleEnum

app = create_app()

ADMIN_EMAIL = "spinotto.webdeveloper@gmail.com"
ADMIN_PASSWORD = "password123"

MARKETING_EMAIL = "marketing@test.com"
MARKETING_PASSWORD = "marketing123"

ORIGINI_SEED = [
    "Instagram", "Facebook", "TikTok", "YouTube", "Google Ads",
    "Passaparola", "Influencer A", "Influencer B",
]

CLIENTI_SEED = [
    ("Mario", "Rossi", "mario.rossi@test.it", "Instagram"),
    ("Anna", "Bianchi", "anna.bianchi@test.it", "Facebook"),
    ("Luca", "Verdi", "luca.verdi@test.it", "TikTok"),
    ("Giulia", "Neri", "giulia.neri@test.it", "Instagram"),
    ("Paolo", "Esposito", "paolo.esposito@test.it", "YouTube"),
    ("Chiara", "Russo", "chiara.russo@test.it", "Google Ads"),
    ("Marco", "Ferrari", "marco.ferrari@test.it", "Passaparola"),
    ("Sara", "Romano", "sara.romano@test.it", "Influencer A"),
    ("Davide", "Colombo", "davide.colombo@test.it", "Influencer B"),
    ("Elena", "Ricci", "elena.ricci@test.it", "Instagram"),
    ("Francesco", "Marino", "francesco.marino@test.it", "Facebook"),
    ("Laura", "Greco", "laura.greco@test.it", "TikTok"),
    ("Simone", "Bruno", "simone.bruno@test.it", "YouTube"),
    ("Valentina", "Gallo", "valentina.gallo@test.it", "Google Ads"),
    ("Andrea", "Conti", "andrea.conti@test.it", "Passaparola"),
]


def _upsert_user(email: str, password: str, is_admin: bool, role: UserRoleEnum | None):
    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            first_name=email.split("@")[0].split(".")[0].capitalize(),
            last_name="Test",
            is_admin=is_admin,
            is_active=True,
        )
        if role is not None:
            user.role = role
        db.session.add(user)
        db.session.flush()
        print(f"  [+] CREATED  {email}  admin={is_admin}  role={role}")
    else:
        user.password_hash = generate_password_hash(password)
        user.is_admin = is_admin
        user.is_active = True
        if role is not None:
            user.role = role
        print(f"  [~] UPDATED  {email}  admin={is_admin}  role={role}")
    return user


def _upsert_origine(name: str) -> Origine:
    o = Origine.query.filter_by(name=name).first()
    if o is None:
        o = Origine(name=name, active=True)
        db.session.add(o)
        db.session.flush()
        print(f"  [+] ORIGINE  {name}")
    return o


def main():
    with app.app_context():
        print("=== USERS ===")
        _upsert_user(ADMIN_EMAIL, ADMIN_PASSWORD, is_admin=True, role=None)
        _upsert_user(
            MARKETING_EMAIL,
            MARKETING_PASSWORD,
            is_admin=False,
            role=UserRoleEnum.marketing,
        )

        print("\n=== ORIGINI ===")
        origini_map = {name: _upsert_origine(name) for name in ORIGINI_SEED}

        print("\n=== CLIENTI ===")
        stati_ciclici = ["attivo", "ghost", "pausa", "attivo", "attivo"]
        for idx, (nome, cognome, email, origine_name) in enumerate(CLIENTI_SEED):
            existing = Cliente.query.filter_by(mail=email).first()
            if existing:
                print(f"  [=] SKIP     {nome} {cognome}  (id={existing.cliente_id})")
                continue
            origine = origini_map.get(origine_name)
            cliente = Cliente(
                nome_cognome=f"{nome} {cognome}",
                mail=email,
                numero_telefono=f"+39 333 {1000000 + idx:07d}",
                stato_cliente=stati_ciclici[idx % len(stati_ciclici)],
                origine=origine_name,
                origine_id=origine.id if origine else None,
                data_di_nascita=date(1990, 1, 1),
                genere="uomo" if idx % 2 == 0 else "donna",
                paese="Italia",
            )
            db.session.add(cliente)
            db.session.flush()
            print(f"  [+] CLIENTE  {nome} {cognome}  origine={origine_name}  id={cliente.cliente_id}")

        db.session.commit()
        print("\n[OK] Seed completato.")
        print(f"\nLogin admin:     {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
        print(f"Login marketing: {MARKETING_EMAIL} / {MARKETING_PASSWORD}")


if __name__ == "__main__":
    main()
