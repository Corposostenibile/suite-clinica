#!/usr/bin/env python3
"""
Script di seed per aggiornare i 50.000 clienti con:
- stato_cliente
- programma_attuale
- tipologia_cliente
- durata_programma_giorni
- data_inizio_abbonamento
- data_rinnovo

Date sparse dal 01/01/2024 al 22/01/2026
"""

import sys
import os
import random
from datetime import datetime, date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================
# CONFIGURAZIONE
# ============================================================

BATCH_SIZE = 1000

# Range date
DATA_INIZIO_MIN = date(2024, 1, 1)
DATA_INIZIO_MAX = date(2026, 1, 22)
OGGI = date(2026, 1, 22)

# ============================================================
# PROGRAMMI DISPONIBILI
# ============================================================

# Programmi e loro distribuzione
PROGRAMMI = {
    'N': {
        'label': 'Nutrizione',
        'weight': 15,  # 15% solo nutrizione
        'professionisti': ['nutrizionista']
    },
    'C': {
        'label': 'Coaching',
        'weight': 10,  # 10% solo coaching
        'professionisti': ['coach']
    },
    'P': {
        'label': 'Psicologia',
        'weight': 5,   # 5% solo psicologia
        'professionisti': ['psicologa']
    },
    'N+C': {
        'label': 'Nutrizione + Coaching',
        'weight': 35,  # 35% - il più comune
        'professionisti': ['nutrizionista', 'coach']
    },
    'N+P': {
        'label': 'Nutrizione + Psicologia',
        'weight': 15,  # 15%
        'professionisti': ['nutrizionista', 'psicologa']
    },
    'C+P': {
        'label': 'Coaching + Psicologia',
        'weight': 5,   # 5%
        'professionisti': ['coach', 'psicologa']
    },
    'N+C+P': {
        'label': 'Completo (N+C+P)',
        'weight': 15,  # 15% - programma completo
        'professionisti': ['nutrizionista', 'coach', 'psicologa']
    },
}

# Durate programmi in giorni
DURATE = {
    90: 25,    # 3 mesi - 25%
    180: 40,   # 6 mesi - 40% (più comune)
    270: 20,   # 9 mesi - 20%
    365: 15,   # 12 mesi - 15%
}

# Tipologie cliente
TIPOLOGIE = {
    'a': 50,   # 50% - clienti top engagement
    'b': 35,   # 35% - clienti medio engagement
    'c': 15,   # 15% - clienti basso engagement
}

# Stati cliente (dipendono dalla data)
# Se il cliente è ancora nel periodo attivo -> più probabilità di essere attivo
# Se il cliente ha finito il periodo -> più probabilità di stop/ghost


def weighted_choice(options_weights: dict):
    """Scelta pesata da dizionario {opzione: peso}"""
    options = list(options_weights.keys())
    weights = list(options_weights.values())
    return random.choices(options, weights=weights)[0]


def generate_data_inizio() -> date:
    """Genera data inizio casuale nel range specificato"""
    delta = (DATA_INIZIO_MAX - DATA_INIZIO_MIN).days
    random_days = random.randint(0, delta)
    return DATA_INIZIO_MIN + timedelta(days=random_days)


def calculate_stato(data_inizio: date, durata: int, tipologia: str) -> str:
    """
    Calcola lo stato del cliente basato su:
    - Se è ancora nel periodo di abbonamento
    - La tipologia (A più probabile attivo, C più probabile ghost)
    """
    data_fine = data_inizio + timedelta(days=durata)
    giorni_dalla_fine = (OGGI - data_fine).days

    # Cliente ancora nel periodo attivo
    if giorni_dalla_fine < 0:
        # Abbonamento ancora valido
        if tipologia == 'a':
            return weighted_choice({'attivo': 85, 'ghost': 10, 'pausa': 5})
        elif tipologia == 'b':
            return weighted_choice({'attivo': 70, 'ghost': 20, 'pausa': 10})
        else:  # c
            return weighted_choice({'attivo': 50, 'ghost': 35, 'pausa': 15})

    # Abbonamento scaduto da poco (< 30 giorni)
    elif giorni_dalla_fine < 30:
        if tipologia == 'a':
            return weighted_choice({'attivo': 60, 'stop': 20, 'ghost': 15, 'pausa': 5})
        elif tipologia == 'b':
            return weighted_choice({'attivo': 40, 'stop': 30, 'ghost': 25, 'pausa': 5})
        else:
            return weighted_choice({'attivo': 20, 'stop': 40, 'ghost': 35, 'pausa': 5})

    # Abbonamento scaduto da 30-90 giorni
    elif giorni_dalla_fine < 90:
        if tipologia == 'a':
            return weighted_choice({'attivo': 40, 'stop': 35, 'ghost': 20, 'pausa': 5})
        elif tipologia == 'b':
            return weighted_choice({'attivo': 20, 'stop': 45, 'ghost': 30, 'pausa': 5})
        else:
            return weighted_choice({'stop': 50, 'ghost': 40, 'pausa': 10})

    # Abbonamento scaduto da > 90 giorni
    else:
        if tipologia == 'a':
            return weighted_choice({'attivo': 25, 'stop': 50, 'ghost': 20, 'pausa': 5})
        elif tipologia == 'b':
            return weighted_choice({'attivo': 10, 'stop': 55, 'ghost': 30, 'pausa': 5})
        else:
            return weighted_choice({'stop': 60, 'ghost': 35, 'pausa': 5})


def main():
    from corposostenibile import create_app
    from corposostenibile.extensions import db
    from corposostenibile.models import Cliente

    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("SEED CLIENTS - Step 3: Programma, Stato, Tipologia, Date")
        print("=" * 60)

        # Conta clienti
        total_clients = Cliente.query.count()
        print(f"\n📊 Clienti da aggiornare: {total_clients:,}")

        if total_clients == 0:
            print("❌ Nessun cliente trovato.")
            return

        print(f"\n📅 Range date: {DATA_INIZIO_MIN} → {DATA_INIZIO_MAX}")
        print(f"📅 Data odierna (simulata): {OGGI}")

        # Prepara liste pesate
        programmi_weights = {k: v['weight'] for k, v in PROGRAMMI.items()}

        # ============================================================
        # AGGIORNAMENTO CLIENTI
        # ============================================================
        print(f"\n📝 Aggiornamento {total_clients:,} clienti...")

        start_time = datetime.now()
        updated = 0

        # Stats per tracking
        stats = {
            'programmi': {k: 0 for k in PROGRAMMI.keys()},
            'tipologie': {k: 0 for k in TIPOLOGIE.keys()},
            'stati': {},
            'durate': {k: 0 for k in DURATE.keys()},
        }

        # Processa a batch
        offset = 0
        while offset < total_clients:
            clienti = Cliente.query.order_by(Cliente.cliente_id).offset(offset).limit(BATCH_SIZE).all()

            if not clienti:
                break

            for cliente in clienti:
                # Genera dati
                programma = weighted_choice(programmi_weights)
                tipologia = weighted_choice(TIPOLOGIE)
                durata = weighted_choice(DURATE)
                data_inizio = generate_data_inizio()
                data_rinnovo = data_inizio + timedelta(days=durata)
                stato = calculate_stato(data_inizio, durata, tipologia)

                # Aggiorna cliente
                cliente.programma_attuale = programma
                cliente.tipologia_cliente = tipologia
                cliente.durata_programma_giorni = durata
                cliente.data_inizio_abbonamento = data_inizio
                cliente.data_rinnovo = data_rinnovo
                cliente.stato_cliente = stato

                # Aggiorna stats
                stats['programmi'][programma] += 1
                stats['tipologie'][tipologia] += 1
                stats['stati'][stato] = stats['stati'].get(stato, 0) + 1
                stats['durate'][durata] += 1

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

        print(f"\n📊 PROGRAMMI:")
        for prog, count in sorted(stats['programmi'].items(), key=lambda x: -x[1]):
            pct = count / total_clients * 100
            label = PROGRAMMI[prog]['label']
            print(f"   {prog:8} ({label:25}): {count:,} ({pct:.1f}%)")

        print(f"\n📊 TIPOLOGIE:")
        for tip, count in sorted(stats['tipologie'].items()):
            pct = count / total_clients * 100
            print(f"   Tipo {tip.upper()}: {count:,} ({pct:.1f}%)")

        print(f"\n📊 STATI:")
        for stato, count in sorted(stats['stati'].items(), key=lambda x: -x[1]):
            pct = count / total_clients * 100
            print(f"   {stato:10}: {count:,} ({pct:.1f}%)")

        print(f"\n📊 DURATE:")
        for durata, count in sorted(stats['durate'].items()):
            mesi = durata // 30
            pct = count / total_clients * 100
            print(f"   {durata:3} giorni ({mesi:2} mesi): {count:,} ({pct:.1f}%)")

        # Sample
        print("\n📋 Esempi clienti:")
        samples = Cliente.query.filter(Cliente.programma_attuale.isnot(None)).order_by(db.func.random()).limit(5).all()
        for c in samples:
            print(f"\n   {c.nome_cognome}")
            print(f"   Programma: {c.programma_attuale} | Tipo: {c.tipologia_cliente.upper()} | Stato: {c.stato_cliente}")
            print(f"   Durata: {c.durata_programma_giorni}gg | Inizio: {c.data_inizio_abbonamento} | Rinnovo: {c.data_rinnovo}")

        print("\n✅ STEP 3 COMPLETATO!")


if __name__ == '__main__':
    main()
