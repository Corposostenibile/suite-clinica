import pytest
from flask import url_for

@pytest.fixture
def api_client(client):
    """
    Client specifico per le API che imposta automaticamente gli header corretti.
    Favarisce l'uso di JSON.
    """
    original_post = client.post
    original_put = client.put
    original_patch = client.patch
    original_get = client.get
    original_delete = client.delete

    def json_post(url, data=None, json=None, **kwargs):
        kwargs.setdefault('headers', {})
        kwargs['headers']['Accept'] = 'application/json'
        # Se c'è json data, Flask-Client lo gestisce automaticamente, ma possiamo forzare Content-Type
        return original_post(url, data=data, json=json, **kwargs)

    def json_put(url, data=None, json=None, **kwargs):
        kwargs.setdefault('headers', {})
        kwargs['headers']['Accept'] = 'application/json'
        return original_put(url, data=data, json=json, **kwargs)

    def json_patch(url, data=None, json=None, **kwargs):
        kwargs.setdefault('headers', {})
        kwargs['headers']['Accept'] = 'application/json'
        return original_patch(url, data=data, json=json, **kwargs)

    def json_get(url, **kwargs):
        kwargs.setdefault('headers', {})
        kwargs['headers']['Accept'] = 'application/json'
        return original_get(url, **kwargs)

    def json_delete(url, **kwargs):
        kwargs.setdefault('headers', {})
        kwargs['headers']['Accept'] = 'application/json'
        return original_delete(url, **kwargs)
    
    def login(user):
        """Logga l'utente tramite mock di Flask-Login."""
        from unittest.mock import patch
        from corposostenibile.extensions import db
        
        # Se c'è già un patch attivo, fermalo
        logout()
        
        # Assicura che l'utente sia attaccato alla sessione corrente
        # e non sia detached/expired causando errori quando l'app prova ad accedervi
        if user not in db.session:
            user = db.session.merge(user)
        
        # Patch _get_user per ritornare il nostro utente
        patcher = patch('flask_login.utils._get_user')
        mock_get_user = patcher.start()
        mock_get_user.return_value = user
        
        # Salva riferimento al patcher per poterlo fermare
        client._auth_patcher = patcher
        client.test_user = user

    
    def logout():
        """Logout e stop del mock."""
        if hasattr(client, '_auth_patcher'):
            client._auth_patcher.stop()
            del client._auth_patcher
        if hasattr(client, 'test_user'):
            del client.test_user

    # Monkey patch dei metodi
    client.post = json_post
    client.put = json_put
    client.patch = json_patch
    client.get = json_get
    client.delete = json_delete
    client.login = login
    client.logout = logout
    
    
    # Assicura cleanup al termine del test (se il test finisce senza logout)
    # Pytest request object is not available here easily to add finalizer?
    # Actually api_client fixture uses 'client' fixture. 
    # We can use a yield fixture structure for strict cleanup.
    
    yield client
    
    # Teardown: stop patch if active
    logout()




@pytest.fixture
def api_auth_headers(client, app):
    """
    Restituisce una funzione per ottenere gli headers di autenticazione 
    (utile se si usa JWT token auth, ma qui usiamo session auth tramite client.login).
    In questo setup basato su sessione (flask-login), il client mantiene i cookie,
    quindi questa fixture potrebbe essere superflua se si usa client.login,
    ma la teniamo per estensibilità futura se passiamo a Token Auth.
    """
    def _make_headers(user_email=None):
        return {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    return _make_headers

@pytest.fixture
def department(db_session):
    """Fixture per Dipartimento."""
    from tests.factories import DepartmentFactory
    return DepartmentFactory()

@pytest.fixture
def user(db_session, department):
    """Fixture per User standard."""
    from tests.factories import UserFactory
    return UserFactory()

@pytest.fixture
def admin_user(db_session, department):
    """Fixture per Admin User."""
    from tests.factories import UserFactory
    # Admin spesso ha accesso a tutto, ma lo mettiamo in un dipartimento per coerenza
    return UserFactory(is_admin=True)

@pytest.fixture
def client_customer(db_session):
    """Fixture per Cliente."""
    from tests.factories import ClienteFactory
    return ClienteFactory(nome_cognome="Mario Rossi")

@pytest.fixture
def ticket(db_session, user, admin_user, department, client_customer):
    """Fixture per Ticket creato tramite servizio."""
    from corposostenibile.blueprints.ticket.services import TicketService
    from corposostenibile.models import TicketUrgencyEnum
    from unittest.mock import patch

    service = TicketService()
    
    # Mock notifiche per evitare invio email reale o errori template
    with patch.object(service, '_send_new_ticket_notifications'):
        ticket = service.create_ticket(
            requester_first_name="Mario",
            requester_last_name="Rossi",
            requester_email="mario@example.com",
            department_id=department.id,
            title="Ticket Test API",
            description="Descrizione ticket API",
            urgency=TicketUrgencyEnum.media,
            created_by=user,
            assigned_to_id=admin_user.id, # Assegna all'admin
            related_client_name=client_customer.nome_cognome,
            send_notifications=False
        )
        # Link explicit cliente
        ticket.cliente_id = client_customer.cliente_id
        db_session.commit()
        
    return ticket


# Alias fixtures per test compatibility
@pytest.fixture
def login_test_user(user):
    """Alias for 'user' fixture - regular test user for login tests."""
    return user


@pytest.fixture
def admin_login_test_user(admin_user):
    """Alias for 'admin_user' fixture - admin test user for login tests."""
    return admin_user
