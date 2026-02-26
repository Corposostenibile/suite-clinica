"""
Unit test puri per ReviewService: calculate_brec_distribution, get_quarter_string.
Nessun DB richiesto.
"""
import pytest
from datetime import date

from corposostenibile.blueprints.quality.services.reviews import ReviewService


class TestCalculateBrecDistribution:
    """Richiedente +0.03, resto team +0.02 totali divisi tra (n-1)."""

    def test_solo_richiedente(self):
        dist = ReviewService.calculate_brec_distribution(richiedente_id=10, team_ids=[10])
        assert dist["richiedente_id"] == 10
        assert dist["richiedente_bonus"] == 0.03
        assert dist["team_ids"] == []
        assert dist["team_bonus_each"] == 0.0
        assert dist["team_count"] == 0

    def test_richiedente_piu_uno(self):
        dist = ReviewService.calculate_brec_distribution(richiedente_id=10, team_ids=[10, 20])
        assert dist["richiedente_bonus"] == 0.03
        assert dist["team_ids"] == [20]
        assert dist["team_bonus_each"] == 0.02
        assert dist["team_bonus_total"] == 0.02
        assert dist["team_count"] == 1

    def test_richiedente_piu_due(self):
        dist = ReviewService.calculate_brec_distribution(richiedente_id=10, team_ids=[10, 20, 30])
        assert dist["richiedente_bonus"] == 0.03
        assert set(dist["team_ids"]) == {20, 30}
        assert dist["team_bonus_total"] == 0.02
        assert dist["team_count"] == 2
        # 0.02 / 2 = 0.01 ciascuno
        assert dist["team_bonus_each"] == 0.01


class TestGetQuarterString:
    """Data → "YYYY-Qn" (stesso formato di SuperMalus)."""

    def test_q1(self):
        assert ReviewService.get_quarter_string(date(2025, 2, 1)) == "2025-Q1"

    def test_q4(self):
        assert ReviewService.get_quarter_string(date(2025, 12, 1)) == "2025-Q4"
