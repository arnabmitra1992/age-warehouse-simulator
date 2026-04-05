"""
Tests for AGV selection based on aisle width and storage type.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.warehouse_layout import (
    select_agv_for_rack_aisle,
    select_agv_for_ground_stacking,
    AisleCompatibilityResult,
)


class TestXQESelection:
    """XQE_122 is selected for standard aisles (≥ 2.84 m)."""

    def test_xqe_selected_at_minimum_width(self):
        r = select_agv_for_rack_aisle(2.84)
        assert r.agv_type == "XQE_122"

    def test_xqe_not_selected_for_narrow_aisle(self):
        r = select_agv_for_rack_aisle(1.9)
        assert r.agv_type != "XQE_122"

    def test_xqe_not_selected_for_medium_aisle(self):
        r = select_agv_for_rack_aisle(2.5)
        assert r.agv_type != "XQE_122"

    def test_xqe_does_not_use_handover_by_default(self):
        r = select_agv_for_rack_aisle(2.84)
        assert r.use_handover is False

    def test_xqe_available_for_ground_stacking(self):
        r = select_agv_for_ground_stacking()
        assert "XQE_122" in r.compatible_agvs


class TestXNASelection:
    """XNA is selected for narrow aisles (1.717 m ≤ width ≤ 2.0 m)."""

    def test_xna_selected_at_min_width(self):
        r = select_agv_for_rack_aisle(1.717)
        assert r.agv_type == "XNA"

    def test_xna_selected_at_max_narrow_width(self):
        r = select_agv_for_rack_aisle(2.0)
        assert r.agv_type == "XNA"

    def test_xna_always_handover(self):
        for w in [1.717, 1.77, 1.85, 1.95, 2.0]:
            r = select_agv_for_rack_aisle(w)
            assert r.use_handover is True, f"XNA at {w}m should always use handover"

    def test_xna_models_in_compatible_list(self):
        r = select_agv_for_rack_aisle(1.8)
        assert any("XNA" in agv for agv in r.compatible_agvs)

    def test_xna_not_selected_for_standard_aisle(self):
        r = select_agv_for_rack_aisle(2.84)
        assert r.agv_type != "XNA"


class TestXSCPending:
    """Medium aisles (2.0 m < width < 2.84 m) block calculation (XSC pending)."""

    def test_xsc_pending_2_3m(self):
        r = select_agv_for_rack_aisle(2.3)
        assert r.status == "xsc_pending"
        assert r.agv_type is None

    def test_xsc_pending_no_compatible_agvs(self):
        r = select_agv_for_rack_aisle(2.5)
        assert r.compatible_agvs == []

    def test_xsc_pending_is_blocked(self):
        r = select_agv_for_rack_aisle(2.3)
        assert r.is_blocked is True

    def test_xsc_not_applicable_to_ground_stacking(self):
        # Ground stacking always uses XQE regardless of any aisle width
        r = select_agv_for_ground_stacking()
        assert r.is_ok
        assert r.agv_type == "XQE_122"


class TestNoCompatibleAGV:
    """Aisles narrower than 1.717 m have no compatible AGV."""

    def test_no_agv_below_minimum(self):
        r = select_agv_for_rack_aisle(1.5)
        assert r.is_blocked
        assert r.agv_type is None
        assert r.status == "too_narrow"

    def test_no_agv_zero_width(self):
        r = select_agv_for_rack_aisle(0.0)
        assert r.is_blocked

    def test_no_agv_just_below_minimum(self):
        r = select_agv_for_rack_aisle(1.716)
        assert r.is_blocked


class TestAisleCompatibilityResult:
    """Unit tests for the AisleCompatibilityResult data class."""

    def test_is_ok_true(self):
        r = AisleCompatibilityResult("XQE_122", "ok", "note")
        assert r.is_ok is True
        assert r.is_blocked is False

    def test_is_blocked_xsc_pending(self):
        r = AisleCompatibilityResult(None, "xsc_pending", "note")
        assert r.is_blocked is True
        assert r.is_ok is False

    def test_is_blocked_too_narrow(self):
        r = AisleCompatibilityResult(None, "too_narrow", "note")
        assert r.is_blocked is True

    def test_compatible_agvs_auto_from_agv_type(self):
        r = AisleCompatibilityResult("XQE_122", "ok", "note")
        assert "XQE_122" in r.compatible_agvs

    def test_compatible_agvs_empty_when_none(self):
        r = AisleCompatibilityResult(None, "too_narrow", "note")
        assert r.compatible_agvs == []
