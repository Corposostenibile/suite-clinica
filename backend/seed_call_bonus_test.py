"""
Script di seeding dati per il test manuale del flusso Call Bonus.

Crea nel DB (se non esistono già):
  - 1 professionista nutrizionista con link_call_bonus compilato
  - 1 professionista coach con link_call_bonus compilato
  - 1 cliente di test con storia_cliente compilata

Tutti gli oggetti hanno prefisso "_TEST_CB_" per cleanup sicuro.

Utilizzo:
    cd /home/samu/suite-clinica/backend
    python seed_call_bonus_test.py

Per cleanup:
    python seed_call_bonus_test.py --cleanup
"""

import sys
import os

# Assicura che il backend sia nel path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("FLASK_ENV", "development")

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import (
    User,
    Cliente,
    UserRoleEnum,
    UserSpecialtyEnum,
    StatoClienteEnum,
)

# ─── Dati di test ─────────────────────────────────────────────
TEST_PREFIX = "_TEST_CB_"

PROF_NUTRI = {
    "email": f"{TEST_PREFIX}nutri@test.corposostenibile.com",
    "first_name": "_TEST_CB_",
    "last_name": "Nutrizionista",
    "role": UserRoleEnum.professionista,
    "specialty": UserSpecialtyEnum.nutrizionista,
    "link_call_bonus": "https://calendly.com/test-nutrizionista/call-bonus",
    "password": "TestPassword123!",
}

PROF_COACH = {
    "email": f"{TEST_PREFIX}coach@test.corposostenibile.com",
    "first_name": "_TEST_CB_",
    "last_name": "Coach",
    "role": UserRoleEnum.professionista,
    "specialty": UserSpecialtyEnum.coach,
    "link_call_bonus": "https://calendly.com/test-coach/call-bonus",
    "password": "TestPassword123!",
}

CLIENTE_TEST = {
    "cliente_id": 9999901,  # ID alto per evitare conflitti
    "nome_cognome": "_TEST_CB_ Cliente Prova",
    "mail": f"{TEST_PREFIX}cliente@test.corposostenibile.com",
    "storia_cliente": (
        "Donna di 35 anni, impiegata full-time. "
        "Ha iniziato il percorso nutrizionale 6 mesi fa, ottimi progressi. "
        "Vorrebbe aggiungere un supporto di coaching per gestire lo stress lavorativo "
        "e migliorare la costanza nell'esercizio fisico. "
        "Motivata, ma ha bisogno di struttura e accountability."
    ),
    "programma_attuale": "Piano Nutrizionale Standard",
    "stato_cliente": StatoClienteEnum.attivo,
}


def _create_or_get_professionista(session, data: dict) -> User:
    existing = session.query(User).filter_by(email=data["email"]).first()
    if existing:
        print(f"  ⚡ Professionista già esistente: {existing.email} (id={existing.id})")
        # Assicura che link_call_bonus sia aggiornato
        notes = existing.assignment_ai_notes or {}
        notes["link_call_bonus"] = data["link_call_bonus"]
        existing.assignment_ai_notes = notes
        return existing

    user = User(
        email=data["email"],
        first_name=data["first_name"],
        last_name=data["last_name"],
        role=data["role"],
        specialty=data["specialty"],
        is_active=True,
        is_admin=False,
        assignment_ai_notes={
            "link_call_bonus": data["link_call_bonus"],
            "note": "Professionista di test per Call Bonus flow",
            "disponibilita": "Disponibile lun-ven 9-18",
            "specializzazione_dettaglio": "Test professionista",
        },
        assignment_criteria={
            "lingue": ["italiano"],
            "disponibile_call_bonus": True,
        },
    )
    user.set_password(data["password"])
    session.add(user)
    session.flush()
    print(f"  ✅ Professionista creato: {user.email} (id={user.id})")
    return user


def _create_or_get_cliente(session, data: dict, nutri: User, coach: User) -> Cliente:
    existing = session.query(Cliente).filter_by(cliente_id=data["cliente_id"]).first()
    if existing:
        print(f"  ⚡ Cliente già esistente: {existing.nome_cognome} (id={existing.cliente_id})")
        # Assicura assegnazione nutrizionista
        if nutri not in existing.nutrizionisti_multipli:
            existing.nutrizionisti_multipli.append(nutri)
        return existing

    cliente = Cliente(
        cliente_id=data["cliente_id"],
        nome_cognome=data["nome_cognome"],
        mail=data["mail"],
        storia_cliente=data["storia_cliente"],
        programma_attuale=data["programma_attuale"],
        stato_cliente=data.get("stato_cliente", StatoClienteEnum.attivo),
        # Assegna nutrizionista come professionista principale (coach è candidato per call bonus)
        nutrizionista_id=nutri.id,
    )
    session.add(cliente)
    session.flush()

    # Aggiungi nutrizionista ai multipli
    cliente.nutrizionisti_multipli.append(nutri)

    print(f"  ✅ Cliente creato: {cliente.nome_cognome} (id={cliente.cliente_id})")
    print(f"     Nutrizionista assegnato: {nutri.full_name}")
    print(f"     Coach candidato per call bonus: {coach.full_name}")
    return cliente


def seed():
    app = create_app("development")
    with app.app_context():
        print("\n🌱 SEEDING DATI TEST CALL BONUS")
        print("=" * 50)

        print("\n📋 Creazione professionisti di test...")
        nutri = _create_or_get_professionista(db.session, PROF_NUTRI)
        coach = _create_or_get_professionista(db.session, PROF_COACH)

        print("\n👤 Creazione cliente di test...")
        cliente = _create_or_get_cliente(db.session, CLIENTE_TEST, nutri, coach)

        db.session.commit()

        print("\n" + "=" * 50)
        print("✅ SEEDING COMPLETATO")
        print("\n📌 DATI PER IL TEST MANUALE:")
        print(f"  Cliente:           {cliente.nome_cognome}  (ID: {cliente.cliente_id})")
        print(f"  Email cliente:     {cliente.mail}")
        print(f"  Nutrizionista:     {nutri.full_name}  (ID: {nutri.id})")
        print(f"    Email login:     {nutri.email}")
        print(f"    Password:        {PROF_NUTRI['password']}")
        print(f"    Link CB:         {PROF_NUTRI['link_call_bonus']}")
        print(f"  Coach (per CB):    {coach.full_name}  (ID: {coach.id})")
        print(f"    Email login:     {coach.email}")
        print(f"    Password:        {PROF_COACH['password']}")
        print(f"    Link CB:         {PROF_COACH['link_call_bonus']}")
        print("\n📋 PASSI PER IL TEST MANUALE:")
        print("  1. Admin: apri scheda cliente → tab 'Call Bonus'")
        print("  2. Crea nuova richiesta → seleziona 'Coach'")
        print("  3. Verifica step AI con match professionisti")
        print("  4. Seleziona '_TEST_CB_ Coach' → verifica link Calendly")
        print("  5. Premi 'Conferma prenotazione'")
        print(f"  6. Login come {coach.email} / {PROF_COACH['password']}")
        print("  7. Trova la call bonus → premi 'Interessato'")
        print("  8. Verifica log backend: [GHL_MOCK_WEBHOOK] oppure [GHL_WEBHOOK]")
        print()


def cleanup():
    app = create_app("development")
    with app.app_context():
        print("\n🗑️  CLEANUP DATI TEST CALL BONUS")
        print("=" * 50)

        # Rimuovi call bonus di test
        from corposostenibile.models import CallBonus
        cliente = db.session.query(Cliente).filter_by(cliente_id=CLIENTE_TEST["cliente_id"]).first()
        if cliente:
            cbs = db.session.query(CallBonus).filter_by(cliente_id=cliente.cliente_id).all()
            for cb in cbs:
                db.session.delete(cb)
            print(f"  🗑️  Rimossi {len(cbs)} call bonus di test")

            db.session.delete(cliente)
            print(f"  🗑️  Cliente rimosso: {cliente.nome_cognome}")

        for prof_data in [PROF_NUTRI, PROF_COACH]:
            user = db.session.query(User).filter_by(email=prof_data["email"]).first()
            if user:
                db.session.delete(user)
                print(f"  🗑️  Utente rimosso: {user.email}")

        db.session.commit()
        print("\n✅ CLEANUP COMPLETATO")


if __name__ == "__main__":
    if "--cleanup" in sys.argv:
        cleanup()
    else:
        seed()
