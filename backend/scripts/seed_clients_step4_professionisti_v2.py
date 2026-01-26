#!/usr/bin/env python3
"""
Script di seed per assegnare professionisti ai 50.000 clienti.
VERSIONE CORRETTA: Usa ClienteProfessionistaHistory + relazioni many-to-many

Il frontend Team tab legge da:
1. ClienteProfessionistaHistory - per storico con audit trail
2. Many-to-many (cliente_nutrizionisti, etc.) - per legacy/fallback
"""

import sys
import os
import random
from datetime import datetime, timedelta, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================
# CONFIGURAZIONE
# ============================================================

BATCH_SIZE = 500

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

# Motivazioni assegnazione realistiche
MOTIVAZIONI_ASSEGNAZIONE = [
    "Assegnazione iniziale al momento dell'iscrizione",
    "Prima assegnazione - nuovo cliente",
    "Assegnato in base alla disponibilità",
    "Assegnazione automatica",
    "Richiesta specifica del cliente",
    "Assegnato per competenze specifiche",
    "Assegnazione da team leader",
    "Ribilanciamento carico di lavoro",
]


def main():
    from corposostenibile import create_app
    from corposostenibile.extensions import db
    from corposostenibile.models import (
        Cliente, User, UserSpecialtyEnum,
        ClienteProfessionistaHistory
    )

    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("SEED CLIENTS - Step 4 v2: Assegnazione Professionisti")
        print("(Con ClienteProfessionistaHistory + Many-to-Many)")
        print("=" * 60)

        # ============================================================
        # PULIZIA DATI PRECEDENTI
        # ============================================================
        print("\n🗑️  Pulizia assegnazioni precedenti...")

        # Pulisci history
        deleted_history = ClienteProfessionistaHistory.query.delete()
        print(f"   Eliminati {deleted_history} record da ClienteProfessionistaHistory")

        # Pulisci many-to-many con SQL diretto (evita versioning)
        db.session.execute(db.text("DELETE FROM cliente_nutrizionisti"))
        db.session.execute(db.text("DELETE FROM cliente_coaches"))
        db.session.execute(db.text("DELETE FROM cliente_psicologi"))
        print("   Pulite tabelle many-to-many")

        db.session.commit()

        # ============================================================
        # CARICA PROFESSIONISTI DISPONIBILI
        # ============================================================
        print("\n📋 Caricamento professionisti...")

        # Nutrizionisti
        nutrizionisti = User.query.filter(
            User.specialty == UserSpecialtyEnum.nutrizionista,
            User.is_active == True
        ).all()
        print(f"   Nutrizionisti attivi: {len(nutrizionisti)}")

        # Coach
        coaches = User.query.filter(
            User.specialty == UserSpecialtyEnum.coach,
            User.is_active == True
        ).all()
        print(f"   Coach attivi: {len(coaches)}")

        # Psicologi
        psicologi = User.query.filter(
            User.specialty == UserSpecialtyEnum.psicologo,
            User.is_active == True
        ).all()
        print(f"   Psicologi attivi: {len(psicologi)}")

        if not nutrizionisti or not coaches or not psicologi:
            print("\n❌ Mancano professionisti!")
            return

        # Trova admin per assegnato_da
        admin = User.query.filter_by(email='volpara.corposostenibile@gmail.com').first()
        admin_id = admin.id if admin else 1

        # Liste ID
        nutrizionisti_ids = [u.id for u in nutrizionisti]
        coaches_ids = [u.id for u in coaches]
        psicologi_ids = [u.id for u in psicologi]

        # ============================================================
        # CONTA CLIENTI
        # ============================================================
        total_clients = Cliente.query.count()
        print(f"\n📊 Clienti da aggiornare: {total_clients:,}")

        # ============================================================
        # ASSEGNAZIONE PROFESSIONISTI
        # ============================================================
        print(f"\n👥 Creazione assegnazioni per {total_clients:,} clienti...")

        start_time = datetime.now()
        updated = 0
        history_created = 0

        # Stats
        stats = {
            'con_1_prof': 0,
            'con_2_prof': 0,
            'con_3_prof': 0,
        }

        # Processa a batch
        offset = 0
        while offset < total_clients:
            clienti = Cliente.query.order_by(Cliente.cliente_id).offset(offset).limit(BATCH_SIZE).all()

            if not clienti:
                break

            for cliente in clienti:
                programma = cliente.programma_attuale or 'N+C'
                professionisti_richiesti = PROGRAMMA_TO_PROFESSIONISTI.get(programma, ['nutrizionista', 'coach'])
                data_inizio = cliente.data_inizio_abbonamento or date(2024, 6, 1)

                n_prof = 0

                # Assegna nutrizionista
                if 'nutrizionista' in professionisti_richiesti:
                    nutri_id = random.choice(nutrizionisti_ids)

                    # Aggiorna FK diretto (per compatibilità)
                    cliente.nutrizionista_id = nutri_id

                    # Aggiungi a many-to-many con SQL diretto
                    db.session.execute(
                        db.text("INSERT INTO cliente_nutrizionisti (cliente_id, user_id) VALUES (:c, :u)"),
                        {"c": cliente.cliente_id, "u": nutri_id}
                    )

                    # Crea history record
                    history = ClienteProfessionistaHistory(
                        cliente_id=cliente.cliente_id,
                        user_id=nutri_id,
                        tipo_professionista='nutrizionista',
                        data_dal=data_inizio,
                        motivazione_aggiunta=random.choice(MOTIVAZIONI_ASSEGNAZIONE),
                        assegnato_da_id=admin_id,
                        is_active=True
                    )
                    db.session.add(history)
                    history_created += 1
                    n_prof += 1

                # Assegna coach
                if 'coach' in professionisti_richiesti:
                    coach_id = random.choice(coaches_ids)

                    cliente.coach_id = coach_id

                    db.session.execute(
                        db.text("INSERT INTO cliente_coaches (cliente_id, user_id) VALUES (:c, :u)"),
                        {"c": cliente.cliente_id, "u": coach_id}
                    )

                    history = ClienteProfessionistaHistory(
                        cliente_id=cliente.cliente_id,
                        user_id=coach_id,
                        tipo_professionista='coach',
                        data_dal=data_inizio,
                        motivazione_aggiunta=random.choice(MOTIVAZIONI_ASSEGNAZIONE),
                        assegnato_da_id=admin_id,
                        is_active=True
                    )
                    db.session.add(history)
                    history_created += 1
                    n_prof += 1

                # Assegna psicologo
                if 'psicologa' in professionisti_richiesti:
                    psico_id = random.choice(psicologi_ids)

                    cliente.psicologa_id = psico_id

                    db.session.execute(
                        db.text("INSERT INTO cliente_psicologi (cliente_id, user_id) VALUES (:c, :u)"),
                        {"c": cliente.cliente_id, "u": psico_id}
                    )

                    history = ClienteProfessionistaHistory(
                        cliente_id=cliente.cliente_id,
                        user_id=psico_id,
                        tipo_professionista='psicologa',
                        data_dal=data_inizio,
                        motivazione_aggiunta=random.choice(MOTIVAZIONI_ASSEGNAZIONE),
                        assegnato_da_id=admin_id,
                        is_active=True
                    )
                    db.session.add(history)
                    history_created += 1
                    n_prof += 1

                # Stats
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

        print(f"\n📊 RECORD CREATI:")
        print(f"   ClienteProfessionistaHistory: {history_created:,}")

        # Verifica many-to-many
        nutri_count = db.session.execute(db.text("SELECT COUNT(*) FROM cliente_nutrizionisti")).scalar()
        coach_count = db.session.execute(db.text("SELECT COUNT(*) FROM cliente_coaches")).scalar()
        psico_count = db.session.execute(db.text("SELECT COUNT(*) FROM cliente_psicologi")).scalar()

        print(f"   cliente_nutrizionisti: {nutri_count:,}")
        print(f"   cliente_coaches: {coach_count:,}")
        print(f"   cliente_psicologi: {psico_count:,}")

        print(f"\n📊 DISTRIBUZIONE:")
        print(f"   Clienti con 1 professionista: {stats['con_1_prof']:,}")
        print(f"   Clienti con 2 professionisti: {stats['con_2_prof']:,}")
        print(f"   Clienti con 3 professionisti: {stats['con_3_prof']:,}")

        # Sample
        print("\n📋 Verifica assegnazioni (sample):")
        sample_cliente = Cliente.query.filter(
            Cliente.programma_attuale == 'N+C+P'
        ).first()

        if sample_cliente:
            print(f"\n   Cliente: {sample_cliente.nome_cognome} (ID: {sample_cliente.cliente_id})")
            print(f"   Programma: {sample_cliente.programma_attuale}")

            histories = ClienteProfessionistaHistory.query.filter_by(
                cliente_id=sample_cliente.cliente_id
            ).all()

            for h in histories:
                prof = User.query.get(h.user_id)
                print(f"   → {h.tipo_professionista}: {prof.first_name} {prof.last_name} (dal {h.data_dal})")

        print("\n✅ STEP 4 v2 COMPLETATO!")
        print("   I professionisti ora appariranno nella tab Team!")


if __name__ == '__main__':
    main()
