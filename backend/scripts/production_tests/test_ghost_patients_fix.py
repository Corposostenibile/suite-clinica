#!/usr/bin/env python3
"""
Test di integrazione per il fix: stato globale vs stati M2M servizi.

PROBLEMATICA RISOLTA:
  I pazienti MICHELA VIGOLO, GRETA BELLUCCI, PATRIZIA LANZI risultavano ghost
  nonostante avessero servizi attivi assegnati.

CASO D'USO:
  Quando un paziente ha almeno un servizio M2M con stato 'attivo',
  lo stato globale NON deve essere 'ghost'.

PAZIENTI TESTATI:
  - MICHELA VIGOLO: cliente_id = 29415
  - GRETA BELLUCCI: cliente_id = 29434
  - PATRIZIA LANZI: cliente_id = 29414

USO:
  poetry run python backend/scripts/production_tests/test_ghost_patients_fix.py

  Oppure dalla pipeline Cloud Build:
  kubectl exec deployment/suite-clinica-backend -c backend -- \\
    python /app/scripts/production_tests/test_ghost_patients_fix.py
"""

import os
import sys
from dataclasses import dataclass
from typing import List, Optional

# Aggiungi il path dell'app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))


@dataclass
class PazienteGhostCase:
    """Caso paziente che deve essere verificato."""
    nome: str
    cliente_id: int
    

PAZIENTI_DA_VERIFICARE: List[PazienteGhostCase] = [
    PazienteGhostCase(nome="MICHELA VIGOLO", cliente_id=29415),
    PazienteGhostCase(nome="GRETA BELLUCCI", cliente_id=29434),
    PazienteGhostCase(nome="PATRIZIA LANZI", cliente_id=29414),
]


def verifica_stato_paziente(cliente) -> tuple[bool, str]:
    """
    Verifica se il paziente è in uno stato coerente.
    
    Regola: Se almeno un servizio M2M è 'attivo', stato_cliente NON deve essere 'ghost'.
    
    Returns:
        (is_valid, message): True se valido, False altrimenti con messaggio dettagliato
    """
    from corposostenibile.models import StatoClienteEnum
    
    stato_globale = cliente.stato_cliente
    stati_servizi = {
        "nutrizione": cliente.stato_nutrizione,
        "coach": cliente.stato_coach,
        "psicologia": cliente.stato_psicologia,
    }
    
    # Conta servizi attivi (solo quelli assegnati al paziente)
    servizi_attivi = []
    for servizio, stato in stati_servizi.items():
        if stato == StatoClienteEnum.attivo:
            servizi_attivi.append(servizio)
    
    # Logica di verifica
    if stato_globale == StatoClienteEnum.ghost and len(servizi_attivi) > 0:
        return False, (
            f"INCOERENTE: stato_cliente='ghost' ma servizi attivi: {servizi_attivi}. "
            f"I servizi M2M sono: nutrizione={stati_servizi['nutrizione']}, "
            f"coach={stati_servizi['coach']}, psicologia={stati_servizi['psicologia']}"
        )
    
    if stato_globale != StatoClienteEnum.ghost and len(servizi_attivi) == 0:
        # Questo è OK - potrebbe essere in pausa o stop con servizi non attivi
        return True, f"OK: stato_cliente='{stato_globale}' e nessun servizio attivo"
    
    return True, (
        f"OK: stato_cliente='{stato_globale}', "
        f"servizi attivi: {servizi_attivi if servizi_attivi else 'nessuno'}"
    )


def run_tests() -> bool:
    """
    Esegue i test sui 3 pazienti.
    
    Returns:
        True se tutti i test passano, False altrimenti
    """
    from corposostenibile import create_app
    from corposostenibile.extensions import db
    from corposostenibile.models import Cliente
    
    print("=" * 70)
    print("TEST: Verifica fix stato globale vs stati M2M servizi")
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
        
        all_passed = True
        failed_patients = []
        
        for paziente in PAZIENTI_DA_VERIFICARE:
            print(f"\n--- Paziente: {paziente.nome} (ID: {paziente.cliente_id}) ---")
            
            cliente = db.session.get(Cliente, paziente.cliente_id)
            
            if cliente is None:
                print(f"[WARN] Paziente {paziente.cliente_id} non trovato nel database")
                print(f"       (probabilmente è stato rimosso o l'ID è cambiato)")
                continue
            
            is_valid, message = verifica_stato_paziente(cliente)
            
            print(f"  Stato globale: {cliente.stato_cliente}")
            print(f"  Nutrizione: {cliente.stato_nutrizione}")
            print(f"  Coach: {cliente.stato_coach}")
            print(f"  Psicologia: {cliente.stato_psicologia}")
            print(f"  --> {message}")
            
            if not is_valid:
                all_passed = False
                failed_patients.append(paziente.nome)
                print(f"[FAIL] ❌ PAZIENTE IN STATO INCOERENTE!")
            else:
                print(f"[PASS] ✓ Stato coerente")
        
        print()
        print("=" * 70)
        
        if all_passed:
            print("[SUCCESS] ✓ Tutti i pazienti sono in stato coerente!")
            print("          Il fix funziona correttamente.")
            return True
        else:
            print(f"[FAILURE] ❌ {len(failed_patients)} paziente/i in stato incoerente:")
            for nome in failed_patients:
                print(f"           - {nome}")
            print()
            print("Il deploy è BLOCCATO finché il fix non viene risolto.")
            return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
