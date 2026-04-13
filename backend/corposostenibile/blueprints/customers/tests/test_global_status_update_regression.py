from __future__ import annotations

from contextlib import nullcontext

from flask import Flask

from corposostenibile.blueprints.customers import services
from corposostenibile.models import StatoClienteEnum


class _FakeSession:
    def flush(self) -> None:
        return None

    def add(self, _obj) -> None:
        return None


class _FakeCliente:
    def __init__(self) -> None:
        self.cliente_id = 999
        self.stato_cliente = StatoClienteEnum.ghost
        self.stato_nutrizione = StatoClienteEnum.ghost
        self.stato_coach = None
        self.stato_psicologia = None
        self.nutrizionista_id = None
        self.coach_id = None
        self.psicologa_id = None
        self.nutrizionista = None
        self.coach = None
        self.psicologa = None
        self.nutrizionisti_multipli = []
        self.coaches_multipli = []
        self.psicologi_multipli = []

    def update_stato_servizio(self, servizio: str, nuovo_stato: str) -> None:
        mapping = {
            "nutrizione": "stato_nutrizione",
            "coach": "stato_coach",
            "psicologia": "stato_psicologia",
        }
        setattr(self, mapping[servizio], nuovo_stato)


def test_manual_global_status_is_not_dropped_when_service_status_keys_are_present(
    monkeypatch,
) -> None:
    """
    Regressione: se nel payload c'è stato_cliente=attivo e sono presenti anche
    chiavi stato_servizio (ma senza variazioni reali), il backend non deve
    scartare lo stato globale manuale.
    """
    app = Flask(__name__)
    cliente = _FakeCliente()

    monkeypatch.setattr(services, "_commit_or_rollback", lambda: nullcontext())
    monkeypatch.setattr(services.db, "session", _FakeSession())
    monkeypatch.setattr(services, "_track_patologie_changes", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(services, "_track_patologie_psico_changes", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(services, "_track_patologie_coach_changes", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(services, "emit_updated", lambda *_args, **_kwargs: None)

    payload = {
        "stato_cliente": "attivo",
        # Campo servizio presente nel payload ma invariato rispetto allo stato corrente.
        "stato_nutrizione": StatoClienteEnum.ghost,
    }

    with app.app_context():
        services.update_cliente(cliente, payload, updated_by_user=None)

    assert cliente.stato_cliente == StatoClienteEnum.attivo


def test_global_becomes_ghost_when_all_assigned_services_are_ghost(monkeypatch) -> None:
    """
    Regola M2M: se tutti i servizi assegnati risultano ghost, lo stato globale
    deve diventare ghost.
    """
    app = Flask(__name__)
    cliente = _FakeCliente()
    cliente.stato_cliente = StatoClienteEnum.attivo
    cliente.stato_nutrizione = StatoClienteEnum.ghost
    cliente.stato_coach = StatoClienteEnum.attivo
    cliente.nutrizionisti_multipli = [object()]
    cliente.coaches_multipli = [object()]

    monkeypatch.setattr(services, "_commit_or_rollback", lambda: nullcontext())
    monkeypatch.setattr(services.db, "session", _FakeSession())
    monkeypatch.setattr(services, "_track_patologie_changes", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(services, "_track_patologie_psico_changes", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(services, "_track_patologie_coach_changes", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(services, "emit_updated", lambda *_args, **_kwargs: None)

    payload = {
        "stato_nutrizione": StatoClienteEnum.ghost,
        "stato_coach": StatoClienteEnum.ghost,
    }

    with app.app_context():
        services.update_cliente(cliente, payload, updated_by_user=None)

    assert cliente.stato_cliente == StatoClienteEnum.ghost


def test_global_returns_attivo_when_one_assigned_service_is_not_ghost(monkeypatch) -> None:
    """
    Regola M2M: se almeno un servizio assegnato non è ghost, lo stato globale
    non deve restare ghost (ritorna attivo).
    """
    app = Flask(__name__)
    cliente = _FakeCliente()
    cliente.stato_cliente = StatoClienteEnum.ghost
    cliente.stato_nutrizione = StatoClienteEnum.ghost
    cliente.stato_coach = StatoClienteEnum.ghost
    cliente.nutrizionisti_multipli = [object()]
    cliente.coaches_multipli = [object()]

    monkeypatch.setattr(services, "_commit_or_rollback", lambda: nullcontext())
    monkeypatch.setattr(services.db, "session", _FakeSession())
    monkeypatch.setattr(services, "_track_patologie_changes", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(services, "_track_patologie_psico_changes", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(services, "_track_patologie_coach_changes", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(services, "emit_updated", lambda *_args, **_kwargs: None)

    payload = {
        "stato_nutrizione": StatoClienteEnum.ghost,
        "stato_coach": StatoClienteEnum.attivo,
    }

    with app.app_context():
        services.update_cliente(cliente, payload, updated_by_user=None)

    assert cliente.stato_cliente == StatoClienteEnum.attivo
