"""
Tests for PR-2 AGV workflow cycle time calculations.

Covers:
  - XPL_201 handover cycle (handover_workflow.py)
  - XQE_122 rack storage cycle (rack_storage.py)
  - XQE_122 ground stacking cycle (ground_stacking.py)
"""

import math
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.handover_workflow import (
    xpl_handover_cycle,
    HandoverCycleResult,
    _XPL_FWD_SPEED,
    _XPL_REV_SPEED,
    _DOCK_APPROACH_S,
    _TURN_90_S,
    _PICKUP_S,
    _DROPOFF_S,
)
from src.rack_storage import (
    xqe_rack_storage_cycle,
    xqe_rack_storage_cycle_avg,
    rack_positions_count,
    distance_to_position_m,
    average_position_distance_m,
    RackStorageCycleResult,
    _XQE_FWD_SPEED,
    _XQE_REV_SPEED,
    _XQE_LIFT_SPEED,
    _EURO_PALLET_SLOT_M,
)
from src.ground_stacking import (
    xqe_ground_stacking_cycle,
    xqe_ground_stacking_cycle_avg,
    stacking_capacity,
    position_distance_m,
    lift_height_m,
    GroundStackingCycleResult,
)


# ---------------------------------------------------------------------------
# XPL_201 Handover Workflow tests
# ---------------------------------------------------------------------------

class TestHandoverWorkflow:

    def test_basic_cycle_time(self):
        """Verify every component of the handover cycle formula."""
        d_ri = 20.0   # rest → inbound
        d_ih = 30.0   # inbound → handover
        d_hr = 25.0   # handover → rest

        result = xpl_handover_cycle(d_ri, d_ih, d_hr)

        assert isinstance(result, HandoverCycleResult)

        # Travel segments at forward speed (1.5 m/s)
        assert abs(result.travel_rest_to_inbound_s - d_ri / _XPL_FWD_SPEED) < 0.01
        assert abs(result.travel_inbound_to_handover_s - d_ih / _XPL_FWD_SPEED) < 0.01
        assert abs(result.travel_handover_to_rest_s - d_hr / _XPL_FWD_SPEED) < 0.01

        # Fixed approach/depart segments
        assert result.dock_approach_inbound_s == _DOCK_APPROACH_S
        assert result.dock_depart_inbound_s == _DOCK_APPROACH_S
        assert result.handover_approach_s == _DOCK_APPROACH_S
        assert result.handover_depart_s == _DOCK_APPROACH_S
        assert result.rest_park_s == _DOCK_APPROACH_S

        # Two turns
        assert result.turn_to_handover_s == _TURN_90_S
        assert result.turn_from_handover_s == _TURN_90_S

        # Operations
        assert result.pickup_s == _PICKUP_S
        assert result.dropoff_s == _DROPOFF_S

    def test_total_cycle_time_formula(self):
        """Total = sum of all components."""
        result = xpl_handover_cycle(20.0, 30.0, 25.0)
        expected = (
            20.0 / _XPL_FWD_SPEED  # rest → inbound
            + _DOCK_APPROACH_S      # reverse into dock
            + _PICKUP_S             # pickup
            + _DOCK_APPROACH_S      # forward out of dock
            + 30.0 / _XPL_FWD_SPEED # inbound → handover
            + _TURN_90_S            # turn
            + _DOCK_APPROACH_S      # reverse to handover
            + _DROPOFF_S            # dropoff
            + _DOCK_APPROACH_S      # forward from handover
            + _TURN_90_S            # turn back
            + 25.0 / _XPL_FWD_SPEED # handover → rest
            + _DOCK_APPROACH_S      # reverse park
        )
        assert abs(result.total_cycle_time - expected) < 0.01

    def test_zero_distances(self):
        """Zero-distance scenario: only fixed times count."""
        result = xpl_handover_cycle(0.0, 0.0, 0.0)
        fixed = (
            5 * _DOCK_APPROACH_S   # 5 × 5s approach/park segments
            + 2 * _TURN_90_S       # 2 × 10s turns
            + _PICKUP_S
            + _DROPOFF_S
        )
        assert abs(result.total_cycle_time - fixed) < 0.01

    def test_to_dict_keys(self):
        result = xpl_handover_cycle(10.0, 15.0, 12.0)
        d = result.to_dict()
        assert d["workflow"] == "XPL_201_Handover"
        assert "total_cycle_time_s" in d
        assert "distances_m" in d
        assert "components_s" in d

    def test_large_distances(self):
        """Longer distances → longer total cycle time."""
        r1 = xpl_handover_cycle(10.0, 10.0, 10.0)
        r2 = xpl_handover_cycle(100.0, 100.0, 100.0)
        assert r2.total_cycle_time > r1.total_cycle_time

    def test_dock_approach_is_five_seconds(self):
        """1.5 m at 0.3 m/s = 5 s."""
        assert abs(_DOCK_APPROACH_S - 5.0) < 0.01


# ---------------------------------------------------------------------------
# XQE_122 Rack Storage Workflow tests
# ---------------------------------------------------------------------------

class TestRackStorageWorkflow:

    def test_rack_positions_count(self):
        """Euro pallets (950 mm) fit 21 in 20 000 mm rack."""
        assert rack_positions_count(20000) == 21
        assert rack_positions_count(9500) == 10
        assert rack_positions_count(950) == 1

    def test_distance_to_position(self):
        """Position 1 is at 0.475 m from entry, each +0.95 m thereafter."""
        d1 = distance_to_position_m(1)
        assert abs(d1 - _EURO_PALLET_SLOT_M / 2.0) < 0.001   # 0.475 m
        d2 = distance_to_position_m(2)
        assert abs(d2 - (1.5 * _EURO_PALLET_SLOT_M)) < 0.001  # 1.425 m

    def test_distance_position_invalid(self):
        with pytest.raises(ValueError):
            distance_to_position_m(0)

    def test_basic_rack_cycle(self):
        """Verify component times for a basic rack storage cycle."""
        d_ri = 15.0     # rest → inbound
        d_ia = 20.0     # inbound → aisle entry
        h = 2.6         # shelf height
        rack_len = 10000  # mm

        result = xqe_rack_storage_cycle(
            d_rest_to_inbound=d_ri,
            d_inbound_to_rack_entry=d_ia,
            shelf_height=h,
            rack_length_mm=rack_len,
        )

        assert isinstance(result, RackStorageCycleResult)
        assert abs(result.travel_rest_to_inbound_s - d_ri / _XQE_FWD_SPEED) < 0.01
        assert abs(result.travel_inbound_to_aisle_s - d_ia / _XQE_FWD_SPEED) < 0.01
        assert abs(result.lift_up_s - h / _XQE_LIFT_SPEED) < 0.01
        assert abs(result.lift_down_s - h / _XQE_LIFT_SPEED) < 0.01

    def test_rack_cycle_lift_max(self):
        """4.5 m is the maximum lift height for XQE_122."""
        result = xqe_rack_storage_cycle(
            d_rest_to_inbound=10.0,
            d_inbound_to_rack_entry=10.0,
            shelf_height=4.5,
            rack_length_mm=10000,
        )
        assert result.total_cycle_time > 0

    def test_rack_cycle_exceeds_max_lift(self):
        """Shelf height > 4.5 m should raise ValueError."""
        with pytest.raises(ValueError, match="4.5"):
            xqe_rack_storage_cycle(10.0, 10.0, shelf_height=5.0, rack_length_mm=10000)

    def test_rack_cycle_zero_lift(self):
        """Ground level (height=0) → no lift time."""
        result = xqe_rack_storage_cycle(10.0, 10.0, shelf_height=0.0, rack_length_mm=10000)
        assert result.lift_up_s == 0.0
        assert result.lift_down_s == 0.0

    def test_rack_cycle_avg_multiple_heights(self):
        """Average cycle time across multiple shelf heights."""
        avg = xqe_rack_storage_cycle_avg(
            d_rest_to_inbound=10.0,
            d_inbound_to_rack_entry=15.0,
            shelf_heights=[1.3, 2.6, 3.9, 4.5],
            rack_length_mm=20000,
        )
        assert avg > 0
        # Should be greater than cycle time for lowest shelf
        r_low = xqe_rack_storage_cycle(10.0, 15.0, 1.3, 20000)
        assert avg > r_low.total_cycle_time

    def test_rack_cycle_avg_empty_heights(self):
        with pytest.raises(ValueError):
            xqe_rack_storage_cycle_avg(10.0, 10.0, [], 10000)

    def test_to_dict_keys(self):
        result = xqe_rack_storage_cycle(10.0, 10.0, 2.0, 10000)
        d = result.to_dict()
        assert d["workflow"] == "XQE_122_Rack_Storage"
        assert "total_cycle_time_s" in d
        assert "distances_m" in d

    def test_higher_shelf_longer_cycle(self):
        """Higher shelf → longer lift time → longer total cycle."""
        r1 = xqe_rack_storage_cycle(10.0, 15.0, 1.3, 20000)
        r2 = xqe_rack_storage_cycle(10.0, 15.0, 4.5, 20000)
        assert r2.total_cycle_time > r1.total_cycle_time


# ---------------------------------------------------------------------------
# XQE_122 Ground Stacking Workflow tests
# ---------------------------------------------------------------------------

class TestGroundStackingWorkflow:

    def test_stacking_capacity(self):
        """Verify column/row/level calculation with 200 mm clearance."""
        # area: 10 000 × 20 000, box: 800 × 1200 × 1000
        cols, rows, levels = stacking_capacity(10000, 20000, 800, 1200, 1000)
        assert cols >= 1
        assert rows >= 1
        assert levels >= 4   # 4500 / 1000 = 4

    def test_stacking_capacity_single_box(self):
        """Minimum: at least 1 position in every dimension."""
        c, r, l = stacking_capacity(1000, 1000, 800, 1200, 1000)
        assert c >= 1
        assert r >= 1
        assert l >= 1

    def test_position_distance(self):
        """Position (1,1) should be at the clearance offset."""
        d_col, d_row = position_distance_m(1, 1, 800, 1200)
        assert abs(d_col - 0.2) < 0.001   # 200 mm clearance
        assert abs(d_row - 0.2) < 0.001

    def test_position_distance_col2(self):
        """Column 2 is one (box_width + 2×clearance) further."""
        d_col1, _ = position_distance_m(1, 1, 800, 1200)
        d_col2, _ = position_distance_m(2, 1, 800, 1200)
        step = (800 + 400) / 1000.0  # (box_width + 2×200mm) / 1000
        assert abs(d_col2 - d_col1 - step) < 0.001

    def test_lift_height(self):
        """Level 0 = 0 m; level 2 = 2 × box_height_mm / 1000."""
        assert lift_height_m(0, 1000) == 0.0
        assert abs(lift_height_m(2, 1000) - 2.0) < 0.001

    def test_basic_stacking_cycle(self):
        """Ground level (level=0) → no lift time."""
        result = xqe_ground_stacking_cycle(
            d_rest_to_inbound=15.0,
            d_inbound_to_stacking=20.0,
            box_width_mm=800,
            box_length_mm=1200,
            box_height_mm=1000,
            col=1, row=1, level=0,
        )
        assert isinstance(result, GroundStackingCycleResult)
        assert result.lift_up_s == 0.0
        assert result.lift_down_s == 0.0
        assert result.total_cycle_time > 0

    def test_stacking_cycle_higher_level(self):
        """Higher level → more lift time → longer cycle."""
        r0 = xqe_ground_stacking_cycle(10.0, 20.0, 800, 1200, 1000, 1, 1, 0)
        r2 = xqe_ground_stacking_cycle(10.0, 20.0, 800, 1200, 1000, 1, 1, 2)
        assert r2.total_cycle_time > r0.total_cycle_time

    def test_stacking_cycle_exceeds_max_lift(self):
        """Level × box_height > 4 500 mm should raise ValueError."""
        with pytest.raises(ValueError, match="4.5"):
            # level=5 × 1000 mm = 5 000 mm = 5.0 m > 4.5 m
            xqe_ground_stacking_cycle(10.0, 20.0, 800, 1200, 1000, 1, 1, level=5)

    def test_stacking_cycle_avg(self):
        """Average cycle time across all levels."""
        avg = xqe_ground_stacking_cycle_avg(
            d_rest_to_inbound=15.0,
            d_inbound_to_stacking=20.0,
            area_width_mm=10000,
            area_length_mm=20000,
            box_width_mm=800,
            box_length_mm=1200,
            box_height_mm=1000,
        )
        assert avg > 0

    def test_to_dict_keys(self):
        result = xqe_ground_stacking_cycle(10.0, 20.0, 800, 1200, 1000, 1, 1, 0)
        d = result.to_dict()
        assert d["workflow"] == "XQE_122_Ground_Stacking"
        assert "total_cycle_time_s" in d
        assert "distances_m" in d
        assert d["position"] == {"col": 1, "row": 1, "level": 0}

    def test_farther_column_longer_cycle(self):
        """Position in column 3 takes longer than column 1."""
        r1 = xqe_ground_stacking_cycle(10.0, 20.0, 800, 1200, 1000, 1, 1, 0)
        r3 = xqe_ground_stacking_cycle(10.0, 20.0, 800, 1200, 1000, 3, 1, 0)
        assert r3.total_cycle_time > r1.total_cycle_time


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
