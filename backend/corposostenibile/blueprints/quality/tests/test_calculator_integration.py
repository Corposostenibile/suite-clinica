"""
Test di integrazione per QualityScoreCalculator: quality_raw, penalty, quality_final,
rolling average, bonus_band da quality_trim.
Richiede db_session e fixture (week_start, professionista, cliente, eleggibilità, quality_client_scores).
"""
from datetime import date, timedelta

import pytest

from corposostenibile.models import (
    Cliente,
    EleggibilitaSettimanale,
    QualityClientScore,
    QualityWeeklyScore,
    SubscriptionContract,
    SubscriptionRenewal,
)
from corposostenibile.blueprints.quality.services.calculator import QualityScoreCalculator


@pytest.fixture
def week_start():
    return date(2025, 1, 6)


@pytest.fixture
def week_end(week_start):
    return week_start + timedelta(days=6)


@pytest.fixture
def elig_10_clienti_7_done(db_session, sample_prof_nutrizionista, week_start):
    """10 eleggibili, 7 con check effettuato → miss_rate 0.3 → penalty 2 (fascia 20-30%)."""
    from corposostenibile.models import Cliente
    prof_id = sample_prof_nutrizionista.id
    clienti_ids = []
    for i in range(10):
        c = Cliente(cliente_id=99990100 + i, nome_cognome=f"Cliente E {i}")
        db_session.add(c)
        clienti_ids.append(c.cliente_id)
    db_session.flush()
    for i, cid in enumerate(clienti_ids):
        elig = EleggibilitaSettimanale(
            cliente_id=cid,
            professionista_id=prof_id,
            week_start_date=week_start,
            eleggibile=True,
            check_effettuato=(i < 7),
        )
        db_session.add(elig)
    db_session.flush()
    return {"prof_id": prof_id, "clienti_ids": clienti_ids, "n_eligible": 10, "n_done": 7}


@pytest.fixture
def seven_client_scores_quality_9(db_session, elig_10_clienti_7_done, week_start):
    """7 QualityClientScore con quality_score 9.0 per il prof."""
    prof_id = elig_10_clienti_7_done["prof_id"]
    clienti_ids = elig_10_clienti_7_done["clienti_ids"][:7]
    week_end = week_start + timedelta(days=6)
    for cid in clienti_ids:
        qcs = QualityClientScore(
            cliente_id=cid,
            professionista_id=prof_id,
            week_start_date=week_start,
            week_end_date=week_end,
            quality_score=9.0,
            check_effettuato=True,
            voto_professionista=9.0,
            voto_percorso=9.0,
            brec_value=0.0,
        )
        db_session.add(qcs)
    db_session.flush()
    return prof_id


class TestQualityRawAndFinalWithPenalty:
    """quality_raw = media(quality_score clienti); quality_final = quality_raw - penalty."""

    def test_quality_final_uguale_raw_meno_penalty(
        self, app, db_session, seven_client_scores_quality_9, elig_10_clienti_7_done, week_start
    ):
        prof_id = seven_client_scores_quality_9
        with app.app_context():
            score = QualityScoreCalculator.calculate_weekly_score(prof_id, week_start)
        # 7 clienti con score 9.0 → quality_raw 9.0
        assert score.quality_raw == 9.0
        # miss_rate = 3/10 = 0.3 → penalty 2 (fascia 20-30%)
        assert score.miss_rate == 0.3
        assert score.n_clients_eligible == 10
        assert score.n_checks_done == 7
        # quality_final = 9.0 - 2 = 7.0
        assert score.quality_final == 7.0


@pytest.fixture
def four_weeks_scores(db_session, sample_prof_nutrizionista):
    """4 QualityWeeklyScore con quality_final 10, 9, 9, 10 (media 9.5)."""
    prof_id = sample_prof_nutrizionista.id
    base = date(2024, 12, 16)
    values = [10.0, 9.0, 9.0, 10.0]
    for i in range(4):
        ws = base + timedelta(days=7 * i)
        we = ws + timedelta(days=6)
        rec = QualityWeeklyScore(
            professionista_id=prof_id,
            week_start_date=ws,
            week_end_date=we,
            quality_final=values[i],
            n_clients_eligible=1,
            n_checks_done=1,
        )
        db_session.add(rec)
    db_session.flush()
    return {"prof_id": prof_id, "last_week_start": base + timedelta(days=21)}


class TestRollingAverage:
    """_calculate_rolling_avg: media degli ultimi N quality_final."""

    def test_rolling_4_weeks(self, app, db_session, four_weeks_scores):
        prof_id = four_weeks_scores["prof_id"]
        last_week = four_weeks_scores["last_week_start"]
        with app.app_context():
            avg = QualityScoreCalculator._calculate_rolling_avg(prof_id, last_week, weeks=4)
        # (10 + 9 + 9 + 10) / 4 = 9.5
        assert avg == 9.5

    def test_rolling_12_weeks_meno_dati(self, app, db_session, four_weeks_scores):
        """Con meno di 12 settimane restituisce media sulle disponibili."""
        prof_id = four_weeks_scores["prof_id"]
        last_week = four_weeks_scores["last_week_start"]
        with app.app_context():
            avg = QualityScoreCalculator._calculate_rolling_avg(prof_id, last_week, weeks=12)
        assert avg == 9.5  # solo 4 settimane, media 9.5


class TestBonusBandFromQualityTrim:
    """bonus_band determinato da quality_trim (media rolling 12 settimane)."""

    def test_quality_trim_da_settimana_precedente_bonus_100(
        self, app, db_session, sample_prof_nutrizionista, sample_cliente_quality, week_start
    ):
        """Settimana precedente con quality_final 9; settimana corrente 9 → quality_trim 9 → bonus 100%."""
        prof_id = sample_prof_nutrizionista.id
        cliente_id = sample_cliente_quality.cliente_id
        week_end = week_start + timedelta(days=6)
        prev_week = week_start - timedelta(days=7)
        prev_week_end = prev_week + timedelta(days=6)
        # La rolling avg usa score già presenti in DB; inseriamo la settimana precedente
        db_session.add(
            QualityWeeklyScore(
                professionista_id=prof_id,
                week_start_date=prev_week,
                week_end_date=prev_week_end,
                quality_final=9.0,
                n_clients_eligible=1,
                n_checks_done=1,
            )
        )
        db_session.add(
            EleggibilitaSettimanale(
                cliente_id=cliente_id,
                professionista_id=prof_id,
                week_start_date=week_start,
                eleggibile=True,
                check_effettuato=True,
            )
        )
        db_session.add(
            QualityClientScore(
                cliente_id=cliente_id,
                professionista_id=prof_id,
                week_start_date=week_start,
                week_end_date=week_end,
                quality_score=9.0,
                check_effettuato=True,
                voto_professionista=9.0,
                voto_percorso=9.0,
                brec_value=0.0,
            )
        )
        db_session.flush()
        with app.app_context():
            score = QualityScoreCalculator.calculate_weekly_score(prof_id, week_start)
        assert score.quality_raw == 9.0
        assert score.quality_final == 9.0
        # Rolling 12 include solo la settimana precedente (9.0) → media 9.0
        assert score.quality_trim == 9.0
        assert score.bonus_band == "100%"


# ═══════════════════════════════════════════════════════════════════════════
# Blocco D: Rinnovo Adj %, KPI composito trimestrale
# ═══════════════════════════════════════════════════════════════════════════

QUARTER_Q1_2025 = "2025-Q1"  # 1 gen - 31 mar 2025


@pytest.fixture
def clienti_con_rinnovo_q1(db_session, sample_prof_nutrizionista):
    """3 clienti con data_rinnovo in Q1 2025; 2 con SubscriptionContract + SubscriptionRenewal (rinnovati)."""
    prof_id = sample_prof_nutrizionista.id
    # date in Q1 2025
    data_scad_1 = date(2025, 1, 15)
    data_scad_2 = date(2025, 2, 10)
    data_scad_3 = date(2025, 3, 20)
    clienti = []
    for i, data_rinnovo in enumerate([data_scad_1, data_scad_2, data_scad_3]):
        c = Cliente(
            cliente_id=99990200 + i,
            nome_cognome=f"Cliente Rinnovo {i}",
            nutrizionista_id=prof_id,
            data_rinnovo=data_rinnovo,
        )
        db_session.add(c)
        clienti.append(c)
    db_session.flush()
    # Contratti per cliente 0 e 1 (i primi due)
    for i in range(2):
        sub = SubscriptionContract(cliente_id=clienti[i].cliente_id)
        db_session.add(sub)
        db_session.flush()
        ren = SubscriptionRenewal(
            subscription_id=sub.subscription_id,
            renewal_payment_date=clienti[i].data_rinnovo,  # stesso giorno o dopo
        )
        db_session.add(ren)
    db_session.flush()
    return {"prof_id": prof_id, "n_scaduti": 3, "n_rinnovati": 2}


class TestGetRinnovoAdjPercentage:
    """% Rinnovo Adj = clienti_rinnovati / clienti_con_contratto_scaduto_nel_periodo × 100."""

    def test_nessun_cliente_scaduto_restituisce_none(self, app, db_session, sample_prof_nutrizionista):
        """Prof senza clienti con data_rinnovo nel trimestre → None."""
        with app.app_context():
            result = QualityScoreCalculator.get_rinnovo_adj_percentage(
                sample_prof_nutrizionista.id, QUARTER_Q1_2025
            )
        assert result is None

    def test_tre_scaduti_due_rinnovati_restituisce_66_67(self, app, db_session, clienti_con_rinnovo_q1):
        """3 clienti scaduti in Q1, 2 con rinnovo → 2/3 * 100 ≈ 66.67%."""
        prof_id = clienti_con_rinnovo_q1["prof_id"]
        with app.app_context():
            result = QualityScoreCalculator.get_rinnovo_adj_percentage(prof_id, QUARTER_Q1_2025)
        assert result is not None
        assert abs(result - (2 / 3 * 100)) < 0.02
        assert result == 66.67


class TestCalculateQuarterlyCompositeKpi:
    """KPI composito: 60% rinnovo_adj_bonus + 40% quality_bonus; applicazione Super Malus opzionale."""

    def test_solo_quality_senza_rinnovo(self, app, db_session, sample_prof_nutrizionista):
        """quality_trim=9 (100%), rinnovo_adj=None (0%) → final_bonus = 0.6*0 + 0.4*100 = 40."""
        with app.app_context():
            weekly_score = QualityWeeklyScore(
                professionista_id=sample_prof_nutrizionista.id,
                week_start_date=date(2025, 3, 3),  # ultima settimana Q1
                week_end_date=date(2025, 3, 9),
                quarter=QUARTER_Q1_2025,
                quality_trim=9.0,
                quality_final=9.0,
                n_clients_eligible=1,
                n_checks_done=1,
            )
            QualityScoreCalculator.calculate_quarterly_composite_kpi(weekly_score, apply_super_malus=False)
        assert weekly_score.rinnovo_adj_percentage is None
        assert weekly_score.rinnovo_adj_bonus_band == "0%"
        assert weekly_score.quality_bonus_band == "100%"
        assert weekly_score.final_bonus_percentage == 40.0
        assert weekly_score.final_bonus_after_malus == 40.0

    def test_rinnovo_80_quality_9_bonus_100(self, app, db_session, clienti_con_rinnovo_q1):
        """Con clienti con rinnovo: rinnovo_adj 66.67% → 60% band; quality_trim 9 → 100%. final = 0.6*60 + 0.4*100 = 76."""
        prof_id = clienti_con_rinnovo_q1["prof_id"]
        with app.app_context():
            weekly_score = QualityWeeklyScore(
                professionista_id=prof_id,
                week_start_date=date(2025, 3, 3),
                week_end_date=date(2025, 3, 9),
                quarter=QUARTER_Q1_2025,
                quality_trim=9.0,
                quality_final=9.0,
                n_clients_eligible=1,
                n_checks_done=1,
            )
            QualityScoreCalculator.calculate_quarterly_composite_kpi(weekly_score, apply_super_malus=False)
        assert weekly_score.rinnovo_adj_percentage == 66.67
        assert weekly_score.rinnovo_adj_bonus_band == "30%"  # 60-69% → 30%
        assert weekly_score.quality_bonus_band == "100%"
        # 0.6 * 30 + 0.4 * 100 = 18 + 40 = 58
        assert weekly_score.final_bonus_percentage == 58.0
        assert weekly_score.final_bonus_after_malus == 58.0

    def test_formula_composita_100_100(self, app, db_session, sample_prof_nutrizionista):
        """Rinnovo 100% e quality 9: entrambi 100% → final_bonus 100."""
        # Servono clienti tutti rinnovati in Q1
        c1 = Cliente(
            cliente_id=99990300,
            nome_cognome="Cliente Solo",
            nutrizionista_id=sample_prof_nutrizionista.id,
            data_rinnovo=date(2025, 1, 20),
        )
        db_session.add(c1)
        db_session.flush()
        sub = SubscriptionContract(cliente_id=c1.cliente_id)
        db_session.add(sub)
        db_session.flush()
        db_session.add(
            SubscriptionRenewal(
                subscription_id=sub.subscription_id,
                renewal_payment_date=date(2025, 1, 20),
            )
        )
        db_session.flush()
        with app.app_context():
            weekly_score = QualityWeeklyScore(
                professionista_id=sample_prof_nutrizionista.id,
                week_start_date=date(2025, 3, 3),
                week_end_date=date(2025, 3, 9),
                quarter=QUARTER_Q1_2025,
                quality_trim=9.0,
                quality_final=9.0,
                n_clients_eligible=1,
                n_checks_done=1,
            )
            QualityScoreCalculator.calculate_quarterly_composite_kpi(weekly_score, apply_super_malus=False)
        assert weekly_score.rinnovo_adj_percentage == 100.0
        assert weekly_score.rinnovo_adj_bonus_band == "100%"
        assert weekly_score.quality_bonus_band == "100%"
        assert weekly_score.final_bonus_percentage == 100.0
        assert weekly_score.final_bonus_after_malus == 100.0
