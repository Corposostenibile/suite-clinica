#!/usr/bin/env python3
"""
Script di seed per popolare i campi Setup delle tab Nutrizione, Coaching, Psicologia.
Solo per i clienti che hanno un professionista assegnato.

NUTRIZIONE:
- call_iniziale_nutrizionista (Boolean)
- data_call_iniziale_nutrizionista (Date)
- reach_out_nutrizione (String: lunedi, martedi, etc.)

COACHING:
- call_iniziale_coach (Boolean)
- data_call_iniziale_coach (Date)
- reach_out_coaching (String: lunedi, martedi, etc.)

PSICOLOGIA:
- call_iniziale_psicologa (Boolean)
- data_call_iniziale_psicologia (Date)
- reach_out_psicologia (String: lunedi, martedi, etc.)
- sedute_psicologia_comprate (Integer)
- sedute_psicologia_svolte (Integer)
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

# Giorni della settimana per reach out
GIORNI_SETTIMANA = ['lunedi', 'martedi', 'mercoledi', 'giovedi', 'venerdi', 'sabato', 'domenica']

# Pesi per i giorni (più probabili giorni lavorativi)
GIORNI_WEIGHTS = {
    'lunedi': 20,
    'martedi': 20,
    'mercoledi': 20,
    'giovedi': 15,
    'venerdi': 15,
    'sabato': 7,
    'domenica': 3,
}

# Probabilità call iniziale completata basata su tipologia e stato
# Tipo A = più probabile che abbia fatto la call
# Stato attivo = più probabile che abbia fatto la call
CALL_PROB_BY_TIPOLOGIA = {
    'a': 0.95,  # 95% tipo A ha fatto call
    'b': 0.85,  # 85% tipo B
    'c': 0.70,  # 70% tipo C
}

CALL_PROB_BY_STATO = {
    'attivo': 1.0,   # tutti gli attivi hanno fatto call
    'ghost': 0.90,   # 90% ghost (erano attivi prima)
    'pausa': 0.95,   # 95% pausa
    'stop': 0.85,    # 85% stop
}

# Sedute psicologia
SEDUTE_COMPRATE_RANGE = {
    'a': (8, 20),   # Tipo A compra più sedute
    'b': (5, 12),   # Tipo B
    'c': (3, 8),    # Tipo C
}


def weighted_choice(weights: dict) -> str:
    """Scelta pesata"""
    options = list(weights.keys())
    probs = list(weights.values())
    return random.choices(options, weights=probs)[0]


def generate_data_call(data_inizio: date) -> datetime:
    """
    Genera data call iniziale.
    La call avviene tipicamente nei primi 7 giorni dall'inizio.
    """
    if not data_inizio:
        data_inizio = date(2024, 6, 1)

    # Call entro i primi 7 giorni dall'inizio
    giorni_dopo = random.randint(0, 7)
    data_call = data_inizio + timedelta(days=giorni_dopo)

    # Non può essere nel futuro
    if data_call > OGGI:
        data_call = OGGI

    return datetime.combine(data_call, datetime.min.time())


def calculate_sedute_svolte(comprate: int, data_inizio: date, stato: str) -> int:
    """
    Calcola sedute svolte basato su:
    - Sedute comprate
    - Tempo trascorso da inizio
    - Stato attuale
    """
    if not data_inizio:
        data_inizio = date(2024, 6, 1)

    settimane_trascorse = (OGGI - data_inizio).days // 7

    # Massimo una seduta a settimana tipicamente
    max_possibili = min(comprate, settimane_trascorse)

    if stato == 'attivo':
        # Attivi: svolte tra 70-100% del possibile
        pct = random.uniform(0.7, 1.0)
    elif stato == 'ghost':
        # Ghost: svolte tra 30-60% del possibile
        pct = random.uniform(0.3, 0.6)
    elif stato == 'pausa':
        # Pausa: svolte tra 50-80% del possibile
        pct = random.uniform(0.5, 0.8)
    else:  # stop
        # Stop: svolte tra 20-50% del possibile
        pct = random.uniform(0.2, 0.5)

    svolte = int(max_possibili * pct)
    return max(0, min(svolte, comprate))  # Mai più di comprate


def main():
    from corposostenibile import create_app
    from corposostenibile.extensions import db
    from corposostenibile.models import Cliente

    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("SEED CLIENTS - Step 6: Setup Tabs (Nutrizione, Coach, Psicologia)")
        print("=" * 60)

        # ============================================================
        # CONTA CLIENTI CON PROFESSIONISTI
        # ============================================================
        total_clients = Cliente.query.count()
        print(f"\n📊 Clienti totali: {total_clients:,}")

        # Carica set di clienti con professionisti assegnati
        print("\n📋 Caricamento assegnazioni attive...")

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

        print(f"   Con nutrizionista: {len(nutri_clients):,}")
        print(f"   Con coach: {len(coach_clients):,}")
        print(f"   Con psicologo: {len(psico_clients):,}")

        # ============================================================
        # AGGIORNAMENTO SETUP
        # ============================================================
        print(f"\n📝 Aggiornamento Setup per {total_clients:,} clienti...")

        start_time = datetime.now()
        updated = 0

        # Stats
        stats = {
            'nutrizione': {'call_si': 0, 'call_no': 0, 'reach_out': {}},
            'coach': {'call_si': 0, 'call_no': 0, 'reach_out': {}},
            'psicologia': {'call_si': 0, 'call_no': 0, 'reach_out': {}, 'sedute_totali': 0, 'svolte_totali': 0},
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

                # Calcola probabilità call basata su tipologia e stato
                prob_tipologia = CALL_PROB_BY_TIPOLOGIA.get(tipologia, 0.85)
                prob_stato = CALL_PROB_BY_STATO.get(stato_generale, 0.85)
                prob_call = prob_tipologia * prob_stato

                # --- NUTRIZIONE SETUP ---
                if cliente.cliente_id in nutri_clients:
                    # Call iniziale
                    ha_fatto_call = random.random() < prob_call
                    cliente.call_iniziale_nutrizionista = ha_fatto_call

                    if ha_fatto_call:
                        cliente.data_call_iniziale_nutrizionista = generate_data_call(data_inizio)
                        stats['nutrizione']['call_si'] += 1
                    else:
                        cliente.data_call_iniziale_nutrizionista = None
                        stats['nutrizione']['call_no'] += 1

                    # Reach out settimanale
                    giorno = weighted_choice(GIORNI_WEIGHTS)
                    cliente.reach_out_nutrizione = giorno
                    stats['nutrizione']['reach_out'][giorno] = stats['nutrizione']['reach_out'].get(giorno, 0) + 1
                else:
                    cliente.call_iniziale_nutrizionista = None
                    cliente.data_call_iniziale_nutrizionista = None
                    cliente.reach_out_nutrizione = None

                # --- COACH SETUP ---
                if cliente.cliente_id in coach_clients:
                    # Call iniziale
                    ha_fatto_call = random.random() < prob_call
                    cliente.call_iniziale_coach = ha_fatto_call

                    if ha_fatto_call:
                        cliente.data_call_iniziale_coach = generate_data_call(data_inizio)
                        stats['coach']['call_si'] += 1
                    else:
                        cliente.data_call_iniziale_coach = None
                        stats['coach']['call_no'] += 1

                    # Reach out settimanale
                    giorno = weighted_choice(GIORNI_WEIGHTS)
                    cliente.reach_out_coaching = giorno
                    stats['coach']['reach_out'][giorno] = stats['coach']['reach_out'].get(giorno, 0) + 1
                else:
                    cliente.call_iniziale_coach = None
                    cliente.data_call_iniziale_coach = None
                    cliente.reach_out_coaching = None

                # --- PSICOLOGIA SETUP ---
                if cliente.cliente_id in psico_clients:
                    # Call iniziale
                    ha_fatto_call = random.random() < prob_call
                    cliente.call_iniziale_psicologa = ha_fatto_call

                    if ha_fatto_call:
                        cliente.data_call_iniziale_psicologia = generate_data_call(data_inizio)
                        stats['psicologia']['call_si'] += 1
                    else:
                        cliente.data_call_iniziale_psicologia = None
                        stats['psicologia']['call_no'] += 1

                    # Reach out settimanale
                    giorno = weighted_choice(GIORNI_WEIGHTS)
                    cliente.reach_out_psicologia = giorno
                    stats['psicologia']['reach_out'][giorno] = stats['psicologia']['reach_out'].get(giorno, 0) + 1

                    # Sedute psicologia
                    sedute_range = SEDUTE_COMPRATE_RANGE.get(tipologia, (5, 12))
                    comprate = random.randint(sedute_range[0], sedute_range[1])
                    stato_psico = cliente.stato_psicologia or stato_generale
                    svolte = calculate_sedute_svolte(comprate, data_inizio, stato_psico)

                    cliente.sedute_psicologia_comprate = comprate
                    cliente.sedute_psicologia_svolte = svolte

                    stats['psicologia']['sedute_totali'] += comprate
                    stats['psicologia']['svolte_totali'] += svolte
                else:
                    cliente.call_iniziale_psicologa = None
                    cliente.data_call_iniziale_psicologia = None
                    cliente.reach_out_psicologia = None
                    cliente.sedute_psicologia_comprate = None
                    cliente.sedute_psicologia_svolte = None

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

        # Nutrizione
        print(f"\n📊 NUTRIZIONE SETUP:")
        nutri_total = stats['nutrizione']['call_si'] + stats['nutrizione']['call_no']
        if nutri_total > 0:
            pct_call = stats['nutrizione']['call_si'] / nutri_total * 100
            print(f"   Call iniziale completata: {stats['nutrizione']['call_si']:,} ({pct_call:.1f}%)")
            print(f"   Call iniziale mancante: {stats['nutrizione']['call_no']:,}")
            print(f"   Reach out per giorno:")
            for giorno in GIORNI_SETTIMANA:
                count = stats['nutrizione']['reach_out'].get(giorno, 0)
                pct = count / nutri_total * 100 if nutri_total > 0 else 0
                print(f"      {giorno:12}: {count:,} ({pct:.1f}%)")

        # Coach
        print(f"\n📊 COACHING SETUP:")
        coach_total = stats['coach']['call_si'] + stats['coach']['call_no']
        if coach_total > 0:
            pct_call = stats['coach']['call_si'] / coach_total * 100
            print(f"   Call iniziale completata: {stats['coach']['call_si']:,} ({pct_call:.1f}%)")
            print(f"   Call iniziale mancante: {stats['coach']['call_no']:,}")
            print(f"   Reach out per giorno:")
            for giorno in GIORNI_SETTIMANA:
                count = stats['coach']['reach_out'].get(giorno, 0)
                pct = count / coach_total * 100 if coach_total > 0 else 0
                print(f"      {giorno:12}: {count:,} ({pct:.1f}%)")

        # Psicologia
        print(f"\n📊 PSICOLOGIA SETUP:")
        psico_total = stats['psicologia']['call_si'] + stats['psicologia']['call_no']
        if psico_total > 0:
            pct_call = stats['psicologia']['call_si'] / psico_total * 100
            print(f"   Call iniziale completata: {stats['psicologia']['call_si']:,} ({pct_call:.1f}%)")
            print(f"   Call iniziale mancante: {stats['psicologia']['call_no']:,}")
            print(f"   Reach out per giorno:")
            for giorno in GIORNI_SETTIMANA:
                count = stats['psicologia']['reach_out'].get(giorno, 0)
                pct = count / psico_total * 100 if psico_total > 0 else 0
                print(f"      {giorno:12}: {count:,} ({pct:.1f}%)")

            avg_comprate = stats['psicologia']['sedute_totali'] / psico_total
            avg_svolte = stats['psicologia']['svolte_totali'] / psico_total
            pct_svolte = stats['psicologia']['svolte_totali'] / stats['psicologia']['sedute_totali'] * 100 if stats['psicologia']['sedute_totali'] > 0 else 0
            print(f"\n   SEDUTE PSICOLOGIA:")
            print(f"      Totale sedute comprate: {stats['psicologia']['sedute_totali']:,}")
            print(f"      Totale sedute svolte: {stats['psicologia']['svolte_totali']:,} ({pct_svolte:.1f}%)")
            print(f"      Media comprate per cliente: {avg_comprate:.1f}")
            print(f"      Media svolte per cliente: {avg_svolte:.1f}")

        # Sample
        print("\n📋 Esempio cliente (N+C+P):")
        sample = Cliente.query.filter(
            Cliente.programma_attuale == 'N+C+P',
            Cliente.call_iniziale_nutrizionista.isnot(None)
        ).first()

        if sample:
            print(f"\n   {sample.nome_cognome}")
            print(f"   Tipologia: {sample.tipologia_cliente} | Stato: {sample.stato_cliente}")
            print(f"\n   NUTRIZIONE SETUP:")
            print(f"      Call iniziale: {'✓' if sample.call_iniziale_nutrizionista else '✗'}")
            if sample.data_call_iniziale_nutrizionista:
                print(f"      Data call: {sample.data_call_iniziale_nutrizionista.strftime('%d/%m/%Y')}")
            print(f"      Reach out: {sample.reach_out_nutrizione}")
            print(f"\n   COACHING SETUP:")
            print(f"      Call iniziale: {'✓' if sample.call_iniziale_coach else '✗'}")
            if sample.data_call_iniziale_coach:
                print(f"      Data call: {sample.data_call_iniziale_coach.strftime('%d/%m/%Y')}")
            print(f"      Reach out: {sample.reach_out_coaching}")
            print(f"\n   PSICOLOGIA SETUP:")
            print(f"      Call iniziale: {'✓' if sample.call_iniziale_psicologa else '✗'}")
            if sample.data_call_iniziale_psicologia:
                print(f"      Data call: {sample.data_call_iniziale_psicologia.strftime('%d/%m/%Y')}")
            print(f"      Reach out: {sample.reach_out_psicologia}")
            print(f"      Sedute comprate: {sample.sedute_psicologia_comprate}")
            print(f"      Sedute svolte: {sample.sedute_psicologia_svolte}")

        print("\n✅ STEP 6 COMPLETATO!")


if __name__ == '__main__':
    main()
