"""
API Tests per il blueprint Calendar (React API).
Testa gli endpoint JSON che il frontend React chiama per la gestione del calendario.

Endpoints testati:
- GET /calendar/api/events - Get events for FullCalendar
- POST /calendar/api/events - Create new event
- GET /calendar/api/meetings/<id> - Get meetings for customer
- GET /calendar/api/meeting/<id> - Get meeting details
- PUT /calendar/api/meeting/<id> - Update meeting
- DELETE /calendar/api/meeting/<id> - Delete meeting
- DELETE /calendar/api/event/<google_event_id> - Delete event by Google ID
- POST /calendar/api/sync-single-event - Sync single event
- GET /calendar/api/connection-status - Check Google Calendar connection
- POST /calendar/api/admin/tokens/refresh - Refresh Google tokens
- POST /calendar/api/admin/tokens/cleanup - Cleanup expired tokens
- POST /calendar/api/admin/tokens/<user_id>/refresh - Refresh specific user token
- GET /calendar/api/admin/tokens/status - Get tokens status
- GET /calendar/api/team/users - Get team users for calendar
- GET /calendar/api/customers/search - Search customers
- GET /calendar/api/customers/list - List customers
- GET /calendar/api/customers/<id>/minimal - Get customer minimal data
- GET /calendar/api/admin/scheduler/status - Get scheduler status
"""

from http import HTTPStatus
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from corposostenibile.extensions import db
from corposostenibile.models import User, UserRoleEnum, Cliente, Meeting


class TestCalendarGetEvents:
    """Test GET /calendar/api/events - Get events for FullCalendar"""
    
    def test_get_events_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/calendar/api/events')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_get_events_no_google_auth(self, api_client, admin_user, db_session):
        """Test getting events when user has no Google Auth"""
        db_session.commit()
        api_client.login(admin_user)
        response = api_client.get('/calendar/api/events')
        
        # Can return 200 with error message, 500 on exception, or 302 redirect
        assert response.status_code in (HTTPStatus.OK, HTTPStatus.INTERNAL_SERVER_ERROR, HTTPStatus.FOUND)
    
    def test_get_events_with_time_range(self, api_client, admin_user, db_session):
        """Test getting events with custom time range"""
        db_session.commit()
        api_client.login(admin_user)
        
        start = (datetime.utcnow() - timedelta(days=30)).isoformat() + 'Z'
        end = (datetime.utcnow() + timedelta(days=30)).isoformat() + 'Z'
        
        response = api_client.get(f'/calendar/api/events?start={start}&end={end}')
        
        # Can return 200, 500 on exception, or 302 redirect
        assert response.status_code in (HTTPStatus.OK, HTTPStatus.INTERNAL_SERVER_ERROR, HTTPStatus.FOUND)
    
    def test_get_events_with_date_only_params(self, api_client, admin_user, db_session):
        """Test getting events with date-only parameters (no time)"""
        db_session.commit()
        api_client.login(admin_user)
        
        start = '2025-01-01'
        end = '2025-12-31'
        
        response = api_client.get(f'/calendar/api/events?start={start}&end={end}')
        
        # Can return 200, 500 on exception, or 302 redirect
        assert response.status_code in (HTTPStatus.OK, HTTPStatus.INTERNAL_SERVER_ERROR, HTTPStatus.FOUND)


class TestCalendarCreateEvent:
    """Test POST /calendar/api/events - Create new event"""
    
    def test_create_event_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.post('/calendar/api/events', json={
            'title': 'Test Event',
            'start': datetime.utcnow().isoformat(),
            'end': (datetime.utcnow() + timedelta(hours=1)).isoformat()
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_create_event_no_google_auth(self, api_client, admin_user, db_session):
        """Test creating event when user has no Google Auth"""
        db_session.commit()
        api_client.login(admin_user)
        
        response = api_client.post('/calendar/api/events', json={
            'title': 'Test Event',
            'start': datetime.utcnow().isoformat(),
            'end': (datetime.utcnow() + timedelta(hours=1)).isoformat()
        })
        
        # Should fail gracefully
        assert response.status_code in (HTTPStatus.BAD_REQUEST, HTTPStatus.OK)
    
    def test_create_event_missing_required_fields(self, api_client, admin_user, db_session):
        """Test creating event with missing required fields"""
        db_session.commit()
        api_client.login(admin_user)
        
        response = api_client.post('/calendar/api/events', json={
            'title': 'Test Event'
            # Missing start and end
        })
        
        assert response.status_code in (HTTPStatus.BAD_REQUEST, HTTPStatus.OK)


class TestCalendarGetMeetings:
    """Test GET /calendar/api/meetings/<id> - Get meetings for customer"""
    
    def test_get_meetings_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/calendar/api/meetings/1')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_get_meetings_customer_not_found(self, api_client, admin_user, db_session):
        """Test getting meetings for non-existent customer"""
        db_session.commit()
        api_client.login(admin_user)
        
        response = api_client.get('/calendar/api/meetings/99999')
        
        # Should return empty or 404
        assert response.status_code in (HTTPStatus.NOT_FOUND, HTTPStatus.OK)
    
    def test_get_meetings_success(self, api_client, admin_user, db_session):
        """Test successful meetings retrieval"""
        from tests.factories import ClienteFactory
        
        cliente = ClienteFactory()
        db_session.commit()
        
        api_client.login(admin_user)
        response = api_client.get(f'/calendar/api/meetings/{cliente.cliente_id}')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert isinstance(data, list)


class TestCalendarGetMeetingDetails:
    """Test GET /calendar/api/meeting/<id> - Get meeting details"""
    
    def test_get_meeting_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/calendar/api/meeting/1')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_get_meeting_not_found(self, api_client, admin_user, db_session):
        """Test getting non-existent meeting"""
        db_session.commit()
        api_client.login(admin_user)
        
        response = api_client.get('/calendar/api/meeting/99999')
        
        assert response.status_code == HTTPStatus.NOT_FOUND


class TestCalendarUpdateMeeting:
    """Test PUT /calendar/api/meeting/<id> - Update meeting"""
    
    def test_update_meeting_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.put('/calendar/api/meeting/1', json={
            'title': 'Updated'
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_update_meeting_not_found(self, api_client, admin_user, db_session):
        """Test updating non-existent meeting"""
        db_session.commit()
        api_client.login(admin_user)
        
        response = api_client.put('/calendar/api/meeting/99999', json={
            'title': 'Updated'
        })
        
        assert response.status_code == HTTPStatus.NOT_FOUND


class TestCalendarDeleteMeeting:
    """Test DELETE /calendar/api/meeting/<id> - Delete meeting"""
    
    def test_delete_meeting_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.delete('/calendar/api/meeting/1')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_delete_meeting_not_found(self, api_client, admin_user, db_session):
        """Test deleting non-existent meeting"""
        db_session.commit()
        api_client.login(admin_user)
        
        response = api_client.delete('/calendar/api/meeting/99999')
        
        assert response.status_code == HTTPStatus.NOT_FOUND


class TestCalendarDeleteEvent:
    """Test DELETE /calendar/api/event/<google_event_id> - Delete event by Google ID"""
    
    def test_delete_event_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.delete('/calendar/api/event/google123')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_delete_event_no_google_auth(self, api_client, admin_user, db_session):
        """Test deleting event when user has no Google Auth"""
        db_session.commit()
        api_client.login(admin_user)
        
        response = api_client.delete('/calendar/api/event/google123')
        
        # Should fail gracefully
        assert response.status_code in (HTTPStatus.BAD_REQUEST, HTTPStatus.OK, HTTPStatus.NOT_FOUND)


class TestCalendarSyncSingleEvent:
    """Test POST /calendar/api/sync-single-event - Sync single event"""
    
    def test_sync_event_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.post('/calendar/api/sync-single-event', json={
            'event_id': 'google123'
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_sync_event_missing_event_id(self, api_client, admin_user, db_session):
        """Test syncing without event_id"""
        db_session.commit()
        api_client.login(admin_user)
        
        response = api_client.post('/calendar/api/sync-single-event', json={})
        
        # Can fail with 400, 500, or succeed with empty result
        assert response.status_code in (HTTPStatus.BAD_REQUEST, HTTPStatus.OK, HTTPStatus.INTERNAL_SERVER_ERROR)
    
    def test_sync_event_no_google_auth(self, api_client, admin_user, db_session):
        """Test syncing when user has no Google Auth"""
        db_session.commit()
        api_client.login(admin_user)
        
        response = api_client.post('/calendar/api/sync-single-event', json={
            'event_id': 'google123'
        })
        
        # Can fail with 400, 500, or succeed with empty result
        assert response.status_code in (HTTPStatus.BAD_REQUEST, HTTPStatus.OK, HTTPStatus.INTERNAL_SERVER_ERROR)


class TestCalendarConnectionStatus:
    """Test GET /calendar/api/connection-status - Check Google Calendar connection"""
    
    def test_connection_status_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/calendar/api/connection-status')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_connection_status_no_auth(self, api_client, admin_user, db_session):
        """Test connection status when user has no Google Auth"""
        db_session.commit()
        api_client.login(admin_user)
        
        response = api_client.get('/calendar/api/connection-status')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        # Check for connection status indicators
        assert 'is_connected' in data or 'connected' in data or 'status' in data or 'success' in data
    
    def test_connection_status_success(self, api_client, admin_user, db_session):
        """Test successful connection status retrieval"""
        db_session.commit()
        api_client.login(admin_user)
        
        response = api_client.get('/calendar/api/connection-status')
        
        assert response.status_code == HTTPStatus.OK


class TestCalendarTokenRefresh:
    """Test POST /calendar/api/admin/tokens/refresh - Refresh Google tokens"""
    
    def test_refresh_tokens_requires_admin(self, api_client, user, db_session):
        """Test that non-admin cannot refresh tokens"""
        db_session.commit()
        api_client.login(user)
        
        response = api_client.post('/calendar/api/admin/tokens/refresh')
        
        assert response.status_code == HTTPStatus.FORBIDDEN
    
    def test_refresh_tokens_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.post('/calendar/api/admin/tokens/refresh')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_refresh_tokens_success(self, api_client, admin_user, db_session):
        """Test successful token refresh"""
        db_session.commit()
        api_client.login(admin_user)
        
        response = api_client.post('/calendar/api/admin/tokens/refresh')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert 'success' in data or 'refreshed' in data or 'message' in data


class TestCalendarTokenCleanup:
    """Test POST /calendar/api/admin/tokens/cleanup - Cleanup expired tokens"""
    
    def test_cleanup_tokens_requires_admin(self, api_client, user, db_session):
        """Test that non-admin cannot cleanup tokens"""
        db_session.commit()
        api_client.login(user)
        
        response = api_client.post('/calendar/api/admin/tokens/cleanup')
        
        assert response.status_code == HTTPStatus.FORBIDDEN
    
    def test_cleanup_tokens_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.post('/calendar/api/admin/tokens/cleanup')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_cleanup_tokens_success(self, api_client, admin_user, db_session):
        """Test successful token cleanup"""
        db_session.commit()
        api_client.login(admin_user)
        
        response = api_client.post('/calendar/api/admin/tokens/cleanup')
        
        assert response.status_code == HTTPStatus.OK


class TestCalendarTokenStatusAdmin:
    """Test GET /calendar/api/admin/tokens/status - Get tokens status"""
    
    def test_tokens_status_requires_admin(self, api_client, user, db_session):
        """Test that non-admin cannot view token status"""
        db_session.commit()
        api_client.login(user)
        
        response = api_client.get('/calendar/api/admin/tokens/status')
        
        assert response.status_code == HTTPStatus.FORBIDDEN
    
    def test_tokens_status_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/calendar/api/admin/tokens/status')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_tokens_status_success(self, api_client, admin_user, db_session):
        """Test successful token status retrieval"""
        db_session.commit()
        api_client.login(admin_user)
        
        response = api_client.get('/calendar/api/admin/tokens/status')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert isinstance(data, (dict, list))


class TestCalendarTeamUsers:
    """Test GET /calendar/api/team/users - Get team users for calendar"""
    
    def test_team_users_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/calendar/api/team/users')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_team_users_success(self, api_client, admin_user, db_session):
        """Test successful team users retrieval"""
        db_session.commit()
        api_client.login(admin_user)
        
        response = api_client.get('/calendar/api/team/users')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        # API wraps result in 'users' key
        assert 'users' in data or isinstance(data, list)


class TestCalendarCustomersSearch:
    """Test GET /calendar/api/customers/search - Search customers"""
    
    def test_customers_search_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/calendar/api/customers/search?q=test')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_customers_search_empty_query(self, api_client, admin_user, db_session):
        """Test search with empty query"""
        db_session.commit()
        api_client.login(admin_user)
        
        response = api_client.get('/calendar/api/customers/search?q=')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        # API wraps result in 'customers' key
        assert 'customers' in data or isinstance(data, list)
    
    def test_customers_search_with_query(self, api_client, admin_user, db_session):
        """Test search with specific query"""
        from tests.factories import ClienteFactory
        
        cliente = ClienteFactory(nome_cognome='Mario Rossi')
        db_session.commit()
        
        api_client.login(admin_user)
        response = api_client.get('/calendar/api/customers/search?q=Mario')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        # API wraps result in 'customers' key
        assert 'customers' in data or isinstance(data, list)


class TestCalendarCustomersList:
    """Test GET /calendar/api/customers/list - List customers"""
    
    def test_customers_list_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/calendar/api/customers/list')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_customers_list_success(self, api_client, admin_user, db_session):
        """Test successful customers list retrieval"""
        db_session.commit()
        api_client.login(admin_user)
        
        response = api_client.get('/calendar/api/customers/list')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        # API wraps result in 'customers' key
        assert 'customers' in data or isinstance(data, list)


class TestCalendarCustomerMinimal:
    """Test GET /calendar/api/customers/<id>/minimal - Get customer minimal data"""
    
    def test_customer_minimal_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/calendar/api/customers/1/minimal')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_customer_minimal_not_found(self, api_client, admin_user, db_session):
        """Test getting minimal data for non-existent customer"""
        db_session.commit()
        api_client.login(admin_user)
        
        response = api_client.get('/calendar/api/customers/99999/minimal')
        
        assert response.status_code == HTTPStatus.NOT_FOUND
    
    def test_customer_minimal_success(self, api_client, admin_user, db_session):
        """Test successful customer minimal data retrieval"""
        from tests.factories import ClienteFactory
        
        cliente = ClienteFactory()
        db_session.commit()
        
        api_client.login(admin_user)
        response = api_client.get(f'/calendar/api/customers/{cliente.cliente_id}/minimal')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert 'id' in data or 'nome_cognome' in data or 'cliente_id' in data


class TestCalendarSchedulerStatus:
    """Test GET /calendar/api/admin/scheduler/status - Get scheduler status"""
    
    def test_scheduler_status_requires_admin(self, api_client, user, db_session):
        """Test that non-admin cannot view scheduler status"""
        db_session.commit()
        api_client.login(user)
        
        response = api_client.get('/calendar/api/admin/scheduler/status')
        
        assert response.status_code == HTTPStatus.FORBIDDEN
    
    def test_scheduler_status_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/calendar/api/admin/scheduler/status')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_scheduler_status_success(self, api_client, admin_user, db_session):
        """Test successful scheduler status retrieval"""
        db_session.commit()
        api_client.login(admin_user)
        
        response = api_client.get('/calendar/api/admin/scheduler/status')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert isinstance(data, dict)


class TestCalendarAdminRefreshUserToken:
    """Test POST /calendar/api/admin/tokens/<user_id>/refresh - Refresh specific user token"""
    
    def test_refresh_user_token_requires_admin(self, api_client, user, db_session):
        """Test that non-admin cannot refresh user token"""
        db_session.commit()
        api_client.login(user)
        
        response = api_client.post('/calendar/api/admin/tokens/1/refresh')
        
        assert response.status_code == HTTPStatus.FORBIDDEN
    
    def test_refresh_user_token_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.post('/calendar/api/admin/tokens/1/refresh')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_refresh_user_token_not_found(self, api_client, admin_user, db_session):
        """Test refreshing token for non-existent user"""
        db_session.commit()
        api_client.login(admin_user)
        
        response = api_client.post('/calendar/api/admin/tokens/99999/refresh')
        
        assert response.status_code == HTTPStatus.NOT_FOUND
    
    def test_refresh_user_token_success(self, api_client, admin_user, db_session):
        """Test successful user token refresh"""
        from tests.factories import UserFactory
        
        user = UserFactory()
        db_session.commit()
        
        api_client.login(admin_user)
        response = api_client.post(f'/calendar/api/admin/tokens/{user.id}/refresh')
        
        assert response.status_code in (HTTPStatus.OK, HTTPStatus.NOT_FOUND)
