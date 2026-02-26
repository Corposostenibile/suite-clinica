"""
Test end-to-end (Blocco F): calculate_full_week e calculate_quarterly_scores.
Setup completo: clienti eleggibili, WeeklyCheck, WeeklyCheckResponse, poi flusso completo.
"""
from datetime import date, datetime, timedelta

import pytest

from corposostenibile.models import (
    Cliente,
    QualityWeeklyScore,
    StatoClienteEnum,
    WeeklyCheck,
    WeeklyCheckResponse,
)
from corposostenibile.blueprints.quality.services.calculator import QualityScoreCalculator


@pytest.fixture
def week_start():
    return date(2025, 1, 6)


@pytest.fixture
def week_end(week_start):
    return week_start + timedelta(days=6)


@pytest.fixture
def dataset_full_week(db_session, sample_prof_nutrizionista, week_start):
    """
    Un professionista nutrizionista, un cliente eleggibile con WeeklyCheck e
    WeeklyCheckResponse nella settimana (voti 9,9 → quality atteso 9.0).
    """
    prof = sample_prof_nutrizionista
    inizio_abb = week_start - timedelta(days=10)
    cliente = Cliente(
        cliente_id=99990600,
        nome_cognome="Cliente E2E Nutri",
        nutrizionista_id=prof.id,
        stato_nutrizione=StatoClienteEnum.attivo,
        data_inizio_abbonamento=inizio_abb,
    )
    db_session.add(cliente)
    db_session.flush()

    wc = WeeklyCheck(
        cliente_id=cliente.cliente_id,
        token="e2e_test_token_001",
        is_active=True,
    )
    db_session.add(wc)
    db_session.flush()

    # submit_date nel mezzo della settimana (mercoledì)
    submit_dt = datetime.combine(week_start + timedelta(days=2), datetime.min.time().replace(hour=12, minute=0))
    response = WeeklyCheckResponse(
        weekly_check_id=wc.id,
        submit_date=submit_dt,
        nutritionist_rating=9,
        progress_rating=9,
    )
    db_session.add(response)
    db_session.flush()

    return {
        "prof_id": prof.id,
        "cliente_id": cliente.cliente_id,
        "week_start": week_start,
        "week_end": week_end,
    }


class TestCalculateFullWeekE2E:
    """Flusso completo: eleggibilità → process check → weekly score → commit."""

    def test_full_week_restituisce_eligibility_e_weekly_scores(
        self, app, db_session, dataset_full_week
    ):
        """Esegue calculate_full_week e verifica struttura risultato e almeno un score calcolato."""
        week_start = dataset_full_week["week_start"]
        prof_id = dataset_full_week["prof_id"]
        with app.app_context():
            result = QualityScoreCalculator.calculate_full_week(
                week_start, professionista_id=prof_id
            )
        assert result["week_start"] == week_start
        assert "week_end" in result
        assert "eligibility" in result
        assert "check_processing" in result
        assert "weekly_scores" in result
        elig = result["eligibility"]
        assert elig["total_processed"] >= 1
        assert elig["eligible"] >= 1
        assert prof_id in elig["professionisti"]
        check = result["check_processing"]
        assert check.get("created", 0) + check.get("updated", 0) >= 1
        assert len(result["weekly_scores"]) >= 1
        prof_score = next((s for s in result["weekly_scores"] if s["professionista_id"] == prof_id), None)
        assert prof_score is not None
        assert prof_score["quality_final"] is not None
        # (9+9)/2 + 0 BRec = 9.0
        assert abs(prof_score["quality_final"] - 9.0) < 0.05


class TestCalculateQuarterlyScoresE2E:
    """Flusso trimestrale: QualityWeeklyScore per quarter → KPI composito + Super Malus."""

    def test_quarterly_scores_aggiorna_final_bonus_e_restituisce_stats(
        self, app, db_session, sample_prof_nutrizionista
    ):
        """Crea uno score settimanale per Q1, chiama calculate_quarterly_scores, verifica campi aggiornati."""
        quarter = "2025-Q1"
        prof_id = sample_prof_nutrizionista.id
        # Ultima settimana Q1
        week_start = date(2025, 3, 3)
        week_end = date(2025, 3, 9)
        with app.app_context():
            score = QualityWeeklyScore(
                professionista_id=prof_id,
                week_start_date=week_start,
                week_end_date=week_end,
                quarter=quarter,
                quality_final=9.0,
                quality_trim=9.0,
                n_clients_eligible=1,
                n_checks_done=1,
            )
            db_session.add(score)
            db_session.commit()
        with app.app_context():
            result = QualityScoreCalculator.calculate_quarterly_scores(
                quarter, calculated_by_user_id=None
            )
        assert result["quarter"] == quarter
        assert result["professionisti_processati"] >= 1
        assert len(result["results"]) >= 1
        prof_result = next((r for r in result["results"] if r["professionista_id"] == prof_id), None)
        assert prof_result is not None
        assert "quality_trim" in prof_result
        assert "rinnovo_adj_percentage" in prof_result
        assert "final_bonus_percentage" in prof_result
        assert "final_bonus_after_malus" in prof_result
        # Score aggiornato in DB
        db_session.expire_all()
        updated = db_session.query(QualityWeeklyScore).filter_by(
            professionista_id=prof_id,
            quarter=quarter,
        ).first()
        assert updated is not None
        assert updated.final_bonus_percentage is not None
        assert updated.final_bonus_after_malus is not None
