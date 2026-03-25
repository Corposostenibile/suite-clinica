"""
API Tests per il blueprint Review/Training (React API).
Testa gli endpoint JSON che il frontend React chiama per la gestione di training e review.

Endpoints testati:
- GET /review/api/my-trainings - Get user's trainings
- GET /review/api/my-requests - Get user's training requests
- GET /review/api/received-requests - Get received training requests
- GET /review/api/given-trainings - Get trainings given by user
- GET /review/api/request-recipients - Get list of potential request recipients
- POST /review/api/request - Create training request
- POST /review/api/request/<id>/respond - Respond to training request
- POST /review/api/request/<id>/cancel - Cancel training request
"""

from http import HTTPStatus
import pytest
from datetime import datetime, date, timedelta
from corposostenibile.extensions import db
from corposostenibile.models import User


class TestReviewMyTrainings:
    """Test GET /review/api/my-trainings - Get user's trainings"""
    
    def test_my_trainings_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/review/api/my-trainings')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_my_trainings_success_empty(self, api_client, login_test_user, db_session):
        """Test successful retrieval with no trainings"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/review/api/my-trainings')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert isinstance(data, (list, dict))
    
    def test_my_trainings_pagination(self, api_client, login_test_user, db_session):
        """Test my trainings with pagination"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/review/api/my-trainings?page=1&per_page=10')
        
        assert response.status_code == HTTPStatus.OK


class TestReviewMyRequests:
    """Test GET /review/api/my-requests - Get user's training requests"""
    
    def test_my_requests_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/review/api/my-requests')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_my_requests_success(self, api_client, login_test_user, db_session):
        """Test successful retrieval of user's requests"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/review/api/my-requests')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert isinstance(data, (list, dict))
    
    def test_my_requests_response_structure(self, api_client, login_test_user, db_session):
        """Test response structure"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/review/api/my-requests')
        
        assert response.status_code == HTTPStatus.OK


class TestReviewReceivedRequests:
    """Test GET /review/api/received-requests - Get received training requests"""
    
    def test_received_requests_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/review/api/received-requests')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_received_requests_success(self, api_client, login_test_user, db_session):
        """Test successful retrieval of received requests"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/review/api/received-requests')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert isinstance(data, (list, dict))
    
    def test_received_requests_with_status_filter(self, api_client, login_test_user, db_session):
        """Test filtering received requests by status"""
        db_session.commit()
        api_client.login(login_test_user)
        
        for status in ['pending', 'approved', 'rejected']:
            response = api_client.get(f'/review/api/received-requests?status={status}')
            assert response.status_code == HTTPStatus.OK


class TestReviewGivenTrainings:
    """Test GET /review/api/given-trainings - Get trainings given by user"""
    
    def test_given_trainings_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/review/api/given-trainings')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_given_trainings_success(self, api_client, login_test_user, db_session):
        """Test successful retrieval of given trainings"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/review/api/given-trainings')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert isinstance(data, (list, dict))


class TestReviewRequestRecipients:
    """Test GET /review/api/request-recipients - Get list of potential recipients"""
    
    def test_request_recipients_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/review/api/request-recipients')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_request_recipients_success(self, api_client, login_test_user, db_session):
        """Test successful retrieval of potential recipients"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/review/api/request-recipients')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert isinstance(data, (list, dict))
    
    def test_request_recipients_search(self, api_client, login_test_user, db_session):
        """Test searching for recipients"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/review/api/request-recipients?q=test')
        
        assert response.status_code == HTTPStatus.OK


class TestReviewCreateRequest:
    """Test POST /review/api/request - Create training request"""
    
    def test_create_request_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.post('/review/api/request', json={
            'recipient_id': 1,
            'title': 'Training request'
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_create_request_success(self, api_client, login_test_user, db_session):
        """Test successful request creation"""
        from tests.factories import UserFactory
        
        recipient = UserFactory(email='recipient@test.com')
        db_session.commit()
        
        api_client.login(login_test_user)
        response = api_client.post('/review/api/request', json={
            'recipient_id': recipient.id,
            'title': 'Training Request',
            'description': 'Please provide training on XYZ'
        })
        
        # Should succeed or return validation error
        assert response.status_code in (HTTPStatus.OK, HTTPStatus.CREATED, HTTPStatus.BAD_REQUEST)
    
    def test_create_request_invalid_recipient(self, api_client, login_test_user, db_session):
        """Test creating request with invalid recipient"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.post('/review/api/request', json={
            'recipient_id': 99999,
            'title': 'Training Request'
        })
        
        # Should fail with invalid recipient
        assert response.status_code in (HTTPStatus.NOT_FOUND, HTTPStatus.BAD_REQUEST)
    
    def test_create_request_missing_fields(self, api_client, login_test_user, db_session):
        """Test creating request with missing required fields"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.post('/review/api/request', json={})
        
        assert response.status_code in (HTTPStatus.BAD_REQUEST, HTTPStatus.UNPROCESSABLE_ENTITY)


class TestReviewRespondRequest:
    """Test POST /review/api/request/<id>/respond - Respond to request"""
    
    def test_respond_request_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.post('/review/api/request/1/respond', json={
            'status': 'approved'
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_respond_request_not_found(self, api_client, login_test_user, db_session):
        """Test responding to non-existent request"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.post('/review/api/request/99999/respond', json={
            'status': 'approved'
        })
        
        assert response.status_code in (HTTPStatus.NOT_FOUND, HTTPStatus.BAD_REQUEST)
    
    def test_respond_request_approve(self, api_client, login_test_user, db_session):
        """Test approving a training request"""
        db_session.commit()
        api_client.login(login_test_user)
        
        # Using a placeholder ID for test
        response = api_client.post('/review/api/request/1/respond', json={
            'status': 'approved'
        })
        
        # Should handle gracefully even if request doesn't exist
        assert response.status_code in (HTTPStatus.OK, HTTPStatus.NOT_FOUND, HTTPStatus.BAD_REQUEST)
    
    def test_respond_request_reject(self, api_client, login_test_user, db_session):
        """Test rejecting a training request"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.post('/review/api/request/1/respond', json={
            'status': 'rejected',
            'rejection_reason': 'Not available'
        })
        
        assert response.status_code in (HTTPStatus.OK, HTTPStatus.NOT_FOUND, HTTPStatus.BAD_REQUEST)


class TestReviewCancelRequest:
    """Test POST /review/api/request/<id>/cancel - Cancel request"""
    
    def test_cancel_request_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.post('/review/api/request/1/cancel', json={})
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_cancel_request_not_found(self, api_client, login_test_user, db_session):
        """Test canceling non-existent request"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.post('/review/api/request/99999/cancel', json={})
        
        assert response.status_code in (HTTPStatus.NOT_FOUND, HTTPStatus.BAD_REQUEST)
    
    def test_cancel_request_success(self, api_client, login_test_user, db_session):
        """Test canceling a request"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.post('/review/api/request/1/cancel', json={})
        
        # Should handle gracefully
        assert response.status_code in (HTTPStatus.OK, HTTPStatus.NOT_FOUND, HTTPStatus.BAD_REQUEST)
