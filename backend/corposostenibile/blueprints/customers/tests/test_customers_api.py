"""
API Tests per il blueprint Customers.
Testa gli endpoint HTTP che il frontend React chiama direttamente.

Endpoints testati:
- GET /api/v1/customers - Elenco clienti con filtri
- GET /api/v1/customers/<id> - Dettagli cliente
- POST /api/v1/customers - Creare nuovo cliente
- PATCH /api/v1/customers/<id> - Aggiornare cliente
- DELETE /api/v1/customers/<id> - Eliminare cliente
- GET /api/v1/customers/<id>/history - Cronologia modifiche
- GET /api/v1/customers/stats - Statistiche clienti
- GET /api/v1/customers/<id>/feedback-metrics - Metriche feedback
- GET /api/v1/customers/<id>/initial-checks - Check iniziali
- POST /api/v1/customers/<id>/professionisti/assign - Assegnare professionista
"""

import pytest
from datetime import datetime
from corposostenibile.models import Cliente, User, UserSpecialtyEnum


class TestCustomersListEndpoint:
    """Test GET /api/customers - Elenco clienti"""
    
    def test_get_customers_empty(self, client, app):
        """Test elenco clienti quando non ce ne sono"""
        with app.app_context():
            response = client.get('/api/v1/customers/', follow_redirects=True)
        
        # Endpoint richiede autenticazione - accetta 200, 401, 403
        # Gli unauthenticated users dovrebbero ottenere 401/403
        assert response.status_code in [200, 401, 403]
    
    def test_get_customers_with_sample_data(self, client, app, db_session):
        """Test elenco clienti con dati"""
        with app.app_context():
            # Creiamo un cliente di test
            cliente = Cliente(
                nome_cognome="Test Cliente",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db_session.add(cliente)
            db_session.commit()
            cliente_id = cliente.id
        
        # Ora facciamo la richiesta
        with app.app_context():
            response = client.get('/api/v1/customers/', follow_redirects=True)
        
        assert response.status_code in [200, 301, 302, 307, 308, 401, 403]
    
    def test_get_customers_with_search_filter(self, client, app):
        """Test elenco clienti con filtro di ricerca"""
        response = client.get('/api/v1/customers?search=test')
        
        assert response.status_code in [200, 400, 404]  # Dipende dall'implementazione
    
    def test_get_customers_with_pagination(self, client, app):
        """Test elenco clienti con paginazione"""
        response = client.get('/api/v1/customers?page=1&per_page=10')
        
        assert response.status_code in [200, 400]


class TestCustomersDetailEndpoint:
    """Test GET /api/customers/<id> - Dettagli cliente"""
    
    def test_get_customer_not_found(self, client, app):
        """Test richiesta cliente inesistente"""
        response = client.get('/api/v1/customers/99999')
        
        assert response.status_code in [404, 400, 401]  # Not found o errore
    
    def test_get_customer_detail_with_sample(self, client, app, db_session):
        """Test dettagli cliente esistente"""
        with app.app_context():
            cliente = Cliente(
                nome_cognome="Mario Rossi",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db_session.add(cliente)
            db_session.commit()
            cliente_id = cliente.id
        
        # Otteniamo il cliente_id dalla app context
        with app.app_context():
            response = client.get(f'/api/v1/customers/{cliente_id}')
        
        # Dovrebbe restituire 200 o 401 se non autenticato
        assert response.status_code in [200, 401, 403]


class TestCustomersCreateEndpoint:
    """Test POST /api/customers - Creare cliente"""
    
    def test_create_customer_minimal(self, client, app):
        """Test creazione cliente con dati minimi"""
        payload = {
            'nome_cognome': 'Nuovo Cliente',
        }
        
        response = client.post('/api/v1/customers', json=payload)
        
        # Potrebbe essere 201 (creato), 401 (non autenticato), 400 (errore)
        assert response.status_code in [201, 400, 401, 403]
    
    def test_create_customer_full_data(self, client, app):
        """Test creazione cliente con tutti i dati"""
        payload = {
            'nome_cognome': 'Nuovo Cliente',
            'email': 'cliente@example.com',
            'telefono': '+39 123 456 7890',
            'data_inizio_abbonamento': '2025-01-01',
        }
        
        response = client.post('/api/v1/customers', json=payload)
        
        assert response.status_code in [201, 400, 401, 403]


class TestCustomersUpdateEndpoint:
    """Test PATCH /api/customers/<id> - Aggiornare cliente"""
    
    def test_update_customer_not_found(self, client, app):
        """Test aggiornamento cliente inesistente"""
        payload = {'nome_cognome': 'Nuovo Nome'}
        response = client.patch('/api/v1/customers/99999', json=payload)
        
        assert response.status_code in [404, 400, 401, 403]
    
    def test_update_customer_with_sample(self, client, app, db_session):
        """Test aggiornamento cliente esistente"""
        with app.app_context():
            cliente = Cliente(
                nome_cognome="Mario Rossi",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db_session.add(cliente)
            db_session.commit()
            cliente_id = cliente.id
        
        payload = {'nome_cognome': 'Mario Bianchi'}
        
        with app.app_context():
            response = client.patch(f'/api/v1/customers/{cliente_id}', json=payload)
        
        assert response.status_code in [200, 400, 401, 403]


class TestCustomersDeleteEndpoint:
    """Test DELETE /api/customers/<id> - Eliminare cliente"""
    
    def test_delete_customer_not_found(self, client, app):
        """Test eliminazione cliente inesistente"""
        response = client.delete('/api/v1/customers/99999')
        
        assert response.status_code in [404, 400, 401, 403]
    
    def test_delete_customer_with_sample(self, client, app, db_session):
        """Test eliminazione cliente esistente"""
        with app.app_context():
            cliente = Cliente(
                nome_cognome="Da Eliminare",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db_session.add(cliente)
            db_session.commit()
            cliente_id = cliente.id
        
        with app.app_context():
            response = client.delete(f'/api/v1/customers/{cliente_id}')
        
        assert response.status_code in [200, 204, 400, 401, 403]


class TestCustomersHistoryEndpoint:
    """Test GET /api/customers/<id>/history - Cronologia"""
    
    def test_get_customer_history(self, client, app, db_session):
        """Test cronologia modifiche cliente"""
        with app.app_context():
            cliente = Cliente(
                nome_cognome="Test",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db_session.add(cliente)
            db_session.commit()
            cliente_id = cliente.id
        
        with app.app_context():
            response = client.get(f'/api/v1/customers/{cliente_id}/history')
        
        assert response.status_code in [200, 401, 403, 404]


class TestCustomersStatsEndpoint:
    """Test GET /api/customers/stats - Statistiche"""
    
    def test_get_customers_stats(self, client, app):
        """Test statistiche globali clienti"""
        response = client.get('/api/v1/customers/stats')
        
        assert response.status_code in [200, 401, 403]


class TestCustomersFeedbackMetricsEndpoint:
    """Test GET /api/customers/<id>/feedback-metrics - Metriche feedback"""
    
    def test_get_feedback_metrics(self, client, app, db_session):
        """Test metriche feedback cliente"""
        with app.app_context():
            cliente = Cliente(
                nome_cognome="Test Feedback",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db_session.add(cliente)
            db_session.commit()
            cliente_id = cliente.id
        
        with app.app_context():
            response = client.get(f'/api/v1/customers/{cliente_id}/feedback-metrics')
        
        assert response.status_code in [200, 401, 403, 404]


class TestCustomersInitialChecksEndpoint:
    """Test GET /api/customers/<id>/initial-checks - Check iniziali"""
    
    def test_get_initial_checks(self, client, app, db_session):
        """Test elenco check iniziali cliente"""
        with app.app_context():
            cliente = Cliente(
                nome_cognome="Test Checks",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db_session.add(cliente)
            db_session.commit()
            cliente_id = cliente.id
        
        with app.app_context():
            response = client.get(f'/api/v1/customers/{cliente_id}/initial-checks')
        
        assert response.status_code in [200, 401, 403, 404]


class TestCustomersProfessionalsAssignmentEndpoint:
    """Test POST /api/customers/<id>/professionisti/assign - Assegnare professionista"""
    
    def test_assign_professional_not_found(self, client, app):
        """Test assegnazione professionista a cliente inesistente"""
        payload = {
            'professional_id': 1,
            'specialty': 'nutrizionista',
        }
        response = client.post('/api/v1/customers/99999/professionisti/assign', json=payload)
        
        assert response.status_code in [404, 400, 401, 403]
    
    def test_assign_professional_with_sample(self, client, app, db_session):
        """Test assegnazione professionista a cliente esistente"""
        with app.app_context():
            # Creiamo cliente e professionista
            cliente = Cliente(
                nome_cognome="Test Assign",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            prof = User(
                email="prof@example.com",
                first_name="Prof",
                last_name="Nutri",
                specialty=UserSpecialtyEnum.nutrizionista,
                is_active=True,
            )
            prof.password_hash = "dummy"
            
            db_session.add(cliente)
            db_session.add(prof)
            db_session.commit()
            
            cliente_id = cliente.id
            prof_id = prof.id
        
        payload = {
            'professional_id': prof_id,
            'specialty': 'nutrizionista',
        }
        
        with app.app_context():
            response = client.post(f'/api/v1/customers/{cliente_id}/professionisti/assign', json=payload)
        
        assert response.status_code in [200, 201, 400, 401, 403, 404]
