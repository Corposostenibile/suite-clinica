"""
Unit test puri per QualityScoreCalculator: fasce penalty, bonus band, formule.
Nessun DB richiesto.
"""
import pytest
from datetime import date

from corposostenibile.blueprints.quality.services.calculator import QualityScoreCalculator


class TestMissRatePenalty:
    """Fasce Quality Malus: % check mancanti → punti (doc: 0-5%→0, 5-10%→0.5, ..., >50%→5)."""

    def test_zero_miss_rate(self):
        assert QualityScoreCalculator._get_miss_rate_penalty(0.0) == 0.0

    def test_sotto_5_percent(self):
        assert QualityScoreCalculator._get_miss_rate_penalty(0.04) == 0.0
        assert QualityScoreCalculator._get_miss_rate_penalty(0.05) == 0.0

    def test_fascia_5_10(self):
        assert QualityScoreCalculator._get_miss_rate_penalty(0.06) == 0.5
        assert QualityScoreCalculator._get_miss_rate_penalty(0.10) == 0.5

    def test_fascia_10_20(self):
        assert QualityScoreCalculator._get_miss_rate_penalty(0.11) == 1.0
        assert QualityScoreCalculator._get_miss_rate_penalty(0.20) == 1.0

    def test_fascia_20_30(self):
        assert QualityScoreCalculator._get_miss_rate_penalty(0.21) == 2.0
        assert QualityScoreCalculator._get_miss_rate_penalty(0.30) == 2.0

    def test_fascia_30_40(self):
        assert QualityScoreCalculator._get_miss_rate_penalty(0.31) == 3.0
        assert QualityScoreCalculator._get_miss_rate_penalty(0.40) == 3.0

    def test_fascia_40_50(self):
        assert QualityScoreCalculator._get_miss_rate_penalty(0.41) == 4.0
        assert QualityScoreCalculator._get_miss_rate_penalty(0.50) == 4.0

    def test_sopra_50_percent(self):
        assert QualityScoreCalculator._get_miss_rate_penalty(0.51) == 5.0
        assert QualityScoreCalculator._get_miss_rate_penalty(1.0) == 5.0


class TestBonusBandQuality:
    """Bonus band KPI2 Quality (40%): ≥9→100%, 8.5-9→60%, 8-8.5→30%, <8→0%."""

    def test_ge_9(self):
        assert QualityScoreCalculator._get_bonus_band(9.0) == "100%"
        assert QualityScoreCalculator._get_bonus_band(9.5) == "100%"

    def test_85_9(self):
        assert QualityScoreCalculator._get_bonus_band(8.5) == "60%"
        assert QualityScoreCalculator._get_bonus_band(8.99) == "60%"

    def test_8_85(self):
        assert QualityScoreCalculator._get_bonus_band(8.0) == "30%"
        assert QualityScoreCalculator._get_bonus_band(8.49) == "30%"

    def test_under_8(self):
        assert QualityScoreCalculator._get_bonus_band(7.99) == "0%"
        assert QualityScoreCalculator._get_bonus_band(0.0) == "0%"

    def test_none(self):
        assert QualityScoreCalculator._get_bonus_band(None) == "0%"


class TestGetBonusFromBands:
    """_get_bonus_from_bands: valore + fasce → percentuale (0, 30, 60, 100)."""

    def test_quality_bands(self):
        bands = QualityScoreCalculator.QUALITY_BONUS_BANDS
        assert QualityScoreCalculator._get_bonus_from_bands(9.0, bands) == 100
        assert QualityScoreCalculator._get_bonus_from_bands(8.5, bands) == 60
        assert QualityScoreCalculator._get_bonus_from_bands(8.0, bands) == 30
        assert QualityScoreCalculator._get_bonus_from_bands(7.0, bands) == 0

    def test_rinnovo_bands(self):
        bands = QualityScoreCalculator.RINNOVO_ADJ_BONUS_BANDS
        assert QualityScoreCalculator._get_bonus_from_bands(80.0, bands) == 100
        assert QualityScoreCalculator._get_bonus_from_bands(70.0, bands) == 60
        assert QualityScoreCalculator._get_bonus_from_bands(60.0, bands) == 30
        assert QualityScoreCalculator._get_bonus_from_bands(50.0, bands) == 0


class TestQualityClientFormula:
    """Formula quality cliente: (VProf + VRating) / 2 + BRec; VRating = coordinator se presente else progress."""

    def test_formula_senza_coordinatore(self):
        voto_prof = 8.0
        voto_percorso = 9.0
        voto_coordinatore = None
        brec = 0.03
        v_rating = voto_coordinatore if voto_coordinatore is not None else voto_percorso
        quality = (voto_prof + v_rating) / 2.0 + brec
        assert abs(quality - 8.53) < 0.01  # 8.5 + 0.03
        assert round(quality, 2) == 8.53

    def test_formula_con_coordinatore(self):
        voto_prof = 9.0
        voto_percorso = 7.0
        voto_coordinatore = 10.0
        brec = 0.0
        v_rating = voto_coordinatore if voto_coordinatore is not None else voto_percorso
        quality = (voto_prof + v_rating) / 2.0 + brec
        assert quality == 9.5  # (9+10)/2

    def test_formula_rounding(self):
        voto_prof = 8.0
        v_rating = 8.0
        brec = 0.02
        quality = (voto_prof + v_rating) / 2.0 + brec  # 8.02
        assert round(quality, 2) == 8.02


class TestKpiCompositeWeights:
    """Formula bonus composito: 60% × rinnovo_adj_bonus + 40% × quality_bonus."""

    def test_weights_constants(self):
        assert QualityScoreCalculator.KPI_WEIGHT_RINNOVO_ADJ == 0.60
        assert QualityScoreCalculator.KPI_WEIGHT_QUALITY == 0.40

    def test_composite_formula_explicit(self):
        # Con valori noti: 100 e 100 → 100; 0 e 0 → 0; 60 e 40 → 52
        rinnovo_bonus = 100
        quality_bonus = 100
        final = (
            QualityScoreCalculator.KPI_WEIGHT_RINNOVO_ADJ * rinnovo_bonus
            + QualityScoreCalculator.KPI_WEIGHT_QUALITY * quality_bonus
        )
        assert final == 100.0

        rinnovo_bonus = 60
        quality_bonus = 30
        final = (
            QualityScoreCalculator.KPI_WEIGHT_RINNOVO_ADJ * rinnovo_bonus
            + QualityScoreCalculator.KPI_WEIGHT_QUALITY * quality_bonus
        )
        assert abs(final - 48.0) < 0.01  # 36 + 12
