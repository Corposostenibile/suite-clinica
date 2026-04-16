"""
Test DIRECT per la logica semplificata stato_cliente derivato dagli stati M2M.

Logica implementata:
- stato_cliente = ATTIVO se ALMENO UN servizio è ATTIVO
- stato_cliente = GHOST se TUTTI i servizi sono GHOST
- stato_cliente = PAUSA se TUTTI i servizi sono PAUSA
"""

from __future__ import annotations

from typing import Optional

import pytest
from flask import Flask

from corposostenibile.blueprints.customers import services
from corposostenibile.models import StatoClienteEnum


class _FakeActivityLog:
    """Mock ActivityLog per catturare i log."""
    instances = []
    
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        _FakeActivityLog.instances.append(kwargs)


class _FakeCliente:
    """Mock Cliente per i test."""

    def __init__(
        self,
        stato_cliente: Optional[StatoClienteEnum] = None,
        stato_nutrizione: Optional[StatoClienteEnum] = None,
        stato_coach: Optional[StatoClienteEnum] = None,
        stato_psicologia: Optional[StatoClienteEnum] = None,
        has_nutrizione: bool = True,
        has_coach: bool = False,
        has_psicologia: bool = False,
    ) -> None:
        self.cliente_id = 999
        self.stato_cliente = stato_cliente
        self.stato_nutrizione = stato_nutrizione
        self.stato_coach = stato_coach
        self.stato_psicologia = stato_psicologia
        self.nutrizionista_id = 1 if has_nutrizione else None
        self.coach_id = 1 if has_coach else None
        self.psicologa_id = 1 if has_psicologia else None
        self.nutrizionisti_multipli = []
        self.coaches_multipli = []
        self.psicologi_multipli = []
        self.nutrizionista = None
        self.coach = None
        self.psicologa = None


@pytest.fixture(autouse=True)
def setup_mocks(monkeypatch):
    """Setup automatico dei mocks per tutti i test."""
    monkeypatch.setattr(services, "_commit_or_rollback", lambda: None)
    monkeypatch.setattr(services.db.session, "add", lambda x: None)
    monkeypatch.setattr(services.db.session, "flush", lambda: None)


@pytest.fixture(autouse=True)
def app_context():
    """Crea un app context per tutti i test."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    with app.app_context():
        yield


def call_update_stato_cliente(
    cliente: _FakeCliente,
    updated_by_user=None
) -> bool:
    """Chiamiamo direttamente la funzione sotto test."""
    return services._update_stato_cliente_from_services(cliente, updated_by_user)


# ============================================================
# CASO 1: ALMENO UN SERVIZIO ATTIVO → stato_cliente = ATTIVO
# ============================================================

def test_un_servizio_attivo_imposta_cliente_attivo(setup_mocks) -> None:
    """Se UN servizio è ATTIVO, stato_cliente deve diventare ATTIVO."""
    cliente = _FakeCliente(
        stato_cliente=None,
        stato_nutrizione=StatoClienteEnum.attivo,
        has_nutrizione=True,
    )
    
    result = call_update_stato_cliente(cliente)
    
    assert result is True
    assert cliente.stato_cliente == StatoClienteEnum.attivo


def test_due_servizi_attivi_imposta_cliente_attivo(setup_mocks) -> None:
    """Se DUE servizi sono ATTIVI, stato_cliente deve essere ATTIVO."""
    cliente = _FakeCliente(
        stato_cliente=None,
        stato_nutrizione=StatoClienteEnum.attivo,
        stato_coach=StatoClienteEnum.attivo,
        has_nutrizione=True,
        has_coach=True,
    )
    
    result = call_update_stato_cliente(cliente)
    
    assert result is True
    assert cliente.stato_cliente == StatoClienteEnum.attivo


def test_tutti_servizi_attivi_imposta_cliente_attivo(setup_mocks) -> None:
    """Se TUTTI i servizi sono ATTIVI, stato_cliente deve essere ATTIVO."""
    cliente = _FakeCliente(
        stato_cliente=None,
        stato_nutrizione=StatoClienteEnum.attivo,
        stato_coach=StatoClienteEnum.attivo,
        stato_psicologia=StatoClienteEnum.attivo,
        has_nutrizione=True,
        has_coach=True,
        has_psicologia=True,
    )
    
    result = call_update_stato_cliente(cliente)
    
    assert result is True
    assert cliente.stato_cliente == StatoClienteEnum.attivo


def test_attivo_giusto_stato_non_cambia(setup_mocks) -> None:
    """Se stato_cliente è già ATTIVO e c'è un servizio attivo, non cambia nulla."""
    cliente = _FakeCliente(
        stato_cliente=StatoClienteEnum.attivo,
        stato_nutrizione=StatoClienteEnum.attivo,
        has_nutrizione=True,
    )
    
    result = call_update_stato_cliente(cliente)
    
    assert result is False
    assert cliente.stato_cliente == StatoClienteEnum.attivo


# ============================================================
# CASO 2: TUTTI I SERVIZI GHOST → stato_cliente = GHOST
# ============================================================

def test_tutti_servizi_ghost_imposta_cliente_ghost(setup_mocks) -> None:
    """Se TUTTI i servizi sono GHOST, stato_cliente deve essere GHOST."""
    cliente = _FakeCliente(
        stato_cliente=StatoClienteEnum.attivo,
        stato_nutrizione=StatoClienteEnum.ghost,
        stato_coach=StatoClienteEnum.ghost,
        has_nutrizione=True,
        has_coach=True,
    )
    
    result = call_update_stato_cliente(cliente)
    
    assert result is True
    assert cliente.stato_cliente == StatoClienteEnum.ghost


def test_tutti_servizi_ghost_unico_servizio(setup_mocks) -> None:
    """Se l'unico servizio è GHOST, stato_cliente deve essere GHOST."""
    cliente = _FakeCliente(
        stato_cliente=StatoClienteEnum.attivo,
        stato_nutrizione=StatoClienteEnum.ghost,
        has_nutrizione=True,
    )
    
    result = call_update_stato_cliente(cliente)
    
    assert result is True
    assert cliente.stato_cliente == StatoClienteEnum.ghost


def test_ghost_giusto_stato_non_cambia(setup_mocks) -> None:
    """Se stato_cliente è già GHOST e tutti i servizi sono GHOST, non cambia nulla."""
    cliente = _FakeCliente(
        stato_cliente=StatoClienteEnum.ghost,
        stato_nutrizione=StatoClienteEnum.ghost,
        has_nutrizione=True,
    )
    
    result = call_update_stato_cliente(cliente)
    
    assert result is False
    assert cliente.stato_cliente == StatoClienteEnum.ghost


# ============================================================
# CASO 3: TUTTI I SERVIZI PAUSA → stato_cliente = PAUSA
# ============================================================

def test_tutti_servizi_pausa_imposta_cliente_pausa(setup_mocks) -> None:
    """Se TUTTI i servizi sono PAUSA, stato_cliente deve essere PAUSA."""
    cliente = _FakeCliente(
        stato_cliente=StatoClienteEnum.attivo,
        stato_nutrizione=StatoClienteEnum.pausa,
        stato_coach=StatoClienteEnum.pausa,
        has_nutrizione=True,
        has_coach=True,
    )
    
    result = call_update_stato_cliente(cliente)
    
    assert result is True
    assert cliente.stato_cliente == StatoClienteEnum.pausa


def test_pausa_giusto_stato_non_cambia(setup_mocks) -> None:
    """Se stato_cliente è già PAUSA e tutti i servizi sono PAUSA, non cambia nulla."""
    cliente = _FakeCliente(
        stato_cliente=StatoClienteEnum.pausa,
        stato_nutrizione=StatoClienteEnum.pausa,
        has_nutrizione=True,
    )
    
    result = call_update_stato_cliente(cliente)
    
    assert result is False
    assert cliente.stato_cliente == StatoClienteEnum.pausa


# ============================================================
# CASO 4: MISTO (ghost + pausa) → nessun cambiamento
# ============================================================

def test_servizi_misti_ghost_pausa_nessun_cambiamento(setup_mocks) -> None:
    """Se i servizi sono misti (ghost + pausa), stato_cliente non cambia."""
    cliente = _FakeCliente(
        stato_cliente=StatoClienteEnum.attivo,
        stato_nutrizione=StatoClienteEnum.ghost,
        stato_coach=StatoClienteEnum.pausa,
        has_nutrizione=True,
        has_coach=True,
    )
    
    result = call_update_stato_cliente(cliente)
    
    # Non cambia perché non rientra in nessuna regola
    assert result is False
    assert cliente.stato_cliente == StatoClienteEnum.attivo


def test_servizi_misti_attivo_ghost_diventa_attivo(setup_mocks) -> None:
    """Se c'è un servizio attivo E altri ghost, stato_cliente = ATTIVO."""
    cliente = _FakeCliente(
        stato_cliente=None,
        stato_nutrizione=StatoClienteEnum.attivo,
        stato_coach=StatoClienteEnum.ghost,
        has_nutrizione=True,
        has_coach=True,
    )
    
    result = call_update_stato_cliente(cliente)
    
    # Diventa attivo perché c'è almeno un servizio attivo
    assert result is True
    assert cliente.stato_cliente == StatoClienteEnum.attivo


# ============================================================
# CASO 5: RIENTRO DA GHOST CON SERVIZIO ATTIVO
# ============================================================

def test_cliente_ghost_con_servizio_attivo_diventa_attivo(setup_mocks) -> None:
    """Se stato_cliente è GHOST e un servizio diventa ATTIVO, stato_cliente = ATTIVO."""
    cliente = _FakeCliente(
        stato_cliente=StatoClienteEnum.ghost,
        stato_nutrizione=StatoClienteEnum.ghost,
        stato_coach=StatoClienteEnum.attivo,
        has_nutrizione=True,
        has_coach=True,
    )
    
    result = call_update_stato_cliente(cliente)
    
    assert result is True
    assert cliente.stato_cliente == StatoClienteEnum.attivo


def test_cliente_ghost_con_solo_ghost_resta_ghost(setup_mocks) -> None:
    """Se stato_cliente è GHOST e TUTTI i servizi sono GHOST, resta GHOST."""
    cliente = _FakeCliente(
        stato_cliente=StatoClienteEnum.ghost,
        stato_nutrizione=StatoClienteEnum.ghost,
        stato_coach=StatoClienteEnum.ghost,
        has_nutrizione=True,
        has_coach=True,
    )
    
    result = call_update_stato_cliente(cliente)
    
    assert result is False
    assert cliente.stato_cliente == StatoClienteEnum.ghost


# ============================================================
# CASO 6: RIENTRO DA PAUSA CON SERVIZIO ATTIVO
# ============================================================

def test_cliente_pausa_con_servizio_attivo_diventa_attivo(setup_mocks) -> None:
    """Se stato_cliente è PAUSA e un servizio diventa ATTIVO, stato_cliente = ATTIVO."""
    cliente = _FakeCliente(
        stato_cliente=StatoClienteEnum.pausa,
        stato_nutrizione=StatoClienteEnum.pausa,
        stato_coach=StatoClienteEnum.attivo,
        has_nutrizione=True,
        has_coach=True,
    )
    
    result = call_update_stato_cliente(cliente)
    
    assert result is True
    assert cliente.stato_cliente == StatoClienteEnum.attivo


def test_cliente_pausa_con_solo_pausa_resta_pausa(setup_mocks) -> None:
    """Se stato_cliente è PAUSA e TUTTI i servizi sono PAUSA, resta PAUSA."""
    cliente = _FakeCliente(
        stato_cliente=StatoClienteEnum.pausa,
        stato_nutrizione=StatoClienteEnum.pausa,
        stato_coach=StatoClienteEnum.pausa,
        has_nutrizione=True,
        has_coach=True,
    )
    
    result = call_update_stato_cliente(cliente)
    
    assert result is False
    assert cliente.stato_cliente == StatoClienteEnum.pausa


# ============================================================
# CASO 7: NESSUN SERVIZIO ASSEGNATO → nessun cambiamento
# ============================================================

def test_nessun_servizio_assegnato_nessun_cambiamento(setup_mocks) -> None:
    """Se non ci sono servizi assegnati, stato_cliente non cambia."""
    cliente = _FakeCliente(
        stato_cliente=StatoClienteEnum.attivo,
        stato_nutrizione=None,
        stato_coach=None,
        stato_psicologia=None,
        has_nutrizione=False,
        has_coach=False,
        has_psicologia=False,
    )
    
    result = call_update_stato_cliente(cliente)
    
    assert result is False
    assert cliente.stato_cliente == StatoClienteEnum.attivo


# ============================================================
# CASI LIMITE
# ============================================================

def test_servizio_senza_stato_ma_attivo_altro(setup_mocks) -> None:
    """Se un servizio ha stato=None e l'altro è attivo, cliente diventa attivo."""
    cliente = _FakeCliente(
        stato_cliente=None,
        stato_nutrizione=None,  # stato non definito
        stato_coach=StatoClienteEnum.attivo,
        has_nutrizione=True,
        has_coach=True,
    )
    
    result = call_update_stato_cliente(cliente)
    
    # Coach è attivo, quindi cliente diventa attivo
    assert result is True
    assert cliente.stato_cliente == StatoClienteEnum.attivo


def test_solo_servizio_con_stato_non_assegnato(setup_mocks) -> None:
    """Se un servizio ha stato ma non è assegnato, non influenza lo stato globale."""
    cliente = _FakeCliente(
        stato_cliente=None,
        stato_nutrizione=StatoClienteEnum.attivo,  # ha stato
        has_nutrizione=False,  # ma NON è assegnato!
    )
    
    result = call_update_stato_cliente(cliente)
    
    # Nessun servizio assegnato, quindi stato resta None
    assert result is False
    assert cliente.stato_cliente is None


def test_transizione_ghost_a_pausa_con_servizi_misti(setup_mocks) -> None:
    """Se i servizi cambiano da tutti ghost a tutti pausa, stato_cliente cambia."""
    cliente = _FakeCliente(
        stato_cliente=StatoClienteEnum.ghost,
        stato_nutrizione=StatoClienteEnum.pausa,
        stato_coach=StatoClienteEnum.pausa,
        has_nutrizione=True,
        has_coach=True,
    )
    
    result = call_update_stato_cliente(cliente)
    
    # Tutti pausa, quindi diventa pausa
    assert result is True
    assert cliente.stato_cliente == StatoClienteEnum.pausa


def test_mix_attivo_ghost_e_pausa_diventa_attivo(setup_mocks) -> None:
    """Mix di attivo, ghost e pausa → diventa attivo perché c'è almeno un attivo."""
    cliente = _FakeCliente(
        stato_cliente=None,
        stato_nutrizione=StatoClienteEnum.attivo,
        stato_coach=StatoClienteEnum.ghost,
        stato_psicologia=StatoClienteEnum.pausa,
        has_nutrizione=True,
        has_coach=True,
        has_psicologia=True,
    )
    
    result = call_update_stato_cliente(cliente)
    
    assert result is True
    assert cliente.stato_cliente == StatoClienteEnum.attivo
