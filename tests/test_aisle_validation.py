"""
Tests for aisle width validation and AGV selection logic.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.warehouse_layout import (
    XNA_MIN_AISLE_WIDTH_M,
    XNA_MAX_AISLE_WIDTH_M,
    XSC_MAX_AISLE_WIDTH_M,
    XQE_MIN_AISLE_WIDTH_M,
    HANDOVER_DISTANCE_THRESHOLD_M,
    select_agv_for_rack_aisle,
    select_agv_for_ground_stacking,
    needs_handover_xqe,
)


class TestAisleWidthThresholds:
    def test_xna_min_threshold(self):
        assert XNA_MIN_AISLE_WIDTH_M == pytest.approx(1.717)

    def test_xna_max_threshold(self):
        assert XNA_MAX_AISLE_WIDTH_M == pytest.approx(2.0)

    def test_xsc_max_is_xqe_min(self):
        assert XSC_MAX_AISLE_WIDTH_M == XQE_MIN_AISLE_WIDTH_M

    def test_xqe_min_threshold(self):
        assert XQE_MIN_AISLE_WIDTH_M == pytest.approx(2.84)

    def test_handover_distance_threshold(self):
        assert HANDOVER_DISTANCE_THRESHOLD_M == pytest.approx(50.0)


class TestRackAisleSelection:
    # ------------------------------------------------------------------
    # Standard aisle (≥ 2.84 m) → XQE_122
    # ------------------------------------------------------------------

    def test_standard_aisle_exact(self):
        result = select_agv_for_rack_aisle(2.84)
        assert result.is_ok
        assert result.agv_type == "XQE_122"
        assert result.status == "ok"
        assert not result.use_handover

    def test_standard_aisle_wide(self):
        result = select_agv_for_rack_aisle(3.5)
        assert result.is_ok
        assert result.agv_type == "XQE_122"

    def test_standard_aisle_contains_xqe(self):
        result = select_agv_for_rack_aisle(2.84)
        assert "XQE_122" in result.compatible_agvs

    # ------------------------------------------------------------------
    # Medium aisle (2.0 m < width < 2.84 m) → XSC_PENDING
    # ------------------------------------------------------------------

    def test_medium_aisle_2_3m(self):
        result = select_agv_for_rack_aisle(2.3)
        assert result.is_blocked
        assert result.status == "xsc_pending"
        assert result.agv_type is None
        assert result.compatible_agvs == []

    def test_medium_aisle_2_01m(self):
        result = select_agv_for_rack_aisle(2.01)
        assert result.is_blocked
        assert result.status == "xsc_pending"

    def test_medium_aisle_2_83m(self):
        result = select_agv_for_rack_aisle(2.83)
        assert result.is_blocked
        assert result.status == "xsc_pending"

    def test_medium_aisle_note_mentions_xsc(self):
        result = select_agv_for_rack_aisle(2.5)
        assert "xsc" in result.note.lower() or "XSC" in result.note

    # ------------------------------------------------------------------
    # Narrow aisle (1.717 m ≤ width ≤ 2.0 m) → XNA
    # ------------------------------------------------------------------

    def test_narrow_aisle_exact_min(self):
        result = select_agv_for_rack_aisle(1.717)
        assert result.is_ok
        assert result.agv_type == "XNA"
        assert result.use_handover

    def test_narrow_aisle_exact_max(self):
        result = select_agv_for_rack_aisle(2.0)
        assert result.is_ok
        assert result.agv_type == "XNA"
        assert result.use_handover

    def test_narrow_aisle_mid(self):
        result = select_agv_for_rack_aisle(1.9)
        assert result.is_ok
        assert result.agv_type == "XNA"

    def test_narrow_aisle_contains_xna_models(self):
        result = select_agv_for_rack_aisle(1.8)
        assert "XNA_121" in result.compatible_agvs or "XNA_151" in result.compatible_agvs

    def test_narrow_aisle_always_handover(self):
        for w in [1.717, 1.8, 1.9, 2.0]:
            result = select_agv_for_rack_aisle(w)
            assert result.use_handover, f"XNA at {w}m should always use handover"

    # ------------------------------------------------------------------
    # Too narrow (< 1.717 m) → no compatible AGV
    # ------------------------------------------------------------------

    def test_too_narrow_1_5m(self):
        result = select_agv_for_rack_aisle(1.5)
        assert result.is_blocked
        assert result.status == "too_narrow"
        assert result.agv_type is None

    def test_too_narrow_1_716m(self):
        result = select_agv_for_rack_aisle(1.716)
        assert result.is_blocked
        assert result.status == "too_narrow"

    def test_too_narrow_zero(self):
        result = select_agv_for_rack_aisle(0.0)
        assert result.is_blocked

    def test_too_narrow_note_contains_minimum(self):
        result = select_agv_for_rack_aisle(1.5)
        assert "1.717" in result.note


class TestGroundStackingSelection:
    def test_xqe_only(self):
        result = select_agv_for_ground_stacking()
        assert result.is_ok
        assert result.agv_type == "XQE_122"
        assert result.compatible_agvs == ["XQE_122"]

    def test_no_handover_required_by_default(self):
        result = select_agv_for_ground_stacking()
        # Handover is distance-based for XQE stacking, not from this call
        assert result.status == "ok"

    def test_note_mentions_xsc_cannot_floor_stack(self):
        result = select_agv_for_ground_stacking()
        assert "xsc" in result.note.lower() or "XSC" in result.note


class TestHandoverDecision:
    def test_no_handover_below_threshold(self):
        assert needs_handover_xqe(49.9) is False

    def test_no_handover_at_zero(self):
        assert needs_handover_xqe(0.0) is False

    def test_handover_at_exact_threshold(self):
        assert needs_handover_xqe(50.0) is True

    def test_handover_above_threshold(self):
        assert needs_handover_xqe(60.0) is True
        assert needs_handover_xqe(100.0) is True
