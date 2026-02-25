#!/usr/bin/env python3
"""
Script di seed per assegnare professionisti ai 50.000 clienti.
Assegna nutrizionista, coach, psicologo in base al programma del cliente.

Programmi:
- N = solo nutrizionista
- C = solo coach
- P = solo psicologo
- N+C = nutrizionista + coach
- N+P = nutrizionista + psicologo
- C+P = coach + psicologo
- N+C+P = tutti e tre
"""

import sys
import os
import random
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================
# CONFIGURAZIONE
# ============================================================

BATCH_SIZE = 1000

# Mappa programma -> professionisti necessari
PROGRAMMA_TO_PROFESSIONISTI = {
    'N': ['nutrizionista'],
    'C': ['coach'],
    'P': ['psicologa'],
    'N+C': ['nutrizionista', 'coach'],
    'N+P': ['nutrizionista', 'psicologa'],
    'C+P': ['coach', 'psicologa'],
    'N+C+P': ['nutrizionista', 'coach', 'psicologa'],
}


def main():
    from corposostenibile import create_app
    from corposostenibile.extensions import db
    from corposostenibile.models import Cliente, User, UserSpecialtyEnum, UserRoleEnum

    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("SEED CLIENTS - Step 4: Assegnazione Professionisti")
        print("=" * 60)

        # ============================================================
        # CARICA PROFESSIONISTI DISPONIBILI
        # ============================================================
        print("\n📋 Caricamento professionisti...")

        # Nutrizionisti (specialty = nutrizionista)
        nutrizionisti = User.query.filter(
            User.specialty == UserSpecialtyEnum.nutrizionista,
            User.is_active == True
        ).all()
        print(f"   Nutrizionisti attivi: {len(nutrizionisti)}")

        # Coach (specialty = coach)
        coaches = User.query.filter(
            User.specialty == UserSpecialtyEnum.coach,
            User.is_active == True
        ).all()
        print(f"   Coach attivi: {len(coaches)}")

        # Psicologi (specialty = psicologo)
        psicologi = User.query.filter(
            User.specialty == UserSpecialtyEnum.psicologo,
            User.is_active == True
        ).all()
        print(f"   Psicologi attivi: {len(psicologi)}")

        if not nutrizionisti or not coaches or not psicologi:
            print("\n❌ Mancano professionisti! Assicurati di aver eseguito seed_fake_professionals.py")
            return

        # Crea liste di ID per assegnazione veloce
        nutrizionisti_ids = [u.id for u in nutrizionisti]
        coaches_ids = [u.id for u in coaches]
        psicologi_ids = [u.id for u in psicologi]

        # ============================================================
        # CONTA CLIENTI
        # ============================================================
        total_clients = Cliente.query.count()
        print(f"\n📊 Clienti da aggiornare: {total_clients:,}")

        if total_clients == 0:
            print("❌ Nessun cliente trovato.")
            return

        # ============================================================
        # ASSEGNAZIONE PROFESSIONISTI
        # ============================================================
        print(f"\n👥 Assegnazione professionisti a {total_clients:,} clienti...")

        start_time = datetime.now()
        updated = 0

        # Stats
        stats = {
            'con_1_prof': 0,
            'con_2_prof': 0,
            'con_3_prof': 0,
            'nutrizionisti_assegnati': {},
            'coach_assegnati': {},
            'psicologi_assegnati': {},
        }

        # Processa a batch
        offset = 0
        while offset < total_clients:
            clienti = Cliente.query.order_by(Cliente.cliente_id).offset(offset).limit(BATCH_SIZE).all()

            if not clienti:
                break

            for cliente in clienti:
                programma = cliente.programma_attuale or 'N+C'  # Default se mancante
                professionisti_richiesti = PROGRAMMA_TO_PROFESSIONISTI.get(programma, ['nutrizionista', 'coach'])

                # Reset assegnazioni
                cliente.nutrizionista_id = None
                cliente.coach_id = None
                cliente.psicologa_id = None

                n_prof = 0

                # Assegna nutrizionista se richiesto
                if 'nutrizionista' in professionisti_richiesti:
                    nutri_id = random.choice(nutrizionisti_ids)
                    cliente.nutrizionista_id = nutri_id
                    stats['nutrizionisti_assegnati'][nutri_id] = stats['nutrizionisti_assegnati'].get(nutri_id, 0) + 1
                    n_prof += 1

                # Assegna coach se richiesto
                if 'coach' in professionisti_richiesti:
                    coach_id = random.choice(coaches_ids)
                    cliente.coach_id = coach_id
                    stats['coach_assegnati'][coach_id] = stats['coach_assegnati'].get(coach_id, 0) + 1
                    n_prof += 1

                # Assegna psicologo se richiesto
                if 'psicologa' in professionisti_richiesti:
                    psico_id = random.choice(psicologi_ids)
                    cliente.psicologa_id = psico_id
                    stats['psicologi_assegnati'][psico_id] = stats['psicologi_assegnati'].get(psico_id, 0) + 1
                    n_prof += 1

                # Aggiorna stats
                if n_prof == 1:
                    stats['con_1_prof'] += 1
                elif n_prof == 2:
                    stats['con_2_prof'] += 1
                elif n_prof == 3:
                    stats['con_3_prof'] += 1

            db.session.commit()

            updated += len(clienti)
            progress = (updated / total_clients) * 100
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = updated / elapsed if elapsed > 0 else 0
            eta = (total_clients - updated) / rate if rate > 0 else 0

            print(f"  ✅ {updated:,}/{total_clients:,} ({progress:.1f}%) - {rate:.0f}/sec - ETA: {eta:.0f}s")

            offset += BATCH_SIZE

        # ============================================================
        # RIEPILOGO
        # ============================================================
        elapsed_total = (datetime.now() - start_time).total_seconds()

        print("\n" + "=" * 60)
        print("RIEPILOGO")
        print("=" * 60)

        print(f"\n⏱️  Tempo totale: {elapsed_total:.1f} secondi")
        print(f"   Rate: {updated/elapsed_total:.0f} clienti/secondo")

        print(f"\n📊 DISTRIBUZIONE PROFESSIONISTI:")
        print(f"   Clienti con 1 professionista: {stats['con_1_prof']:,} ({stats['con_1_prof']/total_clients*100:.1f}%)")
        print(f"   Clienti con 2 professionisti: {stats['con_2_prof']:,} ({stats['con_2_prof']/total_clients*100:.1f}%)")
        print(f"   Clienti con 3 professionisti: {stats['con_3_prof']:,} ({stats['con_3_prof']/total_clients*100:.1f}%)")

        print(f"\n📊 CARICO DI LAVORO:")

        # Nutrizionisti
        nutri_counts = list(stats['nutrizionisti_assegnati'].values())
        if nutri_counts:
            print(f"   Nutrizionisti:")
            print(f"      Min clienti: {min(nutri_counts)}")
            print(f"      Max clienti: {max(nutri_counts)}")
            print(f"      Media clienti: {sum(nutri_counts)/len(nutri_counts):.1f}")

        # Coach
        coach_counts = list(stats['coach_assegnati'].values())
        if coach_counts:
            print(f"   Coach:")
            print(f"      Min clienti: {min(coach_counts)}")
            print(f"      Max clienti: {max(coach_counts)}")
            print(f"      Media clienti: {sum(coach_counts)/len(coach_counts):.1f}")

        # Psicologi
        psico_counts = list(stats['psicologi_assegnati'].values())
        if psico_counts:
            print(f"   Psicologi:")
            print(f"      Min clienti: {min(psico_counts)}")
            print(f"      Max clienti: {max(psico_counts)}")
            print(f"      Media clienti: {sum(psico_counts)/len(psico_counts):.1f}")

        # Sample
        print("\n📋 Esempi assegnazioni:")
        samples = Cliente.query.filter(
            Cliente.programma_attuale == 'N+C+P'
        ).order_by(db.func.random()).limit(3).all()

        for c in samples:
            nutri = User.query.get(c.nutrizionista_id) if c.nutrizionista_id else None
            coach = User.query.get(c.coach_id) if c.coach_id else None
            psico = User.query.get(c.psicologa_id) if c.psicologa_id else None

            print(f"\n   {c.nome_cognome} (Programma: {c.programma_attuale})")
            if nutri:
                print(f"      Nutrizionista: {nutri.first_name} {nutri.last_name}")
            if coach:
                print(f"      Coach: {coach.first_name} {coach.last_name}")
            if psico:
                print(f"      Psicologo: {psico.first_name} {psico.last_name}")

        print("\n✅ STEP 4 COMPLETATO!")


if __name__ == '__main__':
    main()
