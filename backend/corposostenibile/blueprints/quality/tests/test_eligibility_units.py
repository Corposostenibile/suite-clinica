"""
Unit test puri per EligibilityService: get_week_bounds (Lun–Dom).
Nessun DB richiesto.
"""
import pytest
from datetime import date

from corposostenibile.blueprints.quality.services.eligibility import EligibilityService


class TestGetWeekBounds:
    """Settimana ISO: lunedì = inizio, domenica = fine."""

    def test_lunedi_ritorna_stessa_settimimana(self):
        lun = date(2025, 1, 6)
        start, end = EligibilityService.get_week_bounds(lun)
        assert start == date(2025, 1, 6)
        assert end == date(2025, 1, 12)

    def test_domenica_ritorna_lun_dom(self):
        dom = date(2025, 1, 12)
        start, end = EligibilityService.get_week_bounds(dom)
        assert start == date(2025, 1, 6)
        assert end == date(2025, 1, 12)

    def test_mezzo_settimana(self):
        gio = date(2025, 1, 9)
        start, end = EligibilityService.get_week_bounds(gio)
        assert start == date(2025, 1, 6)
        assert end == date(2025, 1, 12)

    def test_capodanno(self):
        # 1 gen 2025 è mercoledì
        start, end = EligibilityService.get_week_bounds(date(2025, 1, 1))
        assert start == date(2024, 12, 30)
        assert end == date(2025, 1, 5)
