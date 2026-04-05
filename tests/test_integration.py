"""
End-to-end integration tests for the PR-2 pipeline.
"""
import json
import os
import pytest
from src.warehouse_layout import load_config, parse_config, WarehouseConfig, AisleConfig
from src.simulator import WarehouseSimulator, is_mm_config
from src.fleet_sizer import FleetSizer
from src.cycle_calculator import CycleCalculator


SMALL_CONFIG = {
    "name": "Integration Test Warehouse",
    "width_mm": 30000,
    "length_mm": 50000,
    "head_aisle_width_mm": 4000,
    "inbound_docks": 2,
    "outbound_docks": 2,
    "aisles": [
        {
            "name": "SA1",
            "type": "rack",
            "width_mm": 2840,
            "depth_mm": 15000,
            "num_positions": 30,
            "shelf_heights_mm": [0, 1200, 2400, 3600]
        },
        {
            "name": "SA2",
            "type": "ground_stacking",
            "width_mm": 3000,
            "depth_mm": 15000,
            "stacking_levels": 3
        },
        {
            "name": "SA3",
            "type": "handover",
            "width_mm": 2840,
            "depth_mm": 10000
        }
    ],
    "throughput": {
        "pallets_per_day": 500,
        "operating_hours": 16
    },
    "utilization_target": 0.80
}


class TestWarehouseSimulatorIntegration:
    def test_from_dict(self):
        sim = WarehouseSimulator.from_dict(SMALL_CONFIG)
        assert sim.config.name == "Integration Test Warehouse"

    def test_run_returns_result(self):
        sim = WarehouseSimulator.from_dict(SMALL_CONFIG)
        result = sim.run(verbose=False)
        assert result is not None
        assert result.total_agvs >= 1

    def test_run_has_aisle_results(self):
        sim = WarehouseSimulator.from_dict(SMALL_CONFIG)
        result = sim.run(verbose=False)
        assert len(result.aisle_results) == 3

    def test_get_cycle_times(self):
        sim = WarehouseSimulator.from_dict(SMALL_CONFIG)
        ct = sim.get_cycle_times()
        assert "SA1" in ct
        assert "SA2" in ct
        assert "SA3" in ct

    def test_cycle_times_have_avg(self):
        sim = WarehouseSimulator.from_dict(SMALL_CONFIG)
        ct = sim.get_cycle_times()
        for name, data in ct.items():
            assert "avg_cycle_time_s" in data
            assert data["avg_cycle_time_s"] > 0

    def test_is_mm_config_true(self):
        assert is_mm_config(SMALL_CONFIG) is True

    def test_is_mm_config_false_for_legacy(self):
        legacy = {"storage_aisles": [{"name": "SA1", "width": 2.84}]}
        assert is_mm_config(legacy) is False

    def test_parse_config(self):
        config = parse_config(SMALL_CONFIG)
        assert isinstance(config, WarehouseConfig)
        assert len(config.aisles) == 3
        assert config.aisles[0].name == "SA1"

    def test_aisle_width_conversion(self):
        config = parse_config(SMALL_CONFIG)
        sa1 = config.aisles[0]
        assert sa1.width_mm == pytest.approx(2840.0)
        assert sa1.width_m == pytest.approx(2.84)

    def test_load_config_from_file(self, tmp_path):
        config_path = tmp_path / "test_config.json"
        config_path.write_text(json.dumps(SMALL_CONFIG))
        config = load_config(str(config_path))
        assert config.name == "Integration Test Warehouse"

    def test_run_with_custom_throughput(self):
        sim = WarehouseSimulator.from_dict(SMALL_CONFIG)
        result = sim.run(throughput_per_hour=50.0, verbose=False)
        assert result.throughput_per_hour == pytest.approx(50.0)

    def test_config_json_files_loadable(self):
        base = os.path.dirname(os.path.dirname(__file__))
        config_dir = os.path.join(base, "config")
        if not os.path.exists(config_dir):
            pytest.skip("config/ directory not found")
        for fname in ["config_small.json", "config_medium.json", "config_large.json"]:
            path = os.path.join(config_dir, fname)
            if os.path.exists(path):
                config = load_config(path)
                assert config.name
                assert len(config.aisles) >= 1
