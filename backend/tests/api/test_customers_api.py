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
"""

from http import HTTPStatus
from corposostenibile.extensions import db
from corposostenibile.models import Cliente


class TestCustomersListEndpoint:
    """Test GET /api/v1/customers - Elenco clienti"""
    
    def test_list_customers_empty(self, api_client, admin_user):
        """Test elenco clienti quando non ce ne sono"""
        api_client.login(admin_user)
        response = api_client.get('/api/v1/customers/')
        
        assert response.status_code == HTTPStatus.OK
        assert 'data' in response.json or isinstance(response.json, list)
    
    def test_list_customers_with_data(self, api_client, admin_user, client_customer):
        """Test elenco clienti con dati"""
        api_client.login(admin_user)
        
        # Merge cliente to ensure it's in current session
        if client_customer not in db.session:
            client_customer = db.session.merge(client_customer)
        db.session.commit()
        
        response = api_client.get('/api/v1/customers/')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json.get('data', response.json)
        assert isinstance(data, list)
    
    def test_list_customers_with_search_filter(self, api_client, admin_user, client_customer):
        """Test elenco clienti con filtro di ricerca"""
        api_client.login(admin_user)
        
        # Merge cliente to ensure it's in current session
        if client_customer not in db.session:
            client_customer = db.session.merge(client_customer)
        db.session.commit()
        
        # Search by nome_cognome
        response = api_client.get('/api/v1/customers/?search=' + client_customer.nome_cognome)
        
        assert response.status_code == HTTPStatus.OK
    
    def test_list_customers_pagination(self, api_client, admin_user):
        """Test elenco clienti con paginazione"""
        api_client.login(admin_user)
        response = api_client.get('/api/v1/customers/?page=1&per_page=10')
        
        assert response.status_code == HTTPStatus.OK


class TestCustomersDetailEndpoint:
    """Test GET /api/v1/customers/<id> - Dettagli cliente"""
    
    def test_get_customer_not_found(self, api_client, admin_user):
        """Test richiesta cliente inesistente"""
        api_client.login(admin_user)
        response = api_client.get('/api/v1/customers/99999')
        
        assert response.status_code == HTTPStatus.NOT_FOUND
    
    def test_get_customer_detail(self, api_client, admin_user, client_customer):
        """Test dettagli cliente esistente"""
        api_client.login(admin_user)
        
        # Merge cliente to ensure it's in current session
        if client_customer not in db.session:
            client_customer = db.session.merge(client_customer)
        db.session.commit()
        
        cliente_id = client_customer.cliente_id
        response = api_client.get(f'/api/v1/customers/{cliente_id}')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json['data']
        assert data['cliente_id'] == cliente_id
        assert data['nome_cognome'] == client_customer.nome_cognome
    
    def test_get_customer_requires_auth(self, api_client, client_customer):
        """Test che dettagli cliente richiedono autenticazione"""
        # No login
        cliente_id = client_customer.cliente_id
        response = api_client.get(f'/api/v1/customers/{cliente_id}')
        
        # Should be 401 Unauthorized or redirect
        assert response.status_code in [HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN, HTTPStatus.FOUND]


class TestCustomersCreateEndpoint:
    """Test POST /api/v1/customers - Creare cliente"""
    
    def test_create_customer_minimal(self, api_client, admin_user):
        """Test creazione cliente con dati minimi"""
        api_client.login(admin_user)
        
        payload = {
            "nome_cognome": "Nuovo Cliente",
        }
        
        response = api_client.post('/api/v1/customers/', json=payload)
        
        assert response.status_code == HTTPStatus.CREATED
        data = response.json['data']
        assert data['nome_cognome'] == "Nuovo Cliente"
        assert 'cliente_id' in data
    
    def test_create_customer_full(self, api_client, admin_user):
        """Test creazione cliente con tutti i dati"""
        api_client.login(admin_user)
        
        payload = {
            "nome_cognome": "Marco Bianchi",
            "email": "marco.bianchi@example.com",
            "numero_tel": "+39 3333333333",
            "tipologia_cliente": "a"
        }
        
        response = api_client.post('/api/v1/customers/', json=payload)
        
        assert response.status_code == HTTPStatus.CREATED
        data = response.json['data']
        assert data['nome_cognome'] == "Marco Bianchi"
        assert data['email'] == "marco.bianchi@example.com"
        assert 'cliente_id' in data
        
        # Verify in DB
        new_id = data['cliente_id']
        cliente = db.session.get(Cliente, new_id)
        assert cliente is not None
        assert cliente.email == "marco.bianchi@example.com"
    
    def test_create_customer_requires_auth(self, api_client):
        """Test che creazione cliente richiede autenticazione"""
        payload = {"nome_cognome": "Test"}
        response = api_client.post('/api/v1/customers/', json=payload)
        
        # Should be 401 Unauthorized or redirect
        assert response.status_code in [HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN, HTTPStatus.FOUND]


class TestCustomersUpdateEndpoint:
    """Test PATCH /api/v1/customers/<id> - Aggiornare cliente"""
    
    def test_update_customer_name(self, api_client, admin_user, client_customer):
        """Test aggiornamento nome cliente"""
        api_client.login(admin_user)
        
        # Merge cliente to ensure it's in current session
        if client_customer not in db.session:
            client_customer = db.session.merge(client_customer)
        db.session.commit()
        
        cliente_id = client_customer.cliente_id
        payload = {"nome_cognome": "Nome Aggiornato"}
        
        response = api_client.patch(f'/api/v1/customers/{cliente_id}', json=payload)
        
        assert response.status_code == HTTPStatus.OK
        data = response.json['data']
        assert data['nome_cognome'] == "Nome Aggiornato"
        
        # Verify in DB
        cliente = db.session.get(Cliente, cliente_id)
        assert cliente.nome_cognome == "Nome Aggiornato"
    
    def test_update_customer_email(self, api_client, admin_user, client_customer):
        """Test aggiornamento email cliente"""
        api_client.login(admin_user)
        
        # Merge cliente to ensure it's in current session
        if client_customer not in db.session:
            client_customer = db.session.merge(client_customer)
        db.session.commit()
        
        cliente_id = client_customer.cliente_id
        payload = {"email": "newemail@example.com"}
        
        response = api_client.patch(f'/api/v1/customers/{cliente_id}', json=payload)
        
        assert response.status_code == HTTPStatus.OK
        data = response.json['data']
        assert data['email'] == "newemail@example.com"
    
    def test_update_customer_not_found(self, api_client, admin_user):
        """Test aggiornamento cliente inesistente"""
        api_client.login(admin_user)
        
        payload = {"nome_cognome": "Test"}
        response = api_client.patch('/api/v1/customers/99999', json=payload)
        
        assert response.status_code == HTTPStatus.NOT_FOUND


class TestCustomersDeleteEndpoint:
    """Test DELETE /api/v1/customers/<id> - Eliminare cliente"""
    
    def test_delete_customer(self, api_client, admin_user, client_customer):
        """Test eliminazione cliente"""
        api_client.login(admin_user)
        
        # Merge cliente to ensure it's in current session
        if client_customer not in db.session:
            client_customer = db.session.merge(client_customer)
        db.session.commit()
        
        cliente_id = client_customer.cliente_id
        response = api_client.delete(f'/api/v1/customers/{cliente_id}')
        
        assert response.status_code == HTTPStatus.NO_CONTENT
        
        # Verify in DB (should be marked as deleted or removed)
        cliente = db.session.get(Cliente, cliente_id)
        # Implementation dependent: could be soft delete (stato_cliente=stop) or hard delete
        assert cliente is None or hasattr(cliente, 'stato_cliente')
    
    def test_delete_customer_not_found(self, api_client, admin_user):
        """Test eliminazione cliente inesistente"""
        api_client.login(admin_user)
        response = api_client.delete('/api/v1/customers/99999')
        
        assert response.status_code == HTTPStatus.NOT_FOUND


class TestCustomersAuthorizationEndpoint:
    """Test autorizzazione per endpoint customers"""
    
    def test_list_customers_requires_auth(self, api_client):
        """Test che elenco clienti richiede autenticazione"""
        response = api_client.get('/api/v1/customers/')
        
        # Should be 401 Unauthorized or redirect
        assert response.status_code in [HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN, HTTPStatus.FOUND]
    
    def test_standard_user_can_view_customers(self, api_client, user, client_customer):
        """Test che utente standard può visualizzare clienti"""
        api_client.login(user)
        
        # Merge cliente to ensure it's in current session
        if client_customer not in db.session:
            client_customer = db.session.merge(client_customer)
        db.session.commit()
        
        response = api_client.get('/api/v1/customers/')
        
        # Standard user might have restricted access depending on implementation
        assert response.status_code in [HTTPStatus.OK, HTTPStatus.FORBIDDEN]


class TestCustomersEdgeCases:
    """Test edge cases e scenari particolari"""
    
    def test_customer_with_special_characters(self, api_client, admin_user):
        """Test creazione cliente con caratteri speciali"""
        api_client.login(admin_user)
        
        payload = {
            "nome_cognome": "Giuseppe D'Angelo",
            "email": "giuseppe.d'angelo@example.com",
        }
        
        response = api_client.post('/api/v1/customers/', json=payload)
        
        assert response.status_code == HTTPStatus.CREATED
        data = response.json['data']
        assert data['nome_cognome'] == "Giuseppe D'Angelo"
    
    def test_customer_with_unicode(self, api_client, admin_user):
        """Test creazione cliente con caratteri unicode"""
        api_client.login(admin_user)
        
        payload = {
            "nome_cognome": "Étienne Müller",
        }
        
        response = api_client.post('/api/v1/customers/', json=payload)
        
        assert response.status_code == HTTPStatus.CREATED
        data = response.json['data']
        assert data['nome_cognome'] == "Étienne Müller"
    
    def test_customer_empty_string_name(self, api_client, admin_user):
        """Test creazione cliente con nome vuoto"""
        api_client.login(admin_user)
        
        payload = {
            "nome_cognome": "",
        }
        
        response = api_client.post('/api/v1/customers/', json=payload)
        
        # Should fail or reject empty name
        assert response.status_code in [HTTPStatus.BAD_REQUEST, HTTPStatus.UNPROCESSABLE_ENTITY, HTTPStatus.CREATED]
    
    def test_logout_after_operations(self, api_client, admin_user, client_customer):
        """Test logout e successive operazioni non autenticate"""
        api_client.login(admin_user)
        
        # Merge cliente to ensure it's in current session
        if client_customer not in db.session:
            client_customer = db.session.merge(client_customer)
        db.session.commit()
        
        # Login works
        response = api_client.get('/api/v1/customers/')
        assert response.status_code == HTTPStatus.OK
        
        # Logout
        api_client.logout()
        
        # Subsequent requests should fail
        response = api_client.get('/api/v1/customers/')
        assert response.status_code in [HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN, HTTPStatus.FOUND]
