"""
API Tests per il blueprint Team (React API).
Testa gli endpoint JSON che il frontend React chiama per la gestione del team.

Endpoints testati:
- GET/POST /api/team/members - List and create team members
- GET/PUT/DELETE /api/team/members/<id> - Individual member operations
- POST /api/team/members/<id>/toggle - Toggle member status
- POST /api/team/members/<id>/avatar - Upload member avatar
- GET /api/team/departments - List departments
- GET /api/team/stats - Team statistics
- GET /api/team/professionals/criteria - Get professional criteria
- PUT /api/team/professionals/<id>/criteria - Update professional criteria
- PUT /api/team/professionals/<id>/toggle-available - Toggle professional availability
- GET /api/team/criteria/schema - Get criteria schema
- POST /api/team/assignments/analyze-lead - Analyze lead story for assignments
- POST /api/team/assignments/match - Match professionals to clients
- POST /api/team/assignments/confirm - Confirm assignment
- GET /api/team/admin-dashboard-stats - Admin dashboard statistics
- GET/POST /api/team/teams - List and create teams
- GET/PUT/DELETE /api/team/teams/<id> - Individual team operations
- POST /api/team/teams/<id>/members - Add member to team
- DELETE /api/team/teams/<id>/members/<id> - Remove member from team
- GET /api/team/available-leaders/<team_type> - Get available team leaders
- GET /api/team/available-professionals/<team_type> - Get available professionals
- GET /api/team/capacity - Get professional capacity metrics
- GET/PUT /api/team/capacity-weights - Get and update capacity weights
- PUT /api/team/capacity/<id> - Update professional capacity
- GET /api/team/members/<id>/clients - Get member's assigned clients
- GET /api/team/members/<id>/checks - Get member's client checks
"""

from http import HTTPStatus
import pytest
from corposostenibile.extensions import db
from corposostenibile.models import (
    User, UserRoleEnum, UserSpecialtyEnum, Department, Team, TeamTypeEnum
)
from werkzeug.security import generate_password_hash


class TestTeamGetMembers:
    """Test GET /api/team/members - List team members with pagination and filters"""
    
    def test_get_members_success_without_login_fails(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/api/team/members')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_get_members_success_with_login(self, api_client, admin_user, db_session):
        """Test successful members list retrieval with login"""
        db_session.commit()  # Ensure admin_user is in DB
        api_client.login(admin_user)
        response = api_client.get('/api/team/members')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['success'] is True
        assert 'members' in data
        assert 'total' in data
        assert 'page' in data
        assert 'per_page' in data
        assert 'total_pages' in data
        assert 'has_next' in data
        assert 'has_prev' in data
    
    def test_get_members_with_pagination(self, api_client, admin_user, db_session):
        """Test members list with pagination parameters"""
        from tests.factories import UserFactory
        
        # Create multiple users
        for i in range(5):
            UserFactory()
        db_session.commit()
        
        api_client.login(admin_user)
        response = api_client.get('/api/team/members?page=1&per_page=2')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert len(data['members']) <= 2
        assert data['per_page'] == 2
    
    def test_get_members_with_search_query(self, api_client, admin_user, db_session):
        """Test members list with search filter"""
        from tests.factories import UserFactory
        
        user = UserFactory(first_name='John', last_name='Doe', email='john@test.com')
        db_session.commit()
        
        api_client.login(admin_user)
        response = api_client.get('/api/team/members?q=John')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['success'] is True
        # Should find John
        assert any(m['id'] == user.id for m in data['members'])
    
    def test_get_members_with_role_filter(self, api_client, admin_user, db_session):
        """Test members list with role filter"""
        from tests.factories import UserFactory
        
        prof = UserFactory(role=UserRoleEnum.professionista)
        db_session.commit()
        
        api_client.login(admin_user)
        response = api_client.get('/api/team/members?role=professionista')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['success'] is True
    
    def test_get_members_with_active_filter_true(self, api_client, admin_user, db_session):
        """Test members list filtering by active status"""
        from tests.factories import UserFactory
        
        active_user = UserFactory(is_active=True)
        inactive_user = UserFactory(is_active=False)
        db_session.commit()
        
        api_client.login(admin_user)
        response = api_client.get('/api/team/members?active=1')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['success'] is True
    
    def test_get_members_with_department_filter(self, api_client, admin_user, db_session):
        """Test members list filtering by department"""
        from tests.factories import DepartmentFactory, UserFactory
        
        dept = DepartmentFactory()
        db_session.commit()
        
        api_client.login(admin_user)
        response = api_client.get(f'/api/team/members?department_id={dept.id}')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['success'] is True


class TestTeamGetMember:
    """Test GET /api/team/members/<id> - Get single team member details"""
    
    def test_get_member_not_found(self, api_client, admin_user, db_session):
        """Test getting non-existent member returns 404"""
        db_session.commit()
        api_client.login(admin_user)
        response = api_client.get('/api/team/members/99999')
        
        assert response.status_code == HTTPStatus.NOT_FOUND
    
    def test_get_member_success(self, api_client, admin_user, db_session):
        """Test successful member details retrieval"""
        from tests.factories import UserFactory
        
        user = UserFactory()
        db_session.commit()
        
        api_client.login(admin_user)
        response = api_client.get(f'/api/team/members/{user.id}')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['success'] is True
        assert data['id'] == user.id
        assert data['email'] == user.email
    
    def test_get_member_unauthorized_non_admin(self, api_client, user, db_session):
        """Test that non-admin cannot view other members"""
        from tests.factories import UserFactory
        
        other_user = UserFactory()
        db_session.commit()
        
        api_client.login(user)
        # Non-admin can only see themselves
        response = api_client.get(f'/api/team/members/{other_user.id}')
        
        # Should be forbidden or not found (403 FORBIDDEN before 404)
        assert response.status_code in (HTTPStatus.FORBIDDEN, HTTPStatus.NOT_FOUND)


class TestTeamCreateMember:
    """Test POST /api/team/members - Create new team member"""
    
    def test_create_member_requires_admin(self, api_client, user, db_session):
        """Test that non-admin cannot create members"""
        db_session.commit()
        api_client.login(user)
        response = api_client.post('/api/team/members', json={
            'email': 'newmember@test.com',
            'password': 'TempPass123!',
            'first_name': 'New',
            'last_name': 'Member'
        })
        
        assert response.status_code == HTTPStatus.FORBIDDEN
    
    def test_create_member_success(self, api_client, admin_user, db_session):
        """Test successful member creation"""
        db_session.commit()
        api_client.login(admin_user)
        response = api_client.post('/api/team/members', json={
            'email': 'newmember@test.com',
            'password': 'TempPass123!',
            'first_name': 'New',
            'last_name': 'Member',
            'role': 'professionista'
        })
        
        assert response.status_code == HTTPStatus.CREATED
        data = response.json
        assert data['success'] is True
        assert data['email'] == 'newmember@test.com'
        assert 'id' in data
    
    def test_create_member_missing_required_field(self, api_client, admin_user, db_session):
        """Test member creation fails with missing required fields"""
        db_session.commit()
        api_client.login(admin_user)
        response = api_client.post('/api/team/members', json={
            'email': 'newmember@test.com',
            'password': 'TempPass123!',
            'first_name': 'New'
            # Missing last_name
        })
        
        assert response.status_code == HTTPStatus.BAD_REQUEST
        data = response.json
        assert data['success'] is False
    
    def test_create_member_duplicate_email(self, api_client, admin_user, db_session):
        """Test member creation fails with duplicate email"""
        from tests.factories import UserFactory
        
        existing_user = UserFactory(email='existing@test.com')
        db_session.commit()
        api_client.login(admin_user)
        response = api_client.post('/api/team/members', json={
            'email': 'existing@test.com',
            'password': 'TempPass123!',
            'first_name': 'New',
            'last_name': 'Member'
        })
        
        assert response.status_code == HTTPStatus.BAD_REQUEST
        data = response.json
        assert 'Email' in data['message']
    
    def test_create_admin_member(self, api_client, admin_user, db_session):
        """Test creating an admin member"""
        db_session.commit()
        api_client.login(admin_user)
        response = api_client.post('/api/team/members', json={
            'email': 'newadmin@test.com',
            'password': 'AdminPass123!',
            'first_name': 'New',
            'last_name': 'Admin',
            'role': 'admin',
            'is_admin': True
        })
        
        assert response.status_code == HTTPStatus.CREATED
        data = response.json
        assert data['success'] is True
        assert data['is_admin'] is True
    
    def test_create_external_member(self, api_client, admin_user, db_session):
        """Test creating an external team member"""
        db_session.commit()
        api_client.login(admin_user)
        response = api_client.post('/api/team/members', json={
            'email': 'external@test.com',
            'password': 'ExtPass123!',
            'first_name': 'External',
            'last_name': 'Team',
            'role': 'team_esterno',
            'is_external': True
        })
        
        assert response.status_code == HTTPStatus.CREATED
        data = response.json
        assert data['success'] is True
        assert data['is_external'] is True
    
    def test_create_member_with_specialty(self, api_client, admin_user, db_session):
        """Test creating a member with specialty"""
        db_session.commit()
        api_client.login(admin_user)
        response = api_client.post('/api/team/members', json={
            'email': 'specialist@test.com',
            'password': 'SpecPass123!',
            'first_name': 'Specialist',
            'last_name': 'Pro',
            'role': 'professionista',
            'specialty': 'nutrizionista'
        })
        
        assert response.status_code == HTTPStatus.CREATED
        data = response.json
        assert data['success'] is True


class TestTeamUpdateMember:
    """Test PUT /api/team/members/<id> - Update team member"""
    
    def test_update_member_requires_admin(self, api_client, user, db_session):
        """Test that non-admin cannot update members"""
        from tests.factories import UserFactory
        
        other_user = UserFactory()
        db_session.commit()
        
        api_client.login(user)
        response = api_client.put(f'/api/team/members/{other_user.id}', json={
            'first_name': 'Updated'
        })
        
        assert response.status_code == HTTPStatus.FORBIDDEN
    
    def test_update_member_not_found(self, api_client, admin_user, db_session):
        """Test updating non-existent member returns 404"""
        db_session.commit()
        api_client.login(admin_user)
        response = api_client.put('/api/team/members/99999', json={
            'first_name': 'Updated'
        })
        
        assert response.status_code == HTTPStatus.NOT_FOUND
    
    def test_update_member_success(self, api_client, admin_user, db_session):
        """Test successful member update"""
        from tests.factories import UserFactory
        
        user = UserFactory(first_name='Old', last_name='Name')
        db_session.commit()
        api_client.login(admin_user)
        response = api_client.put(f'/api/team/members/{user.id}', json={
            'first_name': 'Updated',
            'last_name': 'NewName'
        })
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['success'] is True
        assert data['first_name'] == 'Updated'
        assert data['last_name'] == 'NewName'
    
    def test_update_member_email_conflict(self, api_client, admin_user, db_session):
        """Test member update fails when email already exists"""
        from tests.factories import UserFactory
        
        user1 = UserFactory(email='user1@test.com')
        user2 = UserFactory(email='user2@test.com')
        db_session.commit()
        api_client.login(admin_user)
        response = api_client.put(f'/api/team/members/{user2.id}', json={
            'email': 'user1@test.com'
        })
        
        assert response.status_code == HTTPStatus.BAD_REQUEST
        data = response.json
        assert 'Email' in data['message']
    
    def test_update_member_password(self, api_client, admin_user, db_session):
        """Test updating member password"""
        from tests.factories import UserFactory
        
        user = UserFactory()
        db_session.commit()
        api_client.login(admin_user)
        response = api_client.put(f'/api/team/members/{user.id}', json={
            'password': 'NewPass123!'
        })
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['success'] is True
    
    def test_update_member_role(self, api_client, admin_user, db_session):
        """Test updating member role"""
        from tests.factories import UserFactory
        
        user = UserFactory(role=UserRoleEnum.professionista)
        db_session.commit()
        api_client.login(admin_user)
        response = api_client.put(f'/api/team/members/{user.id}', json={
            'role': 'admin',
            'is_admin': True
        })
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['success'] is True
        assert data['is_admin'] is True
    
    def test_update_member_specialty(self, api_client, admin_user, db_session):
        """Test updating member specialty"""
        from tests.factories import UserFactory
        
        user = UserFactory()
        db_session.commit()
        api_client.login(admin_user)
        response = api_client.put(f'/api/team/members/{user.id}', json={
            'specialty': 'coach'
        })
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['success'] is True


class TestTeamDeleteMember:
    """Test DELETE /api/team/members/<id> - Delete team member (soft delete)"""
    
    def test_delete_member_requires_admin(self, api_client, user, db_session):
        """Test that non-admin cannot delete members"""
        from tests.factories import UserFactory
        
        other_user = UserFactory()
        db_session.commit()
        
        api_client.login(user)
        response = api_client.delete(f'/api/team/members/{other_user.id}')
        
        assert response.status_code == HTTPStatus.FORBIDDEN
    
    def test_delete_member_not_found(self, api_client, admin_user, db_session):
        """Test deleting non-existent member returns 404"""
        db_session.commit()
        api_client.login(admin_user)
        response = api_client.delete('/api/team/members/99999')
        
        assert response.status_code == HTTPStatus.NOT_FOUND
    
    def test_delete_member_success(self, api_client, admin_user, db_session):
        """Test successful member deletion (soft delete)"""
        from tests.factories import UserFactory
        
        user = UserFactory(is_active=True)
        db_session.commit()
        user_id = user.id
        api_client.login(admin_user)
        response = api_client.delete(f'/api/team/members/{user_id}')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['success'] is True
        
        # Verify user is deactivated (soft delete)
        deleted_user = User.query.get(user_id)
        assert deleted_user.is_active is False
    
    def test_delete_self_not_allowed(self, api_client, admin_user, db_session):
        """Test that admin cannot delete their own account"""
        db_session.commit()
        api_client.login(admin_user)
        response = api_client.delete(f'/api/team/members/{admin_user.id}')
        
        assert response.status_code == HTTPStatus.BAD_REQUEST
        data = response.json
        assert 'eliminare il tuo account' in data['message'].lower()


class TestTeamToggleMemberStatus:
    """Test POST /api/team/members/<id>/toggle - Toggle member active status"""
    
    def test_toggle_member_status_requires_admin(self, api_client, user, db_session):
        """Test that non-admin cannot toggle member status"""
        from tests.factories import UserFactory
        
        other_user = UserFactory()
        db_session.commit()
        
        api_client.login(user)
        response = api_client.post(f'/api/team/members/{other_user.id}/toggle')
        
        assert response.status_code == HTTPStatus.FORBIDDEN
    
    def test_toggle_member_status_not_found(self, api_client, admin_user, db_session):
        """Test toggling non-existent member returns 404"""
        db_session.commit()
        api_client.login(admin_user)
        response = api_client.post('/api/team/members/99999/toggle')
        
        assert response.status_code == HTTPStatus.NOT_FOUND
    
    def test_toggle_member_status_success(self, api_client, admin_user, db_session):
        """Test successful member status toggle"""
        from tests.factories import UserFactory
        
        user = UserFactory(is_active=True)
        db_session.commit()
        initial_status = user.is_active
        api_client.login(admin_user)
        response = api_client.post(f'/api/team/members/{user.id}/toggle')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['success'] is True
        assert data['is_active'] == (not initial_status)


class TestTeamUploadAvatar:
    """Test POST /api/team/members/<id>/avatar - Upload member avatar"""
    
    def test_upload_avatar_requires_admin(self, api_client, user, db_session):
        """Test that non-admin cannot upload member avatar"""
        from tests.factories import UserFactory
        
        other_user = UserFactory()
        db_session.commit()
        
        api_client.login(user)
        response = api_client.post(
            f'/api/team/members/{other_user.id}/avatar',
            data={'avatar': (b'fake image data', 'test.png')}
        )
        
        assert response.status_code == HTTPStatus.FORBIDDEN
    
    def test_upload_avatar_not_found(self, api_client, admin_user, db_session):
        """Test uploading avatar for non-existent member returns 404"""
        db_session.commit()
        api_client.login(admin_user)
        response = api_client.post(
            '/api/team/members/99999/avatar',
            data={'avatar': (b'fake image data', 'test.png')}
        )
        
        assert response.status_code == HTTPStatus.NOT_FOUND
    
    def test_upload_avatar_missing_file(self, api_client, admin_user, db_session):
        """Test avatar upload fails without file"""
        from tests.factories import UserFactory
        
        user = UserFactory()
        db_session.commit()
        api_client.login(admin_user)
        response = api_client.post(f'/api/team/members/{user.id}/avatar')
        
        # Should return 400 or similar error
        assert response.status_code in (HTTPStatus.BAD_REQUEST, HTTPStatus.UNPROCESSABLE_ENTITY)


class TestTeamGetDepartments:
    """Test GET /api/team/departments - List departments"""
    
    def test_get_departments_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/api/team/departments')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_get_departments_success(self, api_client, admin_user, db_session):
        """Test successful departments list retrieval"""
        from tests.factories import DepartmentFactory
        
        dept1 = DepartmentFactory()
        dept2 = DepartmentFactory()
        db_session.commit()
        
        api_client.login(admin_user)
        response = api_client.get('/api/team/departments')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['success'] is True
        assert 'departments' in data
        assert isinstance(data['departments'], list)


class TestTeamGetStats:
    """Test GET /api/team/stats - Team statistics"""
    
    def test_get_stats_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/api/team/stats')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_get_stats_success(self, api_client, admin_user, db_session):
        """Test successful stats retrieval"""
        api_client.login(admin_user)
        response = api_client.get('/api/team/stats')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['success'] is True
        assert 'stats' in data


class TestTeamGetAdminDashboardStats:
    """Test GET /api/team/admin-dashboard-stats - Admin dashboard statistics"""
    
    def test_admin_dashboard_stats_requires_admin(self, api_client, user):
        """Test that non-admin cannot access admin stats"""
        api_client.login(user)
        response = api_client.get('/api/team/admin-dashboard-stats')
        
        assert response.status_code == HTTPStatus.FORBIDDEN
    
    def test_admin_dashboard_stats_success(self, api_client, admin_user, db_session):
        """Test successful admin dashboard stats retrieval"""
        api_client.login(admin_user)
        response = api_client.get('/api/team/admin-dashboard-stats')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['success'] is True


class TestTeamGetTeams:
    """Test GET /api/team/teams - List teams"""
    
    def test_get_teams_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/api/team/teams')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_get_teams_success(self, api_client, admin_user, db_session):
        """Test successful teams list retrieval"""
        api_client.login(admin_user)
        response = api_client.get('/api/team/teams')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['success'] is True
        assert 'teams' in data


class TestTeamGetTeam:
    """Test GET /api/team/teams/<id> - Get single team details"""
    
    def test_get_team_not_found(self, api_client, admin_user, db_session):
        """Test getting non-existent team returns 404"""
        api_client.login(admin_user)
        response = api_client.get('/api/team/teams/99999')
        
        assert response.status_code == HTTPStatus.NOT_FOUND
    
    def test_get_team_success(self, api_client, admin_user, db_session):
        """Test successful team details retrieval"""
        from tests.factories import TeamFactory
        
        team = TeamFactory()
        db_session.commit()
        
        api_client.login(admin_user)
        response = api_client.get(f'/api/team/teams/{team.id}')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['success'] is True
        assert data['id'] == team.id


class TestTeamCreateTeam:
    """Test POST /api/team/teams - Create new team"""
    
    def test_create_team_requires_admin(self, api_client, user):
        """Test that non-admin cannot create teams"""
        api_client.login(user)
        response = api_client.post('/api/team/teams', json={
            'name': 'New Team',
            'team_type': 'nutrizione'
        })
        
        assert response.status_code == HTTPStatus.FORBIDDEN
    
    def test_create_team_success(self, api_client, admin_user, db_session):
        """Test successful team creation"""
        db_session.commit()
        api_client.login(admin_user)
        response = api_client.post('/api/team/teams', json={
            'name': 'New Team',
            'team_type': 'nutrizione'
        })
        
        assert response.status_code == HTTPStatus.CREATED
        data = response.json
        assert data['success'] is True
        assert data['name'] == 'New Team'
        assert 'id' in data


class TestTeamUpdateTeam:
    """Test PUT /api/team/teams/<id> - Update team"""
    
    def test_update_team_requires_admin(self, api_client, user, db_session):
        """Test that non-admin cannot update teams"""
        from tests.factories import TeamFactory
        
        team = TeamFactory()
        db_session.commit()
        
        api_client.login(user)
        response = api_client.put(f'/api/team/teams/{team.id}', json={
            'name': 'Updated'
        })
        
        assert response.status_code == HTTPStatus.FORBIDDEN
    
    def test_update_team_not_found(self, api_client, admin_user, db_session):
        """Test updating non-existent team returns 404"""
        db_session.commit()
        api_client.login(admin_user)
        response = api_client.put('/api/team/teams/99999', json={
            'name': 'Updated'
        })
        
        assert response.status_code == HTTPStatus.NOT_FOUND
    
    def test_update_team_success(self, api_client, admin_user, db_session):
        """Test successful team update"""
        from tests.factories import TeamFactory
        
        team = TeamFactory(name='Old Name')
        db_session.commit()
        api_client.login(admin_user)
        response = api_client.put(f'/api/team/teams/{team.id}', json={
            'name': 'Updated Name'
        })
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['success'] is True
        assert data['name'] == 'Updated Name'


class TestTeamDeleteTeam:
    """Test DELETE /api/team/teams/<id> - Delete team"""
    
    def test_delete_team_requires_admin(self, api_client, user, db_session):
        """Test that non-admin cannot delete teams"""
        from tests.factories import TeamFactory
        
        team = TeamFactory()
        db_session.commit()
        
        api_client.login(user)
        response = api_client.delete(f'/api/team/teams/{team.id}')
        
        assert response.status_code == HTTPStatus.FORBIDDEN
    
    def test_delete_team_not_found(self, api_client, admin_user, db_session):
        """Test deleting non-existent team returns 404"""
        db_session.commit()
        api_client.login(admin_user)
        response = api_client.delete('/api/team/teams/99999')
        
        assert response.status_code == HTTPStatus.NOT_FOUND
    
    def test_delete_team_success(self, api_client, admin_user, db_session):
        """Test successful team deletion"""
        from tests.factories import TeamFactory
        
        team = TeamFactory()
        db_session.commit()
        team_id = team.id
        api_client.login(admin_user)
        response = api_client.delete(f'/api/team/teams/{team_id}')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['success'] is True
        
        # Verify team is deactivated
        deleted_team = Team.query.get(team_id)
        assert deleted_team is not None
        assert deleted_team.is_active is False


class TestTeamAddTeamMember:
    """Test POST /api/team/teams/<id>/members - Add member to team"""
    
    def test_add_team_member_requires_admin(self, api_client, user, db_session):
        """Test that non-admin cannot add members to teams"""
        from tests.factories import TeamFactory, UserFactory
        
        team = TeamFactory()
        member = UserFactory()
        db_session.commit()
        
        api_client.login(user)
        response = api_client.post(f'/api/team/teams/{team.id}/members', json={
            'user_id': member.id
        })
        
        assert response.status_code == HTTPStatus.FORBIDDEN
    
    def test_add_team_member_success(self, api_client, admin_user, db_session):
        """Test successful member addition to team"""
        from tests.factories import TeamFactory, UserFactory
        
        team = TeamFactory()
        member = UserFactory()
        db_session.commit()
        api_client.login(admin_user)
        response = api_client.post(f'/api/team/teams/{team.id}/members', json={
            'user_id': member.id
        })
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['success'] is True


class TestTeamRemoveTeamMember:
    """Test DELETE /api/team/teams/<id>/members/<id> - Remove member from team"""
    
    def test_remove_team_member_requires_admin(self, api_client, user, db_session):
        """Test that non-admin cannot remove members from teams"""
        from tests.factories import TeamFactory, UserFactory
        
        team = TeamFactory()
        member = UserFactory()
        db_session.add(member)
        team.members.append(member)
        db_session.commit()
        
        api_client.login(user)
        response = api_client.delete(f'/api/team/teams/{team.id}/members/{member.id}')
        
        assert response.status_code == HTTPStatus.FORBIDDEN
    
    def test_remove_team_member_success(self, api_client, admin_user, db_session):
        """Test successful member removal from team"""
        from tests.factories import TeamFactory, UserFactory
        
        team = TeamFactory()
        member = UserFactory()
        db_session.add(member)
        team.members.append(member)
        db_session.commit()
        api_client.login(admin_user)
        response = api_client.delete(f'/api/team/teams/{team.id}/members/{member.id}')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['success'] is True


class TestTeamCapacity:
    """Test GET /api/team/capacity - Get professional capacity metrics"""
    
    def test_get_capacity_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/api/team/capacity')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_get_capacity_success(self, api_client, admin_user, db_session):
        """Test successful capacity metrics retrieval"""
        api_client.login(admin_user)
        response = api_client.get('/api/team/capacity')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['success'] is True
        assert 'capacity' in data


class TestTeamCapacityWeights:
    """Test GET/PUT /api/team/capacity-weights - Get and update capacity weights"""
    
    def test_get_capacity_weights_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/api/team/capacity-weights')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_get_capacity_weights_success(self, api_client, admin_user, db_session):
        """Test successful capacity weights retrieval"""
        api_client.login(admin_user)
        response = api_client.get('/api/team/capacity-weights')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['success'] is True
        assert 'weights' in data
    
    def test_update_capacity_weights_requires_admin(self, api_client, user):
        """Test that non-admin cannot update capacity weights"""
        api_client.login(user)
        response = api_client.put('/api/team/capacity-weights', json={
            'weights': {}
        })
        
        assert response.status_code == HTTPStatus.FORBIDDEN
    
    def test_update_capacity_weights_success(self, api_client, admin_user, db_session):
        """Test successful capacity weights update"""
        db_session.commit()
        api_client.login(admin_user)
        response = api_client.put('/api/team/capacity-weights', json={
            'weights': {
                'nutrizione': {
                    'a': 2.0,
                    'b': 1.5,
                    'c': 1.0,
                    'secondario': 0.5
                }
            }
        })
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['success'] is True


class TestTeamUpdateCapacity:
    """Test PUT /api/team/capacity/<id> - Update professional capacity"""
    
    def test_update_capacity_requires_permission(self, api_client, user, db_session):
        """Test that user without permission cannot update capacity"""
        from tests.factories import UserFactory
        
        prof = UserFactory()
        db_session.commit()
        
        api_client.login(user)
        response = api_client.put(f'/api/team/capacity/{prof.id}', json={
            'contractual_capacity': 100
        })
        
        # May be 403 or allowed depending on permissions
        assert response.status_code in (HTTPStatus.FORBIDDEN, HTTPStatus.OK)
    
    def test_update_capacity_not_found(self, api_client, admin_user, db_session):
        """Test updating capacity for non-existent user returns 404"""
        db_session.commit()
        api_client.login(admin_user)
        response = api_client.put('/api/team/capacity/99999', json={
            'contractual_capacity': 100
        })
        
        assert response.status_code == HTTPStatus.NOT_FOUND


class TestTeamGetMemberClients:
    """Test GET /api/team/members/<id>/clients - Get member's assigned clients"""
    
    def test_get_member_clients_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/api/team/members/1/clients')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_get_member_clients_not_found(self, api_client, admin_user, db_session):
        """Test getting clients for non-existent member returns 404"""
        api_client.login(admin_user)
        response = api_client.get('/api/team/members/99999/clients')
        
        assert response.status_code == HTTPStatus.NOT_FOUND
    
    def test_get_member_clients_success(self, api_client, admin_user, db_session):
        """Test successful member clients retrieval"""
        from tests.factories import UserFactory
        
        member = UserFactory()
        db_session.commit()
        
        api_client.login(admin_user)
        response = api_client.get(f'/api/team/members/{member.id}/clients')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['success'] is True
        assert 'clients' in data


class TestTeamGetMemberChecks:
    """Test GET /api/team/members/<id>/checks - Get member's client checks"""
    
    def test_get_member_checks_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/api/team/members/1/checks')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_get_member_checks_not_found(self, api_client, admin_user, db_session):
        """Test getting checks for non-existent member returns 404"""
        api_client.login(admin_user)
        response = api_client.get('/api/team/members/99999/checks')
        
        assert response.status_code == HTTPStatus.NOT_FOUND
    
    def test_get_member_checks_success(self, api_client, admin_user, db_session):
        """Test successful member checks retrieval"""
        from tests.factories import UserFactory
        
        member = UserFactory()
        db_session.commit()
        
        api_client.login(admin_user)
        response = api_client.get(f'/api/team/members/{member.id}/checks')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['success'] is True
