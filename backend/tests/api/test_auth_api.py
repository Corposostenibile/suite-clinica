"""
API Tests per il blueprint Auth (React API).
Testa gli endpoint JSON che il frontend React chiama direttamente.

Endpoints testati:
- POST /api/auth/login - Login con email e password
- POST /api/auth/logout - Logout utente corrente
- GET /api/auth/me - Informazioni utente autenticato
- POST /api/auth/forgot-password - Richiesta reset password
- GET /api/auth/verify-reset-token/<token> - Verifica token reset
- POST /api/auth/reset-password/<token> - Reset password con token
- GET /api/auth/impersonate/users - Lista utenti per impersonazione (admin)
- POST /api/auth/impersonate/<user_id> - Impersonare utente (admin)
- POST /api/auth/stop-impersonation - Torna all'account admin
"""

from http import HTTPStatus
import pytest
from corposostenibile.extensions import db
from corposostenibile.models import User, UserRoleEnum, ImpersonationLog, Department
from werkzeug.security import generate_password_hash


@pytest.fixture
def login_test_user(db_session):
    """Create a user in the database for login testing"""
    from tests.factories import DepartmentFactory
    
    dept = DepartmentFactory()
    db_session.commit()
    
    user = User(
        email='login_test@example.com',
        first_name='Login',
        last_name='Test',
        password_hash=generate_password_hash('TestPassword123!'),
        is_active=True,
        is_admin=False,
        role=UserRoleEnum.professionista
    )
    db_session.add(user)
    db_session.commit()
    
    return user


@pytest.fixture
def admin_login_test_user(db_session):
    """Create an admin user in the database for login testing"""
    from tests.factories import DepartmentFactory
    
    dept = DepartmentFactory()
    db_session.commit()
    
    user = User(
        email='admin_login_test@example.com',
        first_name='Admin',
        last_name='Login',
        password_hash=generate_password_hash('AdminPass123!'),
        is_active=True,
        is_admin=True,
        role=UserRoleEnum.professionista
    )
    db_session.add(user)
    db_session.commit()
    
    return user


class TestAuthLogin:
    """Test POST /api/auth/login - Login with email and password"""
    
    def test_login_success_with_valid_credentials(self, api_client, admin_login_test_user):
        """Test successful login with valid email and password"""
        response = api_client.post('/api/auth/login', json={
            'email': admin_login_test_user.email,
            'password': 'AdminPass123!',
            'remember_me': False
        })
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['success'] is True
        assert 'user' in data
        assert data['user']['email'] == admin_login_test_user.email
        assert data['user']['is_admin'] is True
        assert 'redirect' in data
    
    def test_login_with_remember_me(self, api_client, admin_login_test_user):
        """Test login with remember_me flag"""
        response = api_client.post('/api/auth/login', json={
            'email': admin_login_test_user.email,
            'password': 'AdminPass123!',
            'remember_me': True
        })
        
        assert response.status_code == HTTPStatus.OK
        assert response.json['success'] is True
    
    def test_login_already_authenticated(self, api_client, admin_user):
        """Test login when already authenticated"""
        api_client.login(admin_user)
        
        response = api_client.post('/api/auth/login', json={
            'email': admin_user.email,
            'password': 'password'
        })
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['success'] is True
        assert 'redirect' in data
    
    def test_login_invalid_email(self, api_client):
        """Test login with non-existent email"""
        response = api_client.post('/api/auth/login', json={
            'email': 'nonexistent@example.com',
            'password': 'SomePassword123!'
        })
        
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert response.json['success'] is False
        assert 'Email non trovata' in response.json['error']
    
    def test_login_wrong_password(self, api_client, admin_login_test_user):
        """Test login with wrong password"""
        response = api_client.post('/api/auth/login', json={
            'email': admin_login_test_user.email,
            'password': 'WrongPassword123!'
        })
        
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert response.json['success'] is False
        assert 'Password errata' in response.json['error']
    
    def test_login_missing_email(self, api_client):
        """Test login without email"""
        response = api_client.post('/api/auth/login', json={
            'password': 'SomePassword123!'
        })
        
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json['success'] is False
        assert 'Email e password' in response.json['error']
    
    def test_login_missing_password(self, api_client, admin_login_test_user):
        """Test login without password"""
        response = api_client.post('/api/auth/login', json={
            'email': admin_login_test_user.email
        })
        
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json['success'] is False
    
    def test_login_empty_body(self, api_client):
        """Test login with empty body"""
        response = api_client.post('/api/auth/login', json={})
        
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json['success'] is False
    
    def test_login_inactive_user(self, api_client, db_session):
        """Test login with inactive user"""
        from tests.factories import DepartmentFactory
        
        dept = DepartmentFactory()
        user = User(
            email='inactive@example.com',
            first_name='Inactive',
            last_name='User',
            password_hash=generate_password_hash('InactivePass123!'),
            is_active=False,
            role=UserRoleEnum.professionista
        )
        db_session.add(user)
        db_session.commit()
        
        response = api_client.post('/api/auth/login', json={
            'email': 'inactive@example.com',
            'password': 'InactivePass123!'
        })
        
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert 'disattivato' in response.json['error']
    
    def test_login_case_insensitive_email(self, api_client, admin_login_test_user):
        """Test login with uppercase email"""
        response = api_client.post('/api/auth/login', json={
            'email': admin_login_test_user.email.upper(),
            'password': 'AdminPass123!'
        })
        
        assert response.status_code == HTTPStatus.OK
        assert response.json['success'] is True
    
    def test_login_user_with_clinical_role(self, api_client, login_test_user):
        """Test login with non-admin clinical user"""
        response = api_client.post('/api/auth/login', json={
            'email': login_test_user.email,
            'password': 'TestPassword123!'
        })
        
        assert response.status_code == HTTPStatus.OK
        assert response.json['success'] is True
        assert response.json['user']['is_admin'] is False


class TestAuthLogout:
    """Test POST /api/auth/logout - Logout current user"""
    
    def test_logout_success(self, api_client, admin_user):
        """Test successful logout"""
        api_client.login(admin_user)
        
        response = api_client.post('/api/auth/logout')
        
        assert response.status_code == HTTPStatus.OK
        assert response.json['success'] is True
        assert 'uscito' in response.json['message']
    
    def test_logout_not_authenticated(self, api_client):
        """Test logout without being authenticated"""
        response = api_client.post('/api/auth/logout')
        
        # Flask-Login returns 401 for protected endpoints without authentication
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_logout_then_access_protected_endpoint(self, api_client, admin_user):
        """Test logout and access protected endpoint"""
        api_client.login(admin_user)
        
        # First logout
        api_client.post('/api/auth/logout', follow_redirects=True)
        api_client.logout() # Ensure mock is cleared
        
        # Try to access /api/auth/me which requires authentication
        response = api_client.get('/api/auth/me')
        
        # Should return not authenticated
        assert response.status_code == HTTPStatus.OK
        assert response.json['authenticated'] is False


class TestAuthMe:
    """Test GET /api/auth/me - Get current user info"""
    
    def test_me_authenticated(self, api_client, admin_user):
        """Test /me endpoint when authenticated"""
        api_client.login(admin_user)
        
        response = api_client.get('/api/auth/me')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['authenticated'] is True
        assert 'user' in data
        assert data['user']['email'] == admin_user.email
        assert data['user']['is_admin'] is True
    
    def test_me_not_authenticated(self, api_client):
        """Test /me endpoint when not authenticated"""
        response = api_client.get('/api/auth/me')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['authenticated'] is False
        assert 'user' not in data
    
    def test_me_user_data_structure(self, api_client, user):
        """Test that /me returns all required user fields"""
        api_client.login(user)
        
        response = api_client.get('/api/auth/me')
        
        assert response.status_code == HTTPStatus.OK
        user_data = response.json['user']
        
        # Check essential fields
        assert 'id' in user_data
        assert 'email' in user_data
        assert 'first_name' in user_data
        assert 'last_name' in user_data
        assert 'full_name' in user_data
        assert 'is_admin' in user_data
        assert 'role' in user_data
    
    def test_me_impersonation_info(self, api_client, admin_user, user):
        """Test that /me includes impersonation info"""
        api_client.login(admin_user)
        
        response = api_client.get('/api/auth/me')
        
        assert response.status_code == HTTPStatus.OK
        user_data = response.json['user']
        assert 'impersonating' in user_data
        assert user_data['impersonating'] is False


class TestAuthForgotPassword:
    """Test POST /api/auth/forgot-password - Request password reset"""
    
    def test_forgot_password_success(self, api_client, admin_user):
        """Test successful forgot password request"""
        response = api_client.post('/api/auth/forgot-password', json={
            'email': admin_user.email
        })
        
        assert response.status_code == HTTPStatus.OK
        assert response.json['success'] is True
        assert 'Email' in response.json['message'] or 'email' in response.json['message'].lower()
    
    def test_forgot_password_nonexistent_email(self, api_client):
        """Test forgot password with non-existent email (should still return success for privacy)"""
        response = api_client.post('/api/auth/forgot-password', json={
            'email': 'nonexistent@example.com'
        })
        
        # Returns success for privacy (don't reveal if email exists)
        assert response.status_code == HTTPStatus.OK
        assert response.json['success'] is True
    
    def test_forgot_password_missing_email(self, api_client):
        """Test forgot password without email"""
        response = api_client.post('/api/auth/forgot-password', json={})
        
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json['success'] is False
        assert 'Email' in response.json['error']
    
    def test_forgot_password_empty_body(self, api_client):
        """Test forgot password with empty body"""
        # Cambiato da json=None a json={} per evitare 415
        response = api_client.post('/api/auth/forgot-password', json={})
        
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json['success'] is False
    
    def test_forgot_password_already_authenticated(self, api_client, admin_login_test_user):
        """Test forgot password when already authenticated"""
        # Login reale
        api_client.post('/api/auth/login', json={
            'email': admin_login_test_user.email,
            'password': 'AdminPass123!'
        })
        
        response = api_client.post('/api/auth/forgot-password', json={
            'email': admin_login_test_user.email
        })
        
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json['success'] is False
        assert 'Già autenticato' in response.json['error']
    
    def test_forgot_password_case_insensitive(self, api_client, admin_user):
        """Test forgot password with uppercase email"""
        response = api_client.post('/api/auth/forgot-password', json={
            'email': admin_user.email.upper()
        })
        
        assert response.status_code == HTTPStatus.OK
        assert response.json['success'] is True


class TestAuthVerifyResetToken:
    """Test GET /api/auth/verify-reset-token/<token> - Verify reset token"""
    
    def test_verify_reset_token_invalid(self, api_client):
        """Test verification with invalid token"""
        response = api_client.get('/api/auth/verify-reset-token/invalid_token_12345')
        
        assert response.status_code == HTTPStatus.BAD_REQUEST
        data = response.json
        assert data['valid'] is False
        assert 'non valido' in data['error'] or 'scaduto' in data['error']
    
    def test_verify_reset_token_empty(self, api_client):
        """Test verification with empty token"""
        response = api_client.get('/api/auth/verify-reset-token/')
        
        # This will likely be a 404 since the route won't match
        assert response.status_code in [HTTPStatus.NOT_FOUND, HTTPStatus.BAD_REQUEST]


class TestAuthResetPassword:
    """Test POST /api/auth/reset-password/<token> - Reset password with token"""
    
    def test_reset_password_invalid_token(self, api_client):
        """Test reset password with invalid token"""
        response = api_client.post('/api/auth/reset-password/invalid_token_12345', json={
            'password': 'NewPassword123!',
            'password2': 'NewPassword123!'
        })
        
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json['success'] is False
        assert 'non valido' in response.json['error'] or 'scaduto' in response.json['error']
    
    def test_reset_password_already_authenticated(self, api_client, admin_user):
        """Test reset password when already authenticated"""
        api_client.login(admin_user)
        
        response = api_client.post('/api/auth/reset-password/any_token', json={
            'password': 'NewPassword123!',
            'password2': 'NewPassword123!'
        })
        
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json['success'] is False
        assert 'Già autenticato' in response.json['error']
    
    def test_reset_password_passwords_mismatch(self, api_client):
        """Test reset password with mismatched passwords"""
        # Create a valid reset token first
        from corposostenibile.blueprints.auth.routes import _generate_reset_token
        from corposostenibile.models import User
        
        user = User.query.first()  # Use any user in database
        if user:
            token = _generate_reset_token(user)
            
            response = api_client.post(f'/api/auth/reset-password/{token}', json={
                'password': 'NewPassword123!',
                'password2': 'DifferentPassword123!'
            })
            
            assert response.status_code == HTTPStatus.BAD_REQUEST
            assert response.json['success'] is False
            assert 'non coincidono' in response.json['error']
    
    def test_reset_password_too_short(self, api_client):
        """Test reset password with password too short"""
        from corposostenibile.blueprints.auth.routes import _generate_reset_token
        from corposostenibile.models import User
        
        user = User.query.first()
        if user:
            token = _generate_reset_token(user)
            
            response = api_client.post(f'/api/auth/reset-password/{token}', json={
                'password': 'Short1!',  # Less than 8 chars
                'password2': 'Short1!'
            })
            
            assert response.status_code == HTTPStatus.BAD_REQUEST
            assert response.json['success'] is False
            assert '8 caratteri' in response.json['error']
    
    def test_reset_password_no_uppercase(self, api_client):
        """Test reset password without uppercase letter"""
        from corposostenibile.blueprints.auth.routes import _generate_reset_token
        from corposostenibile.models import User
        
        user = User.query.first()
        if user:
            token = _generate_reset_token(user)
            
            response = api_client.post(f'/api/auth/reset-password/{token}', json={
                'password': 'newpassword123!',
                'password2': 'newpassword123!'
            })
            
            assert response.status_code == HTTPStatus.BAD_REQUEST
            assert response.json['success'] is False
            assert 'maiuscola' in response.json['error']
    
    def test_reset_password_no_number(self, api_client):
        """Test reset password without number"""
        from corposostenibile.blueprints.auth.routes import _generate_reset_token
        from corposostenibile.models import User
        
        user = User.query.first()
        if user:
            token = _generate_reset_token(user)
            
            response = api_client.post(f'/api/auth/reset-password/{token}', json={
                'password': 'NewPassword!',
                'password2': 'NewPassword!'
            })
            
            assert response.status_code == HTTPStatus.BAD_REQUEST
            assert response.json['success'] is False
            assert 'numero' in response.json['error']
    
    def test_reset_password_no_special_char(self, api_client):
        """Test reset password without special character"""
        from corposostenibile.blueprints.auth.routes import _generate_reset_token
        from corposostenibile.models import User
        
        user = User.query.first()
        if user:
            token = _generate_reset_token(user)
            
            response = api_client.post(f'/api/auth/reset-password/{token}', json={
                'password': 'NewPassword123',
                'password2': 'NewPassword123'
            })
            
            assert response.status_code == HTTPStatus.BAD_REQUEST
            assert response.json['success'] is False
            assert 'speciale' in response.json['error']


class TestAuthImpersonateUsers:
    """Test GET /api/auth/impersonate/users - List users for impersonation"""
    
    def test_impersonate_users_admin_success(self, api_client, admin_user, user, db_session):
        """Test listing users as admin"""
        api_client.login(admin_user)
        
        response = api_client.get('/api/auth/impersonate/users')
        
        assert response.status_code == HTTPStatus.OK
        assert response.json['success'] is True
        assert 'users' in response.json
        assert isinstance(response.json['users'], list)
    
    def test_impersonate_users_non_admin(self, api_client, user):
        """Test listing users as non-admin returns 403"""
        api_client.login(user)
        
        response = api_client.get('/api/auth/impersonate/users')
        
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert response.json['success'] is False
        assert 'non autorizzato' in response.json['error']
    
    def test_impersonate_users_not_authenticated(self, api_client):
        """Test listing users without authentication"""
        response = api_client.get('/api/auth/impersonate/users')
        
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_impersonate_users_excludes_inactive(self, api_client, admin_user, db_session):
        """Test that inactive users are not listed"""
        # Create an inactive user
        inactive_user = User(
            email='inactive@example.com',
            first_name='Inactive',
            last_name='User',
            password_hash=generate_password_hash('TestPass123!'),
            is_active=False,
            role=UserRoleEnum.professionista
        )
        db_session.add(inactive_user)
        db_session.commit()
        
        api_client.login(admin_user)
        response = api_client.get('/api/auth/impersonate/users')
        
        assert response.status_code == HTTPStatus.OK
        user_emails = [u['email'] for u in response.json['users']]
        assert 'inactive@example.com' not in user_emails
    
    def test_impersonate_users_excludes_admin(self, api_client, admin_user, db_session):
        """Test that admin is excluded from the list"""
        api_client.login(admin_user)
        
        response = api_client.get('/api/auth/impersonate/users')
        
        assert response.status_code == HTTPStatus.OK
        user_ids = [u['id'] for u in response.json['users']]
        assert admin_user.id not in user_ids
    
    def test_impersonate_users_user_structure(self, api_client, admin_user, user):
        """Test that user data has required fields"""
        api_client.login(admin_user)
        
        response = api_client.get('/api/auth/impersonate/users')
        
        assert response.status_code == HTTPStatus.OK
        users = response.json['users']
        if users:
            user_data = users[0]
            assert 'id' in user_data
            assert 'full_name' in user_data
            assert 'email' in user_data
            assert 'role' in user_data


class TestAuthImpersonateUser:
    """Test POST /api/auth/impersonate/<user_id> - Impersonate a user"""
    
    def test_impersonate_success(self, api_client, admin_login_test_user, login_test_user, db_session):
        """Test successful impersonation"""
        # Pulizia mock prima di login reale
        api_client.logout()
        # Login reale come admin
        api_client.post('/api/auth/login', json={
            'email': admin_login_test_user.email,
            'password': 'AdminPass123!'
        })
        
        target_user_id = db_session.query(User.id).filter_by(email="login_test@example.com").scalar()
        assert target_user_id is not None
        response = api_client.post(f'/api/auth/impersonate/{target_user_id}')
        
        assert response.status_code == HTTPStatus.OK
        assert response.json['success'] is True
        assert 'navigando come' in response.json['message']
    
    def test_impersonate_non_admin(self, api_client, login_test_user, user):
        """Test impersonation as non-admin returns 403"""
        api_client.logout()
        # Login reale come utente non admin
        api_client.post('/api/auth/login', json={
            'email': login_test_user.email,
            'password': 'TestPassword123!'
        })
        
        response = api_client.post(f'/api/auth/impersonate/{user.id}')
        
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert response.json['success'] is False
    
    def test_impersonate_not_authenticated(self, api_client, login_test_user):
        """Test impersonation without authentication"""
        api_client.logout()
        response = api_client.post(f'/api/auth/impersonate/{login_test_user.id}')
        
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_impersonate_nonexistent_user(self, api_client, admin_login_test_user):
        """Test impersonation of non-existent user"""
        api_client.logout()
        api_client.post('/api/auth/login', json={
            'email': admin_login_test_user.email,
            'password': 'AdminPass123!'
        })
        
        response = api_client.post('/api/auth/impersonate/99999')
        
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json['success'] is False
        assert 'non trovato' in response.json['error']
    
    def test_impersonate_self(self, api_client, admin_login_test_user):
        """Test impersonating oneself"""
        api_client.logout()
        api_client.post('/api/auth/login', json={
            'email': admin_login_test_user.email,
            'password': 'AdminPass123!'
        })
        
        response = api_client.post(f'/api/auth/impersonate/{admin_login_test_user.id}')
        
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json['success'] is False
        assert 'te stesso' in response.json['error']
    
    def test_impersonate_while_impersonating(self, api_client, admin_login_test_user, login_test_user, db_session):
        """Test that can't impersonate while already impersonating"""
        api_client.logout()
        api_client.post('/api/auth/login', json={
            'email': admin_login_test_user.email,
            'password': 'AdminPass123!'
        })
        
        # Start impersonation
        target_user_id = db_session.query(User.id).filter_by(email="login_test@example.com").scalar()
        assert target_user_id is not None
        response1 = api_client.post(f'/api/auth/impersonate/{target_user_id}')
        assert response1.status_code == HTTPStatus.OK
        
        # Create another user
        from tests.factories import UserFactory
        user2 = UserFactory()
        db_session.commit()
        
        # Try to impersonate another user while already impersonating
        response2 = api_client.post(f'/api/auth/impersonate/{user2.id}')
        
        assert response2.status_code == HTTPStatus.BAD_REQUEST
        assert 'già in modalità' in response2.json['error'].lower()


class TestAuthStopImpersonation:
    """Test POST /api/auth/stop-impersonation - Return to admin account"""
    
    def test_stop_impersonation_success(self, api_client, admin_login_test_user, login_test_user, db_session):
        """Test successful stop of impersonation"""
        api_client.logout()
        api_client.post('/api/auth/login', json={
            'email': admin_login_test_user.email,
            'password': 'AdminPass123!'
        })
        
        # Start impersonation
        target_user_id = db_session.query(User.id).filter_by(email="login_test@example.com").scalar()
        assert target_user_id is not None
        api_client.post(f'/api/auth/impersonate/{target_user_id}')
        
        # Stop impersonation
        response = api_client.post('/api/auth/stop-impersonation')
        
        assert response.status_code == HTTPStatus.OK
        assert response.json['success'] is True
        assert 'tornato' in response.json['message']
    
    def test_stop_impersonation_not_impersonating(self, api_client, admin_login_test_user):
        """Test stop impersonation when not impersonating"""
        api_client.logout()
        api_client.post('/api/auth/login', json={
            'email': admin_login_test_user.email,
            'password': 'AdminPass123!'
        })
        
        response = api_client.post('/api/auth/stop-impersonation')
        
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json['success'] is False
        assert 'non sei in modalità' in response.json['error'].lower()
    
    def test_stop_impersonation_not_authenticated(self, api_client):
        """Test stop impersonation without authentication"""
        response = api_client.post('/api/auth/stop-impersonation')
        
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_stop_impersonation_returns_to_admin(self, api_client, admin_login_test_user, login_test_user, db_session):
        """Test that stopping impersonation returns to admin user"""
        api_client.logout()
        api_client.post('/api/auth/login', json={
            'email': admin_login_test_user.email,
            'password': 'AdminPass123!'
        })
        admin_id = db_session.query(User.id).filter_by(email=admin_login_test_user.email).scalar()
        assert admin_id is not None
        
        # Start impersonation
        target_user_id = db_session.query(User.id).filter_by(email="login_test@example.com").scalar()
        assert target_user_id is not None
        api_client.post(f'/api/auth/impersonate/{target_user_id}')
        
        # Verify we're now logged in as the other user
        response1 = api_client.get('/api/auth/me')
        assert response1.json['user']['id'] == target_user_id
        
        # Stop impersonation
        api_client.post('/api/auth/stop-impersonation')
        
        # Verify we're back to admin
        response2 = api_client.get('/api/auth/me')
        assert response2.json['user']['id'] == admin_id
    
    def test_impersonation_creates_log(self, api_client, admin_login_test_user, login_test_user, db_session):
        """Test that impersonation creates a log entry"""
        api_client.logout()
        api_client.post('/api/auth/login', json={
            'email': admin_login_test_user.email,
            'password': 'AdminPass123!'
        })
        
        initial_log_count = db_session.query(ImpersonationLog).count()
        
        # Start impersonation
        target_user_id = db_session.query(User.id).filter_by(email="login_test@example.com").scalar()
        assert target_user_id is not None
        api_client.post(f'/api/auth/impersonate/{target_user_id}')
        
        # Stop impersonation
        api_client.post('/api/auth/stop-impersonation')
        
        # Check that log was created
        final_log_count = db_session.query(ImpersonationLog).count()
        assert final_log_count > initial_log_count
        
        # Check log details
        log = db_session.query(ImpersonationLog).order_by(ImpersonationLog.id.desc()).first()
        admin_id = db_session.query(User.id).filter_by(email=admin_login_test_user.email).scalar()
        assert admin_id is not None
        assert log.admin_id == admin_id
        assert log.impersonated_user_id == target_user_id
        assert log.ended_at is not None
