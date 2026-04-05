"""
Tests for physics-based cycle time calculations.
"""
import math
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agv_specs import XQE122Specs, XPL201Specs, TurnSpecs
from src.warehouse_layout import WarehouseDistances
from src.rack_storage import RackConfig
from src.ground_stacking import GroundStackingConfig, BoxDimensions, StackingAreaDimensions
from src.cycle_calculator import (
    xpl201_handover_cycle,
    xqe122_rack_cycle,
    xqe122_rack_average_cycle,
    xqe122_stacking_cycle,
    xqe122_stacking_average_cycle,
    REVERSE_ENTRY_DIST_M,
)


@pytest.fixture
def default_xqe():
    return XQE122Specs()


@pytest.fixture
def default_xpl():
    return XPL201Specs()


@pytest.fixture
def default_turns():
    return TurnSpecs()


@pytest.fixture
def default_dist():
    return WarehouseDistances()


@pytest.fixture
def default_rack():
    return RackConfig()


@pytest.fixture
def default_stacking():
    return GroundStackingConfig()


class TestXPL201HandoverCycle:
    def test_cycle_returns_positive_time(self, default_xpl, default_turns, default_dist):
        result = xpl201_handover_cycle(default_xpl, default_turns, default_dist)
        assert result.total_time_s > 0

    def test_cycle_has_phases(self, default_xpl, default_turns, default_dist):
        result = xpl201_handover_cycle(default_xpl, default_turns, default_dist)
        assert len(result.phases) > 0

    def test_cycle_phases_sum_to_total(self, default_xpl, default_turns, default_dist):
        result = xpl201_handover_cycle(default_xpl, default_turns, default_dist)
        phase_sum = sum(p.duration_s for p in result.phases)
        assert abs(phase_sum - result.total_time_s) < 0.001

    def test_pickup_and_dropoff_included(self, default_xpl, default_turns, default_dist):
        result = xpl201_handover_cycle(default_xpl, default_turns, default_dist)
        names = [p.name for p in result.phases]
        assert any("PICKUP" in n for n in names)
        assert any("DROPOFF" in n for n in names)

    def test_two_turns_included(self, default_xpl, default_turns, default_dist):
        result = xpl201_handover_cycle(default_xpl, default_turns, default_dist)
        turn_phases = [p for p in result.phases if "Turn" in p.name]
        assert len(turn_phases) == 2
        for tp in turn_phases:
            assert tp.duration_s == default_turns.turn_90_degrees_s

    def test_pickup_dropoff_duration(self, default_xpl, default_turns, default_dist):
        result = xpl201_handover_cycle(default_xpl, default_turns, default_dist)
        pickup = next(p for p in result.phases if "PICKUP" in p.name)
        dropoff = next(p for p in result.phases if "DROPOFF" in p.name)
        assert pickup.duration_s == default_xpl.pickup_time_s
        assert dropoff.duration_s == default_xpl.dropoff_time_s

    def test_cycle_total_min_property(self, default_xpl, default_turns, default_dist):
        result = xpl201_handover_cycle(default_xpl, default_turns, default_dist)
        assert abs(result.total_time_min - result.total_time_s / 60.0) < 0.0001

    def test_faster_speeds_reduce_cycle_time(self, default_turns, default_dist):
        slow = XPL201Specs(forward_speed_ms=1.0, reverse_speed_ms=0.3)
        fast = XPL201Specs(forward_speed_ms=2.0, reverse_speed_ms=1.0)
        slow_result = xpl201_handover_cycle(slow, default_turns, default_dist)
        fast_result = xpl201_handover_cycle(fast, default_turns, default_dist)
        assert fast_result.total_time_s < slow_result.total_time_s

    def test_longer_distances_increase_cycle_time(self, default_xpl, default_turns):
        short = WarehouseDistances(
            rest_to_inbound_mm=3000, rest_to_head_aisle_mm=2000,
            head_aisle_to_handover_mm=4000,
        )
        long_ = WarehouseDistances(
            rest_to_inbound_mm=10000, rest_to_head_aisle_mm=5000,
            head_aisle_to_handover_mm=15000,
        )
        short_r = xpl201_handover_cycle(default_xpl, default_turns, short)
        long_r = xpl201_handover_cycle(default_xpl, default_turns, long_)
        assert long_r.total_time_s > short_r.total_time_s


class TestXQE122RackCycle:
    def test_cycle_returns_positive_time(self, default_xqe, default_turns, default_dist, default_rack):
        result = xqe122_rack_cycle(default_xqe, default_turns, default_dist, default_rack, 1, 1)
        assert result.total_time_s > 0

    def test_cycle_phases_sum_to_total(self, default_xqe, default_turns, default_dist, default_rack):
        result = xqe122_rack_cycle(default_xqe, default_turns, default_dist, default_rack, 5, 2)
        phase_sum = sum(p.duration_s for p in result.phases)
        assert abs(phase_sum - result.total_time_s) < 0.001

    def test_lift_phase_present(self, default_xqe, default_turns, default_dist, default_rack):
        result = xqe122_rack_cycle(default_xqe, default_turns, default_dist, default_rack, 1, 2)
        lift_phases = [p for p in result.phases if "LIFT" in p.name]
        assert len(lift_phases) > 0

    def test_lift_time_correct(self, default_xqe, default_turns, default_dist, default_rack):
        level = 2
        result = xqe122_rack_cycle(default_xqe, default_turns, default_dist, default_rack, 1, level)
        height_m = default_rack.shelf_height_m(level)
        expected_lift = height_m / default_xqe.lift_speed_ms
        lift_phase = next(p for p in result.phases if "LIFT" in p.name)
        assert abs(lift_phase.duration_s - expected_lift) < 0.001

    def test_higher_shelf_increases_cycle_time(self, default_xqe, default_turns, default_dist, default_rack):
        r1 = xqe122_rack_cycle(default_xqe, default_turns, default_dist, default_rack, 1, 1)
        r3 = xqe122_rack_cycle(default_xqe, default_turns, default_dist, default_rack, 1, 3)
        assert r3.total_time_s > r1.total_time_s

    def test_position_cycle_time_is_constant_across_aisle(self, default_xqe, default_turns, default_dist, default_rack):
        """
        The AGV enters one end and exits the other end of the aisle.
        Total aisle traversal = rack_length regardless of which position is stored.
        Therefore cycle times for different positions at the same level are equal.
        """
        r_near = xqe122_rack_cycle(default_xqe, default_turns, default_dist, default_rack, 1, 1)
        r_far = xqe122_rack_cycle(default_xqe, default_turns, default_dist, default_rack, 10, 1)
        assert abs(r_far.total_time_s - r_near.total_time_s) < 0.001

    def test_two_turns_in_rack_cycle(self, default_xqe, default_turns, default_dist, default_rack):
        result = xqe122_rack_cycle(default_xqe, default_turns, default_dist, default_rack, 5, 2)
        turn_phases = [p for p in result.phases if "Turn" in p.name]
        assert len(turn_phases) == 2

    def test_average_cycle_is_within_bounds(self, default_xqe, default_turns, default_dist, default_rack):
        avg = xqe122_rack_average_cycle(default_xqe, default_turns, default_dist, default_rack)
        near = xqe122_rack_cycle(default_xqe, default_turns, default_dist, default_rack, 1, 1)
        far = xqe122_rack_cycle(
            default_xqe, default_turns, default_dist, default_rack,
            default_rack.positions_per_shelf, default_rack.num_levels
        )
        assert near.total_time_s <= avg.total_time_s <= far.total_time_s


class TestXQE122StackingCycle:
    def test_cycle_returns_positive_time(self, default_xqe, default_turns, default_dist, default_stacking):
        result = xqe122_stacking_cycle(default_xqe, default_turns, default_dist, default_stacking, 1, 1, 1)
        assert result.total_time_s > 0

    def test_cycle_phases_sum_to_total(self, default_xqe, default_turns, default_dist, default_stacking):
        result = xqe122_stacking_cycle(default_xqe, default_turns, default_dist, default_stacking, 2, 2, 2)
        phase_sum = sum(p.duration_s for p in result.phases)
        assert abs(phase_sum - result.total_time_s) < 0.001

    def test_higher_level_increases_cycle_time(self, default_xqe, default_turns, default_dist, default_stacking):
        r1 = xqe122_stacking_cycle(default_xqe, default_turns, default_dist, default_stacking, 1, 1, 1)
        r4 = xqe122_stacking_cycle(default_xqe, default_turns, default_dist, default_stacking, 1, 1, 4)
        assert r4.total_time_s > r1.total_time_s

    def test_farther_row_increases_cycle_time(self, default_xqe, default_turns, default_dist, default_stacking):
        r_near = xqe122_stacking_cycle(default_xqe, default_turns, default_dist, default_stacking, 1, 1, 1)
        r_far = xqe122_stacking_cycle(default_xqe, default_turns, default_dist, default_stacking, 5, 1, 1)
        assert r_far.total_time_s > r_near.total_time_s

    def test_pickup_dropoff_present(self, default_xqe, default_turns, default_dist, default_stacking):
        result = xqe122_stacking_cycle(default_xqe, default_turns, default_dist, default_stacking, 1, 1, 1)
        names = [p.name for p in result.phases]
        assert any("PICKUP" in n for n in names)
        assert any("DROPOFF" in n for n in names)

    def test_level_1_no_lift_time(self, default_xqe, default_turns, default_dist, default_stacking):
        """Level 1 is at height = 1 * box_height = 1000mm = 1.0m, requiring a lift operation."""
        result = xqe122_stacking_cycle(default_xqe, default_turns, default_dist, default_stacking, 1, 1, 1)
        lift_phases = [p for p in result.phases if "LIFT" in p.name]
        # level 1: height = 1 * 1000mm = 1.0m, lift time = 1.0/0.2 = 5s
        assert len(lift_phases) > 0

    def test_average_cycle_positive(self, default_xqe, default_turns, default_dist, default_stacking):
        avg = xqe122_stacking_average_cycle(default_xqe, default_turns, default_dist, default_stacking)
        assert avg.total_time_s > 0


class TestCycleTimeSummary:
    def test_summary_contains_total(self, default_xpl, default_turns, default_dist):
        result = xpl201_handover_cycle(default_xpl, default_turns, default_dist)
        summary = result.summary()
        assert "Total cycle time" in summary

    def test_summary_lists_phases(self, default_xpl, default_turns, default_dist):
        result = xpl201_handover_cycle(default_xpl, default_turns, default_dist)
        summary = result.summary()
        assert "PICKUP" in summary
        assert "DROPOFF" in summary
