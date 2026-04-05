"""
Tests for fleet sizing calculations.
"""

import sys
import os
import math
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.warehouse_layout import WarehouseLayoutLoader
from src.fleet_sizer import FleetSizer, FleetRequirement, FleetSizingReport


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _small_config() -> dict:
    """Small warehouse: standard aisle, short distances → no handover."""
    return {
        "warehouse": {"name": "Small Test WH", "width_mm": 20000, "length_mm": 30000},
        "inbound": {
            "distance_to_handover_mm": 8000,
            "distance_to_rack_handover_mm": 8000,
            "distance_to_stacking_handover_mm": 10000,
        },
        "outbound": {
            "rack_handover_to_outbound_mm": 8000,
            "stacking_handover_to_outbound_mm": 10000,
            "distance_from_handover_mm": 8000,
        },
        "distances": {"handover_to_rack_mm": 4000, "handover_to_stacking_mm": 5000},
        "rack_storage": {
            "aisle_width_mm": 2840,
            "aisle_depth_mm": 15000,
            "pallet_spacing_mm": 950,
            "shelves": [
                {"height_mm": 300}, {"height_mm": 1500},
                {"height_mm": 3000}, {"height_mm": 4500},
            ],
        },
        "ground_stacking": {
            "rows": 4, "cols": 3, "levels": 3,
            "level_height_mm": 1200, "area_length_mm": 8000, "area_width_mm": 6000,
        },
        "workflow": {"rack_fraction": 0.6, "stacking_fraction": 0.4},
        "throughput": {
            "inbound": {"daily_tasks": 300, "operating_hours": 8.0, "utilization": 0.75},
            "outbound": {"daily_tasks": 200, "operating_hours": 8.0, "utilization": 0.75},
        },
    }


def _large_config() -> dict:
    """Large warehouse: all distances ≥ 50m → full handover."""
    return {
        "warehouse": {"name": "Large Test WH", "width_mm": 100000, "length_mm": 120000},
        "inbound": {
            "distance_to_handover_mm": 60000,
            "distance_to_rack_handover_mm": 60000,
            "distance_to_stacking_handover_mm": 65000,
        },
        "outbound": {
            "rack_handover_to_outbound_mm": 70000,
            "stacking_handover_to_outbound_mm": 75000,
            "distance_from_handover_mm": 70000,
        },
        "distances": {"handover_to_rack_mm": 15000, "handover_to_stacking_mm": 18000},
        "rack_storage": {
            "aisle_width_mm": 2840,
            "aisle_depth_mm": 50000,
            "pallet_spacing_mm": 950,
            "shelves": [
                {"height_mm": 300}, {"height_mm": 1500},
                {"height_mm": 3000}, {"height_mm": 4500},
            ],
        },
        "ground_stacking": {
            "rows": 10, "cols": 8, "levels": 4,
            "level_height_mm": 1200, "area_length_mm": 25000, "area_width_mm": 20000,
        },
        "workflow": {"rack_fraction": 0.6, "stacking_fraction": 0.4},
        "throughput": {
            "inbound": {"daily_tasks": 1800, "operating_hours": 10.0, "utilization": 0.80},
            "outbound": {"daily_tasks": 1200, "operating_hours": 10.0, "utilization": 0.80},
        },
    }


def _xsc_config() -> dict:
    """Warehouse with XSC pending aisle (2.3m aisle width)."""
    cfg = _small_config()
    cfg["rack_storage"]["aisle_width_mm"] = 2300
    return cfg


def _narrow_config() -> dict:
    """Warehouse with narrow aisle (XNA required)."""
    cfg = _small_config()
    cfg["rack_storage"]["aisle_width_mm"] = 1900
    return cfg


# ---------------------------------------------------------------------------
# Fleet sizing formula
# ---------------------------------------------------------------------------

class TestFleetFormula:
    def test_formula_manual(self):
        """fleet = ceil( (tasks × cycle_s) / (hours × 3600 × util) )"""
        tasks = 300
        cycle_s = 200.0
        hours = 8.0
        util = 0.75
        req = FleetSizer._req("XQE_122", "inbound", "rack", tasks, hours, util, cycle_s)
        expected = math.ceil((tasks * cycle_s) / (hours * 3600 * util))
        assert req.fleet_size == expected

    def test_fleet_scales_with_tasks(self):
        """More tasks → more AGVs (or same if capacity allows)."""
        cfg = WarehouseLayoutLoader().load_dict(_small_config())
        r_low = FleetSizer(cfg, inbound_tasks_per_day=100).calculate()
        r_high = FleetSizer(cfg, inbound_tasks_per_day=500).calculate()

        low_xqe = sum(r.fleet_size for r in r_low.fleet_requirements
                      if r.agv_type == "XQE_122" and r.direction == "inbound")
        high_xqe = sum(r.fleet_size for r in r_high.fleet_requirements
                       if r.agv_type == "XQE_122" and r.direction == "inbound")
        assert high_xqe >= low_xqe

    def test_fleet_positive_for_nonzero_tasks(self):
        cfg = WarehouseLayoutLoader().load_dict(_small_config())
        report = FleetSizer(cfg, inbound_tasks_per_day=100).calculate()
        for req in report.fleet_requirements:
            assert req.fleet_size >= 1

    def test_utilization_within_bounds(self):
        cfg = WarehouseLayoutLoader().load_dict(_small_config())
        report = FleetSizer(cfg).calculate()
        for req in report.fleet_requirements:
            assert 0.0 < req.actual_utilization <= 1.0


class TestSmallWarehouseFleet:
    def setup_method(self):
        cfg = WarehouseLayoutLoader().load_dict(_small_config())
        self.report = FleetSizer(cfg).calculate()

    def test_report_valid(self):
        assert self.report.is_valid

    def test_no_errors(self):
        assert len(self.report.errors) == 0

    def test_has_inbound_rack_workflow(self):
        assert self.report.inbound_rack_wct is not None

    def test_has_inbound_stacking_workflow(self):
        assert self.report.inbound_stacking_wct is not None

    def test_has_outbound_rack_workflow(self):
        assert self.report.outbound_rack_wct is not None

    def test_has_outbound_stacking_workflow(self):
        assert self.report.outbound_stacking_wct is not None

    def test_no_handover_short_distance(self):
        assert self.report.inbound_rack_wct.uses_handover is False

    def test_xqe_fleet_present(self):
        assert self.report.total_xqe_fleet > 0

    def test_no_xpl_for_short_distances(self):
        assert self.report.total_xpl_fleet == 0


class TestLargeWarehouseFleet:
    def setup_method(self):
        cfg = WarehouseLayoutLoader().load_dict(_large_config())
        self.report = FleetSizer(cfg).calculate()

    def test_report_valid(self):
        assert self.report.is_valid

    def test_uses_handover_for_long_distances(self):
        assert self.report.inbound_rack_wct.uses_handover is True
        assert self.report.outbound_rack_wct.uses_handover is True

    def test_has_xpl_fleet(self):
        assert self.report.total_xpl_fleet > 0

    def test_has_xqe_fleet(self):
        assert self.report.total_xqe_fleet > 0

    def test_larger_fleet_than_small(self):
        small_cfg = WarehouseLayoutLoader().load_dict(_small_config())
        small_report = FleetSizer(small_cfg).calculate()
        assert self.report.total_xqe_fleet >= small_report.total_xqe_fleet


class TestXSCPendingBlocking:
    def setup_method(self):
        cfg = WarehouseLayoutLoader().load_dict(_xsc_config())
        self.report = FleetSizer(cfg).calculate()

    def test_report_has_errors(self):
        assert len(self.report.errors) > 0

    def test_report_invalid(self):
        assert not self.report.is_valid

    def test_error_mentions_xsc(self):
        error_text = " ".join(self.report.errors).lower()
        assert "xsc" in error_text or "2.3" in error_text or "2300" in error_text


class TestNarrowAisleXNAFleet:
    def setup_method(self):
        cfg = WarehouseLayoutLoader().load_dict(_narrow_config())
        self.report = FleetSizer(cfg).calculate()

    def test_report_valid(self):
        assert self.report.is_valid

    def test_has_xna_fleet(self):
        assert self.report.total_xna_fleet > 0

    def test_has_xpl_fleet(self):
        assert self.report.total_xpl_fleet > 0

    def test_xna_uses_handover(self):
        assert self.report.inbound_rack_wct is not None
        assert self.report.inbound_rack_wct.uses_handover is True
        assert self.report.outbound_rack_wct is not None
        assert self.report.outbound_rack_wct.uses_handover is True


class TestFleetSizingReportSerialization:
    def test_to_dict_keys(self):
        cfg = WarehouseLayoutLoader().load_dict(_small_config())
        report = FleetSizer(cfg).calculate()
        d = report.to_dict()
        assert "warehouse" in d
        assert "valid" in d
        assert "fleet" in d
        assert "requirements" in d

    def test_fleet_dict_has_agv_types(self):
        cfg = WarehouseLayoutLoader().load_dict(_small_config())
        report = FleetSizer(cfg).calculate()
        d = report.to_dict()
        assert "XQE_122" in d["fleet"]
        assert "XPL_201" in d["fleet"]
        assert "XNA" in d["fleet"]

    def test_requirements_non_empty(self):
        cfg = WarehouseLayoutLoader().load_dict(_small_config())
        report = FleetSizer(cfg).calculate()
        d = report.to_dict()
        assert len(d["requirements"]) > 0


class TestFleetRequirementStats:
    def test_actual_utilization_reasonable(self):
        cfg = WarehouseLayoutLoader().load_dict(_small_config())
        report = FleetSizer(cfg).calculate()
        for req in report.fleet_requirements:
            # Actual utilization should be ≤ 1.0 and > 0 for positive tasks
            assert req.actual_utilization <= 1.0
            assert req.actual_utilization > 0

    def test_cycle_time_positive(self):
        cfg = WarehouseLayoutLoader().load_dict(_small_config())
        report = FleetSizer(cfg).calculate()
        for req in report.fleet_requirements:
            assert req.avg_cycle_time_s > 0
