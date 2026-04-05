"""
Integration tests – complete simulator pipeline from config to fleet report.
"""

import sys
import os
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.simulator import WarehouseSimulator
from src.rack_storage import RackStorage
from src.ground_stacking import GroundStackingMultipleLevels
from src.warehouse_layout import WarehouseLayoutLoader


# Config file directory
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")


# ---------------------------------------------------------------------------
# Config file tests
# ---------------------------------------------------------------------------

class TestConfigFiles:
    @pytest.mark.parametrize("filename", [
        "config_small.json",
        "config_medium.json",
        "config_large.json",
        "config_template.json",
    ])
    def test_config_file_exists(self, filename):
        path = os.path.join(CONFIG_DIR, filename)
        assert os.path.isfile(path), f"Missing config file: {filename}"

    @pytest.mark.parametrize("filename", [
        "config_small.json",
        "config_medium.json",
        "config_large.json",
    ])
    def test_config_file_parseable(self, filename):
        path = os.path.join(CONFIG_DIR, filename)
        cfg = WarehouseLayoutLoader().load(path)
        assert cfg.name != ""

    def test_small_config_dimensions(self):
        path = os.path.join(CONFIG_DIR, "config_small.json")
        cfg = WarehouseLayoutLoader().load(path)
        assert cfg.width_m == pytest.approx(20.0)
        assert cfg.length_m == pytest.approx(30.0)

    def test_medium_config_dimensions(self):
        path = os.path.join(CONFIG_DIR, "config_medium.json")
        cfg = WarehouseLayoutLoader().load(path)
        assert cfg.width_m == pytest.approx(60.0)
        assert cfg.length_m == pytest.approx(80.0)

    def test_large_config_dimensions(self):
        path = os.path.join(CONFIG_DIR, "config_large.json")
        cfg = WarehouseLayoutLoader().load(path)
        assert cfg.width_m == pytest.approx(100.0)
        assert cfg.length_m == pytest.approx(120.0)


# ---------------------------------------------------------------------------
# Full simulator pipeline tests
# ---------------------------------------------------------------------------

class TestSmallSimulator:
    def setup_method(self):
        path = os.path.join(CONFIG_DIR, "config_small.json")
        self.sim = WarehouseSimulator(config_path=path)
        self.report = self.sim.run()

    def test_report_valid(self):
        assert self.report.is_valid

    def test_has_fleet_requirements(self):
        assert len(self.report.fleet_requirements) > 0

    def test_inbound_throughput_override(self):
        report = self.sim.run(inbound_tasks=200, outbound_tasks=150)
        assert report.is_valid

    def test_cycle_time_positive_for_all_workflows(self):
        for wct in [
            self.report.inbound_rack_wct,
            self.report.inbound_stacking_wct,
            self.report.outbound_rack_wct,
            self.report.outbound_stacking_wct,
        ]:
            if wct is not None:
                assert wct.avg_cycle_time_s > 0


class TestMediumSimulator:
    def setup_method(self):
        path = os.path.join(CONFIG_DIR, "config_medium.json")
        self.sim = WarehouseSimulator(config_path=path)
        self.report = self.sim.run()

    def test_report_valid(self):
        assert self.report.is_valid

    def test_outbound_uses_handover(self):
        """Medium config has 55m outbound distance → handover expected."""
        assert self.report.outbound_rack_wct is not None
        assert self.report.outbound_rack_wct.uses_handover is True

    def test_inbound_no_handover(self):
        """Medium config has 30m inbound distance → no handover."""
        assert self.report.inbound_rack_wct is not None
        assert self.report.inbound_rack_wct.uses_handover is False


class TestLargeSimulator:
    def setup_method(self):
        path = os.path.join(CONFIG_DIR, "config_large.json")
        self.sim = WarehouseSimulator(config_path=path)
        self.report = self.sim.run()

    def test_report_valid(self):
        assert self.report.is_valid

    def test_all_workflows_use_handover(self):
        """Large warehouse: all distances ≥ 50m → all workflows use handover."""
        for wct in [
            self.report.inbound_rack_wct,
            self.report.outbound_rack_wct,
            self.report.inbound_stacking_wct,
            self.report.outbound_stacking_wct,
        ]:
            if wct is not None:
                assert wct.uses_handover is True, \
                    f"Expected handover for {wct.direction}/{wct.storage_type}"

    def test_has_xpl_fleet(self):
        assert self.report.total_xpl_fleet > 0

    def test_has_xqe_fleet(self):
        assert self.report.total_xqe_fleet > 0


class TestSimulatorFromDict:
    def test_dict_config_works(self):
        raw = {
            "warehouse": {"name": "Dict WH", "width_mm": 20000, "length_mm": 20000},
            "inbound": {
                "distance_to_handover_mm": 5000,
                "distance_to_rack_handover_mm": 5000,
                "distance_to_stacking_handover_mm": 5000,
            },
            "outbound": {
                "rack_handover_to_outbound_mm": 5000,
                "stacking_handover_to_outbound_mm": 5000,
                "distance_from_handover_mm": 5000,
            },
            "distances": {"handover_to_rack_mm": 3000, "handover_to_stacking_mm": 3000},
            "rack_storage": {
                "aisle_width_mm": 2840,
                "aisle_depth_mm": 10000,
                "pallet_spacing_mm": 950,
                "shelves": [{"height_mm": 300}, {"height_mm": 1500}],
            },
            "ground_stacking": {
                "rows": 3, "cols": 3, "levels": 2,
                "level_height_mm": 1200, "area_length_mm": 5000, "area_width_mm": 5000,
            },
            "workflow": {"rack_fraction": 0.6, "stacking_fraction": 0.4},
            "throughput": {
                "inbound": {"daily_tasks": 50, "operating_hours": 8.0, "utilization": 0.75},
                "outbound": {"daily_tasks": 50, "operating_hours": 8.0, "utilization": 0.75},
            },
        }
        sim = WarehouseSimulator(config_dict=raw)
        report = sim.run()
        assert report.is_valid


# ---------------------------------------------------------------------------
# Rack storage integration
# ---------------------------------------------------------------------------

class TestRackStorageIntegration:
    def test_capacity_from_config(self):
        path = os.path.join(CONFIG_DIR, "config_small.json")
        cfg = WarehouseLayoutLoader().load(path)
        rs = RackStorage(
            aisle_depth_m=cfg.rack.aisle_depth_m,
            pallet_spacing_m=cfg.rack.pallet_spacing_m,
            shelves=cfg.rack.shelves,
        )
        assert rs.total_capacity > 0
        assert rs.num_shelves == 4

    def test_avg_cycle_distances_positive(self):
        rs = RackStorage(aisle_depth_m=20.0, pallet_spacing_m=0.95,
                         shelves=[{"height_mm": 300}, {"height_mm": 1500}])
        depth, height = rs.avg_cycle_distances()
        assert depth > 0
        assert height > 0

    def test_bays_created_from_depth(self):
        rs = RackStorage(aisle_depth_m=5.0, pallet_spacing_m=1.0)
        assert rs.num_bays >= 1


# ---------------------------------------------------------------------------
# Ground stacking integration
# ---------------------------------------------------------------------------

class TestGroundStackingIntegration:
    def test_capacity_calculation(self):
        gs = GroundStackingMultipleLevels(
            rows=5, cols=4, levels=3,
            level_height_m=1.2,
            area_length_m=10.0,
            area_width_m=8.0,
        )
        assert gs.total_capacity == 5 * 4 * 3

    def test_max_height(self):
        gs = GroundStackingMultipleLevels(5, 4, 3, 1.2, 10.0, 8.0)
        assert gs.max_stack_height_m == pytest.approx(3 * 1.2)

    def test_avg_depth_positive(self):
        gs = GroundStackingMultipleLevels(5, 4, 3, 1.2, 10.0, 8.0)
        assert gs.avg_depth_m > 0

    def test_avg_lift_height_positive(self):
        gs = GroundStackingMultipleLevels(5, 4, 3, 1.2, 10.0, 8.0)
        assert gs.avg_lift_height_m > 0

    def test_xqe_only_attribute(self):
        from src.ground_stacking import GroundStackingMultipleLevels as GS
        assert GS.AGV_TYPE == "XQE_122"


# ---------------------------------------------------------------------------
# Save report
# ---------------------------------------------------------------------------

class TestSaveReport:
    def test_save_report_creates_json(self, tmp_path):
        path = os.path.join(CONFIG_DIR, "config_small.json")
        sim = WarehouseSimulator(config_path=path)
        report = sim.run()
        out = sim.save_report(report, output_dir=str(tmp_path))
        assert os.path.isfile(out)
        with open(out) as fh:
            data = json.load(fh)
        assert "fleet" in data
