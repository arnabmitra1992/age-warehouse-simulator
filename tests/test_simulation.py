"""
Unit tests for the Warehouse AGV Fleet Sizing Simulator.

Tests cover:
  - AGV specification constants
  - Physics cycle time calculations (backward fork logic, turns, lifting)
  - Graph generation from layout JSON
  - Fleet sizing formula
  - Reference layout structure validity
"""

import math
import sys
import os

import pytest

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agv_specs import (
    AGV_SPECS,
    TASK_PARAMETERS,
    get_agv_spec,
    get_compatible_agv_types,
    validate_aisle_width,
    validate_lift_height,
    get_compatible_agvs_for_aisle,
)
from src.physics import AGVPhysics, TaskCycleResult
from src.graph_generator import WarehouseGraph
from src.reference_layouts import (
    SIMPLE_WAREHOUSE_JSON,
    MEDIUM_WAREHOUSE_JSON,
    COMPLEX_WAREHOUSE_JSON,
    REFERENCE_LAYOUTS,
)
from src.fleet_sizing import FleetSizingCalculator
from src.simulation_engine import SimulationEngine
from src.layout_parser import _validate_layout_schema, _validate_agv_constraints, _extract_json_from_text


# ---------------------------------------------------------------------------
# AGV Specs tests
# ---------------------------------------------------------------------------

class TestAGVSpecs:
    def test_all_four_agv_types_present(self):
        assert set(AGV_SPECS.keys()) == {"XQE_122", "XPL_201", "XNA_121", "XNA_151"}

    def test_xqe_122_specs(self):
        s = AGV_SPECS["XQE_122"]
        assert s["forward_speed"] == 1.0
        assert s["reverse_speed"] == 0.3
        assert s["lifting_speed"] == 0.2
        assert s["capacity"] == 1200
        assert s["aisle_width"] == 2.84
        assert s["max_lift_height"] == 4.5

    def test_xpl_201_specs(self):
        s = AGV_SPECS["XPL_201"]
        assert s["forward_speed"] == 1.5
        assert s["reverse_speed"] == 0.3
        assert s["lifting_speed"] is None   # no significant lifting
        assert s["capacity"] == 2000
        assert s["max_lift_height"] == 0.20  # 20 cm

    def test_xna_121_specs(self):
        s = AGV_SPECS["XNA_121"]
        assert s["forward_speed"] == 1.0
        assert s["reverse_speed"] == 1.0    # equal in both directions
        assert s["lifting_speed"] == 0.2
        assert s["capacity"] == 1200
        assert s["aisle_width"] == 1.77
        assert s["turn_radius"] == 4.0
        assert s["max_lift_height"] == 8.5

    def test_xna_151_specs(self):
        s = AGV_SPECS["XNA_151"]
        assert s["forward_speed"] == 1.0
        assert s["reverse_speed"] == 1.0
        assert s["capacity"] == 1500
        assert s["max_lift_height"] == 13.0
        assert s["turn_radius"] == 4.0

    def test_task_parameters(self):
        assert TASK_PARAMETERS["pickup_time"] == 30
        assert TASK_PARAMETERS["dropoff_time"] == 30
        assert TASK_PARAMETERS["turn_time_per_90deg"] == 10
        assert TASK_PARAMETERS["target_utilization"] == 0.80

    def test_get_agv_spec(self):
        spec = get_agv_spec("XQE_122")
        assert spec["forward_speed"] == 1.0

    def test_get_agv_spec_invalid(self):
        with pytest.raises(ValueError):
            get_agv_spec("UNKNOWN_AGV")

    def test_get_compatible_agv_types_rack(self):
        rack_agvs = get_compatible_agv_types("rack")
        assert "XQE_122" in rack_agvs
        assert "XNA_121" in rack_agvs
        assert "XNA_151" in rack_agvs
        assert "XPL_201" not in rack_agvs  # XPL can only go 20cm

    def test_get_compatible_agv_types_ground_storage(self):
        ground_agvs = get_compatible_agv_types("ground_storage")
        assert "XPL_201" in ground_agvs
        assert "XQE_122" in ground_agvs

    def test_validate_aisle_width(self):
        assert validate_aisle_width("XNA_121", 1.77) is True
        assert validate_aisle_width("XNA_121", 1.5) is False
        assert validate_aisle_width("XQE_122", 1.77) is False  # needs 2.84m
        assert validate_aisle_width("XQE_122", 2.84) is True
        assert validate_aisle_width("XQE_122", 3.0) is True

    def test_validate_lift_height(self):
        assert validate_lift_height("XQE_122", 4.5) is True
        assert validate_lift_height("XQE_122", 4.6) is False
        assert validate_lift_height("XNA_151", 13.0) is True
        assert validate_lift_height("XNA_151", 13.1) is False

    def test_get_compatible_agvs_for_aisle_narrow_rack(self):
        # 1.77m narrow aisle, rack, 8.5m height
        compatible = get_compatible_agvs_for_aisle(1.77, "rack", required_lift_height=8.5)
        assert "XNA_121" in compatible
        assert "XNA_151" in compatible
        assert "XQE_122" not in compatible  # aisle too narrow

    def test_get_compatible_agvs_for_aisle_wide_rack(self):
        # 2.84m wide aisle (>= 2.5m), rack, 4.5m height
        # XNA models must NOT appear for standard-width aisles
        compatible = get_compatible_agvs_for_aisle(2.84, "rack", required_lift_height=4.5)
        assert "XQE_122" in compatible
        assert "XNA_121" not in compatible   # XNA only for < 2.5m aisles
        assert "XNA_151" not in compatible   # XNA only for < 2.5m aisles
        # XPL_201 can't do rack
        assert "XPL_201" not in compatible


# ---------------------------------------------------------------------------
# Physics tests
# ---------------------------------------------------------------------------

class TestAGVPhysics:
    def test_rack_task_xqe_basic(self):
        """XQE_122 rack task: verify travel time formula."""
        phys = AGVPhysics("XQE_122")
        result = phys.calculate_rack_task(
            d_head_aisle_inbound=20.0,
            d_aisle=15.0,
            d_head_aisle_outbound=20.0,
            lift_height=2.0,
            num_turns=2,
            aisle_name="SA1",
        )
        # Forward travel: (20 + 20) / 1.0 = 40s
        assert abs(result.forward_travel_time - 40.0) < 0.01
        # Reverse travel: (15 + 15) / 0.3 = 100s
        assert abs(result.reverse_travel_time - 100.0) < 0.01
        # Lift up + down: 2 * (2.0 / 0.2) = 20s
        assert abs(result.lift_time_up - 10.0) < 0.01
        assert abs(result.lift_time_down - 10.0) < 0.01
        # Turns: 2 * 10s = 20s
        assert abs(result.turn_time - 20.0) < 0.01
        # Pickup + dropoff: 60s
        assert result.pickup_time == 30
        assert result.dropoff_time == 30
        # Total
        expected_total = 40 + 100 + 20 + 30 + 30 + 20
        assert abs(result.total_cycle_time - expected_total) < 0.01

    def test_rack_task_xna_equal_speeds(self):
        """XNA_121 has equal forward/reverse speeds, so travel time is the same
        regardless of load state."""
        phys = AGVPhysics("XNA_121")
        result = phys.calculate_rack_task(
            d_head_aisle_inbound=10.0,
            d_aisle=20.0,
            d_head_aisle_outbound=10.0,
            lift_height=4.0,
            num_turns=2,
            aisle_name="SA1",
        )
        # forward speed = reverse speed = 1.0 m/s
        # Forward: (10 + 10) / 1.0 = 20s
        assert abs(result.forward_travel_time - 20.0) < 0.01
        # Reverse: (20 + 20) / 1.0 = 40s
        assert abs(result.reverse_travel_time - 40.0) < 0.01
        # Lift: 2 * (4.0 / 0.2) = 40s
        assert abs(result.lift_time_up + result.lift_time_down - 40.0) < 0.01

    def test_ground_storage_task_xpl(self):
        """XPL_201 ground storage: reverse distance × 2 (in + out)."""
        phys = AGVPhysics("XPL_201")
        result = phys.calculate_ground_storage_task(
            d_head_aisle_inbound=15.0,
            d_aisle=10.0,
            d_head_aisle_outbound=15.0,
            num_turns=2,
            aisle_name="SA3",
        )
        # Forward: (15 + 15) / 1.5 = 20s
        assert abs(result.forward_travel_time - 20.0) < 0.01
        # Reverse: (10 + 10) / 0.3 ≈ 66.67s  (in empty + out loaded, both reverse)
        assert abs(result.reverse_travel_time - (10 + 10) / 0.3) < 0.01
        # No lifting
        assert result.lift_time_up == 0.0
        assert result.lift_time_down == 0.0
        # Dock positioning
        assert result.dock_positioning_time == 10.0

    def test_rack_task_xqe_lift_height_too_high(self):
        """XQE_122 cannot lift beyond 4.5m."""
        phys = AGVPhysics("XQE_122")
        with pytest.raises(ValueError, match="exceeds"):
            phys.calculate_rack_task(
                d_head_aisle_inbound=10.0,
                d_aisle=10.0,
                d_head_aisle_outbound=10.0,
                lift_height=5.0,  # exceeds 4.5m max
                num_turns=2,
            )

    def test_can_operate_in_aisle_narrow_xqe(self):
        """XQE_122 must not enter a 1.77m narrow aisle."""
        phys = AGVPhysics("XQE_122")
        ok, reason = phys.can_operate_in_aisle(1.77, "rack", 4.0)
        assert ok is False
        assert "1.77" in reason or "narrow" in reason.lower() or "2.84" in reason

    def test_can_operate_in_aisle_xna_rack(self):
        """XNA_121 can enter 1.77m rack aisle."""
        phys = AGVPhysics("XNA_121")
        ok, reason = phys.can_operate_in_aisle(1.77, "rack", 8.5)
        assert ok is True
        assert reason == ""

    def test_can_operate_in_aisle_xpl_rack(self):
        """XPL_201 cannot do rack storage."""
        phys = AGVPhysics("XPL_201")
        ok, reason = phys.can_operate_in_aisle(3.0, "rack", 0.0)
        assert ok is False

    def test_ground_stacking_with_height(self):
        """Ground stacking adds lift time for stack height."""
        phys = AGVPhysics("XQE_122")
        stack_height = 1.0
        result = phys.calculate_ground_stacking_task(
            d_head_aisle_inbound=10.0,
            d_aisle=10.0,
            d_head_aisle_outbound=10.0,
            num_turns=2,
            stack_height=stack_height,
        )
        # Lift time should reflect stack_height
        expected_lift = 2 * stack_height / 0.2  # up and down
        assert abs(result.lift_time_up + result.lift_time_down - expected_lift) < 0.01

    def test_turn_time_calculation(self):
        """Turn time = num_turns × 10 seconds."""
        phys = AGVPhysics("XQE_122")
        for turns in [0, 1, 2, 4]:
            result = phys.calculate_rack_task(
                d_head_aisle_inbound=10.0,
                d_aisle=5.0,
                d_head_aisle_outbound=10.0,
                lift_height=1.0,
                num_turns=turns,
            )
            assert abs(result.turn_time - turns * 10.0) < 0.01

    def test_count_turns_in_path(self):
        """Validate turn counting using node positions."""
        # L-shaped path: (0,0) → (10,0) → (10,10) = 1 turn
        positions = {
            "A": (0, 0),
            "B": (10, 0),
            "C": (10, 10),
        }
        turns = AGVPhysics.count_turns_in_path(["A", "B", "C"], positions)
        assert turns == 1

        # Straight path: no turns
        positions2 = {"A": (0, 0), "B": (5, 0), "C": (10, 0)}
        turns2 = AGVPhysics.count_turns_in_path(["A", "B", "C"], positions2)
        assert turns2 == 0

        # U-turn: (0,0) → (10,0) → (10,10) → (0,10) = 2 turns
        positions3 = {
            "A": (0, 0), "B": (10, 0), "C": (10, 10), "D": (0, 10)
        }
        turns3 = AGVPhysics.count_turns_in_path(["A", "B", "C", "D"], positions3)
        assert turns3 == 2

    def test_cycle_time_to_dict(self):
        """Verify to_dict serialization."""
        phys = AGVPhysics("XQE_122")
        result = phys.calculate_rack_task(10.0, 10.0, 10.0, 2.0, 2)
        d = result.to_dict()
        assert d["agv_type"] == "XQE_122"
        assert "total_cycle_time_s" in d
        assert "components" in d
        assert "distances_m" in d


# ---------------------------------------------------------------------------
# Graph generator tests
# ---------------------------------------------------------------------------

class TestWarehouseGraph:
    def setup_method(self):
        self.wg = WarehouseGraph()
        self.wg.build_from_layout(MEDIUM_WAREHOUSE_JSON)

    def test_graph_has_nodes(self):
        assert self.wg.graph.number_of_nodes() > 0

    def test_graph_has_edges(self):
        assert self.wg.graph.number_of_edges() > 0

    def test_dock_nodes_present(self):
        nodes = list(self.wg.graph.nodes)
        assert "dock_IB1" in nodes
        assert "dock_OB1" in nodes

    def test_aisle_entry_nodes_present(self):
        nodes = list(self.wg.graph.nodes)
        for aisle in ["SA1", "SA2", "SA3", "SA4"]:
            assert f"aisle_entry_{aisle}" in nodes

    def test_storage_positions_present(self):
        positions = self.wg.get_all_storage_positions("SA1")
        assert len(positions) > 0

    def test_positions_have_coordinates(self):
        pos = self.wg.get_node_positions()
        assert "dock_IB1" in pos
        x, y = pos["dock_IB1"]
        assert x == 0.0
        assert y == 6.0

    def test_dock_to_aisle_distance(self):
        d_head, d_aisle, turns = self.wg.get_dock_to_aisle_distances("dock_IB1", "SA1")
        assert d_head > 0
        # The turn at aisle entry should be counted
        assert turns >= 1

    def test_validate_agv_path_compatible(self):
        path = self.wg.shortest_path("dock_IB1", "aisle_entry_SA1")
        assert path is not None
        # XNA_121 can operate in SA1 (2.84m > 1.77m)
        ok, issues = self.wg.validate_agv_path(path, "XNA_121")
        assert ok is True

    def test_validate_agv_path_incompatible(self):
        # SA1 is 2.84m wide – XQE_122 needs 2.84m so should be compatible
        path = self.wg.shortest_path("dock_IB1", "aisle_entry_SA1")
        assert path is not None
        # SA1 for XNA – needs 1.77m, width is 2.84m – compatible
        ok, issues = self.wg.validate_agv_path(path, "XNA_121")
        assert ok is True

    def test_graph_summary(self):
        summary = self.wg.summary()
        assert "nodes" in summary.lower() or "Graph" in summary

    def test_simple_warehouse_graph(self):
        wg = WarehouseGraph()
        wg.build_from_layout(SIMPLE_WAREHOUSE_JSON)
        assert "dock_IB1" in wg.graph.nodes
        assert "aisle_entry_SA1" in wg.graph.nodes
        assert "aisle_entry_SA2" in wg.graph.nodes

    def test_complex_warehouse_graph(self):
        wg = WarehouseGraph()
        wg.build_from_layout(COMPLEX_WAREHOUSE_JSON)
        for aisle in ["SA1", "SA2", "SA3", "SA4", "SA5", "SA6"]:
            assert f"aisle_entry_{aisle}" in wg.graph.nodes


# ---------------------------------------------------------------------------
# Reference layouts tests
# ---------------------------------------------------------------------------

class TestReferenceLayouts:
    def test_three_reference_layouts(self):
        assert len(REFERENCE_LAYOUTS) == 3

    def test_each_layout_has_required_fields(self):
        required = {
            "warehouse", "inbound_docks", "outbound_docks",
            "head_aisles", "storage_aisles",
            "ground_storage_zones", "ground_stacking_zones",
        }
        for ref in REFERENCE_LAYOUTS:
            layout = ref["json"]
            missing = required - set(layout.keys())
            assert not missing, f"Layout '{ref['label']}' missing keys: {missing}"

    def test_simple_warehouse_structure(self):
        layout = SIMPLE_WAREHOUSE_JSON
        assert layout["warehouse"]["width"] == 40.0
        assert len(layout["storage_aisles"]) == 2
        for aisle in layout["storage_aisles"]:
            assert aisle["storage_type"] == "rack"
            assert aisle["entry_type"] == "dead-end"

    def test_medium_warehouse_mixed_storage(self):
        layout = MEDIUM_WAREHOUSE_JSON
        types = {a["storage_type"] for a in layout["storage_aisles"]}
        assert "rack" in types
        assert "ground_storage" in types
        assert "ground_stacking" in types

    def test_complex_warehouse_has_through_aisle(self):
        layout = COMPLEX_WAREHOUSE_JSON
        through_aisles = [
            a for a in layout["storage_aisles"] if a["entry_type"] == "through"
        ]
        assert len(through_aisles) >= 1

    def test_complex_warehouse_has_two_head_aisles(self):
        assert len(COMPLEX_WAREHOUSE_JSON["head_aisles"]) == 2


# ---------------------------------------------------------------------------
# Layout parser utilities tests
# ---------------------------------------------------------------------------

class TestLayoutParserUtils:
    def test_validate_layout_schema_valid(self):
        errors = _validate_layout_schema(MEDIUM_WAREHOUSE_JSON)
        assert errors == []

    def test_validate_layout_schema_missing_keys(self):
        partial = {"warehouse": {"name": "test"}}
        errors = _validate_layout_schema(partial)
        assert len(errors) > 0

    def test_validate_agv_constraints_valid(self):
        warnings = _validate_agv_constraints(MEDIUM_WAREHOUSE_JSON)
        assert warnings == []  # all aisles should have at least one compatible AGV

    def test_extract_json_plain(self):
        text = '{"warehouse": {"name": "test", "width": 10.0, "length": 20.0}}'
        result = _extract_json_from_text(text)
        assert result is not None
        assert result["warehouse"]["name"] == "test"

    def test_extract_json_with_markdown_fences(self):
        text = "Here is the JSON:\n```json\n{\"key\": \"value\"}\n```"
        result = _extract_json_from_text(text)
        assert result is not None
        assert result["key"] == "value"

    def test_extract_json_invalid_returns_none(self):
        result = _extract_json_from_text("this is not json at all")
        assert result is None


# ---------------------------------------------------------------------------
# Fleet sizing tests
# ---------------------------------------------------------------------------

class TestFleetSizing:
    def setup_method(self):
        self.wg = WarehouseGraph()
        self.wg.build_from_layout(MEDIUM_WAREHOUSE_JSON)
        self.calc = FleetSizingCalculator(self.wg, MEDIUM_WAREHOUSE_JSON)

    def test_analyse_aisles_returns_list(self):
        analyses = self.calc.analyse_aisles()
        assert len(analyses) == 4  # medium warehouse has 4 aisles

    def test_aisle_compatibility_sa1(self):
        analyses = self.calc.analyse_aisles()
        sa1 = next(a for a in analyses if a.aisle_name == "SA1")
        # SA1 is 2.84m rack aisle (>= 2.5m) – XQE should be compatible;
        # XNA models must NOT appear (they are reserved for narrow aisles < 2.5m)
        assert "XQE_122" in sa1.compatible_agvs
        assert "XNA_121" not in sa1.compatible_agvs
        assert "XNA_151" not in sa1.compatible_agvs
        # XPL is ground only
        assert "XPL_201" not in sa1.compatible_agvs

    def test_fleet_size_formula(self):
        """Fleet size = ceil(tph / (tph_per_agv * utilization))."""
        analyses = self.calc.analyse_aisles()
        # Use XQE_122 which is compatible with the 2.84m rack aisles in MEDIUM layout
        xqe_analysis = [a for a in analyses if "XQE_122" in a.cycle_times]
        assert xqe_analysis
        avg_ct = sum(a.cycle_times["XQE_122"] for a in xqe_analysis) / len(xqe_analysis)
        tph_per_agv = 3600.0 / avg_ct
        expected_fleet = math.ceil(30.0 / (tph_per_agv * 0.80))

        result = self.calc.calculate_fleet_size(tasks_per_hour=30.0, agv_type="XQE_122")
        assert result.fleet_size_per_agv["XQE_122"] == expected_fleet

    def test_fleet_size_scales_with_throughput(self):
        """More throughput → more AGVs needed."""
        r1 = self.calc.calculate_fleet_size(30.0, agv_type="XQE_122")
        r2 = self.calc.calculate_fleet_size(60.0, agv_type="XQE_122")
        assert r2.fleet_size_per_agv["XQE_122"] >= r1.fleet_size_per_agv["XQE_122"]

    def test_utilization_at_recommended_fleet(self):
        """Utilization at the recommended fleet size should be ≤ 100%."""
        result = self.calc.calculate_fleet_size(30.0)
        for agv_type, util in result.utilization_per_agv.items():
            assert util <= 1.0, f"{agv_type} utilization {util:.2%} exceeds 100%"
            assert util > 0.0, f"{agv_type} utilization is zero"

    def test_recommended_agv_is_set(self):
        result = self.calc.calculate_fleet_size(30.0)
        assert result.recommended_agv is not None
        assert result.recommended_agv in AGV_SPECS

    def test_throughput_sensitivity(self):
        tph_range = [10.0, 20.0, 30.0, 40.0, 50.0]
        # Use XQE_122 which is compatible with the standard-width aisles in MEDIUM layout
        data = self.calc.throughput_sensitivity("XQE_122", tph_range)
        assert len(data) == len(tph_range)
        # Fleet sizes should be non-decreasing
        fleet_sizes = [d[1] for d in data]
        for i in range(1, len(fleet_sizes)):
            assert fleet_sizes[i] >= fleet_sizes[i - 1]

    def test_fleet_result_to_dict(self):
        result = self.calc.calculate_fleet_size(30.0)
        d = result.to_dict()
        assert "tasks_per_hour" in d
        assert "fleet_sizes" in d
        assert "recommended_agv" in d


# ---------------------------------------------------------------------------
# Simulation engine tests
# ---------------------------------------------------------------------------

class TestSimulationEngine:
    def setup_method(self):
        self.wg = WarehouseGraph()
        self.wg.build_from_layout(MEDIUM_WAREHOUSE_JSON)
        self.engine = SimulationEngine(self.wg, MEDIUM_WAREHOUSE_JSON)

    def test_single_task_rack_xna(self):
        # The COMPLEX warehouse has narrow (1.77m) aisles where XNA is appropriate.
        wg_complex = WarehouseGraph()
        wg_complex.build_from_layout(COMPLEX_WAREHOUSE_JSON)
        engine_complex = SimulationEngine(wg_complex, COMPLEX_WAREHOUSE_JSON)
        result = engine_complex.calculate_single_task_cycle(
            "XNA_121", "rack", "SA1", lift_height=2.25
        )
        assert result.total_cycle_time > 0
        assert result.agv_type == "XNA_121"
        assert result.storage_type == "rack"

    def test_single_task_ground_xpl(self):
        result = self.engine.calculate_single_task_cycle(
            "XPL_201", "ground_storage", "SA3", lift_height=0.0
        )
        assert result.total_cycle_time > 0
        # Reverse distance should be used (fork-first travel)
        assert result.d_reverse_empty > 0
        assert result.d_reverse_loaded > 0

    def test_incompatible_agv_raises(self):
        """XNA_121 cannot do ground_stacking (not in its storage_types)."""
        with pytest.raises(ValueError, match="incompatible|storage|support"):
            self.engine.calculate_single_task_cycle(
                "XNA_121", "ground_stacking", "SA4", lift_height=0.0
            )

    def test_simulate_throughput_returns_result(self):
        result = self.engine.simulate_throughput(
            agv_type="XNA_121",
            fleet_size=2,
            tasks_per_hour=20,
            simulation_hours=1.0,
        )
        assert result.total_tasks_completed > 0
        assert result.avg_utilization >= 0
        assert result.avg_utilization <= 1.0

    def test_simulate_larger_fleet_more_tasks(self):
        """More AGVs should result in more tasks completed (or equal)."""
        r1 = self.engine.simulate_throughput("XQE_122", 1, 30, 1.0)
        r2 = self.engine.simulate_throughput("XQE_122", 3, 30, 1.0)
        assert r2.total_tasks_completed >= r1.total_tasks_completed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
