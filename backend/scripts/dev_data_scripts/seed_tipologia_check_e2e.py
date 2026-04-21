#!/usr/bin/env python3
"""
Seed dataset E2E per test tipologia check.

Crea utenti e clienti di test in modo idempotente, utili per:
- setup tipologia check da dettaglio cliente
- bulk assignment
- verifica RBAC
- verifica coerenza check attivi per tipologia
"""

from __future__ import annotations

import argparse
import os
import secrets
import sys
from dataclasses import dataclass
from datetime import date, datetime

from werkzeug.security import generate_password_hash


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


@dataclass(frozen=True)
class UserSeed:
    key: str
    email: str
    first_name: str
    last_name: str
    role: str
    specialty: str | None
    is_admin: bool = False


def _full_name(first_name: str, last_name: str) -> str:
    return f"{first_name} {last_name}"


USERS_TO_SEED: tuple[UserSeed, ...] = (
    UserSeed("admin", "seed.admin.tipologia@test.local", "Seed", "Admin", "admin", "amministrazione", True),
    UserSeed("hm_tl", "seed.hm.tl.tipologia@test.local", "Seed", "HMTeamLeader", "team_leader", "coach"),
    UserSeed("unauthorized_prof", "seed.prof.tipologia@test.local", "Seed", "Nutrizionista", "professionista", "nutrizionista"),
    UserSeed("nutri", "seed.nutri.tipologia@test.local", "Nora", "Nutrizione", "professionista", "nutrizionista"),
    UserSeed("coach", "seed.coach.tipologia@test.local", "Carlo", "Coach", "professionista", "coach"),
    UserSeed("psy", "seed.psy.tipologia@test.local", "Paola", "Psicologa", "professionista", "psicologo"),
    UserSeed("hm_user", "seed.hm.user.tipologia@test.local", "Hugo", "Manager", "health_manager", None),
)


def upsert_user(models, db, seed: UserSeed):
    User = models.User
    UserRoleEnum = models.UserRoleEnum
    UserSpecialtyEnum = models.UserSpecialtyEnum

    user = User.query.filter_by(email=seed.email).first()
    if not user:
        user = User(
            email=seed.email,
            password_hash=generate_password_hash("Test1234!"),
            first_name=seed.first_name,
            last_name=seed.last_name,
            role=UserRoleEnum(seed.role),
            specialty=UserSpecialtyEnum(seed.specialty) if seed.specialty else None,
            is_admin=seed.is_admin,
            is_active=True,
        )
        db.session.add(user)
        db.session.flush()
        return user, True

    user.first_name = seed.first_name
    user.last_name = seed.last_name
    user.role = UserRoleEnum(seed.role)
    user.specialty = UserSpecialtyEnum(seed.specialty) if seed.specialty else None
    user.is_admin = seed.is_admin
    user.is_active = True
    user.updated_at = datetime.utcnow()
    return user, False


def _upsert_cliente(models, db, *, slug: str, nome: str, mail: str, tipologia: str | None, check_day: str, profs: dict):
    Cliente = models.Cliente
    TipologiaCheckEnum = models.TipologiaCheckEnum
    StatoClienteEnum = models.StatoClienteEnum
    TipologiaClienteEnum = models.TipologiaClienteEnum
    GiornoEnum = models.GiornoEnum

    cliente = Cliente.query.filter_by(mail=mail).first()
    created = False
    if not cliente:
        cliente = Cliente(mail=mail)
        created = True

    cliente.nome_cognome = nome
    cliente.data_di_nascita = date(1990, 1, 1)
    cliente.professione = "Programmatore/trice"
    cliente.paese = "Italia"
    cliente.genere = "donna" if "a " in nome.lower() else "uomo"
    cliente.numero_telefono = f"+39 339 000 {abs(hash(slug)) % 10000:04d}"
    cliente.indirizzo = "Via Test 1, 00100 Roma (RM)"
    cliente.programma_attuale = "3 mesi"
    cliente.data_inizio_abbonamento = date.today().replace(day=1)
    cliente.durata_programma_giorni = 365
    cliente.stato_cliente = StatoClienteEnum.attivo
    cliente.stato_nutrizione = StatoClienteEnum.attivo
    cliente.stato_coach = StatoClienteEnum.attivo
    cliente.stato_psicologia = StatoClienteEnum.attivo
    cliente.tipologia_cliente = TipologiaClienteEnum.a
    cliente.check_day = GiornoEnum(check_day)
    cliente.tipologia_check_assegnato = TipologiaCheckEnum(tipologia) if tipologia else None

    cliente.nutrizionista_id = profs["nutri"].id
    cliente.coach_id = profs["coach"].id
    cliente.psicologa_id = profs["psy"].id
    cliente.health_manager_id = profs["hm_user"].id
    cliente.nutrizionista = _full_name(profs["nutri"].first_name, profs["nutri"].last_name)
    cliente.coach = _full_name(profs["coach"].first_name, profs["coach"].last_name)
    cliente.psicologa = _full_name(profs["psy"].first_name, profs["psy"].last_name)
    cliente.figura_di_riferimento = "nutrizionista"

    if created:
        db.session.add(cliente)
    db.session.flush()
    return cliente, created


def _ensure_single_active_assignment(models, db, cliente_id: int, tipologia: str | None):
    WeeklyCheck = models.WeeklyCheck
    DCACheck = models.DCACheck
    MinorCheck = models.MinorCheck

    mapping = {
        "regolare": WeeklyCheck,
        "dca": DCACheck,
        "minori": MinorCheck,
    }

    for key, model in mapping.items():
        active = model.query.filter_by(cliente_id=cliente_id, is_active=True).all()
        if key != tipologia:
            for row in active:
                row.is_active = False
                row.deactivated_at = datetime.utcnow()
        else:
            if not active:
                db.session.add(
                    model(
                        cliente_id=cliente_id,
                        token=secrets.token_urlsafe(32),
                        is_active=True,
                        assigned_at=datetime.utcnow(),
                    )
                )
            elif len(active) > 1:
                # Mantieni un solo attivo per pulizia baseline.
                for row in active[1:]:
                    row.is_active = False
                    row.deactivated_at = datetime.utcnow()


def _cleanup_seed_data(models, db):
    Cliente = models.Cliente
    User = models.User
    WeeklyCheck = models.WeeklyCheck
    DCACheck = models.DCACheck
    MinorCheck = models.MinorCheck

    seed_clients = Cliente.query.filter(Cliente.mail.like("%@tipologia-seed.local")).all()
    seed_client_ids = [c.cliente_id for c in seed_clients]
    if seed_client_ids:
        WeeklyCheck.query.filter(WeeklyCheck.cliente_id.in_(seed_client_ids)).delete(synchronize_session=False)
        DCACheck.query.filter(DCACheck.cliente_id.in_(seed_client_ids)).delete(synchronize_session=False)
        MinorCheck.query.filter(MinorCheck.cliente_id.in_(seed_client_ids)).delete(synchronize_session=False)
        Cliente.query.filter(Cliente.cliente_id.in_(seed_client_ids)).delete(synchronize_session=False)

    User.query.filter(User.email.like("seed.%.tipologia@test.local")).delete(synchronize_session=False)
    db.session.commit()


def run_seed(reset: bool):
    from corposostenibile import create_app
    from corposostenibile.extensions import db
    from corposostenibile import models

    app = create_app()
    with app.app_context():
        if reset:
            _cleanup_seed_data(models, db)

        users: dict[str, object] = {}
        created_users = 0
        for seed in USERS_TO_SEED:
            user, created = upsert_user(models, db, seed)
            users[seed.key] = user
            if created:
                created_users += 1
        db.session.flush()

        clients_plan = [
            # 3 senza tipologia (bulk candidates)
            ("bulk-a", "TIPOLOGIA TEST Bulk A", "tipologia.bulk.a@tipologia-seed.local", None, "lun"),
            ("bulk-b", "TIPOLOGIA TEST Bulk B", "tipologia.bulk.b@tipologia-seed.local", None, "mar"),
            ("bulk-c", "TIPOLOGIA TEST Bulk C", "tipologia.bulk.c@tipologia-seed.local", None, "mer"),
            # 3 regolare
            ("reg-1", "TIPOLOGIA TEST Regolare 1", "tipologia.reg.1@tipologia-seed.local", "regolare", "gio"),
            ("reg-2", "TIPOLOGIA TEST Regolare 2", "tipologia.reg.2@tipologia-seed.local", "regolare", "ven"),
            ("reg-3", "TIPOLOGIA TEST Regolare 3", "tipologia.reg.3@tipologia-seed.local", "regolare", "sab"),
            # 3 dca
            ("dca-1", "TIPOLOGIA TEST DCA 1", "tipologia.dca.1@tipologia-seed.local", "dca", "lun"),
            ("dca-2", "TIPOLOGIA TEST DCA 2", "tipologia.dca.2@tipologia-seed.local", "dca", "mar"),
            ("dca-3", "TIPOLOGIA TEST DCA 3", "tipologia.dca.3@tipologia-seed.local", "dca", "mer"),
            # 3 minori
            ("min-1", "TIPOLOGIA TEST Minori 1", "tipologia.min.1@tipologia-seed.local", "minori", "gio"),
            ("min-2", "TIPOLOGIA TEST Minori 2", "tipologia.min.2@tipologia-seed.local", "minori", "ven"),
            ("min-3", "TIPOLOGIA TEST Minori 3", "tipologia.min.3@tipologia-seed.local", "minori", "sab"),
        ]

        created_clients = 0
        for slug, nome, mail, tipologia, check_day in clients_plan:
            cliente, created = _upsert_cliente(
                models,
                db,
                slug=slug,
                nome=nome,
                mail=mail,
                tipologia=tipologia,
                check_day=check_day,
                profs=users,
            )
            _ensure_single_active_assignment(models, db, cliente.cliente_id, tipologia)
            if created:
                created_clients += 1

        db.session.commit()

        print("=" * 72)
        print("SEED TIPLOGIA CHECK E2E COMPLETATO")
        print("=" * 72)
        print(f"Utenti creati: {created_users} (totale gestiti: {len(USERS_TO_SEED)})")
        print(f"Clienti creati: {created_clients} (totale gestiti: {len(clients_plan)})")
        print("")
        print("Credenziali test (password uguale per tutti: Test1234!):")
        for seed in USERS_TO_SEED:
            print(f"- {seed.key:16} {seed.email:40} role={seed.role} specialty={seed.specialty}")
        print("")
        print("Ricerca clienti in UI con testo: TIPOLOGIA TEST")
        print("Bulk candidates: tipologia.bulk.a/b/c@tipologia-seed.local")
        print("=" * 72)


def parse_args():
    parser = argparse.ArgumentParser(description="Seed E2E per Tipologia Check")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Cancella i soli dati seed tipologia precedenti prima di ricreare",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_seed(reset=args.reset)
