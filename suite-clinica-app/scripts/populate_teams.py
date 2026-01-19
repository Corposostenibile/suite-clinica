#!/usr/bin/env python3
"""
Script per creare team e distribuire i professionisti equamente.

- Nutrizione: 3 team totali (ne esistono già 2, ne crea 1)
- Coach: 3 team totali
- Psicologia: 3 team totali

Uso:
    cd /Users/matteovolpara/Desktop/suite_clinica/suite-clinica-app
    python scripts/populate_teams.py
"""

import sys
import os

# Aggiungi il path del progetto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import User, Team, TeamTypeEnum, UserSpecialtyEnum


# Configurazione team da creare
TEAM_CONFIG = {
    'nutrizione': {
        'target_count': 3,
        'names': ['Team Nutrizione Alpha', 'Team Nutrizione Beta', 'Team Nutrizione Gamma'],
        'specialties': ['nutrizionista', 'nutrizione']
    },
    'coach': {
        'target_count': 3,
        'names': ['Team Coach Alpha', 'Team Coach Beta', 'Team Coach Gamma'],
        'specialties': ['coach']
    },
    'psicologia': {
        'target_count': 3,
        'names': ['Team Psicologia Alpha', 'Team Psicologia Beta', 'Team Psicologia Gamma'],
        'specialties': ['psicologo', 'psicologia']
    }
}


def get_professionals_by_type(team_type):
    """Recupera i professionisti per tipo di team."""
    config = TEAM_CONFIG[team_type]
    specialties = config['specialties']

    # Query professionisti con specialty corrispondente
    professionals = User.query.filter(
        User.is_active == True,
        User.specialty.isnot(None)
    ).all()

    # Filtra per specialty
    filtered = []
    for p in professionals:
        spec_value = p.specialty.value if hasattr(p.specialty, 'value') else str(p.specialty)
        if spec_value and spec_value.lower() in [s.lower() for s in specialties]:
            filtered.append(p)

    return filtered


def get_team_leaders_by_type(team_type):
    """Recupera i team leader per tipo di team."""
    config = TEAM_CONFIG[team_type]
    specialties = config['specialties']

    # Query team leaders
    leaders = User.query.filter(
        User.is_active == True,
        User.role.isnot(None)
    ).all()

    # Filtra per role=team_leader e specialty corrispondente
    filtered = []
    for l in leaders:
        role_value = l.role.value if hasattr(l.role, 'value') else str(l.role)
        spec_value = l.specialty.value if hasattr(l.specialty, 'value') else str(l.specialty) if l.specialty else ''

        if role_value == 'team_leader' and spec_value.lower() in [s.lower() for s in specialties]:
            filtered.append(l)

    return filtered


def distribute_equally(items, num_groups):
    """Distribuisce items equamente in num_groups gruppi."""
    groups = [[] for _ in range(num_groups)]
    for i, item in enumerate(items):
        groups[i % num_groups].append(item)
    return groups


def main():
    print("=" * 60)
    print("SCRIPT CREAZIONE TEAM E DISTRIBUZIONE PROFESSIONISTI")
    print("=" * 60)

    app = create_app()

    with app.app_context():
        for team_type in ['nutrizione', 'coach', 'psicologia']:
            config = TEAM_CONFIG[team_type]
            target = config['target_count']
            names = config['names']

            print(f"\n{'='*60}")
            print(f"TEAM {team_type.upper()}")
            print(f"{'='*60}")

            # 1. Conta team esistenti
            existing_teams = Team.query.filter_by(
                team_type=TeamTypeEnum(team_type),
                is_active=True
            ).all()
            existing_count = len(existing_teams)
            print(f"\n[1] Team esistenti: {existing_count}")
            for t in existing_teams:
                print(f"    - {t.name} (ID: {t.id}, membri: {t.member_count})")

            # 2. Calcola quanti team creare
            to_create = max(0, target - existing_count)
            print(f"\n[2] Team da creare: {to_create} (target: {target})")

            # 3. Recupera professionisti e team leader
            professionals = get_professionals_by_type(team_type)
            leaders = get_team_leaders_by_type(team_type)
            print(f"\n[3] Professionisti trovati: {len(professionals)}")
            for p in professionals:
                print(f"    - {p.full_name} (ID: {p.id})")
            print(f"    Team leaders trovati: {len(leaders)}")
            for l in leaders:
                print(f"    - {l.full_name} (ID: {l.id})")

            # 4. Crea nuovi team se necessario
            all_teams = list(existing_teams)
            if to_create > 0:
                print(f"\n[4] Creazione {to_create} nuovi team...")

                # Trova nomi non usati
                existing_names = [t.name for t in existing_teams]
                available_names = [n for n in names if n not in existing_names]

                # Trova leader non assegnati
                assigned_leader_ids = [t.head_id for t in existing_teams if t.head_id]
                available_leaders = [l for l in leaders if l.id not in assigned_leader_ids]

                for i in range(to_create):
                    name = available_names[i] if i < len(available_names) else f"Team {team_type.title()} {existing_count + i + 1}"
                    head = available_leaders[i] if i < len(available_leaders) else None

                    new_team = Team(
                        name=name,
                        team_type=TeamTypeEnum(team_type),
                        head_id=head.id if head else None,
                        is_active=True,
                        description=f"Team {team_type} creato automaticamente"
                    )
                    db.session.add(new_team)
                    db.session.flush()
                    all_teams.append(new_team)
                    print(f"    Creato: {name} (head: {head.full_name if head else 'Nessuno'})")
            else:
                print(f"\n[4] Nessun team da creare")

            # 5. Distribuisci professionisti nei team
            print(f"\n[5] Distribuzione professionisti nei {len(all_teams)} team...")

            # Prima rimuovi tutti i membri esistenti dai team
            for team in all_teams:
                team.members = []

            # Distribuisci equamente
            if professionals and all_teams:
                groups = distribute_equally(professionals, len(all_teams))
                for idx, team in enumerate(all_teams):
                    team.members = groups[idx]
                    member_names = [m.full_name for m in groups[idx]]
                    print(f"    {team.name}: {len(groups[idx])} membri")
                    for m in member_names:
                        print(f"      - {m}")

        # 6. Commit
        print(f"\n{'='*60}")
        print("SALVATAGGIO")
        print(f"{'='*60}")
        db.session.commit()
        print("Completato!")

        # 7. Riepilogo finale
        print(f"\n{'='*60}")
        print("RIEPILOGO FINALE")
        print(f"{'='*60}")

        for team_type in ['nutrizione', 'coach', 'psicologia']:
            teams = Team.query.filter_by(
                team_type=TeamTypeEnum(team_type),
                is_active=True
            ).all()
            print(f"\n{team_type.upper()}: {len(teams)} team")
            for t in teams:
                head_name = t.head.full_name if t.head else "Nessuno"
                print(f"  - {t.name} (head: {head_name}, membri: {t.member_count})")

        print("\n" + "=" * 60)
        print("SCRIPT COMPLETATO CON SUCCESSO!")
        print("=" * 60)


if __name__ == "__main__":
    main()
