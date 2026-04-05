"""
Tests for individual AGV workflow modules.
"""
import pytest
from src.handover_workflow import (
    calculate_handover_cycle, HandoverCycleResult,
    XPL_FORWARD_SPEED, XPL_REVERSE_SPEED, PICKUP_TIME, DROPOFF_TIME, TURN_TIME,
)
from src.rack_storage import (
    calculate_rack_storage_cycle, RackStorageCycleResult, RackLayoutInfo,
    EURO_PALLET_SLOT_SPACING_MM, DEFAULT_SHELF_HEIGHTS_MM,
)
from src.ground_stacking import (
    calculate_ground_stacking_cycle, GroundStackingCycleResult, lift_height_for_level,
    PALLET_HEIGHT_MM, STACK_CLEARANCE_MM, GRID_CLEARANCE_MM,
)
from src.cycle_calculator import CycleCalculator, CycleTimeResult, WORKFLOW_XPL_HANDOVER, WORKFLOW_XQE_RACK, WORKFLOW_XQE_STACKING
from src.warehouse_layout import AisleConfig


class TestHandoverWorkflowDetailed:
    def test_xpl_forward_speed(self):
        assert XPL_FORWARD_SPEED == 1.5

    def test_xpl_reverse_speed(self):
        assert XPL_REVERSE_SPEED == 0.3

    def test_pickup_time(self):
        assert PICKUP_TIME == 30

    def test_dropoff_time(self):
        assert DROPOFF_TIME == 30

    def test_turn_time_per_turn(self):
        assert TURN_TIME == 10

    def test_handover_result_distances_stored(self):
        r = calculate_handover_cycle(7.0, 12.0, num_turns=3)
        assert r.d_to_dock_m == pytest.approx(7.0)
        assert r.d_to_handover_m == pytest.approx(12.0)
        assert r.num_turns == 3

    def test_handover_turn_time(self):
        r = calculate_handover_cycle(5.0, 10.0, num_turns=3)
        assert r.turn_time == pytest.approx(30.0)

    def test_handover_to_dict_distances(self):
        r = calculate_handover_cycle(5.0, 10.0)
        d = r.to_dict()
        assert d["distances_m"]["to_dock"] == pytest.approx(5.0)
        assert d["distances_m"]["to_handover"] == pytest.approx(10.0)

    def test_handover_to_dict_components_sum(self):
        r = calculate_handover_cycle(5.0, 10.0)
        d = r.to_dict()
        comps = d["components"]
        total = (comps["empty_travel_s"] + comps["loaded_travel_s"]
                 + comps["pickup_s"] + comps["dropoff_s"] + comps["turns_s"])
        assert total == pytest.approx(d["total_cycle_time_s"], abs=0.01)

    def test_handover_zero_distances(self):
        r = calculate_handover_cycle(0.0, 0.0)
        assert r.total_cycle_time == pytest.approx(PICKUP_TIME + DROPOFF_TIME + 2 * TURN_TIME)


class TestRackStorageWorkflowDetailed:
    def test_euro_pallet_spacing(self):
        assert EURO_PALLET_SLOT_SPACING_MM == 950

    def test_default_shelf_heights(self):
        assert DEFAULT_SHELF_HEIGHTS_MM == [0, 1200, 2400, 3600]

    def test_rack_cycle_num_turns_stored(self):
        r = calculate_rack_storage_cycle(5.0, 10.0, 1.2, num_turns=4)
        assert r.num_turns == 4

    def test_rack_cycle_to_dict_workflow(self):
        r = calculate_rack_storage_cycle(5.0, 10.0, 1.2)
        assert r.to_dict()["workflow"] == "XQE_122_RackStorage"

    def test_rack_layout_info_slots(self):
        info = RackLayoutInfo(aisle_depth_mm=19000.0)
        # 19000 / 950 = 20 slots
        assert info.num_slots_per_side == 20

    def test_rack_layout_info_avg_height_custom(self):
        info = RackLayoutInfo(aisle_depth_mm=15000.0, shelf_heights_mm=[0, 1500, 3000])
        # avg = (0 + 1500 + 3000) / 3 / 1000 = 1.5 m
        assert info.avg_shelf_height_m == pytest.approx(1.5)

    def test_higher_lift_increases_cycle_time(self):
        r_low = calculate_rack_storage_cycle(5.0, 10.0, 0.0)
        r_high = calculate_rack_storage_cycle(5.0, 10.0, 3.6)
        assert r_high.total_cycle_time > r_low.total_cycle_time

    def test_deeper_aisle_increases_cycle_time(self):
        r_shallow = calculate_rack_storage_cycle(5.0, 5.0, 1.2)
        r_deep = calculate_rack_storage_cycle(5.0, 20.0, 1.2)
        assert r_deep.total_cycle_time > r_shallow.total_cycle_time

    def test_rack_cycle_to_dict_distances(self):
        r = calculate_rack_storage_cycle(3.0, 8.0, 1.2)
        d = r.to_dict()
        assert d["distances_m"]["head_aisle"] == pytest.approx(3.0)
        assert d["distances_m"]["aisle"] == pytest.approx(8.0)
        assert d["distances_m"]["lift_height"] == pytest.approx(1.2)


class TestGroundStackingWorkflowDetailed:
    def test_pallet_height_mm(self):
        assert PALLET_HEIGHT_MM == 1200

    def test_stack_clearance_mm(self):
        assert STACK_CLEARANCE_MM == 200

    def test_grid_clearance_mm(self):
        assert GRID_CLEARANCE_MM == 200

    def test_stacking_level_stored(self):
        r = calculate_ground_stacking_cycle(5.0, 10.0, stacking_level=2)
        assert r.stacking_level == 2

    def test_lift_height_matches_formula(self):
        r = calculate_ground_stacking_cycle(5.0, 10.0, stacking_level=2)
        assert r.lift_height_m == pytest.approx(lift_height_for_level(2))

    def test_higher_level_increases_cycle_time(self):
        r0 = calculate_ground_stacking_cycle(5.0, 10.0, stacking_level=0)
        r2 = calculate_ground_stacking_cycle(5.0, 10.0, stacking_level=2)
        assert r2.total_cycle_time > r0.total_cycle_time

    def test_to_dict_workflow(self):
        r = calculate_ground_stacking_cycle(5.0, 10.0)
        assert r.to_dict()["workflow"] == "XQE_122_GroundStacking"

    def test_to_dict_has_all_keys(self):
        r = calculate_ground_stacking_cycle(5.0, 10.0, stacking_level=1)
        d = r.to_dict()
        assert all(k in d for k in ["workflow", "stacking_level", "lift_height_m", "total_cycle_time_s", "components", "distances_m"])


class TestCycleCalculator:
    def setup_method(self):
        self.calc = CycleCalculator(head_aisle_width_m=4.0)

    def _rack_aisle(self, depth_mm=15000):
        return AisleConfig(
            name="RA1", aisle_type="rack",
            width_mm=2840, depth_mm=depth_mm,
            shelf_heights_mm=[0, 1200, 2400, 3600]
        )

    def _handover_aisle(self):
        return AisleConfig(
            name="HA1", aisle_type="handover",
            width_mm=2840, depth_mm=10000,
        )

    def _stacking_aisle(self):
        return AisleConfig(
            name="ST1", aisle_type="ground_stacking",
            width_mm=3000, depth_mm=15000,
            stacking_levels=3,
        )

    def test_rack_workflow(self):
        result = self.calc.calculate_for_aisle(self._rack_aisle())
        assert result.workflow == WORKFLOW_XQE_RACK
        assert result.agv_type == "XQE_122"

    def test_handover_workflow(self):
        result = self.calc.calculate_for_aisle(self._handover_aisle())
        assert result.workflow == WORKFLOW_XPL_HANDOVER
        assert result.agv_type == "XPL_201"

    def test_stacking_workflow(self):
        result = self.calc.calculate_for_aisle(self._stacking_aisle())
        assert result.workflow == WORKFLOW_XQE_STACKING
        assert result.agv_type == "XQE_122"

    def test_cycle_result_has_min_max(self):
        result = self.calc.calculate_for_aisle(self._rack_aisle())
        assert result.min_cycle_time_s <= result.avg_cycle_time_s <= result.max_cycle_time_s

    def test_tasks_per_hour(self):
        result = self.calc.calculate_for_aisle(self._rack_aisle())
        expected = 3600.0 / result.avg_cycle_time_s
        assert result.tasks_per_hour == pytest.approx(expected)

    def test_to_dict(self):
        result = self.calc.calculate_for_aisle(self._rack_aisle())
        d = result.to_dict()
        assert "workflow" in d
        assert "avg_cycle_time_s" in d
        assert "tasks_per_hour" in d
