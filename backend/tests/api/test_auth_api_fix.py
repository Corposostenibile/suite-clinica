import pytest
from http import HTTPStatus

def test_logout_then_access_protected_endpoint_FIXED(api_client, admin_user):
    """Test logout and access protected endpoint"""
    api_client.login(admin_user)
    
    # Logout
    api_client.post('/api/auth/logout', follow_redirects=True)
    
    # IMPORTANT: The login fixture uses a patch on flask_login.utils._get_user.
    # The route calls logout_user(), but the patch remains active in the test context.
    # We must explicitly call api_client.logout() to remove the mock.
    api_client.logout() 
    
    # Access protected
    response = api_client.get('/api/auth/me')
    
    # Should return not authenticated
    assert response.status_code == HTTPStatus.OK
    assert response.json['authenticated'] is False
