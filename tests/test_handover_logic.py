"""
Tests for handover logic – XNA always handover, XQE distance-based.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.warehouse_layout import (
    HANDOVER_DISTANCE_THRESHOLD_M,
    needs_handover_xqe,
    select_agv_for_rack_aisle,
)
from src.fleet_sizer import FleetSizer
from src.warehouse_layout import WarehouseLayoutLoader


# ---------------------------------------------------------------------------
# Helper: build a minimal config dict
# ---------------------------------------------------------------------------

def _make_config(
    aisle_width_mm: float = 2840,
    inbound_to_handover_mm: float = 10000,
    rack_handover_to_outbound_mm: float = 10000,
    handover_to_rack_mm: float = 5000,
    inbound_daily: int = 100,
    outbound_daily: int = 100,
) -> dict:
    return {
        "warehouse": {"name": "Test WH", "width_mm": 30000, "length_mm": 40000},
        "inbound": {
            "distance_to_handover_mm": inbound_to_handover_mm,
            "distance_to_rack_handover_mm": inbound_to_handover_mm,
            "distance_to_stacking_handover_mm": inbound_to_handover_mm,
        },
        "outbound": {
            "rack_handover_to_outbound_mm": rack_handover_to_outbound_mm,
            "stacking_handover_to_outbound_mm": rack_handover_to_outbound_mm,
            "distance_from_handover_mm": rack_handover_to_outbound_mm,
        },
        "distances": {
            "handover_to_rack_mm": handover_to_rack_mm,
            "handover_to_stacking_mm": handover_to_rack_mm,
        },
        "rack_storage": {
            "aisle_width_mm": aisle_width_mm,
            "aisle_depth_mm": 15000,
            "pallet_spacing_mm": 950,
            "shelves": [
                {"height_mm": 300},
                {"height_mm": 1500},
                {"height_mm": 3000},
                {"height_mm": 4500},
            ],
        },
        "ground_stacking": {
            "rows": 4,
            "cols": 3,
            "levels": 3,
            "level_height_mm": 1200,
            "area_length_mm": 8000,
            "area_width_mm": 6000,
        },
        "workflow": {"rack_fraction": 0.6, "stacking_fraction": 0.4},
        "throughput": {
            "inbound": {"daily_tasks": inbound_daily, "operating_hours": 8.0, "utilization": 0.75},
            "outbound": {"daily_tasks": outbound_daily, "operating_hours": 8.0, "utilization": 0.75},
        },
    }


class TestXNAAlwaysHandover:
    """XNA (narrow aisle) must ALWAYS use handover, regardless of distance."""

    def test_xna_handover_short_distance(self):
        """Even at 5m distance, XNA must use handover."""
        raw = _make_config(aisle_width_mm=1900, inbound_to_handover_mm=5000)
        cfg = WarehouseLayoutLoader().load_dict(raw)
        sizer = FleetSizer(cfg)
        report = sizer.calculate()
        assert report.inbound_rack_wct is not None
        assert report.inbound_rack_wct.uses_handover is True

    def test_xna_handover_medium_distance(self):
        raw = _make_config(aisle_width_mm=1800, inbound_to_handover_mm=30000)
        cfg = WarehouseLayoutLoader().load_dict(raw)
        sizer = FleetSizer(cfg)
        report = sizer.calculate()
        assert report.inbound_rack_wct is not None
        assert report.inbound_rack_wct.uses_handover is True

    def test_xna_handover_long_distance(self):
        raw = _make_config(aisle_width_mm=1717, inbound_to_handover_mm=80000)
        cfg = WarehouseLayoutLoader().load_dict(raw)
        sizer = FleetSizer(cfg)
        report = sizer.calculate()
        assert report.inbound_rack_wct is not None
        assert report.inbound_rack_wct.uses_handover is True

    def test_xna_outbound_uses_handover(self):
        raw = _make_config(aisle_width_mm=1900, rack_handover_to_outbound_mm=5000)
        cfg = WarehouseLayoutLoader().load_dict(raw)
        sizer = FleetSizer(cfg)
        report = sizer.calculate()
        assert report.outbound_rack_wct is not None
        assert report.outbound_rack_wct.uses_handover is True

    def test_xna_inbound_uses_xpl_and_xna(self):
        raw = _make_config(aisle_width_mm=1900, inbound_to_handover_mm=10000)
        cfg = WarehouseLayoutLoader().load_dict(raw)
        sizer = FleetSizer(cfg)
        report = sizer.calculate()
        agv_types = {r.agv_type for r in report.fleet_requirements if r.storage_type == "rack"}
        assert "XPL_201" in agv_types
        assert any("XNA" in t for t in agv_types)


class TestXQEDistanceBasedHandover:
    """XQE uses handover ONLY when distance ≥ 50 m."""

    def test_xqe_no_handover_short_inbound(self):
        """Distance 30m → no handover for inbound rack."""
        raw = _make_config(aisle_width_mm=2840, inbound_to_handover_mm=30000)
        cfg = WarehouseLayoutLoader().load_dict(raw)
        sizer = FleetSizer(cfg)
        report = sizer.calculate()
        assert report.inbound_rack_wct is not None
        assert report.inbound_rack_wct.uses_handover is False

    def test_xqe_no_handover_49m(self):
        """Distance 49.9m → no handover."""
        raw = _make_config(aisle_width_mm=2840, inbound_to_handover_mm=49900)
        cfg = WarehouseLayoutLoader().load_dict(raw)
        sizer = FleetSizer(cfg)
        report = sizer.calculate()
        assert report.inbound_rack_wct is not None
        assert report.inbound_rack_wct.uses_handover is False

    def test_xqe_handover_at_50m(self):
        """Distance exactly 50m → handover triggered."""
        raw = _make_config(aisle_width_mm=2840, inbound_to_handover_mm=50000)
        cfg = WarehouseLayoutLoader().load_dict(raw)
        sizer = FleetSizer(cfg)
        report = sizer.calculate()
        assert report.inbound_rack_wct is not None
        assert report.inbound_rack_wct.uses_handover is True

    def test_xqe_handover_long_inbound(self):
        """Distance 80m → handover."""
        raw = _make_config(aisle_width_mm=2840, inbound_to_handover_mm=80000)
        cfg = WarehouseLayoutLoader().load_dict(raw)
        sizer = FleetSizer(cfg)
        report = sizer.calculate()
        assert report.inbound_rack_wct is not None
        assert report.inbound_rack_wct.uses_handover is True

    def test_xqe_no_handover_outbound_short(self):
        """Outbound 40m → no handover."""
        raw = _make_config(aisle_width_mm=2840, rack_handover_to_outbound_mm=40000)
        cfg = WarehouseLayoutLoader().load_dict(raw)
        sizer = FleetSizer(cfg)
        report = sizer.calculate()
        assert report.outbound_rack_wct is not None
        assert report.outbound_rack_wct.uses_handover is False

    def test_xqe_handover_outbound_long(self):
        """Outbound 70m → handover."""
        raw = _make_config(aisle_width_mm=2840, rack_handover_to_outbound_mm=70000)
        cfg = WarehouseLayoutLoader().load_dict(raw)
        sizer = FleetSizer(cfg)
        report = sizer.calculate()
        assert report.outbound_rack_wct is not None
        assert report.outbound_rack_wct.uses_handover is True

    def test_xqe_inbound_with_handover_uses_xpl(self):
        """When handover is triggered, XPL_201 should be in fleet requirements."""
        raw = _make_config(aisle_width_mm=2840, inbound_to_handover_mm=60000)
        cfg = WarehouseLayoutLoader().load_dict(raw)
        sizer = FleetSizer(cfg)
        report = sizer.calculate()
        rack_agvs = {r.agv_type for r in report.fleet_requirements
                     if r.direction == "inbound" and r.storage_type == "rack"}
        assert "XPL_201" in rack_agvs
        assert "XQE_122" in rack_agvs

    def test_xqe_inbound_no_handover_single_agv(self):
        """Without handover, only XQE_122 for rack inbound."""
        raw = _make_config(aisle_width_mm=2840, inbound_to_handover_mm=20000)
        cfg = WarehouseLayoutLoader().load_dict(raw)
        sizer = FleetSizer(cfg)
        report = sizer.calculate()
        rack_agvs = {r.agv_type for r in report.fleet_requirements
                     if r.direction == "inbound" and r.storage_type == "rack"}
        assert "XPL_201" not in rack_agvs
        assert "XQE_122" in rack_agvs


class TestHandoverDistanceThreshold:
    def test_threshold_value(self):
        assert HANDOVER_DISTANCE_THRESHOLD_M == 50.0

    def test_below_threshold(self):
        for d in [0, 10, 25, 49.9]:
            assert needs_handover_xqe(d) is False

    def test_at_and_above_threshold(self):
        for d in [50.0, 50.1, 60, 100]:
            assert needs_handover_xqe(d) is True
