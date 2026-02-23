#!/usr/bin/env python3
"""
Script di seed per popolare le Patologie di Nutrizione e Psicologia.
Solo per i clienti che hanno il professionista corrispondente assegnato.

PATOLOGIE NUTRIZIONE (17 + nessuna):
- nessuna_patologia
- patologia_ibs, patologia_reflusso, patologia_gastrite, patologia_dca
- patologia_insulino_resistenza, patologia_diabete, patologia_dislipidemie
- patologia_steatosi_epatica, patologia_ipertensione
- patologia_pcos, patologia_endometriosi (solo donne)
- patologia_obesita_sindrome, patologia_osteoporosi, patologia_diverticolite
- patologia_crohn, patologia_stitichezza, patologia_tiroidee

PATOLOGIE PSICOLOGIA (7 + nessuna):
- nessuna_patologia_psico
- patologia_psico_dca, patologia_psico_obesita_psicoemotiva
- patologia_psico_ansia_umore_cibo, patologia_psico_comportamenti_disfunzionali
- patologia_psico_immagine_corporea, patologia_psico_psicosomatiche
- patologia_psico_relazionali_altro
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

# Lista patologie nutrizione con probabilità base
PATOLOGIE_NUTRI = {
    'patologia_ibs': 0.15,              # 15% - molto comune
    'patologia_reflusso': 0.12,         # 12% - comune
    'patologia_gastrite': 0.10,         # 10%
    'patologia_dca': 0.08,              # 8% - DCA
    'patologia_insulino_resistenza': 0.18,  # 18% - molto comune
    'patologia_diabete': 0.08,          # 8%
    'patologia_dislipidemie': 0.12,     # 12%
    'patologia_steatosi_epatica': 0.10, # 10%
    'patologia_ipertensione': 0.15,     # 15% - comune
    'patologia_pcos': 0.12,             # 12% - solo donne
    'patologia_endometriosi': 0.06,     # 6% - solo donne
    'patologia_obesita_sindrome': 0.20, # 20% - molto comune (clinica dimagrimento)
    'patologia_osteoporosi': 0.05,      # 5%
    'patologia_diverticolite': 0.04,    # 4%
    'patologia_crohn': 0.02,            # 2% - rara
    'patologia_stitichezza': 0.18,      # 18% - molto comune
    'patologia_tiroidee': 0.12,         # 12%
}

# Patologie correlate (se hai una, più probabile avere l'altra)
CORRELAZIONI_NUTRI = {
    'patologia_diabete': ['patologia_insulino_resistenza', 'patologia_obesita_sindrome', 'patologia_dislipidemie'],
    'patologia_insulino_resistenza': ['patologia_obesita_sindrome', 'patologia_pcos'],
    'patologia_obesita_sindrome': ['patologia_steatosi_epatica', 'patologia_ipertensione', 'patologia_dislipidemie'],
    'patologia_ibs': ['patologia_stitichezza', 'patologia_reflusso'],
    'patologia_pcos': ['patologia_insulino_resistenza', 'patologia_tiroidee'],
    'patologia_crohn': ['patologia_ibs'],
}

# Lista patologie psicologia con probabilità base
PATOLOGIE_PSICO = {
    'patologia_psico_dca': 0.25,                        # 25% - molto comune in clinica DCA
    'patologia_psico_obesita_psicoemotiva': 0.30,       # 30% - molto comune
    'patologia_psico_ansia_umore_cibo': 0.35,           # 35% - molto comune
    'patologia_psico_comportamenti_disfunzionali': 0.20, # 20%
    'patologia_psico_immagine_corporea': 0.28,          # 28% - comune
    'patologia_psico_psicosomatiche': 0.15,             # 15%
    'patologia_psico_relazionali_altro': 0.12,          # 12%
}

# Correlazioni psicologia
CORRELAZIONI_PSICO = {
    'patologia_psico_dca': ['patologia_psico_immagine_corporea', 'patologia_psico_ansia_umore_cibo'],
    'patologia_psico_obesita_psicoemotiva': ['patologia_psico_ansia_umore_cibo', 'patologia_psico_comportamenti_disfunzionali'],
    'patologia_psico_immagine_corporea': ['patologia_psico_ansia_umore_cibo'],
}

# Probabilità "nessuna patologia" basata su tipologia
NESSUNA_PROB_BY_TIPOLOGIA = {
    'a': 0.25,  # 25% tipo A non ha patologie
    'b': 0.20,  # 20% tipo B
    'c': 0.15,  # 15% tipo C (più problematici)
}


def genera_patologie_nutri(genere: str, tipologia: str) -> dict:
    """
    Genera patologie nutrizione per un cliente.
    Considera genere (PCOS/endometriosi solo donne) e correlazioni.
    """
    result = {key: False for key in PATOLOGIE_NUTRI.keys()}
    result['nessuna_patologia'] = False

    # Check se nessuna patologia
    prob_nessuna = NESSUNA_PROB_BY_TIPOLOGIA.get(tipologia, 0.20)
    if random.random() < prob_nessuna:
        result['nessuna_patologia'] = True
        return result

    # Genera patologie con probabilità base
    patologie_attive = []
    for patologia, prob in PATOLOGIE_NUTRI.items():
        # PCOS e endometriosi solo per donne
        if patologia in ['patologia_pcos', 'patologia_endometriosi']:
            if genere != 'F':
                continue

        # Aumenta probabilità per tipo C (più problematici)
        if tipologia == 'c':
            prob *= 1.3
        elif tipologia == 'a':
            prob *= 0.8

        if random.random() < prob:
            result[patologia] = True
            patologie_attive.append(patologia)

    # Applica correlazioni
    for patologia in patologie_attive:
        if patologia in CORRELAZIONI_NUTRI:
            for correlata in CORRELAZIONI_NUTRI[patologia]:
                # 50% probabilità di avere la correlata
                if correlata in result and not result[correlata]:
                    if random.random() < 0.5:
                        result[correlata] = True

    # Se non ha nessuna patologia attiva, imposta nessuna_patologia
    if not any(v for k, v in result.items() if k != 'nessuna_patologia'):
        result['nessuna_patologia'] = True

    return result


def genera_patologie_psico(tipologia: str, ha_dca_nutri: bool = False) -> dict:
    """
    Genera patologie psicologia per un cliente.
    Considera correlazione con DCA nutrizione.
    """
    result = {key: False for key in PATOLOGIE_PSICO.keys()}
    result['nessuna_patologia_psico'] = False

    # Check se nessuna patologia
    prob_nessuna = NESSUNA_PROB_BY_TIPOLOGIA.get(tipologia, 0.20) * 0.7  # Psico ha meno "nessuna"
    if random.random() < prob_nessuna:
        result['nessuna_patologia_psico'] = True
        return result

    # Genera patologie con probabilità base
    patologie_attive = []
    for patologia, prob in PATOLOGIE_PSICO.items():
        # Se ha DCA nutrizionale, molto più probabile DCA psico
        if patologia == 'patologia_psico_dca' and ha_dca_nutri:
            prob = 0.85  # 85% se ha DCA nutrizionale

        # Aumenta probabilità per tipo C
        if tipologia == 'c':
            prob *= 1.4
        elif tipologia == 'a':
            prob *= 0.7

        if random.random() < prob:
            result[patologia] = True
            patologie_attive.append(patologia)

    # Applica correlazioni
    for patologia in patologie_attive:
        if patologia in CORRELAZIONI_PSICO:
            for correlata in CORRELAZIONI_PSICO[patologia]:
                if correlata in result and not result[correlata]:
                    if random.random() < 0.6:  # 60% correlazione
                        result[correlata] = True

    # Se non ha nessuna patologia attiva, imposta nessuna_patologia_psico
    if not any(v for k, v in result.items() if k != 'nessuna_patologia_psico'):
        result['nessuna_patologia_psico'] = True

    return result


def main():
    from corposostenibile import create_app
    from corposostenibile.extensions import db
    from corposostenibile.models import Cliente

    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("SEED CLIENTS - Step 7: Patologie (Nutrizione + Psicologia)")
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
        psico_clients = set(
            row[0] for row in db.session.execute(
                db.text("SELECT DISTINCT cliente_id FROM cliente_professionista_history WHERE tipo_professionista = 'psicologa' AND is_active = true")
            ).fetchall()
        )

        print(f"   Con nutrizionista: {len(nutri_clients):,}")
        print(f"   Con psicologo: {len(psico_clients):,}")

        # ============================================================
        # AGGIORNAMENTO PATOLOGIE
        # ============================================================
        print(f"\n📝 Aggiornamento Patologie per {total_clients:,} clienti...")

        start_time = datetime.now()
        updated = 0

        # Stats nutrizione
        stats_nutri = {
            'nessuna': 0,
            'con_patologie': 0,
            'patologie': {key: 0 for key in PATOLOGIE_NUTRI.keys()},
            'media_patologie': [],
        }

        # Stats psicologia
        stats_psico = {
            'nessuna': 0,
            'con_patologie': 0,
            'patologie': {key: 0 for key in PATOLOGIE_PSICO.keys()},
            'media_patologie': [],
        }

        # Processa a batch
        offset = 0
        while offset < total_clients:
            clienti = Cliente.query.order_by(Cliente.cliente_id).offset(offset).limit(BATCH_SIZE).all()

            if not clienti:
                break

            for cliente in clienti:
                tipologia = cliente.tipologia_cliente or 'b'
                # Determina genere dal nome (semplificato - F se primo nome finisce in 'a')
                nome_cognome = cliente.nome_cognome or ''
                # Prendi il primo nome (prima dello spazio)
                primo_nome = nome_cognome.split()[0] if nome_cognome else ''
                genere = 'F' if primo_nome.endswith('a') else 'M'

                ha_dca_nutri = False

                # --- PATOLOGIE NUTRIZIONE ---
                if cliente.cliente_id in nutri_clients:
                    patologie_nutri = genera_patologie_nutri(genere, tipologia)

                    # Applica al cliente
                    cliente.nessuna_patologia = patologie_nutri['nessuna_patologia']
                    for key in PATOLOGIE_NUTRI.keys():
                        setattr(cliente, key, patologie_nutri[key])

                    # Stats
                    if patologie_nutri['nessuna_patologia']:
                        stats_nutri['nessuna'] += 1
                    else:
                        stats_nutri['con_patologie'] += 1
                        count = sum(1 for k, v in patologie_nutri.items() if v and k != 'nessuna_patologia')
                        stats_nutri['media_patologie'].append(count)

                    for key in PATOLOGIE_NUTRI.keys():
                        if patologie_nutri[key]:
                            stats_nutri['patologie'][key] += 1

                    ha_dca_nutri = patologie_nutri.get('patologia_dca', False)
                else:
                    # Reset campi se non ha nutrizionista
                    cliente.nessuna_patologia = None
                    for key in PATOLOGIE_NUTRI.keys():
                        setattr(cliente, key, None)

                # --- PATOLOGIE PSICOLOGIA ---
                if cliente.cliente_id in psico_clients:
                    patologie_psico = genera_patologie_psico(tipologia, ha_dca_nutri)

                    # Applica al cliente
                    cliente.nessuna_patologia_psico = patologie_psico['nessuna_patologia_psico']
                    for key in PATOLOGIE_PSICO.keys():
                        setattr(cliente, key, patologie_psico[key])

                    # Stats
                    if patologie_psico['nessuna_patologia_psico']:
                        stats_psico['nessuna'] += 1
                    else:
                        stats_psico['con_patologie'] += 1
                        count = sum(1 for k, v in patologie_psico.items() if v and k != 'nessuna_patologia_psico')
                        stats_psico['media_patologie'].append(count)

                    for key in PATOLOGIE_PSICO.keys():
                        if patologie_psico[key]:
                            stats_psico['patologie'][key] += 1
                else:
                    # Reset campi se non ha psicologo
                    cliente.nessuna_patologia_psico = None
                    for key in PATOLOGIE_PSICO.keys():
                        setattr(cliente, key, None)

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
        nutri_total = stats_nutri['nessuna'] + stats_nutri['con_patologie']
        print(f"\n📊 PATOLOGIE NUTRIZIONE ({nutri_total:,} clienti):")
        if nutri_total > 0:
            pct_nessuna = stats_nutri['nessuna'] / nutri_total * 100
            pct_con = stats_nutri['con_patologie'] / nutri_total * 100
            print(f"   Nessuna patologia: {stats_nutri['nessuna']:,} ({pct_nessuna:.1f}%)")
            print(f"   Con patologie: {stats_nutri['con_patologie']:,} ({pct_con:.1f}%)")

            if stats_nutri['media_patologie']:
                media = sum(stats_nutri['media_patologie']) / len(stats_nutri['media_patologie'])
                print(f"   Media patologie per cliente: {media:.1f}")

            print(f"\n   Dettaglio patologie:")
            for key, count in sorted(stats_nutri['patologie'].items(), key=lambda x: -x[1]):
                pct = count / nutri_total * 100
                label = key.replace('patologia_', '').replace('_', ' ').title()
                print(f"      {label:25}: {count:,} ({pct:.1f}%)")

        # Psicologia
        psico_total = stats_psico['nessuna'] + stats_psico['con_patologie']
        print(f"\n📊 PATOLOGIE PSICOLOGIA ({psico_total:,} clienti):")
        if psico_total > 0:
            pct_nessuna = stats_psico['nessuna'] / psico_total * 100
            pct_con = stats_psico['con_patologie'] / psico_total * 100
            print(f"   Nessuna patologia: {stats_psico['nessuna']:,} ({pct_nessuna:.1f}%)")
            print(f"   Con patologie: {stats_psico['con_patologie']:,} ({pct_con:.1f}%)")

            if stats_psico['media_patologie']:
                media = sum(stats_psico['media_patologie']) / len(stats_psico['media_patologie'])
                print(f"   Media patologie per cliente: {media:.1f}")

            print(f"\n   Dettaglio patologie:")
            for key, count in sorted(stats_psico['patologie'].items(), key=lambda x: -x[1]):
                pct = count / psico_total * 100
                label = key.replace('patologia_psico_', '').replace('_', ' ').title()
                print(f"      {label:30}: {count:,} ({pct:.1f}%)")

        # Sample
        print("\n📋 Esempio cliente con patologie:")
        sample = Cliente.query.filter(
            Cliente.patologia_dca == True,
            Cliente.patologia_psico_dca == True
        ).first()

        if sample:
            print(f"\n   {sample.nome_cognome}")
            print(f"   Tipologia: {sample.tipologia_cliente}")

            print(f"\n   PATOLOGIE NUTRIZIONE:")
            if sample.nessuna_patologia:
                print(f"      Nessuna patologia")
            else:
                for key in PATOLOGIE_NUTRI.keys():
                    if getattr(sample, key, False):
                        label = key.replace('patologia_', '').replace('_', ' ').title()
                        print(f"      ✓ {label}")

            print(f"\n   PATOLOGIE PSICOLOGIA:")
            if sample.nessuna_patologia_psico:
                print(f"      Nessuna patologia")
            else:
                for key in PATOLOGIE_PSICO.keys():
                    if getattr(sample, key, False):
                        label = key.replace('patologia_psico_', '').replace('_', ' ').title()
                        print(f"      ✓ {label}")

        print("\n✅ STEP 7 COMPLETATO!")


if __name__ == '__main__':
    main()
