"""
Test di integrazione per EligibilityService: is_cliente_eligible, calculate_eligibility_for_week.
Richiede db_session e fixture (professionisti, clienti con stati e date).
"""
from datetime import date, timedelta

import pytest

from corposostenibile.models import (
    Cliente,
    EleggibilitaSettimanale,
    StatoClienteEnum,
)
from corposostenibile.blueprints.quality.services.eligibility import EligibilityService


@pytest.fixture
def week_start():
    return date(2025, 1, 6)


class TestIsClienteEligible:
    """Criteri: stato servizio attivo, professionista assegnato, almeno 7 giorni da data_inizio_abbonamento."""

    def test_eleggibile_nutrizionista_stato_attivo_7_giorni(
        self, app, db_session, sample_prof_nutrizionista, week_start
    ):
        """Cliente con stato_nutrizione=attivo, nutrizionista assegnato, attivo da 10 giorni → eleggibile."""
        inizio_abb = week_start - timedelta(days=10)
        cliente = Cliente(
            cliente_id=99990400,
            nome_cognome="Cliente Eleggibile Nutri",
            nutrizionista_id=sample_prof_nutrizionista.id,
            stato_nutrizione=StatoClienteEnum.attivo,
            data_inizio_abbonamento=inizio_abb,
        )
        db_session.add(cliente)
        db_session.flush()
        with app.app_context():
            ok, motivo = EligibilityService.is_cliente_eligible(
                cliente, sample_prof_nutrizionista.id, week_start
            )
        assert ok is True
        assert motivo is None

    def test_non_eleggibile_stato_nutrizione_non_attivo(
        self, app, db_session, sample_prof_nutrizionista, week_start
    ):
        """Stato nutrizione ghost → non eleggibile."""
        inizio_abb = week_start - timedelta(days=10)
        cliente = Cliente(
            cliente_id=99990401,
            nome_cognome="Cliente Ghost Nutri",
            nutrizionista_id=sample_prof_nutrizionista.id,
            stato_nutrizione=StatoClienteEnum.ghost,
            data_inizio_abbonamento=inizio_abb,
        )
        db_session.add(cliente)
        db_session.flush()
        with app.app_context():
            ok, motivo = EligibilityService.is_cliente_eligible(
                cliente, sample_prof_nutrizionista.id, week_start
            )
        assert ok is False
        assert motivo is not None
        assert "nutrizione" in motivo.lower() or "non eleggibile" in motivo.lower()

    def test_non_eleggibile_professionista_non_assegnato(
        self, app, db_session, sample_prof_nutrizionista, sample_prof_coach, week_start
    ):
        """Cliente ha coach assegnato ma non nutrizionista; verifica per nutrizionista → non eleggibile."""
        inizio_abb = week_start - timedelta(days=10)
        cliente = Cliente(
            cliente_id=99990402,
            nome_cognome="Cliente Solo Coach",
            nutrizionista_id=None,
            coach_id=sample_prof_coach.id,
            stato_nutrizione=StatoClienteEnum.attivo,
            stato_coach=StatoClienteEnum.attivo,
            data_inizio_abbonamento=inizio_abb,
        )
        db_session.add(cliente)
        db_session.flush()
        with app.app_context():
            ok, motivo = EligibilityService.is_cliente_eligible(
                cliente, sample_prof_nutrizionista.id, week_start
            )
        assert ok is False
        assert "non assegnato" in motivo.lower()

    def test_non_eleggibile_meno_di_7_giorni_attivo(
        self, app, db_session, sample_prof_nutrizionista, week_start
    ):
        """data_inizio_abbonamento a 3 giorni da week_start → non eleggibile."""
        inizio_abb = week_start - timedelta(days=3)
        cliente = Cliente(
            cliente_id=99990403,
            nome_cognome="Cliente Pochi Giorni",
            nutrizionista_id=sample_prof_nutrizionista.id,
            stato_nutrizione=StatoClienteEnum.attivo,
            data_inizio_abbonamento=inizio_abb,
        )
        db_session.add(cliente)
        db_session.flush()
        with app.app_context():
            ok, motivo = EligibilityService.is_cliente_eligible(
                cliente, sample_prof_nutrizionista.id, week_start
            )
        assert ok is False
        assert "giorni" in motivo.lower() or "7" in motivo

    def test_non_eleggibile_manca_data_inizio_abbonamento(
        self, app, db_session, sample_prof_nutrizionista, week_start
    ):
        """Cliente senza data_inizio_abbonamento → non eleggibile."""
        cliente = Cliente(
            cliente_id=99990404,
            nome_cognome="Cliente Senza Data",
            nutrizionista_id=sample_prof_nutrizionista.id,
            stato_nutrizione=StatoClienteEnum.attivo,
            data_inizio_abbonamento=None,
        )
        db_session.add(cliente)
        db_session.flush()
        with app.app_context():
            ok, motivo = EligibilityService.is_cliente_eligible(
                cliente, sample_prof_nutrizionista.id, week_start
            )
        assert ok is False
        assert "data_inizio_abbonamento" in motivo.lower() or "manca" in motivo.lower()

    def test_eleggibile_coach_stato_attivo(
        self, app, db_session, sample_prof_coach, week_start
    ):
        """Cliente con stato_coach=attivo e coach assegnato, 7+ giorni → eleggibile."""
        inizio_abb = week_start - timedelta(days=14)
        cliente = Cliente(
            cliente_id=99990405,
            nome_cognome="Cliente Eleggibile Coach",
            coach_id=sample_prof_coach.id,
            stato_coach=StatoClienteEnum.attivo,
            data_inizio_abbonamento=inizio_abb,
        )
        db_session.add(cliente)
        db_session.flush()
        with app.app_context():
            ok, motivo = EligibilityService.is_cliente_eligible(
                cliente, sample_prof_coach.id, week_start
            )
        assert ok is True
        assert motivo is None

    def test_eleggibile_psicologo_stato_attivo(
        self, app, db_session, sample_prof_psicologo, week_start
    ):
        """Cliente con stato_psicologia=attivo e psicologa assegnata, 7+ giorni → eleggibile."""
        inizio_abb = week_start - timedelta(days=14)
        cliente = Cliente(
            cliente_id=99990406,
            nome_cognome="Cliente Eleggibile Psico",
            psicologa_id=sample_prof_psicologo.id,
            stato_psicologia=StatoClienteEnum.attivo,
            data_inizio_abbonamento=inizio_abb,
        )
        db_session.add(cliente)
        db_session.flush()
        with app.app_context():
            ok, motivo = EligibilityService.is_cliente_eligible(
                cliente, sample_prof_psicologo.id, week_start
            )
        assert ok is True
        assert motivo is None


class TestCalculateEligibilityForWeek:
    """Calcolo eleggibilità per settimana: conteggi e record EleggibilitaSettimanale."""

    def test_conteggi_eligible_not_eligible(
        self, app, db_session, sample_prof_nutrizionista, week_start
    ):
        """2 clienti del prof: 1 eleggibile (7+ giorni), 1 non eleggibile (solo 3 giorni) → eligible=1, not_eligible=1."""
        inizio_abb_ok = week_start - timedelta(days=10)
        inizio_abb_pochi = week_start - timedelta(days=3)
        c1 = Cliente(
            cliente_id=99990500,
            nome_cognome="Elig One",
            nutrizionista_id=sample_prof_nutrizionista.id,
            stato_nutrizione=StatoClienteEnum.attivo,
            data_inizio_abbonamento=inizio_abb_ok,
        )
        c2 = Cliente(
            cliente_id=99990501,
            nome_cognome="Not Elig Two",
            nutrizionista_id=sample_prof_nutrizionista.id,
            stato_nutrizione=StatoClienteEnum.attivo,
            data_inizio_abbonamento=inizio_abb_pochi,
        )
        db_session.add(c1)
        db_session.add(c2)
        db_session.flush()
        with app.app_context():
            result = EligibilityService.calculate_eligibility_for_week(
                week_start, professionista_id=sample_prof_nutrizionista.id
            )
        assert result["total_processed"] == 2
        assert result["eligible"] == 1
        assert result["not_eligible"] == 1
        assert result["week_start"] == week_start
        assert sample_prof_nutrizionista.id in result["professionisti"]

    def test_record_eleggibilita_creati_con_valori_corretti(
        self, app, db_session, sample_prof_nutrizionista, week_start
    ):
        """Verifica che i record in eleggibilita_settimanale abbiano eleggibile e motivo coerenti."""
        inizio_abb = week_start - timedelta(days=10)
        c1 = Cliente(
            cliente_id=99990510,
            nome_cognome="Solo Elig",
            nutrizionista_id=sample_prof_nutrizionista.id,
            stato_nutrizione=StatoClienteEnum.attivo,
            data_inizio_abbonamento=inizio_abb,
        )
        db_session.add(c1)
        db_session.flush()
        with app.app_context():
            EligibilityService.calculate_eligibility_for_week(
                week_start, professionista_id=sample_prof_nutrizionista.id
            )
        elig = db_session.query(EleggibilitaSettimanale).filter_by(
            cliente_id=c1.cliente_id,
            professionista_id=sample_prof_nutrizionista.id,
            week_start_date=week_start,
        ).first()
        assert elig is not None
        assert elig.eleggibile is True
        assert elig.motivo_non_eleggibile is None
        assert elig.giorni_attivo_snapshot >= 7
