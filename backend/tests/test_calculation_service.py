"""
test_calculation_service.py — Unit tests for the CO attainment calculation engine.

These tests are pure-function, no database required.
All expected values are derived manually from the Excel formulas
documented in docs/excel-data-dictionary.md.
"""

import pytest

from app.services.calculation_service import (
    AttainmentResult,
    _compute_direct_attainment,
    _compute_endsem_y,
    _compute_internal_x,
    calculate_attainment,
)


# ---------------------------------------------------------------------------
# Unit tests for individual formula helpers
# ---------------------------------------------------------------------------


class TestComputeInternalX:
    """Test _compute_internal_x: ((CIA*2.5 + Assign*10 + Pres + Quiz) / 400) * 100"""

    def test_all_full_marks(self):
        """Full marks → Internal X = 100%."""
        # cia=40, assess=10, pres=100, quiz=100
        # numerator = (40*2.5) + (10*10) + 100 + 100 = 100+100+100+100 = 400
        result = _compute_internal_x(cia=40, assess=10, presentation=100, quiz=100)
        assert result == pytest.approx(100.0)

    def test_all_zero_marks(self):
        """Zero marks → Internal X = 0%."""
        result = _compute_internal_x(cia=0, assess=0, presentation=0, quiz=0)
        assert result == pytest.approx(0.0)

    def test_typical_values(self):
        """Typical student values from the sample sheet."""
        # cia=30, assess=8, pres=75, quiz=80
        # numerator = 75 + 80 + 75 + 80 = 310
        numerator = (30 * 2.5) + (8 * 10) + 75 + 80
        expected = (numerator / 400.0) * 100.0
        result = _compute_internal_x(cia=30, assess=8, presentation=75, quiz=80)
        assert result == pytest.approx(expected)

    def test_partial_marks(self):
        """Half-marks scenario."""
        # cia=20, assess=5, pres=50, quiz=50
        # numerator = 50 + 50 + 50 + 50 = 200
        result = _compute_internal_x(cia=20, assess=5, presentation=50, quiz=50)
        assert result == pytest.approx(50.0)


class TestComputeEndSemY:
    """Test _compute_endsem_y: (endsem / 20) * 100"""

    def test_full_marks(self):
        result = _compute_endsem_y(endsem=20)
        assert result == pytest.approx(100.0)

    def test_zero(self):
        result = _compute_endsem_y(endsem=0)
        assert result == pytest.approx(0.0)

    def test_half(self):
        result = _compute_endsem_y(endsem=10)
        assert result == pytest.approx(50.0)

    def test_typical(self):
        result = _compute_endsem_y(endsem=15)
        assert result == pytest.approx(75.0)


class TestComputeDirectAttainment:
    """Test _compute_direct_attainment: (X * 0.4) + (Y * 0.6)"""

    def test_both_hundred(self):
        result = _compute_direct_attainment(internal_x=100.0, endsem_y=100.0)
        assert result == pytest.approx(100.0)

    def test_both_zero(self):
        result = _compute_direct_attainment(internal_x=0.0, endsem_y=0.0)
        assert result == pytest.approx(0.0)

    def test_only_internal(self):
        """Only internal marks contribute: 80*0.4 + 0*0.6 = 32."""
        result = _compute_direct_attainment(internal_x=80.0, endsem_y=0.0)
        assert result == pytest.approx(32.0)

    def test_only_endsem(self):
        """Only endsem marks contribute: 0*0.4 + 70*0.6 = 42."""
        result = _compute_direct_attainment(internal_x=0.0, endsem_y=70.0)
        assert result == pytest.approx(42.0)

    def test_typical(self):
        """Typical: X=75, Y=80 → 0.4*75 + 0.6*80 = 30 + 48 = 78."""
        result = _compute_direct_attainment(internal_x=75.0, endsem_y=80.0)
        assert result == pytest.approx(78.0)


# ---------------------------------------------------------------------------
# Integration test: calculate_attainment()
# ---------------------------------------------------------------------------


class TestCalculateAttainment:
    """Test the main calculate_attainment() function end-to-end."""

    def _full_marks_payload(self) -> dict:
        return {
            'cia_co1': 40, 'cia_co2': 40, 'cia_co3': 40, 'cia_co4': 40, 'cia_co5': 40,
            'assess_co1': 10, 'assess_co2': 10, 'assess_co3': 10, 'assess_co4': 10, 'assess_co5': 10,
            'presentation': 100, 'quiz': 100,
            'endsem_co1': 20, 'endsem_co2': 20, 'endsem_co3': 20, 'endsem_co4': 20, 'endsem_co5': 20,
        }

    def _zero_marks_payload(self) -> dict:
        return {
            'cia_co1': 0, 'cia_co2': 0, 'cia_co3': 0, 'cia_co4': 0, 'cia_co5': 0,
            'assess_co1': 0, 'assess_co2': 0, 'assess_co3': 0, 'assess_co4': 0, 'assess_co5': 0,
            'presentation': 0, 'quiz': 0,
            'endsem_co1': 0, 'endsem_co2': 0, 'endsem_co3': 0, 'endsem_co4': 0, 'endsem_co5': 0,
        }

    def test_returns_attainment_result(self):
        result = calculate_attainment(**self._full_marks_payload())
        assert isinstance(result, AttainmentResult)

    def test_full_marks_gives_100(self):
        result = calculate_attainment(**self._full_marks_payload())
        for co in range(1, 6):
            assert getattr(result, f'internal_x_co{co}') == pytest.approx(100.0), f'CO{co} internal_x'
            assert getattr(result, f'endsem_y_co{co}') == pytest.approx(100.0), f'CO{co} endsem_y'
            assert getattr(result, f'direct_attainment_co{co}') == pytest.approx(100.0), f'CO{co} da'

    def test_zero_marks_gives_0(self):
        result = calculate_attainment(**self._zero_marks_payload())
        for co in range(1, 6):
            assert getattr(result, f'internal_x_co{co}') == pytest.approx(0.0)
            assert getattr(result, f'endsem_y_co{co}') == pytest.approx(0.0)
            assert getattr(result, f'direct_attainment_co{co}') == pytest.approx(0.0)

    def test_known_values_co1(self):
        """Verify CO1 calculation with known inputs."""
        # cia=30, assess=8, pres=75, quiz=80, endsem=15
        # internal_x = ((30*2.5)+(8*10)+75+80)/400*100 = (75+80+75+80)/400*100 = 310/400*100 = 77.5
        # endsem_y   = (15/20)*100 = 75
        # direct_att = 77.5*0.4 + 75*0.6 = 31 + 45 = 76
        payload = {
            'cia_co1': 30, 'cia_co2': 0, 'cia_co3': 0, 'cia_co4': 0, 'cia_co5': 0,
            'assess_co1': 8, 'assess_co2': 0, 'assess_co3': 0, 'assess_co4': 0, 'assess_co5': 0,
            'presentation': 75, 'quiz': 80,
            'endsem_co1': 15, 'endsem_co2': 0, 'endsem_co3': 0, 'endsem_co4': 0, 'endsem_co5': 0,
        }
        result = calculate_attainment(**payload)
        assert result.internal_x_co1 == pytest.approx(77.5)
        assert result.endsem_y_co1 == pytest.approx(75.0)
        assert result.direct_attainment_co1 == pytest.approx(76.0)

    def test_co_indices_are_independent(self):
        """Different CIA per CO should produce different internal_x values."""
        payload = {
            'cia_co1': 40, 'cia_co2': 20, 'cia_co3': 0, 'cia_co4': 40, 'cia_co5': 20,
            'assess_co1': 10, 'assess_co2': 5, 'assess_co3': 0, 'assess_co4': 10, 'assess_co5': 5,
            'presentation': 100, 'quiz': 100,
            'endsem_co1': 20, 'endsem_co2': 10, 'endsem_co3': 0, 'endsem_co4': 20, 'endsem_co5': 10,
        }
        result = calculate_attainment(**payload)
        # CO1 and CO4 should be equal (same inputs)
        assert result.direct_attainment_co1 == pytest.approx(result.direct_attainment_co4)
        # CO2 and CO5 should be equal
        assert result.direct_attainment_co2 == pytest.approx(result.direct_attainment_co5)
        # CO3 should be 0 (zero inputs, but pres/quiz shared → non-zero internal)
        # CO3 cia=0, assess=0, pres=100, quiz=100 → internal_x = (0+0+100+100)/400*100 = 50
        assert result.internal_x_co3 == pytest.approx(50.0)
        assert result.endsem_y_co3 == pytest.approx(0.0)
