"""
Test mirato per ITS-20260416-0012: Team Leader deve poter accedere alla formazione
dal profilo di un professionista nel proprio team.

Verifica che:
1. can_view_member_reviews() restituisca True per Team Leader verso membri del proprio team
2. can_write_review() restituisca True per Team Leader verso membri del proprio team
3. Le API /api/admin/trainings/<user_id> non diano 500 (AttributeError su department/department_id)
"""
import pytest


class TestTeamLeaderFormazioneAccess:
    """
    Test di integrazione per il ticket ITS-20260416-0012.
    Simula lo scenario: Team Leader accede a formazione dal profilo professionista.
    """

    def test_can_view_member_reviews_team_leader_vs_member(self, app):
        """Team Leader deve poter vedere le review dei membri del proprio team."""
        with app.app_context():
            from corposostenibile.blueprints.review.routes import can_view_member_reviews
            from corposostenibile.models import User, Team
            from corposostenibile.extensions import db

            # Trova un team con almeno 2 membri dove uno è team leader
            # Scenario: team_leader -> team member
            team_with_leader = None
            team_leader_user = None
            team_member_user = None

            # Cerca utenti che sono team leader
            all_users = User.query.all()
            for u in all_users:
                if getattr(u, 'teams_led', None) and len(u.teams_led) > 0:
                    team_leader_user = u
                    team = u.teams_led[0]
                    team_with_leader = team
                    # Prendi un membro del team diverso dal leader
                    if getattr(team, 'members', None) and len(team.members) > 1:
                        for m in team.members:
                            if m.id != team_leader_user.id:
                                team_member_user = m
                                break
                    break

            if team_leader_user is None:
                pytest.skip("Nessun Team Leader con team trovato nel DB")

            if team_member_user is None:
                pytest.skip(f"Team Leader {team_leader_user.id} ha team senza altri membri")

            print(f"\n[Test] Team Leader: {team_leader_user.id} ({team_leader_user.first_name})")
            print(f"[Test] Team Member: {team_member_user.id} ({team_member_user.first_name})")
            print(f"[Test] Team: {getattr(team_with_leader, 'name', 'N/A')}")

            # TEST PRINCIPALE: Team Leader vede review del membro
            result = can_view_member_reviews(team_leader_user, team_member_user)
            print(f"[Test] can_view_member_reviews({team_leader_user.id}, {team_member_user.id}) = {result}")
            assert result is True, f"Team Leader {team_leader_user.id} deve poter vedere review del membro {team_member_user.id}"

    def test_can_write_review_team_leader_vs_member(self, app):
        """Team Leader deve poter scrivere review ai membri del proprio team."""
        with app.app_context():
            from corposostenibile.blueprints.review.routes import can_write_review
            from corposostenibile.models import User

            team_leader_user = None
            team_member_user = None

            all_users = User.query.all()
            for u in all_users:
                if getattr(u, 'teams_led', None) and len(u.teams_led) > 0:
                    team_leader_user = u
                    team = u.teams_led[0]
                    if getattr(team, 'members', None) and len(team.members) > 1:
                        for m in team.members:
                            if m.id != team_leader_user.id:
                                team_member_user = m
                                break
                    break

            if team_leader_user is None or team_member_user is None:
                pytest.skip("Nessun Team Leader con team e membri trovato nel DB")

            # TEST PRINCIPALE: Team Leader scrive review al membro
            result = can_write_review(team_leader_user, team_member_user)
            print(f"\n[Test] can_write_review({team_leader_user.id}, {team_member_user.id}) = {result}")
            assert result is True, f"Team Leader {team_leader_user.id} deve poter scrivere review al membro {team_member_user.id}"

    def test_no_attribute_error_on_member_without_department(self, app):
        """
        Verifica che NON ci sia AttributeError quando un membro non ha department_id.
        Questo era il bug causato da accesso diretto a member.department / member.department_id.
        """
        with app.app_context():
            from corposostenibile.blueprints.review.routes import can_view_member_reviews, can_write_review
            from corposostenibile.models import User

            team_leader_user = None
            member_without_dept = None

            all_users = User.query.all()
            for u in all_users:
                if getattr(u, 'teams_led', None) and len(u.teams_led) > 0:
                    team_leader_user = u
                    team = u.teams_led[0]
                    if getattr(team, 'members', None):
                        for m in team.members:
                            if m.id != team_leader_user.id:
                                member_without_dept = m
                                break
                    break

            if team_leader_user is None or member_without_dept is None:
                pytest.skip("Nessun Team Leader con team e membri trovato nel DB")

            dept_id = getattr(member_without_dept, 'department_id', None)
            dept = getattr(member_without_dept, 'department', None)
            print(f"\n[Test] Membro {member_without_dept.id}: department_id={dept_id}, department={dept}")

            # Non deve dare AttributeError anche se department_id / department sono None/missing
            try:
                view_result = can_view_member_reviews(team_leader_user, member_without_dept)
                print(f"[Test] can_view OK: {view_result}")
            except AttributeError as e:
                pytest.fail(f"AttributeError in can_view_member_reviews: {e}")

            try:
                write_result = can_write_review(team_leader_user, member_without_dept)
                print(f"[Test] can_write OK: {write_result}")
            except AttributeError as e:
                pytest.fail(f"AttributeError in can_write_review: {e}")

    def test_api_admin_user_trainings_no_500(self, app, client):
        """Verifica che GET /review/api/admin/trainings/<user_id> non dia 500 per Team Leader."""
        with app.app_context():
            from corposostenibile.models import User
            from corposostenibile.extensions import db

            team_leader_user = None
            team_member_user = None

            all_users = User.query.all()
            for u in all_users:
                if getattr(u, 'teams_led', None) and len(u.teams_led) > 0:
                    team_leader_user = u
                    team = u.teams_led[0]
                    if getattr(team, 'members', None) and len(team.members) > 1:
                        for m in team.members:
                            if m.id != team_leader_user.id:
                                team_member_user = m
                                break
                    break

            if team_leader_user is None or team_member_user is None:
                pytest.skip("Nessun Team Leader con team e membri trovato nel DB")

            # Login come team leader
            with client.session_transaction() as sess:
                sess['_user_id'] = str(team_leader_user.id)

            # Chiama l'API - non deve dare 500
            response = client.get(f'/review/api/admin/trainings/{team_member_user.id}')
            print(f"\n[Test] GET /review/api/admin/trainings/{team_member_user.id} -> {response.status_code}")

            # Accettiamo 200 (autorizzato) o 403 (non autorizzato per quello specifico membro)
            # Ma NON 500 (errore interno)
            assert response.status_code != 500, f"API ha restituito 500 Internal Server Error: {response.data}"
