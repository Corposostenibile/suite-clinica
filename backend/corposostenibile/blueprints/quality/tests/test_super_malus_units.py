"""
Unit test puri per SuperMalusService: get_quarter_dates, get_quarter_string.
Nessun DB richiesto.
"""
import pytest
from datetime import date

from corposostenibile.blueprints.quality.services.super_malus import SuperMalusService


class TestGetQuarterDates:
    """Trimestre string → (start_date, end_date)."""

    def test_q1(self):
        start, end = SuperMalusService.get_quarter_dates("2025-Q1")
        assert start == date(2025, 1, 1)
        assert end == date(2025, 3, 31)

    def test_q2(self):
        start, end = SuperMalusService.get_quarter_dates("2025-Q2")
        assert start == date(2025, 4, 1)
        assert end == date(2025, 6, 30)

    def test_q3(self):
        start, end = SuperMalusService.get_quarter_dates("2025-Q3")
        assert start == date(2025, 7, 1)
        assert end == date(2025, 9, 30)

    def test_q4(self):
        start, end = SuperMalusService.get_quarter_dates("2025-Q4")
        assert start == date(2025, 10, 1)
        assert end == date(2025, 12, 31)


class TestGetQuarterString:
    """Data → stringa "YYYY-Qn"."""

    def test_gennaio(self):
        assert SuperMalusService.get_quarter_string(date(2025, 1, 15)) == "2025-Q1"

    def test_marzo(self):
        assert SuperMalusService.get_quarter_string(date(2025, 3, 31)) == "2025-Q1"

    def test_aprile(self):
        assert SuperMalusService.get_quarter_string(date(2025, 4, 1)) == "2025-Q2"

    def test_dicembre(self):
        assert SuperMalusService.get_quarter_string(date(2025, 12, 31)) == "2025-Q4"


class TestSuperMalusConstants:
    """Verifica costanti penalità (doc: Primario 50%/100%, Secondario 25%/50%)."""

    def test_primary_single(self):
        assert SuperMalusService.MALUS_PRIMARY_SINGLE == 50.0

    def test_primary_both(self):
        assert SuperMalusService.MALUS_PRIMARY_BOTH == 100.0

    def test_secondary_single(self):
        assert SuperMalusService.MALUS_SECONDARY_SINGLE == 25.0

    def test_secondary_both(self):
        assert SuperMalusService.MALUS_SECONDARY_BOTH == 50.0

    def test_negative_review_threshold(self):
        assert SuperMalusService.NEGATIVE_REVIEW_THRESHOLD == 2
