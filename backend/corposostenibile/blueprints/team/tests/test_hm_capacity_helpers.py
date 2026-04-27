from types import SimpleNamespace

from corposostenibile.blueprints.team import api as team_api


def test_compute_hm_capacity_values_with_target() -> None:
    residual, percent = team_api._compute_hm_capacity_values(10, 4)
    assert residual == 6
    assert percent == 40.0


def test_compute_hm_capacity_values_without_target() -> None:
    residual, percent = team_api._compute_hm_capacity_values(None, 7)
    assert residual is None
    assert percent is None


def test_can_manage_hm_capacity_acl(monkeypatch) -> None:
    monkeypatch.setattr(team_api, "_is_cco_user", lambda _u: False)
    monkeypatch.setattr(team_api, "_is_health_manager_team_leader", lambda _u: False)

    admin = SimpleNamespace(is_authenticated=True, is_admin=True)
    assert team_api._can_manage_hm_capacity(admin) is True

    regular = SimpleNamespace(is_authenticated=True, is_admin=False)
    assert team_api._can_manage_hm_capacity(regular) is False

    monkeypatch.setattr(team_api, "_is_cco_user", lambda _u: True)
    cco_user = SimpleNamespace(is_authenticated=True, is_admin=False)
    assert team_api._can_manage_hm_capacity(cco_user) is True

    monkeypatch.setattr(team_api, "_is_cco_user", lambda _u: False)
    monkeypatch.setattr(team_api, "_is_health_manager_team_leader", lambda _u: True)
    hm_tl = SimpleNamespace(is_authenticated=True, is_admin=False)
    assert team_api._can_manage_hm_capacity(hm_tl) is True
