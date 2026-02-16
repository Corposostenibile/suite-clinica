#!/usr/bin/env python3
"""
Crea utenti di prova per testare la dashboard con filtri per ruolo.

Utenti creati (stessa password per tutti: Dashboard1!):
- dashboard_admin@example.com   — Admin (vede tutti i dati)
- dashboard_tl@example.com      — Team Leader Nutrizione (vede team + membri + loro clienti/check/formazione)
- dashboard_prof@example.com    — Professionista Nutrizionista (vede solo i propri dati)

Dati creati:
- 1 team "Team Nutrizione Dashboard Test" con TL come head e prof come membro
- 3 clienti assegnati al professionista (nutrizionista_id)
- WeeklyCheck + 2-3 risposte per cliente (rating noti per verificare i calcoli)
- 1 QualityWeeklyScore per il professionista (settimana corrente, completed)
- 2 Review/Formazione: TL->prof (confermata), prof->TL (confermata)

Dopo l'esecuzione, accedi con le credenziali sopra: con prof vedi solo i 3 clienti,
i check e la quality/formazione relativi; con TL vedi gli stessi dati del team;
con admin vedi tutto.

Uso:
    cd backend && poetry run python scripts/seed_dashboard_test_users.py
"""

import sys
import os
from datetime import datetime, date, timedelta
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import (
    User,
    UserRoleEnum,
    UserSpecialtyEnum,
    Team,
    TeamTypeEnum,
    team_members,
    Cliente,
    StatoClienteEnum,
    TipologiaClienteEnum,
    WeeklyCheck,
    WeeklyCheckResponse,
    QualityWeeklyScore,
    Review,
    ReviewAcknowledgment,
)


PASSWORD = "Dashboard1!"

USERS_CONFIG = [
    {
        "email": "dashboard_admin@example.com",
        "first_name": "Dashboard",
        "last_name": "Admin",
        "role": UserRoleEnum.admin,
        "specialty": None,
        "is_admin": True,
    },
    {
        "email": "dashboard_tl@example.com",
        "first_name": "Team",
        "last_name": "Leader Test",
        "role": UserRoleEnum.team_leader,
        "specialty": UserSpecialtyEnum.nutrizione,
        "is_admin": False,
    },
    {
        "email": "dashboard_prof@example.com",
        "first_name": "Prof",
        "last_name": "Dashboard Test",
        "role": UserRoleEnum.professionista,
        "specialty": UserSpecialtyEnum.nutrizionista,
        "is_admin": False,
    },
]

TEAM_NAME = "Team Nutrizione Dashboard Test"
CLIENTI_NAMES = [
    "Paziente Test Alpha",
    "Paziente Test Beta",
    "Paziente Test Gamma",
]


def get_or_create_user(config):
    u = User.query.filter_by(email=config["email"]).first()
    if u:
        u.first_name = config["first_name"]
        u.last_name = config["last_name"]
        u.role = config["role"]
        u.specialty = config.get("specialty")
        u.is_admin = config.get("is_admin", False)
        u.is_active = True
        u.set_password(PASSWORD)
        db.session.add(u)
        db.session.flush()
        print(f"  Aggiornato: {config['email']}")
        return u
    u = User(
        email=config["email"],
        first_name=config["first_name"],
        last_name=config["last_name"],
        role=config["role"],
        specialty=config.get("specialty"),
        is_admin=config.get("is_admin", False),
        is_active=True,
    )
    u.set_password(PASSWORD)
    db.session.add(u)
    db.session.flush()
    print(f"  Creato: {config['email']}")
    return u


def main():
    print("=" * 60)
    print("SEED UTENTI DI PROVA DASHBOARD (ruoli: Admin, TL, Professionista)")
    print("=" * 60)

    app = create_app()
    with app.app_context():
        # 1. Utenti
        print("\n[1] Utenti (password per tutti: {})".format(PASSWORD))
        admin = get_or_create_user(USERS_CONFIG[0])
        tl = get_or_create_user(USERS_CONFIG[1])
        prof = get_or_create_user(USERS_CONFIG[2])
        db.session.commit()

        # 2. Team con TL come head e prof come membro
        print("\n[2] Team")
        team = Team.query.filter_by(name=TEAM_NAME, team_type=TeamTypeEnum.nutrizione).first()
        if not team:
            team = Team(
                name=TEAM_NAME,
                team_type=TeamTypeEnum.nutrizione,
                head_id=tl.id,
                is_active=True,
                description="Team creato per test dashboard (filtri ruolo)",
            )
            db.session.add(team)
            db.session.flush()
            print(f"  Creato team: {TEAM_NAME} (head: {tl.full_name})")
        else:
            team.head_id = tl.id
            db.session.add(team)
            db.session.flush()
            print(f"  Team esistente: {TEAM_NAME} (head: {tl.full_name})")
        # Assicura che prof sia membro
        if prof not in team.members:
            team.members.append(prof)
            print(f"  Aggiunto membro: {prof.full_name}")
        db.session.commit()

        # 3. Clienti assegnati al professionista
        print("\n[3] Clienti assegnati al professionista")
        clienti = []
        for i, nome in enumerate(CLIENTI_NAMES):
            c = Cliente.query.filter_by(nome_cognome=nome).first()
            if not c:
                c = Cliente(
                    nome_cognome=nome,
                    mail=f"paziente.dashboard.test.{i+1}@example.com",
                    stato_cliente=StatoClienteEnum.attivo,
                    stato_nutrizione=StatoClienteEnum.attivo,
                    nutrizionista_id=prof.id,
                    tipologia_cliente=TipologiaClienteEnum.a,
                )
                db.session.add(c)
                db.session.flush()
                print(f"  Creato: {nome} (nutrizionista_id={prof.id})")
            else:
                c.nutrizionista_id = prof.id
                c.stato_cliente = StatoClienteEnum.attivo
                db.session.add(c)
                print(f"  Aggiornato: {nome}")
            clienti.append(c)
        db.session.commit()

        # 4. WeeklyCheck + risposte (rating noti: 8, 9, 7 per verificare medie)
        print("\n[4] Check settimanali e risposte")
        today = date.today()
        for idx, cliente in enumerate(clienti):
            wc = WeeklyCheck.query.filter_by(cliente_id=cliente.cliente_id).first()
            if not wc:
                wc = WeeklyCheck(
                    cliente_id=cliente.cliente_id,
                    token=str(uuid4()),
                    is_active=True,
                    assigned_at=datetime.utcnow(),
                )
                db.session.add(wc)
                db.session.flush()
                print(f"  Creato WeeklyCheck per {cliente.nome_cognome}")
            # 2-3 risposte con rating deterministici (8, 9, 7) per sanity check
            ratings = [(8, 9, 8, 8), (9, 8, 9, 9), (7, 8, 7, 8)][: 2 + (idx % 2)]
            for ri, (n, c, p, prog) in enumerate(ratings):
                submit_date = datetime.combine(today - timedelta(days=7 * (ri + 1)), datetime.min.time())
                existing = WeeklyCheckResponse.query.filter_by(
                    weekly_check_id=wc.id,
                    submit_date=submit_date,
                ).first()
                if not existing:
                    resp = WeeklyCheckResponse(
                        weekly_check_id=wc.id,
                        submit_date=submit_date,
                        nutritionist_rating=n,
                        coach_rating=c,
                        psychologist_rating=p,
                        progress_rating=prog,
                        nutritionist_feedback="Ok",
                        coach_feedback="Ok",
                        psychologist_feedback="Ok",
                        digestion_rating=7,
                        energy_rating=8,
                        strength_rating=7,
                        sleep_rating=8,
                        mood_rating=8,
                        motivation_rating=8,
                        hunger_rating=7,
                    )
                    db.session.add(resp)
            print(f"  Risposte per {cliente.nome_cognome}: {len(ratings)}")
        db.session.commit()

        # 5. QualityWeeklyScore per il professionista (ultima settimana)
        print("\n[5] Quality score (professionista)")
        # Lunedì della settimana scorsa
        last_monday = today - timedelta(days=today.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)
        qs = QualityWeeklyScore.query.filter_by(
            professionista_id=prof.id,
            week_start_date=last_monday,
        ).first()
        if not qs:
            qs = QualityWeeklyScore(
                professionista_id=prof.id,
                week_start_date=last_monday,
                week_end_date=last_sunday,
                week_number=last_monday.isocalendar()[1],
                year=last_monday.year,
                n_clients_eligible=3,
                n_checks_done=3,
                miss_rate=0.0,
                quality_final=85.0,
                quality_month=85.0,
                quality_trim=85.0,
                bonus_band="100%",
                trend_indicator="stable",
                calculation_status="completed",
            )
            db.session.add(qs)
            print(f"  Creato QualityWeeklyScore: week {last_monday}, quality_final=85")
        else:
            qs.quality_final = 85.0
            qs.calculation_status = "completed"
            db.session.add(qs)
            print(f"  Aggiornato QualityWeeklyScore")
        db.session.commit()

        # 6. Review (formazione): TL -> prof e prof -> TL (entrambe confermate)
        print("\n[6] Formazione (Review)")
        for (reviewer, reviewee, title, rtype) in [
            (tl, prof, "Training TL -> Prof", "settimanale"),
            (prof, tl, "Feedback Prof -> TL", "mensile"),
        ]:
            r = Review.query.filter_by(
                reviewer_id=reviewer.id,
                reviewee_id=reviewee.id,
                title=title,
                deleted_at=None,
            ).first()
            if not r:
                r = Review(
                    reviewer_id=reviewer.id,
                    reviewee_id=reviewee.id,
                    title=title,
                    content="Contenuto training dashboard test.",
                    review_type=rtype,
                    is_draft=False,
                )
                db.session.add(r)
                db.session.flush()
                ack = ReviewAcknowledgment(
                    review_id=r.id,
                    acknowledged_by=reviewee.id,
                    acknowledged_at=datetime.utcnow(),
                )
                db.session.add(ack)
                print(f"  Creata review: {title} (confermata)")
        db.session.commit()

        # Riepilogo
        print("\n" + "=" * 60)
        print("RIEPILOGO CREDENZIALI (password per tutti: {})".format(PASSWORD))
        print("=" * 60)
        print("  Admin:         dashboard_admin@example.com  → vede tutti i dati")
        print("  Team Leader:   dashboard_tl@example.com      → vede team + prof + 3 clienti/check/formazione")
        print("  Professionista: dashboard_prof@example.com  → vede solo propri 3 clienti, check, quality, formazione")
        print("\nVerifica: accedi con dashboard_prof@example.com e controlla che in ogni tab")
        print("(Pazienti, Check, Professionisti, Quality, Formazione) compaiano solo i dati filtrati.")
        print("=" * 60)


if __name__ == "__main__":
    main()
