#!/usr/bin/env python3
"""
Suite Clinica - Test Data Seed Script
======================================

Script unificato per popolare il database di sviluppo con dati di test completi.

UTILIZZO:
    python scripts/seed_test_data.py [opzioni]

OPZIONI:
    --clean         Elimina tutti i dati esistenti prima di seed
    --patients N    Numero di pazienti da creare (default: 50)
    --professionals N    Numero di professionisti per tipo (default: 10)

ESEMPI:
    # Seed veloce con dati minimi
    python scripts/seed_test_data.py

    # Seed completo con pulizia database
    python scripts/seed_test_data.py --clean --patients 100 --professionals 20

DATI GENERATI:
    - Dipartimenti (Nutrizione, Coaching, Psicologia, Admin)
    - Amministratori e Team Leaders
    - Professionisti (Nutrizionisti, Coach, Psicologi)
    - Team con membri assegnati
    - Pazienti con tutte le tipologie (VIP, Premium, Standard)
    - Assegnazioni paziente-professionista
    - Stati e programmi realistici

CREDENZIALI GENERATE:
    Admin: admin@test.local / Test1234!
    Professionisti: [email]@test.local / Test1234!
    
NOTA: Questo script è solo per ambiente di sviluppo!
"""

import sys
import os
import random
import argparse
from datetime import datetime, date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================
# CONFIGURAZIONE
# ============================================================

# Nomi italiani comuni
NOMI_MASCHILI = [
    "Marco", "Luca", "Andrea", "Francesco", "Alessandro", "Matteo", "Lorenzo",
    "Davide", "Simone", "Federico", "Gabriele", "Riccardo", "Tommaso", "Stefano",
    "Giuseppe", "Antonio", "Giovanni", "Michele", "Paolo", "Roberto", "Filippo",
]

NOMI_FEMMINILI = [
    "Giulia", "Francesca", "Sara", "Chiara", "Valentina", "Alessia", "Martina",
    "Federica", "Elisa", "Silvia", "Laura", "Anna", "Maria", "Elena", "Giorgia",
    "Alice", "Beatrice", "Camilla", "Claudia", "Daniela", "Emma", "Gaia",
]

COGNOMI = [
    "Rossi", "Russo", "Ferrari", "Esposito", "Bianchi", "Romano", "Colombo",
    "Ricci", "Marino", "Greco", "Bruno", "Gallo", "Conti", "De Luca", "Mancini",
    "Costa", "Giordano", "Rizzo", "Lombardi", "Moretti", "Barbieri", "Fontana",
]

PROFESSIONI = [
    "Impiegato/a", "Libero professionista", "Insegnante", "Infermiere/a",
    "Medico", "Avvocato", "Manager", "Consulente", "Imprenditore/trice",
    "Studente/ssa", "Commerciante", "Programmatore/trice", "Designer",
]

CITTA_PROVINCE = [
    ("Milano", "MI"), ("Roma", "RM"), ("Napoli", "NA"), ("Torino", "TO"),
    ("Bologna", "BO"), ("Firenze", "FI"), ("Venezia", "VE"), ("Genova", "GE"),
]

VIE = [
    "Via Roma", "Via Garibaldi", "Via Mazzini", "Via Cavour", "Via Dante",
    "Corso Italia", "Viale Europa", "Piazza del Popolo",
]

PREFISSI_MOBILE = ["320", "328", "329", "330", "333", "338", "339", "340", "347", "348"]

# ============================================================
# FUNZIONI HELPER
# ============================================================

def generate_birth_date(min_age=18, max_age=75):
    """Genera data di nascita realistica"""
    today = date.today()
    days_range = (max_age - min_age) * 365
    random_days = random.randint(0, days_range)
    return today - timedelta(days=min_age * 365 + random_days)

def generate_phone():
    """Genera numero di telefono italiano"""
    prefisso = random.choice(PREFISSI_MOBILE)
    numero = ''.join([str(random.randint(0, 9)) for _ in range(7)])
    return f"+39 {prefisso} {numero[:3]} {numero[3:]}"

def generate_address():
    """Genera indirizzo italiano"""
    via = random.choice(VIE)
    numero = random.randint(1, 200)
    citta, provincia = random.choice(CITTA_PROVINCE)
    cap = f"{random.randint(10, 99)}{random.randint(100, 999)}"
    return f"{via} {numero}, {cap} {citta} ({provincia})"

def generate_email(first_name, last_name, domain="test.local", idx=None):
    """Genera email unica"""
    first = first_name.lower().replace("'", "").replace(" ", "")
    last = last_name.lower().replace("'", "").replace(" ", "")
    suffix = f"{idx}" if idx else ""
    return f"{first}.{last}{suffix}@{domain}"

# ============================================================
# SEED FUNCTIONS
# ============================================================

def seed_departments(db, Department):
    """Crea dipartimenti base"""
    print("\n📂 Creazione dipartimenti...")
    
    departments_data = [
        {"name": "Amministrazione", "description": "Gestione amministrativa"},
        {"name": "Nutrizione", "description": "Team nutrizionisti"},
        {"name": "Coaching", "description": "Team coach"},
        {"name": "Psicologia", "description": "Team psicologi"},
    ]
    
    departments = {}
    for dept_data in departments_data:
        dept = Department.query.filter_by(name=dept_data["name"]).first()
        if not dept:
            dept = Department(name=dept_data["name"])
            db.session.add(dept)
        departments[dept_data["name"]] = dept
    
    db.session.commit()
    print(f"  ✅ Creati/verificati {len(departments)} dipartimenti")
    return departments

def seed_admin_users(db, User, Department, UserRoleEnum, UserSpecialtyEnum):
    """Crea admin e account di base"""
    from werkzeug.security import generate_password_hash
    
    print("\n👤 Creazione utenti admin...")
    
    # Admin principale
    admin = User.query.filter_by(email="admin@test.local").first()
    if not admin:
        admin = User(
            email="admin@test.local",
            password_hash=generate_password_hash("Test1234!"),
            first_name="Admin",
            last_name="Sistema",
            role=UserRoleEnum.admin,
            specialty=UserSpecialtyEnum.amministrazione,
            is_admin=True,
            is_active=True
        )
        db.session.add(admin)
        print("  ✅ Creato admin: admin@test.local / Test1234!")
    else:
        print("  ℹ️  Admin già esistente")
    
    db.session.commit()
    return admin

def seed_professionals(db, User, Department, Team, departments, count_per_type=10):
    """Crea professionisti (nutrizionisti, coach, psicologi)"""
    from corposostenibile.models import UserRoleEnum, UserSpecialtyEnum, TeamTypeEnum
    from werkzeug.security import generate_password_hash
    
    print(f"\n👥 Creazione professionisti ({count_per_type} per tipo)...")
    
    professionals = {'nutrizionista': [], 'coach': [], 'psicologo': []}
    teams = {'nutrizionista': [], 'coach': [], 'psicologo': []}
    
    specialty_config = {
        'nutrizionista': {
            'role_specialty': UserSpecialtyEnum.nutrizionista,
            'leader_specialty': UserSpecialtyEnum.nutrizione,
            'team_type': TeamTypeEnum.nutrizione,
            'department': departments["Nutrizione"],
            'domain': 'nutrizione.test.local',
            'team_prefix': 'Nutrition'
        },
        'coach': {
            'role_specialty': UserSpecialtyEnum.coach,
            'leader_specialty': UserSpecialtyEnum.coach,
            'team_type': TeamTypeEnum.coach,
            'department': departments["Coaching"],
            'domain': 'coaching.test.local',
            'team_prefix': 'Coach'
        },
        'psicologo': {
            'role_specialty': UserSpecialtyEnum.psicologo,
            'leader_specialty': UserSpecialtyEnum.psicologia,
            'team_type': TeamTypeEnum.psicologia,
            'department': departments["Psicologia"],
            'domain': 'psico.test.local',
            'team_prefix': 'Psico'
        },
    }
    
    for prof_type, config in specialty_config.items():
        print(f"  Creando {count_per_type} {prof_type}...")
        
        # Verifica se il team esiste già
        team_name = f"Team {config['team_prefix']} Alpha"
        existing_team = Team.query.filter_by(
            name=team_name,
            team_type=config['team_type']
        ).first()
        
        if existing_team:
            print(f"    ℹ️  Team '{team_name}' già esistente, usando quello")
            teams[prof_type].append(existing_team)
            
            # Usa i membri esistenti del team
            existing_members = existing_team.members
            professionals[prof_type].extend(existing_members)
            print(f"    ✅ {len(existing_members)} {prof_type} già nel team")
            continue
        
        # Crea team leader (primo professionista)
        is_female = random.random() < 0.6
        first_name = random.choice(NOMI_FEMMINILI if is_female else NOMI_MASCHILI)
        last_name = random.choice(COGNOMI)
        
        team_leader = User(
            email=generate_email(first_name, last_name, config['domain'], 'lead'),
            password_hash=generate_password_hash("Test1234!"),
            first_name=first_name,
            last_name=last_name,
            role=UserRoleEnum.team_leader,
            specialty=config['leader_specialty'],
            is_admin=False,
            is_active=True
        )
        db.session.add(team_leader)
        db.session.flush()
        
        # Crea team
        team = Team(
            name=team_name,
            team_type=config['team_type'],
            head_id=team_leader.id,
            is_active=True,
            description=f"Team principale {prof_type}"
        )
        db.session.add(team)
        db.session.flush()
        
        # Assegna team leader al team (via relationship)
        team.members.append(team_leader)
        teams[prof_type].append(team)
        professionals[prof_type].append(team_leader)
        
        # Crea altri professionisti (membri del team)
        for i in range(count_per_type - 1):
            is_female = random.random() < 0.6
            first_name = random.choice(NOMI_FEMMINILI if is_female else NOMI_MASCHILI)
            last_name = random.choice(COGNOMI)
            
            user = User(
                email=generate_email(first_name, last_name, config['domain'], i),
                password_hash=generate_password_hash("Test1234!"),
                first_name=first_name,
                last_name=last_name,
                role=UserRoleEnum.professionista,
                specialty=config['role_specialty'],
                is_admin=False,
                is_active=random.random() < 0.95
            )
            db.session.add(user)
            # Assegna user al team (via relationship)
            team.members.append(user)
            professionals[prof_type].append(user)
        
        print(f"    ✅ {len(professionals[prof_type])} {prof_type} (1 team leader + {count_per_type-1} membri)")
    
    db.session.commit()
    return professionals, teams

def seed_patients(db, Cliente, TipologiaClienteEnum, StatoClienteEnum, 
                 professionals, count=50):
    """Crea pazienti con diverse tipologie"""
    print(f"\n🏥 Creazione {count} pazienti...")
    
    patients = []
    
    # Distribuzione tipologie: 20% VIP, 30% Premium, 50% Standard
    tipologie_weights = [
        (TipologiaClienteEnum.a, 0.20),  # VIP
        (TipologiaClienteEnum.b, 0.30),  # Premium
        (TipologiaClienteEnum.c, 0.50),  # Standard
    ]
    
    # Distribuzione stati realistici
    stati_weights = [
        (StatoClienteEnum.attivo, 0.70),
        (StatoClienteEnum.ghost, 0.15),
        (StatoClienteEnum.pausa, 0.10),
        (StatoClienteEnum.stop, 0.05),
    ]
    
    # Piattaforma lista nutrizionisti, coach, psicologi
    nutrizionisti = professionals.get('nutrizionista', [])
    coaches = professionals.get('coach', [])
    psicologi = professionals.get('psicologo', [])
    
    for i in range(count):
        # 60% donne (target tipico)
        is_female = random.random() < 0.6
        first_name = random.choice(NOMI_FEMMINILI if is_female else NOMI_MASCHILI)
        last_name = random.choice(COGNOMI)
        
        # Seleziona tipologia con pesi
        tipologia = random.choices(
            [t[0] for t in tipologie_weights],
            weights=[t[1] for t in tipologie_weights]
        )[0]
        
        # Seleziona stato con pesi
        stato = random.choices(
            [s[0] for s in stati_weights],
            weights=[s[1] for s in stati_weights]
        )[0]
        
        # Data inizio abbonamento (ultimi 12 mesi)
        data_inizio = date.today() - timedelta(days=random.randint(0, 365))
        durata_giorni = random.choice([90, 180, 365])  # 3, 6, 12 mesi
        
        # Assegna professionisti casuali (80% dei pazienti hanno almeno un professionista)
        assign_nutrizionista = random.random() < 0.80 and nutrizionisti
        assign_coach = random.random() < 0.60 and coaches
        assign_psicologo = random.random() < 0.30 and psicologi
        
        cliente = Cliente(
            nome_cognome=f"{first_name} {last_name}",
            mail=generate_email(first_name, last_name, "patient.test.local", i),
            data_di_nascita=generate_birth_date(),
            genere='donna' if is_female else 'uomo',  # String, not enum
            numero_telefono=generate_phone(),
            indirizzo=generate_address(),
            professione=random.choice(PROFESSIONI),
            paese='Italia',
            
            # Tipologia e stato
            tipologia_cliente=tipologia,
            stato_cliente=stato,
            
            # Programma
            programma_attuale=random.choice(['3 mesi', '6 mesi', '12 mesi']),
            data_inizio_abbonamento=data_inizio,
            durata_programma_giorni=durata_giorni,
            
            # Professionisti (assegnazione casuale)
            nutrizionista_id=random.choice(nutrizionisti).id if assign_nutrizionista else None,
            coach_id=random.choice(coaches).id if assign_coach else None,
            psicologa_id=random.choice(psicologi).id if assign_psicologo else None,
        )
        
        db.session.add(cliente)
        patients.append(cliente)
    
    db.session.commit()
    
    # Statistiche
    stats = {
        'vip': sum(1 for p in patients if p.tipologia_cliente == TipologiaClienteEnum.a),
        'premium': sum(1 for p in patients if p.tipologia_cliente == TipologiaClienteEnum.b),
        'standard': sum(1 for p in patients if p.tipologia_cliente == TipologiaClienteEnum.c),
        'attivi': sum(1 for p in patients if p.stato_cliente == StatoClienteEnum.attivo),
        'donne': sum(1 for p in patients if p.genere == 'donna'),
        'uomini': sum(1 for p in patients if p.genere == 'uomo'),
    }
    
    print(f"  ✅ Creati {len(patients)} pazienti")
    print(f"     Tipologie: {stats['vip']} VIP, {stats['premium']} Premium, {stats['standard']} Standard")
    print(f"     Stati: {stats['attivi']} Attivi, {len(patients)-stats['attivi']} Altri")
    print(f"     Genere: {stats['donne']} Donne, {stats['uomini']} Uomini")
    
    return patients

# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='Seed test data for Suite Clinica')
    parser.add_argument('--clean', action='store_true', help='Clean existing data before seeding')
    parser.add_argument('--patients', type=int, default=50, help='Number of patients to create (default: 50)')
    parser.add_argument('--professionals', type=int, default=10, help='Number of professionals per type (default: 10)')
    
    args = parser.parse_args()
    
    # Import models
    from corposostenibile import create_app
    from corposostenibile.extensions import db
    from corposostenibile.models import (
        Department, User, Team, Cliente,
        UserRoleEnum, UserSpecialtyEnum, TeamTypeEnum,
        TipologiaClienteEnum, StatoClienteEnum
    )
    
    app = create_app()
    
    with app.app_context():
        print("=" * 70)
        print("🌱 SUITE CLINICA - TEST DATA SEED")
        print("=" * 70)
        
        # Pulizia database se richiesta
        if args.clean:
            print("\n🗑️  Pulizia database...")
            confirm = input("⚠️  Confermi eliminazione di TUTTI i dati? (scrivi 'SI' per confermare): ")
            if confirm == 'SI':
                Cliente.query.delete()
                Team.query.delete()
                User.query.delete()
                Department.query.delete()
                db.session.commit()
                print("  ✅ Database pulito")
            else:
                print("  ❌ Pulizia annullata - procedendo con dati esistenti")
        
        # Seed operations
        start_time = datetime.now()
        
        departments = seed_departments(db, Department)
        admin = seed_admin_users(db, User, Department, UserRoleEnum, UserSpecialtyEnum)
        professionals, teams = seed_professionals(db, User, Department, Team, departments, args.professionals)
        patients = seed_patients(db, Cliente, TipologiaClienteEnum, StatoClienteEnum, 
                               professionals, args.patients)
        
        # Riepilogo finale
        elapsed = (datetime.now() - start_time).total_seconds()
        
        print("\n" + "=" * 70)
        print("📊 RIEPILOGO FINALE")
        print("=" * 70)
        
        total_users = User.query.count()
        total_teams = Team.query.count()
        total_patients = Cliente.query.count()
        total_departments = Department.query.count()
        
        print(f"\n✅ Seed completato in {elapsed:.1f} secondi")
        print(f"\n📈 Totali nel database:")
        print(f"   Dipartimenti: {total_departments}")
        print(f"   Utenti: {total_users}")
        print(f"   Team: {total_teams}")
        print(f"   Pazienti: {total_patients}")
        
        print(f"\n🔑 Credenziali di accesso:")
        print(f"   Admin: admin@test.local / Test1234!")
        print(f"   Professionisti: [email]@test.local / Test1234!")
        
        print(f"\n📝 Prossimi passi:")
        print(f"   1. Verifica il login con le credenziali admin")
        print(f"   2. Naviga nella sezione pazienti per vedere VIP/Premium/Standard")
        print(f"   3. Estendi lo script aggiungendo più dati (anamnesi, check, etc.)")
        print(f"\n✨ Buon testing!")

if __name__ == '__main__':
    main()
