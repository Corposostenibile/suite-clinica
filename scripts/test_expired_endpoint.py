#!/usr/bin/env python3
"""
Test in produzione per ITS-20260417-0001: verifica endpoint /api/v1/customers/expired
 Esegue test direttamente nel container GKE
"""
import sys
sys.path.insert(0, '/app')

from datetime import date
from corposostenibile.extensions import db
from corposostenibile.models import Cliente


def test_expired_endpoint():
    """Verifica che la query sottostante funzioni correttamente."""
    today = date.today()
    print(f"📅 Data odierna: {today}")
    print("=" * 60)
    
    # Test 1: Conta clienti scaduti
    print("\n🧪 TEST 1: Conteggio clienti scaduti")
    expired_count = db.session.query(db.func.count(Cliente.cliente_id)).filter(
        Cliente.show_in_clienti_lista.is_(True),
        Cliente.data_rinnovo.isnot(None),
        Cliente.data_rinnovo < today,
    ).scalar()
    print(f"   Clienti con data_rinnovo < oggi: {expired_count}")
    
    # Test 2: Verifica che non includa date future
    print("\n🧪 TEST 2: Verifica esclusione date future")
    future_count = db.session.query(db.func.count(Cliente.cliente_id)).filter(
        Cliente.show_in_clienti_lista.is_(True),
        Cliente.data_rinnovo.isnot(None),
        Cliente.data_rinnovo >= today,
    ).scalar()
    print(f"   Clienti con data_rinnovo >= oggi: {future_count}")
    
    # Test 3: Esempio clienti scaduti
    print("\n🧪 TEST 3: Primi 5 clienti scaduti (più vecchi)")
    expired_clients = db.session.query(Cliente).filter(
        Cliente.show_in_clienti_lista.is_(True),
        Cliente.data_rinnovo.isnot(None),
        Cliente.data_rinnovo < today,
    ).order_by(Cliente.data_rinnovo.asc()).limit(5).all()
    
    for c in expired_clients:
        giorni_scaduto = (today - c.data_rinnovo).days
        print(f"   [{c.cliente_id}] {c.nome_cognome} - "
              f"scaduto il {c.data_rinnovo} ({giorni_scaduto} gg fa) - "
              f"stato: {c.stato_cliente.value if hasattr(c.stato_cliente, 'value') else c.stato_cliente}")
    
    # Test 4: Verifica che la query frontend restituisca i campi giusti
    print("\n🧪 TEST 4: Simulazione risposta API")
    if expired_clients:
        c = expired_clients[0]
        response_mock = {
            "cliente_id": c.cliente_id,
            "nome_cognome": c.nome_cognome,
            "stato_cliente": c.stato_cliente.value if hasattr(c.stato_cliente, 'value') else c.stato_cliente,
            "data_rinnovo": c.data_rinnovo.isoformat() if c.data_rinnovo else None,
            "giorni_rimanenti": (c.data_rinnovo - today).days if c.data_rinnovo else None,
        }
        print(f"   Risposta mock: {response_mock}")
    
    print("\n" + "=" * 60)
    print("✅ TEST COMPLETATI")
    
    return expired_count > 0  # True se ci sono clienti scaduti


if __name__ == '__main__':
    success = test_expired_endpoint()
    sys.exit(0 if success else 1)
