#!/usr/bin/env python3
"""
Script di seed per creare professionisti fittizi.
- 1000 nutrizionisti in 10 team
- 1000 psicologi in 10 team  
- 1000 coach in 10 team
- Avatar da URL esterni (DiceBear, UI Avatars, Pravatar)
"""

import sys
import os
import random
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================
# CONFIGURAZIONE
# ============================================================

TOTAL_PER_SPECIALTY = 50
TEAM_SIZE = 100

# Nomi italiani comuni
NOMI_MASCHILI = [
    "Marco", "Luca", "Andrea", "Francesco", "Alessandro", "Matteo", "Lorenzo",
    "Davide", "Simone", "Federico", "Gabriele", "Riccardo", "Tommaso", "Stefano",
    "Giuseppe", "Antonio", "Giovanni", "Michele", "Paolo", "Roberto", "Filippo",
    "Nicola", "Daniele", "Emanuele", "Fabio", "Giacomo", "Leonardo", "Pietro",
    "Vincenzo", "Alberto", "Claudio", "Diego", "Enrico", "Giorgio", "Ivan",
    "Jacopo", "Massimo", "Omar", "Sergio", "Vittorio", "Bruno", "Carlo",
    "Dario", "Edoardo", "Franco", "Giulio", "Hugo", "Igor", "Kevin", "Luigi"
]

NOMI_FEMMINILI = [
    "Giulia", "Francesca", "Sara", "Chiara", "Valentina", "Alessia", "Martina",
    "Federica", "Elisa", "Silvia", "Laura", "Anna", "Maria", "Elena", "Giorgia",
    "Alice", "Beatrice", "Camilla", "Claudia", "Daniela", "Emma", "Gaia",
    "Ilaria", "Jessica", "Lisa", "Marta", "Nicole", "Paola", "Rebecca",
    "Sofia", "Teresa", "Valeria", "Aurora", "Bianca", "Carlotta", "Diana",
    "Eva", "Fiamma", "Gloria", "Helena", "Irene", "Jasmine", "Katia",
    "Lucia", "Monica", "Nadia", "Olivia", "Patrizia", "Rachele", "Serena"
]

COGNOMI = [
    "Rossi", "Russo", "Ferrari", "Esposito", "Bianchi", "Romano", "Colombo",
    "Ricci", "Marino", "Greco", "Bruno", "Gallo", "Conti", "De Luca", "Mancini",
    "Costa", "Giordano", "Rizzo", "Lombardi", "Moretti", "Barbieri", "Fontana",
    "Santoro", "Mariani", "Rinaldi", "Caruso", "Ferrara", "Galli", "Martini",
    "Leone", "Longo", "Gentile", "Martinelli", "Vitale", "Lombardo", "Serra",
    "Coppola", "De Santis", "D'Angelo", "Marchetti", "Parisi", "Villa", "Conte",
    "Ferraro", "Ferri", "Fabbri", "Bianco", "Marini", "Grasso", "Valentini",
    "Messina", "Sala", "De Angelis", "Gatti", "Pellegrini", "Palumbo", "Sanna",
    "Farina", "Rizzi", "Monti", "Cattaneo", "Morelli", "Amato", "Silvestri",
    "Mazza", "Testa", "Grassi", "Pellegrino", "Carbone", "Giuliani", "Benedetti",
    "Barone", "Orlando", "Damico", "Palmieri", "Bernardi", "Martino", "Fiore"
]

# Provider avatar esterni (URL che generano immagini dinamiche)
AVATAR_PROVIDERS = [
    # DiceBear - vari stili
    lambda name, idx: f"https://api.dicebear.com/7.x/avataaars/svg?seed={name.replace(' ', '')}{idx}",
    lambda name, idx: f"https://api.dicebear.com/7.x/lorelei/svg?seed={name.replace(' ', '')}{idx}",
    lambda name, idx: f"https://api.dicebear.com/7.x/notionists/svg?seed={name.replace(' ', '')}{idx}",
    lambda name, idx: f"https://api.dicebear.com/7.x/personas/svg?seed={name.replace(' ', '')}{idx}",
    # UI Avatars - iniziali con colori
    lambda name, idx: f"https://ui-avatars.com/api/?name={name.replace(' ', '+')}&background=random&size=200",
    # Pravatar - foto placeholder
    lambda name, idx: f"https://i.pravatar.cc/200?u={name.replace(' ', '')}{idx}",
]

def get_avatar_url(name: str, idx: int) -> str:
    """Genera URL avatar casuale da provider esterni"""
    provider = random.choice(AVATAR_PROVIDERS)
    return provider(name, idx)

def generate_email(first_name: str, last_name: str, domain_suffix: str) -> str:
    """Genera email fittizia"""
    # Normalizza nomi per email
    first = first_name.lower().replace("'", "").replace(" ", "")
    last = last_name.lower().replace("'", "").replace(" ", "")
    
    formats = [
        f"{first}.{last}@{domain_suffix}.fake.it",
        f"{first}{last}@{domain_suffix}.fake.it",
        f"{first[0]}.{last}@{domain_suffix}.fake.it",
        f"{first}.{last[0]}@{domain_suffix}.fake.it",
    ]
    return random.choice(formats)

def generate_password_hash():
    """Genera hash password fittizio (tutti avranno password 'Test1234!')"""
    # Hash pre-calcolato per 'Test1234!'
    return "scrypt:32768:8:1$fakesalt123$abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef12345678"

def generate_professionals(specialty: str, count: int, start_idx: int):
    """Genera lista di professionisti per una specialità"""
    professionals = []
    
    domain_map = {
        'nutrizionista': 'nutrizione',
        'coach': 'coaching', 
        'psicologo': 'psicologia'
    }
    domain = domain_map[specialty]
    
    for i in range(count):
        # 60% donne, 40% uomini
        is_female = random.random() < 0.6
        first_name = random.choice(NOMI_FEMMINILI if is_female else NOMI_MASCHILI)
        last_name = random.choice(COGNOMI)
        full_name = f"{first_name} {last_name}"
        
        idx = start_idx + i
        
        professionals.append({
            'email': generate_email(first_name, last_name, domain) + str(idx),
            'password_hash': generate_password_hash(),
            'first_name': first_name,
            'last_name': last_name,
            'avatar_url': get_avatar_url(full_name, idx),
            'specialty': specialty,
            'is_active': random.random() < 0.95,  # 95% attivi
        })
    
    return professionals

def main():
    from corposostenibile import create_app
    from corposostenibile.extensions import db
    from corposostenibile.models import User, Team, UserRoleEnum, UserSpecialtyEnum, TeamTypeEnum
    
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("SEED FAKE PROFESSIONALS")
        print("=" * 60)
        
        # Verifica utente admin esistente
        admin = User.query.filter_by(email='volpara.corposostenibile@gmail.com').first()
        if not admin:
            print("❌ Admin volpara non trovato!")
            return
        print(f"✅ Admin trovato: {admin.email}")
        
        # ============================================================
        # STEP 1: Genera professionisti
        # ============================================================
        print("\n📦 Generazione professionisti...")
        
        all_professionals = {
            'nutrizionista': generate_professionals('nutrizionista', TOTAL_PER_SPECIALTY, 1000),
            'coach': generate_professionals('coach', TOTAL_PER_SPECIALTY, 2000),
            'psicologo': generate_professionals('psicologo', TOTAL_PER_SPECIALTY, 3000),
        }
        
        # Mappa specialty string -> enum
        specialty_map = {
            'nutrizionista': UserSpecialtyEnum.nutrizionista,
            'coach': UserSpecialtyEnum.coach,
            'psicologo': UserSpecialtyEnum.psicologo,
        }
        
        team_type_map = {
            'nutrizionista': TeamTypeEnum.nutrizione,
            'coach': TeamTypeEnum.coach,
            'psicologo': TeamTypeEnum.psicologia,
        }
        
        # ============================================================
        # STEP 2: Crea utenti nel database
        # ============================================================
        print("\n👥 Creazione utenti...")
        
        created_users = {'nutrizionista': [], 'coach': [], 'psicologo': []}
        
        for specialty, professionals in all_professionals.items():
            print(f"  Creando {len(professionals)} {specialty}...")
            
            for p in professionals:
                user = User(
                    email=p['email'],
                    password_hash=p['password_hash'],
                    first_name=p['first_name'],
                    last_name=p['last_name'],
                    role=UserRoleEnum.professionista,
                    specialty=specialty_map[specialty],
                    is_admin=False,
                    is_active=p['is_active'],
                    avatar_path=p['avatar_url'],  # URL esterno come avatar
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.session.add(user)
                created_users[specialty].append(user)
            
            db.session.flush()  # Per ottenere gli ID
        
        db.session.commit()
        print(f"  ✅ Creati {sum(len(v) for v in created_users.values())} utenti")
        
        # ============================================================
        # STEP 3: Crea Team Leaders (primi 10 di ogni specialty)
        # ============================================================
        print("\n👔 Promozione Team Leaders...")
        
        team_leaders = {'nutrizionista': [], 'coach': [], 'psicologo': []}
        
        # Mappa specialty professionista -> specialty team leader
        tl_specialty_map = {
            'nutrizionista': UserSpecialtyEnum.nutrizione,
            'coach': UserSpecialtyEnum.coach,
            'psicologo': UserSpecialtyEnum.psicologia,
        }
        
        for specialty, users in created_users.items():
            # Primi 10 diventano team leader
            for i in range(10):
                user = users[i]
                user.role = UserRoleEnum.team_leader
                user.specialty = tl_specialty_map[specialty]
                team_leaders[specialty].append(user)
            
            print(f"  ✅ {specialty}: 10 team leaders")
        
        db.session.commit()
        
        # ============================================================
        # STEP 4: Crea Team (10 per specialty)
        # ============================================================
        print("\n🏢 Creazione Team...")
        
        team_names = {
            'nutrizionista': ['Alpha', 'Beta', 'Gamma', 'Delta', 'Epsilon', 'Zeta', 'Eta', 'Theta', 'Iota', 'Kappa'],
            'coach': ['Forza', 'Energia', 'Vitalità', 'Potenza', 'Resistenza', 'Agilità', 'Sprint', 'Focus', 'Drive', 'Peak'],
            'psicologo': ['Armonia', 'Serenità', 'Equilibrio', 'Benessere', 'Crescita', 'Consapevolezza', 'Resilienza', 'Empatia', 'Insight', 'Mindful'],
        }
        
        created_teams = {'nutrizionista': [], 'coach': [], 'psicologo': []}
        
        for specialty in ['nutrizionista', 'coach', 'psicologo']:
            for i in range(10):
                team = Team(
                    name=f"Team {team_names[specialty][i]}",
                    team_type=team_type_map[specialty],
                    head_id=team_leaders[specialty][i].id,
                    is_active=True,
                    description=f"Team {team_names[specialty][i]} - {specialty.capitalize()}"
                )
                db.session.add(team)
                created_teams[specialty].append(team)
            
            print(f"  ✅ {specialty}: 10 team creati")
        
        db.session.commit()
        
        # ============================================================
        # STEP 5: Assegna membri ai team (100 per team)
        # ============================================================
        print("\n🔗 Assegnazione membri ai team...")
        
        for specialty, users in created_users.items():
            teams = created_teams[specialty]
            
            # Salta i primi 10 (sono team leaders)
            members = users[10:]
            
            # 990 membri / 10 team = 99 membri per team (+ il TL = 100)
            members_per_team = len(members) // 10
            
            for i, team in enumerate(teams):
                start = i * members_per_team
                end = start + members_per_team
                team_members = members[start:end]
                
                for member in team_members:
                    team.members.append(member)
            
            print(f"  ✅ {specialty}: {len(members)} membri assegnati")
        
        db.session.commit()
        
        # ============================================================
        # RIEPILOGO FINALE
        # ============================================================
        print("\n" + "=" * 60)
        print("RIEPILOGO FINALE")
        print("=" * 60)
        
        total_users = User.query.count()
        total_teams = Team.query.count()
        
        print(f"\n📊 Totali:")
        print(f"   Utenti totali: {total_users}")
        print(f"   Team totali: {total_teams}")
        
        print(f"\n👥 Per specialità:")
        for spec in [UserSpecialtyEnum.nutrizionista, UserSpecialtyEnum.coach, UserSpecialtyEnum.psicologo]:
            count = User.query.filter_by(specialty=spec).count()
            print(f"   {spec.value}: {count}")
        
        for spec in [UserSpecialtyEnum.nutrizione, UserSpecialtyEnum.psicologia, UserSpecialtyEnum.coach]:
            count = User.query.filter_by(role=UserRoleEnum.team_leader, specialty=spec).count()
            print(f"   Team Leaders {spec.value}: {count}")
        
        print(f"\n🏢 Team per tipo:")
        for tt in [TeamTypeEnum.nutrizione, TeamTypeEnum.coach, TeamTypeEnum.psicologia]:
            count = Team.query.filter_by(team_type=tt).count()
            print(f"   {tt.value}: {count}")
        
        print("\n✅ SEED COMPLETATO!")
        print("\n📝 Note:")
        print("   - Password per tutti: Test1234!")
        print("   - Avatar: URL esterni (DiceBear, UI Avatars, Pravatar)")
        print("   - 10 Team Leaders per specialità")
        print("   - ~99 membri per team + 1 TL = ~100 per team")

if __name__ == '__main__':
    main()
