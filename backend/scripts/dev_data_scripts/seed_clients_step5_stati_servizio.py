#!/usr/bin/env python3
"""
Script di seed per aggiungere stati servizio e stati chat ai clienti.
Solo per i servizi che hanno un professionista assegnato.

Campi:
- stato_nutrizione / stato_cliente_chat_nutrizione / stato_nutrizione_data
- stato_coach / stato_cliente_chat_coaching / stato_coach_data
- stato_psicologia / stato_cliente_chat_psicologia / stato_psicologia_data
"""

import sys
import os
import random
from datetime import datetime, timedelta, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================
# CONFIGURAZIONE
# ============================================================

BATCH_SIZE = 1000
OGGI = date(2026, 1, 22)

# Stati possibili (coerenti con stato_cliente generale)
STATI_SERVIZIO = ['attivo', 'ghost', 'pausa', 'stop']

# Distribuzione stati basata su tipologia cliente
# Tipo A = più probabile attivo
# Tipo C = più probabile ghost/stop
STATI_WEIGHTS_BY_TIPOLOGIA = {
    'a': {'attivo': 70, 'ghost': 15, 'pausa': 10, 'stop': 5},
    'b': {'attivo': 50, 'ghost': 25, 'pausa': 15, 'stop': 10},
    'c': {'attivo': 30, 'ghost': 35, 'pausa': 15, 'stop': 20},
}

# Per clienti con stato_cliente = stop/ghost, i servizi sono più probabilmente stop/ghost
STATI_WEIGHTS_INATTIVI = {'attivo': 5, 'ghost': 40, 'pausa': 10, 'stop': 45}


def weighted_choice(weights: dict) -> str:
    """Scelta pesata"""
    options = list(weights.keys())
    probs = list(weights.values())
    return random.choices(options, weights=probs)[0]


def generate_stato_data(data_inizio: date, stato: str) -> datetime:
    """Genera data cambio stato realistica"""
    if not data_inizio:
        data_inizio = date(2024, 6, 1)

    # Lo stato è stato impostato tra data_inizio e oggi
    giorni_disponibili = (OGGI - data_inizio).days
    if giorni_disponibili <= 0:
        giorni_disponibili = 1

    # Se attivo, stato recente. Se stop/ghost, potrebbe essere più vecchio
    if stato == 'attivo':
        max_giorni = min(30, giorni_disponibili)
        giorni_fa = random.randint(0, max(0, max_giorni))
    elif stato == 'ghost':
        max_giorni = min(90, giorni_disponibili)
        min_giorni = min(7, max_giorni)
        giorni_fa = random.randint(min_giorni, max(min_giorni, max_giorni))
    elif stato == 'pausa':
        max_giorni = min(60, giorni_disponibili)
        min_giorni = min(3, max_giorni)
        giorni_fa = random.randint(min_giorni, max(min_giorni, max_giorni))
    else:  # stop
        max_giorni = min(180, giorni_disponibili)
        min_giorni = min(14, max_giorni)
        giorni_fa = random.randint(min_giorni, max(min_giorni, max_giorni))

    return datetime.combine(OGGI - timedelta(days=giorni_fa), datetime.min.time())


def main():
    from corposostenibile import create_app
    from corposostenibile.extensions import db
    from corposostenibile.models import Cliente, ClienteProfessionistaHistory

    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("SEED CLIENTS - Step 5: Stati Servizio e Chat")
        print("=" * 60)

        # ============================================================
        # CONTA CLIENTI CON PROFESSIONISTI
        # ============================================================
        total_clients = Cliente.query.count()
        print(f"\n📊 Clienti totali: {total_clients:,}")

        # Conta per tipo professionista
        clienti_con_nutri = db.session.execute(
            db.text("SELECT COUNT(DISTINCT cliente_id) FROM cliente_professionista_history WHERE tipo_professionista = 'nutrizionista' AND is_active = true")
        ).scalar()
        clienti_con_coach = db.session.execute(
            db.text("SELECT COUNT(DISTINCT cliente_id) FROM cliente_professionista_history WHERE tipo_professionista = 'coach' AND is_active = true")
        ).scalar()
        clienti_con_psico = db.session.execute(
            db.text("SELECT COUNT(DISTINCT cliente_id) FROM cliente_professionista_history WHERE tipo_professionista = 'psicologa' AND is_active = true")
        ).scalar()

        print(f"   Con nutrizionista: {clienti_con_nutri:,}")
        print(f"   Con coach: {clienti_con_coach:,}")
        print(f"   Con psicologo: {clienti_con_psico:,}")

        # ============================================================
        # CARICA ASSEGNAZIONI ATTIVE
        # ============================================================
        print("\n📋 Caricamento assegnazioni attive...")

        # Crea set di cliente_id per ogni tipo
        nutri_clients = set(
            row[0] for row in db.session.execute(
                db.text("SELECT DISTINCT cliente_id FROM cliente_professionista_history WHERE tipo_professionista = 'nutrizionista' AND is_active = true")
            ).fetchall()
        )
        coach_clients = set(
            row[0] for row in db.session.execute(
                db.text("SELECT DISTINCT cliente_id FROM cliente_professionista_history WHERE tipo_professionista = 'coach' AND is_active = true")
            ).fetchall()
        )
        psico_clients = set(
            row[0] for row in db.session.execute(
                db.text("SELECT DISTINCT cliente_id FROM cliente_professionista_history WHERE tipo_professionista = 'psicologa' AND is_active = true")
            ).fetchall()
        )

        print(f"   Set nutrizionisti: {len(nutri_clients):,} clienti")
        print(f"   Set coach: {len(coach_clients):,} clienti")
        print(f"   Set psicologi: {len(psico_clients):,} clienti")

        # ============================================================
        # AGGIORNAMENTO STATI
        # ============================================================
        print(f"\n📝 Aggiornamento stati servizio per {total_clients:,} clienti...")

        start_time = datetime.now()
        updated = 0

        # Stats
        stats = {
            'nutrizione': {'attivo': 0, 'ghost': 0, 'pausa': 0, 'stop': 0, 'none': 0},
            'coach': {'attivo': 0, 'ghost': 0, 'pausa': 0, 'stop': 0, 'none': 0},
            'psicologia': {'attivo': 0, 'ghost': 0, 'pausa': 0, 'stop': 0, 'none': 0},
        }

        # Processa a batch
        offset = 0
        while offset < total_clients:
            clienti = Cliente.query.order_by(Cliente.cliente_id).offset(offset).limit(BATCH_SIZE).all()

            if not clienti:
                break

            for cliente in clienti:
                tipologia = cliente.tipologia_cliente or 'b'
                stato_generale = cliente.stato_cliente or 'attivo'
                data_inizio = cliente.data_inizio_abbonamento

                # Determina pesi per stati servizio
                if stato_generale in ['stop', 'ghost', 'insoluto', 'freeze']:
                    weights = STATI_WEIGHTS_INATTIVI
                else:
                    weights = STATI_WEIGHTS_BY_TIPOLOGIA.get(tipologia, STATI_WEIGHTS_BY_TIPOLOGIA['b'])

                # --- NUTRIZIONE ---
                if cliente.cliente_id in nutri_clients:
                    stato = weighted_choice(weights)
                    cliente.stato_nutrizione = stato
                    cliente.stato_cliente_chat_nutrizione = stato  # Chat allineato a servizio
                    cliente.stato_nutrizione_data = generate_stato_data(data_inizio, stato)
                    stats['nutrizione'][stato] += 1
                else:
                    cliente.stato_nutrizione = None
                    cliente.stato_cliente_chat_nutrizione = None
                    cliente.stato_nutrizione_data = None
                    stats['nutrizione']['none'] += 1

                # --- COACH ---
                if cliente.cliente_id in coach_clients:
                    stato = weighted_choice(weights)
                    cliente.stato_coach = stato
                    cliente.stato_cliente_chat_coaching = stato
                    cliente.stato_coach_data = generate_stato_data(data_inizio, stato)
                    stats['coach'][stato] += 1
                else:
                    cliente.stato_coach = None
                    cliente.stato_cliente_chat_coaching = None
                    cliente.stato_coach_data = None
                    stats['coach']['none'] += 1

                # --- PSICOLOGIA ---
                if cliente.cliente_id in psico_clients:
                    stato = weighted_choice(weights)
                    cliente.stato_psicologia = stato
                    cliente.stato_cliente_chat_psicologia = stato
                    cliente.stato_psicologia_data = generate_stato_data(data_inizio, stato)
                    stats['psicologia'][stato] += 1
                else:
                    cliente.stato_psicologia = None
                    cliente.stato_cliente_chat_psicologia = None
                    cliente.stato_psicologia_data = None
                    stats['psicologia']['none'] += 1

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

        print(f"\n📊 STATI NUTRIZIONE:")
        for stato, count in stats['nutrizione'].items():
            if stato != 'none':
                pct = count / (clienti_con_nutri or 1) * 100
                print(f"   {stato:10}: {count:,} ({pct:.1f}%)")
        print(f"   (non assegnato): {stats['nutrizione']['none']:,}")

        print(f"\n📊 STATI COACH:")
        for stato, count in stats['coach'].items():
            if stato != 'none':
                pct = count / (clienti_con_coach or 1) * 100
                print(f"   {stato:10}: {count:,} ({pct:.1f}%)")
        print(f"   (non assegnato): {stats['coach']['none']:,}")

        print(f"\n📊 STATI PSICOLOGIA:")
        for stato, count in stats['psicologia'].items():
            if stato != 'none':
                pct = count / (clienti_con_psico or 1) * 100
                print(f"   {stato:10}: {count:,} ({pct:.1f}%)")
        print(f"   (non assegnato): {stats['psicologia']['none']:,}")

        # Sample
        print("\n📋 Esempio cliente (N+C+P):")
        sample = Cliente.query.filter(
            Cliente.programma_attuale == 'N+C+P',
            Cliente.stato_nutrizione.isnot(None)
        ).first()

        if sample:
            print(f"\n   {sample.nome_cognome}")
            print(f"   Stato generale: {sample.stato_cliente}")
            print(f"   Tipologia: {sample.tipologia_cliente}")
            print(f"\n   NUTRIZIONE:")
            print(f"      Stato servizio: {sample.stato_nutrizione}")
            print(f"      Stato chat: {sample.stato_cliente_chat_nutrizione}")
            print(f"      Data stato: {sample.stato_nutrizione_data}")
            print(f"\n   COACH:")
            print(f"      Stato servizio: {sample.stato_coach}")
            print(f"      Stato chat: {sample.stato_cliente_chat_coaching}")
            print(f"      Data stato: {sample.stato_coach_data}")
            print(f"\n   PSICOLOGIA:")
            print(f"      Stato servizio: {sample.stato_psicologia}")
            print(f"      Stato chat: {sample.stato_cliente_chat_psicologia}")
            print(f"      Data stato: {sample.stato_psicologia_data}")

        print("\n✅ STEP 5 COMPLETATO!")


if __name__ == '__main__':
    main()
