"""
Tests for fleet sizing calculations and simulator integration.
"""
import math
import json
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.fleet_sizer import (
    ThroughputConfig,
    FleetSizeResult,
    calculate_fleet_size,
    throughput_config_from_dict,
)
from src.simulator import WarehouseSimulator, load_config


# ---------------------------------------------------------------------------
# Fleet sizing unit tests
# ---------------------------------------------------------------------------

class TestCalculateFleetSize:
    def test_basic_fleet_calculation(self):
        result = calculate_fleet_size(
            daily_pallets=1000,
            avg_cycle_time_s=300,
            operating_hours=16,
            utilization_target=0.75,
        )
        # expected = ceil(1000 * 300 / (16 * 3600 * 0.75)) = ceil(300000/43200) = ceil(6.94) = 7
        assert result.fleet_size == 7

    def test_zero_pallets_returns_zero_fleet(self):
        result = calculate_fleet_size(
            daily_pallets=0,
            avg_cycle_time_s=300,
            operating_hours=16,
            utilization_target=0.75,
        )
        assert result.fleet_size == 0

    def test_zero_cycle_time_returns_zero_fleet(self):
        result = calculate_fleet_size(
            daily_pallets=1000,
            avg_cycle_time_s=0,
            operating_hours=16,
            utilization_target=0.75,
        )
        assert result.fleet_size == 0

    def test_fleet_size_is_ceiling(self):
        # With exactly 6.94 vehicles needed, must round up to 7
        result = calculate_fleet_size(
            daily_pallets=1000,
            avg_cycle_time_s=300,
            operating_hours=16,
            utilization_target=0.75,
        )
        assert result.fleet_size == math.ceil(1000 * 300 / (16 * 3600 * 0.75))

    def test_higher_throughput_needs_more_vehicles(self):
        low = calculate_fleet_size(500, 300, 16, 0.75)
        high = calculate_fleet_size(2000, 300, 16, 0.75)
        assert high.fleet_size > low.fleet_size

    def test_longer_cycle_needs_more_vehicles(self):
        short = calculate_fleet_size(1000, 200, 16, 0.75)
        long_ = calculate_fleet_size(1000, 600, 16, 0.75)
        assert long_.fleet_size > short.fleet_size

    def test_more_operating_hours_needs_fewer_vehicles(self):
        short_shift = calculate_fleet_size(1000, 300, 8, 0.75)
        long_shift = calculate_fleet_size(1000, 300, 16, 0.75)
        assert long_shift.fleet_size <= short_shift.fleet_size

    def test_utilization_percent_range(self):
        result = calculate_fleet_size(1000, 300, 16, 0.75)
        assert 0 < result.utilization_percent <= 100

    def test_throughput_per_hour_positive(self):
        result = calculate_fleet_size(1000, 300, 16, 0.75)
        assert result.throughput_per_hour > 0

    def test_result_metadata(self):
        result = calculate_fleet_size(
            500, 200, 10, 0.8,
            vehicle_type="XPL_201",
            workflow="Handover",
        )
        assert result.vehicle_type == "XPL_201"
        assert result.workflow == "Handover"

    def test_summary_string(self):
        result = calculate_fleet_size(1000, 300, 16, 0.75, "XQE_122", "Rack")
        summary = result.summary()
        assert "XQE_122" in summary
        assert "Rack" in summary


class TestThroughputConfig:
    def test_daily_pallet_splits(self):
        cfg = ThroughputConfig(
            total_daily_pallets=1000,
            xpl201_percentage=30,
            xqe_rack_percentage=50,
            xqe_stacking_percentage=20,
        )
        assert cfg.xpl201_daily_pallets == 300
        assert cfg.xqe_rack_daily_pallets == 500
        assert cfg.xqe_stacking_daily_pallets == 200

    def test_validation_passes_when_100_percent(self):
        cfg = ThroughputConfig(
            xpl201_percentage=30,
            xqe_rack_percentage=50,
            xqe_stacking_percentage=20,
        )
        cfg.validate()  # should not raise

    def test_validation_fails_when_not_100_percent(self):
        cfg = ThroughputConfig(
            xpl201_percentage=40,
            xqe_rack_percentage=50,
            xqe_stacking_percentage=20,
        )
        with pytest.raises(ValueError):
            cfg.validate()

    def test_from_dict(self):
        d = {
            "Total_Daily_Pallets": 500,
            "Operating_Hours": 8,
            "XPL_201_Percentage": 25,
            "XQE_Rack_Percentage": 50,
            "XQE_Stacking_Percentage": 25,
            "Utilization_Target": 0.8,
        }
        cfg = throughput_config_from_dict(d)
        assert cfg.total_daily_pallets == 500
        assert cfg.operating_hours == 8
        assert cfg.utilization_target == 0.8


# ---------------------------------------------------------------------------
# Simulator integration tests
# ---------------------------------------------------------------------------

MEDIUM_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "config_medium.json"
)
SMALL_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "config_small.json"
)
LARGE_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "config_large.json"
)


def _load_config(path):
    with open(path) as f:
        return json.load(f)


class TestSimulatorIntegration:
    def test_medium_config_runs(self):
        config = _load_config(MEDIUM_CONFIG_PATH)
        sim = WarehouseSimulator(config)
        results = sim.run()
        assert results.xpl_cycle.total_time_s > 0
        assert results.xqe_rack_cycle.total_time_s > 0
        assert results.xqe_stack_cycle.total_time_s > 0

    def test_medium_config_fleet_sizes_positive(self):
        config = _load_config(MEDIUM_CONFIG_PATH)
        sim = WarehouseSimulator(config)
        results = sim.run()
        assert results.xpl_fleet.fleet_size > 0
        assert results.xqe_rack_fleet.fleet_size > 0
        assert results.xqe_stack_fleet.fleet_size > 0

    def test_total_fleet_is_sum(self):
        config = _load_config(MEDIUM_CONFIG_PATH)
        sim = WarehouseSimulator(config)
        results = sim.run()
        expected = (
            results.xpl_fleet.fleet_size
            + results.xqe_rack_fleet.fleet_size
            + results.xqe_stack_fleet.fleet_size
        )
        assert results.total_fleet_size == expected

    def test_to_dict_structure(self):
        config = _load_config(MEDIUM_CONFIG_PATH)
        sim = WarehouseSimulator(config)
        results = sim.run()
        d = results.to_dict()
        assert "rack_capacity" in d
        assert "stacking_capacity" in d
        assert "cycle_times_s" in d
        assert "fleet_sizes" in d

    def test_to_json_valid(self):
        config = _load_config(MEDIUM_CONFIG_PATH)
        sim = WarehouseSimulator(config)
        results = sim.run()
        parsed = json.loads(results.to_json())
        assert parsed["fleet_sizes"]["total"] == results.total_fleet_size

    def test_to_csv_valid(self):
        config = _load_config(MEDIUM_CONFIG_PATH)
        sim = WarehouseSimulator(config)
        results = sim.run()
        csv_str = results.to_csv()
        assert "cycle_times_s.xpl201_handover" in csv_str

    def test_full_report_contains_vehicle_names(self):
        config = _load_config(MEDIUM_CONFIG_PATH)
        sim = WarehouseSimulator(config)
        results = sim.run()
        report = sim.full_report(results)
        assert "XPL_201" in report
        assert "XQE_122" in report

    def test_small_config_runs(self):
        config = _load_config(SMALL_CONFIG_PATH)
        sim = WarehouseSimulator(config)
        results = sim.run()
        assert results.total_fleet_size > 0

    def test_large_config_more_fleet_than_small(self):
        small_cfg = _load_config(SMALL_CONFIG_PATH)
        large_cfg = _load_config(LARGE_CONFIG_PATH)
        small_sim = WarehouseSimulator(small_cfg)
        large_sim = WarehouseSimulator(large_cfg)
        small_results = small_sim.run()
        large_results = large_sim.run()
        assert large_results.total_fleet_size > small_results.total_fleet_size

    def test_rack_capacity_positive(self):
        config = _load_config(MEDIUM_CONFIG_PATH)
        sim = WarehouseSimulator(config)
        results = sim.run()
        assert results.rack_config.total_positions > 0

    def test_stacking_capacity_positive(self):
        config = _load_config(MEDIUM_CONFIG_PATH)
        sim = WarehouseSimulator(config)
        results = sim.run()
        assert results.stacking_config.total_positions > 0
