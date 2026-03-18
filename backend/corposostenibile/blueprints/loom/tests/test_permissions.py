from types import SimpleNamespace

from corposostenibile.blueprints.loom.routes import can_view_submitter_id_for_role
from corposostenibile.models import UserRoleEnum


def _user(user_id: int, role: str, is_admin: bool = False):
    return SimpleNamespace(id=user_id, role=role, is_admin=is_admin)


def test_professionista_can_view_only_own_submitter_scope():
    user = _user(10, UserRoleEnum.professionista.value)
    allowed_ids = {10}

    assert can_view_submitter_id_for_role(user, 10, allowed_ids) is True
    assert can_view_submitter_id_for_role(user, 11, allowed_ids) is False


def test_team_leader_can_view_only_team_submitter_scope():
    leader = _user(20, UserRoleEnum.team_leader.value)
    team_scope_ids = {20, 21, 22}

    assert can_view_submitter_id_for_role(leader, 20, team_scope_ids) is True
    assert can_view_submitter_id_for_role(leader, 21, team_scope_ids) is True
    assert can_view_submitter_id_for_role(leader, 99, team_scope_ids) is False


def test_admin_can_view_all_submitters():
    admin = _user(1, UserRoleEnum.admin.value, is_admin=True)

    assert can_view_submitter_id_for_role(admin, 10, None) is True
    assert can_view_submitter_id_for_role(admin, 999, set()) is True


def test_non_admin_with_no_scope_cannot_view():
    user = _user(30, UserRoleEnum.professionista.value, is_admin=False)

    assert can_view_submitter_id_for_role(user, 30, None) is False
