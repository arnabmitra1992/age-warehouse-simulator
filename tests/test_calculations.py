"""
Tests for cycle time calculation physics.
"""
import pytest
from src.rack_storage import (
    calculate_rack_storage_cycle, RackLayoutInfo, RackStorageCycleResult,
    EURO_PALLET_SLOT_SPACING_MM, XQE_FORWARD_SPEED, XQE_REVERSE_SPEED, XQE_LIFT_SPEED,
    PICKUP_TIME, DROPOFF_TIME, TURN_TIME, DEFAULT_SHELF_HEIGHTS_MM,
)
from src.ground_stacking import (
    calculate_ground_stacking_cycle, GroundStackingCycleResult, lift_height_for_level,
    PALLET_HEIGHT_MM, STACK_CLEARANCE_MM,
)
from src.handover_workflow import (
    calculate_handover_cycle, HandoverCycleResult,
    XPL_FORWARD_SPEED, XPL_REVERSE_SPEED,
)


class TestLiftHeightForLevel:
    def test_level_0_is_zero(self):
        assert lift_height_for_level(0) == 0.0

    def test_level_1(self):
        # (1 * 1200 + 200) / 1000 = 1.4 m
        assert lift_height_for_level(1) == pytest.approx(1.4)

    def test_level_2(self):
        # (2 * 1200 + 200) / 1000 = 2.6 m
        assert lift_height_for_level(2) == pytest.approx(2.6)

    def test_level_3(self):
        # (3 * 1200 + 200) / 1000 = 3.8 m
        assert lift_height_for_level(3) == pytest.approx(3.8)

    def test_monotone_increasing(self):
        heights = [lift_height_for_level(i) for i in range(5)]
        for i in range(1, len(heights)):
            assert heights[i] > heights[i-1]


class TestRackStoragePhysics:
    def test_forward_travel_time(self):
        r = calculate_rack_storage_cycle(
            d_head_aisle_m=5.0, d_aisle_m=10.0, lift_height_m=1.2
        )
        # 5.0 / 1.0 = 5.0 s
        assert r.forward_travel_time == pytest.approx(5.0)

    def test_reverse_travel_time(self):
        r = calculate_rack_storage_cycle(
            d_head_aisle_m=5.0, d_aisle_m=10.0, lift_height_m=1.2
        )
        # 2 * 10.0 / 0.3 = 66.67 s
        assert r.reverse_travel_time == pytest.approx(66.67, abs=0.01)

    def test_lift_time(self):
        r = calculate_rack_storage_cycle(
            d_head_aisle_m=5.0, d_aisle_m=10.0, lift_height_m=1.2
        )
        # 2 * 1.2 / 0.2 = 12.0 s
        assert r.lift_time == pytest.approx(12.0)

    def test_turn_time_default(self):
        r = calculate_rack_storage_cycle(
            d_head_aisle_m=5.0, d_aisle_m=10.0, lift_height_m=1.2
        )
        assert r.turn_time == pytest.approx(20.0)  # 2 * 10s

    def test_total_cycle_time_components(self):
        r = calculate_rack_storage_cycle(
            d_head_aisle_m=5.0, d_aisle_m=10.0, lift_height_m=1.2
        )
        expected = r.forward_travel_time + r.reverse_travel_time + r.lift_time + PICKUP_TIME + DROPOFF_TIME + r.turn_time
        assert r.total_cycle_time == pytest.approx(expected)

    def test_zero_lift_height(self):
        r = calculate_rack_storage_cycle(
            d_head_aisle_m=2.0, d_aisle_m=7.5, lift_height_m=0.0
        )
        assert r.lift_time == pytest.approx(0.0)

    def test_shelf_level_stored(self):
        r = calculate_rack_storage_cycle(
            d_head_aisle_m=2.0, d_aisle_m=7.5, lift_height_m=1.2, shelf_level=2
        )
        assert r.shelf_level == 2

    def test_to_dict_keys(self):
        r = calculate_rack_storage_cycle(5.0, 10.0, 1.2)
        d = r.to_dict()
        assert "workflow" in d
        assert "total_cycle_time_s" in d
        assert "components" in d
        assert "distances_m" in d

    def test_typical_cycle_range(self):
        # Standard warehouse: 5m head aisle, 10m aisle, avg 1.8m lift
        r = calculate_rack_storage_cycle(5.0, 10.0, 1.8)
        assert 150 <= r.total_cycle_time <= 250


class TestRackLayoutInfo:
    def test_num_slots_per_side(self):
        layout = RackLayoutInfo(aisle_depth_mm=9500.0)
        # 9500 / 950 = 10 slots
        assert layout.num_slots_per_side == 10

    def test_avg_depth_m(self):
        layout = RackLayoutInfo(aisle_depth_mm=20000.0)
        # 20000 / 2 / 1000 = 10.0 m
        assert layout.avg_depth_m == pytest.approx(10.0)

    def test_avg_shelf_height_m_default(self):
        layout = RackLayoutInfo(aisle_depth_mm=15000.0)
        # [0, 1200, 2400, 3600] / 4 = 1800 mm = 1.8 m
        assert layout.avg_shelf_height_m == pytest.approx(1.8)

    def test_avg_shelf_height_m_empty(self):
        layout = RackLayoutInfo(aisle_depth_mm=15000.0, shelf_heights_mm=[])
        assert layout.avg_shelf_height_m == pytest.approx(1.2)


class TestGroundStackingPhysics:
    def test_level_0_no_lift(self):
        r = calculate_ground_stacking_cycle(
            d_head_aisle_m=5.0, d_aisle_m=10.0, stacking_level=0
        )
        assert r.lift_time == pytest.approx(0.0)

    def test_level_1_lift(self):
        r = calculate_ground_stacking_cycle(
            d_head_aisle_m=5.0, d_aisle_m=10.0, stacking_level=1
        )
        # lift_height = 1.4 m, 2 * 1.4 / 0.2 = 14.0 s
        assert r.lift_time == pytest.approx(14.0)

    def test_total_cycle_level_0(self):
        r = calculate_ground_stacking_cycle(5.0, 10.0, stacking_level=0)
        expected = r.forward_travel_time + r.reverse_travel_time + PICKUP_TIME + DROPOFF_TIME + r.turn_time
        assert r.total_cycle_time == pytest.approx(expected)

    def test_to_dict_has_stacking_level(self):
        r = calculate_ground_stacking_cycle(5.0, 10.0, stacking_level=2)
        d = r.to_dict()
        assert d["stacking_level"] == 2
        assert "lift_height_m" in d


class TestHandoverWorkflow:
    def test_empty_travel_time(self):
        r = calculate_handover_cycle(d_to_dock_m=5.0, d_to_handover_m=10.0)
        # (5 + 10) / 1.5 = 10.0 s
        assert r.empty_travel_time == pytest.approx(10.0)

    def test_loaded_travel_time(self):
        r = calculate_handover_cycle(d_to_dock_m=5.0, d_to_handover_m=10.0)
        # (10 + 5) / 0.3 = 50.0 s
        assert r.loaded_travel_time == pytest.approx(50.0)

    def test_typical_cycle_range(self):
        # Standard 10m distances, 2 turns
        r = calculate_handover_cycle(d_to_dock_m=10.0, d_to_handover_m=15.0)
        assert 150 <= r.total_cycle_time <= 300

    def test_to_dict_workflow_name(self):
        r = calculate_handover_cycle(5.0, 10.0)
        d = r.to_dict()
        assert d["workflow"] == "XPL_201_Handover"

    def test_num_turns_affects_total(self):
        r1 = calculate_handover_cycle(5.0, 10.0, num_turns=2)
        r2 = calculate_handover_cycle(5.0, 10.0, num_turns=4)
        assert r2.total_cycle_time > r1.total_cycle_time
