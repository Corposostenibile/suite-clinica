"""
Test per la sincronizzazione automatica dei campi cache di scadenza
(``corposostenibile.blueprints.customers.events``).

Coperture:

* Calcolo ``inizio + durata``, edge case su durata None/zero/negativa/invalid.
* Popolamento del target solo se ``NULL``.
* Non-sovrascrittura di valori gia` impostati (override manuali).
* Sync indipendente dei 4 campi (rinnovo + 3 specialita`).

I test non toccano il DB: invocano direttamente le funzioni pure usando un
mock ``_FakeCliente`` con gli attributi minimi richiesti.
"""
from __future__ import annotations

from datetime import date

from corposostenibile.blueprints.customers.events import (
    _SCADENZA_FIELDS,
    _compute_scadenza,
    _sync_scadenza_fields,
)


class _FakeCliente:
    """Mock con solo gli attributi coinvolti nel sync (default tutti None)."""

    def __init__(self, **overrides):
        for target, inizio, durata in _SCADENZA_FIELDS:
            setattr(self, target, None)
            setattr(self, inizio, None)
            setattr(self, durata, None)
        self.cliente_id = 1
        for k, v in overrides.items():
            setattr(self, k, v)


# --------------------------------------------------------------------------- #
# _compute_scadenza                                                           #
# --------------------------------------------------------------------------- #
def test_compute_scadenza_happy_path():
    assert _compute_scadenza(date(2026, 4, 21), 90) == date(2026, 7, 20)


def test_compute_scadenza_inizio_none():
    assert _compute_scadenza(None, 90) is None


def test_compute_scadenza_durata_none():
    assert _compute_scadenza(date(2026, 4, 21), None) is None


def test_compute_scadenza_durata_zero():
    assert _compute_scadenza(date(2026, 4, 21), 0) is None


def test_compute_scadenza_durata_negative():
    assert _compute_scadenza(date(2026, 4, 21), -5) is None


def test_compute_scadenza_durata_string_number():
    assert _compute_scadenza(date(2026, 4, 21), "30") == date(2026, 5, 21)


def test_compute_scadenza_durata_invalid_string():
    assert _compute_scadenza(date(2026, 4, 21), "abc") is None


# --------------------------------------------------------------------------- #
# _sync_scadenza_fields                                                       #
# --------------------------------------------------------------------------- #
def test_sync_popola_quando_target_none():
    c = _FakeCliente(
        data_inizio_abbonamento=date(2026, 4, 21),
        durata_programma_giorni=90,
    )
    _sync_scadenza_fields(c)
    assert c.data_rinnovo == date(2026, 7, 20)


def test_sync_non_sovrascrive_valore_esistente():
    # Caso critico: un operatore puo` aver impostato manualmente un rinnovo
    # diverso dal calcolo inizio+durata. Il listener NON deve toccarlo.
    override = date(2027, 1, 1)
    c = _FakeCliente(
        data_rinnovo=override,
        data_inizio_abbonamento=date(2026, 4, 21),
        durata_programma_giorni=90,
    )
    _sync_scadenza_fields(c)
    assert c.data_rinnovo == override


def test_sync_non_popola_senza_inizio():
    c = _FakeCliente(durata_programma_giorni=90)
    _sync_scadenza_fields(c)
    assert c.data_rinnovo is None


def test_sync_non_popola_senza_durata():
    c = _FakeCliente(data_inizio_abbonamento=date(2026, 4, 21))
    _sync_scadenza_fields(c)
    assert c.data_rinnovo is None


def test_sync_non_popola_durata_zero():
    c = _FakeCliente(
        data_inizio_abbonamento=date(2026, 4, 21),
        durata_programma_giorni=0,
    )
    _sync_scadenza_fields(c)
    assert c.data_rinnovo is None


def test_sync_popola_solo_target_mancante():
    # nutrizione calcolabile, coach gia` impostato (da preservare), psicologia
    # senza dati per calcolare.
    c = _FakeCliente(
        data_inizio_nutrizione=date(2026, 4, 21),
        durata_nutrizione_giorni=30,
        data_scadenza_coach=date(2099, 1, 1),
        data_inizio_coach=date(2026, 4, 21),
        durata_coach_giorni=60,
    )
    _sync_scadenza_fields(c)
    assert c.data_scadenza_nutrizione == date(2026, 5, 21)
    assert c.data_scadenza_coach == date(2099, 1, 1)  # preservato
    assert c.data_scadenza_psicologia is None


def test_sync_tutti_e_quattro_i_campi_in_una_chiamata():
    c = _FakeCliente(
        data_inizio_abbonamento=date(2026, 1, 1),
        durata_programma_giorni=365,
        data_inizio_nutrizione=date(2026, 1, 1),
        durata_nutrizione_giorni=30,
        data_inizio_coach=date(2026, 1, 1),
        durata_coach_giorni=60,
        data_inizio_psicologia=date(2026, 1, 1),
        durata_psicologia_giorni=90,
    )
    _sync_scadenza_fields(c)
    # 2026 non e` bisestile: 2026-01-01 + 365gg = 2027-01-01
    assert c.data_rinnovo == date(2027, 1, 1)
    assert c.data_scadenza_nutrizione == date(2026, 1, 31)
    assert c.data_scadenza_coach == date(2026, 3, 2)
    assert c.data_scadenza_psicologia == date(2026, 4, 1)


def test_sync_idempotente():
    # Chiamare piu` volte il sync non deve mai cambiare il risultato.
    c = _FakeCliente(
        data_inizio_abbonamento=date(2026, 4, 21),
        durata_programma_giorni=90,
    )
    _sync_scadenza_fields(c)
    first = c.data_rinnovo
    _sync_scadenza_fields(c)
    _sync_scadenza_fields(c)
    assert c.data_rinnovo == first == date(2026, 7, 20)
