"""Test RBAC: visibilità clienti per professionisti.

Questo file copre il comportamento desiderato dopo il fix:
- nutrizione / coach / psicologia devono vedere solo la propria M2M;
- il medico continua a vedere i clienti tramite history attiva;
- le assegnazioni legacy via FK non devono più far comparire clienti in lista
  per le specialità standard.
"""

from __future__ import annotations

from corposostenibile.blueprints.customers import rbac_scope
from corposostenibile.blueprints.customers.rbac_scope import (
    is_professionista_assigned_to_cliente,
    is_professionista_assigned_to_service,
)


class _FakeUser:
    def __init__(self, user_id: int, specialty: str):
        self.id = user_id
        self.is_admin = False
        self._role = "professionista"
        self._specialty = specialty

    @property
    def role(self):
        class _Role:
            def __init__(self, value):
                self.value = value
        return _Role(self._role)

    @property
    def specialty(self):
        class _Specialty:
            def __init__(self, value):
                self.value = value
        return _Specialty(self._specialty)


class _FakeCliente:
    def __init__(self, cliente_id: int, **kwargs):
        self.cliente_id = cliente_id
        self.nutrizionista_id = kwargs.get("nutrizionista_id")
        self.coach_id = kwargs.get("coach_id")
        self.psicologa_id = kwargs.get("psicologa_id")
        self.consulente_alimentare_id = kwargs.get("consulente_alimentare_id")
        self.nutrizionisti_multipli = kwargs.get("nutrizionisti_multipli", [])
        self.coaches_multipli = kwargs.get("coaches_multipli", [])
        self.psicologi_multipli = kwargs.get("psicologi_multipli", [])
        self.consulenti_multipli = kwargs.get("consulenti_multipli", [])


class _FakeHistoryQuery:
    def __init__(self, matched: bool):
        self._matched = matched

    def filter_by(self, **kwargs):  # noqa: ANN003 - fake query API
        return self

    def first(self):
        return object() if self._matched else None


class _FakeHistoryModel:
    def __init__(self, matched: bool):
        self.query = _FakeHistoryQuery(matched)


def test_nutrizionista_con_m2m_vede_il_paziente():
    user = _FakeUser(50, "nutrizionista")
    cliente = _FakeCliente(27558, nutrizionisti_multipli=[user])

    assert is_professionista_assigned_to_cliente(user, cliente) is True
    assert is_professionista_assigned_to_service(user, cliente, "nutrizione") is True


def test_nutrizionista_con_sola_fk_legacy_non_vede_il_paziente():
    user = _FakeUser(50, "nutrizionista")
    cliente = _FakeCliente(27558, nutrizionista_id=50, nutrizionisti_multipli=[])

    assert is_professionista_assigned_to_cliente(user, cliente) is False
    assert is_professionista_assigned_to_service(user, cliente, "nutrizione") is False


def test_medico_con_history_attiva_vede_il_paziente(monkeypatch):
    user = _FakeUser(70, "medico")
    cliente = _FakeCliente(99999)

    monkeypatch.setattr(
        rbac_scope,
        "ClienteProfessionistaHistory",
        _FakeHistoryModel(True),
    )

    assert is_professionista_assigned_to_cliente(user, cliente) is True
    assert is_professionista_assigned_to_service(user, cliente, "nutrizione") is True


def test_nutrizionista_non_puo_accedere_a_uno_servizio_non_suo():
    user = _FakeUser(50, "nutrizionista")
    cliente = _FakeCliente(27558, coaches_multipli=[])

    assert is_professionista_assigned_to_service(user, cliente, "coaching") is False
