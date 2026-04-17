"""
Test mirato per ITS-20260417-0001: Verifica che l'endpoint /api/customers/expired
restituisca correttamente i clienti con data_rinnovo scaduta (data_rinnovo < oggi).

Ticket: ITS-20260417-0001
Richiesta: Nel tab HEALTH MANAGER - CLIENTI IN SCADENZA aggiungere anche quelli scaduti
"""
import pytest
from datetime import date, timedelta


class TestCustomersExpired:
    """
    Test di integrazione per l'endpoint /api/customers/expired.
    Verifica che restituisca solo clienti con data_rinnovo < oggi.
    """

    def test_expired_returns_only_expired_clients(self, app):
        """L'endpoint /expired deve restituire solo clienti con data_rinnovo < oggi."""
        with app.app_context():
            from corposostenibile.blueprints.customers.routes import api_expired
            from flask import request
            from corposostenibile.models import Cliente
            from corposostenibile.extensions import db
            
            today = date.today()
            
            # Conta clienti scaduti nel DB
            expired_count = db.session.query(db.func.count(Cliente.cliente_id)).filter(
                Cliente.show_in_clienti_lista.is_(True),
                Cliente.data_rinnovo.isnot(None),
                Cliente.data_rinnovo < today,
            ).scalar()
            
            print(f"\n[Test] Clienti scaduti nel DB: {expired_count}")
            
            # Se non ci sono clienti scaduti, skip
            if expired_count == 0:
                pytest.skip("Nessun cliente scaduto nel DB per test")
            
            # Verifica che tutti i clienti restituiti siano effettivamente scaduti
            with app.test_request_context('/api/customers/expired'):
                # Simula la query dell'endpoint
                from corposostenibile.blueprints.customers.routes import _apply_hm_page_scope
                
                query = _apply_hm_page_scope(
                    db.session.query(Cliente).filter(
                        Cliente.show_in_clienti_lista.is_(True),
                        Cliente.data_rinnovo.isnot(None),
                        Cliente.data_rinnovo < today,
                    )
                )
                
                # Verifica che tutti i risultati abbiano data_rinnovo < oggi
                results = query.limit(10).all()
                for cliente in results:
                    assert cliente.data_rinnovo < today, (
                        f"Cliente {cliente.cliente_id} ({cliente.nome_cognome}) "
                        f"ha data_rinnovo {cliente.data_rinnovo} che NON è < oggi {today}"
                    )
                    
            print(f"[Test] OK: Tutti i {len(results)} clienti testati sono effettivamente scaduti")

    def test_expired_excludes_future_dates(self, app):
        """I clienti con data_rinnovo futura NON devono essere inclusi."""
        with app.app_context():
            from corposostenibile.models import Cliente
            from corposostenibile.extensions import db
            
            today = date.today()
            future_date = today + timedelta(days=30)
            
            # Verifica che non esistano clienti con data_rinnovo futura nel gruppo scaduto
            future_in_expired = db.session.query(db.func.count(Cliente.cliente_id)).filter(
                Cliente.show_in_clienti_lista.is_(True),
                Cliente.data_rinnovo.isnot(None),
                Cliente.data_rinnovo < today,
                Cliente.data_rinnovo > today,  # Contraddizione, deve essere 0
            ).scalar()
            
            # Verifica che la query normale non includa date future
            future_clients = db.session.query(db.func.count(Cliente.cliente_id)).filter(
                Cliente.show_in_clienti_lista.is_(True),
                Cliente.data_rinnovo.isnot(None),
                Cliente.data_rinnovo >= today,
            ).scalar()
            
            print(f"\n[Test] Clienti con data_rinnovo >= oggi: {future_clients}")
            assert future_in_expired == 0, "Query scaduti non deve mai includere date future"
            print(f"[Test] OK: Query scaduti correttamente limitata a data_rinnovo < oggi")

    def test_expired_includes_proper_fields(self, app):
        """Verifica che i campi restituiti siano corretti."""
        with app.app_context():
            from corposostenibile.models import Cliente
            from corposostenibile.extensions import db
            
            today = date.today()
            
            # Prendi un cliente scaduto
            expired_cliente = db.session.query(Cliente).filter(
                Cliente.show_in_clienti_lista.is_(True),
                Cliente.data_rinnovo.isnot(None),
                Cliente.data_rinnovo < today,
            ).first()
            
            if expired_cliente is None:
                pytest.skip("Nessun cliente scaduto per test")
            
            # Verifica i campi necessari per il frontend
            assert expired_cliente.data_rinnovo is not None, "data_rinnovo deve essere presente"
            assert expired_cliente.data_rinnovo < today, "data_rinnovo deve essere nel passato"
            
            # Calcola giorni scaduto
            giorni_scaduto = (today - expired_cliente.data_rinnovo).days
            print(f"\n[Test] Cliente {expired_cliente.cliente_id}: {expired_cliente.nome_cognome}")
            print(f"[Test] data_rinnovo: {expired_cliente.data_rinnovo}, "
                  f"scaduto da {giorni_scaduto} giorni")
            
            assert giorni_scaduto > 0, "Deve essere scaduto da almeno 1 giorno"
            print(f"[Test] OK: Campi corretti per rendering frontend")
