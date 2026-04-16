#!/usr/bin/env python3
"""
Script per correggere lo stato_cliente dei 3 pazienti ghost che avevano servizi attivi.

PAZIENTI:
  - MICHELA VIGOLO:  cliente_id = 29415
  - GRETA BELLUCCI:  cliente_id = 29434
  - PATRIZIA LANZI:  cliente_id = 29414

AZIONE:
  Imposta stato_cliente = 'attivo' per pazienti che hanno almeno un servizio M2M attivo.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))


PAZIENTI = [
    (29415, "MICHELA VIGOLO"),
    (29434, "GRETA BELLUCCI"),
    (29414, "PATRIZIA LANZI"),
]


def main():
    from corposostenibile import create_app
    from corposostenibile.extensions import db
    from corposostenibile.models import Cliente, StatoClienteEnum
    
    print("=" * 70)
    print("FIX: Correzione stato_cliente per pazienti con servizi attivi")
    print("=" * 70)
    print()
    
    app = create_app()
    
    with app.app_context():
        # Verifica connessione DB
        try:
            db.session.execute(db.text("SELECT 1"))
            print("[OK] Connessione al database: OK")
        except Exception as e:
            print(f"[FATAL] Connessione al database fallita: {e}")
            return False
        
        corretti = 0
        gia_corretti = 0
        errori = []
        
        for cliente_id, nome in PAZIENTI:
            print(f"\n--- {nome} (ID: {cliente_id}) ---")
            
            cliente = db.session.get(Cliente, cliente_id)
            
            if cliente is None:
                print(f"  [WARN] Paziente non trovato")
                errori.append((cliente_id, nome, "Non trovato"))
                continue
            
            # Stato attuale
            print(f"  Stato attuale: stato_cliente={cliente.stato_cliente}")
            print(f"                 nutrizione={cliente.stato_nutrizione}")
            print(f"                 coach={cliente.stato_coach}")
            print(f"                 psicologia={cliente.stato_psicologia}")
            
            # Verifica se ha servizi attivi
            servizi_attivi = []
            if cliente.stato_nutrizione == StatoClienteEnum.attivo:
                servizi_attivi.append("nutrizione")
            if cliente.stato_coach == StatoClienteEnum.attivo:
                servizi_attivi.append("coach")
            if cliente.stato_psicologia == StatoClienteEnum.attivo:
                servizi_attivi.append("psicologia")
            
            print(f"  Servizi attivi: {servizi_attivi if servizi_attivi else 'nessuno'}")
            
            # Se ha servizi attivi e stato_cliente non è attivo, correggi
            if servizi_attivi:
                if cliente.stato_cliente == StatoClienteEnum.attivo:
                    print(f"  --> GIA' CORRETTO (stato_cliente=attivo)")
                    gia_corretti += 1
                else:
                    vecchio_stato = cliente.stato_cliente
                    cliente.stato_cliente = StatoClienteEnum.attivo
                    print(f"  --> CORRETTO: {vecchio_stato} -> attivo")
                    corretti += 1
            else:
                print(f"  --> NESSUNA CORREZIONE (nessun servizio attivo)")
        
        print()
        print("=" * 70)
        print(f"RIEPILOGO:")
        print(f"  Pazienti corretti: {corretti}")
        print(f"  Gia' corretti:     {gia_corretti}")
        print(f"  Errori:            {len(errori)}")
        
        if corretti > 0:
            print()
            print("Commit delle modifiche...")
            db.session.commit()
            print("[OK] Modifiche salvate nel database")
        
        return corretti == 0 or True  # True anche se gia' corretti


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
