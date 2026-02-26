"""
Test di integrazione per SuperMalusService: is_primary_professional, get_client_professionals,
formula final_bonus_after_malus (con patch di calculate_super_malus).
Richiede db_session e fixture User/Cliente.
"""
from datetime import date
from unittest.mock import patch

import pytest

from corposostenibile.models import Cliente, FiguraRifEnum, User, UserSpecialtyEnum
from corposostenibile.blueprints.quality.services.super_malus import SuperMalusService


class TestIsPrimaryProfessional:
    """Psicologo sempre primario; altrimenti primario se coincide con figura_di_riferimento."""

    def test_psicologo_sempre_primario(
        self, db_session, sample_prof_psicologo, sample_cliente_quality
    ):
        # Cliente ha figura_di_riferimento=nutrizionista, ma psicologo è sempre primario
        assert SuperMalusService.is_primary_professional(
            sample_prof_psicologo, sample_cliente_quality
        ) is True

    def test_figura_nutrizionista_nutrizionista_primario(
        self, db_session, sample_prof_nutrizionista, sample_cliente_quality
    ):
        sample_cliente_quality.figura_di_riferimento = FiguraRifEnum.nutrizionista
        db_session.flush()
        assert SuperMalusService.is_primary_professional(
            sample_prof_nutrizionista, sample_cliente_quality
        ) is True

    def test_figura_nutrizionista_coach_secondario(
        self, db_session, sample_prof_coach, sample_cliente_quality
    ):
        sample_cliente_quality.figura_di_riferimento = FiguraRifEnum.nutrizionista
        db_session.flush()
        assert SuperMalusService.is_primary_professional(
            sample_prof_coach, sample_cliente_quality
        ) is False

    def test_figura_coach_coach_primario(
        self, db_session, sample_prof_coach, sample_cliente_quality
    ):
        sample_cliente_quality.figura_di_riferimento = FiguraRifEnum.coach
        db_session.flush()
        assert SuperMalusService.is_primary_professional(
            sample_prof_coach, sample_cliente_quality
        ) is True

    def test_figura_psicologa_psicologo_primario(
        self, db_session, sample_prof_psicologo, sample_cliente_quality
    ):
        sample_cliente_quality.figura_di_riferimento = FiguraRifEnum.psicologa
        db_session.flush()
        assert SuperMalusService.is_primary_professional(
            sample_prof_psicologo, sample_cliente_quality
        ) is True

    def test_figura_non_impostata_assegnato_considerato_primario(
        self, db_session, sample_prof_nutrizionista, sample_cliente_quality
    ):
        sample_cliente_quality.figura_di_riferimento = None
        db_session.flush()
        assert SuperMalusService.is_primary_professional(
            sample_prof_nutrizionista, sample_cliente_quality
        ) is True


class TestGetClientProfessionals:
    """Lista ID professionisti assegnati al cliente."""

    def test_restituisce_tutti_gli_assegnati(self, sample_cliente_quality):
        ids = SuperMalusService.get_client_professionals(sample_cliente_quality)
        assert len(ids) == 3
        assert sample_cliente_quality.nutrizionista_id in ids
        assert sample_cliente_quality.coach_id in ids
        assert sample_cliente_quality.psicologa_id in ids


class TestCalculateSuperMalusNoData:
    """Senza review negative né rimborsi nel trimestre, malus = 0."""

    def test_nessun_malus_senza_dati(self, db_session, sample_prof_nutrizionista, quarter_string):
        result = SuperMalusService.calculate_super_malus(
            sample_prof_nutrizionista.id, quarter_string
        )
        assert result["malus_percentage"] == 0.0
        assert result["has_negative_review"] is False
        assert result["has_refund"] is False
        assert result["affected_clients"] == []


class TestApplySuperMalusFormula:
    """Formula: final_bonus_after_malus = max(0, final_bonus_percentage - reduction)."""

    def test_malus_50_riduce_meta(self, app, quarter_string):
        """Super malus 50%: bonus 100 → 50."""
        with app.app_context():
            from corposostenibile.models import QualityWeeklyScore
            score = QualityWeeklyScore(
                professionista_id=1,
                week_start_date=date(2025, 1, 6),
                week_end_date=date(2025, 1, 12),
                final_bonus_percentage=100.0,
            )
            with patch.object(
                SuperMalusService,
                "calculate_super_malus",
                return_value={
                    "has_negative_review": True,
                    "has_refund": False,
                    "malus_percentage": 50.0,
                    "is_primary": True,
                    "reason": "test",
                    "affected_clients": [],
                },
            ):
                SuperMalusService.apply_super_malus_to_score(score, quarter_string)
            assert score.super_malus_percentage == 50.0
            assert score.final_bonus_after_malus == 50.0

    def test_malus_100_azzera_bonus(self, app, quarter_string):
        """Super malus 100%: bonus 60 → 0."""
        with app.app_context():
            from corposostenibile.models import QualityWeeklyScore
            score = QualityWeeklyScore(
                professionista_id=1,
                week_start_date=date(2025, 1, 6),
                week_end_date=date(2025, 1, 12),
                final_bonus_percentage=60.0,
            )
            with patch.object(
                SuperMalusService,
                "calculate_super_malus",
                return_value={
                    "has_negative_review": True,
                    "has_refund": True,
                    "malus_percentage": 100.0,
                    "is_primary": True,
                    "reason": "test",
                    "affected_clients": [],
                },
            ):
                SuperMalusService.apply_super_malus_to_score(score, quarter_string)
            assert score.super_malus_percentage == 100.0
            assert score.final_bonus_after_malus == 0.0

    def test_malus_25_secondario(self, app, quarter_string):
        """Super malus 25% (secondario): bonus 40 → 30."""
        with app.app_context():
            from corposostenibile.models import QualityWeeklyScore
            score = QualityWeeklyScore(
                professionista_id=1,
                week_start_date=date(2025, 1, 6),
                week_end_date=date(2025, 1, 12),
                final_bonus_percentage=40.0,
            )
            with patch.object(
                SuperMalusService,
                "calculate_super_malus",
                return_value={
                    "has_negative_review": True,
                    "has_refund": False,
                    "malus_percentage": 25.0,
                    "is_primary": False,
                    "reason": "test",
                    "affected_clients": [],
                },
            ):
                SuperMalusService.apply_super_malus_to_score(score, quarter_string)
            assert score.final_bonus_after_malus == 30.0
