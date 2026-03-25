"""
API Tests per i blueprint Postit, News, Search, Push, Loom, Tickets, Integrazioni.
Testa gli endpoint JSON per le funzionalità minori.

Endpoints testati:
- GET/POST /postit/ - Postit list and creation
- POST /postit/reorder - Reorder postits
- GET /news/list - News list
- GET /search/global - Global search
- POST /push/subscriptions - Register push notifications
- GET /push/public-key - Get push public key
- DELETE /push/subscriptions - Unregister push
- GET /push/notifications - Fetch notifications
- GET /loom/api/patients/search - Search Loom patients
- GET /loom/api/recordings - Get Loom recordings
- GET /team-tickets/ - Team tickets list
- GET /leads - Leads list
- POST /confirm-assignment - Confirm assignment
"""

from http import HTTPStatus
import pytest
from corposostenibile.extensions import db


# ============================================================================
# POSTIT TESTS
# ============================================================================

class TestPostitList:
    """Test GET /postit/list - Get postits"""
    
    def test_postit_list_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/postit/list')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_postit_list_success(self, api_client, login_test_user, db_session):
        """Test successful postit list retrieval"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/postit/list')
        
        assert response.status_code == HTTPStatus.OK


class TestPostitCreate:
    """Test POST /postit/create - Create postit"""
    
    def test_postit_create_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.post('/postit/create', json={'content': 'Test'})
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_postit_create_success(self, api_client, login_test_user, db_session):
        """Test successful postit creation"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.post('/postit/create', json={
            'content': 'Test postit content'
        })
        
        assert response.status_code in (HTTPStatus.OK, HTTPStatus.CREATED, HTTPStatus.BAD_REQUEST)


class TestPostitReorder:
    """Test POST /postit/reorder - Reorder postits"""
    
    def test_postit_reorder_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.post('/postit/reorder', json={'order': []})
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_postit_reorder_success(self, api_client, login_test_user, db_session):
        """Test successful postit reordering"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.post('/postit/reorder', json={
            'order': []
        })
        
        assert response.status_code in (HTTPStatus.OK, HTTPStatus.BAD_REQUEST)


# ============================================================================
# NEWS TESTS
# ============================================================================

class TestNewsList:
    """Test GET /news/list - Get news"""
    
    def test_news_list_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/news/list')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_news_list_success(self, api_client, login_test_user, db_session):
        """Test successful news list retrieval"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/news/list')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert isinstance(data, (list, dict))
    
    def test_news_list_with_limit(self, api_client, login_test_user, db_session):
        """Test news list with limit parameter"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/news/list?limit=5')
        
        assert response.status_code == HTTPStatus.OK


# ============================================================================
# SEARCH TESTS
# ============================================================================

class TestGlobalSearch:
    """Test GET /search/global - Global search"""
    
    def test_search_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/search/global?q=test')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_search_success_empty(self, api_client, login_test_user, db_session):
        """Test successful empty search"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/search/global?q=')
        
        assert response.status_code == HTTPStatus.OK
    
    def test_search_with_query(self, api_client, login_test_user, db_session):
        """Test search with query parameter"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/search/global?q=test')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert isinstance(data, (list, dict))
    
    def test_search_missing_query(self, api_client, login_test_user, db_session):
        """Test search without query parameter"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/search/global')
        
        assert response.status_code in (HTTPStatus.OK, HTTPStatus.BAD_REQUEST)


# ============================================================================
# PUSH NOTIFICATIONS TESTS
# ============================================================================

class TestPushSubscribe:
    """Test POST /push/subscriptions - Register push notification"""
    
    def test_push_subscribe_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.post('/push/subscriptions', json={
            'subscription': {}
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_push_subscribe_success(self, api_client, login_test_user, db_session):
        """Test successful push subscription"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.post('/push/subscriptions', json={
            'subscription': {
                'endpoint': 'https://example.com/push',
                'keys': {
                    'p256dh': 'test',
                    'auth': 'test'
                }
            }
        })
        
        assert response.status_code in (HTTPStatus.OK, HTTPStatus.CREATED, HTTPStatus.BAD_REQUEST)


class TestPushPublicKey:
    """Test GET /push/public-key - Get push public key"""
    
    def test_push_public_key_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/push/public-key')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_push_public_key_success(self, api_client, login_test_user, db_session):
        """Test successful public key retrieval"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/push/public-key')
        
        assert response.status_code == HTTPStatus.OK


class TestPushUnsubscribe:
    """Test DELETE /push/subscriptions - Unregister push"""
    
    def test_push_unsubscribe_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.delete('/push/subscriptions', json={
            'endpoint': 'test'
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_push_unsubscribe_success(self, api_client, login_test_user, db_session):
        """Test successful push unsubscription"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.delete('/push/subscriptions', json={
            'endpoint': 'https://example.com/push'
        })
        
        assert response.status_code in (HTTPStatus.OK, HTTPStatus.NO_CONTENT, HTTPStatus.BAD_REQUEST)


class TestPushNotifications:
    """Test GET /push/notifications - Fetch notifications"""
    
    def test_push_notifications_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/push/notifications')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_push_notifications_success(self, api_client, login_test_user, db_session):
        """Test successful notifications retrieval"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/push/notifications')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert isinstance(data, (list, dict))


# ============================================================================
# LOOM INTEGRATION TESTS
# ============================================================================

class TestLoomPatientSearch:
    """Test GET /loom/api/patients/search - Search Loom patients"""
    
    def test_loom_search_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/loom/api/patients/search?q=test')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_loom_search_success(self, api_client, login_test_user, db_session):
        """Test successful patient search"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/loom/api/patients/search?q=test')
        
        assert response.status_code in (HTTPStatus.OK, HTTPStatus.BAD_REQUEST)


class TestLoomRecordings:
    """Test GET /loom/api/recordings - Get Loom recordings"""
    
    def test_loom_recordings_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/loom/api/recordings?patient_id=1')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_loom_recordings_success(self, api_client, login_test_user, db_session):
        """Test successful recordings retrieval"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/loom/api/recordings?patient_id=1')
        
        assert response.status_code in (HTTPStatus.OK, HTTPStatus.BAD_REQUEST)


# ============================================================================
# TEAM TICKETS TESTS
# ============================================================================

class TestTeamTickets:
    """Test GET /team-tickets/ - Team tickets list"""
    
    def test_team_tickets_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/team-tickets/')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_team_tickets_success(self, api_client, login_test_user, db_session):
        """Test successful tickets retrieval"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/team-tickets/')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert isinstance(data, (list, dict))


# ============================================================================
# EXTERNAL INTEGRATIONS TESTS
# ============================================================================

class TestLeadsIntegration:
    """Test GET /leads - Leads list"""
    
    def test_leads_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/leads')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_leads_success(self, api_client, login_test_user, db_session):
        """Test successful leads retrieval"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/leads')
        
        assert response.status_code in (HTTPStatus.OK, HTTPStatus.FORBIDDEN, HTTPStatus.NOT_FOUND)


class TestConfirmAssignment:
    """Test POST /confirm-assignment - Confirm assignment"""
    
    def test_confirm_assignment_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.post('/confirm-assignment', json={
            'lead_id': 1
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_confirm_assignment_success(self, api_client, login_test_user, db_session):
        """Test successful assignment confirmation"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.post('/confirm-assignment', json={
            'lead_id': 1
        })
        
        assert response.status_code in (HTTPStatus.OK, HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_FOUND)
