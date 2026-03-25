"""
API Tests per il blueprint Quality (React API).
Testa gli endpoint JSON che il frontend React chiama per la gestione della qualità.

Endpoints testati:
- GET /api/quality/weekly-scores - Get weekly quality scores for professionals
- GET /api/quality/professionista/<id>/trend - Get trend data for a professional
- GET /api/quality/dashboard/stats - Get dashboard statistics
- POST /api/quality/calculate - Calculate quality scores for a specialty
- POST /api/quality/calcola/<dept_key> - Calculate quality for department
- GET /api/quality/clienti-eleggibili/<prof_id> - Get eligible clients
- GET /api/quality/check-responses/<prof_id> - Get check responses
- POST /api/quality/calcola-trimestrale - Calculate quarterly scores
- GET /api/quality/quarterly-summary - Get quarterly summary
- GET /api/quality/professionista/<id>/kpi-breakdown - Get KPI breakdown
"""

from http import HTTPStatus
import pytest
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock
from corposostenibile.extensions import db
from corposostenibile.models import (
    User, UserRoleEnum, UserSpecialtyEnum,
    Cliente, Team, TeamTypeEnum,
    QualityWeeklyScore, EleggibilitaSettimanale,
)


class TestQualityWeeklyScores:
    """Test GET /api/quality/weekly-scores - Get weekly quality scores"""
    
    def test_weekly_scores_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/quality/api/weekly-scores')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_weekly_scores_access_denied_for_regular_user(self, api_client, login_test_user, db_session):
        """Test that regular users cannot access quality scores"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/quality/api/weekly-scores?specialty=nutrizione')
        assert response.status_code == HTTPStatus.FORBIDDEN
    
    def test_weekly_scores_admin_access(self, api_client, admin_login_test_user, db_session):
        """Test that admin can access quality scores"""
        db_session.commit()
        api_client.login(admin_login_test_user)
        
        response = api_client.get('/quality/api/weekly-scores?specialty=nutrizione')
        
        # Should succeed (200) or return no data (200 with empty list)
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data.get('success') is True
        assert 'professionals' in data
        assert isinstance(data['professionals'], list)
        assert 'stats' in data
    
    def test_weekly_scores_cco_user_access(self, api_client, db_session):
        """Test that CCO users can access quality scores"""
        from tests.factories import UserFactory
        
        # Create a CCO user (specialty='cco')
        cco_user = UserFactory(
            email='cco@test.com',
            is_admin=False,
            specialty=UserSpecialtyEnum.cco
        )
        db_session.add(cco_user)
        db_session.commit()
        
        api_client.login(cco_user)
        response = api_client.get('/quality/api/weekly-scores?specialty=nutrizione')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data.get('success') is True
    
    def test_weekly_scores_default_specialty(self, api_client, admin_login_test_user, db_session):
        """Test weekly scores with default specialty"""
        db_session.commit()
        api_client.login(admin_login_test_user)
        
        # No specialty param - should default to 'nutrizione'
        response = api_client.get('/quality/api/weekly-scores')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data['specialty'] == 'nutrizione'
    
    def test_weekly_scores_specialty_param(self, api_client, admin_login_test_user, db_session):
        """Test weekly scores with different specialties"""
        db_session.commit()
        api_client.login(admin_login_test_user)
        
        for specialty in ['nutrizione', 'coach', 'psicologia']:
            response = api_client.get(f'/quality/api/weekly-scores?specialty={specialty}')
            
            assert response.status_code == HTTPStatus.OK
            data = response.json
            assert data['specialty'] == specialty
    
    def test_weekly_scores_invalid_specialty(self, api_client, admin_login_test_user, db_session):
        """Test weekly scores with invalid specialty"""
        db_session.commit()
        api_client.login(admin_login_test_user)
        
        response = api_client.get('/quality/api/weekly-scores?specialty=invalid')
        
        assert response.status_code == HTTPStatus.BAD_REQUEST
    
    def test_weekly_scores_with_week_param(self, api_client, admin_login_test_user, db_session):
        """Test weekly scores with custom week parameter"""
        db_session.commit()
        api_client.login(admin_login_test_user)
        
        week_date = (date.today() - timedelta(days=7)).strftime('%Y-%m-%d')
        response = api_client.get(f'/quality/api/weekly-scores?specialty=nutrizione&week={week_date}')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert 'week_start' in data
        assert 'week_end' in data
    
    def test_weekly_scores_with_team_filter(self, api_client, admin_login_test_user, db_session):
        """Test weekly scores filtered by team"""
        from tests.factories import TeamFactory
        
        team = TeamFactory(team_type=TeamTypeEnum.nutrizione)
        db_session.commit()
        
        api_client.login(admin_login_test_user)
        response = api_client.get(f'/quality/api/weekly-scores?specialty=nutrizione&team_id={team.id}')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data.get('success') is True
    
    def test_weekly_scores_response_structure(self, api_client, admin_login_test_user, db_session):
        """Test response structure contains required fields"""
        db_session.commit()
        api_client.login(admin_login_test_user)
        
        response = api_client.get('/quality/api/weekly-scores?specialty=nutrizione')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        
        # Verify structure
        assert 'success' in data
        assert 'week_start' in data
        assert 'week_end' in data
        assert 'specialty' in data
        assert 'professionals' in data
        assert 'stats' in data
        
        # Verify stats structure
        stats = data['stats']
        assert 'total_professionisti' in stats
        assert 'with_score' in stats
        assert 'total_eligible' in stats
        assert 'total_checks' in stats
        assert 'avg_quality' in stats
        assert 'avg_miss_rate' in stats


class TestQualityProfessionistaTrend:
    """Test GET /api/quality/professionista/<id>/trend - Get trend data"""
    
    def test_trend_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/quality/api/professionista/1/trend')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_trend_requires_admin(self, api_client, login_test_user, db_session):
        """Test that regular users cannot access trend data"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/quality/api/professionista/1/trend')
        assert response.status_code == HTTPStatus.FORBIDDEN
    
    def test_trend_admin_access(self, api_client, admin_login_test_user, db_session):
        """Test that admin can access trend data"""
        from tests.factories import UserFactory
        
        prof = UserFactory(specialty=UserSpecialtyEnum.nutrizione)
        db_session.commit()
        
        api_client.login(admin_login_test_user)
        response = api_client.get(f'/quality/api/professionista/{prof.id}/trend')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert 'labels' in data
        assert 'quality_final' in data
        assert 'quality_month' in data
        assert 'quality_trim' in data
        assert 'miss_rate' in data
    
    def test_trend_invalid_user(self, api_client, admin_login_test_user, db_session):
        """Test trend for non-existent user"""
        db_session.commit()
        api_client.login(admin_login_test_user)
        
        response = api_client.get('/quality/api/professionista/99999/trend')
        
        # Should return empty data, not error
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert isinstance(data['labels'], list)


class TestQualityDashboardStats:
    """Test GET /api/quality/dashboard/stats - Get dashboard statistics"""
    
    def test_dashboard_stats_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/quality/api/dashboard/stats')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_dashboard_stats_requires_admin(self, api_client, login_test_user, db_session):
        """Test that regular users cannot access dashboard stats"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/quality/api/dashboard/stats')
        assert response.status_code == HTTPStatus.FORBIDDEN
    
    def test_dashboard_stats_admin_access(self, api_client, admin_login_test_user, db_session):
        """Test that admin can access dashboard stats"""
        db_session.commit()
        api_client.login(admin_login_test_user)
        
        response = api_client.get('/quality/api/dashboard/stats')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert 'total_professionisti' in data
        assert 'bands_distribution' in data
        assert 'avg_quality' in data
    
    def test_dashboard_stats_bands_distribution(self, api_client, admin_login_test_user, db_session):
        """Test that bands distribution has expected bands"""
        db_session.commit()
        api_client.login(admin_login_test_user)
        
        response = api_client.get('/quality/api/dashboard/stats')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        bands = data['bands_distribution']
        
        # Check expected band keys
        for band in ['100%', '60%', '30%', '0%']:
            assert band in bands
            assert isinstance(bands[band], int)


class TestQualityCalculate:
    """Test POST /api/quality/calculate - Calculate quality scores"""
    
    def test_calculate_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.post('/quality/api/calculate', json={
            'specialty': 'nutrizione',
            'week': date.today().strftime('%Y-%m-%d')
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_calculate_requires_admin(self, api_client, login_test_user, db_session):
        """Test that regular users cannot calculate quality"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.post('/quality/api/calculate', json={
            'specialty': 'nutrizione',
            'week': date.today().strftime('%Y-%m-%d')
        })
        assert response.status_code == HTTPStatus.FORBIDDEN
    
    def test_calculate_missing_week_param(self, api_client, admin_login_test_user, db_session):
        """Test calculate without required week parameter"""
        db_session.commit()
        api_client.login(admin_login_test_user)
        
        response = api_client.post('/quality/api/calculate', json={
            'specialty': 'nutrizione'
        })
        assert response.status_code == HTTPStatus.BAD_REQUEST
    
    def test_calculate_invalid_week_format(self, api_client, admin_login_test_user, db_session):
        """Test calculate with invalid week format"""
        db_session.commit()
        api_client.login(admin_login_test_user)
        
        response = api_client.post('/quality/api/calculate', json={
            'specialty': 'nutrizione',
            'week': 'invalid-date'
        })
        assert response.status_code == HTTPStatus.BAD_REQUEST
    
    def test_calculate_invalid_specialty(self, api_client, admin_login_test_user, db_session):
        """Test calculate with invalid specialty"""
        db_session.commit()
        api_client.login(admin_login_test_user)
        
        response = api_client.post('/quality/api/calculate', json={
            'specialty': 'invalid',
            'week': date.today().strftime('%Y-%m-%d')
        })
        assert response.status_code == HTTPStatus.BAD_REQUEST
    
    def test_calculate_success_empty_data(self, api_client, admin_login_test_user, db_session):
        """Test successful calculation with no professionals"""
        db_session.commit()
        api_client.login(admin_login_test_user)
        
        response = api_client.post('/quality/api/calculate', json={
            'specialty': 'nutrizione',
            'week': date.today().strftime('%Y-%m-%d')
        })
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data.get('success') is True
        assert 'processed' in data
        assert 'scores' in data
        assert isinstance(data['scores'], list)
    
    def test_calculate_response_structure(self, api_client, admin_login_test_user, db_session):
        """Test calculate response structure"""
        db_session.commit()
        api_client.login(admin_login_test_user)
        
        response = api_client.post('/quality/api/calculate', json={
            'specialty': 'coach',
            'week': date.today().strftime('%Y-%m-%d')
        })
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        
        # Verify structure
        assert 'success' in data
        assert 'total_professionisti' in data
        assert 'processed' in data
        assert 'eligible_total' in data
        assert 'checks_total' in data
        assert 'scores' in data
        assert 'elapsed_seconds' in data
        assert 'check_processing' in data


class TestQualityCalcolaDipartimento:
    """Test POST /api/quality/calcola/<dept_key> - Calculate for department"""
    
    def test_calcola_dipartimento_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.post('/quality/api/calcola/nutrizione', json={})
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_calcola_dipartimento_requires_admin(self, api_client, login_test_user, db_session):
        """Test that regular users cannot calculate"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.post('/quality/api/calcola/nutrizione', json={})
        assert response.status_code == HTTPStatus.FORBIDDEN
    
    def test_calcola_dipartimento_invalid_dept(self, api_client, admin_login_test_user, db_session):
        """Test calculate with invalid department key"""
        db_session.commit()
        api_client.login(admin_login_test_user)
        
        response = api_client.post('/quality/api/calcola/invalid_dept', json={})
        assert response.status_code == HTTPStatus.BAD_REQUEST
    
    def test_calcola_dipartimento_valid_depts(self, api_client, admin_login_test_user, db_session):
        """Test calculate for all valid departments"""
        db_session.commit()
        api_client.login(admin_login_test_user)
        
        for dept in ['nutrizione', 'coach', 'psicologia']:
            response = api_client.post(f'/quality/api/calcola/{dept}', json={})
            
            assert response.status_code == HTTPStatus.OK
            data = response.json
            assert data.get('success') is True
    
    def test_calcola_dipartimento_with_week(self, api_client, admin_login_test_user, db_session):
        """Test calculate with week parameter"""
        db_session.commit()
        api_client.login(admin_login_test_user)
        
        week_date = date.today().strftime('%Y-%m-%d')
        response = api_client.post('/quality/api/calcola/nutrizione', json={
            'week_start': week_date
        })
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data.get('success') is True


class TestQualityClientiEleggibili:
    """Test GET /api/quality/clienti-eleggibili/<prof_id> - Get eligible clients"""
    
    def test_clienti_eleggibili_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/quality/api/clienti-eleggibili/1')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_clienti_eleggibili_requires_admin(self, api_client, login_test_user, db_session):
        """Test that regular users cannot access"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/quality/api/clienti-eleggibili/1')
        assert response.status_code == HTTPStatus.FORBIDDEN
    
    def test_clienti_eleggibili_admin_access(self, api_client, admin_login_test_user, db_session):
        """Test that admin can access eligible clients"""
        from tests.factories import UserFactory
        
        prof = UserFactory(specialty=UserSpecialtyEnum.nutrizione)
        db_session.commit()
        
        api_client.login(admin_login_test_user)
        response = api_client.get(f'/quality/api/clienti-eleggibili/{prof.id}')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data.get('success') is True
        assert 'clienti' in data
        assert isinstance(data['clienti'], list)
    
    def test_clienti_eleggibili_with_week(self, api_client, admin_login_test_user, db_session):
        """Test eligible clients with specific week"""
        from tests.factories import UserFactory
        
        prof = UserFactory(specialty=UserSpecialtyEnum.nutrizione)
        db_session.commit()
        
        api_client.login(admin_login_test_user)
        week_date = date.today().strftime('%Y-%m-%d')
        response = api_client.get(f'/quality/api/clienti-eleggibili/{prof.id}?week={week_date}')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data.get('success') is True


class TestQualityCheckResponses:
    """Test GET /api/quality/check-responses/<prof_id> - Get check responses"""
    
    def test_check_responses_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/quality/api/check-responses/1')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_check_responses_requires_admin(self, api_client, login_test_user, db_session):
        """Test that regular users cannot access"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/quality/api/check-responses/1')
        assert response.status_code == HTTPStatus.FORBIDDEN
    
    def test_check_responses_admin_access(self, api_client, admin_login_test_user, db_session):
        """Test that admin can access check responses"""
        from tests.factories import UserFactory
        
        prof = UserFactory(specialty=UserSpecialtyEnum.nutrizione)
        db_session.commit()
        
        api_client.login(admin_login_test_user)
        response = api_client.get(f'/quality/api/check-responses/{prof.id}')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data.get('success') is True
        assert 'responses' in data
        assert isinstance(data['responses'], list)
    
    def test_check_responses_with_week(self, api_client, admin_login_test_user, db_session):
        """Test check responses with specific week"""
        from tests.factories import UserFactory
        
        prof = UserFactory(specialty=UserSpecialtyEnum.nutrizione)
        db_session.commit()
        
        api_client.login(admin_login_test_user)
        week_date = date.today().strftime('%Y-%m-%d')
        response = api_client.get(f'/quality/api/check-responses/{prof.id}?week={week_date}')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data.get('success') is True


class TestQualityCalcolaTrimestrale:
    """Test POST /api/quality/calcola-trimestrale - Calculate quarterly scores"""
    
    def test_calcola_trimestrale_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.post('/quality/api/calcola-trimestrale', json={})
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_calcola_trimestrale_requires_admin(self, api_client, login_test_user, db_session):
        """Test that regular users cannot calculate"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.post('/quality/api/calcola-trimestrale', json={})
        assert response.status_code == HTTPStatus.FORBIDDEN
    
    def test_calcola_trimestrale_success(self, api_client, admin_login_test_user, db_session):
        """Test successful quarterly calculation"""
        db_session.commit()
        api_client.login(admin_login_test_user)
        
        response = api_client.post('/quality/api/calcola-trimestrale', json={})
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data.get('success') is True
    
    def test_calcola_trimestrale_with_quarter(self, api_client, admin_login_test_user, db_session):
        """Test quarterly calculation with specific quarter"""
        db_session.commit()
        api_client.login(admin_login_test_user)
        
        response = api_client.post('/quality/api/calcola-trimestrale', json={
            'quarter': '2025-Q1'
        })
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data.get('success') is True


class TestQualityQuarterlySummary:
    """Test GET /api/quality/quarterly-summary - Get quarterly summary"""
    
    def test_quarterly_summary_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/quality/api/quarterly-summary')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_quarterly_summary_requires_admin(self, api_client, login_test_user, db_session):
        """Test that regular users cannot access"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/quality/api/quarterly-summary')
        assert response.status_code == HTTPStatus.FORBIDDEN
    
    def test_quarterly_summary_admin_access(self, api_client, admin_login_test_user, db_session):
        """Test that admin can access quarterly summary"""
        db_session.commit()
        api_client.login(admin_login_test_user)
        
        response = api_client.get('/quality/api/quarterly-summary')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data.get('success') is True
        assert 'quarter' in data
        assert 'total_professionisti' in data
        assert 'professionisti_con_malus' in data
        assert 'malus_details' in data
    
    def test_quarterly_summary_with_quarter_param(self, api_client, admin_login_test_user, db_session):
        """Test quarterly summary with specific quarter"""
        db_session.commit()
        api_client.login(admin_login_test_user)
        
        response = api_client.get('/quality/api/quarterly-summary?quarter=2025-Q1')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data.get('success') is True


class TestQualityKPIBreakdown:
    """Test GET /api/quality/professionista/<id>/kpi-breakdown - Get KPI breakdown"""
    
    def test_kpi_breakdown_requires_login(self, api_client):
        """Test that unauthenticated request fails"""
        response = api_client.get('/quality/api/professionista/1/kpi-breakdown')
        assert response.status_code == HTTPStatus.UNAUTHORIZED
    
    def test_kpi_breakdown_requires_admin(self, api_client, login_test_user, db_session):
        """Test that regular users cannot access"""
        db_session.commit()
        api_client.login(login_test_user)
        
        response = api_client.get('/quality/api/professionista/1/kpi-breakdown')
        assert response.status_code == HTTPStatus.FORBIDDEN
    
    def test_kpi_breakdown_user_not_found(self, api_client, admin_login_test_user, db_session):
        """Test KPI breakdown for non-existent user"""
        db_session.commit()
        api_client.login(admin_login_test_user)
        
        response = api_client.get('/quality/api/professionista/99999/kpi-breakdown')
        
        assert response.status_code == HTTPStatus.NOT_FOUND
    
    def test_kpi_breakdown_admin_access(self, api_client, admin_login_test_user, db_session):
        """Test that admin can access KPI breakdown"""
        from tests.factories import UserFactory
        
        prof = UserFactory(specialty=UserSpecialtyEnum.nutrizione)
        db_session.commit()
        
        api_client.login(admin_login_test_user)
        response = api_client.get(f'/quality/api/professionista/{prof.id}/kpi-breakdown')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data.get('success') is True
        assert 'professionista_id' in data
        assert 'quarter' in data
    
    def test_kpi_breakdown_response_structure(self, api_client, admin_login_test_user, db_session):
        """Test KPI breakdown response structure"""
        from tests.factories import UserFactory
        
        prof = UserFactory(specialty=UserSpecialtyEnum.nutrizione)
        db_session.commit()
        
        api_client.login(admin_login_test_user)
        response = api_client.get(f'/quality/api/professionista/{prof.id}/kpi-breakdown')
        
        # When no data: message field present
        # When data exists: KPI fields present
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert 'professionista_name' in data
    
    def test_kpi_breakdown_with_quarter(self, api_client, admin_login_test_user, db_session):
        """Test KPI breakdown with specific quarter"""
        from tests.factories import UserFactory
        
        prof = UserFactory(specialty=UserSpecialtyEnum.nutrizione)
        db_session.commit()
        
        api_client.login(admin_login_test_user)
        response = api_client.get(f'/quality/api/professionista/{prof.id}/kpi-breakdown?quarter=2025-Q1')
        
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data.get('success') is True
