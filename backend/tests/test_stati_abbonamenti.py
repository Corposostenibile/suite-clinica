"""
Test per le modifiche del branch feature/stati-abbonamenti-paziente:

- Ghost globale: quando tutti i professionisti assegnati mettono in ghost → stato_cliente = ghost
- Pausa globale: quando tutti mettono in pausa → stato_cliente = pausa; riattivazione
- Ricalcolo data scadenza: alla riattivazione da pausa, data_scadenza_* += durata pausa
- Payload webhook outbound GHL (ghost/pausa)

Esegui dalla cartella backend: poetry run pytest tests/test_stati_abbonamenti.py -v
"""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest


# ─────────────────────────── Outbound GHL (no DB) ─────────────────────────── #

class TestOutboundPayloads:
    """Test build payload per webhook GHL ghost e pausa."""

    def test_build_ghost_payload_has_event_and_cliente(self):
        from corposostenibile.blueprints.ghl_integration.outbound import build_ghost_payload

        cliente = MagicMock()
        cliente.cliente_id = 42
        cliente.nome_cognome = "Mario Rossi"
        cliente.mail = "mario@test.it"
        cliente.numero_telefono = "3331234567"
        cliente.ghl_contact_id = "ghl_123"
        cliente.stato_cliente = None
        cliente.stato_nutrizione = None
        cliente.stato_coach = None
        cliente.stato_psicologia = None
        cliente.programma_attuale = None
        cliente.data_inizio_abbonamento = None
        cliente.data_rinnovo = None
        cliente.tipologia_cliente = None
        for attr in ("stato_cliente_data", "stato_nutrizione_data", "stato_coach_data", "stato_psicologia_data"):
            setattr(cliente, attr, None)

        payload = build_ghost_payload(cliente)
        assert payload["event"] == "cliente_ghost"
        assert "timestamp" in payload
        assert payload["cliente"]["cliente_id"] == 42
        assert payload["cliente"]["nome_cognome"] == "Mario Rossi"
        assert payload["cliente"]["mail"] == "mario@test.it"
        assert payload["cliente"]["ghl_contact_id"] == "ghl_123"

    def test_build_pausa_payload_has_event_cliente_pausa(self):
        from corposostenibile.blueprints.ghl_integration.outbound import build_pausa_payload

        cliente = MagicMock()
        cliente.cliente_id = 1
        cliente.nome_cognome = "Test"
        cliente.mail = ""
        cliente.numero_telefono = None
        cliente.ghl_contact_id = None
        cliente.stato_cliente = None
        cliente.stato_nutrizione = None
        cliente.stato_coach = None
        cliente.stato_psicologia = None
        cliente.programma_attuale = None
        cliente.data_inizio_abbonamento = None
        cliente.data_rinnovo = None
        cliente.tipologia_cliente = None
        for attr in ("stato_cliente_data", "stato_nutrizione_data", "stato_coach_data", "stato_psicologia_data"):
            setattr(cliente, attr, None)

        payload = build_pausa_payload(cliente)
        assert payload["event"] == "cliente_pausa"
        assert payload["cliente"]["cliente_id"] == 1


# ─────────────────────────── Service: ghost/pausa globale (mock, no DB) ───── #

def _make_mock_cliente(**kwargs):
    """Crea un MagicMock con attributi tipici di Cliente per i test di servizio."""
    c = MagicMock()
    c.cliente_id = kwargs.get("cliente_id", 1)
    c.nutrizionista_id = kwargs.get("nutrizionista_id")
    c.coach_id = kwargs.get("coach_id")
    c.psicologa_id = kwargs.get("psicologa_id")
    c.nutrizionisti_multipli = kwargs.get("nutrizionisti_multipli")
    c.coaches_multipli = kwargs.get("coaches_multipli")
    c.psicologi_multipli = kwargs.get("psicologi_multipli")
    c.nutrizionista = kwargs.get("nutrizionista")
    c.coach = kwargs.get("coach")
    c.psicologa = kwargs.get("psicologa")
    c.stato_nutrizione = kwargs.get("stato_nutrizione")
    c.stato_coach = kwargs.get("stato_coach")
    c.stato_psicologia = kwargs.get("stato_psicologia")
    c.stato_cliente = kwargs.get("stato_cliente")
    c.stato_cliente_data = kwargs.get("stato_cliente_data")
    return c


class TestCheckGlobalGhostStatus:
    """Test _check_and_update_global_ghost_status (logica servizi assegnati, senza DB)."""

    def test_ghost_globale_con_solo_nutrizionista_in_ghost(self):
        from corposostenibile import create_app
        from corposostenibile.blueprints.customers.services import _check_and_update_global_ghost_status
        from corposostenibile.models import StatoClienteEnum

        app = create_app("testing")
        with app.app_context():
            with patch("corposostenibile.blueprints.customers.services.db.session.add"):
                c = _make_mock_cliente(
                    nutrizionista_id=1,
                    stato_nutrizione=StatoClienteEnum.ghost,
                    stato_cliente=StatoClienteEnum.attivo,
                )
                assert c.stato_cliente == StatoClienteEnum.attivo
                _check_and_update_global_ghost_status(c, None)
                assert c.stato_cliente == StatoClienteEnum.ghost

    def test_pausa_globale_con_solo_coach_in_pausa(self):
        from corposostenibile import create_app
        from corposostenibile.blueprints.customers.services import _check_and_update_global_pausa_status
        from corposostenibile.models import StatoClienteEnum

        app = create_app("testing")
        with app.app_context():
            with patch("corposostenibile.blueprints.customers.services.db.session.add"):
                c = _make_mock_cliente(
                    coach_id=1,
                    stato_coach=StatoClienteEnum.pausa,
                    stato_cliente=StatoClienteEnum.attivo,
                )
                _check_and_update_global_pausa_status(c, None)
                assert c.stato_cliente == StatoClienteEnum.pausa

    def test_riattivazione_se_almeno_uno_non_ghost(self):
        from corposostenibile import create_app
        from corposostenibile.blueprints.customers.services import _check_and_update_global_ghost_status
        from corposostenibile.models import StatoClienteEnum

        app = create_app("testing")
        with app.app_context():
            with patch("corposostenibile.blueprints.customers.services.db.session.add"):
                c = _make_mock_cliente(
                    nutrizionista_id=1,
                    stato_nutrizione=StatoClienteEnum.attivo,
                    stato_cliente=StatoClienteEnum.ghost,
                )
                _check_and_update_global_ghost_status(c, None)
                assert c.stato_cliente == StatoClienteEnum.attivo


# ─────────────────────────── Model: extend scadenza dopo pausa (no DB) ─────── #

class TestExtendScadenzaAfterPausa:
    """Test _extend_scadenza_after_pausa: logica su istanza (senza persistenza)."""

    def test_extend_scadenza_nutrizione_aggiunge_giorni_pausa(self):
        from datetime import date
        from corposostenibile.models import Cliente

        # Oggetto con solo gli attributi usati dal metodo (nessun DB)
        class FakeCliente:
            pass
        c = FakeCliente()
        oggi = date.today()
        scadenza_prima = oggi + timedelta(days=10)
        c.data_scadenza_nutrizione = scadenza_prima

        pausa_start = datetime.utcnow() - timedelta(days=5)
        Cliente._extend_scadenza_after_pausa(c, "nutrizione", pausa_start)

        assert c.data_scadenza_nutrizione is not None
        new_date = c.data_scadenza_nutrizione.date() if hasattr(c.data_scadenza_nutrizione, "date") else c.data_scadenza_nutrizione
        expected = scadenza_prima + timedelta(days=5)
        assert new_date == expected

    def test_extend_scadenza_non_fa_nulla_se_scadenza_assente(self):
        from corposostenibile.models import Cliente

        class FakeCliente:
            pass
        c = FakeCliente()
        c.data_scadenza_nutrizione = None

        pausa_start = datetime.utcnow() - timedelta(days=3)
        Cliente._extend_scadenza_after_pausa(c, "nutrizione", pausa_start)

        assert c.data_scadenza_nutrizione is None


# ─────────────────────────── Labels Ex-Cliente ───────────────────────────── #
# Le label "Ex-Cliente" (al posto di "Stop") sono definite nel frontend
# (corposostenibile-clinica/src/services/clientiService.js: STATO_LABELS, ecc.).
# Test manuale: in UI tab Programma/Nutrizione/Coach/Psicologia deve comparire "Ex-Cliente".
