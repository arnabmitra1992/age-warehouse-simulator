"""
Tests for the PR-2 workflow-based fleet sizing.

Covers:
  - CycleCalculator (all_cycle_times)
  - FleetSizer (size_fleet)
  - FleetSizingReport structure
  - Simulator.run()
"""

import math
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.warehouse_layout import WarehouseLayout
from src.cycle_calculator import CycleCalculator
from src.fleet_sizer import FleetSizer, FleetSizingReport, WorkflowFleetResult
from src.simulator import Simulator


# ---------------------------------------------------------------------------
# Shared config fixture
# ---------------------------------------------------------------------------

CONFIG = {
    "warehouse": {
        "name": "Test Fleet Warehouse",
        "length_mm": 50000,
        "width_mm": 30000,
        "head_aisle_width_mm": 4000,
    },
    "docks": {
        "inbound":  {"x_mm": 0,     "y_mm": 15000},
        "outbound": {"x_mm": 50000, "y_mm": 15000},
    },
    "rest_area":    {"x_mm": 25000, "y_mm": 0},
    "handover_zone":{"x_mm": 25000, "y_mm": 30000},
    "storage_aisles": [
        {
            "name": "Rack 1",
            "type": "rack",
            "width_mm": 2840,
            "length_mm": 25000,
            "entry_x_mm": 8000,
            "entry_y_mm": 8000,
            "rack_length_mm": 18000,
            "shelf_heights": [1.3, 2.6, 3.9, 4.5],
        },
        {
            "name": "Stacking 1",
            "type": "ground_stacking",
            "width_mm": 8000,
            "length_mm": 15000,
            "entry_x_mm": 30000,
            "entry_y_mm": 8000,
            "box_width_mm": 800,
            "box_length_mm": 1200,
            "box_height_mm": 1000,
        },
    ],
    "throughput": {
        "daily_pallets": 800,
        "operating_hours": 16,
        "xpl_percentage": 30,
        "xqe_rack_percentage": 50,
        "xqe_stacking_percentage": 20,
        "utilization_target": 0.75,
    },
}


# ---------------------------------------------------------------------------
# CycleCalculator tests
# ---------------------------------------------------------------------------

class TestCycleCalculator:

    def setup_method(self):
        self.layout = WarehouseLayout.from_dict(CONFIG)
        self.calc = CycleCalculator(self.layout)

    def test_handover_cycle_returns_result(self):
        result = self.calc.handover_cycle()
        assert result.total_cycle_time > 0

    def test_rack_storage_cycle_returns_result(self):
        rack_aisle = self.layout.rack_aisles()[0]
        result = self.calc.rack_storage_cycle(rack_aisle)
        assert result.total_cycle_time > 0

    def test_rack_storage_cycle_wrong_type_raises(self):
        stacking_aisle = self.layout.ground_stacking_aisles()[0]
        with pytest.raises(ValueError, match="rack"):
            self.calc.rack_storage_cycle(stacking_aisle)

    def test_ground_stacking_cycle_returns_result(self):
        stacking_aisle = self.layout.ground_stacking_aisles()[0]
        result = self.calc.ground_stacking_cycle(stacking_aisle)
        assert result.total_cycle_time > 0

    def test_ground_stacking_cycle_wrong_type_raises(self):
        rack_aisle = self.layout.rack_aisles()[0]
        with pytest.raises(ValueError, match="ground_stacking"):
            self.calc.ground_stacking_cycle(rack_aisle)

    def test_all_cycle_times_returns_dict(self):
        times = self.calc.all_cycle_times()
        assert isinstance(times, dict)
        assert len(times) > 0

    def test_all_cycle_times_has_handover(self):
        times = self.calc.all_cycle_times()
        assert "XPL_201_Handover" in times
        assert times["XPL_201_Handover"] > 0

    def test_all_cycle_times_has_rack(self):
        times = self.calc.all_cycle_times()
        rack_keys = [k for k in times if "Rack" in k]
        assert len(rack_keys) == 1

    def test_all_cycle_times_has_stacking(self):
        times = self.calc.all_cycle_times()
        stack_keys = [k for k in times if "Stacking" in k]
        assert len(stack_keys) == 1

    def test_all_cycle_times_positive(self):
        for key, ct in self.calc.all_cycle_times().items():
            assert ct > 0, f"Cycle time for '{key}' is not positive: {ct}"


# ---------------------------------------------------------------------------
# FleetSizer tests
# ---------------------------------------------------------------------------

class TestFleetSizer:

    def setup_method(self):
        self.layout = WarehouseLayout.from_dict(CONFIG)
        self.sizer = FleetSizer(self.layout)

    def test_size_fleet_returns_report(self):
        report = self.sizer.size_fleet(tasks_per_hour=50.0)
        assert isinstance(report, FleetSizingReport)

    def test_report_has_workflow_results(self):
        report = self.sizer.size_fleet(tasks_per_hour=50.0)
        assert len(report.workflow_results) > 0

    def test_total_fleet_is_positive(self):
        report = self.sizer.size_fleet(tasks_per_hour=50.0)
        assert report.total_fleet >= 1

    def test_fleet_scales_with_throughput(self):
        """Higher throughput → more AGVs needed."""
        r1 = self.sizer.size_fleet(tasks_per_hour=10.0)
        r2 = self.sizer.size_fleet(tasks_per_hour=100.0)
        assert r2.total_fleet >= r1.total_fleet

    def test_utilization_at_most_100_pct(self):
        report = self.sizer.size_fleet(tasks_per_hour=50.0)
        for r in report.workflow_results:
            assert r.achieved_utilization <= 1.0, (
                f"Utilization for {r.workflow_key} exceeds 100%: "
                f"{r.achieved_utilization:.2%}"
            )

    def test_utilization_positive(self):
        report = self.sizer.size_fleet(tasks_per_hour=50.0)
        for r in report.workflow_results:
            assert r.achieved_utilization > 0

    def test_fleet_size_formula_handover(self):
        """fleet = ceil(tph_workflow / (tph_per_agv × utilization))."""
        times = CycleCalculator(self.layout).all_cycle_times()
        ct_handover = times.get("XPL_201_Handover", 0)
        if ct_handover <= 0:
            pytest.skip("No handover workflow in test config")

        report = self.sizer.size_fleet(tasks_per_hour=60.0)
        hw_result = next(
            (r for r in report.workflow_results if r.workflow_key == "XPL_201_Handover"),
            None,
        )
        assert hw_result is not None

        tph_per_agv = 3600.0 / ct_handover
        expected_fleet = math.ceil(
            hw_result.tasks_per_hour / (tph_per_agv * self.sizer.utilization_target)
        )
        assert hw_result.fleet_size == expected_fleet

    def test_throughput_from_config(self):
        """Default throughput = daily_pallets / operating_hours = 800/16 = 50."""
        report = self.sizer.size_fleet()  # no override
        assert abs(report.total_tasks_per_hour - 50.0) < 0.01

    def test_to_dict_keys(self):
        report = self.sizer.size_fleet(tasks_per_hour=40.0)
        d = report.to_dict()
        assert "warehouse" in d
        assert "total_fleet" in d
        assert "workflows" in d
        assert "cycle_times_s" in d

    def test_utilization_target_custom(self):
        """Custom utilization target is respected."""
        sizer_80 = FleetSizer(self.layout, utilization_target=0.80)
        sizer_50 = FleetSizer(self.layout, utilization_target=0.50)
        r_80 = sizer_80.size_fleet(tasks_per_hour=40.0)
        r_50 = sizer_50.size_fleet(tasks_per_hour=40.0)
        # Lower utilization target → more AGVs needed
        assert r_50.total_fleet >= r_80.total_fleet


# ---------------------------------------------------------------------------
# Simulator integration tests
# ---------------------------------------------------------------------------

class TestSimulatorIntegration:

    def setup_method(self):
        self.layout = WarehouseLayout.from_dict(CONFIG)
        self.sim = Simulator.from_layout(self.layout)

    def test_run_returns_report(self):
        report = self.sim.run(tasks_per_hour=30.0)
        assert isinstance(report, FleetSizingReport)
        assert report.total_fleet >= 1

    def test_run_default_throughput(self):
        report = self.sim.run()
        assert report.total_tasks_per_hour > 0

    def test_run_with_config_file(self, tmp_path):
        import json
        cfg_path = tmp_path / "sim_config.json"
        cfg_path.write_text(json.dumps(CONFIG))
        sim = Simulator(str(cfg_path))
        report = sim.run(tasks_per_hour=50.0)
        assert report.total_fleet >= 1

    def test_print_report_runs_without_error(self, capsys):
        report = self.sim.run(tasks_per_hour=40.0)
        self.sim.print_report(report)
        captured = capsys.readouterr()
        assert "Fleet" in captured.out or "fleet" in captured.out.lower()
        assert report.warehouse_name in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
