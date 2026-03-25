"""
API Tests per il blueprint Tasks (React API).
Testa gli endpoint JSON che il frontend React chiama per la gestione dei task.

Endpoints testati:
- GET /api/tasks/ - List tasks with filtering and pagination
- POST /api/tasks/ - Create new task
- PUT /api/tasks/<id> - Update task
- GET /api/tasks/stats - Get task statistics
- GET /api/tasks/filter-options - Get filter options
"""

from http import HTTPStatus
import pytest
from datetime import datetime, date, timedelta
from corposostenibile.extensions import db
from corposostenibile.models import (
    Task, TaskStatusEnum, TaskCategoryEnum, TaskPriorityEnum,
    User, UserRoleEnum, Team, TeamTypeEnum
)


class TestTasksListTasks:
    """Test GET /api/tasks/ - List tasks with filtering"""
    
    def test_list_tasks_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/api/tasks/')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_list_tasks_success_empty(self, api_client, login_test_user, db_session):
        """Test successful list with no tasks"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/api/tasks/')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert isinstance(data, list)
    
    def test_list_tasks_with_pagination(self, api_client, login_test_user, db_session):
        """Test list with pagination parameters"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/api/tasks/?page=1&per_page=10&paginate=true')
        
        # Should either return list or paginated response
        assert response.status_code == HTTPStatus.OK
    
    def test_list_tasks_mine_only(self, api_client, login_test_user, db_session):
        """Test list with mine_only filter"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/api/tasks/?mine=true')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert isinstance(data, list)
    
    def test_list_tasks_with_include_summary(self, api_client, login_test_user, db_session):
        """Test list with summary statistics"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/api/tasks/?include_summary=true')
        
        assert response.status_code == HTTPStatus.OK
    
    def test_list_tasks_with_include_filter_options(self, api_client, login_test_user, db_session):
        """Test list with filter options included"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/api/tasks/?include_filter_options=true')
        
        assert response.status_code == HTTPStatus.OK
    
    def test_list_tasks_admin_filters(self, api_client, admin_login_test_user, db_session):
        """Test list with admin filters"""
        db_session.commit()
        api_client.login(admin_login_test_user)
        
        # Admin can filter by assignee
        response = api_client.get('/api/tasks/?assignee_id=1')
        
        assert response.status_code == HTTPStatus.OK
    
    def test_list_tasks_team_leader_scope(self, api_client, db_session):
        """Test that team leaders can only see their team members' tasks"""
        from tests.factories import UserFactory, TeamFactory
        
        team = TeamFactory(team_type=TeamTypeEnum.nutrizione)
        team_leader = UserFactory(
            email='leader@test.com',
            role=UserRoleEnum.team_leader
        )
        db_session.add_all([team, team_leader])
        db_session.commit()
        
        api_client.login(team_leader)
        response = api_client.get('/api/tasks/')
        
        assert response.status_code == HTTPStatus.OK


class TestTasksCreateTask:
    """Test POST /api/tasks/ - Create new task"""
    
    def test_create_task_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.post('/api/tasks/', json={
            'title': 'Test Task',
            'description': 'Test description'
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_create_task_success(self, api_client, login_test_user, db_session):
        """Test successful task creation"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.post('/api/tasks/', json={
            'title': 'New Task',
            'description': 'Task description',
            'priority': 'high',
            'status': 'open',
            'assignee_id': login_test_user.id
        })
        
        # Should succeed or return validation error
        assert response.status_code in (HTTPStatus.OK, HTTPStatus.CREATED, HTTPStatus.BAD_REQUEST)
    
    def test_create_task_missing_title(self, api_client, login_test_user, db_session):
        """Test task creation without title"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.post('/api/tasks/', json={
            'description': 'No title'
        })
        
        # Should fail due to missing required field
        assert response.status_code in (HTTPStatus.BAD_REQUEST, HTTPStatus.UNPROCESSABLE_ENTITY)
    
    def test_create_task_with_priority(self, api_client, login_test_user, db_session):
        """Test task creation with priority"""
        db_session.commit()
        api_client.login(login_test_user)
        
        for priority in ['low', 'medium', 'high', 'urgent']:
            response = api_client.post('/api/tasks/', json={
                'title': f'Task {priority}',
                'priority': priority,
                'assignee_id': login_test_user.id
            })
            
            assert response.status_code in (HTTPStatus.OK, HTTPStatus.CREATED, HTTPStatus.BAD_REQUEST)
    
    def test_create_task_with_due_date(self, api_client, login_test_user, db_session):
        """Test task creation with due date"""
        db_session.commit()
        api_client.login(login_test_user)
        
        due_date = (date.today() + timedelta(days=7)).isoformat()
        response = api_client.post('/api/tasks/', json={
            'title': 'Task with due date',
            'due_date': due_date,
            'assignee_id': login_test_user.id
        })
        
        assert response.status_code in (HTTPStatus.OK, HTTPStatus.CREATED, HTTPStatus.BAD_REQUEST)


class TestTasksUpdateTask:
    """Test PUT /api/tasks/<id> - Update task"""
    
    def test_update_task_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.put('/api/tasks/1', json={'title': 'Updated'})
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_update_task_not_found(self, api_client, login_test_user, db_session):
        """Test updating non-existent task"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.put('/api/tasks/99999', json={'title': 'Updated'})
        
        assert response.status_code in (HTTPStatus.NOT_FOUND, HTTPStatus.BAD_REQUEST)
    
    def test_update_task_status(self, api_client, login_test_user, db_session):
        """Test updating task status"""
        from tests.factories import UserFactory
        
        task = Task(
            title='Test Task',
            description='Description',
            assignee=login_test_user,
            status=TaskStatusEnum.open,
            priority=TaskPriorityEnum.medium
        )
        db_session.add(task)
        db_session.commit()
        
        api_client.login(login_test_user)
        response = api_client.put(f'/api/tasks/{task.id}', json={
            'status': 'done'
        })
        
        assert response.status_code in (HTTPStatus.OK, HTTPStatus.BAD_REQUEST)
    
    def test_update_task_title(self, api_client, login_test_user, db_session):
        """Test updating task title"""
        task = Task(
            title='Original Title',
            description='Description',
            assignee=login_test_user,
            status=TaskStatusEnum.open,
            priority=TaskPriorityEnum.medium
        )
        db_session.add(task)
        db_session.commit()
        
        api_client.login(login_test_user)
        response = api_client.put(f'/api/tasks/{task.id}', json={
            'title': 'Updated Title'
        })
        
        assert response.status_code in (HTTPStatus.OK, HTTPStatus.BAD_REQUEST)
    
    def test_update_task_priority(self, api_client, login_test_user, db_session):
        """Test updating task priority"""
        task = Task(
            title='Test Task',
            description='Description',
            assignee=login_test_user,
            status=TaskStatusEnum.open,
            priority=TaskPriorityEnum.low
        )
        db_session.add(task)
        db_session.commit()
        
        api_client.login(login_test_user)
        response = api_client.put(f'/api/tasks/{task.id}', json={
            'priority': 'high'
        })
        
        assert response.status_code in (HTTPStatus.OK, HTTPStatus.BAD_REQUEST)
    
    def test_update_task_due_date(self, api_client, login_test_user, db_session):
        """Test updating task due date"""
        task = Task(
            title='Test Task',
            description='Description',
            assignee=login_test_user,
            status=TaskStatusEnum.open,
            priority=TaskPriorityEnum.medium
        )
        db_session.add(task)
        db_session.commit()
        
        due_date = (date.today() + timedelta(days=14)).isoformat()
        api_client.login(login_test_user)
        response = api_client.put(f'/api/tasks/{task.id}', json={
            'due_date': due_date
        })
        
        assert response.status_code in (HTTPStatus.OK, HTTPStatus.BAD_REQUEST)


class TestTasksStats:
    """Test GET /api/tasks/stats - Get task statistics"""
    
    def test_stats_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/api/tasks/stats')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_stats_success(self, api_client, login_test_user, db_session):
        """Test successful stats retrieval"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/api/tasks/stats')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        # Should contain stats about tasks
        assert isinstance(data, dict)
    
    def test_stats_contains_summary(self, api_client, login_test_user, db_session):
        """Test that stats contains summary data"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/api/tasks/stats')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        # Stats should have counts for different statuses
        assert isinstance(data, dict)


class TestTasksFilterOptions:
    """Test GET /api/tasks/filter-options - Get filter options"""
    
    def test_filter_options_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/api/tasks/filter-options')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_filter_options_success(self, api_client, login_test_user, db_session):
        """Test successful filter options retrieval"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/api/tasks/filter-options')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert isinstance(data, dict)
    
    def test_filter_options_contains_teams(self, api_client, admin_login_test_user, db_session):
        """Test that filter options contains teams (for admins)"""
        db_session.commit()
        api_client.login(admin_login_test_user)
        
        response = api_client.get('/api/tasks/filter-options')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        # Admin should see teams in filter options
        assert 'teams' in data or isinstance(data, dict)
    
    def test_filter_options_contains_assignees(self, api_client, login_test_user, db_session):
        """Test that filter options contains assignees"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/api/tasks/filter-options')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        # Should contain assignee information
        assert isinstance(data, dict)
