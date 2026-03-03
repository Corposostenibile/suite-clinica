"""
Test sui filtri di periodo e condizione (vedi quality-test-coverage.md).
Verificano che review, rimborsi, rinnovo e check response siano inclusi/esclusi
in base a applied_to_quarter, payment_date, data_rinnovo e submit_date.
"""
from datetime import date, datetime, timedelta

import pytest

from corposostenibile.models import (
    Cliente,
    EleggibilitaSettimanale,
    PaymentTransaction,
    QualityClientScore,
    StatoClienteEnum,
    SubscriptionContract,
    SubscriptionRenewal,
    TrustpilotReview,
    WeeklyCheck,
    WeeklyCheckResponse,
)
from corposostenibile.models import TransactionTypeEnum
from corposostenibile.blueprints.quality.services.calculator import QualityScoreCalculator
from corposostenibile.blueprints.quality.services.super_malus import SuperMalusService


QUARTER_Q1 = "2025-Q1"
QUARTER_Q2 = "2025-Q2"


# ─── 1. Super Malus – filtro review (applied_to_quarter) ─────────────────────

class TestFilterReviewAppliedToQuarter:
    """Review negative: incluse solo se applied_to_quarter == quarter."""

    def test_review_nel_trimestre_inclusa(self, app, db_session, sample_prof_nutrizionista, sample_cliente_quality):
        """Review con applied_to_quarter=2025-Q1 e stelle<=2 → get_clients_with_negative_reviews(Q1) la include."""
        cliente = sample_cliente_quality
        prof_id = sample_prof_nutrizionista.id
        review = TrustpilotReview(
            cliente_id=cliente.cliente_id,
            richiesta_da_professionista_id=prof_id,
            data_richiesta=datetime(2025, 1, 10, 12, 0),
            pubblicata=True,
            stelle=2,
            applied_to_quarter=QUARTER_Q1,
        )
        db_session.add(review)
        db_session.flush()
        with app.app_context():
            results = SuperMalusService.get_clients_with_negative_reviews(prof_id, QUARTER_Q1)
        assert len(results) == 1
        assert results[0]["cliente_id"] == cliente.cliente_id
        assert results[0]["stelle"] == 2

    def test_review_in_altro_trimestre_esclusa(self, app, db_session, sample_prof_nutrizionista, sample_cliente_quality):
        """Review con applied_to_quarter=2025-Q2 → get_clients_with_negative_reviews(2025-Q1) non la include."""
        cliente = sample_cliente_quality
        prof_id = sample_prof_nutrizionista.id
        review = TrustpilotReview(
            cliente_id=cliente.cliente_id,
            richiesta_da_professionista_id=prof_id,
            data_richiesta=datetime(2025, 4, 10, 12, 0),
            pubblicata=True,
            stelle=1,
            applied_to_quarter=QUARTER_Q2,
        )
        db_session.add(review)
        db_session.flush()
        with app.app_context():
            results = SuperMalusService.get_clients_with_negative_reviews(prof_id, QUARTER_Q1)
        assert len(results) == 0


# ─── 2. Super Malus – filtro rimborsi (payment_date nel trimestre) ────────────

class TestFilterRefundPaymentDate:
    """Rimborsi: inclusi solo se payment_date nel trimestre."""

    def test_rimborso_nel_trimestre_incluso(self, app, db_session, sample_prof_nutrizionista):
        """PaymentTransaction rimborso con payment_date in Q1 → get_clients_with_refunds(prof, Q1) lo include."""
        cliente = Cliente(
            cliente_id=99990700,
            nome_cognome="Cliente Rimborso Q1",
            nutrizionista_id=sample_prof_nutrizionista.id,
        )
        db_session.add(cliente)
        db_session.flush()
        sub = SubscriptionContract(cliente_id=cliente.cliente_id)
        db_session.add(sub)
        db_session.flush()
        pay = PaymentTransaction(
            subscription_id=sub.subscription_id,
            cliente_id=cliente.cliente_id,
            payment_date=date(2025, 2, 15),
            transaction_type=TransactionTypeEnum.rimborso,
        )
        db_session.add(pay)
        db_session.flush()
        with app.app_context():
            results = SuperMalusService.get_clients_with_refunds(sample_prof_nutrizionista.id, QUARTER_Q1)
        assert len(results) >= 1
        assert any(r["cliente_id"] == cliente.cliente_id for r in results)

    def test_rimborso_fuori_trimestre_escluso(self, app, db_session, sample_prof_nutrizionista):
        """Rimborso con payment_date in Q2 → get_clients_with_refunds(prof, Q1) non lo include."""
        cliente = Cliente(
            cliente_id=99990701,
            nome_cognome="Cliente Rimborso Q2",
            nutrizionista_id=sample_prof_nutrizionista.id,
        )
        db_session.add(cliente)
        db_session.flush()
        sub = SubscriptionContract(cliente_id=cliente.cliente_id)
        db_session.add(sub)
        db_session.flush()
        pay = PaymentTransaction(
            subscription_id=sub.subscription_id,
            cliente_id=cliente.cliente_id,
            payment_date=date(2025, 4, 15),
            transaction_type=TransactionTypeEnum.rimborso,
        )
        db_session.add(pay)
        db_session.flush()
        with app.app_context():
            results = SuperMalusService.get_clients_with_refunds(sample_prof_nutrizionista.id, QUARTER_Q1)
        assert not any(r["cliente_id"] == cliente.cliente_id for r in results)


# ─── 3. Rinnovo Adj – data_rinnovo fuori dal trimestre ──────────────────────

class TestFilterRinnovoDataRinnovoFuoriPeriodo:
    """Clienti con data_rinnovo fuori dal trimestre non entrano nel calcolo."""

    def test_cliente_con_data_rinnovo_in_q2_escluso_da_q1(self, app, db_session, sample_prof_nutrizionista):
        """Unico cliente del prof ha data_rinnovo in Q2 → get_rinnovo_adj_percentage(prof, Q1) = None."""
        cliente = Cliente(
            cliente_id=99990710,
            nome_cognome="Cliente Rinnovo Q2",
            nutrizionista_id=sample_prof_nutrizionista.id,
            data_rinnovo=date(2025, 4, 20),
        )
        db_session.add(cliente)
        db_session.flush()
        with app.app_context():
            result = QualityScoreCalculator.get_rinnovo_adj_percentage(sample_prof_nutrizionista.id, QUARTER_Q1)
        assert result is None

    def test_solo_clienti_con_data_rinnovo_in_q1_contano(self, app, db_session, sample_prof_nutrizionista):
        """Due clienti: uno con data_rinnovo in Q1 (rinnovato), uno in Q2. Per Q1 conta solo il primo → 100%."""
        c1 = Cliente(
            cliente_id=99990711,
            nome_cognome="Cliente Q1",
            nutrizionista_id=sample_prof_nutrizionista.id,
            data_rinnovo=date(2025, 1, 15),
        )
        c2 = Cliente(
            cliente_id=99990712,
            nome_cognome="Cliente Q2",
            nutrizionista_id=sample_prof_nutrizionista.id,
            data_rinnovo=date(2025, 5, 10),
        )
        db_session.add(c1)
        db_session.add(c2)
        db_session.flush()
        sub = SubscriptionContract(cliente_id=c1.cliente_id)
        db_session.add(sub)
        db_session.flush()
        db_session.add(SubscriptionRenewal(subscription_id=sub.subscription_id, renewal_payment_date=date(2025, 1, 15)))
        db_session.flush()
        with app.app_context():
            result = QualityScoreCalculator.get_rinnovo_adj_percentage(sample_prof_nutrizionista.id, QUARTER_Q1)
        assert result is not None
        assert result == 100.0


# ─── 4. Check – response con submit_date fuori settimana esclusa ─────────────

class TestFilterCheckResponseFuoriSettimana:
    """WeeklyCheckResponse con submit_date in altra settimana non crea QualityClientScore per la settimana corrente."""

    def test_response_solo_nella_settimana_precedente_non_crea_score_corrente(
        self, app, db_session, sample_prof_nutrizionista, sample_cliente_quality
    ):
        """Cliente eleggibile, WeeklyCheck con una sola response nella settimana PRECEDENTE; settimana corrente senza response → nessun QualityClientScore per la settimana corrente."""
        week_current = date(2025, 1, 6)
        week_prev = date(2024, 12, 30)
        inizio_abb = week_current - timedelta(days=14)
        cliente = sample_cliente_quality
        # Aggiorna cliente per eleggibilità
        cliente.stato_nutrizione = StatoClienteEnum.attivo
        cliente.data_inizio_abbonamento = inizio_abb
        cliente.nutrizionista_id = sample_prof_nutrizionista.id
        db_session.flush()
        wc = WeeklyCheck(cliente_id=cliente.cliente_id, token="filter_test_token_001", is_active=True)
        db_session.add(wc)
        db_session.flush()
        # Response solo nella settimana precedente (mercoledì 1 gen 2025 è ancora nella settimana che inizia 30 dic)
        submit_prev = datetime.combine(week_prev + timedelta(days=2), datetime.min.time())
        resp_prev = WeeklyCheckResponse(
            weekly_check_id=wc.id,
            submit_date=submit_prev,
            nutritionist_rating=8,
            progress_rating=8,
        )
        db_session.add(resp_prev)
        db_session.flush()
        # Eleggibilità per settimana corrente
        elig = EleggibilitaSettimanale(
            cliente_id=cliente.cliente_id,
            professionista_id=sample_prof_nutrizionista.id,
            week_start_date=week_current,
            eleggibile=True,
        )
        db_session.add(elig)
        db_session.flush()
        with app.app_context():
            QualityScoreCalculator.process_check_responses_for_week(week_current, sample_prof_nutrizionista.id)
        score = db_session.query(QualityClientScore).filter_by(
            cliente_id=cliente.cliente_id,
            professionista_id=sample_prof_nutrizionista.id,
            week_start_date=week_current,
        ).first()
        assert score is None
