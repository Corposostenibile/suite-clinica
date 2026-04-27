from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

from flask import Flask

from corposostenibile.blueprints.customers import services
from corposostenibile.blueprints.customers.models.activity_log import ActivityLog
from corposostenibile.models import Cliente


class _FakeSession:
    def __init__(self) -> None:
        self.added = []

    def get(self, _model, _id):
        return None

    def add(self, obj) -> None:
        self.added.append(obj)

    def flush(self) -> None:
        # Simula assegnazione PK dopo flush
        for obj in self.added:
            if isinstance(obj, Cliente) and not getattr(obj, "cliente_id", None):
                obj.cliente_id = 12345


def test_select_hm_for_new_client_tie_breaks_by_current_then_id(monkeypatch) -> None:
    hm10 = SimpleNamespace(id=10)
    hm11 = SimpleNamespace(id=11)
    hm9 = SimpleNamespace(id=9)

    monkeypatch.setattr(
        services,
        "_get_hm_capacity_candidates",
        lambda _session: [
            {"user": hm10, "target": 10, "current_assigned": 7, "residual": 3},
            {"user": hm11, "target": 10, "current_assigned": 6, "residual": 3},
            {"user": hm9, "target": 10, "current_assigned": 6, "residual": 3},
        ],
    )

    selected = services.select_hm_for_new_client(object())
    assert selected is hm9


def test_select_hm_for_new_client_returns_none_when_no_positive_residual(monkeypatch) -> None:
    hm1 = SimpleNamespace(id=1)
    hm2 = SimpleNamespace(id=2)

    monkeypatch.setattr(
        services,
        "_get_hm_capacity_candidates",
        lambda _session: [
            {"user": hm1, "target": None, "current_assigned": 0, "residual": None},
            {"user": hm2, "target": 5, "current_assigned": 5, "residual": 0},
        ],
    )

    assert services.select_hm_for_new_client(object()) is None


def test_create_cliente_auto_assigns_hm_and_writes_activity_log(monkeypatch) -> None:
    app = Flask(__name__)
    fake_session = _FakeSession()

    monkeypatch.setattr(services, "_commit_or_rollback", lambda: nullcontext(fake_session))
    monkeypatch.setattr(services, "select_hm_for_new_client", lambda _session: SimpleNamespace(id=77))
    monkeypatch.setattr(services, "_update_stato_cliente_from_services", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(services, "emit_created", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(services, "_enqueue_async", lambda *_args, **_kwargs: None)

    with app.app_context():
        cliente = services.create_cliente({"nome_cognome": "Mario Rossi"}, created_by_user=SimpleNamespace(id=5))

    assert cliente.health_manager_id == 77
    assert any(
        isinstance(obj, ActivityLog)
        and obj.field == "health_manager_id"
        and obj.after == "77"
        and obj.user_id == 5
        for obj in fake_session.added
    )
